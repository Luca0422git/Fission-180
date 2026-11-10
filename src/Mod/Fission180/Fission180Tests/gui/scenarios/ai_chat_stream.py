# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI chat shows its answers word by word, as they arrive (docs/fission180/known-issues.md
had "The AI chat shows an answer only when it is complete"), against a fake AI provider: a
local server in this test that streams like Anthropic's Messages API (server-sent events)
and like Ollama / LM Studio (OpenAI-compatible Chat Completions). Real clicks and typing.

Path 1, Claude: the address of Claude's API is this test's server for the test; a key typed.
Path 2, a long answer: the server sends the first words, then holds the rest until the test
  lets it go. The words already sent are in the panel while the answer is not over (Send
  greyed, Stop offered), the paragraph grew word by word with the newest words in view, the
  window kept answering; let go, the whole answer is there exactly once and Send is back.
Path 3, "make a 40 x 30 x 10 box" with streamed tool calls (the arguments come in pieces of
  JSON): the box is built (12000 mm3), one Undo step each; the words before each call are
  shown before the call runs; the model got the calls and Fission 180's answers back.
Path 4, Stop in the middle of an answer the server keeps open: the chat ends at once (it does
  not wait for the server), Send is back, the words already shown stay.
Path 5, the connection drops in the middle of an answer: a plain message says so; Send is back.
Path 6, a local model (OpenAI-compatible) streams too: words, a tool call in pieces, the
  answer; the conversation still follows its newest lines.
"""

import http.server
import json
import socket
import threading
import time

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import widget_input as wi

KEY = "sk-ant-test-STREAM-0123456789"
PACE = 0.03  # seconds between two pieces of an answer (a model writing)
LONG = [
    "Extrude ",
    "pulls ",
    "a closed ",
    "sketch profile ",
    "straight out ",
    "into a ",
    "solid body. ",
    "Pick the ",
    "profile, ",
    "drag the ",
    "arrow or ",
    "type a distance.",  # (12th piece: the server holds the rest here)
    "\n\nTaper Angle ",
    "leans the ",
    "sides in ",
    "or out, ",
    "and Operation ",
    "chooses whether ",
    "it joins, ",
    "cuts or ",
    "makes a new body.",
]
LONG_TEXT = "".join(LONG)
SKETCH_ARGS = {"plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]}
EXTRUDE_ARGS = {"profile": "Sketch1", "distance": 10}

s = {
    "plans": [],  # what the fake server answers, request by request
    "requests": [],  # (path, body) of every request
    "waiting": threading.Event(),  # the server holds the rest of an answer
    "release": threading.Event(),  # ... until this is set
    "holding": threading.Event(),  # the server keeps an answer open (Path 4)
    "end": threading.Event(),  # the test is over: every held answer ends
    "samples": [],  # (seconds, words in the AI's live paragraph) while the chat works
    "gap": 0.0,  # the longest the window did not answer while the chat worked
}


# -- what the fake provider sends ---------------------------------------------------------
def claude(pieces=(), tool=None, stop="end_turn"):
    """The events of a streamed Claude answer: text in pieces, then a tool call whose
    arguments come in pieces of JSON text."""
    events = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "model": "claude-opus-5-5",
                    "content": [],
                    "stop_reason": None,
                    "usage": {"input_tokens": 100, "output_tokens": 1},
                },
            },
        ),
        ("ping", {"type": "ping"}),
    ]
    index = 0
    if pieces:
        events.append(
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
            )
        )
        for piece in pieces:
            events.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": piece},
                    },
                )
            )
        events.append(("content_block_stop", {"type": "content_block_stop", "index": 0}))
        index = 1
    if tool:
        call_id, name, args = tool
        raw = json.dumps(args)
        events.append(
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "tool_use", "id": call_id, "name": name, "input": {}},
                },
            )
        )
        for start in range(0, len(raw), 6):
            events.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": raw[start : start + 6],
                        },
                    },
                )
            )
        events.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
    events += [
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop},
                "usage": {"output_tokens": 30},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return events


def local(pieces=(), tool=None):
    """The events of a streamed OpenAI-compatible answer (Ollama / LM Studio)."""

    def chunk(delta, finish=None):
        return (
            None,
            {
                "object": "chat.completion.chunk",
                "model": "qwen3:8b",
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            },
        )

    events = [chunk({"role": "assistant", "content": ""})]
    events += [chunk({"content": piece}) for piece in pieces]
    if tool:
        call_id, name, raw = tool
        events.append(
            chunk(
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": ""},
                        }
                    ]
                }
            )
        )
        for part in raw:
            events.append(chunk({"tool_calls": [{"index": 0, "function": {"arguments": part}}]}))
    events.append(chunk({}, "tool_calls" if tool else "stop"))
    events.append((None, "[DONE]"))
    return events


class _Fake(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def _json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/models"):
            self._json({"object": "list", "data": [{"id": "qwen3:8b", "object": "model"}]})
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _send(self, name, data):
        text = data if isinstance(data, str) else json.dumps(data)
        raw = (("event: %s\n" % name) if name else "") + "data: %s\n\n" % text
        raw = raw.encode("utf-8")
        self.wfile.write(b"%x\r\n%s\r\n" % (len(raw), raw))
        self.wfile.flush()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        s["requests"].append((self.path, body))
        plan = s["plans"].pop(0) if s["plans"] else {"events": claude(["Nothing more to do."])}
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            for number, (name, data) in enumerate(plan["events"]):
                self._send(name, data)
                if plan.get("paced"):
                    time.sleep(PACE)  # on purpose (the app under test): a model writes
                if plan.get("hold_after") == number:
                    s["waiting"].set()
                    s["release"].wait(120)  # (until the test lets the rest go)
                if plan.get("keep_open_after") == number:
                    s["holding"].set()
                    s["end"].wait(120)  # (an answer that never ends: only Stop ends it)
                    self.close_connection = True
                    return
                if plan.get("drop_after") == number:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
            self.wfile.write(b"0\r\n\r\n")
        except OSError:
            self.close_connection = True  # (the chat closed the connection: Stop)


# -- helpers -------------------------------------------------------------------------------
def panel():
    from fission180.ai import chat_ui

    return chat_ui.panel()


def transcript():
    p = panel()
    return p.transcript.toPlainText() if p is not None else ""


def body_volume():
    doc = App.ActiveDocument
    if doc is None:
        return None
    return sum(
        o.Shape.Volume
        for o in doc.Objects
        if o.TypeId == "PartDesign::Body" and not o.Shape.isNull()
    )


def pick(combo, data):
    """Choose an entry with the keyboard (as a person tabbing through the form)."""
    from PySide6 import QtTest

    index = combo.findData(data)
    combo.setFocus()
    while combo.currentIndex() != index:
        key = QtCore.Qt.Key_Down if combo.currentIndex() < index else QtCore.Qt.Key_Up
        QtTest.QTest.keyClick(combo, key)


def newest_in_view():
    bar = panel().transcript.verticalScrollBar()
    return bar.value() == bar.maximum(), (bar.value(), bar.maximum())


def ask(text):
    from PySide6 import QtTest

    p = panel()
    p.input.setFocus()
    QtTest.QTest.keyClicks(p.input, text)
    s["samples"], s["gap"], s["last_tick"] = [], 0.0, None
    wi.click(p.send_button)


def watch():
    """Every 20 ms while the chat works: how many words the AI's paragraph shows, and how
    long since the last tick (the window answering)."""
    try:
        p = panel()
        now = time.monotonic()
        if p is None or not p.busy():
            s["last_tick"] = None
            return
        if s.get("last_tick") is not None:
            s["gap"] = max(s["gap"], now - s["last_tick"])
        s["last_tick"] = now
        words = len(p.live_text().split())
        if not s["samples"] or s["samples"][-1][1] != words:
            s["samples"].append((now, words))
    except RuntimeError:
        pass


# -- Path 1 --------------------------------------------------------------------------------
def setup():
    import signal

    from fission180.ai import providers

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)  # (as the bridge does: bridge.py)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Fake)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    s["server"] = server
    s["base"] = "http://127.0.0.1:%d" % server.server_address[1]
    # Claude's API address, for this test only: the fake server (given back in tidy)
    s["claude_url"] = providers.PROVIDERS["anthropic"]["base_url"]
    providers.PROVIDERS["anthropic"]["base_url"] = s["base"]
    timer = s["watch"] = QtCore.QTimer()
    timer.setInterval(20)
    timer.timeout.connect(watch)
    timer.start()
    from FreeCADGui import runCommand

    runCommand("Fission180_AIChat")


def choose_claude():
    p = panel()
    h.check("the AI chat panel opened", p is not None and p.isVisible())
    if p is None:
        return
    pick(p.provider, "anthropic")
    h.check("Claude needs a key", p.key.isVisible() and not p.address.isVisible())
    vi.type_into(p.key, KEY)


# -- Path 2 --------------------------------------------------------------------------------
def ask_long():
    s["plans"] = [{"events": claude(LONG), "paced": True, "hold_after": 2 + 12}]
    ask("what does extrude do?")


# (the words come from the fake server's thread; the panel shows them on its timer)
ask_long.done = lambda: s["waiting"].is_set() and "type a distance." in transcript()
ask_long.done_what = "the first words shown while the server holds the rest"
ask_long.while_busy = True  # the answer is not over: the chat works on purpose


def words_so_far():
    p = panel()
    text = transcript()
    h.check("the first words are shown before the answer is over", "Extrude pulls" in text, text)
    h.check("... the rest is not there yet", "makes a new body" not in text, text[-300:])
    h.check(
        "... the chat still works (Send greyed, Stop offered)",
        p.busy() and not p.send_button.isEnabled() and p.stop_button.isEnabled(),
    )
    counts = [n for _t, n in s["samples"]]
    # (how many redraws the pieces were seen in depends on the machine's pace: a speed check)
    h.speed_check(
        "the paragraph grew word by word", len(counts) >= 4 and counts == sorted(counts), counts
    )
    h.check("the newest words are in view", *newest_in_view())
    h.shot("streaming")
    s["release"].set()


words_so_far.done = lambda: not panel().busy() and "makes a new body." in transcript()
words_so_far.done_what = "the whole answer shown and the chat done"
words_so_far.while_busy = True  # the rest of the answer arrives during this step


def whole_answer():
    p = panel()
    text = transcript()
    expected = "AI: " + LONG_TEXT
    h.check("the whole answer is shown", expected in text, text[-700:])
    h.check(
        "... once",
        text.count("makes a new body.") == 1 and text.count("Extrude pulls") == 1,
        text[-700:],
    )
    h.check("Send is ready again", p.send_button.isEnabled() and not p.stop_button.isEnabled())
    h.speed_check(
        "the window kept answering while the words came (longest pause %.2f s)" % s["gap"],
        s["gap"] < 1.0 * h.SLOWDOWN,
        s["gap"],
    )
    body = s["requests"][-1][1]
    h.check(
        "Claude was asked for a stream",
        s["requests"][-1][0] == "/v1/messages" and body.get("stream") is True,
        s["requests"][-1][0],
    )
    h.check("the key never shows in Fission 180's log", KEY not in h.report_text())


# -- Path 3 --------------------------------------------------------------------------------
def ask_for_a_box():
    s["plans"] = [
        {
            "events": claude(
                ["I'll draw ", "the rectangle first."],
                ("toolu_1", "create_sketch", SKETCH_ARGS),
                "tool_use",
            ),
            "paced": True,
        },
        {
            "events": claude(
                ["Now the ", "extrude."], ("toolu_2", "extrude", EXTRUDE_ARGS), "tool_use"
            ),
            "paced": True,
        },
        {"events": claude(["Done: a 40 x 30 x 10 ", "mm box."]), "paced": True},
    ]
    s["before"] = len(s["requests"])
    ask("make a 40 x 30 x 10 box")


ask_for_a_box.done = lambda: "Done: a 40 x 30 x 10 mm box." in transcript() and not panel().busy()
ask_for_a_box.done_what = "the AI's answer shown and the chat done"
ask_for_a_box.timeout_s = 120


def box_built():
    p = panel()
    text = transcript()
    h.check("40 x 30 x 10 = 12000 mm3", abs((body_volume() or 0) - 12000) < 1e-6, body_volume())
    doc = App.ActiveDocument
    names = doc.UndoNames[:2] if doc else []
    h.check("one Undo step each", names == ["AI: Extrude 10 mm", "AI: Sketch on XY"], names)
    order = [
        text.find("AI: I'll draw the rectangle first."),
        text.find("Tool: create_sketch"),
        text.find("AI: Now the extrude."),
        text.find("Tool: extrude"),
        text.find("AI: Done: a 40 x 30 x 10 mm box."),
    ]
    h.check(
        "the words before each call, then the call, in order",
        all(i >= 0 for i in order) and order == sorted(order),
        (order, text[-900:]),
    )
    h.check("... each said once", text.count("Now the extrude.") == 1, text[-900:])
    h.check("Send is ready again", p.send_button.isEnabled() and not p.stop_button.isEnabled())
    asked = [body for _path, body in s["requests"][s["before"] :]]
    h.check(
        "three requests, each for a stream",
        len(asked) == 3 and all(b.get("stream") for b in asked),
        len(asked),
    )
    if len(asked) == 3:
        messages = asked[1]["messages"]
        sent = [
            b
            for m in messages
            if m["role"] == "assistant" and isinstance(m["content"], list)
            for b in m["content"]
            if b.get("type") == "tool_use"
        ]
        h.check(
            "the call went back whole (its arguments put together from the pieces)",
            sent and sent[-1]["input"] == SKETCH_ARGS,
            sent[-1:],
        )
        results = [
            b
            for m in messages
            if m["role"] == "user" and isinstance(m["content"], list)
            for b in m["content"]
            if b.get("type") == "tool_result"
        ]
        h.check(
            "the model got Fission 180's answer back (the sketch's id)",
            results and "'Sketch1'" in json.dumps(results[-1]),
            results[-1:],
        )
    h.shot("box")


# -- Path 4 --------------------------------------------------------------------------------
def endless_answer():
    s["plans"] = [
        {
            "events": claude(["One, ", "two, ", "three, ", "four, ", "five..."]),
            "paced": True,
            "keep_open_after": 2 + 3,
        }
    ]
    ask("count slowly")


endless_answer.done = lambda: s["holding"].is_set() and "three," in transcript()
endless_answer.done_what = "the first words shown while the server keeps the answer open"
endless_answer.while_busy = True  # the answer never ends on its own


def press_stop():
    p = panel()
    h.check("Stop is offered while the answer arrives", p.stop_button.isEnabled() and p.busy())
    s["stop_pressed"] = time.monotonic()
    wi.click(p.stop_button)


press_stop.done = lambda: not panel().busy() and panel().send_button.isEnabled()
press_stop.done_what = "the chat stopped and Send back"
press_stop.while_busy = True  # Stop is pressed while the answer arrives


def stopped():
    p = panel()
    took = time.monotonic() - s["stop_pressed"]
    text = transcript()
    h.check(
        "Stop ended the answer without waiting for the server (%.2f s)" % took,
        took < 5.0 * h.SLOWDOWN,
        took,
    )
    h.check("... says so", "Stopping" in text, text[-300:])
    h.check("... the words already shown stay", "AI: One, two, three," in text, text[-300:])
    h.check("... and Send is back", p.send_button.isEnabled() and not p.stop_button.isEnabled())
    history = p.chat.history if p.chat is not None else []
    h.check(
        "the conversation keeps what was shown",
        history and history[-1] == {"role": "assistant", "text": "One, two, three,"},
        history[-1:],
    )
    s["end"].set()  # (the server's held answer ends)


# -- Path 5 --------------------------------------------------------------------------------
def dropped_answer():
    s["plans"] = [
        {
            "events": claude(["Half of ", "an answer ", "and then"]),
            "paced": True,
            "drop_after": 2 + 2,
        }
    ]
    ask("tell me more")


dropped_answer.done = lambda: not panel().busy() and panel().send_button.isEnabled()
dropped_answer.done_what = "the chat done after the connection dropped"
dropped_answer.while_busy = True  # the answer arrives during this step


def dropped():
    text = transcript()
    h.check("the words that came are shown", "AI: Half of an answer" in text, text[-400:])
    h.check(
        "a plain message says the connection was lost",
        "The connection to Claude (Anthropic) was lost before the answer was complete" in text,
        text[-400:],
    )
    h.check("no pop-up", not h.popups(), h.popups())


# -- Path 6 --------------------------------------------------------------------------------
def choose_local():
    p = panel()
    pick(p.provider, "openai_compat")
    h.check("Local or other needs no key", not p.key.isVisible() and p.address.isVisible())
    vi.type_into(p.address, s["base"] + "/v1")
    wi.click(p.models_button)


choose_local.done = lambda: panel() is not None and panel().model.count() > 0
choose_local.done_what = "the model list filled from the server"


def ask_local():
    s["plans"] = [
        {
            "events": local(
                ["Let me ", "look at ", "the design."], ("call_l1", "get_design", ["{", "}"])
            ),
            "paced": True,
        },
        {"events": local(["It has ", "one body: ", "the box."]), "paced": True},
    ]
    s["before"] = len(s["requests"])
    ask("what is in the design?")


ask_local.done = lambda: "one body: the box." in transcript() and not panel().busy()
ask_local.done_what = "the local model's answer shown and the chat done"
ask_local.timeout_s = 120


def local_answered():
    text = transcript()
    asked = s["requests"][s["before"] :]
    h.check(
        "the local server was asked for streams",
        len(asked) == 2
        and all(path.endswith("/chat/completions") and body.get("stream") for path, body in asked),
        [p for p, _b in asked],
    )
    h.check(
        "its words are shown",
        "AI: Let me look at the design." in text and "AI: It has one body: the box." in text,
        text[-500:],
    )
    h.check("its tool call ran", "Tool: get_design" in text, text[-500:])
    h.check("the newest lines are in view (the conversation followed them)", *newest_in_view())
    if len(asked) == 2:
        tool_messages = [m for m in asked[1][1].get("messages", []) if m.get("role") == "tool"]
        h.check(
            "it got the tool's answer back",
            any("Body" in str(m.get("content")) for m in tool_messages),
            tool_messages[-1:],
        )
    h.shot("local")


def tidy():
    from fission180.ai import providers

    providers.PROVIDERS["anthropic"]["base_url"] = s["claude_url"]
    s["release"].set()
    s["end"].set()
    s["watch"].stop()
    s["server"].shutdown()
    h.check("no pop-up left", not h.popups(), h.popups())


h.run(
    "ai_chat_stream",
    [
        setup,
        choose_claude,
        ask_long,
        words_so_far,
        whole_answer,
        ask_for_a_box,
        box_built,
        endless_answer,
        press_stop,
        stopped,
        dropped_answer,
        dropped,
        choose_local,
        ask_local,
        local_answered,
        tidy,
    ],
    paced_by="state",
)
