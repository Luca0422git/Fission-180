# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the SIMULATION workspace: its SETUP and RESULTS tabs (wave 8, builder
tips-workspaces).

One entry per ribbon command id: "summary" (the small tooltip), "what", "steps", "tips" and
"picture" (a file in fission180/icons/tips/, made by
tools/fission180/tip_pictures_simulation.py). The texts describe what Fission 180's own dialogs
do (simulation_ui.py, simulation_dialogs.py, simulation_panels.py, simulation_solve_dialog.py,
simulation_results_ui.py, simulation_results_panels.py). Manage Physical Materials and Measure
are on the SOLID tab too, so their entries live in tips/solid.py.
"""

TIPS = {
    # ------------------------------------------------------------------ SETUP
    "Fission180_SimNewStudy": {
        "summary": "Start a new simulation study of the design (Static Stress).",
        "what": (
            "A study holds one simulation: its materials, what holds the part, the loads, the "
            "mesh and the results. Fission 180 solves Static Stress: how much a part bends "
            "and where it is stressed under steady loads. The other study types are shown "
            "greyed."
        ),
        "steps": [
            "Click New Simulation Study.",
            "Click the Static Stress tile.",
            "Optionally click the gear to change the Study Settings.",
            "Click Create Study: it shows in the browser as Study 1 - Static Stress.",
        ],
        "tips": [
            "The first visit to SIMULATION opens this dialog by itself.",
            "Right-click a study in the browser > Clone Study to try a change side by side.",
        ],
        "picture": "sim_new_study.png",
    },
    "Fission180_SimStudyMaterials": {
        "summary": "Choose each body's material for this study, without changing the design.",
        "what": (
            "Lists every body with its Model Material and its Study Material, (Same as Model) "
            "at first. Pick another material to try it in this study only, leave a body out "
            "with In Study, and choose whether the safety factor compares the stress with the "
            "Yield Strength or the Ultimate Tensile Strength."
        ),
        "steps": [
            "Click Study Materials.",
            "In a body's row, pick a Study Material.",
            "Click a row to read the values used (stiffness, density, strength).",
            "Set the Safety Factor basis and click OK.",
        ],
        "tips": [
            "A body without a physical material gets one in DESIGN > Physical Material.",
        ],
        "picture": "sim_study_materials.png",
    },
    "Fission180_SimConstraints": {
        "summary": "Hold the part where it is fixed, pinned or resting on something.",
        "what": (
            "A simulation needs to know where the part is held, like the bolted foot of a "
            "bracket. Fixed holds faces, edges or corners still; Pin lets a round hole turn; "
            "Frictionless lets a face slide along itself; Prescribed Displacement moves faces "
            "by a set distance."
        ),
        "steps": [
            "Click Structural Constraints.",
            "Pick the Type: Fixed, Pin, Frictionless or Prescribed Displacement.",
            "Click the faces to hold (only what the type takes lights up).",
            "For Fixed, untick Ux, Uy or Uz to let it move that way; click OK.",
        ],
        "tips": [
            "Cones show a Fixed constraint on the model.",
            "Not held enough? DISPLAY > DOF View shows how the part can still move.",
        ],
        "picture": "sim_constraints.png",
    },
    "Fission180_SimLoads": {
        "summary": "Push, pull or twist the part: a force, a pressure, a moment or a bearing load.",
        "what": (
            "Adds what acts on the part. Force pushes faces, edges or points; Pressure presses "
            "evenly on faces; Moment twists; Bearing Load presses across a hole like a shaft; "
            "Remote Force acts from a point off the part. Values take units: 100 N, 2 MPa, "
            "10 lbf."
        ),
        "steps": [
            "Click Structural Loads and pick the Type, for example Force.",
            "Click the faces the load acts on.",
            "Type the Magnitude.",
            "Set the direction (Normal to the faces, an Angle or a Vector); Flip Direction "
            "turns it round.",
            "Click OK: arrows show the load on the model.",
        ],
        "tips": [
            "Force Per Entity puts the full force on each picked face instead of sharing it.",
        ],
        "picture": "sim_loads.png",
    },
    "Fission180_SimGravity": {
        "summary": "Switch the weight of the bodies on or off for this study.",
        "what": (
            "Adds the bodies' own weight as a load (off in a new study). Use it for heavy "
            "parts or where the weight matters next to the other loads. A tick in the menu "
            "shows when it is on."
        ),
        "steps": [
            "Click Toggle Gravity On/Off.",
            "To change its direction or size, right-click Gravity in the browser > Edit "
            "Gravity.",
        ],
        "tips": [
            "Gravity needs a material with a density on every body.",
        ],
        "picture": "sim_gravity.png",
    },
    "Fission180_SimAutoContacts": {
        "summary": "Find the bodies that touch: they are glued (bonded) together when it solves.",
        "what": (
            "When a study has several bodies, the solver must know which ones touch. Automatic "
            "Contacts finds faces within the tolerance of each other and bonds them, as if "
            "glued. The study does this by itself at solve time; this dialog shows them first."
        ),
        "steps": [
            "Click Automatic Contacts.",
            "Check the tolerance (how close faces must be).",
            "Click Generate and read the list of bonded pairs with their gap.",
            "Click OK.",
        ],
        "tips": [
            "Contact Manager lists the pairs again later.",
        ],
        "picture": "sim_auto_contacts.png",
    },
    "Fission180_SimContactManager": {
        "summary": "See the list of bodies bonded together in this study.",
        "what": (
            "Shows every contact of the study: the two bodies and how they are joined (bonded). "
            "It is a read-only list; Automatic Contacts makes the pairs."
        ),
        "steps": [
            "Click Contact Manager.",
            "Read the pairs, then click Close.",
        ],
        "tips": [
            "Bodies that should not touch? Check their gap with Automatic Contacts' tolerance.",
        ],
        "picture": "sim_contact_manager.png",
    },
    "Fission180_SimDOFView": {
        "summary": "Show arrows for the ways a part that is not held enough could still move.",
        "what": (
            "A part must be held so it cannot float away, or the solve fails. DOF View draws "
            "arrows on each body that can still slide or turn, and names them with how they "
            "can move. The arrows follow the setup until you switch it off."
        ),
        "steps": [
            "Click DOF View (on).",
            "Read the arrows: each is a way the part can still move.",
            "Add a Structural Constraint that stops it, then click DOF View again (off).",
        ],
        "tips": [
            "No arrows means every body is held.",
        ],
        "picture": "sim_dof_view.png",
    },
    "Fission180_SimShowMesh": {
        "summary": "Show or hide the mesh made by Generate Mesh on the model.",
        "what": (
            "Switches the drawing of the study's mesh (the small elements the solver uses) on "
            "the model on and off. The mesh must have been made by Generate Mesh or a solve."
        ),
        "steps": [
            "Click Generate Mesh first if there is no mesh yet.",
            "Click Show Mesh to switch the mesh lines on or off.",
        ],
        "tips": [],
        "picture": "sim_show_mesh.png",
    },
    "Fission180_SimSettings": {
        "summary": "Change the study's settings: mesh size, adaptive refinement, contacts.",
        "what": (
            "Opens Study Settings: General (rigid body modes, keeping the results in the "
            "file), Mesh (Average Element Size and quality), Adaptive Mesh Refinement (solve "
            "again with a finer mesh where it matters) and Contacts (the tolerance)."
        ),
        "steps": [
            "Click Settings.",
            "Pick a tab: General, Mesh, Adaptive Mesh Refinement or Contacts.",
            "Change the values (a smaller element size is more exact but slower).",
            "Click OK.",
        ],
        "tips": [
            "Adaptive Mesh Refinement unlocks the Convergence Plot in RESULTS.",
        ],
        "picture": "sim_settings.png",
    },
    "Fission180_SimLocalMesh": {
        "summary": "Use smaller mesh elements on the faces or edges where the stress matters.",
        "what": (
            "A finer mesh gives more exact results but takes longer to solve. Local Mesh Control "
            "makes it finer only where you pick, such as a round corner or a hole, and keeps "
            "the rest of the part coarse. Green dots mark it on the model."
        ),
        "steps": [
            "Click Local Mesh Control.",
            "Click the faces or edges (or tick Body Selection for whole bodies).",
            "Move the slider toward Fine, or type a Length.",
            "Click OK.",
        ],
        "tips": [
            "Generate Mesh shows the result before you solve.",
        ],
        "picture": "sim_local_mesh.png",
    },
    "Fission180_SimAttributes": {
        "summary": "List every constraint and load of the study, with where it is and how big.",
        "what": (
            "Shows a table of the study's constraints and loads: their type, the faces they are "
            "on, their size and direction and their status (OK, lost its faces, suppressed). "
            "Use it to check the setup at a glance before solving."
        ),
        "steps": [
            "Click Load Case Attributes.",
            "Read the table; a lost item must be edited in the browser and picked again.",
            "Click Close.",
        ],
        "tips": [],
        "picture": "sim_attributes.png",
    },
    "Fission180_SimPrecheck": {
        "summary": "Check the study before solving: what is missing or may be wrong.",
        "what": (
            "Looks at the study and lists what stops a solve or may give wrong results: no "
            "constraint, a body without material, a load that lost its faces. The button's "
            "light turns green (ready), yellow (warnings) or red (cannot solve)."
        ),
        "steps": [
            "Click Pre-check.",
            "Read the messages.",
            "Click Repair to go to the first thing to fix, or Solve when it is ready.",
        ],
        "tips": [
            "Hover the Pre-check button to see its last result.",
        ],
        "picture": "sim_precheck.png",
    },
    "Fission180_SimSolve": {
        "summary": "Solve the study on this computer and show the results.",
        "what": (
            "Meshes the part and runs the solver (CalculiX) on this computer. The window "
            "shows each stage and the time taken; Cancel stops it. When it ends the RESULTS "
            "tab opens with the safety factor. A big part with a fine mesh can take minutes."
        ),
        "steps": [
            "Click Solve.",
            "Tick the studies to solve (a red one says what to fix, with Repair).",
            "Click Solve N Studies and wait for the stages to finish.",
            "The results open by themselves.",
        ],
        "tips": [
            "You can keep working in DESIGN while it solves.",
            "Results go out of date when the design changes: solve again.",
        ],
        "picture": "sim_solve.png",
    },
    "Fission180_SimGenerateMesh": {
        "summary": "Make the mesh now and show it on the model, before solving.",
        "what": (
            "Splits the part into the small elements the solver uses and draws them, so you "
            "can check the mesh is fine enough at holes and corners. The node and element "
            "counts show in the browser. A solve makes the mesh by itself otherwise."
        ),
        "steps": [
            "Click Generate Mesh.",
            "Look at the mesh on the model; DISPLAY > Show Mesh hides it.",
            "Too coarse? Use Settings or Local Mesh Control and generate again.",
        ],
        "tips": [],
        "picture": "sim_generate_mesh.png",
    },
    "Fission180_SimJobStatus": {
        "summary": "See the solve running now, and this session's earlier solves and meshes.",
        "what": (
            "Shows the progress of a running solve with its stages and a Cancel button, and "
            "lists the solves and meshes made in this session with how they ended."
        ),
        "steps": [
            "Click Job Status.",
            "Double-click a solved study to see its results.",
            "Click Close.",
        ],
        "tips": [],
        "picture": "sim_job_status.png",
    },
    # ------------------------------------------------------------------ RESULTS
    "Fission180_SimResultsAnimate": {
        "summary": "Play the part bending from its unloaded shape to its loaded one.",
        "what": (
            "Shows a bar at the bottom of the view that plays the bend over and over, to see "
            "how the part moves under the load. Set the speed, the number of steps and the "
            "loop; Save writes an animated GIF or WebP."
        ),
        "steps": [
            "Click Animate: the bar appears and the part moves.",
            "Change the speed or Play Once / Loop / Mirror Loop.",
            "Click Save... to keep it as a picture file, or Close.",
        ],
        "tips": [
            "Click Animate again to stop.",
        ],
        "picture": "simr_animate.png",
    },
    "Fission180_SimResultsDetails": {
        "summary": "What the results mean: the lowest safety factor against your target.",
        "what": (
            "Explains the result in a sentence: whether the lowest safety factor is below, "
            "within or above your Lower and Upper targets (3 and 6 at first), with advice. "
            "It also lists per body the material, the highest stress and the largest "
            "movement."
        ),
        "steps": [
            "Click Results Details (or the i button in the legend).",
            "Read the sentence and the table.",
            "Change the targets or tick Show the target bands on the model.",
            "Click Close.",
        ],
        "tips": [
            "A safety factor below 1 means the part would yield.",
        ],
        "picture": "simr_details.png",
    },
    "Fission180_SimResultsConvergence": {
        "summary": "See how the result settled as adaptive refinement made the mesh finer.",
        "what": (
            "For a study solved with Adaptive Mesh Refinement, a chart and a table show the "
            "watched result at each solve and how much it changed. If it settled within the "
            "tolerance, the mesh was fine enough. Greyed for other studies."
        ),
        "steps": [
            "Switch on Adaptive Mesh Refinement in Settings and solve.",
            "Click Convergence Plot.",
            "Read the sentence: converged, or allow more refinements; click Close.",
        ],
        "tips": [],
        "picture": "simr_convergence.png",
    },
    "Fission180_SimResultsRange": {
        "summary": "Set the values the legend's colours run between.",
        "what": (
            "Narrows the colour scale to the values you care about, so small differences show. "
            "Values beyond the range take the end colours (or grey, from the legend's ... "
            "menu). Not for the safety factor."
        ),
        "steps": [
            "Pick a result other than Safety Factor in the legend.",
            "Click Legend Min/Max.",
            "Type Min and Max (in the legend's unit); Reset goes back; click OK.",
        ],
        "tips": [
            "You can also drag the two ends of the colour bar.",
        ],
        "picture": "simr_range.png",
    },
    "Fission180_SimResultsCompare": {
        "summary": "Show two to four studies side by side on one colour scale.",
        "what": (
            "Splits the view into panes, one study in each, turning together, so you can "
            "compare designs, materials or loads. One colour scale for all: the same colour is "
            "the same value."
        ),
        "steps": [
            "Click Compare.",
            "Tick two to four studies that have results.",
            "Click Compare; turn or zoom any pane, the others follow.",
            "Click Finish Compare (or Compare again) to end.",
        ],
        "tips": [],
        "picture": "simr_compare.png",
    },
    "Fission180_SimResultsReport": {
        "summary": "Write the study's setup, results and pictures to an HTML report.",
        "what": (
            "Makes a web page report: the cover, materials, constraints, loads, mesh, the "
            "results with pictures and the reaction forces. One report can cover several "
            "studies. Preview opens it in the web browser without saving."
        ),
        "steps": [
            "Click Report.",
            "Fill in the title, author and the other General fields.",
            "Tick the studies to include and pick the file.",
            "Click Preview to look, then Save or Save and Open.",
        ],
        "tips": [],
        "picture": "simr_report.png",
    },
    "Fission180_SimResultsUndeformed": {
        "summary": "Show the results on the part's unloaded shape.",
        "what": (
            "Draws the colours on the part as it is without the loads, so its shape is not "
            "bent. One of the DEFORMATION choices; the ticked one is shown."
        ),
        "steps": [
            "Open DEFORMATION and click Undeformed.",
            "Pick Adjusted again to see the bend.",
        ],
        "tips": [],
        "picture": "simr_undeformed.png",
    },
    "Fission180_SimResultsActual": {
        "summary": "Show the bend of the part at its true size.",
        "what": (
            "Draws the part bent by exactly as much as the solve found. Real bends are often "
            "too small to see; Adjusted makes them visible."
        ),
        "steps": [
            "Open DEFORMATION and click Actual.",
            "Read the true movement in the legend (Displacement).",
        ],
        "tips": [],
        "picture": "simr_actual.png",
    },
    "Fission180_SimResultsAdjustedHalf": {
        "summary": "Exaggerate the bend half as much as Adjusted.",
        "what": (
            "Draws the bend enlarged, at half of the Adjusted scale, when Adjusted looks too "
            "strong. The colours and values do not change, only the drawn shape."
        ),
        "steps": [
            "Open DEFORMATION and click Adjusted x 0.5.",
            "Compare with Adjusted to see where it bends.",
        ],
        "tips": [],
        "picture": "simr_adjusted_half.png",
    },
    "Fission180_SimResultsAdjusted": {
        "summary": "Exaggerate the bend so it is easy to see (the default).",
        "what": (
            "Draws the bend enlarged so the largest movement is 5 % of the model's size, "
            "whatever the true size. It shows how the part bends; the values in the legend "
            "stay the true ones."
        ),
        "steps": [
            "Open DEFORMATION and click Adjusted.",
            "Read the scale used at the bottom of Results Details.",
        ],
        "tips": [],
        "picture": "simr_adjusted.png",
    },
    "Fission180_SimResultsAdjusted2": {
        "summary": "Exaggerate the bend twice as much as Adjusted.",
        "what": (
            "Draws the bend at twice the Adjusted scale, to make a small movement plain. The "
            "colours and values do not change, only the drawn shape."
        ),
        "steps": [
            "Open DEFORMATION and click Adjusted x 2.",
            "Pick Adjusted again for the usual view.",
        ],
        "tips": [],
        "picture": "simr_adjusted_2.png",
    },
    "Fission180_SimResultsAdjusted5": {
        "summary": "Exaggerate the bend five times as much as Adjusted.",
        "what": (
            "Draws the bend at five times the Adjusted scale, for a part that hardly moves. "
            "The colours and values do not change, only the drawn shape."
        ),
        "steps": [
            "Open DEFORMATION and click Adjusted x 5.",
            "Pick Adjusted again for the usual view.",
        ],
        "tips": [],
        "picture": "simr_adjusted_5.png",
    },
    "Fission180_SimResultsMesh": {
        "summary": "Show the mesh's element edges on the result.",
        "what": (
            "Draws the edges of the mesh elements over the coloured result, to check that "
            "the mesh is fine enough where the stress changes fast."
        ),
        "steps": [
            "Click Show Mesh (on).",
            "Click it again to hide the lines.",
        ],
        "tips": [
            "Too coarse at a hot spot? SETUP > Local Mesh Control, then solve again.",
        ],
        "picture": "simr_show_mesh.png",
    },
    "Fission180_SimResultsGhost": {
        "summary": "Show the part's unloaded shape, see-through, around the bent result.",
        "what": (
            "Draws the part as it is without loads as a see-through ghost, so you can see how "
            "far and which way the loaded part moved."
        ),
        "steps": [
            "Click Undeformed Model (on).",
            "Click it again to hide the ghost.",
        ],
        "tips": [],
        "picture": "simr_ghost.png",
    },
    "Fission180_SimResultsLoads": {
        "summary": "Show the loads and constraints on the result.",
        "what": (
            "Draws the setup's arrows, cones and pins over the result, to read the colours "
            "against where the part is held and pushed. Off at first."
        ),
        "steps": [
            "Click Loads and Constraints (on).",
            "Click it again to hide them.",
        ],
        "tips": [],
        "picture": "simr_loads.png",
    },
    "Fission180_SimResultsProbes": {
        "summary": "Click on the result to read its value there.",
        "what": (
            "Shows the value under the mouse as it moves over the part; a click leaves a tag "
            "with that value. Place as many as you like. They read the result chosen in the "
            "legend."
        ),
        "steps": [
            "Click Surface Probes.",
            "Move over the part to read values; click to place a tag.",
            "Remove deletes the chosen tag, Clear All every tag; Close keeps them.",
        ],
        "tips": [
            "For values inside the part, use Point Probes.",
        ],
        "picture": "simr_probes.png",
    },
    "Fission180_SimResultsMinMax": {
        "summary": "Show tags at the places of the lowest and the highest value.",
        "what": (
            "Marks where the result shown is lowest and highest, with their values. On by "
            "default; switch it off for a clean picture."
        ),
        "steps": [
            "Click Show Min/Max to switch the tags on or off.",
            "Pick another result in the legend: the tags follow it.",
        ],
        "tips": [],
        "picture": "simr_minmax.png",
    },
    "Fission180_SimResultsReactions": {
        "summary": "See the force each constraint takes to hold the part.",
        "what": (
            "Lists for each constraint the force it holds the part with (X, Y, Z and total) "
            "and tags it on the model. The total should balance the loads; use it to size "
            "bolts or supports."
        ),
        "steps": [
            "Click Reaction Force.",
            "Read the table and the tags on the model.",
            "Click Close.",
        ],
        "tips": [],
        "picture": "simr_reactions.png",
    },
    "Fission180_SimResultsSlice": {
        "summary": "Cut the result with a plane to see the values inside the part.",
        "what": (
            "Slices the result along a plane across X, Y or Z, a construction plane, or "
            "parallel to a face you click. Cut the result away shows the values on the cut "
            "face; Slice alone draws only the cut, the rest see-through."
        ),
        "steps": [
            "Click Slice Plane.",
            "Pick the direction, or click a face of the result.",
            "Drag the arrow, the slider or type the position; Flip turns it.",
            "Click OK to keep it, or Remove Slice.",
        ],
        "tips": [
            "Tick Mesh lines on the cut to see the elements inside.",
        ],
        "picture": "simr_slice.png",
    },
    "Fission180_SimResultsPointProbes": {
        "summary": "Read the result at points inside the part.",
        "what": (
            "Places probes that can sit inside the part: click the result, a slice's cut face or "
            "an iso-surface, then move a probe with its three arrows or by typing X, Y, Z. A "
            "table lists every probe with its value."
        ),
        "steps": [
            "Click Point Probes.",
            "Click on the result (or a slice) to place a probe.",
            "Drag its arrows or type X, Y, Z in the table to move it.",
            "Remove or Clear All; Close keeps them.",
        ],
        "tips": [],
        "picture": "simr_point_probes.png",
    },
    "Fission180_SimResultsIso": {
        "summary": "Show the surface inside the part where the result has one value.",
        "what": (
            "Draws, inside the see-through part, the surface where the shown result equals "
            "a value, like a contour line in 3D. Use it to see how far a high stress reaches "
            "into the part."
        ),
        "steps": [
            "Click Iso-surface.",
            "Move the slider or type the value (in the legend's unit).",
            "Click OK to keep it, or Remove Iso-surface.",
        ],
        "tips": [],
        "picture": "simr_iso.png",
    },
    "Fission180_SimResultsSolverData": {
        "summary": "See how the study was solved: time taken, mesh size and quality, messages.",
        "what": (
            "Lists when the study was solved, how long each stage took, the mesh's nodes, "
            "elements and quality, and the solver's messages. Useful when a result looks "
            "wrong or a solve is slow."
        ),
        "steps": [
            "Click Solver Data.",
            "Read the rows; Copy puts them on the clipboard as text.",
            "Click Close.",
        ],
        "tips": [],
        "picture": "simr_solver_data.png",
    },
    "Fission180_SimResultsFinish": {
        "summary": "Leave the results and go back to the study's setup.",
        "what": (
            "Closes the RESULTS tab: the SETUP tab and the model show again. The results are "
            "kept; double-click Results in the browser to see them again."
        ),
        "steps": [
            "Click Finish Results.",
            "Change the setup and Solve again, or switch back to DESIGN.",
        ],
        "tips": [],
        "picture": "simr_finish.png",
    },
}
