# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, fix-4: the Pizza Cutter's handle profile, the same way every time.

The book replay (replay_12_pizza_cutter) failed once on the merged develop and passed on
its retry: the Wooden Handle's last dimension (a flat, 0.25 in) came out driven, "already
set by the Coincident between Line 1 and Projected Curve 1". That Coincident is the book's
own (the handle starts at the End Cap's projected rim; it is there in every run, nothing
was projected by a passing pointer). What differed was the sketch the dimensions met: the
same profile with the same constraints solved to a different shape on every run (the
flats 0.15 to 0.30 in long before their dimension; once 0.01 in, a flat 2 pixels long, so
the click on its middle took its corner). FreeCAD's solver, for a sketch that is not fully
constrained, takes a step that depends on where in memory its numbers happen to lie.
Fission 180 now has it take the step that moves the curves the least
(sketch_mode.PARAMS, "DogLegGaussStep"), which does not. (One more such dependence is
left in FreeCAD's solver: a new Equal between two circles' sizes, Horizontal / Vertical
between two points, Coincident, starts from one of the two values, whichever lies higher
in memory; the replay's Equal on the arcs gave one of four shapes. The replay zooms in on
the flat before dimensioning it, as a person does with a piece too small to click.)

The End Cap is a stand-in: a round head 1.00 across whose flat face lies 0.25 in along X
(the replay's head, without its shank). Then the replay's own steps for the handle, by
real input with a person's defaults (replay_12_handle_steps): New Component, a sketch on
the Front plane, Project (P) of the head's face, the profile drawn on the grid, Collinear
and Equal on the flats; then
  A  Equal on the four flats is undone (Ctrl+Z) and made again four more times: the flats
     come out exactly as long each time (before fix-4: five different lengths, 0.16 to
     0.20 in)
  B  the rest of the book's constraints and dimensions (Equal arcs, Horizontal centres,
     R1.5, 4.00, 0.25, then the flat 0.25 with the view zoomed in on it): the profile is
     the book's and fully constrained.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_12_handle_steps as handle
from Fission180Tests.gui import replay_e_steps as r

V = App.Vector
IN = r.IN
S = r.S
REPEATS = 4


def new_design():
    r.user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Fix4Handle")
    from fission180 import design_units

    # an inch design, set as the default (the replay does it with Change Active Units)
    design_units.set_units(App.ActiveDocument, 3, as_default=True)
    # the End Cap's head: a disc 1.00 across, 0.25 thick, its axis along X
    cap = k.new_component("End Cap")
    cap.Placement = App.Placement(V(0, 0, 0), App.Rotation(V(0, 1, 0), 90))
    k.add_cylinder(cap, (0, 0), 0.5 * IN, 0.25 * IN)
    k.settle_design()


def solver_setting():
    from fission180 import sketch_mode

    step = App.ParamGet(sketch_mode.SOLVER_ADVANCED).GetInt("DogLegGaussStep", 0)
    h.check(
        "the sketch solver moves the curves the least it can (least-norm step)",
        step == sketch_mode.LEAST_NORM_STEP,
        step,
    )


def flat_lengths():
    sketch = r.sk()
    return [sketch.Geometry[i].length() / IN for i in handle.flats()]


def first_equal():
    S["fix4_flats"] = [flat_lengths()]
    S["fix4_cons"] = len(r.sk().Constraints)


def undo():
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def undone():
    added = S["fix4_cons"] - len(r.sk().Constraints)
    h.check("Ctrl+Z takes the three Equal constraints out", added == 3, added)


def again_done():
    r.stop_tool()
    S["fix4_flats"].append(flat_lengths())


def same_every_time():
    runs = S["fix4_flats"]
    first = runs[0]
    h.check(
        "A: Equal on the same flats gives the same flats every time (%d tries)" % len(runs),
        all(max(abs(a - b) for a, b in zip(first, other)) < 1e-9 for other in runs),
        [[round(x, 6) for x in run] for run in runs],
    )


def again(n):
    out = [r.named("a_undo_%d" % n, undo), r.named("a_undone_%d" % n, undone)]
    out += handle.select(handle.flats, "a_pick_flats_%d" % n)
    out += [r.menu("CONSTRAINTS", "Equal", "a_equal_%d" % n), r.named("a_done_%d" % n, again_done)]
    return out


def steps():
    out = [new_design, solver_setting]
    replay = handle.steps()
    names = [step.__name__ for step in replay]
    upto = replay[: names.index("handle_finish")]  # the sketch, up to its last check
    cut = names.index("equal_flats_done") + 1
    out += upto[:cut] + [first_equal]
    for n in range(1, REPEATS + 1):
        out += again(n)
    out += [same_every_time]
    out += upto[cut:]
    return out


h.run("fix4_handle_projection", steps(), paced_by="state")
