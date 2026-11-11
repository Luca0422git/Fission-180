# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch environment on top of FreeCAD's Sketcher.

While Fission 180 is on, every sketch that is opened (FreeCAD "edit mode") behaves like
a Fusion sketch:

- Esc stops the drawing tool; a second Esc clears the selection. Esc never closes
  the sketch (only Finish Sketch does).
- No pop-ups: a new dimension gets a small box next to it where you type the value
  (Enter keeps it, Esc keeps the measured value). Double-clicking a dimension opens
  the same box instead of FreeCAD's "Insert length" window.
- Closed regions (profiles) are shaded light blue while you draw, also where curves
  cross (sketch_regions.py). A click inside one (not on a curve) picks it for E / Q,
  Ctrl or Shift + click adds more (sketch_areas.py). After Finish Sketch the areas stay
  clickable: FreeCAD's sketch areas (MakeInternals) are on for every sketch; with no
  command running they come before the face they are drawn on, and commands that cannot
  use them click through them (sketch_area_pick.py).
- The SKETCH PALETTE sits at the top of the sketch panel (sketch_palette.py): Look At,
  grid, snap, slice, show profiles/points/dimensions/constraints/projected geometry.
- Sketch curves use Fusion's colours on the dark background (blue = not fully
  constrained, white = fully constrained, orange = construction, purple = projected).
- The circumscribed polygon previews and builds with the mouse on the middle of an
  edge (FreeCAD's polygon tool only knows corners).

Everything here is undone by disable(): parameters get their old values back.

Rules followed (docs/fission180/dev/feature-guide.md): FreeCAD's Python event and
observer hooks only schedule work with QTimer.singleShot; Coin nodes are only read and
changed from Qt timers (never from pivy callbacks).
"""

import math
import time

import FreeCAD as App
import FreeCADGui as Gui

from . import log, theme, warn
from .compat import QtCore, QtGui, QtWidgets

SKETCHER = "User parameter:BaseApp/Preferences/Mod/Sketcher"
SKETCHER_GENERAL = SKETCHER + "/General"
SNAP = SKETCHER + "/Snap"
VIEW = "User parameter:BaseApp/Preferences/View"
PALETTE_PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/SketchPalette"
NOTIFICATIONS = "User parameter:BaseApp/Preferences/NotificationArea"


def _rgba(hex_color):
    value = int(hex_color.lstrip("#"), 16)
    return (value << 8) | 0xFF


# Fusion's sketch colours, made for Fission 180's dark 3D view. Fusion: blue until fully
# defined, then black (white on a dark background); fixed geometry green; construction
# orange; projected purple. The exact shades are Fission 180's own (Fusion's are not
# published): checked only by eye so far.
BLUE = "#5cb3ff"  # curves that can still move (under-constrained)
WHITE = "#f0f0f0"  # fully constrained curves, dimension text
GREEN = "#4ad66d"  # fixed curves and points (Fix/Unfix); FreeCAD has no colour for them
ORANGE = "#f5a142"  # construction
PURPLE = "#c084fc"  # projected / included geometry
GLYPH = "#9fe0a8"  # constraint symbols
DRIVEN = "#9fb4cc"  # driven (reference) dimensions
# Selected and hovered curves, pinned here so they stay apart from the under-constrained
# blue whatever FreeCAD theme the user had. SELECT is the value FreeCAD's own theme packs
# write (Light and Dark alike), HOVER its Dark pack's (the Light pack hovers in green,
# which would read as "fixed"). Fusion's are unknown (a guess). Both are FreeCAD-wide:
# the part's selection and hover colours follow them too.
SELECT = "#3b5bdb"  # selected curves and points
HOVER = "#246eab"  # under the pointer

# (group, kind, name, value) set while Fission 180 is on; old values come back in disable().
PARAMS = [
    # Esc never leaves the sketch (Fusion: only Finish Sketch does)
    (SKETCHER, "Bool", "LeaveSketchWithEscape", False),
    # no modal "Insert length" window after a dimension: Fission 180's in-place box instead
    (SKETCHER, "Bool", "ShowDialogOnDistanceConstraint", False),
    # Fusion has no constraint/element lists: keep FreeCAD's folded under the palette
    (SKETCHER, "Bool", "ExpandedConstraintsWidget", False),
    (SKETCHER, "Bool", "ExpandedElementsWidget", False),
    # projected edges form profiles, like Fusion's (Include 3D Geometry: reference only)
    (SKETCHER_GENERAL, "Bool", "AlwaysExtGeoReference", False),
    # Fusion's grid: quiet solid lines, every 10th a little brighter
    (SKETCHER_GENERAL, "Int", "GridLinePattern", 0xFFFF),
    (SKETCHER_GENERAL, "Int", "GridDivLinePattern", 0xFFFF),
    (SKETCHER_GENERAL, "Int", "GridDivLineWidth", 1),
    (SKETCHER_GENERAL, "Unsigned", "GridLineColor", _rgba("#33383f")),
    (SKETCHER_GENERAL, "Unsigned", "GridDivLineColor", _rgba("#4b525d")),
    (VIEW, "Unsigned", "EditedEdgeColor", _rgba(BLUE)),
    (VIEW, "Unsigned", "CreateLineColor", _rgba(BLUE)),
    (VIEW, "Unsigned", "FullyConstraintElementColor", _rgba(WHITE)),
    (VIEW, "Unsigned", "FullyConstrainedColor", _rgba(WHITE)),
    (VIEW, "Unsigned", "ConstructionColor", _rgba(ORANGE)),
    (VIEW, "Unsigned", "FullyConstraintConstructionElementColor", _rgba(ORANGE)),
    (VIEW, "Unsigned", "ExternalColor", _rgba(PURPLE)),
    (VIEW, "Unsigned", "ExternalDefiningColor", _rgba(PURPLE)),
    (VIEW, "Unsigned", "ConstrainedDimColor", _rgba(WHITE)),
    # constraint glyphs: FreeCAD draws them red, which reads as an error; Fusion's are
    # quiet light symbols. Driven (reference) dimensions: FreeCAD's dark blue is
    # unreadable on the dark background.
    (VIEW, "Unsigned", "ConstrainedIcoColor", _rgba(GLYPH)),
    (VIEW, "Unsigned", "NonDrivingConstrDimColor", _rgba(DRIVEN)),
    (VIEW, "Unsigned", "CursorTextColor", _rgba(WHITE)),
    (VIEW, "Unsigned", "CursorCrosshairColor", _rgba(WHITE)),
    # a selected or hovered curve must be told apart from an under-constrained one
    (VIEW, "Unsigned", "SelectionColor", _rgba(SELECT)),
    (VIEW, "Unsigned", "HighlightColor", _rgba(HOVER)),
    # FreeCAD's pop-up balloons at the bottom of the window ("Autoconstraints cause
    # redundancy. Removing them" when a line from the origin along an axis snaps twice,
    # "Sub shape not found: Sketch.?InternalFace1"...): FreeCAD's wording, nothing a
    # Fusion user can act on. Fission 180 says what matters next to the mouse
    # (commands.tell) or in its dialogs; the messages stay in FreeCAD's notification
    # list and the Report view. No balloon is ever open (MaxOpenNotifications 0). The
    # "non-intrusive" setting must stay on: off, FreeCAD shows its user warnings ("Wrong
    # selection"...) as blocking message boxes instead.
    (NOTIFICATIONS, "Bool", "NonIntrusiveNotificationsEnabled", True),
    # FreeCAD's modal "Sketcher Constraint Substitution" box (Tangent on curves whose ends
    # are joined) never shows: Fusion says nothing there (sf/book-sketch-b; Fission 180's
    # own Tangent does the same swap without a word, sketch_constrain_tools.py)
    (SKETCHER_GENERAL, "Bool", "NotifyConstraintSubstitutions", False),
    (NOTIFICATIONS, "Int", "MaxOpenNotifications", 0),
    # Fusion: every closed area of a sketch is a profile you can click, also after Finish
    # Sketch and before any command (then E or Q uses it). FreeCAD can do that when a
    # sketch makes its "internal faces" (MakeInternals): new sketches get it from this
    # preference, older ones when they are opened (sketch_areas.ensure_areas).
    (SKETCHER, "Bool", "MakeInternals", True),
    # ... and shades those areas in this colour (RRGGBBAA, AA = opacity): the light blue
    # of Fission 180's profiles (ProfileShading.FILL), strong enough to see on the dark
    # background. FreeCAD's own is a dim 0x54ABFF40.
    (SKETCHER_GENERAL, "Unsigned", "SketchFaceColor", 0x73C4FF80),
    # A spline is drawn as a plain curve, as in Fusion: FreeCAD's B-spline information
    # (curvature comb, degree, knot multiplicity and pole weight labels) buried an
    # exploded text under green hair and numbers. The control polygon stays (Fusion
    # shows it for control-point splines).
    (SKETCHER_GENERAL, "Bool", "BSplineCombVisible", False),
    (SKETCHER_GENERAL, "Bool", "BSplineDegreeVisible", False),
    (SKETCHER_GENERAL, "Bool", "BSplineKnotMultiplicityVisible", False),
    (SKETCHER_GENERAL, "Bool", "BSplinePoleWeightVisible", False),
    # FreeCAD draws the control polygon of every spline, a fit point spline's too (wave 7,
    # the book parity report: "Fusion shows just the curve"). Off; Fission 180 draws the
    # control frame itself for the splines whose control circles are shown (ControlFrames).
    (SKETCHER_GENERAL, "Bool", "BSplineControlPolygonVisible", False),
]

# Sketch palette options (Fusion's defaults); remembered between sessions.
PALETTE_DEFAULTS = {
    "grid": True,
    "snap": True,
    "slice": False,
    "profile": True,
    "points": True,
    "dimensions": True,
    "constraints": True,
    "projected": True,
}

DIMENSIONAL = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle")
# Tools where Enter after one typed value draws the shape (the pointer gives the rest).
ENTER_FINISHES = {
    "Fission180_SketchLine",
    "Sketcher_CreateLine",
    "Sketcher_CreateRectangle",
    "Sketcher_CreateRectangle_Center",
    "Fission180_PolygonCircumscribed",
    "Fission180_PolygonInscribed",
}
# FreeCAD's Project tool, started by Fission 180's P / Include 3D Geometry or FreeCAD's own
PROJECT_COMMANDS = (
    "Fission180_SketchProject",
    "Fission180_SketchInclude3D",
    "Sketcher_Projection",
    "Sketcher_External",
)
# FreeCAD's spline tools (Fusion's Fit Point / Control Point Spline) and the undo step
# their points are kept in while a spline is drawn.
SPLINE_COMMANDS = (
    "Sketcher_CreateBSpline",
    "Sketcher_CreateBSplineByInterpolation",
    "Sketcher_CreatePeriodicBSpline",
    "Sketcher_CreatePeriodicBSplineByInterpolation",
    "Sketcher_CompCreateBSpline",
)
SPLINE_STEP = "Add Sketch B-Spline"
ELLIPSE_STEP = "Add sketch ellipse"  # FreeCAD's Ellipse tool's undo step
LINE_STEP = "Add sketch line"  # ...and its Line tool's
# the spline tools whose clicks are fit points (the curve goes through them)
FIT_SPLINE_COMMANDS = (
    "Fission180_SketchFitSpline",
    "Sketcher_CreateBSplineByInterpolation",
    "Sketcher_CreatePeriodicBSplineByInterpolation",
)
# Commands after which a new dimension gets the in-place value box.
DIMENSION_COMMANDS = {
    "Sketcher_Dimension",
    "Sketcher_CompDimensionTools",
    "Sketcher_ConstrainDistance",
    "Sketcher_ConstrainDistanceX",
    "Sketcher_ConstrainDistanceY",
    "Sketcher_ConstrainRadius",
    "Sketcher_ConstrainDiameter",
    "Sketcher_ConstrainRadiam",
    "Sketcher_ConstrainAngle",
    "Fission180_SketchDimension",
}

_state = {
    "on": False,
    "saved": [],
    "observer": None,
    "app_observer": None,
    "session": None,
    "profilelib": None,
    "polygon": None,  # {"circumscribed": bool} while Fission 180's polygon tool runs
    "centerline": False,  # new lines are centerlines (Linetype > Centerline, nothing selected)
}


# -- palette options ------------------------------------------------------------------
def option(name):
    try:
        group = App.ParamGet(PALETTE_PARAMS)
        return group.GetBool(name, PALETTE_DEFAULTS[name])
    except Exception:
        return PALETTE_DEFAULTS.get(name, True)


def set_option(name, value):
    """Change a palette option and apply it to the open sketch."""
    try:
        App.ParamGet(PALETTE_PARAMS).SetBool(name, bool(value))
    except Exception as exc:
        warn("sketch palette: %s" % exc)
    if name == "snap":
        _set_param(SNAP, "Bool", "SnapToGrid", bool(value))
    session = current()
    if session is not None:
        session.apply_option(name)


def construction_mode():
    """True while FreeCAD draws new curves as construction curves (its Toggle
    Construction run with nothing selected). FreeCAD keeps that mode only in C++; its
    button icon shows it, so the icon is compared with the construction icon."""
    try:
        cmd = Gui.Command.get("Sketcher_ToggleConstruction")
        actions = cmd.getAction() if cmd is not None else []
        if not actions:
            return False
        constr = Gui.getIcon("Sketcher_ToggleConstruction_Constr")
        if constr is None:
            return False
        shown = actions[0].icon().pixmap(16, 16).toImage()
        return shown == constr.pixmap(16, 16).toImage()
    except Exception:
        return False


def centerline_mode():
    """New lines are drawn as centerlines (Linetype > Centerline with nothing selected)."""
    return bool(_state.get("centerline"))


def toggle_centerline():
    """The palette's Centerline button (Fusion's Linetype): the selected lines become
    centerlines (normal lines again when all of them are), or, with nothing selected, new
    lines are drawn as centerlines until it is clicked again (sketch_centerline.py)."""
    from . import commands, sketch_centerline

    sketch = editing_sketch()
    if sketch is None:
        return
    try:
        geos = []
        others = 0
        for sel in Gui.Selection.getSelectionEx():
            if sel.Object is not sketch:
                continue
            for name in sel.SubElementNames:
                short = name.rsplit(".", 1)[-1]
                if short.startswith("Edge"):
                    geo = int(short[4:]) - 1
                    if sketch.Geometry[geo].TypeId == sketch_centerline.LINE:
                        geos.append(geo)
                    else:
                        others += 1
        if not geos:
            if others:
                commands.tell("Only lines can be centerlines: select a line.")
                return
            _state["centerline"] = not centerline_mode()
            commands.tell(
                "New lines are centerlines (dashed: a dimension to one is a diameter, "
                "Revolve takes it as its axis). Click Centerline again for normal lines."
                if _state["centerline"]
                else "New lines are normal lines again."
            )
            return
        now = set(sketch_centerline.lines(sketch))
        on = not all(g in now for g in geos)
        doc = sketch.Document
        doc.openTransaction("Centerline")
        try:
            sketch_centerline.set_centerline(sketch, geos, on)
            sketch.solve()
        except Exception:
            doc.abortTransaction()
            raise
        doc.commitTransaction()
        Gui.Selection.clearSelection()
    except Exception as exc:
        warn("centerline: %s" % exc)


def normal_mode():
    """Back to normal curves (Fusion starts every sketch with normal lines; FreeCAD keeps
    construction mode from the last sketch)."""
    try:
        if construction_mode() and not Gui.Selection.getSelectionEx():
            Gui.runCommand("Sketcher_ToggleConstruction")
    except Exception as exc:
        warn("sketch line type: %s" % exc)


def _set_param(path, kind, name, value):
    try:
        getattr(App.ParamGet(path), "Set" + kind)(name, value)
    except Exception as exc:
        warn("could not set %s: %s" % (name, exc))


# -- on / off -----------------------------------------------------------------------
def enable():
    if _state["on"]:
        return
    _state["on"] = True
    try:
        from .sketch_infer import repair_snap

        repair_snap()
    except Exception as exc:
        warn("sketch snapping: %s" % exc)
    _save_and_apply(_all_params())
    _patch_profilelib()
    try:
        observer = _GuiObserver()
        Gui.addDocumentObserver(observer)
        _state["observer"] = observer
        app_observer = _AppObserver()
        App.addDocumentObserver(app_observer)
        _state["app_observer"] = app_observer
    except Exception as exc:
        warn("sketch mode: cannot follow sketch editing: %s" % exc)
    try:
        from . import sketch_area_pick

        # Fusion: a finished sketch's areas come before the face they are drawn on, and
        # commands that cannot use them see through them
        sketch_area_pick.enable()
    except Exception as exc:
        warn("sketch areas: %s" % exc)
    try:
        from . import sketch_companions

        sketch_companions.enable()  # Project to Surface / 3D curves go with their sketch
    except Exception as exc:
        warn("sketch curves: %s" % exc)
    sketch = editing_sketch()
    if sketch is not None:
        _start(sketch)


def disable():
    if not _state["on"]:
        return
    _state["on"] = False
    _end()
    try:
        from . import sketch_area_pick

        sketch_area_pick.disable()
    except Exception as exc:
        warn("sketch areas: %s" % exc)
    try:
        from . import sketch_companions

        sketch_companions.disable()
    except Exception as exc:
        warn("sketch curves: %s" % exc)
    for key, remove in (
        ("observer", Gui.removeDocumentObserver),
        ("app_observer", App.removeDocumentObserver),
    ):
        if _state[key] is not None:
            try:
                remove(_state[key])
            except Exception:
                pass
            _state[key] = None
    _unpatch_profilelib()
    _restore_params()


# The user's own values of the settings above, kept until Fission 180 is switched off. In
# FreeCAD's preferences, not in memory: FreeCAD saves its preferences when it quits, so
# after quitting with Fission 180 on, memory alone took Fission 180's values for the user's next
# time (FreeCAD's "make sketch areas" stayed on with Fission 180 off; CI run #95).
BACKUP = "User parameter:BaseApp/Preferences/Mod/Fission180/SketchBackup"


# The light look (theme.py): the colours made for the dark 3D view that would vanish on a
# light one. Fully constrained curves black, as Fusion's on its white background.
LIGHT = {
    "GridLineColor": _rgba("#e1e4e8"),
    "GridDivLineColor": _rgba("#c4c9d0"),
    "FullyConstraintElementColor": _rgba("#1f2329"),
    "FullyConstrainedColor": _rgba("#1f2329"),
    "ConstrainedDimColor": _rgba("#1f2329"),
    "ConstrainedIcoColor": _rgba("#2e7d32"),
    "NonDrivingConstrDimColor": _rgba("#3d5f85"),
    "CursorTextColor": _rgba("#1f2329"),
    "CursorCrosshairColor": _rgba("#1f2329"),
}


def _all_params():
    from . import theme

    light = theme.is_light()
    params = [
        (group, kind, name, LIGHT[name] if light and name in LIGHT else value)
        for group, kind, name, value in PARAMS
    ]
    return params + [(SNAP, "Bool", "SnapToGrid", option("snap"))]


def theme_changed():
    """The look was switched: the sketch colours of the new look, at once (the user's own
    values kept by enable() stay kept)."""
    if not _state["on"]:
        return
    for group, kind, name, value in _all_params():
        if name in LIGHT:
            try:
                getattr(App.ParamGet(group), "Set" + kind)(name, value)
            except Exception as exc:
                warn("sketch colours: %s" % exc)


def _save_and_apply(params):
    from . import theme

    try:
        theme.keep_and_set(params, BACKUP)
    except Exception as exc:
        warn("sketch mode: cannot set FreeCAD's sketch settings: %s" % exc)
    _state["saved"] = list(params)


def _restore_params():
    from . import theme

    try:
        theme.give_back(_all_params(), BACKUP)
    except Exception as exc:
        warn("sketch mode: cannot give FreeCAD's sketch settings back: %s" % exc)
    _state["saved"] = []


def give_back_left_over():
    """Fission 180 is off: put back FreeCAD's sketch settings a session that ended with Fission 180
    on left behind (nothing to do when none were kept)."""
    if not _state["on"]:
        _restore_params()


# -- which sketch is open --------------------------------------------------------------
def sketch_edited_anywhere():
    """A sketch is being edited in any open design (not only the active one): FreeCAD's
    one task panel is then the Sketcher's, whatever design is in front."""
    try:
        for name in App.listDocuments():
            gdoc = Gui.getDocument(name)
            edit = gdoc.getInEdit() if gdoc is not None else None
            obj = getattr(edit, "Object", None)
            if obj is not None and obj.TypeId == "Sketcher::SketchObject":
                return True
    except Exception:
        pass
    return False


def editing_sketch():
    """The sketch being edited in the active document, or None."""
    try:
        gdoc = Gui.ActiveDocument
        edit = gdoc.getInEdit() if gdoc is not None else None
        obj = edit.Object if edit is not None else None
        if obj is not None and obj.TypeId == "Sketcher::SketchObject":
            return obj
    except Exception:
        pass
    return None


def current():
    """The open SketchSession, or None."""
    session = _state["session"]
    if session is not None and session.closed:
        _state["session"] = None
        return None
    return session


def picked_areas(sketch):
    """The areas picked inside the open sketch `sketch` (a point inside each, sketch mm),
    for E / Q to extrude (sketch_areas.profiles turns them into the sketch's areas once
    it is closed); [] when none are picked or another sketch is open."""
    session = current()
    if session is None or sketch is None or session.sketch is not sketch:
        return []
    try:
        return session.areas.points()
    except Exception as exc:
        warn("sketch areas: %s" % exc)
        return []


class _GuiObserver:
    """FreeCAD tells us when a sketch opens/closes; the work runs later from a timer."""

    def slotInEdit(self, vp):
        try:
            obj = vp.Object
            if obj is not None and obj.TypeId == "Sketcher::SketchObject":
                name, doc = obj.Name, obj.Document.Name
                QtCore.QTimer.singleShot(0, lambda: _start_named(doc, name))
        except Exception as exc:
            warn("sketch mode: %s" % exc)
        _areas_later("update")  # (a sketch is open: no shift, areas let clicks through)

    def slotResetEdit(self, vp):
        try:
            QtCore.QTimer.singleShot(0, _end_if_closed)
        except Exception as exc:
            warn("sketch mode: %s" % exc)
        _areas_later("update")

    def slotDeletedDocument(self, doc):
        try:
            from . import sketch_area_pick

            sketch_area_pick.forget(doc.Document.Name)
        except Exception as exc:
            warn("sketch areas: %s" % exc)


def _areas_later(name):
    """sketch_area_pick.<name>() from a Qt timer (not inside FreeCAD's signal)."""
    try:
        from . import sketch_area_pick

        sketch_area_pick.later(getattr(sketch_area_pick, name))
    except Exception as exc:
        warn("sketch areas: %s" % exc)


class _AppObserver:
    """Changes to the open sketch (new curves, constraints) refresh the shading,
    the display options and open the dimension box. Only schedules work."""

    def slotChangedObject(self, obj, prop):
        session = _state["session"]
        if session is None or session.closed:
            return
        try:
            if prop in ("Geometry", "Constraints", "ExternalGeo", "Placement") and (
                obj.Name == session.name and obj.Document.Name == session.doc_name
            ):
                session.changed(prop)
        except Exception:
            pass

    def _settled(self, doc, kind):
        session = _state["session"]
        if session is None or session.closed:
            return
        try:
            if doc.Name == session.doc_name:
                session.settled(kind, len(session.sketch.Constraints))
        except Exception:
            pass

    def slotCommitTransaction(self, doc):
        self._settled(doc, "commit")

    def slotAbortTransaction(self, doc):
        self._settled(doc, "abort")

    def slotUndoDocument(self, doc):
        self._settled(doc, "undo")
        _merge_recompute_step(doc, undo=True)

    def slotRedoDocument(self, doc):
        self._settled(doc, "redo")
        _merge_recompute_step(doc, undo=False)


# FreeCAD records the recompute it runs when a sketch is closed as an undo step of its
# own ("Sketch recompute", ViewProviderSketch::unsetEdit). The first Ctrl+Z after Finish
# Sketch then seemed to do nothing, or showed the part half rebuilt (with a broken
# profile: only the features after it). In Fusion one Ctrl+Z takes back the last sketch
# change with its effect on the part, so that step is undone/redone together with the
# sketch change before it.
RECOMPUTE_STEP = "Sketch recompute"
# Steps undone and redone together with the step before them: FreeCAD's recompute on
# closing a sketch, and the constraints Fission 180 adds right after a click
# (sketch_infer.py: Fusion adds them with the line itself).
INFER_STEP = "Inferred Constraints"
GLUED_STEPS = (RECOMPUTE_STEP, INFER_STEP)
# FreeCAD's drawing tools record the constraints of the points they were clicked on as a
# step of its own after the shape ("Add Auto-Constraints"): one Ctrl+Z took only those back
# and left the shape (Fusion: one Ctrl+Z, the spline is gone). That step goes with the
# shape's step before it: the spline's since 3.2.1, every tool's since wave 7 (the book
# parity report: "Ctrl+Z after drawing a polyline only removed its auto-constraints, not
# the lines", with Fission 180's own inferred constraints glued in front of them).
AUTO_STEP = "Add Auto-Constraints"
_merging = {"busy": False}


def _count_splines(sketch):
    try:
        return sum(1 for g in sketch.Geometry if g.TypeId == "Part::GeomBSplineCurve")
    except Exception:
        return 0


def _glued_next(doc):
    """The first step of the redo list goes with the step before it (the newest of the
    undo list)."""
    if not doc.RedoNames:
        return False
    following = doc.RedoNames[0]
    if following in GLUED_STEPS:
        return True
    return following == AUTO_STEP and bool(doc.UndoNames)


def _merge_recompute_step(doc, undo):
    if _merging["busy"]:
        return
    try:
        if undo:
            # the step just undone is first in the redo list
            go_on = _glued_next(doc) and bool(doc.UndoNames)
        else:
            # the step just redone is first in the undo list; a step glued to it is
            # next in the redo list
            go_on = _glued_next(doc)
    except Exception:
        return
    if go_on:
        name = doc.Name
        QtCore.QTimer.singleShot(0, lambda: _one_more_step(name, undo))


def _one_more_step(doc_name, undo):
    _merging["busy"] = True
    try:
        doc = App.getDocument(doc_name)
        # several glued steps in a row (inferred constraints, then a recompute)
        for _ in range(4):
            if undo and doc.UndoNames:
                doc.undo()
            elif not undo and doc.RedoNames:
                doc.redo()
            if not _glued_next(doc) or (undo and not doc.UndoNames):
                break
        if doc.isTouched() or any("Touched" in o.State for o in doc.Objects):
            doc.recompute()
    except Exception as exc:
        warn("undo: %s" % exc)
    finally:
        _merging["busy"] = False


NO_MORE_UNDO = (
    "Nothing more to undo in this sketch. Finish Sketch first to undo what came before it."
)


def _back_into_sketch(doc_name, name):
    """Ctrl+Z went one step past what was done in the open sketch (SketchSession.
    _count_undo): the step that made the sketch, which deletes it and ends the editing, or
    the last step of the design before a sketch opened for editing. That step is put back
    and the sketch stays open (or opens again), with a note beside the pointer. Before,
    the sketch closed, the camera turned away, and Redo brought back the curves but not
    the open sketch (the book parity report, 2026-11-10). From a timer."""
    from . import commands

    _merging["busy"] = True  # (the redo is ours: no step glued to it follows)
    try:
        doc = App.getDocument(doc_name)
        if doc is None or not doc.RedoNames:
            return
        doc.redo()
        if doc.isTouched() or any("Touched" in o.State for o in doc.Objects):
            doc.recompute()
        sketch = doc.getObject(name)
        if sketch is not None and editing_sketch() is not sketch:
            from . import sketch_ui

            # the sketch came back as it was when the Undo deleted it: hidden, as FreeCAD
            # hides every sketch while it is open. Opened again like that, Finish Sketch
            # would "restore" it hidden for good
            try:
                if sketch.ViewObject is not None and not sketch.ViewObject.Visibility:
                    sketch.ViewObject.Visibility = True
            except Exception as exc:
                warn("undo: %s" % exc)
            sketch_ui.edit_sketch(sketch)
        commands.tell(NO_MORE_UNDO)
    except Exception as exc:
        warn("undo: %s" % exc)
    finally:
        _merging["busy"] = False


def _start_named(doc_name, name):
    try:
        doc = App.getDocument(doc_name)
        sketch = doc.getObject(name) if doc is not None else None
        if sketch is not None and editing_sketch() is sketch:
            _start(sketch)
    except Exception as exc:
        warn("sketch mode: could not prepare the sketch: %s" % exc)


def repark_keys():
    """FreeCAD makes the Sketcher's buttons only when a sketch is first opened, and
    those come with the Sketcher's own one-letter keys (C coincident, T tangent, E
    equal, P parallel...). Two owners of a key make Qt ignore both, so C and T did
    nothing in a sketch. When that happens the Fusion keys are bound again, which
    parks the new FreeCAD keys too (shortcuts.py gives them back when Fission 180 is off)."""
    from . import shortcuts

    keys = set(shortcuts.bound_keys())
    if not keys:
        return False
    for name in Gui.listCommands():
        try:
            cmd = Gui.Command.get(name)
            current_key = cmd.getShortcut() if cmd is not None else ""
        except Exception:
            continue
        if current_key and shortcuts.normalise(current_key) in keys:
            shortcuts.restore()
            shortcuts.apply()
            return True
    return False


def _start(sketch):
    session = current()
    if session is not None and session.sketch is sketch:
        return
    _end()
    if not _state["on"]:
        return
    try:
        from . import sketch_ui

        # the design as it is at the sketch's place, never the step it hangs on (a sketch
        # opened by FreeCAD's own commands still had "Show support" on)
        sketch_ui.show_design_at(sketch)
    except Exception as exc:
        warn("sketch mode: %s" % exc)
    try:
        repark_keys()
    except Exception as exc:
        warn("sketch keys: %s" % exc)
    try:
        _state["session"] = SketchSession(sketch)
        log("sketch %s: Fusion sketch mode on" % sketch.Label)
        try:
            from . import sketch_helpers

            sketch_helpers.opened(_state["session"])  # hidden helper lines stay unseen
        except Exception as exc:
            warn("sketch helper lines: %s" % exc)
    except Exception as exc:
        warn("sketch mode: %s" % exc)


def _end_if_closed():
    session = current()
    if session is not None and editing_sketch() is not session.sketch:
        _end()


def _end():
    session = _state["session"]
    _state["session"] = None
    if session is not None:
        try:
            session.close()
        except Exception as exc:
            warn("sketch mode: closing: %s" % exc)
        doc_name, name = session.doc_name, session.name
        QtCore.QTimer.singleShot(0, lambda: _show_finished(doc_name, name))


def _show_finished(doc_name, name):
    """Fusion: a finished sketch stays shown until a feature uses it (Extrude hides its
    profile sketch). FreeCAD hides a sketch while it is open and puts back how it was
    shown before; a sketch that was hidden then for a reason that is over (opened hidden
    after an Undo and Redo of its making; its only feature deleted since) stayed hidden
    after Finish Sketch, with an empty view (the book parity report: "the sketch had
    become hidden; right-click > Show"). From a timer, after FreeCAD closed the sketch."""
    try:
        doc = App.getDocument(doc_name) if doc_name in App.listDocuments() else None
        sketch = doc.getObject(name) if doc is not None else None
        from . import sketch_ui

        if sketch is None or sketch.ViewObject is None or editing_sketch() is sketch:
            return
        if sketch.ViewObject.Visibility:
            sketch_ui.shown_before_edit(doc_name, name)  # (asked once)
            return

        shown = sketch_ui.shown_before_edit(doc_name, name)
        if not shown or sketch_ui.used_by_feature(sketch):
            return  # hidden before it was opened (by hand, or by its feature): stays so
        sketch.ViewObject.Visibility = True
        log("sketch %s shown again: nothing uses it yet" % sketch.Label)
    except Exception as exc:
        warn("sketch mode: %s" % exc)


# -- helpers for the 3D view ----------------------------------------------------------
def gl_widget():
    """The OpenGL widget of the active 3D view (receives mouse and keys)."""
    try:
        area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        sub = area.activeSubWindow() or (area.subWindowList() or [None])[-1]
        if sub is None:
            return None
        for widget in sub.findChildren(QtWidgets.QWidget):
            if widget.metaObject().className() == "QOpenGLWidget":
                return widget
    except Exception:
        pass
    return None


def find_node(root, name):
    """(node, its parent) for the first Coin node called `name` under root (also inside
    switches), or (None, None). The search path dies with the search action, so only
    the nodes (kept alive by the scene graph) are returned."""
    from pivy import coin

    action = coin.SoSearchAction()
    action.setName(coin.SbName(name))
    action.setInterest(coin.SoSearchAction.FIRST)
    action.setSearchingAll(True)
    action.apply(root)
    path = action.getPath()
    if path is None or path.getLength() < 2:
        return None, None
    node = path.getTail()
    parent = path.getNodeFromTail(1)
    return node, parent


def view_widget(gl=None):
    """The 3D view widget that has the keyboard (Gui::View3DInventorViewer): a real
    keyboard sends its keys there, not to the OpenGL drawing area inside it (which gets
    the mouse). Keys sent to the drawing area go on to it as well."""
    gl = gl if gl is not None else gl_widget()
    widget = gl
    try:
        while widget is not None:
            if widget.metaObject().className() == "Gui::View3DInventorViewer":
                return widget
            widget = widget.parentWidget()
    except Exception:
        pass
    return gl


def _same(a, b):
    """The same Qt object (Python wrappers of one widget are not always the same)."""
    if a is None or b is None:
        return False
    try:
        import shiboken6

        return shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]
    except Exception:
        return a is b


def _is_valid(widget):
    try:
        import shiboken6

        return widget is not None and shiboken6.isValid(widget)
    except Exception:
        try:
            widget.objectName()
            return True
        except Exception:
            return False


def label_point(sketch, index):
    """Sketch point where FreeCAD draws the text of dimension `index` (lengths, radius,
    diameter), or None. Lengths: LabelDistance off the middle of the measured points
    (LabelPosition along them); radius/diameter: LabelDistance beyond the circle at the
    angle LabelPosition (10 means 0), as FreeCAD's SoDatumLabel does."""
    c = sketch.Constraints[index]
    if c.Type in ("Radius", "Diameter"):
        g = sketch.Geometry[c.First]
        center, radius = getattr(g, "Center", None), getattr(g, "Radius", None)
        if center is None or radius is None:
            return None
        angle = c.LabelPosition
        if angle == 10:
            if g.TypeId == "Part::GeomArcOfCircle":
                angle = (g.FirstParameter + g.LastParameter) / 2.0
            else:
                angle = 0.0
        direction = App.Vector(math.cos(angle), math.sin(angle), 0)
        return center + direction * (radius + c.LabelDistance)
    if c.Type not in ("Distance", "DistanceX", "DistanceY"):
        return None
    try:
        # every form of a length dimension: from the origin, to a projected point, a point
        # to a line (sf/book-sketch-b; the code below knew two points of sketch curves)
        from . import sketch_dimension_tool

        spot = sketch_dimension_tool.label_point(sketch, index)
        return App.Vector(spot[0], spot[1], 0) if spot is not None else None
    except Exception:
        pass

    def point(geo, pos):
        g = sketch.Geometry[geo]
        return {1: g.StartPoint, 2: g.EndPoint}.get(pos, getattr(g, "Center", None))

    if c.Second >= 0:
        p1, p2 = point(c.First, c.FirstPos), point(c.Second, c.SecondPos)
    elif c.First >= 0 and c.FirstPos == 0:
        g = sketch.Geometry[c.First]
        p1, p2 = g.StartPoint, g.EndPoint
    else:
        return None
    if p1 is None or p2 is None:
        return None
    if c.Type == "DistanceX":
        p2 = App.Vector(p2.x, p1.y, 0)
    elif c.Type == "DistanceY":
        p2 = App.Vector(p1.x, p2.y, 0)
    direction = p2 - p1
    if direction.Length < 1e-9:
        return None
    direction.normalize()
    normal = App.Vector(-direction.y, direction.x, 0)
    return (p1 + p2) * 0.5 + normal * c.LabelDistance + direction * c.LabelPosition


# -- the open sketch -----------------------------------------------------------------
class SketchSession:
    def __init__(self, sketch):
        self.sketch = sketch
        self.doc = sketch.Document
        self.name = sketch.Name
        self.doc_name = sketch.Document.Name
        self.closed = False
        self.view = Gui.ActiveDocument.ActiveView
        self.gl = gl_widget()
        self.constraint_count = len(sketch.Constraints)
        self.editor = None
        self.palette = None
        self.last_press = None
        self._drawing_cursor = False  # what the view's cursor said last (drawing_cursor)
        self.undo_steps = 0  # steps of the undo list made in this sketch (_count_undo)
        self._tidy_seen = len(sketch.Geometry)  # curves already looked at by _tidy_new
        try:
            self._undo_names = tuple(self.doc.UndoNames)
        except Exception:
            self._undo_names = ()
        self._enter_follow = False
        self.shading = ProfileShading(self)
        from .sketch_areas import AreaPicker, ensure_areas

        # Fusion: click inside a closed area to pick it as a profile for E / Q
        self.areas = AreaPicker(self)
        ensure_areas(sketch)  # an older sketch: its areas can be clicked after Finish Sketch
        self.display = DisplayOptions(self)
        self.fixed = FixedColour(self)
        from . import sketch_dimension_signs

        # the diameter sign on dimensions to a centerline
        self.signs = sketch_dimension_signs.DiameterSigns(self)
        from . import sketch_field_names

        # parameter names typed into the value boxes of FreeCAD's own drawing tools
        self.names = sketch_field_names.FieldNames(self)
        self.right_angles = None  # the 90 degree marks at corners (sketch_right_angles.py)
        try:
            from .sketch_right_angles import RightAngleMarks

            self.right_angles = RightAngleMarks(self)
            self.right_angles.visible = option("constraints")
        except Exception as exc:
            warn("right-angle marks: %s" % exc)
        self.polygon = PolygonPreview(self)
        self.frames = ControlFrames(self)  # control point splines' control frames
        from .sketch_line import LineChain

        self.line = LineChain(self)
        self.tool = None  # Fission 180's own drawing tool while one runs (sketch_draw.py)
        self.check = None  # Fusion's floating green check (sketch_check.py), made below
        self.sketch3d = None  # Fusion's 3D Sketch (sketch3d_ui.Layer) once it is used
        self.infer = None
        try:
            from .sketch_infer import Inference

            # Fusion's guides, perpendicular and Ctrl while drawing (sketch_infer.py)
            self.infer = Inference(self)
        except Exception as exc:
            warn("sketch inference: %s" % exc)
        self.fillet_watch = FilletRadius(self)
        from .sketch_select import SketchSelect

        # Fusion: a double-click selects a curve's chain; a box replaces / Shift adds /
        # Ctrl toggles (sketch_select.py)
        self.select = SketchSelect(self)
        self._refresh = QtCore.QTimer()
        self._refresh.setSingleShot(True)
        self._refresh.setInterval(120)
        self._refresh.timeout.connect(self._refreshed)
        self.filter = _ViewFilter(self)
        self.keys = _KeyFilter(self)
        self.viewer = view_widget(self.gl) if self.gl is not None else None
        self._fields = []
        self._typed = None  # the value field the user typed a value into
        self._typed_since_commit = False  # a value typed for the shape being drawn
        self.last_letter = ""  # what the last letter typed into a value field did (reports)
        if self.gl is not None:
            remove_stray_editors(self.gl)
            self.gl.installEventFilter(self.filter)
        if self.viewer is not None:
            self.viewer.installEventFilter(self.keys)
        try:
            from .sketch_check import FloatingCheck

            self.check = FloatingCheck(self)  # ends a line chain / a spline (Fusion)
        except Exception as exc:
            warn("sketch check: %s" % exc)
        try:
            QtWidgets.QApplication.instance().focusChanged.connect(self._focus_changed)
        except Exception as exc:
            warn("sketch mode: value fields: %s" % exc)
        for name in PALETTE_DEFAULTS:
            if name != "snap":
                self.apply_option(name)
        self._palette_tries = 0
        normal_mode()
        try:
            from . import sketch3d_ui

            if sketch3d_ui.starts_on(sketch):  # a sketch with 3D curves opens in 3D
                sketch3d_ui.layer(self).set_on(True, quiet=True)
        except Exception as exc:
            warn("3D Sketch: %s" % exc)
        QtCore.QTimer.singleShot(0, self._add_palette)
        self._refreshed()

    # -- changes ---------------------------------------------------------------------
    def changed(self, prop):
        if self.infer is not None:
            self.infer.invalidate()
        if self.tool is not None:
            self.tool.changed()
        self.fixed.invalidate()
        self.signs.invalidate()
        self._refresh.start()

    def _refreshed(self):
        if self.closed:
            return
        try:
            self.shading.update()
            self.areas.refresh(self.shading.shaded)
            self.display.apply()
            self.fixed.apply()
            self.signs.apply()
            self.frames.update()
        except Exception as exc:
            warn("sketch display: %s" % exc)
        if self.right_angles is not None:
            self.right_angles.update()

    def settled(self, kind, count):
        """A sketch operation was committed, aborted or undone (called by FreeCAD's
        document signal: only counts here, the box opens from a timer). A dimension
        the Dimension tool just placed gets the value box. FreeCAD adds the dimension
        already while it follows the mouse, so only a committed one counts."""
        before = self.constraint_count
        grew = count > before
        self.constraint_count = count
        self._count_undo(kind)
        if self.infer is not None:
            try:
                self.infer.commit_signal(kind)
            except Exception as exc:
                warn("sketch inference: %s" % exc)
        self.names.settled(kind)
        if kind in ("undo", "redo", "abort"):
            try:
                self._tidy_seen = len(self.sketch.Geometry)
            except Exception:
                pass
        if kind == "commit":
            self._typed_since_commit = False  # the next shape: nothing typed yet
            QtCore.QTimer.singleShot(0, self._repair)
            QtCore.QTimer.singleShot(0, self._tidy_new)
            self.line.committed()
            self.fillet_watch.committed()
        if kind == "commit" and grew:
            QtCore.QTimer.singleShot(0, lambda: self._new_dimension(count - 1))
        if kind in ("commit", "redo"):
            # (FreeCAD's Tangent on joined ends swaps the join: the count does not grow)
            QtCore.QTimer.singleShot(0, lambda: self._check_added(before, kind))
        if kind in ("undo", "redo") and self.editor is not None:
            QtCore.QTimer.singleShot(0, self._close_editor_after_undo)
        if kind in ("undo", "redo") and self.tool is not None:
            tool = self.tool
            QtCore.QTimer.singleShot(0, lambda: _tool_undone(tool))

    def _count_undo(self, kind):
        """How many steps of the design's undo list were made in this sketch since it
        opened. An Undo that takes one more is put back (_back_into_sketch): Ctrl+Z never
        leaves the sketch. Only counts and a timer (called from FreeCAD's signal)."""
        try:
            names = tuple(self.doc.UndoNames)
        except Exception:
            return
        before, self._undo_names = self._undo_names, names
        if kind == "commit":
            if len(names) > len(before):
                self.undo_steps += len(names) - len(before)
            elif names != before:
                # (the list is full: the oldest step fell out as this one came in)
                self.undo_steps = min(self.undo_steps + 1, len(names))
        elif kind == "redo":
            self.undo_steps += 1
        elif kind == "undo":
            self.undo_steps -= 1
            if self.undo_steps < 0:
                doc_name, name = self.doc_name, self.name
                QtCore.QTimer.singleShot(0, lambda: _back_into_sketch(doc_name, name))

    def _tidy_new(self):
        """A spline or an ellipse FreeCAD's tools just made is shown as Fusion shows it
        (sketch_draw_helpers.py): a spline's helper constraints are not drawn, a fit point
        spline's control circles neither; an ellipse loses its two focus points, and one
        drawn level or upright is held so (Fusion infers it while drawing: the book's
        ellipse is fully defined by its dimensions). In a step glued to the shape's own
        (one Ctrl+Z). From a timer after FreeCAD's commit."""
        if self.closed:
            return
        try:
            sketch = self.sketch
            geometry = sketch.Geometry
            seen, self._tidy_seen = self._tidy_seen, len(geometry)
            if len(geometry) <= seen:
                return
            from . import sketch_draw_helpers as helpers

            new = range(seen, len(geometry))
            # only what the drawing tools just made (their step is among the newest of the
            # undo list, under its own constraints' steps): a spline or an ellipse that
            # came some other way (a paste, a pattern, a script) is left as it is
            steps = list(self.doc.UndoNames)[:3]
            splines, ellipses, centerlines = [], [], []
            if centerline_mode() and LINE_STEP in steps:
                # Linetype > Centerline is on: the lines the Line tool just drew
                centerlines = [
                    i
                    for i in new
                    if geometry[i].TypeId == "Part::GeomLineSegment"
                    and not sketch.getConstruction(i)
                ]
            if SPLINE_STEP in steps:
                splines = [i for i in new if geometry[i].TypeId == helpers.BSPLINE]
            if ELLIPSE_STEP in steps:
                ellipses = [i for i in new if geometry[i].TypeId == helpers.ELLIPSE]
            if not splines and not ellipses and not centerlines:
                return
            from . import recent

            fit = recent.running_tool() in FIT_SPLINE_COMMANDS
            doc = self.doc
            infer = self.infer
            if infer is not None:
                infer._applying = True  # (our own step: no shape of the tool's)
            doc.openTransaction(INFER_STEP)
            try:
                for spline in splines:
                    helpers.tidy_spline(sketch, spline, fit)
                for ellipse in reversed(ellipses):
                    major, _minor = helpers.tidy_ellipse(sketch, ellipse)
                    self._level_ellipse(major)
                if centerlines:
                    from . import sketch_centerline

                    sketch_centerline.set_centerline(sketch, centerlines, True)
                sketch.solve()
            except Exception:
                doc.abortTransaction()
                raise
            finally:
                if infer is not None:
                    infer._applying = False
            doc.commitTransaction()
            self._tidy_seen = len(sketch.Geometry)
            if infer is not None:
                infer.seen = sketch.GeometryCount
                infer.invalidate()
        except Exception as exc:
            warn("sketch helpers: %s" % exc)

    def _level_ellipse(self, major):
        """The major axis of an ellipse just drawn within HVDegrees of level or upright
        gets Horizontal / Vertical (dropped again if the sketch cannot take it)."""
        import math

        import Sketcher

        from . import sketch_infer

        if major is None:
            return
        sketch = self.sketch
        line = sketch.Geometry[major]
        d = line.EndPoint - line.StartPoint
        if d.Length < 1e-9:
            return
        tol = math.radians(float(sketch_infer.setting("HVDegrees")))
        angle = abs(math.atan2(d.y, d.x))
        if min(angle, math.pi - angle) <= tol:
            name = "Horizontal"
        elif abs(angle - math.pi / 2.0) <= tol:
            name = "Vertical"
        else:
            return
        index = sketch.addConstraint(Sketcher.Constraint(name, major))
        if sketch.solve() < 0 or sketch.RedundantConstraints or sketch.ConflictingConstraints:
            sketch.delConstraint(index)
            sketch.solve()

    def _close_editor_after_undo(self):
        """Undo and Redo put the sketch's curves and dimensions back as whole lists, so the
        numbers the box knows its dimension by can now belong to another one (a curve deleted,
        a dimension opened, Undo: the typed value went into the wrong dimension). The box
        closes without setting anything, and says so when something was typed in it."""
        editor = self.editor
        if editor is None or self.closed:
            return
        typed = False
        try:
            text = editor.edit.text().strip()
            typed = bool(text) and not editor._fresh
        except Exception:
            pass
        editor.discard()
        if typed:
            from . import commands

            commands.tell(
                "Undo changed the sketch while the dimension box was open: the value "
                "was not set."
            )

    def _repair(self):
        """FreeCAD's trim can leave an invalid constraint behind (sketch_fix.py)."""
        if self.closed:
            return
        try:
            from . import sketch_fix

            if not sketch_fix.bad_coincidences(self.sketch):
                return
            self.doc.openTransaction("Repair Trim")
            try:
                fixed = sketch_fix.repair(self.sketch)
                self.sketch.solve()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()
            log("repaired %d constraint(s) FreeCAD's trim made invalid" % fixed)
        except Exception as exc:
            warn("could not repair the sketch: %s" % exc)

    def _new_dimension(self, index):
        if self.closed or self.editor is not None:
            return
        try:
            from . import recent

            last = recent.last()
            if last is None or last[0] not in DIMENSION_COMMANDS:
                return
            constraints = self.sketch.Constraints
            if index >= len(constraints):
                return
            c = constraints[index]
            if c.Type in DIMENSIONAL and c.Driving:
                if self._make_driven_if_redundant(index):
                    return
                self.edit_dimension(index)
        except Exception as exc:
            warn("dimension box: %s" % exc)

    def _make_driven_if_redundant(self, index):
        """A dimension on a size the other dimensions/constraints already set would
        over-constrain the sketch (FreeCAD keeps it and the sketch turns red). Fusion
        offers a driven dimension instead: that is what it becomes here, without asking.
        True when it was made driven."""
        from . import sketch_explain as explain
        from . import sketch_explain_core as explain_core

        sketch = self.sketch
        try:
            finding = explain.check_new(sketch, [index], probe=True)
        except Exception:
            return False
        if not finding:
            return False
        explain.log_finding("dimension", sketch, finding)
        doc = self.doc
        doc.openTransaction("Driven Dimension")
        try:
            sketch.setDriving(index, False)
            sketch.solve()
        except Exception:
            doc.abortTransaction()
            raise
        doc.commitTransaction()
        from . import commands

        text, _count = explain.words(sketch, finding.culprits)
        commands.tell(explain_core.driven_dimension(text, finding.partial))
        explain.highlight(sketch, finding.culprits)
        return True

    def _check_added(self, first, kind):
        """FreeCAD's own constraint tools (Horizontal/Vertical, Parallel, Equal...) add what
        was clicked even when it fights the sketch (the sketch turns red) or repeats it.
        Fusion refuses such a constraint and shows which ones it fights: the step is taken
        back and the message names them, highlighted (sketch_explain.py). Whatever the tool
        was started with: a preselected line, two points (FreeCAD's "alignment"), or a
        Tangent on joined ends (FreeCAD swaps the join for an end-to-end tangency: the new
        one is the last). Dimensions are handled by _new_dimension (made driven); a Redo of
        a refused step is refused again. A refused step leaves nothing to Redo (Fusion keeps
        no trace of it)."""
        if self.closed:
            return
        try:
            doc, sketch = self.doc, self.sketch
            from . import commands
            from . import sketch_explain as explain
            from . import sketch_explain_core as explain_core

            step = (doc.UndoNames or [""])[0]
            count = len(sketch.Constraints)
            if count > first:
                new = list(range(first, count))
            elif explain_core.is_swap_step(step) and count:
                new = [count - 1]
            else:
                return
            types = [sketch.Constraints[i].Type for i in new]
            title = explain_core.constraint_step_title(step, types)
            if title is None:  # not a constraint tool's step (a dimension's: made driven)
                return

            finding = explain.check_new(sketch, new, probe=True)
            if not finding:
                return
            explain.log_finding(title, sketch, finding)
            text = explain.refusal(sketch, title, finding)
            doc.undo()
            if kind == "commit":
                _drop_redo(doc, sketch, step)
            commands.tell(text)
            explain.highlight(sketch, finding.culprits)
        except Exception as exc:
            warn("constraint check: %s" % exc)

    # -- palette options -----------------------------------------------------------------
    def apply_option(self, name):
        try:
            value = option(name)
            vp = self.sketch.ViewObject
            if name == "grid":
                if bool(vp.ShowGrid) != value:
                    vp.ShowGrid = value
            elif name == "slice":
                self.set_slice(value)
            elif name == "profile":
                self.shading.set_visible(value)
                if not value:
                    self.areas.clear()  # hidden profiles cannot stay picked
            elif name in ("points", "dimensions", "constraints", "projected"):
                self.display.apply()
                if name == "constraints" and self.right_angles is not None:
                    self.right_angles.set_visible(value)
        except Exception as exc:
            warn("sketch palette %s: %s" % (name, exc))

    def set_slice(self, on):
        vp = self.sketch.ViewObject
        if bool(vp.SectionView) == bool(on):
            return
        tv = vp.TempoVis
        if tv is None:
            return
        reverted = False
        try:
            direction = self.view.getViewDirection()
            normal = self.sketch.getGlobalPlacement().Rotation.multVec(App.Vector(0, 0, 1))
            reverted = direction.dot(normal) > 0
        except Exception:
            pass
        tv.sketchClipPlane(self.sketch, bool(on), reverted)

    def look_at(self):
        try:
            Gui.runCommand("Sketcher_ViewSketch")
        except Exception as exc:
            warn("look at: %s" % exc)

    # -- the palette -----------------------------------------------------------------------
    def _add_palette(self):
        if self.closed:
            return
        try:
            from . import sketch_palette

            self.palette = sketch_palette.install(self)
        except Exception as exc:
            warn("sketch palette: %s" % exc)
            self.palette = None
        if self.palette is None and self._palette_tries < 10:
            self._palette_tries += 1
            QtCore.QTimer.singleShot(100, self._add_palette)

    # -- dimensions --------------------------------------------------------------------
    def edit_dimension(self, index, pos=None):
        """Open the value box for dimension `index` (at pos, view pixels)."""
        if self.gl is None:
            return
        self.close_editor(commit=True)
        label = self.label_pixel(index)
        if label is not None:
            pos, centred = label, True  # over the dimension's text, like Fusion
        else:
            centred = False
            if pos is None:
                pos = self.last_press or self.gl.mapFromGlobal(QtGui.QCursor.pos())
        self.editor = DimensionEditor(self, index, pos, centred)

    def show_all_if_outside(self):
        """After the whole sketch was scaled: when part of it is outside the view now, the
        view shows all of it (Fusion fits the view then; Autodesk community manager:
        "auto-fit will get invoked when ... the sketch goes outside the canvas")."""
        if self.closed or self.gl is None:
            return
        try:
            box = self.sketch.Shape.BoundBox
            if not box.isValid():
                return
            ratio = self.gl.devicePixelRatioF() or 1.0
            w, h = self.gl.width() * ratio, self.gl.height() * ratio
            place = self.sketch.getGlobalPlacement()
            for corner in range(8):
                p = place.multVec(box.getPoint(corner))
                x, y = self.view.getPointOnViewport(p)
                if x < 0 or y < 0 or x > w or y > h:
                    self.view.fitAll()
                    return
        except Exception as exc:
            warn("sketch view: %s" % exc)

    def label_pixel(self, index):
        """Where a dimension's text is on screen (view pixels), or None."""
        try:
            local = label_point(self.sketch, index)
            if local is None:
                return None
            world = self.sketch.getGlobalPlacement().multVec(local)
            x, y = self.view.getPointOnViewport(world)
            ratio = self.gl.devicePixelRatioF()
            return QtCore.QPoint(int(x / ratio), int(self.gl.height() - y / ratio))
        except Exception:
            return None

    def close_editor(self, commit=True):
        """Close the dimension box, keeping a typed value when it can be set. It always
        closes (only Enter typed in the box keeps it open with the reason, like Fusion): a
        value that cannot be set is dropped with a note next to the mouse. A box that stayed
        open here was forgotten by the sketch and stayed on the screen for good, also after
        Finish Sketch (Luca: "Invalid constraint index: 19" boxes over the part)."""
        editor = self.editor
        if editor is None:
            return
        try:
            editor.finish(commit)
            if not editor.closed():
                reason = editor.reason()
                editor.finish(False)
                if reason:
                    from . import commands

                    commands.tell("The dimension was not changed: %s" % reason)
        except Exception as exc:
            warn("dimension box: %s" % exc)
            editor.discard()
        finally:
            if self.editor is editor:
                self.editor = None

    # -- Esc -------------------------------------------------------------------------
    def tool_running(self):
        """A drawing tool is running: Fission 180's Line chain, or FreeCAD's drawing cursor
        on the 3D view (FreeCAD gives Python no other sign of its active tool)."""
        if self.closed:
            return False
        if self.line.active or (self.tool is not None and self.tool.active):
            return True
        return self.drawing_cursor()

    def drawing_cursor(self):
        """FreeCAD's drawing cursor is on the 3D view: one of its sketch tools runs.

        While the left button is down the view shows a pointing hand whatever runs
        (View3DInventorViewer::setCursorRepresentation, the navigation's SELECTION mode),
        and it keeps it after the release for as long as Ctrl stays held (Revit style:
        Ctrl alone changes no mode). The hand therefore says nothing: the answer is what
        the cursor said last. (Taking the hand for a tool sent the release of a Ctrl+click
        on a curve through the inference's "Ctrl frees the point" path, with FreeCAD's
        pick radius shrunk to nothing: the click selected nothing. Book parity report,
        2026-11-10: "Ctrl+click does not add to a sketch selection".)"""
        try:
            gl = self.gl
            if gl is None or not _is_valid(gl):
                return False
            shape = gl.cursor().shape()
            if shape != QtCore.Qt.PointingHandCursor:
                self._drawing_cursor = shape != QtCore.Qt.ArrowCursor
            return self._drawing_cursor
        except Exception:
            return False

    def stop_tool(self):
        """End Fission 180's own drawing tool, if one runs (sketch_draw.py)."""
        tool = self.tool
        if tool is not None:
            try:
                tool.stop()
            except Exception as exc:
                warn("sketch tool: %s" % exc)
            self.tool = None

    def give_way(self):
        """A SKETCH command that waits for picks of its own starts (Offset, Mirror, the
        patterns, Move/Copy, Scale, a constraint): the tool running now ends first,
        Fission 180's or FreeCAD's, as in Fusion where any tool replaces the one before. A
        FreeCAD tool kept drawing under it: with Rectangle running, Offset waited for a
        curve while every click still went to the rectangle (Luca, 2026-11-02). What is
        selected stays selected (FreeCAD's stop clears it; the new command may use it);
        a half-drawn shape goes, as with Esc."""
        if self.closed:
            return
        self.stop_tool()
        self.line.stop()
        if self.infer is not None:
            self.infer.reset()
        try:
            from . import sketch_pick_ui, sketch_tools_ui

            sketch_tools_ui.stop_waiting()
            sketch_pick_ui.stop_waiting()
        except Exception as exc:
            warn("sketch tool: %s" % exc)
        if (
            not self.tool_running()
            and not self._spline_in_progress()
            and not self._spline_panel_shown()
        ):
            return
        kept = []
        try:
            for sel in Gui.Selection.getSelectionEx():
                for name in sel.SubElementNames or ("",):
                    kept.append((sel.DocumentName, sel.ObjectName, name))
        except Exception:
            kept = []
        spline = self.spline_drawn()
        try:
            Gui.runCommand("Sketcher_StopOperation")  # quits FreeCAD's tool
        except Exception as exc:
            warn("sketch tool: %s" % exc)
        if spline:
            self._drop_spline()  # a half-drawn spline goes, as with Esc
        _state["polygon"] = None if not self.polygon.active else _state["polygon"]
        try:
            if kept and not Gui.Selection.getSelectionEx():
                for doc, obj, name in kept:
                    Gui.Selection.addSelection(doc, obj, name)
        except Exception as exc:
            warn("sketch tool: %s" % exc)
        log("sketch: the running tool ended for the next command")

    def _spline_tool(self):
        """FreeCAD's spline tool is drawing (Fusion's Fit Point / Control Point Spline).

        A FreeCAD tool runs (its cursor is on the view) and it is the spline tool: the
        spline command was the last one started (past Finish Sketch, recorded before it
        runs), or FreeCAD's tool panel shows the spline tool's parameters (a spline
        started some other way: command search, FreeCAD's own toolbar or menu...)."""
        from . import recent

        try:
            if self.gl is None or self.gl.cursor().shape() == QtCore.Qt.ArrowCursor:
                return False
        except Exception:
            return False
        if recent.running_tool() in SPLINE_COMMANDS:
            return True
        return self._spline_panel_shown()

    def _spline_panel_shown(self):
        """FreeCAD's tool panel (TaskSketcherTool, shown only while a tool with parameters
        runs) has the spline tool's header ("B-Spline Parameters")."""
        try:
            panel = getattr(self, "_tool_panel", None)
            if panel is None or not _is_valid(panel):
                panel = None
                now = time.time()
                if now - getattr(self, "_tool_panel_looked", 0.0) < 0.5:
                    return False  # (looked a moment ago: not on every mouse move)
                self._tool_panel_looked = now
                main = Gui.getMainWindow()
                for widget in main.findChildren(QtWidgets.QWidget):
                    if widget.metaObject().className() == "SketcherGui::TaskSketcherTool":
                        panel = widget
                        break
                self._tool_panel = panel
            if panel is None or panel.isHidden():
                return False
            for child in panel.findChildren(QtWidgets.QWidget):
                text = child.property("text")
                if isinstance(text, str) and "spline" in text.lower():
                    return True
        except Exception as exc:
            warn("spline: %s" % exc)
        return False

    def _spline_points(self):
        """The loose points of the spline being drawn (sketch_spline.pending)."""
        from . import sketch_spline

        return sketch_spline.points_of(self.sketch, getattr(self, "_spline_from", None))

    def _spline_in_progress(self):
        """A spline's first click was seen (`_spline_from`) and its points are still loose
        in the sketch: it is being drawn, whatever the cursor or the last command say now
        (Luca, 2026-11-05, on Windows: OK in the right-click menu lost the spline and left
        its points; the green check vanished when the pointer went onto it)."""
        try:
            return getattr(self, "_spline_from", None) is not None and bool(self._spline_points())
        except Exception:
            return False

    def rescue_spline(self):
        """Safety net, from the green check's timer (every 100 ms): FreeCAD's spline tool
        is gone (no tool cursor on the view, no spline panel) for 3 ticks running, but the
        points of a spline drawn with it are still loose: the tool ended some way that did
        not make the spline. Fission 180 makes it from them (one point: it goes), so no
        orange points are ever left behind."""
        try:
            if self.closed or getattr(self, "_spline_from", None) is None:
                return
            if QtWidgets.QApplication.activePopupWidget() is not None:
                return  # the right-click menu is open: OK or Cancel is coming
            if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
                return
            cursor_on = self.gl is not None and self.gl.cursor().shape() != QtCore.Qt.ArrowCursor
            if (
                cursor_on
                or self._spline_panel_shown()
                or (self.tool is not None and self.tool.active)
            ):
                self._orphan_ticks = 0
                return
            points = self._spline_points()
            if not points:
                self._spline_from = None
                self._orphan_ticks = 0
                return
            self._orphan_ticks = getattr(self, "_orphan_ticks", 0) + 1
            if self._orphan_ticks < 3:
                return
            self._orphan_ticks = 0
            if len(points) >= 2:
                made = self._own_spline(points)
                log("spline: its tool ended without making it: made from its points (%s)" % made)
            else:
                from . import sketch_spline

                doc = self.doc
                doc.openTransaction("Cancel Spline")
                sketch_spline.remove_points(self.sketch, points)
                doc.commitTransaction()
            self._spline_from = None
        except Exception as exc:
            warn("spline: %s" % exc)
            self._spline_from = None

    def spline_drawn(self):
        """A spline is being drawn with FreeCAD's spline tool: the tool is recognised, or
        the points of its first clicks are there (the sure sign)."""
        return self._spline_in_progress() or self._spline_tool()

    def projection_refused(self, pos):
        """FreeCAD's Project tool (P) runs and the press at widget pixel `pos` is on a
        face or edge of the part whose edges the sketch has already (Auto project put the
        face's edges in, sketch_auto_project): FreeCAD would fail on the same face ("Link
        to Face5 already exists") or double the curves. True when the click is taken here:
        nothing new (a note beside the pointer), or only the edges still missing are
        projected (a face with a hole drilled after Auto project took it)."""
        from . import recent, sketch_auto_project

        last = recent.last()
        if last is None or last[0] not in PROJECT_COMMANDS or not self.tool_running():
            return False
        try:
            ratio = self.gl.devicePixelRatioF()
            info = self.view.getObjectInfo((pos.x() * ratio, (self.gl.height() - pos.y()) * ratio))
            if not info or not info.get("Component"):
                return False
            obj = self.doc.getObject(info.get("Object", ""))
            sub = info["Component"].rsplit(".", 1)[-1]
            if obj is None or obj is self.sketch:
                return False
            missing, have = sketch_auto_project.missing_edges(self.sketch, obj, sub)
            if not have:
                return False  # nothing of it in the sketch: FreeCAD's tool projects it
        except Exception as exc:
            warn("project: %s" % exc)
            return False
        from . import commands

        if not missing:
            commands.tell("Project: %s is in the sketch already (projected)." % sub)
            log("project: %s.%s is projected already; click ignored" % (obj.Label, sub))
            return True
        sketch = self.sketch

        def add():
            try:
                count = sketch_auto_project.add_edges(sketch, obj, missing)
                log(
                    "project: %d curve(s) of %s.%s added (the rest was projected already)"
                    % (count, obj.Label, sub)
                )
            except Exception as exc:
                warn("project: %s" % exc)

        QtCore.QTimer.singleShot(0, add)
        return True

    def open_spline_step(self):
        """FreeCAD's spline tool adds a point (or control circle) to the sketch at each
        click, meant to be kept in its undo step "Add Sketch B-Spline"; but FreeCAD's
        command runner closes that step as soon as the tool has started, so the points
        land outside any undo step (Esc could not take them back, and Ctrl+Z after the
        spline undid the step before it). Fission 180 opens the step again at the click."""
        try:
            if not self._spline_tool():
                return
            # the first click of a spline: its points are the curves added from here on
            if getattr(self, "_spline_from", None) is None or not self._spline_points():
                self._spline_from = len(self.sketch.Geometry)
            if App.getActiveTransaction() is None:
                App.setActiveTransaction(SPLINE_STEP)
        except Exception as exc:
            warn("spline: %s" % exc)

    def _commit_spline(self):
        """Fusion's Enter / OK / green check on a spline being drawn: the spline is made
        from the points clicked so far. FreeCAD's spline tool makes it on Esc (or its right
        click), which Fission 180 otherwise takes for "cancel": that Esc is handed to
        FreeCAD directly. Then it is checked: when no spline came of it, Fission 180 makes
        it from the points (sketch_spline.make_from_points) and FreeCAD's tool is stopped
        (its points are gone). Returns "freecad", "own" or None (nothing to make)."""
        gl = self.gl
        if gl is None or not _is_valid(gl):
            return None
        sketch = self.sketch
        points = self._spline_points()
        splines = _count_splines(sketch)
        before = len(sketch.Geometry)
        self.keys.pass_escape = True
        try:
            gl.setFocus()
            for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                event = QtGui.QKeyEvent(kind, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
                QtWidgets.QApplication.sendEvent(gl, event)
        finally:
            self.keys.pass_escape = False
        made = None
        if _count_splines(sketch) <= splines:
            # (a spline made a moment later must not be made twice: what is queued runs first)
            QtWidgets.QApplication.processEvents()
        if _count_splines(sketch) > splines:
            made = "freecad"
            log(
                "spline: made from the points clicked (%d curve(s) added)"
                % (len(sketch.Geometry) - before)
            )
        else:
            left = self._spline_points() or points
            if len(left) >= 2:
                made = self._own_spline(left)
            elif left:
                log("spline: only one point clicked: nothing to make")
        self._spline_from = None
        return made

    def _own_spline(self, points):
        """FreeCAD's tool did not make the spline: Fission 180 makes it from the points,
        in the spline's undo step, and stops FreeCAD's tool (it still held those points)."""
        from . import sketch_spline

        doc = self.doc
        sketch = self.sketch
        start = getattr(self, "_spline_from", None)
        made = sketch_spline.plan(sketch, points)  # before the tool stops (it may drop them)
        if made is None:
            return None
        try:
            Gui.runCommand("Sketcher_StopOperation")
        except Exception as exc:
            warn("spline: %s" % exc)
        try:
            still = sketch_spline.points_of(sketch, start) if start is not None else []
            still = [i for i in still if i in points] or (
                points if len(sketch.Geometry) == made["count"] else []
            )
            active = App.getActiveTransaction()
            name = active[0] if isinstance(active, (tuple, list)) else active
            mine = name != SPLINE_STEP
            if mine:
                doc.openTransaction(SPLINE_STEP)
            new = sketch_spline.build(sketch, made, remove=still)
            if mine:
                doc.commitTransaction()
            else:
                App.closeActiveTransaction(False)  # the step the points are in, with the spline
        except Exception as exc:
            warn("spline: could not make it from the points: %s" % exc)
            try:
                doc.abortTransaction()
            except Exception:
                pass
            return None
        return "own" if new is not None else None

    def _drop_spline(self, cancelled=True):
        """Fusion's Esc on a spline being drawn cancels that spline: the undo step that
        holds its points so far (open_spline_step) is dropped. Also run after Enter / OK
        (cancelled=False): FreeCAD opens a fresh step for the next spline, which would
        hold whatever the user changes next."""
        try:
            active = App.getActiveTransaction()
            name = active[0] if isinstance(active, (tuple, list)) else active
            if name == SPLINE_STEP:
                App.closeActiveTransaction(True)
                self.sketch.solve()
                if cancelled:
                    log("spline: the spline being drawn was cancelled")
            if cancelled:
                # points that were not in that step (its first click was not seen): they
                # go too; Fusion leaves nothing behind
                from . import sketch_spline

                left = self._spline_points()
                if left:
                    doc = self.doc
                    doc.openTransaction("Cancel Spline")
                    try:
                        sketch_spline.remove_points(self.sketch, left)
                    except Exception:
                        doc.abortTransaction()
                        raise
                    doc.commitTransaction()
        except Exception as exc:
            warn("spline: %s" % exc)
        self._spline_from = None

    def enter_finishes_tool(self):
        """Fusion: Enter while a tool runs and nothing was typed for the shape completes
        the tool. With a value typed, Enter draws the shape (field_key / enter_pressed)."""
        return (
            not self.closed
            and self.editor is None
            and not self._typed_since_commit
            and self.tool_running()
        )

    def finish_tool(self):
        """OK in the right-click menu, or Enter with nothing typed: the tool ends and what
        was drawn stays (a half-drawn shape has nothing to keep: FreeCAD drops it). Unlike
        Esc, the selection and the picked areas are left alone."""
        if self.closed or editing_sketch() is not self.sketch:
            return
        self._typed_since_commit = False
        if self.tool is not None and self.tool.active:
            # Fission 180's own tool: what can be kept is made (the conic's rho step)
            tool, self.tool = self.tool, None
            tool.finish()
            log("sketch: tool finished")
            return
        self.line.stop()
        if self.infer is not None:
            self.infer.reset()
        try:
            from . import sketch_pick_ui, sketch_tools_ui

            sketch_tools_ui.stop_waiting()
            sketch_pick_ui.stop_waiting()
        except Exception:
            pass
        _state["polygon"] = None if not self.polygon.active else _state["polygon"]
        spline = self.spline_drawn()
        if spline:
            try:
                self._commit_spline()
            except Exception as exc:
                warn("spline: %s" % exc)
        try:
            Gui.runCommand("Sketcher_StopOperation")  # quits FreeCAD's tool
        except Exception as exc:
            warn("sketch OK: %s" % exc)
        if spline:
            self._drop_spline(cancelled=False)  # the empty step opened for a next spline
        log("sketch: tool finished")

    def escape(self):
        """Fusion: Esc stops the tool; with no tool running it clears the selection.
        FreeCAD has already handled the key (and reset a half-drawn shape)."""
        if self.closed or editing_sketch() is not self.sketch:
            return
        self._typed_since_commit = False
        self.names.close()
        self.stop_tool()  # Fission 180's own tool: the half-drawn shape goes with it
        self.line.stop()
        if self.infer is not None:
            self.infer.reset()
        self.areas.clear()  # Fusion: Esc also drops the picked profiles
        try:
            from . import sketch_pick_ui, sketch_tools_ui

            sketch_tools_ui.stop_waiting()  # Offset waiting for a curve
            sketch_pick_ui.stop_waiting()  # Mirror, patterns... waiting for curves
            sketch_pick_ui.close_box()  # Rectangular Pattern panel: cancel
        except Exception:
            pass
        _state["polygon"] = None if not self.polygon.active else _state["polygon"]
        spline = self.spline_drawn()
        try:
            Gui.runCommand("Sketcher_StopOperation")  # quits the tool, clears the selection
        except Exception:
            pass
        if spline:
            self._drop_spline()
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass

    def _focus_changed(self, old, new):
        """A drawing tool's on-screen value field took the keyboard: Enter and Esc typed
        there must work as in Fusion too (FreeCAD keeps those keys in the field)."""
        try:
            if self.closed or not isinstance(new, QtWidgets.QAbstractSpinBox):
                return
            if not self._is_field(new):
                return
            new.installEventFilter(self.keys)  # Qt keeps one copy; it runs first
            self._fields = [f for f in self._fields if _is_valid(f) and not _same(f, new)]
            self._fields.append(new)
            if self._typed is not None and not _same(self._typed, new):
                self._typed = None  # another field: nothing typed into it yet
        except Exception as exc:
            warn("sketch value field: %s" % exc)

    def _is_field(self, widget):
        """One of FreeCAD's on-screen value fields of this 3D view."""
        try:
            mdi = self.viewer.parentWidget() if self.viewer is not None else None
            return mdi is not None and _same(widget.parentWidget(), mdi)
        except Exception:
            return False

    def _focused_field(self):
        widget = QtWidgets.QApplication.focusWidget()
        if isinstance(widget, QtWidgets.QAbstractSpinBox) and self._is_field(widget):
            return widget
        return None

    def field_key(self, field, event):
        """A key typed into an on-screen value field of a drawing tool."""
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            # Fusion: Esc stops the tool, also right after typing a value (FreeCAD keeps
            # Esc in the field for two seconds after a digit, then resets the shape).
            if not event.isAutoRepeat():
                self.escape()
            return True
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self._enter_follow or event.modifiers() & QtCore.Qt.ControlModifier:
                return False
            if self.enter_finishes_tool():
                # Fusion: Enter with nothing typed completes the tool (Autodesk's help on
                # lines: "Press Enter to complete the tool"); the drawn lines stay.
                if not event.isAutoRepeat():
                    QtCore.QTimer.singleShot(0, self.finish_tool)
                return True
            if not self._finishes_on_enter():
                return False
            self._accept_fields(field)
            return True
        if self.names.feeding:
            return False  # (our own keys: the number a typed name stands for, with its unit)
        if self.names.wants(field, event):
            # Fusion: a parameter's name (or a formula) typed into the box of the shape
            # being drawn; FreeCAD's box takes numbers only (sketch_field_names.py)
            self.names.start(field, event.text()[:1])
            return True
        if _is_value_key(event) or key in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete):
            self._typed = field  # the user is typing a value here
            self._typed_since_commit = True
            return False
        mods = event.modifiers() & ~(QtCore.Qt.ShiftModifier | QtCore.Qt.KeypadModifier)
        letter = event.text()[:1].isalpha() and mods == QtCore.Qt.NoModifier
        if letter:
            self.last_letter = "%s: %s" % (
                event.text()[:1],
                (
                    "after a value typed here, kept in the field"
                    if _same(self._typed, field)
                    else ("held down" if event.isAutoRepeat() else "a tool key?")
                ),
            )
        if letter and not event.isAutoRepeat() and not _same(self._typed, field):
            # Fusion: a tool's key switches tools at any time. FreeCAD would type the
            # letter into the field for two seconds after any value or Enter (a unit);
            # here only after a value typed into this field.
            command = _sketch_key(event)
            if command is not None:
                self.last_letter += " runs %s" % command
                QtCore.QTimer.singleShot(0, lambda: _run(command))
                return True
            name = _swallowed_shortcut(event)
            if name is not None:
                self.last_letter += " runs shortcut %s" % name
                QtCore.QTimer.singleShot(0, lambda: _run_shortcut(name))
                return True
            self.last_letter += " no tool has this key"
        return False

    def _finishes_on_enter(self):
        from . import recent

        last = recent.last()
        if last is None or last[0] not in ENTER_FINISHES:
            return False
        return self.gl is not None and self.gl.cursor().shape() != QtCore.Qt.ArrowCursor

    def _accept_fields(self, field):
        """FreeCAD's Ctrl+Enter in a value field: every field of the shape keeps what it
        shows (the typed value, or where the pointer is) and the shape is drawn."""
        self._enter_follow = True
        try:
            for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                event = QtGui.QKeyEvent(kind, QtCore.Qt.Key_Return, QtCore.Qt.ControlModifier, "\r")
                QtWidgets.QApplication.sendEvent(field, event)
        finally:
            self._enter_follow = False

    def enter_pressed(self):
        """Enter after typing a value while drawing. FreeCAD keeps the value and moves to
        the next on-screen field (the angle of a line, the height of a rectangle); Fusion
        draws the shape there, the pointer giving the rest. So when Enter did not finish
        the shape, the fields are accepted as they are for the user (Tab still goes to
        the next field). Enter typed in a field itself: field_key."""
        if self._enter_follow or self.closed:
            return
        try:
            if not self._finishes_on_enter():
                return
            count = len(self.sketch.Geometry)
            QtCore.QTimer.singleShot(0, lambda: self._finish_typed(count))
        except Exception as exc:
            warn("sketch Enter: %s" % exc)

    def _finish_typed(self, count):
        if self.closed or self.gl is None or not _is_valid(self.gl):
            return
        try:
            if len(self.sketch.Geometry) != count:
                return  # Enter finished the shape already
            if self.gl.cursor().shape() == QtCore.Qt.ArrowCursor:
                return
            field = self._focused_field()
            if field is not None:
                self._accept_fields(field)
                return
            self._enter_follow = True
            try:
                mods = QtCore.Qt.NoModifier
                for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                    event = QtGui.QKeyEvent(kind, QtCore.Qt.Key_Return, mods, "\r")
                    QtWidgets.QApplication.sendEvent(self.gl, event)
            finally:
                self._enter_follow = False
        except Exception as exc:
            warn("sketch Enter: %s" % exc)

    def double_clicked(self, pos):
        """A double click on a dimension edits it in place (no FreeCAD pop-up)."""
        try:
            pre = Gui.Selection.getPreselection()
            names = list(getattr(pre, "SubElementNames", []) or [])
            obj = getattr(pre, "Object", None)
        except Exception:
            return False
        if obj is not self.sketch:
            return False
        for name in names:
            short = name.rsplit(".", 1)[-1]
            if short.startswith("Constraint"):
                try:
                    index = int(short[len("Constraint") :]) - 1
                    c = self.sketch.Constraints[index]
                except Exception:
                    continue
                if c.Type in DIMENSIONAL:
                    if not c.Driving:
                        from . import commands

                        commands.tell(
                            "A driven dimension only shows the size: change the dimensions "
                            "that set it."
                        )
                        return True
                    QtCore.QTimer.singleShot(0, lambda: self.edit_dimension(index, pos))
                    return True
        try:
            # the text of a vertical or slanted dimension is turned along it: FreeCAD only
            # finds its middle (sf/book-sketch-b, the book report: "hard to hit")
            from . import sketch_dimension_tool

            found = sketch_dimension_tool.dimension_at(self, pos)
            if found is not None and self.sketch.Constraints[found].Driving:
                QtCore.QTimer.singleShot(0, lambda: self.edit_dimension(found, pos))
                return True
        except Exception as exc:
            warn("dimension box: %s" % exc)
        return False

    def chain_clicked(self, pos):
        """A double-click on a curve with no tool running selects its chain (Fusion)."""
        if self.editor is not None or self.tool_running():
            return False
        return self.select.double_clicked(pos)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stop_tool()
        self.line.stop()
        if self.infer is not None:
            try:
                self.infer.close()
            except Exception as exc:
                warn("sketch mode: %s" % exc)
        try:
            from . import sketch_pick_ui

            sketch_pick_ui.settle_box()
        except Exception as exc:
            warn("sketch mode: %s" % exc)
        try:
            self._refresh.stop()
        except Exception:
            pass
        self.close_editor(commit=True)
        remove_stray_editors(self.gl)
        parts = [self.polygon, self.areas, self.shading, self.display, self.fixed, self.check]
        parts.append(self.frames)
        parts.append(self.select)
        parts.append(self.right_angles)
        if self.sketch3d is not None:
            parts.append(self.sketch3d)
        for part in parts:
            try:
                if part is not None:
                    part.remove()
            except Exception as exc:
                warn("sketch mode: %s" % exc)
        try:
            QtWidgets.QApplication.instance().focusChanged.disconnect(self._focus_changed)
        except Exception:
            pass
        hooked = [(self.gl, self.filter), (self.viewer, self.keys)]
        hooked += [(field, self.keys) for field in self._fields]
        for widget, event_filter in hooked:
            if widget is not None and _is_valid(widget):
                try:
                    widget.removeEventFilter(event_filter)
                except Exception:
                    pass
        self._fields = []
        self._typed = None
        try:
            if self.palette is not None:
                self.palette.remove()
        except Exception:
            pass
        self.palette = None


class _KeyFilter(QtCore.QObject):
    """Keys while a sketch is open. On the 3D view widget (where a real keyboard sends
    them; keys aimed at the drawing area inside it arrive here too) and on FreeCAD's
    on-screen value fields while a drawing tool runs (they take the keyboard, and FreeCAD
    passes most other keys on to the view). Never blocks FreeCAD's own handling except
    for the keys Fusion gives another meaning."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.pass_escape = False  # an Esc meant for FreeCAD (finishing a spline)

    def eventFilter(self, obj, event):
        try:
            session = self.session
            if session.closed or self.pass_escape:
                return False
            kind = event.type()
            if kind not in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
                return False
            tool = session.tool
            if tool is not None and tool.active and tool.key(obj, event):
                return True  # Fission 180's own tool: its value boxes, Enter, its keys
            if isinstance(obj, QtWidgets.QAbstractSpinBox):
                if kind == QtCore.QEvent.KeyPress:
                    return session.field_key(obj, event)
                return False
            if kind == QtCore.QEvent.ShortcutOverride:
                # Typing a value: keys go into the value box / FreeCAD's on-screen fields,
                # not to shortcuts (FreeCAD's 0-6 turn the view, M moves...).
                if session.editor is not None or _is_value_key(event):
                    event.accept()
                    return True
                if _sketch_key(event) is not None:
                    event.accept()  # the key comes back as a KeyPress below
                    return True
                return False
            key = event.key()
            if session.editor is not None:
                return session.editor.key(event)
            command = _sketch_key(event)
            if command is not None:
                QtCore.QTimer.singleShot(0, lambda: _run(command))
                return True
            if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                from . import sketch_pick_ui

                if sketch_pick_ui.on_enter():
                    return True
                if session.enter_finishes_tool():
                    if not event.isAutoRepeat():
                        QtCore.QTimer.singleShot(0, session.finish_tool)
                    return True
                session.enter_pressed()
                return False
            if key == QtCore.Qt.Key_Escape:
                if not event.isAutoRepeat():
                    # Right away (a Qt key event, not a Coin callback): a timer could
                    # fire after the next key and stop the tool that key started.
                    session.escape()
                return False
            name = _swallowed_shortcut(event)
            if name is not None:
                QtCore.QTimer.singleShot(0, lambda: _run_shortcut(name))
                return True
        except Exception as exc:
            warn("sketch keys: %s" % exc)
        return False


class _ViewFilter(QtCore.QObject):
    """The mouse on the 3D view's drawing area while a sketch is open (keys: _KeyFilter).
    Never blocks FreeCAD's own handling except for the right click (marking menu)."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.right_pressed = None
        self.refused_release = False  # the release of a refused Project click
        self.chain_double = False  # a double-click's press on the line chain's end

    def eventFilter(self, obj, event):
        try:
            session = self.session
            if session.closed:
                return False
            kind = event.type()
            tool = session.tool
            if tool is not None and tool.active:
                # Fission 180's own drawing tool (sketch_draw.py) has the mouse first; the
                # inference layer below is FreeCAD's tools'
                if tool.mouse(obj, event):
                    return True
                if kind in _REDRAWS:
                    session.fixed.poke()
                if (
                    kind == QtCore.QEvent.MouseButtonPress
                    and event.button() == QtCore.Qt.RightButton
                ):
                    self.right_pressed = event.globalPosition().toPoint()
                    return True
                if (
                    kind == QtCore.QEvent.MouseButtonRelease
                    and event.button() == QtCore.Qt.RightButton
                ):
                    start, self.right_pressed = self.right_pressed, None
                    pos = event.globalPosition().toPoint()
                    if start is not None and (pos - start).manhattanLength() <= 6:
                        QtCore.QTimer.singleShot(0, lambda: _open_marking(pos))
                    return True
                if kind == QtCore.QEvent.Leave:
                    session.areas.left()
                return False
            if kind == QtCore.QEvent.MouseButtonDblClick and event.button() == QtCore.Qt.LeftButton:
                if session.line.at_current(event.position().toPoint()):
                    # Fusion: a double-click on the end of the line being drawn ends the
                    # chain; the Line tool stays on. But a second press that comes soon
                    # after the click and then DRAGS is Fusion's tangent arc (press and
                    # drag on the line's end), which a hand does without waiting out the
                    # double-click time (the book's Carabiner: "no arc" with a real
                    # mouse): the press goes to the inference like any press there, and
                    # only a release without a drag ends the chain. FreeCAD must never
                    # get this second press as another click on that point.
                    self.chain_double = True
                    taken = session.infer is not None and session.infer.mouse(obj, event)
                    if not taken:
                        self.chain_double = False
                        QtCore.QTimer.singleShot(0, session.line.break_chain)
                    return True
            if self.chain_double and (
                (kind == QtCore.QEvent.MouseMove and not (event.buttons() & QtCore.Qt.LeftButton))
                or kind == QtCore.QEvent.MouseButtonPress
            ):
                # the release of that double-click never came (a test's double-click
                # sends none; a release outside the window): it was a double-click
                self.chain_double = False
                try:
                    session.infer.arc.reset()
                except Exception as exc:
                    warn("sketch view: %s" % exc)
                session.line.break_chain()
            if (
                kind == QtCore.QEvent.MouseButtonRelease
                and event.button() == QtCore.Qt.LeftButton
                and self.chain_double
            ):
                self.chain_double = False
                dragged = False
                try:
                    dragged = session.infer.arc.state == "dragging"
                    session.infer.mouse(obj, event)  # places the arc, or lets go
                except Exception as exc:
                    warn("sketch view: %s" % exc)
                if not dragged:
                    QtCore.QTimer.singleShot(0, session.line.break_chain)
                return True
            if kind in _PRESSES and event.button() == QtCore.Qt.LeftButton:
                if session.projection_refused(event.position().toPoint()):
                    self.refused_release = True
                    return True
            if (
                kind == QtCore.QEvent.MouseButtonRelease
                and event.button() == QtCore.Qt.LeftButton
                and self.refused_release
            ):
                self.refused_release = False
                return True
            if kind == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                session.open_spline_step()  # (FreeCAD's spline tool: the points' undo step)
            # Fusion's inference (sketch_infer.py) may hand FreeCAD a copy of the event
            # with the point moved onto a guide; the copy comes back through here.
            if session.infer is not None and session.infer.mouse(obj, event):
                return True
            if kind in _REDRAWS:
                session.fixed.poke()  # FreeCAD recolours curves after these
                session.signs.poke()  # ...and may write the dimensions' texts again
            if kind == QtCore.QEvent.MouseMove:
                if event.buttons() == QtCore.Qt.NoButton:
                    session.areas.moved(event.position().toPoint())
                elif event.buttons() & QtCore.Qt.LeftButton:
                    session.select.moved(event)  # a box drag (Fusion's modifiers)
                return False
            if kind == QtCore.QEvent.Leave:
                session.areas.left()
                if session.infer is not None:
                    session.infer.leave()  # no guide or mark stays behind
                return False
            if kind == QtCore.QEvent.MouseButtonPress:
                # (a double-click whose release never came: Qt's test clicks send none)
                session.select.swallow_release = False
                if event.button() == QtCore.Qt.LeftButton:
                    # (before the value box closes: that click is not a pick)
                    session.areas.pressed(event.position().toPoint(), event.modifiers())
                    if session.editor is None and not session.tool_running():
                        session.select.pressed(event)
                session.last_press = event.position().toPoint()
                if session.editor is not None and not session.editor.underMouse():
                    QtCore.QTimer.singleShot(0, lambda: session.close_editor(commit=True))
                if event.button() == QtCore.Qt.RightButton:
                    # Fusion: a right click in a sketch opens the sketch's marking menu
                    self.right_pressed = event.globalPosition().toPoint()
                    return True
            elif kind == QtCore.QEvent.MouseButtonRelease:
                if event.button() == QtCore.Qt.LeftButton:
                    if session.select.swallow_release:
                        # the release of a double-click that selected a chain: FreeCAD
                        # would toggle the clicked curve off again
                        session.select.swallow_release = False
                        return True
                    session.areas.released(event.position().toPoint())
                    session.select.released(event)
                if event.button() == QtCore.Qt.RightButton and self.right_pressed is not None:
                    start, self.right_pressed = self.right_pressed, None
                    pos = event.globalPosition().toPoint()
                    if (pos - start).manhattanLength() <= 6:
                        from . import sketch_marking

                        QtCore.QTimer.singleShot(0, lambda: sketch_marking.open_at(pos))
                    return True
            elif kind == QtCore.QEvent.MouseButtonDblClick:
                if event.button() == QtCore.Qt.LeftButton:
                    pos = event.position().toPoint()
                    return session.double_clicked(pos) or session.chain_clicked(pos)
        except Exception as exc:
            warn("sketch view: %s" % exc)
        return False


_PRESSES = (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonDblClick)
_REDRAWS = (
    QtCore.QEvent.MouseMove,
    QtCore.QEvent.MouseButtonPress,
    QtCore.QEvent.MouseButtonRelease,
    QtCore.QEvent.Leave,
)


def _tool_undone(tool):
    """Undo / redo while Fission 180's own tool runs (from a timer)."""
    try:
        if tool.active:
            tool.undone()
    except Exception as exc:
        warn("sketch tool after undo: %s" % exc)


def _open_marking(pos):
    """The sketch's right-click menu at the global position (from a timer)."""
    try:
        from . import sketch_marking

        sketch_marking.open_at(pos)
    except Exception as exc:
        warn("sketch marking menu: %s" % exc)


# Keys that mean something else in a sketch than on the part (Fusion): M moves/copies
# sketch curves, Del deletes the selected sketch curves (whatever the part's Move/Delete
# commands do), Ctrl+C / Ctrl+X / Ctrl+V copy, cut and paste sketch curves (FreeCAD's
# own keys for them only work with its menu bar, which Fission 180 hides).
NONE, CTRL = QtCore.Qt.NoModifier, QtCore.Qt.ControlModifier
SKETCH_KEYS = {
    (QtCore.Qt.Key_M, NONE): "Fission180_SketchMove",
    (QtCore.Qt.Key_Delete, NONE): "Std_Delete",
    (QtCore.Qt.Key_C, CTRL): "Sketcher_CopyClipboard",
    (QtCore.Qt.Key_X, CTRL): "Sketcher_Cut",
    (QtCore.Qt.Key_V, CTRL): "paste",
}


LABELS = {"Fission180_SketchMove": "Move/Copy"}
NEEDS_CURVES = {"Sketcher_CopyClipboard": "Ctrl+C", "Sketcher_Cut": "Ctrl+X"}


def _sketch_key(event):
    if event.isAutoRepeat():
        return None
    mods = event.modifiers() & ~QtCore.Qt.KeypadModifier
    for (key, wanted), command in SKETCH_KEYS.items():
        if event.key() == key and mods == wanted:
            return command
    return None


def _swallowed_shortcut(event):
    """A Fission 180 key (L, C, D...) that reached the 3D view as a plain key press. Qt runs
    shortcuts before keys arrive, so this only happens when a drawing tool's value field
    had the keyboard and FreeCAD passed the key on to the view: Fusion still switches to
    that tool."""
    if event.isAutoRepeat() or _is_value_key(event):
        return None
    if event.key() in (QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control, QtCore.Qt.Key_Alt):
        return None
    try:
        from . import shortcuts

        mods = event.modifiers() & ~QtCore.Qt.KeypadModifier
        combo = QtCore.QKeyCombination(mods, QtCore.Qt.Key(event.key()))
        text = QtGui.QKeySequence(combo).toString(QtGui.QKeySequence.PortableText)
        return shortcuts.bound_keys().get(shortcuts.normalise(text))
    except Exception:
        return None


def _run_shortcut(name):
    """What the shortcut itself does (shortcuts.py): the command, remembered for Repeat."""
    try:
        from . import recent

        cmd = Gui.Command.get(name)
        if cmd is None or (hasattr(cmd, "isActive") and not cmd.isActive()):
            return
        label = name
        try:
            label = (cmd.getInfo().get("menuText") or name).replace("&", "")
        except Exception:
            pass
        recent.record(name, label)
        Gui.runCommand(name)
    except Exception as exc:
        warn("%s: %s" % (name, exc))


def _run(command):
    try:
        from . import commands, recent

        if command == "paste":
            paste()
            return
        if command in NEEDS_CURVES:
            sketch = editing_sketch()
            if sketch is None or not _selected_curves(sketch):
                commands.tell("Select sketch curves first, then %s." % NEEDS_CURVES[command])
                return
        if command in LABELS:
            recent.record(command, LABELS[command])
        if command == "Std_Delete" and _delete_projected():
            return  # (only projected curves were selected: done)
        Gui.runCommand(command)
    except Exception as exc:
        warn("%s: %s" % (command, exc))


def _delete_projected():
    """Del with projected (purple) curves selected. FreeCAD removes a projected curve by
    removing the reference it came from, and a face's reference carries all its edges:
    with the four Auto-projected edges of a face selected, the first delete took all four
    and the other three failed with "Not able to delete an external geometry with the
    given index" in the Report view. Here each reference is removed once, in one undo
    step, and the projected curves are taken out of the selection before FreeCAD's own
    Delete does the rest. True when nothing else was selected."""
    import Sketcher

    sketch = editing_sketch()
    if sketch is None:
        return False
    names = []
    for sel in Gui.Selection.getSelectionEx():
        if sel.Object is sketch:
            names += [n.rsplit(".", 1)[-1] for n in sel.SubElementNames]
    projected = [n for n in names if n.startswith("ExternalEdge")]
    if not projected:
        return False
    others = [n for n in names if not n.startswith("ExternalEdge")]

    def ids_now():
        return [Sketcher.ExternalGeometryFacade(g).Id for g in list(sketch.ExternalGeo)[2:]]

    now = ids_now()
    wanted = set()
    for name in projected:
        try:
            wanted.add(now[int(name[len("ExternalEdge") :]) - 1])
        except (ValueError, IndexError):
            continue
    doc = sketch.Document
    doc.openTransaction("Delete Projected Curves")
    try:
        for _ in range(len(wanted) + 1):
            now = ids_now()
            left = [i for i, ident in enumerate(now) if ident in wanted]
            if not left:
                break
            sketch.delExternal(left[-1])
        sketch.solve()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    Gui.Selection.clearSelection()
    for name in others:
        Gui.Selection.addSelection(doc.Name, sketch.Name, name)
    log("sketch: %d projected curve(s) deleted" % len(wanted))
    return not others


def _selected_curves(sketch):
    from .sketch_tools_ui import selected_curves

    return selected_curves(sketch)


def paste():
    """Ctrl+V in a sketch: FreeCAD pastes the copied curves on top of the originals;
    Fusion then lets you place them. The pasted curves are selected and Fission 180's
    Move/Copy starts with them (its arrows, turn handle and fields; Esc leaves them where
    they are). It handed them to FreeCAD's Translate before 0.1.0-beta.3.3.7."""
    from . import commands

    sketch = editing_sketch()
    if sketch is None:
        return
    before = len(sketch.Geometry)
    Gui.runCommand("Sketcher_Paste")
    new = list(range(before, len(sketch.Geometry)))
    if not new:
        commands.tell("Nothing to paste: select sketch curves and press Ctrl+C first.")
        return
    Gui.Selection.clearSelection()
    for index in new:
        Gui.Selection.addSelection(sketch.Document.Name, sketch.Name, "Edge%d" % (index + 1))

    def place():
        _run("Fission180_SketchMove")
        # said once the tool's panel has settled (its start hid an earlier tip)
        QtCore.QTimer.singleShot(
            150,
            lambda: commands.tell(
                "Pasted: drag the arrows (or type X / Y Distance) to place it, then OK."
            ),
        )

    QtCore.QTimer.singleShot(0, place)


VALUE_KEYS = {getattr(QtCore.Qt, "Key_%d" % d) for d in range(10)} | {
    QtCore.Qt.Key_Period,
    QtCore.Qt.Key_Comma,
    QtCore.Qt.Key_Minus,
}


def _is_value_key(event):
    """A digit (or . , -) typed without Ctrl/Alt: part of a value, never a shortcut
    while sketching (Fusion has no number shortcuts)."""
    mods = event.modifiers() & ~(QtCore.Qt.KeypadModifier | QtCore.Qt.ShiftModifier)
    return event.key() in VALUE_KEYS and mods == QtCore.Qt.NoModifier


# -- the value box for dimensions -------------------------------------------------------
EDITOR_NAME = "Fission180DimensionEditor"


def _constraint_key(c):
    """What tells one dimension from another (its index changes when others go)."""
    return tuple(
        getattr(c, name, None)
        for name in (
            "Type",
            "First",
            "FirstPos",
            "Second",
            "SecondPos",
            "Third",
            "ThirdPos",
            "Name",
        )
    )


def remove_stray_editors(gl, keep=None):
    """Delete dimension boxes left on the 3D view by an earlier sketch (or an earlier
    Fission 180), except `keep`. They are children of the view, so they outlive the sketch."""
    if gl is None or not _is_valid(gl):
        return 0
    removed = 0
    try:
        for box in gl.findChildren(QtWidgets.QFrame, EDITOR_NAME):
            if keep is not None and _same(box, keep):
                continue
            box.hide()
            box.deleteLater()
            removed += 1
    except Exception as exc:
        warn("dimension box: %s" % exc)
    return removed


def _drop_redo(doc, sketch, step):
    """Forget the Redo of a refused step (taken back with Undo: FreeCAD would offer it
    again). FreeCAD clears the Redo list when a step starts recording, so a throw-away step
    records one change (the sketch's description, put back by the abort). Only when the
    refused step is all there is to Redo: the commit had cleared the rest already."""
    if list(doc.RedoNames) != [step]:
        return
    label = sketch.Label2
    doc.openTransaction("Fission 180")
    try:
        sketch.Label2 = label + " "
    finally:
        doc.abortTransaction()
    if sketch.Label2 != label:
        sketch.Label2 = label


class DimensionEditor(theme.OwnBackground, QtWidgets.QFrame):
    """Fusion's in-place dimension box: shows the measured value selected; type a
    value or an expression (=width*2), Enter keeps it, Esc keeps the measured one."""

    def __init__(self, session, index, pos, centred=False):
        super().__init__(session.gl)
        self.session = session
        self.sketch = session.sketch
        self.index = index
        self._done = False
        self.just_placed = False  # Sketch Dimension placed it a moment ago (its first value)
        try:  # which dimension this is, to find it again if the sketch changes meanwhile
            self.identity = _constraint_key(self.sketch.Constraints[index])
        except Exception:
            self.identity = None
        self.setObjectName(EDITOR_NAME)
        self.setStyleSheet(
            "#%s { background: #f5f5f5; border: 1px solid #3fa9f5;" % EDITOR_NAME
            + " border-radius: 2px; }"
            " QLineEdit { background: #ffffff; color: #111111; border: none; padding: 1px 3px;"
            " selection-background-color: #3fa9f5; selection-color: #ffffff; }"
            " QLabel { color: #b00020; background: #f5f5f5; padding: 1px 3px; }"
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        self.edit = QtWidgets.QLineEdit(self)
        self.edit.setObjectName("Fission180DimensionValue")
        self.edit.setMinimumWidth(90)
        self.message = QtWidgets.QLabel("", self)
        self.message.setWordWrap(True)
        self.message.hide()
        # a dimension that was given a name (`Width = 12`) IS that parameter: the hint says
        # what a number typed here will do (sketch_named_dimensions.py)
        self.hint = QtWidgets.QLabel("", self)
        self.hint.setObjectName("Fission180DimensionHint")
        self.hint.setStyleSheet("color: #444444;")
        self.hint.setWordWrap(True)
        self.hint.hide()
        layout.addWidget(self.edit)
        layout.addWidget(self.hint)
        layout.addWidget(self.message)
        self.edit.setText(self._current_text())
        self._show_owner()
        self.edit.selectAll()
        self.edit.returnPressed.connect(lambda: self.finish(True))
        self.adjustSize()
        if centred:
            x, y = pos.x() - self.width() // 2, pos.y() - self.height() // 2
        else:
            x, y = pos.x() + 12, pos.y() - self.height() - 6
        x = max(0, min(x, session.gl.width() - self.width() - 4))
        y = max(0, min(y, session.gl.height() - self.height() - 4))
        self.move(x, y)
        self.show()
        self.raise_()
        self.edit.setFocus()
        self._fresh = True
        self.edit.textEdited.connect(self._edited)
        log("dimension: type a value and press Enter")

    def owner(self):
        """The user parameter this dimension IS (it was named here: `Width = 12`), or
        None."""
        try:
            from . import sketch_named_dimensions

            return sketch_named_dimensions.owned(self.sketch, self.index)
        except Exception:
            return None

    def _scale_at_first(self, q):
        """Fusion's "Scale entire sketch at first dimension": the value typed into the
        dimension Sketch Dimension has just placed, when it is the sketch's first size,
        scales the whole sketch (sketch_first_dimension.py). Inside apply()'s undo step.
        True when it scaled."""
        if not self.just_placed:
            return False
        from . import sketch_first_dimension as first

        if not first.applies(self.sketch, self.index):
            return False
        old = self.sketch.getDatum(self.index).getValueAs("mm").Value
        k = first.factor(old, q.getValueAs("mm").Value)
        if k is None:
            return False
        first.scale(self.sketch, k)
        from . import commands

        commands.tell(
            "The whole sketch was scaled to this first dimension (Preferences > Design > "
            "Scale entire sketch at first dimension)."
        )
        return True

    def _show_owner(self):
        name = self.owner()
        if name is None:
            return
        try:
            q = self.sketch.getDatum(self.index)
            if self.is_angle():
                now = "%g deg" % round(abs(q.getValueAs("deg").Value), 6)
            else:
                from . import browser_core

                unit = browser_core.doc_length_unit(self.sketch.Document)
                per = browser_core.MM_PER_UNIT.get(unit, 1.0)
                now = "%g %s" % (round(abs(q.getValueAs("mm").Value) / per, 6), unit)
            self.hint.setText(
                "%s = %s. This dimension is %s: type a number to change %s."
                % (name, now, name, name)
            )
            self.hint.show()
        except Exception as exc:
            warn("dimension box: %s" % exc)

    def _edited(self, _text):
        self._fresh = False

    def closed(self):
        return self._done

    def reason(self):
        """The message the box shows (why the value cannot be set), or ''."""
        try:
            return self.message.text() if self.message.isVisible() else ""
        except Exception:
            return ""

    def discard(self):
        """Close without setting anything, whatever happens."""
        self._done = True
        if self.session.editor is self:
            self.session.editor = None
        try:
            self.hide()
            self.deleteLater()
        except Exception:
            pass

    def _follow(self):
        """The index of this box's dimension now, or None when it is gone. The sketch can
        change while the box is open (a curve deleted, Undo): its index may then point at
        another dimension or past the end ("Invalid constraint index")."""
        try:
            constraints = self.sketch.Constraints
        except Exception:
            return None
        if self.identity is None:
            return self.index if 0 <= self.index < len(constraints) else None
        if (
            0 <= self.index < len(constraints)
            and _constraint_key(constraints[self.index]) == self.identity
        ):
            return self.index
        for i, c in enumerate(constraints):
            if _constraint_key(c) == self.identity:
                return i
        return None

    def _constraint(self):
        return self.sketch.Constraints[self.index]

    def is_angle(self):
        return self._constraint().Type == "Angle"

    def _current_text(self):
        try:
            from . import parameters

            expressions = parameters.expressions_of(self.sketch)
            path = ".Constraints[%d]" % self.index
            if path in expressions:
                # the formula as the person writes it (Fusion shows "Arm_Length", not
                # FreeCAD's "=Parameters.Arm_Length": book parity report, Drone)
                from . import parameters_core

                return parameters_core.from_freecad(expressions[path])
            q = self.sketch.getDatum(self.index)
            if self.is_angle():
                return "%g deg" % round(q.getValueAs("deg").Value, 6)
            # in the design's units, like Fusion (an inch design showed mm: beta 3 VEX QA)
            from . import browser_core

            unit = browser_core.doc_length_unit(self.sketch.Document)
            per = browser_core.MM_PER_UNIT.get(unit, 1.0)
            return "%g %s" % (round(q.getValueAs("mm").Value / per, 6), unit)
        except Exception:
            return ""

    def key(self, event):
        """A key pressed on the 3D view while the box is open: it goes into the box.
        With the keyboard in the box itself, the keys the box does not use (Esc, arrows
        up/down...) come here on their way up: never sent back to it (they would come
        straight back here, again and again)."""
        key = event.key()
        own = _is_valid(self.edit) and self.edit.hasFocus()
        if key == QtCore.Qt.Key_Escape:
            QtCore.QTimer.singleShot(0, lambda: self.session.close_editor(commit=False))
            return True
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if not own:  # in the box, Enter already finished it (returnPressed)
                QtCore.QTimer.singleShot(0, lambda: self.finish(True))
            return True
        if own:
            return True
        if self._fresh and event.text():
            self.edit.selectAll()  # the first key replaces the shown value, as in Fusion
        self._fresh = False
        copy = QtGui.QKeyEvent(
            QtCore.QEvent.KeyPress, key, event.modifiers(), event.text(), False, 1
        )
        QtWidgets.QApplication.sendEvent(self.edit, copy)
        return True

    def _value(self, text):
        """Parse the typed text: (quantity or None, expression or None). Raises
        ValueError with a message for the box when the value is not possible.

        Read the one way every value box reads (parameters.read, wave 7): a number is in
        the design's units, a parameter name or a formula needs no leading "=" (Fusion's
        way: `Head_Length`, `Support_Width/2`, `9 * 1.02`; a bare name used to keep the
        measured value), and `Name = value` makes the user parameter Name and uses it."""
        from . import parameters, parameters_core

        text = text.strip()
        angle = self.is_angle()
        kind = "angle" if angle else "length"
        doc = self.sketch.Document
        name, rest = parameters_core.split_assignment(text)
        if name is not None:
            # checked here; made inside the undo step (apply), so a refusal leaves nothing
            parameters.check_new(doc, name)
            parameters.read(doc, rest, kind)
            return None, text
        got = parameters.read(doc, text, kind)
        if not got.plain:
            return None, got.formula
        value = got.value
        # Fusion refuses sizes of 0 or less: a dimension of 0 collapses the curve (FreeCAD's
        # solver then fails and the sketch breaks).
        if value <= 1e-7:
            raise ValueError(
                "The value must be more than 0. To make two things meet use Coincident; to "
                "line them up, Horizontal/Vertical or Collinear."
            )
        if angle and value >= 360.0:
            raise ValueError("The angle must be less than 360 deg.")
        try:
            current = self.sketch.getDatum(self.index).Value
        except Exception:
            current = 1.0
        if current < 0 and self._constraint().Type in ("DistanceX", "DistanceY", "Angle"):
            # FreeCAD keeps the direction in the sign; the user types the size.
            value = -value
        return App.Units.Quantity("%r %s" % (value, "deg" if angle else "mm")), None

    def keyPressEvent(self, event):
        """Enter typed in the box finished it (returnPressed, inside the box's own key
        handling); QLineEdit then lets the key go on up to the 3D view, where Enter would
        complete the running tool (Fusion's Enter, _KeyFilter). It was the box's: stop it."""
        try:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and self._done:
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)

    def finish(self, commit):
        if self._done:
            return
        if not _is_valid(self):
            self._done = True
            return
        if commit and not self.apply():
            return  # stay open with the message, like Fusion
        self._done = True
        if self.session.editor is self:
            self.session.editor = None
        try:
            self.hide()
            self.deleteLater()
        except Exception:
            pass
        try:
            gl = self.session.gl
            if gl is not None and _is_valid(gl):
                gl.setFocus()
        except Exception:
            pass

    def apply(self):
        """Set the dimension; False (and a message) when the value is not possible."""
        index = self._follow()
        if index is None:
            log("dimension box closed: its dimension changed or no longer exists")
            if not self._fresh and self.edit.text().strip():
                try:
                    from . import commands

                    commands.tell(
                        "The sketch changed while the dimension box was open: "
                        "the value was not set."
                    )
                except Exception:
                    pass
            return True  # nothing left to set
        self.index = index
        text = self.edit.text()
        if text.strip() == self._current_text().strip() or not text.strip():
            return True
        doc = self.sketch.Document
        try:
            q, expression = self._value(text)
        except Exception as exc:
            self._error(str(exc) if isinstance(exc, ValueError) else "Not a value: %s" % text)
            return False
        if not self._constraint().Driving:
            self._error(
                "A driven dimension only shows the size: change the dimensions that set it."
            )
            return False
        from . import sketch_explain as explain
        from . import sketch_explain_core as explain_core

        culprits = []
        scaled = False
        broken_before = _broken_state(self.sketch)
        owner = self.owner()
        if owner is not None and expression is not None:
            from . import parameters_core

            if parameters_core.split_assignment(expression)[0] is not None:
                owner = None  # `Other = value`: the dimension gets a new name, as typed
        doc.openTransaction("Edit Dimension")
        try:
            if owner is not None:
                # Fusion: the dimension IS the parameter it was named (`Width = 12`): what
                # is typed into it later is Width's new value, and everything that uses
                # Width follows (it used to unlink the dimension: params' known issue)
                from . import parameters

                kind = "angle" if self.is_angle() else "length"
                if expression is not None:
                    parameters.read(doc, expression, kind, skip=owner)  # (not itself)
                    new = expression
                else:
                    new = "%r %s" % (abs(q.Value), "deg" if kind == "angle" else "mm")
                parameters.set_user(doc, owner, new)
                holder = parameters.container(doc)
                if holder is not None:
                    holder.recompute()
                self.sketch.recompute()
                kind = self._constraint().Type
                got = self.sketch.getDatum(self.index).getValueAs("mm").Value
                if kind != "Angle" and explain_core.bad_size(kind, got):
                    raise ValueError(
                        "The value must be more than 0 (%s would be %s mm)."
                        % (owner, explain_core._number(got))
                    )
                log("dimension: %s is now %s" % (owner, text.strip()))
            elif expression is not None:
                from . import parameters

                # Fusion's formula (width*2, Arm_Length + 5, Name = value) in FreeCAD's
                # spelling, its numbers in the design's units; `Name = value` makes the
                # parameter here, inside this undo step. A formula that cannot be computed
                # (an unknown name) is said, not kept (parameters.read raises).
                kind = "angle" if self.is_angle() else "length"
                made = parameters.read(doc, expression, kind, create=True)
                formula = made.freecad
                if made.created:
                    from . import sketch_named_dimensions

                    sketch_named_dimensions.remember(self.sketch, made.created)
                # (bound the way FreeCAD renumbers it when a constraint before it is
                # deleted: parameters.set_expression, bug 3 of the book parity report)
                parameters.set_expression(self.sketch, ".Constraints[%d]" % self.index, formula)
                self.sketch.recompute()
                # a formula is checked like a typed value: no size of 0 or less
                kind = self._constraint().Type
                got = self.sketch.getDatum(self.index).getValueAs("mm").Value
                if kind != "Angle" and explain_core.bad_size(kind, got):
                    raise ValueError(
                        "The value must be more than 0 (the formula gives %s mm)."
                        % explain_core._number(got)
                    )
            else:
                from . import parameters

                path = ".Constraints[%d]" % self.index
                if path in parameters.expressions_of(self.sketch):
                    # a number typed over a formula takes its place (found by
                    # book_sketch_c_dimension: the formula stayed bound under the number,
                    # and the next recompute put the parameter's value back)
                    parameters.set_expression(self.sketch, path, None)
                scaled = self._scale_at_first(q)
                self.sketch.setDatum(self.index, q)
            if self.sketch.solve() != 0:
                raise ValueError(CONFLICT)
        except Exception as exc:
            # FreeCAD's failed solve still knows what fought the value (the value itself is
            # already put back): read it before the step is taken back
            try:
                culprits = explain.conflict_culprits(self.sketch, [self.index])
            except Exception:
                culprits = []
            doc.abortTransaction()
            try:
                self.sketch.solve()
                if _broken_state(self.sketch) and not broken_before:
                    # the try's recompute failed: the sketch is fine again, and says so
                    self.sketch.recompute()
            except Exception:
                pass
            if culprits:
                text, _count = explain.words(self.sketch, culprits)
                self._error(explain_core.value_conflict(text))
                log("dimension: %s: conflicts with %s" % (_short(exc), text))
                explain.highlight(self.sketch, culprits)
            else:
                self._error(_plain(exc))
            return False
        doc.commitTransaction()
        log("dimension set to %s" % text.strip())
        if scaled:
            QtCore.QTimer.singleShot(0, self.session.show_all_if_outside)
        return True

    def _error(self, text):
        self.message.setText(text)
        self.message.show()
        self.adjustSize()
        self.edit.setFocus()
        self.edit.selectAll()


def _broken_state(obj):
    return bool({"Invalid", "Error"} & set(obj.State))


def _short(exc):
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return text[:160]


CONFLICT = "That value does not fit the other dimensions and constraints of the sketch."

# FreeCAD's solver texts, said the way a Fusion user needs them. FreeCAD 1.1.4's setDatum says
# "Negative datum values are not valid" for any over-constrained result (its error code -4),
# also for a positive value: sizes of 0 or less never get that far (DimensionEditor._value).
PLAIN = (
    ("conflicting", CONFLICT),
    ("Negative datum", CONFLICT),
    # setDatum's words for a solve that found no solution (its code -1); the index is valid
    ("Invalid constraint index", CONFLICT),
    ("is invalid", "That value is not possible here."),
    ("redundant", "That size is already set by other dimensions."),
)


def _plain(exc):
    text = _short(exc)
    for needle, said in PLAIN:
        if needle.lower() in text.lower():
            return said
    return text


# -- sketch fillet radius -------------------------------------------------------------------
FILLET_COMMANDS = ("Sketcher_CreateFillet", "Sketcher_CompCreateFillets")


class FilletRadius:
    """Fusion's sketch fillet asks for the radius. FreeCAD's fillet tool rounds the
    clicked corner with a radius taken from the mouse; the new arc then gets a radius
    dimension and the value box opens on it (type 5, Enter)."""

    def __init__(self, session):
        self.session = session
        self.seen = len(session.sketch.Geometry)

    def committed(self):
        QtCore.QTimer.singleShot(0, self._check)

    def _check(self):
        session = self.session
        if session.closed:
            return
        try:
            import Sketcher

            from . import recent

            sketch = session.sketch
            count = len(sketch.Geometry)
            new = list(range(self.seen, count))
            self.seen = count
            last = recent.last()
            if not new or last is None or last[0] not in FILLET_COMMANDS:
                return
            arcs = [i for i in new if sketch.Geometry[i].TypeId == "Part::GeomArcOfCircle"]
            if len(arcs) != 1 or session.editor is not None:
                return
            arc = arcs[0]
            doc = session.doc
            doc.openTransaction("Fillet Radius")
            try:
                index = sketch.addConstraint(
                    Sketcher.Constraint("Radius", arc, sketch.Geometry[arc].Radius)
                )
                sketch.solve()
            except Exception:
                doc.abortTransaction()
                raise
            doc.commitTransaction()
            if not session._make_driven_if_redundant(index):
                session.edit_dimension(index)
        except Exception as exc:
            warn("fillet radius: %s" % exc)


# -- profile shading ----------------------------------------------------------------------
class ProfileShading:
    """Light-blue fill of the closed regions of the open sketch (Fusion's profiles)."""

    FILL = (0.45, 0.77, 1.0)
    TRANSPARENCY = 0.72

    def __init__(self, session):
        from pivy import coin

        self.coin = coin
        self.session = session
        self.visible = True
        self.root = coin.SoSeparator()
        self.root.setName("Fission180SketchProfiles")
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        # Drawn a hair in front of the part's faces (FreeCAD pushes those back), so a
        # sketch on a face shows its profiles; the sketch curves sit higher still.
        offset = coin.SoPolygonOffset()
        offset.factor = -1.0
        offset.units = -1.0
        self.root.addChild(offset)
        hints = coin.SoShapeHints()
        hints.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
        self.root.addChild(hints)
        self.transform = coin.SoTransform()
        self.root.addChild(self.transform)
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*self.FILL)
        material.emissiveColor.setValue(*[c * 0.5 for c in self.FILL])
        material.transparency.setValue(self.TRANSPARENCY)
        self.root.addChild(material)
        self.coords = coin.SoCoordinate3()
        self.faces = coin.SoIndexedFaceSet()
        self.root.addChild(self.coords)
        self.root.addChild(self.faces)
        self.count = 0
        self.shaded = []
        self.attached = False

    def set_visible(self, on):
        self.visible = bool(on)
        self._attach(self.visible)

    def _attach(self, on):
        try:
            graph = self.session.view.getSceneGraph()
        except Exception:
            graph = None  # the design was closed: its view (and the drawing in it) is gone
        if graph is None:
            if not on:
                self.attached = False
            return
        try:
            if on and not self.attached:
                graph.addChild(self.root)
                self.attached = True
            elif not on and self.attached:
                graph.removeChild(self.root)
                self.attached = False
        except Exception as exc:
            warn("profile shading: %s" % exc)

    def update(self):
        from . import sketch_regions

        sketch = self.session.sketch
        placement = sketch.getGlobalPlacement()
        self.transform.translation.setValue(*placement.Base)
        self.transform.rotation.setValue(*placement.Rotation.Q)
        # (the area only the face's projected edges bound is the face's: not shaded)
        faces = sketch_regions.profile_regions(sketch)
        self.count = len(faces)
        points, index = [], []
        self.shaded = []  # (face, [(x, y)], triangles) per area: what can be picked
        for face in faces:
            try:
                verts, tris = face.tessellate(0.05)
            except Exception:
                continue
            self.shaded.append((face, [(v.x, v.y) for v in verts], tris))
            base = len(points)
            points += [(v.x, v.y, 0.0) for v in verts]
            for a, b, c in tris:
                index += [base + a, base + b, base + c, -1]
        self.coords.point.setNum(0)
        self.faces.coordIndex.setNum(0)
        if points:
            self.coords.point.setValues(0, len(points), points)
            self.faces.coordIndex.setValues(0, len(index), index)
        self._attach(self.visible)

    def remove(self):
        self._attach(False)


# -- what is shown --------------------------------------------------------------------
class DisplayOptions:
    """Show Points / Dimensions / Constraints / Projected Geometries.

    FreeCAD has no switches for these, so the Sketcher's own (named) Coin nodes are
    adjusted from a Qt timer: point and projected-curve draw styles, and the
    per-constraint switchboard. FreeCAD rewrites the switchboard whenever it redraws,
    so it is checked again a few times a second while something is hidden."""

    def __init__(self, session):
        self.session = session
        self.saved_styles = {}
        self.hidden_curves = set()  # Projected Curves hidden by Show Projected Geometries
        self._timer = QtCore.QTimer()
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.apply)

    def _hidden(self):
        return {
            name: not option(name) for name in ("points", "dimensions", "constraints", "projected")
        }

    def apply(self):
        if self.session.closed:
            return
        try:
            hidden = self._hidden()
            root = self.session.view.getSceneGraph()
            self._styles(root, hidden)
            self._constraints(root, hidden)
            if any(hidden.values()):
                if not self._timer.isActive():
                    self._timer.start()
            elif self._timer.isActive():
                self._timer.stop()
        except Exception as exc:
            self._timer.stop()
            warn("sketch display options: %s" % exc)

    def _styles(self, root, hidden):
        from pivy import coin

        names = ["CurvesExternalDrawStyle", "CurvesExternalDefiningDrawStyle"]
        wanted = {n: hidden["projected"] for n in names}
        for layer in range(4):
            wanted["PointsDrawStyle%d" % layer] = hidden["points"]
        for name, hide in wanted.items():
            node, _ = find_node(root, name)
            if node is None:
                continue
            key = name
            if hide:
                if key not in self.saved_styles:
                    self.saved_styles[key] = node.style.getValue()
                if node.style.getValue() != coin.SoDrawStyle.INVISIBLE:
                    node.style = coin.SoDrawStyle.INVISIBLE
            elif key in self.saved_styles:
                node.style = self.saved_styles.pop(key)
        self._projected_curves(hidden["projected"])

    def _projected_curves(self, hide):
        """Project to Surface's curves are projected geometry too (Fusion draws them
        purple in the sketch): Show Projected Geometries off hides them while the sketch is
        open (sketch_companions.py keeps them beside the sketch)."""
        try:
            from . import sketch_companions

            for obj in sketch_companions.companions(self.session.sketch, "ProjectedCurves"):
                vobj = obj.ViewObject
                if vobj is None:
                    continue
                if hide and vobj.Visibility:
                    vobj.Visibility = False
                    self.hidden_curves.add(obj.Name)
                elif not hide and obj.Name in self.hidden_curves:
                    vobj.Visibility = True
                    self.hidden_curves.discard(obj.Name)
        except Exception as exc:
            warn("sketch display options: %s" % exc)

    def _constraints(self, root, hidden):
        node, _ = find_node(root, "ConstraintGroup")
        if node is None:
            return
        field = node.getField("enable")
        if field is None:
            return
        constraints = self.session.sketch.Constraints
        if node.getNumChildren() != len(constraints):
            return  # FreeCAD is rebuilding; next round
        wanted = []
        for c in constraints:
            show = not c.InVirtualSpace
            if c.Type in DIMENSIONAL:
                show = show and not hidden["dimensions"]
            else:
                show = show and not hidden["constraints"]
            wanted.append(show)
        text = "[%s]" % ", ".join("TRUE" if w else "FALSE" for w in wanted)
        current = field.get()
        current = current.getString() if hasattr(current, "getString") else str(current)
        if _bools(current) == wanted:
            return
        field.set(text)

    def remove(self):
        self._timer.stop()
        try:
            root = self.session.view.getSceneGraph()
            for name, style in list(self.saved_styles.items()):
                node, _ = find_node(root, name)
                if node is not None:
                    node.style = style
        except Exception:
            pass
        self.saved_styles = {}
        if self.hidden_curves:
            self._projected_curves(False)  # shown again when the sketch closes


# -- fixed curves and points (green) ---------------------------------------------------
def _rgb(hex_color):
    value = int(hex_color.lstrip("#"), 16)
    return ((value >> 16) / 255.0, ((value >> 8) & 0xFF) / 255.0, (value & 0xFF) / 255.0)


def point_slots(type_id):
    """The point markers FreeCAD draws for a geometry, in its order: a point, a line's
    or spline's start and end, a circle's or ellipse's centre, an arc's start, end and
    centre (EditModeGeometryCoinConverter)."""
    if type_id == "Part::GeomPoint":
        return (1,)
    if type_id in ("Part::GeomLineSegment", "Part::GeomBSplineCurve"):
        return (1, 2)
    if type_id in ("Part::GeomCircle", "Part::GeomEllipse"):
        return (3,)
    if type_id.startswith("Part::GeomArcOf"):
        return (1, 2, 3)
    return ()


def fixed_items(constraints):
    """(blocked curve indices, locked (geo, pos) points) from a sketch's constraints.
    FreeCAD's Block fixes a curve; Lock is a DistanceX and a DistanceY from the origin
    to a point (Fission 180's Fix/Unfix: Block on curves, Lock on points)."""
    blocked, dx, dy = set(), set(), set()
    for c in constraints:
        if c.Type == "Block":
            blocked.add(c.First)
        elif c.Type in ("DistanceX", "DistanceY") and c.First == -1 and c.FirstPos == 1:
            if c.Second >= 0:
                (dx if c.Type == "DistanceX" else dy).add((c.Second, c.SecondPos))
    return blocked, dx & dy


class FixedColour:
    """Fusion shows fixed geometry green. FreeCAD has no colour for that: a blocked curve
    or a locked point is fully constrained, so it paints it white here. After each of
    FreeCAD's own recolourings (a mouse move, a click, a selection change, a solve) the
    fixed curves and points are painted green in the sketch's Coin material nodes. A
    selected or hovered fixed curve keeps FreeCAD's selection colours."""

    SLOW_MS = 300

    def __init__(self, session):
        self.session = session
        self._items = None  # (blocked curves, locked points), rebuilt after a change
        self._map = None  # material index per curve / point, rebuilt after a change
        self._poked = False
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.SLOW_MS)
        self._timer.timeout.connect(self.apply)
        self._observer = _SelectionPoke(self)
        try:
            Gui.Selection.addObserver(self._observer)
        except Exception as exc:
            warn("sketch fixed colour: %s" % exc)

    def invalidate(self):
        self._items = None
        self._map = None

    def poke(self):
        """FreeCAD is about to recolour (a mouse event, a selection change): paint again
        right after it, from the event loop. Nothing to do while nothing is fixed."""
        try:
            if self._poked or self.session.closed:
                return
            if self._items is not None and not (self._items[0] or self._items[1]):
                return
            self._poked = True
            QtCore.QTimer.singleShot(0, self._apply_poked)
        except Exception as exc:
            warn("sketch fixed colour: %s" % exc)

    def _apply_poked(self):
        self._poked = False
        self.apply()

    def _fixed(self):
        if self._items is None:
            self._items = fixed_items(self.session.sketch.Constraints)
        return self._items

    def _mapping(self):
        """{sublayer: {geo: material index}} for the normal (0) and construction (1)
        curve layers and {(geo, pos): point index}, as FreeCAD lays its Coin nodes out:
        curves per sublayer in geometry order, points of every geometry in order."""
        if self._map is not None:
            return self._map
        sketch = self.session.sketch
        internal = set()
        for c in sketch.Constraints:
            if c.Type == "InternalAlignment":
                internal.add(c.First)
        curves = {0: {}, 1: {}}
        counts = {0: 0, 1: 0}
        points = {}
        n = 0
        for i, geo in enumerate(sketch.Geometry):
            type_id = geo.TypeId
            if type_id != "Part::GeomPoint" and i not in internal:
                try:
                    sub = 1 if sketch.getConstruction(i) else 0
                except Exception:
                    sub = 0
                curves[sub][i] = counts[sub]
                counts[sub] += 1
            for pos in point_slots(type_id):
                points[(i, pos)] = n
                n += 1
        self._map = (curves, points)
        return self._map

    def apply(self):
        if self.session.closed:
            return
        try:
            blocked, locked = self._fixed()
            if not blocked and not locked:
                self._timer.stop()
                return
            if not self._timer.isActive():
                self._timer.start()
            root = self.session.view.getSceneGraph()
            curves, points = self._mapping()
            for sub, name in ((0, "CurvesMaterials0"), (1, "CurvesMaterials1")):
                self._paint(root, name, [curves[sub][g] for g in blocked if g in curves[sub]])
            self._paint(root, "PointsMaterials_0", [points[k] for k in locked if k in points])
        except Exception as exc:
            self._timer.stop()
            warn("sketch fixed colour: %s" % exc)

    def _paint(self, root, name, indices):
        """Paint the given entries of a material node green, unless FreeCAD painted them
        as selected or hovered."""
        if not indices:
            return
        from pivy import coin

        node, _ = find_node(root, name)
        if node is None:
            return
        field = node.diffuseColor
        values = field.getValues(0)
        green = _rgb(GREEN)
        keep = (_rgb(SELECT), _rgb(HOVER))
        for i in indices:
            if i >= len(values):
                continue
            current = values[i].getValue()
            if _same_colour(current, green) or any(_same_colour(current, k) for k in keep):
                continue
            field.set1Value(i, coin.SbColor(*green))

    def remove(self):
        self._timer.stop()
        try:
            Gui.Selection.removeObserver(self._observer)
        except Exception:
            pass


def _same_colour(a, b, tol=0.02):
    return all(abs(float(a[i]) - b[i]) <= tol for i in range(3))


class _SelectionPoke:
    """A selection change makes FreeCAD recolour the sketch: paint the fixed ones again."""

    def __init__(self, fixed):
        self.fixed = fixed

    def addSelection(self, *_args):
        self.fixed.poke()

    def removeSelection(self, *_args):
        self.fixed.poke()

    def clearSelection(self, *_args):
        self.fixed.poke()

    def setPreselection(self, *_args):
        self.fixed.poke()

    def removePreselection(self, *_args):
        self.fixed.poke()


def _bools(text):
    """Parse a Coin SoMFBool string ("[ TRUE, FALSE ]" or "TRUE")."""
    body = text.replace("[", " ").replace("]", " ").replace(",", " ").split()
    return [b.upper() in ("TRUE", "1") for b in body]


# -- circumscribed polygon ------------------------------------------------------------------
def polygon_tool_active():
    """True while FreeCAD's polygon tool is running (its "Sides" field is shown)."""
    try:
        for widget in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
            if widget.metaObject().className() != "SketcherGui::TaskSketcherTool":
                continue
            if not widget.isVisible():
                return False
            for label in widget.findChildren(QtWidgets.QLabel):
                if label.isVisible() and label.text().strip().startswith("Sides"):
                    return True
            return False
    except Exception:
        pass
    return False


def finish_sketch():
    """Fusion's Finish Sketch: works with a drawing tool running or a value being typed
    (the typed value is kept). False when no sketch is open."""
    from . import commands

    sketch = editing_sketch()
    if sketch is None:
        return False
    session = current()
    if session is not None:
        session.close_editor(commit=True)
        session.polygon.stop()
        # Fusion: Finish Sketch is OK for the tool that runs: a spline being drawn is made
        # (Luca, 2026-11-04: it vanished and left its points behind; only Enter made it),
        # a conic waiting for its rho, an Offset with curves picked...
        try:
            if (
                session.tool_running()
                or (session.tool is not None and session.tool.active)
                or session.spline_drawn()
            ):
                session.finish_tool()
        except Exception as exc:
            warn("finish sketch: %s" % exc)
    try:
        from . import sketch_pick_ui

        sketch_pick_ui.stop_waiting()
        sketch_pick_ui.close_box(accept=True)  # Fusion: finishing keeps the pattern
    except Exception as exc:
        warn("finish sketch: %s" % exc)
    _state["polygon"] = None
    label = sketch.Label
    commands.leave_edit()
    try:
        Gui.Selection.clearSelection()
    except Exception:
        pass
    log("sketch %s finished" % label)
    _tell_broken_features(sketch)
    return True


def _tell_broken_features(sketch):
    """Features built on the sketch that could not be rebuilt after the edit (a profile
    left open, a projected edge gone): say so next to the mouse instead of leaving the
    part silently unchanged (Fusion marks them in the timeline and shows a message)."""
    try:
        broken = []
        for obj in sketch.Document.Objects:
            if obj is sketch or sketch not in obj.OutListRecursive:
                continue
            state = list(obj.State)
            if "Invalid" in state or "Error" in state:
                broken.append(obj.Label)
        if broken:
            from . import commands

            commands.tell(
                "%s cannot be rebuilt from %s any more (its profile is open or gone). "
                "Edit the sketch again, or press Ctrl+Z." % (", ".join(broken), sketch.Label)
            )
    except Exception as exc:
        warn("finish sketch: %s" % exc)


def start_polygon(circumscribed):
    """Run FreeCAD's polygon tool (6 sides, sides changeable in the palette or with
    U/J) in Fusion's inscribed or circumscribed form."""
    _state["polygon"] = {"circumscribed": bool(circumscribed)}
    Gui.runCommand("Sketcher_CreateHexagon")
    session = current()
    if session is not None:
        session.polygon.start(circumscribed)


class PolygonPreview:
    """For the circumscribed polygon: FreeCAD's tool previews a corner at the mouse.
    Its preview curve is hidden and redrawn turned by half a side and grown so the
    mouse is on the middle of an edge, which is what the finished polygon will be."""

    POLL_MS = 30

    def __init__(self, session):
        self.session = session
        self.active = False
        self.node = None
        self.saved = None
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._idle = 0

    def start(self, circumscribed):
        self.stop()
        if not circumscribed:
            return
        self.active = True
        self._idle = 0
        self._timer.start()

    def _poll(self):
        try:
            if self.session.closed:
                self.stop()
                return
            mode = _state["polygon"]
            if not polygon_tool_active():
                self._idle += 1
                if self._idle > 3:  # the tool ended
                    _state["polygon"] = None
                    self.stop()
                return
            self._idle = 0
            if not mode or not mode.get("circumscribed"):
                return
            self._draw()
        except Exception as exc:
            warn("polygon preview: %s" % exc)
            self.stop()

    def _draw(self):
        from pivy import coin

        root = self.session.view.getSceneGraph()
        coords, parent = find_node(root, "EditCurvesCoordinate")
        style, _ = find_node(root, "EditCurvesDrawStyle")
        if coords is None or style is None or parent is None:
            return
        # FreeCAD's edit nodes are looked up fresh on every poll and never kept: FreeCAD
        # deletes them when the sketch closes, and touching a deleted node crashes FreeCAD.
        if self.node is not None:
            mine, _ = find_node(root, "Fission180PolygonPreview")
            if mine is None:  # FreeCAD rebuilt its edit scene: our overlay went with it
                self.node = None
        if self.node is None:
            self.node = coin.SoSeparator()
            self.node.setName("Fission180PolygonPreview")
            self.draw_style = coin.SoDrawStyle()
            self.draw_style.style = coin.SoDrawStyle.LINES
            self.draw_style.lineWidth = style.lineWidth.getValue()
            self.coords = coin.SoCoordinate3()
            self.lines = coin.SoLineSet()
            self.node.addChild(self.draw_style)
            self.node.addChild(self.coords)
            self.node.addChild(self.lines)
            parent.addChild(self.node)
        if self.saved is None:
            self.saved = style.style.getValue()
        self.draw_style.lineWidth = style.lineWidth.getValue()
        points = [tuple(v.getValue()) for v in coords.point.getValues(0)]
        if len(points) < 6:
            self.coords.point.setNum(0)
            self.lines.numVertices.setNum(0)
            if style.style.getValue() != self.saved:
                style.style = self.saved
            return
        if style.style.getValue() != coin.SoDrawStyle.INVISIBLE:
            style.style = coin.SoDrawStyle.INVISIBLE
        sides = len(points) // 2
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        z = points[0][2]
        turn = math.pi / sides
        grow = 1.0 / math.cos(turn)
        cos_t, sin_t = math.cos(turn), math.sin(turn)
        out = []
        for i in range(0, sides * 2, 2):
            x, y = points[i][0] - cx, points[i][1] - cy
            out.append(
                (cx + grow * (cos_t * x - sin_t * y), cy + grow * (sin_t * x + cos_t * y), z)
            )
        out.append(out[0])
        self.coords.point.setValues(0, len(out), out)
        self.lines.numVertices.setValue(len(out))

    def stop(self):
        self._timer.stop()
        self.active = False
        # Only while the sketch is still open: once it has closed, FreeCAD has deleted its
        # edit nodes (with our overlay under them), and writing to a deleted node crashed
        # FreeCAD (found by the ribbon sweep scenario, faulthandler stack in MEMORY.md).
        if editing_sketch() is self.session.sketch:
            try:
                root = self.session.view.getSceneGraph()
                style, _ = find_node(root, "EditCurvesDrawStyle")
                if style is not None and self.saved is not None:
                    style.style = self.saved
                mine, parent = find_node(root, "Fission180PolygonPreview")
                if mine is not None and parent is not None:
                    parent.removeChild(mine)
            except Exception:
                pass
        self.node = None
        self.saved = None

    def remove(self):
        self.stop()


class ControlFrames:
    """The control frame of a control point spline: a dashed line through its control
    points, as Fusion draws it. FreeCAD's own control polygon is switched off (it draws
    one for every spline, a fit point spline's too: PARAMS); this draws one only for the
    splines whose control circles are shown (not on the hidden layer:
    sketch_draw_helpers.py). Redrawn when the sketch changes (not while a point is being
    dragged: it follows at the release)."""

    NAME = "Fission180ControlFrames"
    COLOR = "#f5a623"  # the dashed orange of construction curves

    def __init__(self, session):
        self.session = session
        self.drawn = []  # the polylines drawn last (sketch points), for the tests

    def polylines(self):
        from . import sketch_draw_helpers as helpers

        sketch = self.session.sketch
        hidden = helpers.hidden(sketch)
        out = []
        for i, geo in enumerate(sketch.Geometry):
            if geo.TypeId != helpers.BSPLINE:
                continue
            poles = helpers.aligned_to(sketch, i).get("BSplineControlPoint", [])
            if not poles or all(p in hidden for p in poles):
                continue
            points = [(p.x, p.y) for p in geo.getPoles()]
            if len(points) >= 2:
                if geo.isPeriodic():
                    points.append(points[0])
                out.append(points)
        return out

    def update(self):
        if self.session.closed or editing_sketch() is not self.session.sketch:
            return
        try:
            from pivy import coin

            lines = self.polylines()
            root = self.session.view.getSceneGraph()
            node, parent = find_node(root, self.NAME)
            if not lines:
                if node is not None and parent is not None:
                    parent.removeChild(node)
                self.drawn = []
                return
            if node is None:
                _coords, edit_root = find_node(root, "EditCurvesCoordinate")
                if edit_root is None:
                    return
                node = coin.SoSeparator()
                node.setName(self.NAME)
                style = coin.SoDrawStyle()
                style.lineWidth = 1
                style.linePattern = 0x0F0F
                color = coin.SoBaseColor()
                color.rgb.setValue(*_rgb(self.COLOR))
                pick = coin.SoPickStyle()
                pick.style = coin.SoPickStyle.UNPICKABLE
                for child in (pick, style, color, coin.SoCoordinate3(), coin.SoLineSet()):
                    node.addChild(child)
                edit_root.addChild(node)
            coords, lineset = node.getChild(3), node.getChild(4)
            flat = [(x, y, 0.004) for line in lines for x, y in line]
            coords.point.setValues(0, len(flat), flat)
            coords.point.setNum(len(flat))
            counts = [len(line) for line in lines]
            lineset.numVertices.setValues(0, len(counts), counts)
            lineset.numVertices.setNum(len(counts))
            self.drawn = lines
        except Exception as exc:
            warn("spline control frame: %s" % exc)

    def remove(self):
        # (only while the sketch is still open: FreeCAD deletes its edit nodes, ours under
        # them, when it closes; a deleted node must not be touched)
        try:
            if editing_sketch() is self.session.sketch:
                root = self.session.view.getSceneGraph()
                node, parent = find_node(root, self.NAME)
                if node is not None and parent is not None:
                    parent.removeChild(node)
        except Exception:
            pass
        self.drawn = []


def _patch_profilelib():
    """FreeCAD's polygon tool finishes through ProfileLib.RegularPolygon.makeRegularPolygon
    (Python). While Fission 180's circumscribed polygon runs, the clicked point is the
    middle of an edge and the construction circle touches the edges."""
    try:
        import ProfileLib.RegularPolygon as rp
    except Exception as exc:
        warn("polygon: %s" % exc)
        return
    if _state["profilelib"] is not None:
        return
    original = rp.makeRegularPolygon
    _state["profilelib"] = (rp, original)

    def makeRegularPolygon(
        sketch,
        sides,
        centerPoint=App.Vector(0, 0, 0),
        firstCornerPoint=App.Vector(-20.00, 34.64, 0),
        construction=False,
    ):
        mode = _state["polygon"]
        if not mode or not mode.get("circumscribed"):
            geos, cons = len(sketch.Geometry), len(sketch.Constraints)
            made = original(sketch, sides, centerPoint, firstCornerPoint, construction)
            try:
                from . import sketch_draw_helpers

                ids = list(range(geos, len(sketch.Geometry)))
                if len(ids) == int(sides) + 1:  # FreeCAD's: the sides, then their circle
                    sketch_draw_helpers.tidy_polygon(sketch, ids, int(sides), False, cons)
            except Exception as exc:
                warn("polygon: %s" % exc)
            return made
        from . import sketch_polygon

        sketch_polygon.add_polygon(sketch, sides, centerPoint, firstCornerPoint, True, construction)

    rp.makeRegularPolygon = makeRegularPolygon


def _unpatch_profilelib():
    saved = _state["profilelib"]
    _state["profilelib"] = None
    if saved is not None:
        module, original = saved
        module.makeRegularPolygon = original
