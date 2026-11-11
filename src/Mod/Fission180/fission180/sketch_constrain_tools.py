# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch constraints with Fusion's pick flow, on Fission 180's own sketch handler
(sketch_draw.py): Coincident, Collinear, Concentric, Midpoint, Fix/Unfix, Parallel,
Perpendicular, Horizontal/Vertical, Tangent, Curvature, Equal and Symmetry.

Both ways Fusion works (wave 7, the book parity report):

- tool first: start the command, click the things (the one under the pointer lights up, the
  picked ones stay lit), the constraint is added and the command waits for the next ones; Esc
  ends it;
- picks first: with fitting things selected before the command it applies at once, to all of
  them (Equal on four lines, Horizontal/Vertical on three lines, Fix on a mixed selection).

A constraint is never silently dropped: a click that does not fit says what the tool takes,
and a constraint the sketch cannot take says which constraints or dimensions are in the way
(highlighted, sketch_explain.py). Until wave 7 Coincident, Fix/Unfix, Parallel, Perpendicular,
Horizontal/Vertical, Tangent, Equal and Symmetry were FreeCAD's own commands: they did
nothing on a selection that did not fit, showed FreeCAD's modal "Sketcher Constraint
Substitution" box, took a line click as a midpoint and knew Symmetry only for two points.

FreeCAD's forms (checked in FreeCAD 1.1.4, docs/fission180/parity/sketch.md):
- Collinear: a Tangent between two lines (FreeCAD's line-line tangency is collinearity); when
  the lines are parallel already (each Vertical, say) that would say the direction twice, so
  one end is put on the other line instead (PointOnObject).
- Concentric: a Coincident between the two centres.
- Midpoint: Symmetric (the line's ends about the point); on an arc: the point on the arc
  and a construction line from the centre through it that the arc's ends are symmetric about.
- Tangent: curves that share an end get FreeCAD's end-to-end tangency in place of the join
  (what FreeCAD's own tool does, with a modal box; here without a word, like Fusion); an end
  lying on the other curve: end-to-curve tangency; a spline: only at its ends (the solver has
  no tangency along a spline).
- Symmetry: two points about a line (Symmetric); two lines: their ends in pairs; two circles:
  the centres and Equal; two arcs: their ends crosswise and Equal.
- Fix/Unfix: Block on a curve, FreeCAD's Lock (two distances from the origin) on a point.
- Curvature (G2): FreeCAD's solver has no curvature constraint. A spline and a line: a
  tangent join plus the spline's third pole on the line too (curvature 0 at the join,
  exact G2); a spline and an arc, circle or another spline: tangent only (G1), said in a note.

What the solver's answer means is decided in sketch_constrain_core.judge (unit tested).
"""

import math

from . import log, warn
from . import sketch_build as build
from . import sketch_constrain_core as core
from . import sketch_draw as draw
from . import sketch_explain as explain
from . import sketch_explain_core as explain_core
from . import sketch_geometry
from . import sketch_infer_core as icore

LINE = ("Part::GeomLineSegment",)
CIRCULAR = ("Part::GeomCircle", "Part::GeomArcOfCircle")
ROUND = (
    "Part::GeomCircle",
    "Part::GeomArcOfCircle",
    "Part::GeomEllipse",
    "Part::GeomArcOfEllipse",
)
SPLINE = ("Part::GeomBSplineCurve",)
LINE_OR_ARC = ("Part::GeomLineSegment", "Part::GeomArcOfCircle")
CURVES = LINE + ROUND + SPLINE + ("Part::GeomArcOfHyperbola", "Part::GeomArcOfParabola")
OPEN = (
    "Part::GeomLineSegment",
    "Part::GeomArcOfCircle",
    "Part::GeomArcOfEllipse",
    "Part::GeomBSplineCurve",
    "Part::GeomArcOfHyperbola",
    "Part::GeomArcOfParabola",
)
POINT = "point"
TOUCH = 1e-5  # mm: two ends this near are one corner


def _con(*args):
    import Sketcher

    return Sketcher.Constraint(*args)


# -- what the solver says -------------------------------------------------------------------------
def read_state(sketch):
    """Solve and read the result (sketch_constrain_core.State). FreeCAD's own report of a
    solve that failed stays out of the Report view: this is a trial, and what it means is
    said by the tool (a Parallel between a Horizontal and a Vertical line can only be met
    by a line of no length: "Updating geometry: Error build geometry: Both points are
    equal")."""
    from . import preview

    with preview.quiet():
        code = sketch.solve()
    conflicting, redundant = explain.bad_sets(sketch)
    try:
        dof = int(sketch.DoF)
    except Exception:
        dof = None
    return core.State(code, dof, conflicting, redundant)


def end_step(doc, abort=False):
    """Close the undo step opened with doc.openTransaction(). FreeCAD's commit and abort
    only close a step that holds changes: one that changed nothing (a refusal before
    anything was tried) left its name pending, and the next change anywhere (the solve
    right after) became an undo step under that name. The pending name is closed too
    (preview.end_transaction does the same for the dialogs)."""
    import FreeCAD as App

    if abort:
        doc.abortTransaction()
    else:
        doc.commitTransaction()
    try:
        App.closeActiveTransaction(abort)
    except Exception:
        pass


class Outcome:
    """What became of one constraint: `ok`; when not, `text` says why and `culprits` are the
    constraints to highlight; `note`: something to say although it was added."""

    def __init__(self, ok, text="", culprits=(), note="", kind=""):
        self.ok = ok
        self.text = text
        self.culprits = list(culprits)
        self.note = note
        self.kind = kind


class TakeBack(Exception):
    """The step must be undone as a whole (its transaction aborted); `outcome` says why."""

    def __init__(self, outcome):
        Exception.__init__(self, outcome.text)
        self.outcome = outcome


def _rollback(sketch, new, geometry):
    from . import preview

    for i in sorted(new, reverse=True):
        sketch.delConstraint(i, True)
    with preview.quiet():
        sketch.solve()
    try:
        if sketch_geometry.moved(sketch, geometry):
            sketch_geometry.restore(sketch, geometry)
            sketch.solve()
    except Exception as exc:
        warn("constraint: could not put the curves back: %s" % exc)


def _size(g):
    """A curve's size: a line's length, a circle's or arc's radius (None: no size to lose)."""
    try:
        if g.TypeId == "Part::GeomLineSegment":
            return (g.EndPoint - g.StartPoint).Length
        radius = getattr(g, "Radius", None)
        return float(radius) if radius is not None else None
    except Exception:
        return None


def _sizes(sketch):
    return [_size(g) for g in sketch.Geometry]


def _squeezed(sketch, geos, sizes):
    """The curves among `geos` that the solver squeezed to (next to) nothing: a thousandth
    of their size before (`sizes`), or under a tenth of a micrometre. FreeCAD's solver meets
    constraints that cannot be met by shrinking a line towards a point, and stops a hair
    before it (no error then; the next solve fails with "Both points are equal")."""
    out = set()
    geometry = sketch.Geometry
    for g in geos:
        if not 0 <= g < len(geometry) or g >= len(sizes) or sizes[g] is None:
            continue
        now = _size(geometry[g])
        if now is not None and sizes[g] > 1e-4 and now < max(1e-4, sizes[g] * 1e-3):
            out.add(g)
    return out


PROBE_TRIES = 12  # constraints switched off at most to find what a new one fights


def _fights(sketch, new, sizes, geometry=None):
    """The existing constraints a new one cannot live with, when the solver names none (it
    found no solution, or only one that squeezes a curve to nothing): each constraint near
    the new ones is switched off in turn; the ones without which the sketch solves are named.
    Nothing is deleted."""
    cons = sketch.Constraints
    near = [
        j for j in explain.component(sketch, new) if j not in new and explain._nameable(cons[j])
    ]
    if not near:
        return []
    near = explain._nearness(sketch, new[0], near)[:PROBE_TRIES]
    touched = {g for i in new for g in explain._geos(cons[i])}
    found = []
    for j in near:
        try:
            if geometry is not None:
                # from where the curves were: the failed try left them squeezed
                sketch_geometry.restore(sketch, geometry)
            sketch.setActive(j, False)
            state = read_state(sketch)
            if state.code == core.SOLVED and not _squeezed(sketch, touched, sizes):
                found.append(j)
        except Exception:
            pass
        finally:
            try:
                sketch.setActive(j, True)
            except Exception:
                pass
    return found


def _refusal(sketch, title, verdict, which, new, after, sizes=(), geometry=None):
    """The Outcome of a form that did not fit, worded while its constraints are still in."""
    culprits = [i for i in which if i not in new]
    partial = False
    if verdict == core.CONFLICT:
        named = explain.conflict_culprits(sketch, new)
        culprits = named or culprits or _fights(sketch, new, sizes, geometry)
        if not culprits:
            # the solver cannot say: the constraints on the same curves, as the place to look
            near = []
            for i in new:
                near += [j for j in explain._neighbours(sketch, i) if j not in new]
            near = sorted(set(near))
            text, _count = explain.words(sketch, near)
            return Outcome(False, explain_core.refused_unmet(title, text), near, kind="conflict")
        text, count = explain.words(sketch, culprits)
        return Outcome(
            False,
            explain_core.refused_constraint(title, "conflict", text, count),
            culprits,
            kind="conflict",
        )
    # FreeCAD names one constraint of those that say a thing twice: the others are found by
    # switching constraints off in turn (sketch_explain.redundant_culprits)
    flagged = sorted(set(new) & after.redundant) or culprits[:1]
    if flagged:
        found = explain.redundant_culprits(sketch, flagged[0], exclude=new, solved=True)
        culprits = sorted(set(culprits) | set(found))
        partial = bool(getattr(found, "partial", False))
    text, count = explain.words(sketch, culprits)
    if verdict == core.PARTIAL:
        return Outcome(False, explain_core.refused_partial(title, text), culprits, kind="partial")
    return Outcome(
        False,
        explain_core.refused_constraint(title, "redundant", text, count, partial),
        culprits,
        kind="redundant",
    )


def _without(sketch, which, before, holds):
    """True when the sketch is clean with the constraints `which` switched off (tried
    without deleting anything: they are switched on again)."""
    try:
        for i in which:
            sketch.setActive(i, False)
        after = read_state(sketch)
        fine = (
            not (after.conflicting - before.conflicting)
            and len(after.redundant) <= len(before.redundant)
            and (after.code == core.SOLVED or after.code == before.code)
        )
        return fine and (holds is None or holds())
    except Exception as exc:
        warn("constraint: %s" % exc)
        return False
    finally:
        for i in which:
            try:
                sketch.setActive(i, True)
            except Exception:
                pass


def add_forms(sketch, title, forms, holds=None, replace_first=False):
    """_add_forms with FreeCAD's own reports of the tries that fail kept out of the Report
    view (FreeCAD solves an open sketch on every change of its constraints and prints
    "Updating geometry: Error build geometry" for a try that squeezes a line to nothing):
    what a failed try means is said by the tool."""
    from . import preview

    with preview.quiet():
        return _add_forms(sketch, title, forms, holds, replace_first)


def _add_forms(sketch, title, forms, holds, replace_first):
    """Add a constraint in the first of its `forms` (lists of Sketcher constraints that mean
    the same thing here) the sketch takes; inside the caller's open transaction. Returns an
    Outcome. `holds()`: the geometry now is what the constraint asks for (checked for the
    forms after the first, which only complete what the sketch already says in part).

    A form that says something new but makes OLDER relations repeat it (the Coincident of
    joined ends under an end-to-end Tangent) can take their place: FreeCAD's "constraint
    substitution", without its message box. `replace_first`: do that as soon as a form asks
    for it (Tangent); else only when no other form fits (Collinear keeps the lines' own
    Vertical and puts one end on the other line instead). Tried with the older ones switched
    off before anything is deleted."""
    before = read_state(sketch)
    geometry = sketch_geometry.snapshot(sketch)
    sizes = _sizes(sketch)
    refusal = None
    candidate = None

    def replace(form, which):
        words, _count = explain.words(sketch, which, limit=6)
        sketch.addConstraint(list(form))
        for i in sorted(which, reverse=True):
            sketch.delConstraint(i, True)
        sketch.solve()
        log("%s: it now says what %s said: taken out" % (title, words))
        return Outcome(True)

    for n, form in enumerate(forms):
        first = len(sketch.Constraints)
        sketch.addConstraint(list(form))
        new = list(range(first, len(sketch.Constraints)))
        after = read_state(sketch)
        cons = sketch.Constraints
        removable = [
            i
            for i in after.redundant
            if i < first and cons[i].Type in core.RELATIONS and explain._nameable(cons[i])
        ]
        verdict, which = core.judge(before, after, new, removable)
        touched = explain._curves_of(form)
        if verdict == core.OK and _squeezed(sketch, touched, sizes):
            verdict, which = core.CONFLICT, []  # only a curve of no size can meet it
        if verdict == core.OK:
            if n == 0 or holds is None or holds():
                return Outcome(True)
            # (it fits but does not say it all: the next form)
        elif refusal is None:
            refusal = _refusal(sketch, title, verdict, which, new, after, sizes, geometry)
        usable = verdict == core.IMPLIED and _without(sketch, which, before, holds)
        _rollback(sketch, new, geometry)
        if usable and replace_first:
            return replace(form, which)
        if usable and candidate is None:
            candidate = (form, list(which))
        if n == 0 and verdict in (core.CONFLICT, core.SAME):
            return refusal
    if candidate is not None:
        return replace(*candidate)
    if refusal is None:
        refusal = Outcome(False, "%s: could not be added here." % title)
    return refusal


# -- geometry helpers -----------------------------------------------------------------------------
def _geo(sketch, geo):
    return build.geometry(sketch, geo)


def _xy(v):
    return (v.x, v.y)


def point_of(sketch, item):
    """The sketch point (x, y) of a picked point (geo, pos), or None."""
    geo, pos = item
    try:
        if geo == -1 and pos == 1:
            return (0.0, 0.0)
        g = _geo(sketch, geo)
        if g.TypeId == "Part::GeomPoint":
            return (g.X, g.Y)
        if pos == 1:
            return _xy(g.StartPoint)
        if pos == 2:
            return _xy(g.EndPoint)
        if pos == 3:
            c = getattr(g, "Center", None)
            if c is None:
                c = g.Location
            return _xy(c)
    except Exception:
        return None
    return None


def _ends(sketch, geo):
    """{pos: point} of an open curve's two ends ({} for a closed one)."""
    try:
        g = _geo(sketch, geo)
        if g.TypeId in OPEN:
            return {1: g.StartPoint, 2: g.EndPoint}
    except Exception:
        pass
    return {}


def _closest_ends(sketch, a, b):
    """(pos on a, pos on b, distance) of the two end points nearest each other, or None."""
    best = None
    for pa, va in _ends(sketch, a).items():
        for pb, vb in _ends(sketch, b).items():
            d = (va - vb).Length
            if best is None or d < best[2]:
                best = (pa, pb, d)
    return best


def _end_on_curve(sketch, a, b):
    """(pos of a, distance) of the end of curve a nearest to curve b, or None."""
    best = None
    try:
        import Part

        shape = _geo(sketch, b).toShape()
        for pa, va in _ends(sketch, a).items():
            d = Part.Vertex(va).distToShape(shape)[0]
            if best is None or d < best[1]:
                best = (pa, d)
    except Exception:
        return None
    return best


def _line_frame(sketch, geo):
    """(origin, direction) of a line (the axes too), as (x, y) pairs."""
    if geo == -1:
        return (0.0, 0.0), (1.0, 0.0)
    if geo == -2:
        return (0.0, 0.0), (0.0, 1.0)
    g = _geo(sketch, geo)
    d = g.EndPoint - g.StartPoint
    return _xy(g.StartPoint), (d.x, d.y)


def _name(sketch, item):
    """What a picked thing is called in a message ("Line 2", "the origin", "a point")."""
    geo, pos = item
    names, _kinds = explain.names(sketch)
    if geo == -1 and pos == 1:
        return "the origin"
    owner = explain_core.curve_name(geo, names)
    if pos == 0:
        return owner
    what = {1: "start", 2: "end", 3: "centre"}.get(pos, "point")
    try:
        if geo >= 0 and sketch.Geometry[geo].TypeId == "Part::GeomPoint":
            return owner
    except Exception:
        pass
    return "the %s of %s" % (what, owner)


def _kind_word(kind):
    if kind == POINT:
        return "a point"
    word = explain_core.KIND_NAMES.get(kind, "curve").lower()
    return ("an %s" if word[:1] in "aeiou" else "a %s") % word


# -- the tool -------------------------------------------------------------------------------------
_SAID = {"text": "", "count": 0}


def last_said():
    """What a constraint tool last told the user (a refusal or a note), for tests."""
    return _SAID["text"]


def said_count():
    return _SAID["count"]


def _remember(text):
    _SAID["text"] = text
    _SAID["count"] += 1
    try:
        # the last thing told next to the mouse, whoever told it (an older tooltip is not
        # shown again over this)
        from . import commands

        commands._TOLD["msg"] = text
    except Exception:
        pass


class PickConstraint(draw.DrawTool):
    """Click the things a constraint takes; `fits(picks, item)` says whether an item can be
    the next pick (an item is (geo, pos): pos 0 for a whole curve). A subclass gives
    `forms(picks)` (the constraint as lists of Sketcher constraints, see add_forms) or, for
    one that also adds geometry, `constrain(picks)`."""

    needs = 2
    references_model = True  # (a click on a model edge projects it, then picks it)
    points_ok = False  # a sketch point can be picked
    snap_dot = False  # it picks curves: they light up instead
    takes = "two curves"  # what it works on, for the message of a click that does not fit
    replace_first = False  # see add_forms

    def steps(self):
        return self.needs

    def candidates(self, snap):
        """What is under the pointer, best first: [(geo, pos)]. A point (when the tool
        takes points), then the curves within the pick radius, the nearest first; of two
        equally near the sketch's own curve comes before an axis or a projected curve (a
        line drawn along the X axis is the line, not the axis)."""
        geo = self.geometry()
        tol = draw.pick_pixels() * self._px()
        out = []
        vertex = icore.nearest_vertex(snap.raw, geo.verts, tol)
        if self.points_ok and vertex is not None:
            out.append(vertex[0])
        curves = []
        for index, curve in geo.hits:
            if draw._type_of(self.sketch, index) not in CURVES:
                continue
            if not icore.near_curve(snap.raw, curve, tol):
                continue
            d = icore.curve_distance(snap.raw, curve)
            curves.append((round(d, 6), 0 if index >= 0 else 1, index))
        for _d, _own, index in sorted(curves):
            if (index, 0) not in out:
                out.append((index, 0))
        if not self.points_ok and vertex is not None:
            # a click on a circle's centre picks the circle
            if vertex[0][1] == 3 and vertex[0][0] >= 0 and (vertex[0][0], 0) not in out:
                out.append((vertex[0][0], 0))
        return out

    def item_at(self, snap):
        """The point or curve under the pointer the tool can take next: (geo, pos); when
        nothing there fits, the nearest thing (for the message saying why not), or None."""
        found = self.candidates(snap)
        for item in found:
            if item not in self.picks and self.fits(self.picks, item):
                return item
        return found[0] if found else None

    def kind_of(self, item):
        geo, pos = item
        if pos != 0:
            return POINT
        return draw._type_of(self.sketch, geo)

    def fits(self, picks, item):
        return True

    def complete(self, picks):
        return len(picks) >= self.needs

    def why_not(self, picks, item):
        """Why the clicked item is not taken."""
        if item is None:
            return "nothing there. %s" % self._capital(self.prompt())
        if item in picks:
            return "that one is picked already. %s" % self._capital(self.prompt())
        return "it works on %s; that is %s. %s" % (
            self.takes,
            _kind_word(self.kind_of(item)),
            self._capital(self.prompt()),
        )

    @staticmethod
    def _capital(text):
        return text[:1].upper() + text[1:]

    # -- picks made before the tool -----------------------------------------------------
    def plan(self, selection):
        """The picks of each constraint to add for what was selected before the tool:
        [[item, ...], ...] (empty: the selection does not fit)."""
        return core.plan_pairs(selection, self.fits)

    def use_selection(self, selection):
        if not selection:
            return
        groups = self.plan(selection)
        if not groups:
            # Fusion starts the tool and waits for picks. What of the selection can start
            # the constraint is its first pick (one line selected, then Parallel: click the
            # second line); the rest is let go
            picks = []
            for item in selection:
                if item not in picks and self.fits(picks, item):
                    picks.append(item)
                if len(picks) >= self.needs - 1:
                    break
            self._clear_selection()
            if picks and not self.complete(picks):
                self.picks = picks
                self.step = len(picks)
                self._tell()
                log(
                    "%s: %d picked already (selected first). %s"
                    % (self.title, len(picks), self.prompt())
                )
                return
            self.say(
                "%s works on %s: what was selected does not fit. %s"
                % (self.title, self.takes, self._capital(self.prompt()))
            )
            return
        outcome = self.apply(groups)
        self.stop()  # Fusion: with a selection made first the constraint is all
        self._clear_selection()
        if outcome is not None and (outcome.text or outcome.note):
            self._tell_after(outcome)

    def _clear_selection(self):
        try:
            import FreeCADGui as Gui

            Gui.Selection.clearSelection()
        except Exception:
            pass

    def _tell_after(self, outcome):
        """A message after the tool ended (its hint is gone): next to the mouse."""
        try:
            from . import commands

            _remember(outcome.text or outcome.note)
            commands.tell(outcome.text or outcome.note)
            if outcome.culprits:
                explain.highlight(self.sketch, outcome.culprits)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def say(self, text):
        """A refusal or note beside the pointer. A text that names its constraint itself
        ("Vertical: not added, ...") is shown as it is."""
        head = text.split(":", 1)[0]
        if not (text.startswith(self.title) or head in explain_core.FUSION_NAMES.values()):
            text = "%s: %s" % (self.title, text)
        _remember(text)
        log(text)
        try:
            if self.hint is not None:
                self.hint.warn_text(text)
            else:
                from . import commands

                commands.tell(text)
        except Exception:
            pass

    # -- the mouse ----------------------------------------------------------------------
    def moved(self, snap):
        item = self.item_at(snap)
        lit = [self._shape(p) for p in self.picks]
        points = [self._point(p) for p in self.picks if p[1] != 0]
        hover = []
        if item is not None and item not in self.picks and self.fits(self.picks, item):
            if item[1] == 0:
                hover = [self._shape(item)]
            else:
                points.append(self._point(item))
        self.preview.show(picked=[s for s in lit + hover if s], points=[p for p in points if p])

    def _shape(self, item):
        if item[1] != 0:
            return []
        return draw.curve_points(self.sketch, item[0])

    def _point(self, item):
        geo = self.geometry()
        return geo.keyed.get(item)

    def released(self, press_snap, snap, moved):
        item = self.item_at(press_snap)
        if item is None or item in self.picks or not self.fits(self.picks, item):
            self.say("%s: %s" % (self.title, self.why_not(self.picks, item)))
            return
        self.picks.append(item)
        if not self.complete(self.picks):
            self.step = len(self.picks)
            self._tell()
            return
        outcome = self.apply([list(self.picks)])
        self.picks = []
        self.step = 0
        self.preview.clear()
        self._tell()
        if outcome is not None and (outcome.text or outcome.note):
            self.say(outcome.text or outcome.note)
            if outcome.culprits:
                explain.highlight(self.sketch, outcome.culprits)

    # -- adding -------------------------------------------------------------------------
    def apply(self, groups):
        """Add the constraint for each group of picks: one undo step. Returns the Outcome to
        tell (a refusal, a note), or None."""
        doc = self.doc
        sketch = self.sketch
        first = len(sketch.Constraints)
        told = None
        added = 0
        doc.openTransaction(self.title)
        try:
            for picks in groups:
                outcome = self.constrain_one(picks)
                if outcome.ok:
                    added += 1
                    if outcome.note and told is None:
                        told = outcome
                elif told is None or told.ok:
                    told = outcome
        except TakeBack as back:
            end_step(doc, abort=True)
            self._settle()
            log("%s: taken back: %s" % (self.title, back.outcome.text))
            return back.outcome
        except Exception as exc:
            end_step(doc, abort=True)
            self._settle()
            log("%s: refused: %s" % (self.title, exc))
            return Outcome(False, "%s: could not be added (%s)." % (self.title, _plain(exc)))
        if not added:
            end_step(doc, abort=True)
            self._settle()
            if told is not None:
                log("%s: refused: %s" % (self.title, told.text))
            return told
        end_step(doc)
        self._geometry = None
        names = ", ".join(c.Type for c in sketch.Constraints[first:])
        log("%s: added (%s)" % (self.title, names or "replacing older constraints"))
        if told is not None and not told.ok and len(groups) > 1:
            told.text = "%s (%d of %d added.)" % (told.text, added, len(groups))
        return told

    def _settle(self):
        try:
            self.sketch.solve()
        except Exception:
            pass
        self._geometry = None

    def constrain_one(self, picks):
        """One constraint for `picks`, inside the open transaction: an Outcome."""
        try:
            forms = self.forms(picks)
        except ValueError as exc:
            return Outcome(False, "%s: %s" % (self.title, exc))
        if forms is None:
            return self._constrain_own(picks)
        outcome = add_forms(
            self.sketch, self.title, forms, lambda: self.holds(picks), self.replace_first
        )
        if outcome.ok:
            outcome.note = self.note(picks) or ""
        return outcome

    def _constrain_own(self, picks):
        """A tool that adds geometry with its constraint (Midpoint on an arc, Curvature):
        constrain() adds everything; what does not fit takes the whole step back."""
        sketch = self.sketch
        first = len(sketch.Constraints)
        note = self.constrain(picks)
        new = list(range(first, len(sketch.Constraints)))
        finding = explain.check_new(sketch, new, probe=False)
        if finding.kind == "conflict":
            explain.log_finding(self.title, sketch, finding)
            raise TakeBack(
                Outcome(False, explain.refusal(sketch, self.title, finding), finding.culprits)
            )
        ours = finding.bad if finding.kind == "redundant" else []
        if ours and len(ours) == len(new):
            if not finding.culprits:
                culprits = explain.redundant_culprits(sketch, ours[0], exclude=new, solved=True)
                finding.culprits = list(culprits)
                finding.partial = bool(getattr(culprits, "partial", False))
            explain.log_finding(self.title, sketch, finding)
            raise TakeBack(
                Outcome(False, explain.refusal(sketch, self.title, finding), finding.culprits)
            )
        for i in reversed(ours):
            sketch.delConstraint(i)
        if ours:
            sketch.solve()
        if len(sketch.Constraints) == first:
            raise TakeBack(Outcome(False, "%s: not added, it is so already." % self.title))
        return Outcome(True, note=note or "")

    def forms(self, picks):
        """The constraint for `picks` as alternative lists of Sketcher constraints (the first
        is the usual one), or None when constrain() does it. ValueError: why it cannot be."""
        return None

    def holds(self, picks):
        """The geometry now is what the constraint asks (see add_forms)."""
        return True

    def note(self, picks):
        """Something to say after the constraint was added, or None."""
        return None

    def constrain(self, picks):
        """Add the constraint(s) and what they need; returns a note to show, or None."""
        raise NotImplementedError

    def _fixed(self, item):
        """The axes, the origin and projected geometry never move."""
        return item[0] < 0


def _plain(exc):
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return text[:120]


BOTH_FIXED = "both are fixed (an axis, the origin or projected geometry): neither can move"


# -- Coincident -----------------------------------------------------------------------------------
class Coincident(PickConstraint):
    """Fusion's Coincident: two points meet, or a point goes onto a curve (anywhere on it:
    its middle is the Midpoint constraint's)."""

    title = "Coincident"
    command = "Fission180_SketchCoincident"
    points_ok = True
    takes = "a point and another point or a curve"

    def prompt(self):
        if not self.picks:
            return "click a point, then the point or curve it goes onto."
        if self.picks[0][1] != 0:
            return "click the point or curve it goes onto."
        return "click the point to put on that curve."

    def fits(self, picks, item):
        if item in picks:
            return False
        if not picks:
            return True
        first = picks[0]
        if first[1] == 0:
            return item[1] != 0  # a curve first: now the point
        return True

    def why_not(self, picks, item):
        if item is not None and picks and picks[0][1] == 0 and item[1] == 0:
            return "two curves cannot be made coincident: click a point to put on the curve."
        return PickConstraint.why_not(self, picks, item)

    def plan(self, selection):
        return core.plan_coincident(selection, lambda item: item[1] != 0)

    def forms(self, picks):
        a, b = picks
        if a[1] == 0:
            a, b = b, a
        if self._fixed(a) and self._fixed(b):
            raise ValueError(BOTH_FIXED)
        if b[1] != 0:
            if a[0] == b[0] and a[0] >= 0:
                raise ValueError(
                    "both points belong to %s: it would shrink to nothing."
                    % _name(self.sketch, (a[0], 0))
                )
            return [[_con("Coincident", a[0], a[1], b[0], b[1])]]
        if a[0] == b[0]:
            raise ValueError("that point belongs to the curve itself.")
        return [[_con("PointOnObject", a[0], a[1], b[0])]]


# -- Collinear ------------------------------------------------------------------------------------
class Collinear(PickConstraint):
    title = "Collinear"
    command = "Fission180_SketchCollinear"
    takes = "two lines"

    def prompt(self):
        return "click the first line." if not self.picks else "click the line to bring onto it."

    def fits(self, picks, item):
        return item[1] == 0 and self.kind_of(item) in LINE and item not in picks

    def forms(self, picks):
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        forms = [[_con("Tangent", a, b)]]
        # lines that are parallel already (each Vertical, a Parallel between them...): the
        # line-line Tangent would say their direction twice; one end on the other line says
        # the rest
        for line, other in ((b, a), (a, b)):
            if line >= 0:
                forms.append([_con("PointOnObject", line, 1, other)])
                forms.append([_con("PointOnObject", line, 2, other)])
        return forms

    def holds(self, picks):
        (a, _), (b, _) = picks
        try:
            origin, d = _line_frame(self.sketch, a)
            n = math.hypot(*d)
            for pos in (1, 2):
                p = point_of(self.sketch, (b, pos))
                if b in (-1, -2):
                    o2, d2 = _line_frame(self.sketch, b)
                    p = o2 if pos == 1 else (o2[0] + d2[0], o2[1] + d2[1])
                off = abs((p[0] - origin[0]) * d[1] - (p[1] - origin[1]) * d[0]) / n
                if off > TOUCH:
                    return False
            return True
        except Exception:
            return False


# -- Concentric -----------------------------------------------------------------------------------
class Concentric(PickConstraint):
    title = "Concentric"
    command = "Fission180_SketchConcentric"
    takes = "two circles, arcs or ellipses"

    def prompt(self):
        return (
            "click a circle, arc or ellipse."
            if not self.picks
            else "click the one to share its centre."
        )

    def fits(self, picks, item):
        return item[1] == 0 and self.kind_of(item) in ROUND and item not in picks

    def forms(self, picks):
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        return [[_con("Coincident", a, 3, b, 3)]]


# -- Midpoint -------------------------------------------------------------------------------------
class Midpoint(PickConstraint):
    title = "Midpoint"
    command = "Fission180_SketchMidpoint"
    points_ok = True
    takes = "a point and a line or arc"

    def prompt(self):
        if not self.picks:
            return "click a point, then the line or arc whose middle it goes to."
        if self.picks[0][1] != 0:
            return "click the line or arc whose middle the point goes to."
        return "click the point to put at its middle."

    def fits(self, picks, item):
        kind = self.kind_of(item)
        if item in picks:
            return False
        if not picks:
            return kind == POINT or kind in LINE_OR_ARC
        first = self.kind_of(picks[0])
        if first == POINT:
            return kind in LINE_OR_ARC and item[0] != picks[0][0]
        return kind == POINT and item[0] != picks[0][0]

    def _split(self, picks):
        point = picks[0] if picks[0][1] != 0 else picks[1]
        curve = picks[1][0] if picks[0][1] != 0 else picks[0][0]
        return point, curve

    def forms(self, picks):
        point, curve = self._split(picks)
        if draw._type_of(self.sketch, curve) in LINE:
            if curve < 0 and point[0] < 0:
                raise ValueError(BOTH_FIXED)
            return [[_con("Symmetric", curve, 1, curve, 2, point[0], point[1])]]
        return None  # an arc: constrain()

    def constrain(self, picks):
        point, curve = self._split(picks)
        sketch = self.sketch
        # an arc: the point on it, on the line from the centre that bisects its ends. The
        # point is first put at the arc's middle (Fusion snaps it there): started far
        # off, the solver can settle with the constraints unmet (checked in FreeCAD)
        import Part

        g = build.geometry(sketch, curve)
        middle = g.value((g.FirstParameter + g.LastParameter) / 2.0)
        try:
            sketch.moveGeometry(point[0], point[1], middle, False)
        except Exception:
            pass
        g = build.geometry(sketch, curve)
        where = sketch.getPoint(point[0], point[1])
        line = sketch.addGeometry(Part.LineSegment(g.Center, where), True)
        first = len(sketch.Constraints)
        sketch.addConstraint(
            [
                _con("Coincident", line, 1, curve, 3),
                _con("Coincident", line, 2, point[0], point[1]),
                _con("PointOnObject", point[0], point[1], curve),
                _con("Symmetric", curve, 1, curve, 2, line),
            ]
        )
        sketch.solve()
        if any(
            abs(sketch.calculateConstraintError(i)) > 1e-6
            for i in range(first, len(sketch.Constraints))
        ):
            raise ValueError("the point cannot reach the arc's middle")
        return None


# -- Parallel -------------------------------------------------------------------------------------
class Parallel(PickConstraint):
    title = "Parallel"
    command = "Fission180_SketchParallel"
    takes = "two lines"

    def prompt(self):
        return "click the first line." if not self.picks else "click the line to turn."

    def fits(self, picks, item):
        return item[1] == 0 and self.kind_of(item) in LINE and item not in picks

    def forms(self, picks):
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        return [[_con("Parallel", a, b)]]


# -- Perpendicular --------------------------------------------------------------------------------
class Perpendicular(PickConstraint):
    """Two lines at a right angle; a line and a circle or arc: the line through its centre;
    curves that share an end: square to each other there."""

    title = "Perpendicular"
    command = "Fission180_SketchPerpendicular"
    takes = "two lines, or a line and a curve"

    def prompt(self):
        return "click the first line or curve." if not self.picks else "click the other one."

    def fits(self, picks, item):
        if item[1] != 0 or item in picks:
            return False
        kind = self.kind_of(item)
        if kind not in CURVES:
            return False
        if not picks:
            return True
        first = self.kind_of(picks[0])
        if first in LINE and kind in LINE:
            return True
        # with a curve: the solver knows a line through a circle's centre, or curves
        # square to each other at a shared end
        return True

    def forms(self, picks):
        sketch = self.sketch
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        ka, kb = self.kind_of(picks[0]), self.kind_of(picks[1])
        if ka in LINE and kb in LINE:
            return [[_con("Perpendicular", a, b)]]
        forms = []
        near = _closest_ends(sketch, a, b)
        if near is not None and near[2] <= TOUCH:
            forms.append([_con("Perpendicular", a, near[0], b, near[1])])
        plain = (ka in LINE and kb in CIRCULAR) or (kb in LINE and ka in CIRCULAR)
        if plain or (ka in CIRCULAR and kb in CIRCULAR):
            forms.append([_con("Perpendicular", a, b)])
        if not forms:
            raise ValueError(
                "%s and %s must share an end point to be perpendicular there: join them "
                "first (Coincident)." % (_name(sketch, picks[0]), _name(sketch, picks[1]))
            )
        return forms


# -- Horizontal / Vertical ------------------------------------------------------------------------
class HorizontalVertical(PickConstraint):
    """Fusion's Horizontal/Vertical: a line, or two points, snap to the horizontal or the
    vertical, whichever is closest to how they are (Autodesk help). For two points, when the
    closest cannot be (it conflicts) and the other fits, the other is made and said."""

    title = "Horizontal/Vertical"
    command = "Fission180_SketchHorizontalVertical"
    points_ok = True
    takes = "a line, or two points"

    def prompt(self):
        if not self.picks:
            return "click a line, or a point and then a second point."
        return "click the point to line up with it."

    def fits(self, picks, item):
        if item in picks:
            return False
        kind = self.kind_of(item)
        if not picks:
            return (kind in LINE and item[0] >= 0) or kind == POINT
        return kind == POINT and item != picks[0]

    def why_not(self, picks, item):
        if item is not None and not picks and item[0] in (-1, -2) and item[1] == 0:
            return "the axes are horizontal and vertical already. Click a line or a point."
        if item is not None and picks and item[1] == 0:
            return "a point is picked: click the second point to line up with it."
        if item is not None and item[1] == 0 and item[0] < -2:
            return "a projected line follows the part and cannot be turned. Click a sketch line."
        return PickConstraint.why_not(self, picks, item)

    def complete(self, picks):
        return bool(picks) and (picks[0][1] == 0 or len(picks) >= 2)

    def plan(self, selection):
        lines = [[i] for i in selection if i[1] == 0 and self.fits([], i)]
        points = [i for i in selection if i[1] != 0]
        pairs = [[points[0], p] for p in points[1:]] if len(points) >= 2 else []
        return lines + pairs

    def _delta(self, picks):
        if picks[0][1] == 0:
            g = self.sketch.Geometry[picks[0][0]]
            d = g.EndPoint - g.StartPoint
            return d.x, d.y
        p, q = point_of(self.sketch, picks[0]), point_of(self.sketch, picks[1])
        return q[0] - p[0], q[1] - p[1]

    def _constraint(self, name, picks):
        if picks[0][1] == 0:
            return _con(name, picks[0][0])
        (a, pa), (b, pb) = picks
        return _con(name, a, pa, b, pb)

    def constrain_one(self, picks):
        sketch = self.sketch
        if len(picks) == 2:
            if self._fixed(picks[0]) and self._fixed(picks[1]):
                return Outcome(False, "%s: %s." % (self.title, BOTH_FIXED))
            if picks[0][0] == picks[1][0] and picks[0][0] >= 0:
                kind = draw._type_of(sketch, picks[0][0])
                if kind in LINE:
                    picks = [(picks[0][0], 0)]  # a line's two ends: the line itself
        dx, dy = self._delta(picks)
        name = core.hv_choice(dx, dy)
        # (a refusal says which of the two it was: "Vertical: not added, it conflicts...")
        outcome = add_forms(sketch, name, [[self._constraint(name, picks)]])
        if outcome.ok or len(picks) != 2 or outcome.kind != "conflict":
            return outcome
        other = core.other_hv(name)
        second = add_forms(sketch, other, [[self._constraint(other, picks)]])
        if not second.ok:
            return outcome
        culprits, _count = explain.words(sketch, outcome.culprits)
        why = (" (it conflicts with %s)" % culprits) if culprits else ""
        second.note = (
            "Horizontal/Vertical: the points are nearer to %s, but that does not fit%s: "
            "made %s instead. Undo if that is not what you want."
            % (name.lower(), why, other.lower())
        )
        return second


# -- Tangent --------------------------------------------------------------------------------------
SPLINE_NOTE = (
    "Tangent: a spline can only be made tangent at one of its ends (FreeCAD's sketch solver "
    "has no tangency along a spline): its nearest end was joined to %s and made tangent there."
)


class Tangent(PickConstraint):
    title = "Tangent"
    command = "Fission180_SketchTangent"
    replace_first = True  # joined ends: the end-to-end tangency takes the join's place
    takes = "two curves (at least one of them a circle, arc, ellipse or spline)"

    def prompt(self):
        return "click the first curve." if not self.picks else "click the curve to touch it."

    def fits(self, picks, item):
        if item[1] != 0 or item in picks:
            return False
        kind = self.kind_of(item)
        if kind not in CURVES:
            return False
        if picks and kind in LINE and self.kind_of(picks[0]) in LINE:
            return False
        return True

    def why_not(self, picks, item):
        if item is not None and picks and item[1] == 0 and self.kind_of(item) in LINE:
            if self.kind_of(picks[0]) in LINE:
                return (
                    "two lines cannot be tangent (Collinear puts them on one line). Click a "
                    "circle, arc or spline."
                )
        return PickConstraint.why_not(self, picks, item)

    def plan(self, selection):
        pairs = core.plan_pairs(selection, self.fits)
        if pairs or len(selection) != 1 or selection[0][1] == 0:
            return pairs
        # one corner selected: the two curves that meet there (FreeCAD's own Tangent took a
        # shared end point too)
        p = point_of(self.sketch, selection[0])
        meeting = []
        if p is not None:
            helpers = build.internal_geometry(self.sketch)  # (hidden helper lines too)
            for geo in range(len(self.sketch.Geometry)):
                if geo in helpers:
                    continue
                for end in _ends(self.sketch, geo).values():
                    if math.hypot(end.x - p[0], end.y - p[1]) <= TOUCH:
                        meeting.append((geo, 0))
                        break
        if len(meeting) == 2 and self.fits([meeting[0]], meeting[1]):
            return [meeting]
        return []

    def _spline_form(self, spline, other):
        """A spline's nearest end onto `other` and tangent there: (constraints, joined)."""
        sketch = self.sketch
        near = _closest_ends(sketch, spline, other)
        on = _end_on_curve(sketch, spline, other)
        if near is not None and (on is None or near[2] <= on[1] + TOUCH):
            return [_con("Tangent", spline, near[0], other, near[1])], near[2] > TOUCH
        if on is not None:
            return [_con("Tangent", spline, on[0], other)], on[1] > TOUCH
        raise ValueError("that spline has no end to make tangent.")

    def forms(self, picks):
        sketch = self.sketch
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        ka, kb = self.kind_of(picks[0]), self.kind_of(picks[1])
        self._joined = None
        if ka in SPLINE or kb in SPLINE:
            spline, other = (a, b) if ka in SPLINE else (b, a)
            form, joined = self._spline_form(spline, other)
            if joined:
                self._joined = _name(sketch, (other, 0))
            return [form]
        forms = []
        near = _closest_ends(sketch, a, b)
        if near is not None and near[2] <= TOUCH:
            # joined ends: FreeCAD's end-to-end tangency says the join too (the Coincident
            # it repeats goes, add_forms)
            forms.append([_con("Tangent", a, near[0], b, near[1])])
        else:
            for one, other in ((a, b), (b, a)):
                on = _end_on_curve(sketch, one, other)
                if on is not None and on[1] <= TOUCH:
                    forms.append([_con("Tangent", one, on[0], other)])
                    break
        forms.append([_con("Tangent", a, b)])
        return forms

    def note(self, picks):
        joined = getattr(self, "_joined", None)
        return (SPLINE_NOTE % joined) if joined else None


# -- Equal ----------------------------------------------------------------------------------------
class Equal(PickConstraint):
    title = "Equal"
    command = "Fission180_SketchEqual"
    takes = "two lines, or two circles or arcs"

    def prompt(self):
        if not self.picks:
            return "click a line, circle or arc."
        return "click the one to make the same size."

    def _class(self, item):
        if item[1] != 0:
            return None
        kind = self.kind_of(item)
        if kind in LINE:
            return "line"
        if kind in CIRCULAR:
            return "round"
        if kind in ("Part::GeomEllipse", "Part::GeomArcOfEllipse"):
            return "ellipse"
        return None

    def fits(self, picks, item):
        cls = self._class(item)
        if cls is None or item in picks or item[0] in (-1, -2):
            return False
        return not picks or self._class(picks[0]) == cls

    def why_not(self, picks, item):
        if item is not None and picks and self._class(item) not in (None, self._class(picks[0])):
            return "a line and a circle have no size to share: click another %s." % (
                "line" if self._class(picks[0]) == "line" else "circle or arc"
            )
        return PickConstraint.why_not(self, picks, item)

    def plan(self, selection):
        return core.plan_by_class(selection, self._class, self.fits)

    def forms(self, picks):
        (a, _), (b, _) = picks
        if a < 0 and b < 0:
            raise ValueError(BOTH_FIXED)
        return [[_con("Equal", a, b)]]


# -- Symmetry -------------------------------------------------------------------------------------
class Symmetry(PickConstraint):
    """Fusion's Symmetry: the two things, then the line they mirror about (Autodesk help:
    "select the sketch geometry you want to constrain, then select the line of symmetry").
    Two points, two lines, two circles or two arcs. (FreeCAD's own tool knows only two
    points; two points about a third point still works here.)"""

    title = "Symmetry"
    command = "Fission180_SketchSymmetry"
    needs = 3
    points_ok = True
    takes = "two points, two lines, two circles or two arcs, then the line to mirror about"

    def prompt(self):
        if not self.picks:
            return "click the first point, line, circle or arc."
        if len(self.picks) == 1:
            return "click the one that mirrors it."
        return "click the line to mirror about."

    def _class(self, item):
        if item[1] != 0:
            return POINT
        kind = self.kind_of(item)
        if kind in LINE:
            return "line"
        if kind == "Part::GeomCircle":
            return "circle"
        if kind == "Part::GeomArcOfCircle":
            return "arc"
        return None

    def fits(self, picks, item):
        if item in picks:
            return False
        cls = self._class(item)
        if cls is None:
            return False
        if not picks:
            return item[0] not in (-1, -2) or item[1] != 0  # (an axis mirrors, it is not mirrored)
        if len(picks) == 1:
            return cls == self._class(picks[0])
        if cls == "line":
            return True
        return cls == POINT and self._class(picks[0]) == POINT  # two points about a point

    def why_not(self, picks, item):
        if (
            item is not None
            and len(picks) == 1
            and self._class(item)
            not in (
                None,
                self._class(picks[0]),
            )
        ):
            return "the second must be the same kind of thing as the first (%s)." % _kind_word(
                self.kind_of(picks[0])
            )
        if item is not None and len(picks) == 2 and self._class(item) != "line":
            return "click the LINE to mirror about (a construction line or an axis)."
        return PickConstraint.why_not(self, picks, item)

    def plan(self, selection):
        sketch = self.sketch
        construction = []
        for item in selection:
            try:
                if item[1] == 0 and item[0] >= 0 and sketch.getConstruction(item[0]):
                    construction.append(item)
            except Exception:
                pass
        planned = core.plan_symmetry(
            selection,
            lambda i: i[1] != 0,
            lambda i: i[1] == 0 and self.kind_of(i) in LINE,
            construction,
        )
        if planned is None:
            return []
        picks = []
        for item in planned:
            if not self.fits(picks, item):
                return []
            picks.append(item)
        return [picks]

    def forms(self, picks):
        sketch = self.sketch
        a, b, mirror = picks
        if all(self._fixed(i) for i in (a, b)):
            raise ValueError(BOTH_FIXED)
        cls = self._class(a)
        m = mirror[0]
        if cls == POINT:
            if mirror[1] != 0:
                return [[_con("Symmetric", a[0], a[1], b[0], b[1], m, mirror[1])]]
            return [[_con("Symmetric", a[0], a[1], b[0], b[1], m)]]
        if m in (a[0], b[0]):
            raise ValueError("the line to mirror about cannot be one of the two mirrored.")
        origin, direction = _line_frame(sketch, m)
        ga, gb = a[0], b[0]
        if cls == "line":
            a1, a2 = point_of(sketch, (ga, 1)), point_of(sketch, (ga, 2))
            b1, b2 = point_of(sketch, (gb, 1)), point_of(sketch, (gb, 2))
            p1, p2 = core.pair_ends(a1, a2, b1, b2, origin, direction)
            pairs = [((ga, 1), (gb, p1)), ((ga, 2), (gb, p2))]
            full = [_con("Symmetric", p[0], p[1], q[0], q[1], m) for p, q in pairs]
            forms = [full]
            # lines that meet on the mirror line: that shared corner cannot mirror itself
            # (the solver calls it redundant): it only has to be on the line
            for k, (p, q) in enumerate(pairs):
                pp, qq = point_of(sketch, p), point_of(sketch, q)
                if math.hypot(pp[0] - qq[0], pp[1] - qq[1]) <= TOUCH:
                    forms.insert(0, [full[1 - k], _con("PointOnObject", p[0], p[1], m)])
                    forms.append([full[1 - k]])
            return forms
        centres = _con("Symmetric", ga, 3, gb, 3, m)
        if cls == "circle":
            return [[centres, _con("Equal", ga, gb)], [centres]]
        ends = [_con("Symmetric", ga, 1, gb, 2, m), _con("Symmetric", ga, 2, gb, 1, m)]
        return [ends + [_con("Equal", ga, gb)], ends, [centres, _con("Equal", ga, gb)]]

    def holds(self, picks):
        sketch = self.sketch
        a, b, mirror = picks
        try:
            cls = self._class(a)
            if cls == POINT:
                return True
            origin, direction = _line_frame(sketch, mirror[0])
            ga, gb = _geo(sketch, a[0]), _geo(sketch, b[0])
            if cls == "line":
                a1, a2 = _xy(ga.StartPoint), _xy(ga.EndPoint)
                b1, b2 = _xy(gb.StartPoint), _xy(gb.EndPoint)
                return (
                    core.is_mirror(a1, b1, origin, direction, TOUCH)
                    and core.is_mirror(a2, b2, origin, direction, TOUCH)
                ) or (
                    core.is_mirror(a1, b2, origin, direction, TOUCH)
                    and core.is_mirror(a2, b1, origin, direction, TOUCH)
                )
            if abs(ga.Radius - gb.Radius) > TOUCH:
                return False
            if not core.is_mirror(_xy(ga.Center), _xy(gb.Center), origin, direction, TOUCH):
                return False
            if cls == "arc":
                return core.is_mirror(
                    _xy(ga.StartPoint), _xy(gb.EndPoint), origin, direction, TOUCH
                ) and core.is_mirror(_xy(ga.EndPoint), _xy(gb.StartPoint), origin, direction, TOUCH)
            return True
        except Exception:
            return False


# -- Fix / Unfix ----------------------------------------------------------------------------------
class Fix(PickConstraint):
    """Fusion's Fix/Unfix: a click on a curve or point fixes it where it is (it turns green),
    a click on a fixed one frees it. With a selection: everything in it that is not fixed
    yet gets fixed (the fixed ones stay so); when all of it is fixed, all of it is freed.
    FreeCAD's Block for a curve, its Lock (a horizontal and a vertical distance from the
    origin) for a point."""

    title = "Fix/Unfix"
    command = "Fission180_SketchFix"
    needs = 1
    points_ok = True
    takes = "curves and points of this sketch"

    def prompt(self):
        return "click a curve or point to fix it where it is (a fixed one: to free it)."

    def fits(self, picks, item):
        return item[0] >= 0

    def why_not(self, picks, item):
        if item is not None and item[0] < 0:
            return "the axes, the origin and projected geometry are always fixed."
        return PickConstraint.why_not(self, picks, item)

    def item_at(self, snap):
        item = PickConstraint.item_at(self, snap)
        if item is not None and item[1] != 0 and item[0] >= 0:
            # a sketch point of its own (CREATE > Point) is fixed whole, like a curve
            if draw._type_of(self.sketch, item[0]) == "Part::GeomPoint":
                return (item[0], 0)
        return item

    def plan(self, selection):
        items = []
        for item in selection:
            if item[0] < 0:
                continue
            if item[1] != 0 and draw._type_of(self.sketch, item[0]) == "Part::GeomPoint":
                item = (item[0], 0)
            if item not in items:
                items.append(item)
        return [items] if items else []

    # FreeCAD's forms
    def _blocks(self):
        return {c.First: i for i, c in enumerate(self.sketch.Constraints) if c.Type == "Block"}

    def _locks(self, item):
        """The indices of the two distances from the origin that lock point `item`."""
        found = {}
        for i, c in enumerate(self.sketch.Constraints):
            if c.Type in ("DistanceX", "DistanceY") and c.First == -1 and c.FirstPos == 1:
                if (c.Second, c.SecondPos) == tuple(item) and c.Type not in found:
                    found[c.Type] = i
        return [found["DistanceX"], found["DistanceY"]] if len(found) == 2 else []

    def is_fixed(self, item):
        if item[1] == 0:
            return item[0] in self._blocks()
        return bool(self._locks(item)) or item[0] in self._blocks()

    def _fix(self, item):
        sketch = self.sketch
        if item[1] == 0:
            return add_forms(sketch, "Fix", [[_con("Block", item[0])]])
        p = point_of(sketch, item)
        return add_forms(
            sketch,
            "Fix",
            [
                [
                    _con("DistanceX", -1, 1, item[0], item[1], p[0]),
                    _con("DistanceY", -1, 1, item[0], item[1], p[1]),
                ]
            ],
        )

    def _unfix(self, item):
        sketch = self.sketch
        if item[1] == 0 or not self._locks(item):
            indices = [self._blocks()[item[0]]]
        else:
            indices = self._locks(item)
        for i in sorted(indices, reverse=True):
            sketch.delConstraint(i, True)
        sketch.solve()

    def constrain_one(self, picks):
        sketch = self.sketch
        action, items = core.fix_plan(picks, self.is_fixed)
        if action == "unfix":
            for item in items:
                self._unfix(item)
            what = _name(sketch, items[0]) if len(items) == 1 else "%d things" % len(items)
            return Outcome(True, note="Fix/Unfix: %s freed (no longer fixed)." % what)
        fixed, refused = 0, None
        for item in items:
            outcome = self._fix(item)
            if outcome.ok:
                fixed += 1
            elif refused is None:
                refused = outcome
                refused.text = "Fix/Unfix: %s cannot be fixed: %s" % (
                    _name(sketch, item),
                    outcome.text.split(": ", 1)[-1],
                )
        if not fixed:
            return refused
        already = len(picks) - len(items)
        note = ""
        if refused is not None:
            note = "%s (%d fixed.)" % (refused.text, fixed)
        elif already:
            note = "Fix/Unfix: %d fixed (%d %s fixed already)." % (
                fixed,
                already,
                "was" if already == 1 else "were",
            )
        return Outcome(True, note=note, culprits=refused.culprits if refused else ())


# -- Curvature ------------------------------------------------------------------------------------
G2_NOTE = (
    "Curvature: FreeCAD's sketch solver has no curvature (G2) constraint for a spline and "
    "%s, so the two are made tangent (G1). A spline and a line join with matching curvature."
)


class Curvature(PickConstraint):
    title = "Curvature"
    command = "Fission180_SketchCurvature"
    takes = "a spline and the line, arc or spline it joins"

    def prompt(self):
        if not self.picks:
            return "click a spline, then the curve it joins."
        return (
            "click the curve joined to it."
            if self.kind_of(self.picks[0]) in SPLINE
            else ("click the spline joined to it.")
        )

    def fits(self, picks, item):
        if item[1] != 0 or item in picks or item[0] < 0:
            return False
        kind = self.kind_of(item)
        if not picks:
            return kind in SPLINE or kind in LINE_OR_ARC
        first = self.kind_of(picks[0])
        if first in SPLINE:
            return kind in LINE_OR_ARC or kind in SPLINE
        return kind in SPLINE

    def constrain(self, picks):
        sketch = self.sketch
        a, b = picks[0][0], picks[1][0]
        spline, other = (a, b) if self.kind_of(picks[0]) in SPLINE else (b, a)
        near = _closest_ends(sketch, spline, other)
        s_pos, o_pos = near[0], near[1]
        sketch.addConstraint(_con("Tangent", spline, s_pos, other, o_pos))
        kind = self.kind_of((other, 0))
        if kind in LINE and sketch.Geometry[spline].NbPoles >= 4:
            # tangent: the second pole is on the line already; curvature 0 at the join
            # (G2 with a line): the third pole on the line too
            pole = _pole_circle(sketch, spline, 2 if s_pos == 1 else -3)
            if pole is None:
                raise ValueError("the spline's control points are not shown")
            sketch.addConstraint(_con("PointOnObject", pole, 3, other))
            return None
        if kind in LINE:
            what = "a line (a spline of three control points cannot flatten at its end)"
        else:
            what = "an arc" if kind == "Part::GeomArcOfCircle" else "another spline"
        return G2_NOTE % what


def _pole_circle(sketch, spline, index):
    """The construction circle of the spline's pole `index` (negative from the end),
    shown first when the spline's control points are hidden."""
    poles = build.conic_poles(sketch, spline)
    g = sketch.Geometry[spline]
    if len(poles) != g.NbPoles:
        try:
            sketch.exposeInternalGeometry(spline)
        except Exception as exc:
            warn("Curvature: %s" % exc)
        poles = build.conic_poles(sketch, spline)
    if len(poles) != g.NbPoles or not poles:
        return None
    return poles[index]


TOOLS = {
    cls.command: cls
    for cls in (
        Coincident,
        Collinear,
        Concentric,
        Midpoint,
        Fix,
        Parallel,
        Perpendicular,
        HorizontalVertical,
        Tangent,
        Curvature,
        Equal,
        Symmetry,
    )
}
