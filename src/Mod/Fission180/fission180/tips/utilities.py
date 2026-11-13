# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tooltips of the UTILITIES tab (wave 8, builder tips-sketch-drawing).

One entry per command id of the UTILITIES tab. The format is the one of
docs/fission180/dev/briefs/tips.md: summary, what, steps, tips, picture (a PNG in
fission180/icons/tips/, made by tools/fission180/tip_pictures_utilities.py: most of these
are the command's own dialog, as Fission 180 shows it).

The texts describe what Fission 180 does (export_ui.py, ai_*.py, rebuild_ui.py, versions_ui.py
and the rest, read and tried), in plain words for a beginner. Pure data: no FreeCAD, no Qt."""

TIPS = {
    # ------------------------------------------------------------------ MAKE
    "Fission180_3DPrint": {
        "summary": "Send the bodies straight to your slicer, or save a 3MF or STL file.",
        "what": "Turns the bodies into a mesh and opens it in your slicer (PrusaSlicer, Bambu "
        "Studio, OrcaSlicer, Cura...) ready to slice, or saves the file. Use it when the part "
        "is ready to print.",
        "steps": [
            "Pick the bodies under Selection.",
            "Pick the slicer under Send to (or save the file only).",
            "Check the Format and the Refinement (finer means smoother and bigger).",
            "Click OK.",
        ],
        "tips": [
            "Preferences > 3D Print sets the slicer to use every time.",
        ],
        "picture": "util_3d_print.png",
    },
    "Fission180_Export": {
        "summary": "Save the design, some bodies or a component as STEP, IGES, STL, 3MF or OBJ.",
        "what": "Writes a file other programs can open: STEP keeps exact solids and components "
        "for other CAD programs, STL, 3MF and OBJ are meshes for printing and rendering, and "
        "a sketch can be saved as DXF.",
        "steps": [
            "Pick what to export: the whole design, selected bodies or a component.",
            "Pick the Type (the file format) and the Unit Type.",
            "Check the Name and the Location.",
            "Click Export.",
        ],
        "tips": [
            "Select a sketch first to export it as DXF for a laser cutter.",
            "Export Everything writes all formats at once.",
        ],
        "picture": "util_export.png",
    },
    "Fission180_ExportEverything": {
        "summary": "Save the whole design as STEP, STL, 3MF, OBJ and a picture, in one go.",
        "what": "Writes every common format of the design into a folder beside the design file, "
        "with a picture and a short read-me, then opens the folder. Use it to share or back "
        "up a design for any program.",
        "steps": [
            "Save the design first (otherwise you are asked for a folder).",
            "Click Export Everything: the files are written and the folder opens.",
        ],
        "tips": [
            "A message says what each format leaves out (colours, components...).",
        ],
        "picture": "util_export_everything.png",
    },
    # ------------------------------------------------------------------ ADD-INS
    "Fission180_ScriptsAddIns": {
        "summary": "Run, create and edit scripts and add-ins; pick which run at start-up.",
        "what": "Lists the Python scripts and add-ins Fission 180 knows. Scripts automate "
        "repeated work; add-ins add commands of their own. Tick Run on Startup for those to "
        "start with Fission 180.",
        "steps": [
            "Pick a script or add-in in the list (Search narrows it).",
            "Click Run, or Edit to change it.",
            "Click Create for a new one, or + to add one from another folder.",
        ],
        "tips": [
            "Get Add-Ons opens FreeCAD's Add-on Manager.",
        ],
        "picture": "util_scripts.png",
    },
    "Std_AddonMgr": {
        "summary": "FreeCAD's Add-on Manager: install workbenches and macros made by others.",
        "what": "Browses the community's FreeCAD add-ons (workbenches and macros) and installs, "
        "updates or removes them. Use it for tools Fission 180 does not have, such as "
        "fasteners or gears libraries.",
        "steps": [
            "Search or browse the list of add-ons.",
            "Pick one and click Install.",
            "Restart Fission 180 when asked.",
        ],
        "tips": [
            "Installed workbenches open through FreeCAD Tools.",
        ],
        "picture": "util_addon_manager.png",
    },
    # ------------------------------------------------------------------ AI
    "Fission180_AIPanel": {
        "summary": "Open the AI panel: chat, your AI apps, AI control on or off.",
        "what": "Shows the AI panel at the side: a chat with an AI that builds in this design, "
        "the AI apps you added, the AI control switch and what the AIs did. Nothing reaches "
        "an AI until you set one up.",
        "steps": [
            "Click AI to open the panel (again to close it).",
            "Switch AI control on to let AI apps work in Fission 180.",
            "Use the Chat tab, or + Add an AI under Your AIs.",
        ],
        "tips": [
            "The Activity tab lists every AI step; Undo last AI step takes one back.",
        ],
        "picture": "util_ai_panel.png",
    },
    "Fission180_AddAI": {
        "summary": "Let Claude Desktop, Gemini CLI or another AI app build in Fission 180.",
        "what": "Sets up an AI app on this computer so it can see and build your design through "
        "Fission 180. Setting one up switches AI control on; Remove takes Fission 180 out of "
        "the app again.",
        "steps": [
            "Pick the AI app: Claude Desktop, Gemini CLI or another app.",
            "Click Set up (or copy the command line for another app).",
            "Restart the AI app, then ask it for a part.",
        ],
        "tips": [
            "The app's settings file is backed up before it is changed.",
        ],
        "picture": "util_add_ai.png",
    },
    "Fission180_AIChat": {
        "summary": "Chat with an AI that builds in Fission 180, with your own key.",
        "what": "Opens the AI panel on its Chat tab. Pick an AI (Claude, ChatGPT, Gemini or a "
        "local model), give it your key once, and ask for parts or changes in plain words.",
        "steps": [
            "Pick the AI and paste your key (or a local model's address); Save key.",
            "Type what you want, such as a 40 x 30 x 10 block with a 6 mm hole.",
            "Click Send and watch the steps appear in the timeline.",
        ],
        "tips": [
            "Every AI step can be undone with Ctrl+Z.",
        ],
        "picture": "util_ai_chat.png",
    },
    "Fission180_AIActivity": {
        "summary": "See what AI apps did in Fission 180, and undo the last AI step.",
        "what": "Opens the AI panel on its Activity tab: every call an AI made, newest first, "
        "with its answer; errors are red. Use it to check what an AI changed.",
        "steps": [
            "Click AI Activity.",
            "Read the list; click Undo last AI step to take the newest one back.",
        ],
        "tips": [
            "Switch AI control off at the top to stop AI apps at once.",
        ],
        "picture": "util_ai_activity.png",
    },
    "Fission180_RebuildWithTimeline": {
        "summary": "Have an AI rebuild an imported or mesh body as real timeline steps.",
        "what": "Keeps the selected body (an imported STEP body, a mesh...) as a reference and "
        "asks an AI to rebuild it as sketches and features you can edit. Fission 180 writes "
        "the message for the AI.",
        "steps": [
            "Select the body to rebuild.",
            "Click Rebuild with Timeline (AI)...",
            "Read the message for the AI and press Send in the chat (or paste it in an AI app).",
            "Use Compare with Reference to check, then Finish Rebuild.",
        ],
        "tips": [
            "Also on the body's right-click menu.",
        ],
        "picture": "util_rebuild.png",
    },
    "Fission180_CompareReference": {
        "summary": "See how far the rebuild is from the original: missing red, extra green.",
        "what": "Compares the rebuilt body with the original: how much they match, the volumes, "
        "the faces matched and the largest gap. The 3D view shows missing material red and "
        "extra material green.",
        "steps": [
            "Click Compare with Reference while a rebuild is going on.",
            "Read the window; look at the red and green in the 3D view.",
            "Click Compare Again after changes, or Close.",
        ],
        "tips": [],
        "picture": "util_compare.png",
    },
    "Fission180_FinishRebuild": {
        "summary": "End the rebuild: it takes the original's name and place.",
        "what": "The rebuilt body replaces the original: its name, component, place and what "
        "used it (joints, sketches, drawings). The original is deleted or kept hidden.",
        "steps": [
            "Click Finish Rebuild.",
            "Choose Delete the original body or Keep the original, hidden.",
            "Click Finish.",
        ],
        "tips": [
            "A rebuild that does not match yet keeps the original by default.",
        ],
        "picture": "util_finish_rebuild.png",
    },
    "Fission180_StopRebuild": {
        "summary": "Give the rebuild up: the original is shown again as it was.",
        "what": "Stops a rebuild. The original body comes back as it was; the rebuilt body and "
        "its steps are deleted, or kept as a body of its own.",
        "steps": [
            "Click Stop Rebuild...",
            "Choose to delete the rebuilt body or keep it.",
            "Click Stop Rebuild.",
        ],
        "tips": [],
        "picture": "util_stop_rebuild.png",
    },
    # ------------------------------------------------------------------ FREECAD
    "Fission180_FreeCADTools": {
        "summary": "Switch to one of FreeCAD's own workbenches; your designs stay open.",
        "what": "Fission 180 is built on FreeCAD. This opens FreeCAD's own interface with one of "
        "its workbenches (Part Design, TechDraw, FEM...), for a tool Fission 180 does not have "
        "yet.",
        "steps": [
            "Click FreeCAD Tools and pick a workbench.",
            "Use its menus and toolbars.",
            "Click Back to Fission 180 to return to the ribbon.",
        ],
        "tips": [],
        "picture": "util_freecad_tools.png",
    },
    # ------------------------------------------------------------------ UTILITY
    "Fission180_Preferences": {
        "summary": "Change how Fission 180 works: navigation, units, history, graphics, AI.",
        "what": "Opens Fission 180's preferences: the mouse navigation, the units of new "
        "designs, design history, materials, graphics, keyboard shortcuts, AI and 3D Print. "
        "Changes are kept between sessions.",
        "steps": [
            "Pick a page on the left (General, Graphics, Default Units...).",
            "Change the settings.",
            "Click OK.",
        ],
        "tips": [
            "Keyboard Shortcuts lists every command's key in one place.",
        ],
        "picture": "util_preferences.png",
    },
    "Fission180_FilesSettings": {
        "summary": "Set the project folder, how often recovery copies are written, and versions.",
        "what": "Chooses where new designs are saved, how often Fission 180 writes a recovery "
        "copy of your open designs, whether every save asks for a version description, and "
        "whether versions are kept with git.",
        "steps": [
            "Choose the Project folder.",
            "Set Recovery copy every (minutes).",
            "Tick the version options you want; OK.",
        ],
        "tips": [],
        "picture": "util_files_settings.png",
    },
    "Fission180_VersionHistory": {
        "summary": "See the saved versions of this design; open, compare or promote one.",
        "what": "Every save makes a new version. This lists them with their descriptions; open "
        "an old one read-only, compare it with the newest, mark it as a milestone, or make it "
        "the newest again.",
        "steps": [
            "Click Version History in a saved design.",
            "Pick a version in the list.",
            "Click Open, Compare, Promote or the milestone button.",
        ],
        "tips": [
            "Milestones only hides the everyday saves.",
        ],
        "picture": "util_version_history.png",
    },
    "Fission180_RecoverDocuments": {
        "summary": "Open the recovery copies kept when Fission 180 did not close properly.",
        "what": "Fission 180 writes recovery copies of open designs every few minutes. After a "
        "crash this lists them so you can get your unsaved work back.",
        "steps": [
            "Click Recover Documents.",
            "Tick the designs to open.",
            "Click Recover (or Delete to throw the copies away).",
        ],
        "tips": [
            "Later keeps the copies for next time.",
        ],
        "picture": "util_recover.png",
    },
    "Fission180_SaveAs": {
        "summary": "Save the design as a new design in another place or under another name.",
        "what": "Makes a separate copy of the design, starting at version 1, in the folder and "
        "under the name you choose. The original stays as it was.",
        "steps": [
            "Click Save As.",
            "Click the project or folder to save in, and type the name.",
            "Click Save.",
        ],
        "tips": [
            "Ctrl+S saves the next version of the same design instead.",
        ],
        "picture": "util_save_as.png",
    },
    "Fission180_Diagnostics": {
        "summary": "Show the program's versions and any command Fission 180 could not find.",
        "what": "Lists the versions of Fission 180, FreeCAD and their libraries, and anything "
        "missing. Copy it into a problem report so the cause is found faster.",
        "steps": [
            "Click Fission 180 Diagnostics.",
            "Click Copy, then paste the text where you report the problem.",
        ],
        "tips": [
            "Report a Problem adds this for you.",
        ],
        "picture": "util_diagnostics.png",
    },
    "Fission180_ReportProblem": {
        "summary": "Tell us what went wrong; you see the whole report before anything is sent.",
        "what": "Writes a problem report with what happened, what you expected and the "
        "program's details. You read it all first; nothing is sent until you choose.",
        "steps": [
            "Type what happened (and what you expected).",
            "Tick Include the last crash log if there was a crash.",
            "Click Open on GitHub, Save report... or Copy.",
        ],
        "tips": [],
        "picture": "util_report_problem.png",
    },
    "Fission180_CommandSearch": {
        "summary": "Find and run any command by typing a few letters of its name.",
        "what": "Opens a search box that finds commands by their menu names and shows their "
        "keys. Use it when you do not know where a command lives in the ribbon.",
        "steps": [
            "Press S (or click Command Search).",
            "Type a few letters of the command's name.",
            "Press Enter, or click the command, to run it.",
        ],
        "tips": [],
        "picture": "util_command_search.png",
    },
}
