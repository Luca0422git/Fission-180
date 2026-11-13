# SPDX-License-Identifier: LGPL-2.1-or-later
"""ASSEMBLE's commands for an AI, through the real MCP server and Fission 180's AI bridge, as an
AI app calls them (wave 8, builder ai-design; Fission180Tests/gui/ai_design_steps.py).

Path 1, AI control on, the MCP server started, its tool list has the new ASSEMBLE tools.
Path 2, an arm on a base built with joints the AI makes WHERE THE PARTS STAND (as-built
  revolute, slider and rigid), a cap locked to the arm (rigid group), the slider tied to the
  arm (motion link: the arm turned 10 degrees moves the slider 1 mm and turns the cap 10),
  a contact set (the arm turned -45 stops on the stop), Capture Position / Revert Position,
  a joint origin, a pin joined and duplicated into the second hole, a motion study that
  reports the arm at 20, 25, 30 degrees and leaves the assembly as it was: every check of
  the headless run (design_tools.ASSEMBLY), on the design in the window.
Path 3, each change is one Undo step named AI: ...; Undo takes Contact off and the motion study
  back, Redo brings them again.
Path 4, Display Component Colors switched on by the AI draws the colours in the window (and
  off again); the answer gives each component's colour.
Path 5, a changing call while a command dialog is open is refused ("Fission 180 is busy").
Path 6, AI control off again.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets
from Fission180Tests.gui import ai_design_steps as ai
from Fission180Tests.gui import harness as h


def start():
    ai.start()
    ai.offers(
        "as_built_joint",
        "joint_origin",
        "rigid_group",
        "motion_link",
        "contact",
        "position",
        "duplicate_with_joints",
        "motion_study",
        "component_colors",
    )


def assembly_built():
    from Fission180Tests.headless import design_tools

    # (the last call checks the headless refusal of the window-only option: Path 4 here)
    calls = [c for c in design_tools.ASSEMBLY if c["args"] != {"on": True}]
    ai.run_calls(calls, "assembly")
    from fission180 import joints

    doc = App.ActiveDocument
    h.check(
        "the design has the rigid group, the motion link, the contact set, the study",
        bool(joints.rigid_groups(doc))
        and bool(joints.motion_links(doc))
        and bool(joints.contact_sets(doc))
        and bool(joints.motion_studies(doc)),
    )
    h.check("... and a captured Position step", bool(joints.positions(doc)))
    ai.show_all("assembly")
    h.shot("ai-design-assembly")


assembly_built.timeout_s = 240  # (some 45 calls through the bridge)


def undo_redo():
    from fission180 import joints

    ai.ai_steps_only("assembly")
    doc = App.ActiveDocument
    names = ai.undo_names()
    h.check(
        "the last steps are Contact off and the motion study",
        names[:2] == ["AI: Contact off", "AI: Motion study"],
        names[:3],
    )
    answer = ai.call("undo", {})
    h.check("undo answers", not answer["is_error"], answer["text"])
    h.check("Undo put contact sets on again", joints.contact_mode(doc) == "sets")
    answer = ai.call("undo", {})
    h.check("Undo again took the motion study away", not joints.motion_studies(doc))
    ai.call("redo", {})
    answer = ai.call("redo", {})
    h.check("redo answers", not answer["is_error"], answer["text"])
    h.check(
        "Redo brought both back",
        bool(joints.motion_studies(doc)) and joints.contact_mode(doc) == "off",
    )


def component_colours():
    from fission180 import component_colors_ui

    doc = App.ActiveDocument
    answer = ai.call("component_colors", {"on": True})
    h.check("component_colors on answers", not answer["is_error"], answer["text"][:300])
    h.check("... Display Component Colors is on in the window", component_colors_ui.is_on(doc))
    h.check(
        "... and the answer names each component's colour",
        "Arm" in answer["text"] and "#" in answer["text"],
    )
    h.shot("ai-design-component-colours")
    answer = ai.call("component_colors", {"on": False})
    h.check("... and off again", not component_colors_ui.is_on(doc), answer["text"][:200])


class _Panel:
    """A command dialog (as Fission 180's own commands show in the task panel)."""

    def __init__(self):
        self.form = QtWidgets.QLabel("A command is open")

    def reject(self):
        return True


def refused_while_busy():
    Gui.Control.showDialog(_Panel())
    try:
        answer = ai.call("rigid_group", {"components": ["Base", "Stop"]})
        h.check(
            "a changing call is refused while a dialog is open", answer["is_error"], answer["text"]
        )
        h.check("... Fission 180 is busy", "Fission 180 is busy" in answer["text"], answer["text"])
        answer = ai.call("get_design", {})
        h.check(
            "... a call that only reads still runs", not answer["is_error"], answer["text"][:200]
        )
    finally:
        Gui.Control.closeDialog()


def stop():
    ai.stop()


h.run(
    "ai_design_assembly",
    [start, assembly_built, undo_redo, component_colours, refused_while_busy, stop],
    paced_by="state",
)
