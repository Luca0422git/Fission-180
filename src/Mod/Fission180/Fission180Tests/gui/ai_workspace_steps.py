# SPDX-License-Identifier: LGPL-2.1-or-later
"""The steps the ai_workspace_* scenarios share (wave 8, builder ai-workspaces): an AI app's
side of MCP (the real MCP server fission180_mcp.py started as an AI app starts it, every call
passed to Fission 180's AI bridge on the window's thread, as in ai_agent_e2e), AI control
switched on and off, and the call helpers that read an answer's JSON and check it.

    from Fission180Tests.gui import ai_workspace_steps as ai

    h.run("ai_workspace_x", [ai.start, my_steps..., ai.stop], paced_by="state")
"""

import base64
import json

from Fission180Tests.gui import harness as h

S = {}  # the scenario's state: "mcp", the answers kept


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

    def request(self, method, params=None, timeout=300.0):
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
        # (the event loop runs meanwhile: Fission 180 answers on this same GUI thread)
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


def call(tool, args=None, timeout=300.0):
    """One tools/call through the MCP server: {"text", "is_error", "png", "data"} (data: the
    answer's JSON, when it has some)."""
    answer = S["mcp"].request("tools/call", {"name": tool, "arguments": args or {}}, timeout)
    if "error" in answer:
        return {"text": answer["error"]["message"], "is_error": True, "png": b"", "data": None}
    result = answer["result"]
    text = " ".join(c.get("text", "") for c in result.get("content", []) if c["type"] == "text")
    images = [c for c in result.get("content", []) if c["type"] == "image"]
    data = None
    start = text.find("{")
    if start >= 0:
        try:
            data = json.loads(text[start:])
        except ValueError:
            data = None
    return {
        "text": text,
        "is_error": bool(result.get("isError")),
        "png": base64.b64decode(images[0]["data"]) if images else b"",
        "data": data,
    }


def ok(tool, args=None, words=(), timeout=300.0):
    """A call that must work (checked, with its words); returns the answer."""
    answer = call(tool, args, timeout)
    h.check(
        "%s works" % tool,
        not answer["is_error"] and all(w in answer["text"] for w in words),
        answer["text"][:700],
    )
    return answer


def refused(tool, args, words=()):
    """A call that must be refused with these words."""
    answer = call(tool, args)
    h.check(
        "%s is refused in words (%s)" % (tool, ", ".join(words)),
        answer["is_error"] and all(w in answer["text"] for w in words),
        answer["text"][:500],
    )
    return answer


def near(got, want, rel=0.05, absolute=0.0):
    return got is not None and abs(got - want) <= max(rel * abs(want), absolute)


# -- the start and the end of a scenario -----------------------------------------------------------
def start():
    """AI control on (Preferences > AI), the session allowed, the real MCP server started."""
    from fission180 import ai_ui, preferences_ui
    from fission180.ai import bridge

    bridge.ASK = lambda title, text: True  # (ai_bridge clicks Allow for real; overwrite too)
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
    h.check("the MCP server started", "result" in init, init)
    S["mcp"].notify("notifications/initialized")
    names = [t["name"] for t in S["mcp"].request("tools/list").get("result", {}).get("tools", [])]
    S["tools"] = names
    h.check("tools/list has %d tools" % len(names), len(names) > 150, len(names))


def stop():
    """The server closed, AI control off again, nothing left open."""
    from fission180 import preferences_ui
    from fission180.ai import bridge

    S["mcp"].close()
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


def undo_names():
    import FreeCAD as App

    doc = App.ActiveDocument
    return [n for n in (doc.UndoNames if doc is not None else []) if n != "Add a Body"]
