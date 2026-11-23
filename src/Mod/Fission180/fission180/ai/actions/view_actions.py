# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI actions for the 3D view: screenshot (capture_ui.py, through the host: only with the
Fission 180 window), turn and fit the view, Look At a face, the design's Named Views (kept in
the file the way the browser keeps them) and Show / Hide (bodies.set_shown).

The camera moves of these tools (and of render's window pictures, show_study_results) happen
at once, inside still_camera(): with FreeCAD's navigation animations on (its default) a
standard view turned the camera over half a second after the call, so a picture showed a
camera still on its way, and Fit All waited in an event loop of its own (alive.py). That
work is window work (progress.window_work): stuck there, the AI app is answered at once."""

import contextlib

from .. import bridge_core, progress
from ..executor import UserError, json_result
from . import action

META_VIEW = "Fission180.NamedView."  # (browser_ui.META_VIEW: the browser's Named Views)
ORIENTATIONS = {
    "iso": "viewIsometric",
    "front": "viewFront",
    "back": "viewRear",
    "top": "viewTop",
    "bottom": "viewBottom",
    "left": "viewLeft",
    "right": "viewRight",
}


def _view(ctx):
    doc = ctx.need_doc()
    view = ctx.host.view(doc)
    if view is None:
        raise UserError("This needs the 3D view of the Fission 180 window, and there is none.")
    return doc, view


@contextlib.contextmanager
def still_camera(view, what="turning the 3D view"):
    """Inside it the camera of `view` moves at once (FreeCAD's navigation animations off for
    that view, then as they were): a standard view is reached before the picture is taken,
    and Fit All does not animate (it waits for timers in an event loop of its own). It is the
    call's window work (`what`: progress.window_work)."""
    with progress.window_work(what):
        with _no_animation(view):
            yield view


@contextlib.contextmanager
def _no_animation(view):
    try:
        was = bool(view.isAnimationEnabled())
    except Exception:
        was = False
    if was:
        try:
            view.setAnimationEnabled(False)  # (also ends a camera move still going on)
        except Exception:
            was = False
    try:
        yield view
    finally:
        if was:
            try:
                view.setAnimationEnabled(True)
            except Exception:
                pass


@action("screenshot")
def screenshot(ctx, args):
    doc, view = _view(ctx)
    turn = ORIENTATIONS.get(args.get("view") or "")
    width, height = int(args.get("width", 1024)), int(args.get("height", 768))
    with still_camera(view, "turning the 3D view and taking its picture"):
        if turn:
            getattr(view, turn)()
            view.fitAll()
        data = ctx.host.screenshot(doc, width, height)
    return bridge_core.result(
        "A %d x %d picture of %s%s."
        % (width, height, doc.Label, (" (%s view)" % args["view"]) if args.get("view") else ""),
        data,
    )


@action("set_view")
def set_view(ctx, args):
    doc, view = _view(ctx)
    with still_camera(view):
        return _set_view(ctx, args, doc, view)


def _set_view(ctx, args, doc, view):
    done = []
    orientation = args.get("orientation")
    if orientation == "home":
        try:
            import FreeCADGui as Gui

            Gui.runCommand("Std_ViewHome")
        except Exception:
            view.viewIsometric()
        done.append("home view")
    elif orientation:
        getattr(view, ORIENTATIONS[orientation])()
        done.append("%s view" % orientation)
    if args.get("camera"):
        try:
            view.setCamera(args["camera"])
        except Exception as exc:
            raise UserError("That camera could not be set: %s" % exc)
        done.append("camera set")
    if args.get("projection"):
        view.setCameraType("Perspective" if args["projection"] == "perspective" else "Orthographic")
        done.append(args["projection"])
    if "look_at" in args:
        from ..ops import selectors

        body = ctx.host.find_body(doc)
        if body is None or body.Tip is None:
            raise UserError("There is no solid to look at.")
        names = selectors.select(body.Tip.Shape, args["look_at"], "faces")
        if len(names) != 1:
            raise UserError("look_at must pick exactly one face (it picked %d)." % len(names))
        face = body.Tip.Shape.getElement(names[0])
        u0, u1, v0, v1 = face.ParameterRange
        normal = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        normal = body.getGlobalPlacement().Rotation.multVec(normal)
        view.setViewDirection((-normal.x, -normal.y, -normal.z))
        done.append("looking at %s" % names[0])
    if args.get("fit", True):
        view.fitAll()
        done.append("fitted")
    return bridge_core.result("View: %s." % (", ".join(done) or "unchanged"))


def _named(doc):
    try:
        meta = doc.Meta
    except Exception:
        return {}
    return {k[len(META_VIEW) :]: v for k, v in meta.items() if k.startswith(META_VIEW)}


@action("get_view")
def get_view(ctx, args):
    doc, view = _view(ctx)
    return json_result(
        {
            "camera": view.getCamera(),
            "projection": view.getCameraType(),
            "named_views": sorted(_named(doc)),
        }
    )


@action("named_view")
def named_view(ctx, args):
    doc = ctx.need_doc()
    what = args["action"]
    name = args.get("name", "")
    views = _named(doc)
    if what == "list":
        return json_result({"named_views": sorted(views)})
    if what == "delete":
        if name not in views:
            raise UserError("There is no named view %r." % name)
        meta = dict(doc.Meta)
        meta.pop(META_VIEW + name, None)
        doc.Meta = meta
        return bridge_core.result("Deleted the named view %s." % name)
    doc, view = _view(ctx)
    if what == "save":
        meta = dict(doc.Meta)
        meta[META_VIEW + name] = view.getCamera()
        doc.Meta = meta
        ctx.host.after_change(doc)
        return bridge_core.result("Saved the named view %s." % name)
    if name not in views:
        raise UserError(
            "There is no named view %r (it has: %s)." % (name, ", ".join(sorted(views)) or "none")
        )
    view.setCamera(views[name])
    return bridge_core.result("Turned the view to %s." % name)


@action("show_hide")
def show_hide(ctx, args):
    from ... import bodies

    ctx.need_doc()
    found = [ctx.resolve(i) for i in args["targets"]]
    visible = bool(args["visible"])

    def work():
        for obj in found:
            bodies.set_shown(obj, visible)

    ctx.change(work)
    return bridge_core.result(
        "%s %s." % ("Showing" if visible else "Hid", ", ".join(o.Name for o in found))
    )
