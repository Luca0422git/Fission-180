# SPDX-License-Identifier: LGPL-2.1-or-later
"""Shared steps of the ai_design_* scenarios (wave 8, builder ai-design): an AI app's side of
MCP. The real MCP server (fission180_mcp.py) is started as an AI app starts it and passes
every call to Fission 180's AI bridge, which runs it on the window's own thread; a block of
calls of Fission180Tests/headless/design_tools.py goes through it with every check of the
headless run, here on the design in the window (the same checks: they read the model).

The Mcp class is ai_agent_e2e.py's (a request waits for its answer while Qt keeps running,
because Fission 180 answers on this same GUI thread)."""

import base64
import json
import re
import tempfile

import FreeCAD as App
from Fission180Tests.gui import harness as h

S = {}


class Mcp:
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

    def request(self, method, params=None, timeout=150.0):
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


class Run:
    """What design_tools' checks read (Fission180Tests/headless/runner.Run's helpers)."""

    def __init__(self, folder):
        self.folder = folder
        self.ids = {}
        self.called = set()

    def doc(self):
        return App.ActiveDocument

    def obj(self, name):
        doc = self.doc()
        ident = self.ids.get(name, name)
        found = doc.getObject(ident) if doc is not None else None
        if found is None and doc is not None:
            labels = [o for o in doc.Objects if o.Label == ident]
            found = labels[0] if labels else None
        return found

    def body_volume(self, name):
        from fission180 import bodies

        obj = self.obj(name)
        body = obj if bodies.is_body(obj) else bodies.body_of(obj)
        return body.Shape.Volume if body is not None and not body.Shape.isNull() else None


def call(tool, args):
    """One tools/call through MCP -> the answer as the executor gives it ({text, is_error,
    image_png_base64})."""
    answer = S["mcp"].request("tools/call", {"name": tool, "arguments": args})
    if "error" in answer:
        return {"text": answer["error"]["message"], "is_error": True, "image_png_base64": None}
    result = answer["result"]
    text = "\n".join(c.get("text", "") for c in result.get("content", []) if c["type"] == "text")
    images = [c["data"] for c in result.get("content", []) if c["type"] == "image"]
    return {
        "text": text,
        "is_error": bool(result.get("isError")),
        "image_png_base64": images[0] if images else None,
    }


def png(answer):
    data = answer.get("image_png_base64")
    return base64.b64decode(data) if data else b""


def start():
    """Path 1: AI control on (Preferences > AI), the MCP server started like an AI app does,
    its tools listed (the new ones among them)."""
    from fission180 import ai_ui, preferences_ui
    from fission180.ai import bridge
    from Fission180Tests.headless import design_tools

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
    h.check("the server answers initialize", "result" in init, init)
    S["mcp"].notify("notifications/initialized")
    listed = S["mcp"].request("tools/list").get("result", {}).get("tools", [])
    S["tools"] = {t["name"] for t in listed}
    S["folder"] = tempfile.mkdtemp(prefix="fission180-ai-design-")
    design_tools.prepare(S["folder"])
    S["run"] = Run(S["folder"])


def offers(*names):
    missing = [n for n in names if n not in S.get("tools", set())]
    h.check("tools/list offers %s" % ", ".join(names), not missing, missing)


def run_calls(calls, label):
    """The calls (design_tools' format) through MCP, each with its checks, each a check of
    the scenario ("<label> 012 as_built_joint")."""
    from Fission180Tests.headless import runner

    run = S["run"]
    for i, entry in enumerate(calls):
        tool = entry["tool"]
        args = runner._paths(runner._substitute(entry.get("args", {}), run.ids), run.folder)
        answer = call(tool, args)
        run.called.add(tool)
        problems = []
        expect = entry.get("expect", "ok")
        if expect == "ok" and answer["is_error"]:
            problems.append("failed: %s" % answer["text"][:600])
        if expect == "error" and not answer["is_error"]:
            problems.append("should have failed: %s" % answer["text"][:300])
        if expect in ("ok", "error"):
            for text in entry.get("contains", []):
                if text not in answer["text"]:
                    problems.append("the answer lacks %r: %s" % (text, answer["text"][:400]))
        made = runner._ids_from(answer)
        for key in ("save", "save_component", "save_drawing", "save_joint"):
            if key in entry and not answer["is_error"]:
                if made:
                    run.ids[entry[key]] = made
                else:
                    problems.append("no id in the answer: %s" % answer["text"][:200])
        check = entry.get("check")
        if check is not None and not problems and not answer["is_error"]:
            try:
                problem = check(answer, run)
            except Exception as exc:
                problem = "check raised %s" % exc
            if problem:
                problems.append(problem)
        h.check("%s %03d %s" % (label, i, tool), not problems, "; ".join(problems))
        S["last"] = answer
    return run


def undo_names():
    doc = App.ActiveDocument
    return [n for n in (doc.UndoNames if doc is not None else []) if n != "Add a Body"]


def ai_steps_only(label):
    """Every Undo step of the design is the AI's, named AI: ..."""
    names = undo_names()
    h.check(
        "%s: each change is one Undo step named AI: ..." % label,
        names and all(n.startswith("AI:") for n in names),
        names[:10],
    )


def stop():
    from fission180 import preferences_ui
    from fission180.ai import bridge

    S["mcp"].close()
    preferences_ui.save({"allow_ai": False})
    bridge.ASK = None
    h.check("AI control is off again", not bridge.running())
    h.check("no pop-up left", not h.popups(), h.popups())


def show_all(label):
    """The AI sets the view the way a person would look at the whole thing (iso, fit)."""
    answer = call("set_view", {"orientation": "iso", "fit": True})
    h.check("%s: set_view iso + fit" % label, not answer["is_error"], answer["text"][:200])


def ids_in(text):
    return re.findall(r"id '([^']+)'", text)
