# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI chat panel inside Fission 180 (brief home-cloud-ai.md section 4.5, milestone M4;
parity: docs/fission180/parity/ai.md). The person picks an AI (Claude, ChatGPT, Gemini, or a
local model through Ollama / LM Studio), pastes their own key and chats; the AI builds with
the same 16 tools AI apps get (fission180/ai/tools_core.py), each one Undo step.

The conversation loop (fission180/ai/chat_core.py) waits on the network, so it runs on a
worker thread; Fission 180 is only touched on its own thread: the worker hands each tool call
over (a queue the panel's timer empties) and waits for the answer (bridge.call). Keys are
kept with fission180/secrets_store.py (Windows: encrypted for this user) and never logged.

Answers show word by word, as they arrive: the worker queues each piece of text
("text_delta"), and the panel's timer (every 50 ms) adds what came to the AI's paragraph at
the end of the conversation (the "live" paragraph), redrawn once per tick however many
pieces came. Anything else the panel writes closes that paragraph first.
"""

import html
import os
import queue
import threading

import FreeCAD as App

from .. import commands, log, secrets_store, warn
from ..compat import QtCore, QtGui, QtWidgets
from . import bridge, chat_core, providers

PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/AI"
TOOL_WAIT = 180.0  # seconds the worker waits for one tool call (a question may be open)


def secrets_folder():
    return os.path.join(App.getUserAppDataDir(), "Fission180", "secrets")


def key_name(provider):
    return "ai.%s" % provider


def _rebuilding():
    """True when a part of the open design is being rebuilt with a timeline (Auto Timeline):
    the chat may then make more requests per Send (chat_core.step_limit)."""
    try:
        from .. import rebuild

        return bool(rebuild.active_references(App.ActiveDocument))
    except Exception:
        return False


def _console(line):
    """chat_core's own log lines (already "[Fission 180] ..."): into FreeCAD's log, not the
    Report view (a provider's error words are not Fission 180 errors)."""
    try:
        App.Console.PrintLog(str(line) + "\n")
    except Exception:
        pass


class ChatPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Fission180AIChat")
        self.chat = None
        self.events = queue.Queue()  # (kind, data) from the worker
        self.calls = queue.Queue()  # tool calls waiting for Fission 180's thread
        self.worker = None
        self._live = None  # the AI's paragraph being written: {"text", "start", "dirty"}
        self._turn_shown = False  # this step's words are on screen already (streamed)
        column = QtWidgets.QVBoxLayout(self)
        column.setContentsMargins(4, 4, 4, 4)
        form = QtWidgets.QFormLayout()
        self.provider = QtWidgets.QComboBox()
        self.provider.setObjectName("Fission180ChatProvider")
        for name in providers.ORDER:
            self.provider.addItem(providers.get(name)["display_name"], name)
        form.addRow("AI", self.provider)
        row = QtWidgets.QHBoxLayout()
        self.model = QtWidgets.QComboBox()
        self.model.setObjectName("Fission180ChatModel")
        self.model.setEditable(True)
        row.addWidget(self.model, 1)
        self.models_button = QtWidgets.QPushButton("List")
        self.models_button.setObjectName("Fission180ChatModels")
        self.models_button.setToolTip("Ask the provider which models this key can use")
        self.models_button.clicked.connect(self.list_models)
        row.addWidget(self.models_button)
        form.addRow("Model", row)
        self.address = QtWidgets.QLineEdit()
        self.address.setObjectName("Fission180ChatAddress")
        self.address.setToolTip(
            "Ollama: http://localhost:11434/v1, LM Studio: http://localhost:1234/v1"
        )
        form.addRow("Address", self.address)
        row = QtWidgets.QHBoxLayout()
        self.key = QtWidgets.QLineEdit()
        self.key.setObjectName("Fission180ChatKey")
        self.key.setEchoMode(QtWidgets.QLineEdit.Password)
        self.key.setPlaceholderText("Paste your API key")
        row.addWidget(self.key, 1)
        self.save_key_button = QtWidgets.QPushButton("Save key")
        self.save_key_button.setObjectName("Fission180ChatSaveKey")
        self.save_key_button.clicked.connect(self.save_key)
        row.addWidget(self.save_key_button)
        form.addRow("Key", row)
        column.addLayout(form)
        self.note = QtWidgets.QLabel("")
        self.note.setObjectName("Fission180ChatNote")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color: #c3cad4;")
        column.addWidget(self.note)
        self.transcript = QtWidgets.QTextBrowser()
        self.transcript.setObjectName("Fission180ChatLog")
        column.addWidget(self.transcript, 1)
        # the newest words stay in view while the conversation grows, unless the person
        # scrolled up to read (the scroll bar says when the text got longer: its range)
        self._follow = True
        bar = self.transcript.verticalScrollBar()
        bar.valueChanged.connect(self._scrolled)
        bar.rangeChanged.connect(self._grown)
        self.input = QtWidgets.QPlainTextEdit()
        self.input.setObjectName("Fission180ChatInput")
        self.input.setPlaceholderText("Ask the AI to build something, e.g. a 40 x 30 x 10 box")
        self.input.setMaximumHeight(80)
        column.addWidget(self.input)
        row = QtWidgets.QHBoxLayout()
        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.setObjectName("Fission180ChatSend")
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.send_button)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setObjectName("Fission180ChatStop")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        row.addWidget(self.stop_button)
        row.addStretch(1)
        self.new_button = QtWidgets.QPushButton("New chat")
        self.new_button.setObjectName("Fission180ChatNew")
        self.new_button.clicked.connect(self.new_chat)
        row.addWidget(self.new_button)
        column.addLayout(row)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._drain)
        self.timer.start()
        self._restore()
        self.provider.currentIndexChanged.connect(self._provider_changed)
        self._provider_changed()

    # -- settings
    def _prefs(self):
        return App.ParamGet(PREFS)

    def _restore(self):
        index = self.provider.findData(self._prefs().GetString("ChatProvider", "anthropic"))
        self.provider.setCurrentIndex(max(0, index))

    def provider_name(self):
        return self.provider.currentData()

    def _provider_changed(self, *_args):
        try:
            name = self.provider_name()
            entry = providers.get(name)
            self._prefs().SetString("ChatProvider", name)
            self.model.clear()
            saved = self._prefs().GetString("ChatModel_" + name, "")
            model = saved or entry["default_model"]
            if model:
                self.model.addItem(model)
            self.model.setEditText(model)
            local = not entry["needs_key"]
            self.address.setText(self._prefs().GetString("ChatAddress", entry["base_url"]))
            self.address.setVisible(local)
            self.key.setVisible(entry["needs_key"])
            self.save_key_button.setVisible(entry["needs_key"])
            stored = (
                secrets_store.read(key_name(name), secrets_folder()) if entry["needs_key"] else None
            )
            self.key.setText(stored or "")
            words = [chat_core.COST_NOTE]
            if entry["needs_key"]:
                warning = secrets_store.warning(secrets_folder())
                if warning:
                    words.append(warning)
            self.note.setText("\n".join(words))
        except Exception as exc:
            warn("AI chat: %s" % exc)

    def save_key(self):
        try:
            name = self.provider_name()
            value = self.key.text().strip()
            if not value:
                ok = secrets_store.delete(key_name(name), secrets_folder())
                commands.tell("Key removed." if ok else "No key was kept.")
                QtCore.QTimer.singleShot(0, _ais_changed)
                return ok
            ok = secrets_store.store(key_name(name), value, secrets_folder())
            commands.tell(
                "Key kept for %s." % providers.get(name)["display_name"]
                if ok
                else "The key could not be kept."
            )
            log("AI chat: key %s for %s" % ("kept" if ok else "NOT kept", name))
            QtCore.QTimer.singleShot(0, _ais_changed)
            return ok
        except Exception as exc:
            warn("AI chat: %s" % exc)
            return False

    # -- the conversation
    def say(self, who, text, colour=None):
        self._close_live()
        style = (" style='color:%s'" % colour) if colour else ""
        safe = html.escape(str(text)).replace("\n", "<br>")
        self.transcript.append("<p%s><b>%s</b> %s</p>" % (style, who, safe))

    def _delta(self, piece):
        """A piece of the AI's answer arrived: kept until the timer's next redraw."""
        if not piece:
            return
        if self._live is None:
            self._live = {"text": "", "start": None, "dirty": False}
        self._live["text"] += piece
        self._live["dirty"] = True

    def _render_live(self):
        """The AI's live paragraph with all the words that came so far (it is made with the
        first word; a step that only had spaces so far shows nothing yet)."""
        live = self._live
        if live is None or not live["dirty"]:
            return
        live["dirty"] = False
        text = live["text"].strip()
        if not text:
            return
        document = self.transcript.document()
        if live["start"] is None:
            self.transcript.append("<p><b>AI:</b> </p>")
            live["start"] = document.lastBlock().position()
        cursor = QtGui.QTextCursor(document)
        cursor.setPosition(live["start"])
        cursor.movePosition(QtGui.QTextCursor.End, QtGui.QTextCursor.KeepAnchor)
        cursor.insertHtml("<b>AI:</b> " + html.escape(text).replace("\n", "<br>"))
        self._turn_shown = True

    def _scrolled(self, value):
        try:
            bar = self.transcript.verticalScrollBar()
            self._follow = value >= bar.maximum() - 4
        except Exception as exc:
            warn("AI chat: %s" % exc)

    def _grown(self, _low, high):
        try:
            if self._follow:
                self.transcript.verticalScrollBar().setValue(high)
        except Exception as exc:
            warn("AI chat: %s" % exc)

    def _close_live(self):
        """Show what is still waiting and end the live paragraph: the next words start a
        new one below whatever is written now."""
        if self._live is not None:
            self._render_live()
            self._live = None

    def live_text(self):
        """The words of the answer arriving now ("" when none is)."""
        return self._live["text"].strip() if self._live is not None else ""

    def _chat_for(self, name, model, key, base_url):
        """The conversation, kept across sends; another AI or model continues it."""
        if (
            self.chat is not None
            and self.chat.provider_name == name
            and self.chat.model == model
            and self.chat.base_url == base_url
        ):
            self.chat._key = key or None
            self.chat.max_steps = chat_core.step_limit(_rebuilding())
            return self.chat
        history = self.chat.history if self.chat is not None else None
        self.chat = chat_core.Chat(
            providers.adapter(name),
            model,
            key=key,
            base_url=base_url,
            call_tool=self._call_tool,
            log=_console,
            history=history,
            max_steps=chat_core.step_limit(_rebuilding()),
        )
        return self.chat

    def busy(self):
        return self.worker is not None and self.worker.is_alive()

    def send(self):
        try:
            if self.busy():
                return False
            text = self.input.toPlainText().strip()
            if not text:
                return False
            name = self.provider_name()
            entry = providers.get(name)
            key = self.key.text().strip() if entry["needs_key"] else None
            if entry["needs_key"] and not key:
                self.say(
                    "Fission 180:",
                    "Paste your %s API key first (Save key keeps it)." % entry["display_name"],
                    "#ffb74d",
                )
                return False
            model = self.model.currentText().strip()
            base_url = self.address.text().strip() if not entry["needs_key"] else entry["base_url"]
            if not entry["needs_key"]:
                self._prefs().SetString("ChatAddress", base_url)
            if model:
                self._prefs().SetString("ChatModel_" + name, model)
            chat = self._chat_for(name, model, key, base_url)
            self.input.clear()
            self.say("You:", text)
            self.send_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.worker = threading.Thread(
                target=self._work, args=(chat, text), name="Fission180AIChat", daemon=True
            )
            self.worker.start()
            return True
        except Exception as exc:
            warn("AI chat: %s" % exc)
            return False

    def _work(self, chat, text):
        """The worker thread: the whole loop; events go to the panel through a queue."""
        try:
            chat.send(text, lambda kind, data: self.events.put((kind, data)))
        except Exception as exc:  # (chat_core answers in sentences; this is a last guard)
            self.events.put(("error", {"text": "The chat stopped: %s" % exc}))
            self.events.put(("done", {"ok": False}))

    def _call_tool(self, name, args):
        """Called on the worker thread: Fission 180's thread runs the tool, the worker waits."""
        job = {"name": name, "args": args, "done": threading.Event(), "result": None}
        self.calls.put(job)
        if not job["done"].wait(TOOL_WAIT):
            return {
                "text": "Fission 180 did not finish %s in time." % name,
                "is_error": True,
                "image_png_base64": None,
            }
        return job["result"]

    def _drain(self):
        """Fission 180's thread: run waiting tool calls, show the worker's events."""
        try:
            while True:
                try:
                    job = self.calls.get_nowait()
                except queue.Empty:
                    break
                try:
                    job["result"] = bridge.call(job["name"], job["args"], from_chat=True)
                except Exception as exc:
                    job["result"] = {
                        "text": "Not done: %s" % exc,
                        "is_error": True,
                        "image_png_base64": None,
                    }
                job["done"].set()
            # (a piece of a streamed answer is cheap: many per tick, one redraw at the end)
            for _n in range(1000):
                try:
                    kind, data = self.events.get_nowait()
                except queue.Empty:
                    break
                if not isinstance(data, dict):  # chat_core: "text", "progress", "error"
                    data = {"text": "" if data is None else str(data)}
                self._event(kind, data)
            self._render_live()
        except RuntimeError:
            pass  # (the panel was closed)
        except Exception as exc:
            warn("AI chat: %s" % exc)

    def _event(self, kind, data):
        if kind == "text_delta":
            self._delta(data.get("text", ""))
        elif kind == "models":
            self._models(data.get("models", []))
        elif kind == "text":
            # the step's whole text; a streamed one is on screen already
            if data.get("streamed"):
                self._close_live()
            if data.get("text") and not (data.get("streamed") and self._turn_shown):
                self.say("AI:", data["text"])
            self._turn_shown = False
        elif kind == "progress" and data.get("text"):
            self.say("AI (thinking):", data["text"], "#9aa4b2")
        elif kind == "tool_call":
            self._turn_shown = False
            self.say("Tool:", "%s" % data.get("name"), "#3fa9f5")
        elif kind == "tool_result":
            text = data.get("text", "")
            short = text if len(text) < 240 else text[:237] + "..."
            self.say("Fission 180:", short, "#ef6f6c" if data.get("is_error") else "#7fd18b")
        elif kind == "error":
            self.say("Fission 180:", data.get("text", ""), "#ef6f6c")
        elif kind == "done":
            self._close_live()
            self._turn_shown = False
            self.send_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            if data.get("reason") and not data.get("ok"):
                self.say("Fission 180:", str(data["reason"]), "#ffb74d")

    def stop(self):
        try:
            if self.chat is not None:
                self.chat.stop()
            self.say("Fission 180:", "Stopping after the current step...", "#ffb74d")
        except Exception as exc:
            warn("AI chat: %s" % exc)

    def new_chat(self):
        if self.busy():
            commands.tell("Stop the chat first.")
            return
        self.chat = None
        self._live, self._turn_shown = None, False
        self.transcript.clear()

    def list_models(self):
        """Ask the provider for its models (a worker thread: the network may be slow)."""
        name = self.provider_name()
        entry = providers.get(name)
        key = self.key.text().strip() or None
        base_url = self.address.text().strip() if not entry["needs_key"] else entry["base_url"]
        self.models_button.setEnabled(False)

        def fetch():
            try:
                found = providers.adapter(name).list_models(key, base_url)
            except Exception:
                found = []
            self.events.put(("models", {"models": found}))

        self._models_thread = threading.Thread(target=fetch, daemon=True)
        self._models_thread.start()

    def _models(self, found):
        self.models_button.setEnabled(True)
        current = self.model.currentText()
        self.model.clear()
        for model in found:
            self.model.addItem(model)
        self.model.setEditText(current or (found[0] if found else ""))
        if not found:
            self.say(
                "Fission 180:",
                "The provider listed no models (check the key or the address).",
                "#ffb74d",
            )


def _ais_changed():
    """A key kept or removed: the AI panel's and Home's lists of AIs again."""
    try:
        from .. import ai_ui

        ai_ui._refresh_home()
    except Exception as exc:
        warn("AI chat: %s" % exc)


def panel():
    """The Chat tab of the AI panel while the panel exists, else None."""
    from .. import ai_panel_ui

    page = ai_panel_ui.panel()
    return page.chat if page is not None else None


def show():
    """The AI panel on its Chat tab."""
    from .. import ai_panel_ui

    return ai_panel_ui.show("chat")
