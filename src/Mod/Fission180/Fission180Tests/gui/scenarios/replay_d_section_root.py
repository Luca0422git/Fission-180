# SPDX-License-Identifier: LGPL-2.1-or-later
"""Section Analysis with the design's row active and every body inside a component (found by
the book replay, replay_10_fire_piston: the Fire Piston's section was gone after OK).

Section Analysis asks for a body to show the origin squares; the design's root has none, so
one is made, and its undo step "Add a Body" is still open when the dialog opens its own:
FreeCAD makes them one step. At OK the close saw no new step, took the command for a
cancelled one and undid the step, the section with the empty body. Now the empty body goes
inside the step at OK (commands.drop_unused_made_body).

A component "Part" with a box; the design's row active. INSPECT > Section Analysis, the
browser's XY row, OK: the section is kept, no empty body is left, no undo step is open.
Ctrl+Z takes the section away (and leaves no body), Ctrl+Y brings it back."""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import timeline_input as t

S = {}


def say(what):
    doc = App.ActiveDocument
    App.Console.PrintMessage(
        "[Fission 180] section_root %s: active %r pending %s undo %s names %s bodies %s\n"
        % (
            what,
            App.getActiveTransaction(),
            doc.HasPendingTransaction,
            doc.UndoCount,
            list(doc.UndoNames)[:4],
            [o.Name for o in doc.findObjects("PartDesign::Body")],
        )
    )


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Probe")
    part = k.new_component("Part")
    k.add_box(part, (0, 0, 40, 30), 10)
    k.settle_design()
    App.ActiveDocument.clearUndos()
    h.fit()
    say("setup")


def start():
    h.ribbon("Section Analysis")


def started():
    say("started")
    ins.expand_folder("Origin")


def pick():
    t.click_row("XY")


def picked():
    say("picked")
    h.task_button("OK")


def closed():
    from fission180 import section

    say("closed")
    doc = App.ActiveDocument
    h.check("the section is kept", len(section.sections(doc)) == 1)
    h.check("no empty body is left", len(doc.findObjects("PartDesign::Body")) == 1)
    h.check("no undo step is left open", h.open_undo_step() == "", h.open_undo_step())
    t.ctrl("z")


def undone():
    from fission180 import section

    say("undone")
    doc = App.ActiveDocument
    h.check("Ctrl+Z takes the section away", not section.sections(doc))
    h.check("...and leaves no body", len(doc.findObjects("PartDesign::Body")) == 1)
    t.ctrl("y")


def redone():
    from fission180 import section

    say("redone")
    doc = App.ActiveDocument
    h.check("Ctrl+Y brings it back", len(section.sections(doc)) == 1)
    h.check("...without a body", len(doc.findObjects("PartDesign::Body")) == 1)


h.run(
    "replay_d_section_root",
    [setup, start, started, pick, picked, closed, undone, redone],
    paced_by="state",
)
