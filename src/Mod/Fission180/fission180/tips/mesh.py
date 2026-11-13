# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the MESH tab (wave 8, builder tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by tools/fission180/tip_pictures_mesh.py).
The texts describe what Fission 180's own dialogs do (mesh_ui.py, mesh_cut_ui.py,
mesh_groups_ui.py, mesh_pick_ui.py, mesh_direct_ui.py, insert_ui.py), in plain words.
Insert Mesh is on the SOLID tab's INSERT group too, so its entry lives in tips/solid.py.
"""

TIPS = {
    "Fission180_MeshTessellate": {
        "summary": "Turn a solid body into a mesh body made of small triangles.",
        "what": (
            "Makes a mesh body from a solid body, so the MESH tools (Repair, Smooth, Reduce...) "
            "can work on it. Each face of the solid becomes a face group. The solid is used "
            "up by the step; Ctrl+Z brings it back."
        ),
        "steps": [
            "Click Tessellate, then click the solid body.",
            "Pick a Refinement: Low, Medium or High (higher means more, smaller triangles).",
            "Read the Number of Triangles in the dialog.",
            "Click OK.",
        ],
        "tips": [
            "Typing a deviation or a Maximum Edge Length switches Refinement to Custom.",
            "To 3D print a solid you do not need this: UTILITIES > 3D Print takes solids.",
        ],
        "picture": "mesh_tessellate.png",
    },
    "Fission180_MeshSectionSketch": {
        "summary": "Make a sketch of the outline where a plane cuts through a mesh body.",
        "what": (
            "Puts the line where a plane slices a mesh body into a new sketch, as fixed "
            "lines. Use it to rebuild a scanned or downloaded part as a real solid: extrude "
            "the section, or draw clean lines and arcs over it."
        ),
        "steps": [
            "Click the mesh body.",
            "Click a plane: an origin square, a construction plane or a flat face.",
            "Drag the arrow or type a Distance to move the cut; the section shows on the part.",
            "Click OK: a sketch named Mesh Section appears.",
        ],
        "tips": [
            "A closed section can be extruded straight away.",
            "The lines are fixed (green): draw your own lines over them for clean shapes.",
        ],
        "picture": "mesh_section_sketch.png",
    },
    "Fission180_MeshCreateFaceGroup": {
        "summary": "Paint over faces of a mesh body to make them one face group.",
        "what": (
            "A face group is an area of a mesh body that other tools pick as one piece, like a "
            "face of a solid. The faces you paint over become a new face group, drawn in its "
            "own colour. It is a step in the timeline."
        ),
        "steps": [
            "Click the mesh body.",
            "Click or drag over the faces: each click takes the faces within the Brush Size.",
            "Ctrl+click takes faces off again.",
            "Click OK.",
        ],
        "tips": [
            "Generate Face Groups makes all the groups at once from the shape.",
            "Direct Edit can do the same as one of its edits.",
        ],
        "picture": "mesh_create_face_group.png",
    },
    "Fission180_MeshFaceGroups": {
        "summary": "Split a mesh body into face groups by the way its faces point.",
        "what": (
            "Finds the flat and round areas of a mesh body and makes each one a face group, "
            "drawn in its own colour. Do this before Convert Mesh (prismatic) or before "
            "picking areas to smooth, separate or turn round."
        ),
        "steps": [
            "Click the mesh body.",
            "Pick a Method: Fast (by the angle between faces) or Accurate (fits planes, "
            "cylinders, spheres).",
            "Tick Preview to see the groups and read how many there are.",
            "Click OK.",
        ],
        "tips": [
            "Fast: a larger Angle Threshold makes fewer, bigger groups.",
        ],
        "picture": "mesh_face_groups.png",
    },
    "Fission180_MeshCombineFaceGroups": {
        "summary": "Join face groups of a mesh body that touch into one face group.",
        "what": (
            "Merges two or more face groups that share an edge into a single face group, for "
            "example when Generate Face Groups split one area in two. Groups that do not touch "
            "are refused with the reason."
        ),
        "steps": [
            "Click the mesh body.",
            "Click two or more face groups that touch (a click on a picked one drops it).",
            "Click OK: they show in one colour.",
        ],
        "tips": [
            "The body needs face groups first: PREPARE > Generate Face Groups.",
        ],
        "picture": "mesh_combine_face_groups.png",
    },
    "Fission180_MeshRepair": {
        "summary": "Fix a broken mesh: close holes, turn flipped faces, stitch cracks, rebuild.",
        "what": (
            "Scans and downloads often have holes or faces the wrong way round, so they cannot "
            "be printed or converted. Repair fixes them. The types go from gentle to strong: "
            "Close Holes, Stitch and Remove (the default), Wrap, Rebuild. The dialog lists the "
            "problems before and after."
        ),
        "steps": [
            "Click the mesh body (or right-click it in the browser > Repair).",
            "Pick a Repair Type; start with Stitch and Remove.",
            "Tick Preview and read the After line: closed, or what to try next.",
            "Click OK.",
        ],
        "tips": [
            "A yellow warning beside a body in the browser means it needs a repair.",
            "Rebuild makes a new closed surface; a higher Density keeps more detail.",
        ],
        "picture": "mesh_repair.png",
    },
    "Fission180_MeshRemesh": {
        "summary": "Rebuild the triangles of a mesh body, evenly sized or finer where needed.",
        "what": (
            "Replaces the triangles of a mesh body with new ones: Uniform gives triangles of a "
            "similar size, Adaptive puts small ones where there is detail. Use it to clean up "
            "long thin triangles before smoothing or converting."
        ),
        "steps": [
            "Click the mesh body.",
            "Pick a Remesh Type: Adaptive or Uniform.",
            "Set Density (higher means smaller triangles).",
            "Tick Preview to check, then click OK.",
        ],
        "tips": [
            "Preserve Sharp Edges keeps creases crisp.",
            "Big meshes can take a while: leave Preview off until the values are set.",
        ],
        "picture": "mesh_remesh.png",
    },
    "Fission180_MeshReduce": {
        "summary": "Use fewer triangles on a mesh body while keeping its shape.",
        "what": (
            "Lowers the number of triangles of a heavy mesh so it is quicker to work with or "
            "to convert. Choose by Tolerance (how far the shape may move), Proportion (the "
            "percent kept) or an exact Face Count."
        ),
        "steps": [
            "Click the mesh body.",
            "Pick a Reduce Target: Tolerance, Proportion or Face Count.",
            "Type the value; Preview shows the result.",
            "Click OK.",
        ],
        "tips": [
            "Reduce a big scan before Convert Mesh: the solid gets far fewer faces.",
        ],
        "picture": "mesh_reduce.png",
    },
    "Fission180_MeshPlaneCut": {
        "summary": "Trim a mesh body with a plane, or split it in two, closing the cut.",
        "what": (
            "Cuts a mesh body where a plane crosses it. Trim keeps one side, Split Body makes "
            "two bodies, Split Faces only cuts the faces along the plane. Fill Type closes the "
            "open cut so the body stays closed."
        ),
        "steps": [
            "Click the mesh body.",
            "Click a plane or a flat face.",
            "Drag the arrow (or type a Distance) and turn the handles to place the cut.",
            "Pick the Type and Fill Type; tick Flip to keep the other side.",
            "Click OK.",
        ],
        "tips": [
            "A plane that misses the body is refused: move it onto the part.",
        ],
        "picture": "mesh_plane_cut.png",
    },
    "Fission180_MeshShell": {
        "summary": "Hollow out a closed mesh body, leaving walls of a set thickness.",
        "what": (
            "Makes a closed mesh body hollow with an even wall inside, for example to save "
            "material and printing time. The wall is the surface moved inward by the "
            "Thickness."
        ),
        "steps": [
            "Click the closed mesh body.",
            "Type the Thickness of the wall.",
            "Tick Preview to check, then click OK.",
        ],
        "tips": [
            "A wall too thick for the part is refused with the thickest that fits.",
            "Open bodies cannot be shelled: Repair them first.",
        ],
        "picture": "mesh_shell.png",
    },
    "Fission180_MeshSmooth": {
        "summary": "Smooth rough, bumpy or creased areas of a mesh body.",
        "what": (
            "Evens out the surface of a mesh body, for example the noise of a 3D scan. "
            "Smoothness goes from 0 (a little) to 1 (a lot). With face groups you can smooth "
            "only some areas; their edges stay where they are."
        ),
        "steps": [
            "Click the mesh body.",
            "Optionally click face groups in the Face Groups box (all faces when none).",
            "Set Smoothness and tick Preview.",
            "Click OK.",
        ],
        "tips": [
            "Too much smoothing shrinks small details: go up a little at a time.",
        ],
        "picture": "mesh_smooth.png",
    },
    "Fission180_MeshCombine": {
        "summary": "Join, cut, intersect or merge two or more mesh bodies.",
        "what": (
            "Works like Combine for solids, on mesh bodies: Join adds the tools to the target, "
            "Cut takes them away, Intersect keeps the overlap, Merge puts them together as "
            "they are. The tools are used up unless Keep Tools is ticked."
        ),
        "steps": [
            "Click the Target Body.",
            "Click the Tool Bodies.",
            "Pick an Operation: Join, Cut, Intersect or Merge.",
            "Click OK.",
        ],
        "tips": [
            "Join, Cut and Intersect need closed bodies: Repair first, or use Merge.",
        ],
        "picture": "mesh_combine.png",
    },
    "Fission180_MeshSeparate": {
        "summary": "Split a mesh body into one body per loose piece or per face group.",
        "what": (
            "Makes several mesh bodies from one: one per separate shell (pieces that do not "
            "touch), one per face group, or only the face groups you pick. The pieces are named "
            "after the body, biggest first."
        ),
        "steps": [
            "Click the mesh body.",
            "Pick a Separate Type: Mesh Shells, All Face Groups or Select Face Groups.",
            "For Select Face Groups, click the groups.",
            "Click OK.",
        ],
        "tips": [
            "Tick Keep Body to keep the original as well.",
        ],
        "picture": "mesh_separate.png",
    },
    "Fission180_MeshReverseNormal": {
        "summary": "Turn the faces of a mesh body inside out (flip their normals).",
        "what": (
            "Every mesh face has an outside. When a body shows up inside out (dark, or flagged "
            "in the browser), Reverse Normal turns its faces round: the whole body, or only "
            "the face groups you pick."
        ),
        "steps": [
            "Click the mesh body.",
            "Optionally click face groups (all faces when none are picked).",
            "Click OK.",
        ],
        "tips": [
            "Single faces: Direct Edit > Reverse Normal.",
            "Repair also turns faces that disagree with their neighbours.",
        ],
        "picture": "mesh_reverse_normal.png",
    },
    "Fission180_MeshDirectEdit": {
        "summary": "Pick single faces of a mesh body and delete, fill, move or smooth them.",
        "what": (
            "Opens a dialog with a selection brush and edit buttons: Delete, Erase and Fill, "
            "Create Face Group, Reverse Normal, Move, Smooth. All edits made in one session "
            "become one step in the timeline, Mesh Base Feature."
        ),
        "steps": [
            "Click the mesh body.",
            "Paint over faces (or use Window or Free Form selection).",
            "Click an edit button: Delete, Move, Smooth...",
            "Repeat for other faces; Remove Last Edit takes one back.",
            "Click Finish Direct Edit.",
        ],
        "tips": [
            "Shift+Up / Shift+Down grow or shrink the picked faces.",
            "Esc or Cancel leaves the body as it was.",
        ],
        "picture": "mesh_direct_edit.png",
    },
    "Fission180_MeshEraseFill": {
        "summary": "Erase faces of a mesh body and fill the gap with new, smooth faces.",
        "what": (
            "Removes a bad area of a mesh body (a spike, a bump, a scanned clamp) and closes "
            "the hole it leaves with new faces. Uniform fills with even faces, Minimal with "
            "the fewest."
        ),
        "steps": [
            "Click the mesh body.",
            "Click the faces to erase: each click takes the faces within the Brush Size.",
            "Pick the fill Type: Uniform or Minimal.",
            "Click OK.",
        ],
        "tips": [
            "Ctrl+click takes faces off; Clear Faces starts again.",
        ],
        "picture": "mesh_erase_fill.png",
    },
    "Fission180_MeshDeleteFaces": {
        "summary": "Delete faces of a mesh body, leaving the hole open.",
        "what": (
            "Removes the faces you pick from a mesh body. The hole stays open (the browser "
            "flags it): use it to cut away a part of a scan you do not need, then close the "
            "edge with Repair or keep it open on purpose."
        ),
        "steps": [
            "Click the mesh body.",
            "Click the faces to delete: each click takes the faces within the Brush Size.",
            "Click OK.",
        ],
        "tips": [
            "Erase and Fill removes faces and closes the hole in one go.",
        ],
        "picture": "mesh_delete_faces.png",
    },
    "Fission180_MeshMakeClosed": {
        "summary": "Rebuild a broken mesh as a closed (watertight) body.",
        "what": (
            "Wraps a new closed surface around a mesh with holes or gaps, so it can be printed "
            "or converted to a solid. It is Repair with Rebuild (Accurate) chosen; fine "
            "detail can get softer."
        ),
        "steps": [
            "Click the mesh body.",
            "Set Density (higher keeps more detail but is slower).",
            "Tick Preview and read the After line.",
            "Click OK.",
        ],
        "tips": [
            "Try Repair's gentler types first: they keep the original faces.",
        ],
        "picture": "mesh_make_closed.png",
    },
    "Fission180_ConvertMesh": {
        "summary": "Turn a mesh body into a solid body you can model on.",
        "what": (
            "Makes a solid from a closed mesh body so Fillet, Hole, Extrude and the other "
            "SOLID tools work on it. Faceted makes one flat face per triangle; Prismatic merges "
            "flat areas into single faces (a box gets 6 faces). Parametric follows the mesh "
            "when it changes."
        ),
        "steps": [
            "Click the mesh body (or right-click it in the browser > Convert Mesh).",
            "Pick a Method: Prismatic for parts with flat sides, Faceted otherwise.",
            "Pick Operation: Parametric or Base Feature.",
            "Click OK: the new body is named after the mesh, with (solid).",
        ],
        "tips": [
            "The mesh must be closed: Repair it first when the dialog says so.",
            "Over 10,000 triangles takes a while: Reduce the mesh first.",
        ],
        "picture": "mesh_convert.png",
    },
}
