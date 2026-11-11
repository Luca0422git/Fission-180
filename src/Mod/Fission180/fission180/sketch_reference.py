# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's "Auto project edges on reference" (Preferences > General > Design; wave 7,
sketch-c).

Fusion: with the preference on, snapping a sketch point to an edge or corner of the model,
constraining to it or dimensioning to it projects that edge or corner into the sketch by
itself (purple), from the same body, another body or another component; with it off nothing
outside the sketch can be snapped to (Autodesk forum, "Can no longer snap to geometry when
drawing a sketch": the answer is this preference).

Until wave 7 only FreeCAD's Project (P) brought model geometry in (sketch-b's Sketch
Dimension projected an edge of the same body under its click; nothing reached another
component). project_under() is the one place that does it now, for
- the click of a drawing tool, Fission 180's own (sketch_draw.DrawTool) and FreeCAD's
  (sketch_infer): the point then snaps onto the projected curve like onto any sketch curve;
- the picks of the constraint tools and of Sketch Dimension (they are DrawTools).

An edge or corner of the sketch's own body is a plain FreeCAD external reference; one of
another body or component goes through components' sketch_external.project_across (a
hidden reference in the sketch's body). One undo step "Project" before the tool's own.

The default: on. Fusion's own default is not documented by Autodesk; a forum moderator
(2019) "suspected the last update changed that setting to default to off". Fission 180
keeps it on because the book's steps snap and dimension to model edges, and Sketch
Dimension did so already (parity/sketch.md, "Wave 7, sketch-c").

Never lets an exception out (warn() and carry on).
"""

import FreeCAD as App

from . import log, warn

PARAM = ("User parameter:BaseApp/Preferences/Mod/Fission180/SketchInference", "ProjectOnReference")


def enabled():
    """Preferences > Design > "Auto project edges on reference"."""
    try:
        return App.ParamGet(PARAM[0]).GetBool(PARAM[1], True)
    except Exception:
        return True


def element_under(session, pos):
    """(object, "EdgeN" / "VertexN") of the model under widget pixel `pos`, or None: an
    edge or a corner that is not sketch geometry (a face is nothing to snap to)."""
    from . import sketch_project_across

    try:
        point = pos.toPoint() if hasattr(pos, "toPoint") else pos
        found = sketch_project_across.element_at(session.view, session.gl, point)
    except Exception:
        return None
    if found is None:
        return None
    obj, sub = found
    if obj is None or obj is session.sketch or not sub.startswith(("Edge", "Vertex")):
        return None
    if getattr(obj, "TypeId", "") == "Sketcher::SketchObject":
        return None  # another sketch's curve: Project (P) takes those
    return obj, sub


def project_under(session, pos, title="Sketch"):
    """Project the model edge or corner under widget pixel `pos` into the open sketch.
    Returns how many curves came in (0: nothing there, already projected, switched off, or
    it could not be done, which is said next to the mouse)."""
    if session is None or session.closed or not enabled():
        return 0
    found = element_under(session, pos)
    if found is None:
        return 0
    obj, sub = found
    sketch, doc = session.sketch, session.doc
    from . import sketch_auto_project, sketch_constrain_tools, sketch_external

    before = len(sketch.ExternalGeo)
    infer = session.infer
    if infer is not None:
        infer._applying = True  # (our own step: no shape of a drawing tool)
    try:
        doc.openTransaction("Project")
        try:
            if sketch_external.needs_reference(sketch, obj):
                sketch_external.project_across(sketch, obj, sub)
            elif sub.startswith("Edge"):
                missing, _have = sketch_auto_project.missing_edges(sketch, obj, sub)
                for name in missing:
                    sketch.addExternal(obj.Name, name, True, False)
            else:
                sketch.addExternal(obj.Name, sub)
            sketch.solve()
        except Exception:
            sketch_constrain_tools.end_step(doc, abort=True)
            raise
        added = len(sketch.ExternalGeo) - before
        sketch_constrain_tools.end_step(doc, abort=not added)
    except ValueError as exc:
        _tell("%s: %s" % (title, exc))
        return 0
    except Exception as exc:
        warn("%s: the %s under the pointer was not projected: %s" % (title, sub, exc))
        _tell(
            "%s: that %s of %s could not be projected into the sketch (%s). Try SKETCH > "
            "CREATE > Project (P)."
            % (
                title,
                "edge" if sub.startswith("Edge") else "corner",
                obj.Label,
                str(exc).splitlines()[0] if str(exc) else "error",
            )
        )
        return 0
    finally:
        if infer is not None:
            infer._applying = False
    if added:
        try:
            if infer is not None:
                infer.invalidate()
        except Exception:
            pass
        log(
            "%s: %s of %s projected into the sketch (Auto project edges on reference)"
            % (title, sub, obj.Label)
        )
    return added


def _tell(text):
    try:
        from . import commands

        commands.tell(text)
    except Exception:
        pass
