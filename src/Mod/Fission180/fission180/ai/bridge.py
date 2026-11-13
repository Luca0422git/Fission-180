# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI bridge inside Fission 180 (brief home-cloud-ai.md section 4.3, milestone M3).

When Preferences > AI > "Allow AI apps to control Fission 180" is on (off by default), Fission 180
listens on 127.0.0.1 only, at a random port, and writes <user data>/Fission180/ai/bridge.json
with that port and a random key (bridge_core.py). The MCP server an AI app starts
(fission180_mcp.py) sends each tool call there.

A call arrives on the server's thread and waits; the work happens on Fission 180's own (GUI)
thread, where FreeCAD may be touched: a timer takes the calls one by one and hands each to
the executor (fission180/ai/executor.py, the same one the headless backend uses) with the GUI
host below. Every call that changes the design is one Undo step ("AI: Extrude 10 mm"), built
with the same code as the golden models and the dialogs (fission180/ai/ops, fission180/ai/actions).
The tools themselves are listed in the catalogue (fission180/ai/catalog). Safety:
  * the first call of a session asks the person in Fission 180: Allow / Deny;
  * while a Fission 180 dialog or a sketch is open, changing calls answer "Fission 180 is busy";
  * overwriting a file always asks the person; there is no "run any code" tool;
  * every call is listed in the AI activity panel (with Undo and Stop).
"""

import base64
import http.server
import json
import os
import queue
import tempfile
import threading
import time

import FreeCAD as App
import FreeCADGui as Gui

from .. import commands, log, warn
from ..compat import QtCore, QtWidgets
from . import bridge_core, catalog, executor, progress

OPTION = ("User parameter:BaseApp/Preferences/Mod/Fission180/AI", "AllowControl")
WAIT = 115.0  # seconds a call waits for Fission 180 (the MCP server waits 120)
ASK = None  # tests: function(title, text) -> True / False instead of the question
_state = {
    "server": None,
    "thread": None,
    "key": None,
    "file": None,
    "timer": None,
    "jobs": queue.Queue(),
    "consent": None,  # None: not asked this session; True / False: the person's answer
    "running": False,  # a call is being worked on (the questions open nested event loops)
    "current": None,  # (tool, time.time() it started, call_id) of the call being worked on
    "queued": {},  # call_id -> job while it waits (a /stop of a call not started yet drops it)
    "serial": 0,
    "activity": [],  # (time, tool, text, is_error)
    "last_used": None,
    "listeners": [],  # functions called after every call (the activity panel, Home)
}


# -- on / off ----------------------------------------------------------------------------
def allowed():
    path, name = OPTION
    return App.ParamGet(path).GetBool(name, False)


def set_allowed(on):
    path, name = OPTION
    App.ParamGet(path).SetBool(name, bool(on))
    apply()


def running():
    return _state["server"] is not None


def apply():
    """Start or stop the bridge as the option says (Preferences, start-up, Stop)."""
    try:
        if allowed():
            start()
        else:
            stop()
    except Exception as exc:
        warn("AI bridge: %s" % exc)


class _Handler(http.server.BaseHTTPRequestHandler):
    server_version = "Fission180"

    def log_message(self, *_args):
        pass  # (http.server prints every request to stderr; the activity panel lists them)

    def _send(self, status, answer):
        data = bridge_core.encode_result(answer)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            self._send(404, bridge_core.error_result("not found"))
        except Exception:
            pass

    def do_POST(self):
        try:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            status, reason = bridge_core.check_request(
                "POST",
                self.path,
                self.headers.get(bridge_core.KEY_HEADER),
                _state["key"],
                self.headers.get("Origin"),
                length,
            )
            if status != 200:
                self._send(status, bridge_core.error_result(reason))
                return
            path = self.path.split("?", 1)[0]
            body = self.rfile.read(length)
            if path == bridge_core.STATUS_PATH:
                self._send_json(200, _status())  # (this thread: never behind the call)
                return
            if path == bridge_core.STOP_PATH:
                try:
                    call_id, why = bridge_core.decode_stop(body)
                except bridge_core.BridgeError as exc:
                    self._send(400, bridge_core.error_result(str(exc)))
                    return
                self._send_json(200, _stop(call_id, why))
                return
            try:
                tool, args, call_id = bridge_core.decode_call(body)
            except bridge_core.BridgeError as exc:
                self._send(400, bridge_core.error_result(str(exc)))
                return
            current = _state["current"]
            if current is not None and time.time() - current[1] > bridge_core.BUSY_AFTER:
                # (one call at a time on the window's thread: a long one is not queued behind)
                live = progress.current() or {}
                doing = progress.doing_words(live.get("what"), live.get("done"), live.get("total"))
                self._send(
                    200,
                    bridge_core.error_result(
                        bridge_core.busy_text(tool, current[0], time.time() - current[1], doing)
                    ),
                )
                return
            with _LOCK:
                _state["serial"] += 1
                call_id = call_id or "bridge-%d" % _state["serial"]
            job = {
                "tool": tool,
                "args": args,
                "call_id": call_id,
                "done": threading.Event(),
                "answer": None,
                "state": "queued",  # -> running -> done, or -> dropped (nobody waits any more)
                "lock": threading.Lock(),
            }
            with _LOCK:
                _state["queued"][call_id] = job
            _state["jobs"].put(job)
            if not job["done"].wait(WAIT):
                with job["lock"]:
                    dropped = job["state"] == "queued"
                    if dropped:
                        job["state"] = "dropped"
                with _LOCK:
                    _state["queued"].pop(call_id, None)
                if dropped:  # (never started: it is not run later, when nobody waits for it)
                    current = _state["current"]  # (no log here: not the window's thread)
                    self._send(
                        200,
                        bridge_core.error_result(
                            bridge_core.dropped_text(
                                tool,
                                current[0] if current else "",
                                time.time() - current[1] if current else 0,
                            )
                        ),
                    )
                    return
                job["late"] = True
                text = (
                    "Fission 180 is still working on %s (or waiting for the person to answer a "
                    "question in Fission 180). Check Fission 180 before trying again." % tool
                )
                if catalog.is_read_only(tool):
                    # (its answer is lost: working on only keeps the window busy for nothing)
                    if progress.request_stop(
                        "nobody waits for its answer any more", call_id, only_read_only=True
                    ):
                        text += " It stops at its next safe point: nobody waits for it."
                else:  # (honest: it may still happen)
                    text += (
                        " The change may or may not be applied when it finishes: inspect the "
                        "design (get_design, get_timeline) before repeating it."
                    )
                self._send(200, bridge_core.error_result(text))
                return
            self._send(200, job["answer"])
        except Exception:
            pass  # (the connection went away: nothing to answer)

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


_LOCK = threading.Lock()


def _status():
    """The /status answer: what the call running now is doing (the bridge's own thread)."""
    live = progress.current()
    return bridge_core.status_answer(live, progress.line(live))


def _stop(call_id, why):
    """The AI app cancelled the call `call_id` (fission180_mcp.py: notifications/cancelled).
    Not started yet: it is not run. Running and read-only: it stops at its next safe point.
    Running and changing the design: it is left to finish (stopping it would only make the AI
    start it all again, and its result is there when the AI looks; the person can press Stop).
    The bridge's own thread."""
    with _LOCK:
        job = _state["queued"].pop(call_id, None)
    if job is not None:
        with job["lock"]:
            if job["state"] == "queued":
                job["state"] = "dropped"
                _answer(job, bridge_core.error_result("Not done: %s before it started." % why))
                return {"stopped": True, "running": False}
    live = progress.current()
    if live is None or live.get("call_id") != call_id:
        return {"stopped": False, "running": False}
    stopped = progress.request_stop(why, call_id, only_read_only=True)
    return {"stopped": bool(stopped), "running": True, "read_only": bool(live.get("read_only"))}


def _ignore_broken_pipes():
    """Linux / macOS: writing an answer to a connection the AI app already closed sends
    SIGPIPE, which ends a program that does not ignore it, and FreeCAD's embedded Python
    does not (ordinary Python does): Fission 180 was killed, unsaved work and all. Ignored, the
    write fails with an error the handler catches."""
    try:
        import signal

        if hasattr(signal, "SIGPIPE"):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    except (ValueError, OSError) as exc:  # (not the main thread)
        warn("AI bridge: %s" % exc)


def start():
    if running():
        return
    _ignore_broken_pipes()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    _state["key"] = bridge_core.make_key()
    _state["server"] = server
    _state["thread"] = threading.Thread(
        target=server.serve_forever, name="Fission180AIBridge", daemon=True
    )
    _state["thread"].start()
    _state["file"] = bridge_core.bridge_path(App.getUserAppDataDir())
    bridge_core.write_bridge_file(
        _state["file"], bridge_core.bridge_info(server.server_address[1], _state["key"])
    )
    if _state["timer"] is None:
        _state["timer"] = QtCore.QTimer()
        _state["timer"].setInterval(50)
        _state["timer"].timeout.connect(_pump)
    _state["timer"].start()
    log("AI bridge on (127.0.0.1, port %d)" % server.server_address[1])


def stop():
    if not running():
        return
    server = _state["server"]
    _state["server"] = None
    try:
        server.shutdown()
        server.server_close()
    except Exception as exc:
        warn("AI bridge: %s" % exc)
    bridge_core.remove_bridge_file(_state["file"], os.getpid())
    while True:  # calls still waiting: answered, not left hanging
        try:
            job = _state["jobs"].get_nowait()
        except queue.Empty:
            break
        _answer(job, bridge_core.error_result(bridge_core.NOT_RUNNING))
    _state["consent"] = None
    log("AI bridge off")


# -- the GUI thread -----------------------------------------------------------------------
def _answer(job, answer):
    job["answer"] = answer
    job["done"].set()


def _pump():
    """Takes the waiting calls one by one (on Fission 180's own thread)."""
    if _state["running"]:
        return  # (a question of this call is open: its own event loop calls the timer)
    while True:
        try:
            job = _state["jobs"].get_nowait()
        except queue.Empty:
            return
        lock = job.get("lock")
        if lock is None:
            break
        with lock:
            if job.get("state", "queued") == "queued":
                job["state"] = "running"
                break
        log("AI bridge: %s not run: the AI app stopped waiting for it" % job["tool"])
    with _LOCK:
        _state["queued"].pop(job.get("call_id"), None)
    _state["running"] = True
    _state["current"] = (job["tool"], time.time(), job.get("call_id"))
    try:
        answer = call(job["tool"], job["args"], call_id=job.get("call_id"))
    except BaseException as exc:  # (never one up into Qt's timer; executor.run answers a stop)
        warn("AI bridge: %s: %s" % (job["tool"], exc))
        answer = bridge_core.error_result("Fission 180 could not do %s: %s" % (job["tool"], exc))
    finally:
        _state["running"] = False
        _state["current"] = None
    job["state"] = "done"
    _answer(job, answer)


def ask(title, text):
    """A yes / no question to the person in Fission 180 (True = yes)."""
    if ASK is not None:
        return bool(ASK(title, text))
    box = QtWidgets.QMessageBox(Gui.getMainWindow())
    box.setObjectName("Fission180AIQuestion")
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton("Allow", QtWidgets.QMessageBox.AcceptRole)
    no = box.addButton("Deny", QtWidgets.QMessageBox.RejectRole)
    yes.setObjectName("Fission180AIAllow")
    no.setObjectName("Fission180AIDeny")
    box.setDefaultButton(no)
    box.exec_()
    return box.clickedButton() is yes


def _busy():
    """Why Fission 180 cannot change the design now, or ""."""
    try:
        if Gui.Control.activeDialog():
            return "Fission 180 is busy: a command dialog is open. Finish or cancel it first."
        gui_doc = Gui.ActiveDocument
        if gui_doc is not None and gui_doc.getInEdit() is not None:
            return "Fission 180 is busy: something is being edited (a sketch?). Finish it first."
        if QtWidgets.QApplication.activeModalWidget() is not None:
            return "Fission 180 is busy: a window is waiting for an answer. Close it first."
    except Exception:
        pass
    return ""


def call(tool, args, from_chat=False, call_id=None):
    """One tool call: a result dict (bridge_core.result). from_chat: from Fission 180's own chat
    panel, where the person is the one asking (no "Allow this AI app?" question). call_id: the
    AI app's id for it (a cancel names it). A call that comes while another one runs (from a
    question box's own loop) is refused: one call at a time."""
    if progress.working():
        live = progress.current() or {}
        return bridge_core.error_result(
            bridge_core.busy_text(
                tool,
                live.get("tool", "another call"),
                live.get("seconds", 0),
                progress.doing_words(live.get("what"), live.get("done"), live.get("total")),
            )
        )
    problems = catalog.validate(tool, args)
    if problems:
        return bridge_core.error_result("Not done: " + "; ".join(problems) + ".")
    if not from_chat and _state["consent"] is None:
        _state["consent"] = ask(
            "AI control",
            "An AI app wants to control Fission 180 (build, change and save designs). Every step "
            "it makes can be undone and is listed in the AI activity panel.\n\nAllow it for "
            "this session?",
        )
        log("AI bridge: the person %s AI control" % ("allowed" if _state["consent"] else "denied"))
    if not from_chat and not _state["consent"]:
        return _record(
            tool,
            bridge_core.error_result(
                "The person using Fission 180 did not allow AI control in this session."
            ),
        )
    entry = catalog.tool(tool)
    if entry["changes_design"] or entry.get("writes_files"):
        reason = _busy()
        if reason:
            return _record(tool, bridge_core.error_result(reason))
    answer = executor.run(tool, args, host(), call_id)
    return _record(tool, answer)


class GuiHost(executor.Host):
    """The executor's host inside the Fission 180 window: the 3D view's active body, the
    questions to the person, Fission 180's own saving (version history) and screenshots."""

    gui = True

    def find_body(self, doc):
        from .. import bodies

        if doc is App.ActiveDocument:
            return commands.find_body()
        return bodies.find_body(doc)

    def ensure_body(self, doc):
        if doc is not App.ActiveDocument:
            App.setActiveDocument(doc.Name)
        return commands.ensure_body()

    def set_active_body(self, body):
        from .. import components

        try:
            components.activate_body(body)
        except Exception as exc:
            warn("AI bridge: %s" % exc)

    def confirm_overwrite(self, path):
        return _confirm_overwrite(path)

    def refuse_overwrite_text(self, path):
        if isinstance(path, (list, tuple)):
            path = ", ".join(path)
        return "The person did not allow replacing %s." % path

    def save(self, doc, path=None):
        from .. import versions_ui

        if not path:
            versions_ui._save_version(doc.Name, "Saved by an AI app")
            return doc.FileName
        versions_ui._first_save(doc.Name, path, save_as=bool(doc.FileName))
        return path

    def open_design(self, path):
        from .. import versions_ui

        doc = versions_ui.open_design(path)
        if doc is None:
            raise executor.UserError("The design %s could not be opened." % path)
        return doc

    def new_document(self, name):
        doc = App.newDocument(executor._doc_name(name))
        doc.Label = name
        return doc

    def ready(self, doc):
        pass  # (documents of the window have undo on)

    def show_document(self, doc):
        App.setActiveDocument(doc.Name)
        try:
            gdoc = Gui.getDocument(doc.Name)
            area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
            for window in area.subWindowList() if area is not None else []:
                if window.windowTitle().split(" : ")[0].rstrip("*") in (doc.Label, doc.Name):
                    area.setActiveSubWindow(window)
                    break
            if gdoc is not None:
                Gui.ActiveDocument = gdoc
        except Exception as exc:
            warn("AI bridge: %s" % exc)

    def busy(self):
        return _busy()

    def ask(self, title, text):
        return ask(title, text)

    def view(self, doc):
        gui_doc = Gui.getDocument(doc.Name) if doc is not None else None
        view = gui_doc.ActiveView if gui_doc is not None else None
        return view if view is not None and hasattr(view, "saveImage") else None

    def selection(self, doc):
        from . import geometry_facts

        rows = []
        for sel in Gui.Selection.getSelectionEx(doc.Name):
            obj = sel.Object
            row = {"object": obj.Name, "label": obj.Label, "elements": []}
            subs = [n.split(".")[-1] for n in sel.SubElementNames if n]
            row["elements"] = subs
            try:
                shape = obj.Shape
                for element, prefix in (("faces", "Face"), ("edges", "Edge")):
                    wanted = {n for n in subs if n.startswith(prefix)}
                    if wanted:
                        refs = geometry_facts.stable_refs(shape, element, wanted)
                        from .. import bodies

                        body = obj if bodies.is_body(obj) else bodies.body_of(obj)
                        if body is not None:
                            geometry_facts.tie_to_body(refs, body.Name)
                        row.setdefault("refs", {}).update(refs)
            except Exception:
                pass
            rows.append(row)
        return rows

    def push_highlight(self, doc, marked):
        """Before render takes a picture from the window: the person's selection taken off
        (saveImage draws a selected body tinted, and never draws selected faces or edges,
        so selecting them marked nothing) and the marked faces and edges added to the 3D
        view in orange (_highlight_node). pop_highlight puts everything back."""
        saved = {"selection": [], "node": None, "root": None, "drawn": None}
        try:
            for sel in Gui.Selection.getSelectionEx(doc.Name, 0):
                names = sel.SubElementNames or ("",)
                saved["selection"] += [(sel.Object.Name, n) for n in names]
            Gui.Selection.clearSelection(doc.Name)
            Gui.Selection.clearPreselection()
        except Exception as exc:
            warn("AI render: %s" % exc)
        if marked and marked.get("source") is not None:
            saved["drawn"] = False
            try:
                view = self.view(doc)
                node = _highlight_node(doc, marked)
                if view is not None and node is not None:
                    root = view.getSceneGraph()
                    root.addChild(node)
                    saved.update(node=node, root=root, drawn=True)
            except Exception as exc:
                warn("AI render: the highlight could not be drawn: %s" % exc)
        return saved

    def pop_highlight(self, doc, saved):
        if not saved:
            return None
        try:
            if saved["node"] is not None:
                saved["root"].removeChild(saved["node"])
        except Exception as exc:
            warn("AI render: %s" % exc)
        try:
            Gui.Selection.clearSelection(doc.Name)
            for name, sub in saved["selection"]:
                Gui.Selection.addSelection(doc.Name, name, sub)
        except Exception as exc:
            warn("AI render: %s" % exc)
        return saved["drawn"]

    def screenshot(self, doc, width, height):
        from .. import capture_ui

        handle, path = tempfile.mkstemp(suffix=".png", prefix="fission180-ai-")
        os.close(handle)
        try:
            capture_ui.save(path, width, height)
            with open(path, "rb") as stream:
                return base64.b64encode(stream.read()).decode("ascii")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


HIGHLIGHT_RGB = (1.0, 136 / 255.0, 0.0)  # render_core.HIGHLIGHT: the same orange


def _highlight_node(doc, marked):
    """A Coin node drawing the marked faces and edges of marked["source"] in orange where
    that solid is in the design. The faces are tessellated on the very shape the window
    shows, with a deflection no finer than its own, so OpenCASCADE hands back the window's
    triangles and the orange lies exactly on them (pulled forward a little: the window's
    faces are pushed back by their own polygon offset). An earlier step's solid, not shown,
    is drawn alone and its edges on top."""
    from pivy import coin

    from .. import bodies

    source = marked["source"]
    shape = source.Shape
    parent = source.getParentGeoFeatureGroup()
    place = parent.getGlobalPlacement() if parent is not None else App.Placement()
    shown = any(
        b is source or getattr(b, "Tip", None) is source
        for b in bodies.list_bodies(doc)
        if bodies.is_shown(b)
    )
    try:
        deviation = float(source.ViewObject.Deviation)
    except Exception:
        deviation = 0.5
    box = shape.BoundBox
    deflection = max((box.XLength + box.YLength + box.ZLength) / 300.0 * deviation * 1.5, 1e-3)
    root = coin.SoSeparator()
    root.setName("Fission180AIHighlight")
    points, indexes = [], []
    for name in sorted(marked["faces"]):
        verts, tris = shape.getElement(name).tessellate(deflection)
        start = len(points)
        points += [tuple(place.multVec(v)) for v in verts]
        for a, b, c in tris:
            indexes += [a + start, b + start, c + start, -1]
    if indexes:
        faces = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*HIGHLIGHT_RGB)
        material.emissiveColor.setValue(*[0.35 * c for c in HIGHLIGHT_RGB])
        hints = coin.SoShapeHints()
        hints.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING  # (lit on both sides)
        offset = coin.SoPolygonOffset()
        offset.factor.setValue(-1.0)
        offset.units.setValue(-1.0)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(points), points)
        faceset = coin.SoIndexedFaceSet()
        faceset.coordIndex.setValues(0, len(indexes), indexes)
        for child in (material, hints, offset, coords, faceset):
            faces.addChild(child)
        root.addChild(faces)
    lines, counts = [], []
    for name in sorted(marked["edges"]):
        verts = shape.getElement(name).discretize(Deflection=deflection / 1.5)
        lines += [tuple(place.multVec(v)) for v in verts]
        counts.append(len(verts))
    if counts:
        edges = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*HIGHLIGHT_RGB)
        model = coin.SoLightModel()
        model.model = coin.SoLightModel.BASE_COLOR
        style = coin.SoDrawStyle()
        style.lineWidth.setValue(4.0)
        for child in (material, model, style):
            edges.addChild(child)
        if not shown:
            depth = coin.SoDepthBuffer()
            depth.test.setValue(False)
            edges.addChild(depth)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(lines), lines)
        lineset = coin.SoLineSet()
        lineset.numVertices.setValues(0, len(counts), counts)
        edges.addChild(coords)
        edges.addChild(lineset)
        root.addChild(edges)
    return root if (indexes or counts) else None


_HOST = []


def host():
    if not _HOST:
        _HOST.append(GuiHost())
    return _HOST[0]


def _record(tool, answer):
    stamp = time.time()
    _state["activity"].append((stamp, tool, answer["text"], answer["is_error"]))
    del _state["activity"][:-200]
    _state["last_used"] = stamp
    for listener in list(_state["listeners"]):
        try:
            listener()
        except Exception as exc:
            warn("AI bridge: %s" % exc)
    return answer


def activity():
    return list(_state["activity"])


def last_used():
    return _state["last_used"]


def add_listener(fn):
    if fn not in _state["listeners"]:
        _state["listeners"].append(fn)


# -- questions -------------------------------------------------------------------------
def _confirm_overwrite(path):
    if isinstance(path, (list, tuple)):  # (One File Per Body: one question for them all)
        return ask(
            "AI control",
            "The AI app wants to write over these files\n%s\n\nAllow it to replace them?"
            % "\n".join(path),
        )
    return ask(
        "AI control",
        "The AI app wants to write over the file\n%s\n\nAllow it to replace that file?" % path,
    )
