# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the ai_drawing_* scenarios share (wave 8, ai-drawing): an AI app's side of the real
MCP server (fission180_mcp.py, started as ai_ui.server_command starts it) passing every call
to Fission 180's AI bridge on its own (GUI) thread, as Claude Desktop does; the answers read
as text, JSON and pictures; the checks a scenario makes on them. The Mcp class is the pattern
of ai_agent_e2e.py."""

import base64
import json
import os
import struct
import tempfile

import FreeCAD as App
from Fission180Tests.gui import harness as h

S = {"dir": tempfile.mkdtemp(prefix="fission180-ai-drawing-")}


class Mcp:
    """The AI app's side of MCP over stdio. A request waits for its answer while Qt keeps
    running, because Fission 180 answers on this same (GUI) thread."""

    def __init__(self, command, args, env):
        import subprocess
        import threading

        try:  # (a write to a server that died must fail, not end FreeCAD: bridge.py)
            import signal

            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        except (AttributeError, ValueError, OSError):
            pass
        self.proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self.answers = {}
        self.next_id = 1
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
                self.answers[message.get("id")] = message
            except ValueError:
                pass

    def request(self, method, params=None, timeout=240.0):
        ident = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self.proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except OSError as exc:
            return {"error": {"code": -1, "message": "the server is gone: %s" % exc}}
        h.wait_for(
            lambda: ident in self.answers,
            "the AI connector's answer to %s" % method,
            timeout_s=timeout,
        )
        return self.answers.pop(ident, {"error": {"code": -1, "message": "no answer"}})

    def notify(self, method):
        self.proc.stdin.write((json.dumps({"jsonrpc": "2.0", "method": method}) + "\n").encode())
        self.proc.stdin.flush()

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(10)
        except Exception:
            self.proc.kill()


def start():
    """AI control on, the MCP server started and initialized; it offers the drawing tools."""
    from fission180 import ai_ui, preferences_ui
    from fission180.ai import bridge

    bridge.ASK = lambda title, text: True  # (ai_bridge clicks Allow for real)
    preferences_ui.save({"allow_ai": True})
    h.check("AI control is on", bridge.running())
    command, args = ai_ui.server_command()
    S["mcp"] = Mcp(command, args, ai_ui.server_env())
    init = S["mcp"].request(
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "scenario", "version": "1"},
        },
    )
    h.check("the MCP server answers initialize", "result" in init, init)
    S["mcp"].notify("notifications/initialized")
    tools = S["mcp"].request("tools/list").get("result", {}).get("tools", [])
    names = {t["name"] for t in tools}
    wanted = {
        "create_drawing",
        "add_drawing_view",
        "edit_drawing_view",
        "modify_drawing",
        "edit_title_block",
        "drawing_sheet",
        "add_drawing_dimension",
        "edit_drawing_dimension",
        "add_drawing_annotation",
        "add_drawing_geometry",
        "add_drawing_symbol",
        "edit_balloons",
        "get_drawing",
        "export_drawing",
    }
    h.check("tools/list offers every drawing tool", wanted <= names, sorted(wanted - names))


def stop():
    from fission180 import preferences_ui
    from fission180.ai import bridge

    S["mcp"].close()
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


def call(tool, args):
    """One tool call through MCP: {"text", "is_error", "png"}."""
    answer = S["mcp"].request("tools/call", {"name": tool, "arguments": args})
    if "error" in answer:
        return {"text": answer["error"]["message"], "is_error": True, "png": b""}
    result = answer["result"]
    text = " ".join(c.get("text", "") for c in result.get("content", []) if c["type"] == "text")
    images = [c for c in result.get("content", []) if c["type"] == "image"]
    png = base64.b64decode(images[0]["data"]) if images else b""
    S["last"] = {"tool": tool, "text": text}
    return {"text": text, "is_error": bool(result.get("isError")), "png": png}


def ok(label, answer, extra=True, detail=None):
    h.check(label, not answer["is_error"] and bool(extra), detail or answer["text"][:600])


def refused(label, answer, *words):
    h.check(
        label,
        answer["is_error"] and all(w in answer["text"] for w in words),
        answer["text"][:600],
    )


def data(answer):
    """The JSON of an answer (after its first line, when there is one)."""
    text = answer["text"]
    try:
        return json.loads(text[text.index("{") :])
    except ValueError:
        return {}


def drawing_json(ident=None):
    args = {"drawing": ident} if ident else {}
    got = data(call("get_drawing", args))
    return got.get("drawings", [{}])[0] if got.get("drawings") else {}


def png_size(png):
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", png[16:24])


def path(name):
    return os.path.join(S["dir"], name)


def ai_steps_only(doc, since=0):
    """Every undo step of the design after the first `since` is the AI's ("AI: ...")."""
    names = list(doc.UndoNames)[: max(0, len(doc.UndoNames) - since)]
    return [n for n in names if not n.startswith("AI:")]


def open_drawing(page_name="Drawing"):
    """The drawing in its tab for the screenshot (as a person opens it from the browser)."""
    from fission180 import drawing_ui

    page = App.ActiveDocument.getObject(page_name)
    drawing_ui.open_drawing(page)
    h.wait_for(lambda: drawing_ui.active_page() is not None, "the drawing's tab is open")
