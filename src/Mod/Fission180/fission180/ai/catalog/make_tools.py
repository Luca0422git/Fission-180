# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for UTILITIES > MAKE (wave 8, builder ai-workspaces): print_part (Fusion's 3D Print:
the bodies to a slicer, or a print file) and export_everything (Fission 180's Export
Everything). The work is in fission180/ai/actions/make_actions.py, on the same code as the
commands (fission180/export.py, slicer_core.py, export_ui.py). Pure Python."""

from .kit import enum, schema, step_ids, string
from .registry import define, example

# (export.PRINT_FORMATS, export.REFINEMENTS but Custom, export.UNIT_NAMES: a unit test compares)
PRINT_FORMATS = ("3MF", "STL (Binary)", "STL (ASCII)", "OBJ")
REFINEMENTS = ("Low", "Medium", "High")
UNIT_NAMES = ("Millimeter", "Centimeter", "Meter", "Inch", "Foot")
SLICER_IDS = ("prusaslicer", "bambustudio", "orcaslicer", "cura")  # (slicer_core.SLICERS)


def _extra_print(args, problems):
    target = args.get("send_to", "file")
    if target == "file" and "path" not in args:
        problems.append('send_to "file" needs path: where to save the print file')
    if target != "file":
        for key in ("path", "unit"):
            if key in args:
                problems.append('%s is for send_to "file" (a slicer always gets millimetres)' % key)


define(
    "print_part",
    "3D print",
    "import_export",
    "UTILITIES > MAKE > 3D Print",
    "Fusion's 3D Print: the bodies as one mesh file for 3D printing. send_to file (default: "
    "save it at path, a full path or a folder; unit Millimeter by default) | slicer (open it "
    "in the person's slicer: the one picked in Preferences > 3D Print, else the first found "
    "on this computer) | prusaslicer | bambustudio | orcaslicer | cura (that slicer, when "
    "installed). The person is asked before a slicer starts; it needs the window. bodies: "
    "step ids (default: every shown body with a solid, and the mesh bodies). format 3MF "
    "(default: names and unit kept) | STL (Binary) | STL (ASCII) | OBJ; refinement Low | "
    "Medium (default) | High: how finely curved faces are cut into triangles. Answers the "
    "file, the triangles, whether each body is watertight (open edges make a slicer "
    "complain: check_design / mesh repair first) and what the file leaves out. About 10 s for "
    "a part of 1,500 faces (270,000 triangles), twice that at High. "
    "A file that exists is not replaced unless the person agrees. export writes other "
    "formats (STEP...).",
    schema(
        {
            "send_to": enum(("file", "slicer") + SLICER_IDS, "where it goes", default="file"),
            "path": string("send_to file: the file to write, or its folder (a full path)"),
            "bodies": step_ids("the bodies to print (default: every shown body)"),
            "format": enum(PRINT_FORMATS, "the file type", default="3MF"),
            "unit": enum(
                UNIT_NAMES, "send_to file: the unit the file counts in", default="Millimeter"
            ),
            "refinement": enum(REFINEMENTS, "how fine the triangles are", default="Medium"),
        }
    ),
    extra=_extra_print,
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("design",),
    title_fn=lambda a: "AI: 3D Print",
    examples=[
        example({"path": "~/prints"}, "a 3MF of every body in ~/prints"),
        example({"send_to": "slicer", "refinement": "High"}, "open it in the person's slicer"),
        example(
            {"path": "~/prints/bracket.stl", "format": "STL (Binary)", "bodies": ["Extrude1"]},
            "one body as an STL",
        ),
    ],
)

define(
    "export_everything",
    "Export everything",
    "import_export",
    "UTILITIES > MAKE > Export Everything",
    "Write the whole design in every open format at once (Fission 180's Export Everything): "
    "STEP (solids; a mesh body has none), STL, 3MF and OBJ of every shown body, a picture of "
    "the view (with the window) and a README saying what each file is, in folder (a full "
    'path; default: "<design>-export" beside the saved design file). Use it to hand a '
    "design to someone with another program, or to keep a copy any CAD can open; export "
    "writes one file of one format. Answers every file with its size and what each format "
    "leaves out (timeline, parameters, colours...). About 25 s for a part of 1,500 faces. "
    "Files that exist are not replaced unless the person agrees.",
    schema({"folder": string("the folder to write into (a full path; made when missing)")}),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("design",),
    title_fn=lambda a: "AI: Export Everything",
    examples=[
        example({}, "every format beside the saved design"),
        example({"folder": "~/handover/bracket"}, "into a folder of its own"),
    ],
)
