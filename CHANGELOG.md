# Fission 180 changelog

What changed in each release, newest first, in plain words. Each release's page on GitHub shows
its own section of this file (the release notes are made from it), so every release gets a
section here whose heading is exactly its version number, like `## 0.1.0-beta` below. Known
problems are in [docs/fission180/known-issues.md](docs/fission180/known-issues.md).

Fission 180 was called **SciForge** until 0.1.0-beta.3.2.1; the sections below that one describe
releases published under the old name (their tags are `sciforge-v...`).

## 0.1.0-beta.4.0.0

**The fourth beta: the Fusion tutorial book, replayed.** Fission 180 0.1.0-beta.3.3.9 was taken
through *Mastering Autodesk Fusion* (2nd edition) chapter by chapter, with a real mouse and
keyboard, and every step that did not go the way the book says was written down: 123 hiccups,
63 workarounds and 44 failures, among them 20 reproducible bugs. Every one of the 20 is fixed,
or explained below where the report had Fusion wrong; much of the rest is smoothed out; and
the two workspaces the book needs that Fission 180 did not have are here: **Animation**
(exploded views and assembly animations, saved as a video) and **Manufacture** (CNC milling
programs). Render is still not part of Fission 180. This version was then checked the same
way: every project of the book except the Render chapter was replayed step by step with real
mouse and keyboard input and a new user's settings, and every hitch found was fixed (the Hot
End was replayed about a third of the way, the Carabiner up to its path, the Football without
its laces).

**What you will notice first** (details under Changed): new sketches, bodies and planes always
go into the active component; Extrude chooses Cut, Join or New Body by one rule and never
changes the one you picked; on the Front plane a positive distance now goes away from you, for
new sketches and shapes; a design's first body is called Body1 and its first component is
grounded; with Snap on, every sketch point you click lands on a grid crossing, and the first
dimension you type scales the whole sketch; sketch axes have the origin's colours; **Select
Through is now on**, so a window selection takes hidden edges too; a new design opens in the
Home view with the Layout Grid on; and Undo pressed while a dialog is open cancels that dialog.

### New workspace: Animation

- **Workspace > Animation makes exploded views and assembly animations** of a design's
  components without changing the design; only the parts are drawn there (no sketches, planes
  or joint symbols). Storyboards are tabs under the ANIMATION TIMELINE: new (empty, or
  starting where the last one ends), rename, duplicate, reverse, delete, reorder.
- **The ANIMATION TIMELINE records at the playhead.** Drag a bar or its ends, double-click it to
  type its times, Delete removes it; play, pause and loop (Space, wherever the pointer is). The
  scratch zone at the start moves things without recording them, as in Fusion.
- **Transform Components** (manipulator or typed values, Set Pivot, trail lines; click a part
  inside a subassembly twice to take it alone), **Auto Explode** (One Level or All Levels,
  Explosion Scale, One-Step or Sequential), **Manual Explode**, **Show/Hide** (at once or as a
  fade), **Restore Home**, **Create Callout**, and **View** (camera moves are recorded).
- **Publish Video** saves one storyboard or all of them as an AVI video (plays in VLC and
  Windows' players), as an MP4 when the free ffmpeg program is installed (the greyed MP4 entry
  says where to get it), or as PNG pictures, at the size and speed you choose.
- **The AI assistant can animate too**: storyboards, explosions, callouts, the video.

### New workspace: Manufacture

- **Workspace > Manufacture turns a design into a CNC milling program**, with Fusion's names and
  dialogs, without leaving Fission 180 (FreeCAD's CAM engine does the computing). Toolpaths are
  kept in the design and say "needs regenerating" when the design changes.
- **Setup**: how the part sits on the machine (origin and axes) and the stock it is cut from (a
  margin round the part, a fixed size, a solid, or From preceding setup for the other side).
- **Milling operations** with Fusion's five-tab dialogs: Face, 2D Adaptive Clearing, 2D Pocket,
  2D Contour (with holding tabs, spread out or where you click), Slot, Trace, Engrave, 2D
  Chamfer, Bore, Circular, Drill, and the 3D Adaptive Clearing, Pocket Clearing, Parallel and
  Contour. The **Tool Library** has sample metric and inch tools and room for your own.
- **Simulate** shows the tool cutting the stock, the machining time and any rapid move into
  material. **Post Process** writes G-code for Grbl, LinuxCNC, Mach3 / Mach4, Fanuc, Marlin and
  four more controllers, checked before you see it; **Setup Sheet** lists tools, steps and times.
- **The AI assistant can do it too**: setups, operations, generate, simulate and post process.

### New: sketches and parameters

- **Sketch constraints work both ways**: select the things and click the constraint, or click
  the constraint and then the things. One that cannot be added says why, next to the pointer,
  and shows what is in the way. Collinear works on two vertical lines, Symmetry on two lines,
  circles or arcs, Tangent on the corner two splines share.
- **Sketch Dimension (D) is Fission 180's own tool.** The click that places a dimension is never
  taken as another pick, and a sketch line is taken before an axis under the pointer. A
  slanted line gives its length beside it; placed straight beside two points, a dimension is
  their vertical distance, above or below them the horizontal one (or right-click > Aligned /
  Horizontal / Vertical). A dimension the sketch already fixes is added as driven, in brackets.
- **New linetype Centerline**: a dimension to it is a diameter, and Revolve takes it as its axis.
- **Clicking an edge or corner of the model while you draw, constrain or dimension projects it
  into the sketch**, also from another body or component, and a click in the middle of a pin's
  round end or of a hole lands on its centre. Project (P) and Include 3D Geometry take other
  components too (Preferences > General > Design > Auto project edges on reference).
- **Sketch patterns stay tied to the original**: the copies follow it and its dimensions,
  Suppression leaves copies out, a typed Quantity counts without Enter. Mirror closes the
  outline on the mirror line; Offset hides its helper lines.
- **Drawing**: press on a line's end and drag for a tangent arc; a chain that ends on something
  already drawn stops, with a note. Polygons, splines and ellipses no longer show FreeCAD's
  helper circles, points and labels.
- **Change Parameters is rebuilt**: "+ User Parameter", a filter, Favorites, rename by typing
  over a name (formulas follow), a unit per parameter (in, ft, deg, none...), every step's sizes
  in the design's units; all of it is one Undo step, and Cancel puts it back.
- **Parameters are typed as in Fusion**: a name on its own in any value box (with a list of
  matching names as you type); "Thickness = -2.5 mm" in Extrude or "Width=5mm" in a slot's box
  makes the parameter and uses it; a number without a unit is in the design's units;
  "min(100; max(45; Arm_Length))" works; a typo gets "Did you mean Arm_Length?". A pattern of
  bodies follows a parameter as its Quantity.

### New: modelling

- **Extrude picks profiles the way Fusion does**: a profile behind a face is clicked through the
  part (faint blue); a hidden body's sketch can be used; a click beside a thin slot counts;
  plane squares, value boxes and the taper handle no longer catch the click; the only profile
  in view is picked by itself. Touching profiles taper as one, and **Bodies to Cut** has a check
  box per body.
- **Box, Cylinder, Torus and Coil have size boxes on the canvas**: type a size, Tab to the next,
  Enter to place, then the height; the boxes keep out of the pointer's way. Loft can end in the
  origin (click its dot) or a construction point.
- **Thread**: ISO pipe (G) and NPT threads; the size of the clicked face (a 6 mm hole is M6, not
  M7); Unified sizes in inch designs. A thread can be dragged before its chamfer (the book's
  Geocache, Metric Bolt and Pizza Cutter), a chamfer or fillet can follow a modeled thread, and
  Offset Face / Press Pull move a whole thread.
- **Fillet and Chamfer build the book's sizes**: the Tensegrity Tower's 20 mm corner chamfer
  (held at 1.79 mm before), the Carabiner's two 4 mm rounds on its 8 mm face (held at 3.99), a
  window-picked part. A size that does not fit is said within a second or two, with how many
  edges are in the way, instead of freezing the window.
- **Heavy patterns no longer freeze Fission 180**: a knurl shows shaded copies while you type
  and builds the real ones once, on OK, in the background, with progress and Cancel. Hole >
  From Sketch with modeled threads cuts them once, on OK.
- **Split Face stays split** under later features, also while the next Extrude is being changed,
  and a pattern of features can include it.
- **Spur Gear**: Scripts and Add-Ins lists SpurGear; each gear becomes a component of its own at
  the top of the design, named like Fusion's ("Spur Gear (20 teeth)"), and takes root fillets
  as large as Fusion's sample does (the book's 0.88 mm on 100 teeth).

### New: assemblies and joints

- **Mirror of components**; patterned, mirrored or pasted subassemblies keep their parts as rows
  in the browser. A mirrored component is called "Name (Mirror)" and can be renamed on its own.
  A click on a part inside a subassembly picks that part for Move/Copy and patterns.
- **Ground to Parent / Unground From Parent.** The first component you make is grounded, as in
  Fusion (Preferences > General > Design); Joint ungrounds the first part you click if needed.
- **The component right-click menu** has Move/Copy, Create Drawing and Properties. Move/Copy
  turns a component about its own origin; a paste starts where the copy came from, and Esc
  right after it takes the paste away again.
- **Joints**: limits with Flip, Preview Motion and With All Limits; a Rest position the part goes
  back to when let go; Link with Same Joint (a cap that turns as it slides); a closed linkage
  moves as one when dragged; Animate Joint plays one joint, the new Animate Joint Relationships
  everything connected; Motion Study draws a graph. A subassembly's joint can sit on any part
  inside it.
- **A step that changes a body outside the active component** says so next to the pointer, and
  dialogs name such bodies with their component: "Body1 (Bracket)" (Interference too).

### New: appearances, materials and hardware

- **200 appearances in 12 categories** (woods, leather, metals, anodized colours, ABS, rubber,
  glass, carbon fibre, LEDs...) with search and favourites; wood grain and other patterns are
  drawn on the part (MODIFY > Texture Map Controls). Double-click a look to edit it; In This
  Design starts with the editable default look; looks can be dropped on a browser row.
- **A look given to a body whose faces have their own** asks Keep, Remove or Cancel, inside the
  Appearance dialog, as Fusion does.
- **Physical materials**: Brass, Bronze, Gold, Silver, Carbon Fibre, anodized aluminium, woods,
  rubber and more, with search; double-click one for a copy with its own name and density. A
  material of your own can be called Brass or Gold (it was refused as taken).
- **Properties** (INSPECT, or right-click a body or component): mass, volume, area, centre of
  mass, moments of inertia, and a component's Part Number and Description for the parts list.
  A selected face shows its area at the bottom right, an edge its length.
- **Component Color Swatch** (the timeline's gear menu) marks each component's colour in the
  browser and the timeline; right-click a component > Cycle Component Color.
- **INSERT > Hardware is a full standard-parts library**, metric and inch: screws of every common
  head, set and shoulder screws, nuts, washers, O-rings, ball bearings, retaining rings, dowel
  pins, keys, standoffs, inserts, magnets, with a Search box ("set screw m3", "6202").
- **A hardware part goes on any part of a hole** (rim, wall, countersink, chamfer), takes its
  size (a threaded hole's thread size) and seats its head; "All holes like it" fills every such
  hole. Parts are named as you would order them, have a mass and follow their hole when it
  moves. **Insert Catalogue Part** opens a supplier's site (McMaster-Carr...) and inserts the
  STEP file you download there.

### New: drawings

- **TABLES > Parts List, Renumber and Align Balloons; EXPORT > Export CSV** and **Export DWG**
  (with a DWG converter program installed; otherwise it says so and writes a DXF). New: Move,
  Rotate and Center Mark Pattern.
- **Exploded views**: CREATE > Exploded View, or New Drawing > From Animation, draws the design
  as the storyboard in front leaves it, with its trail lines. Right-click a component, or the
  design's own row, > Create Drawing.

### New: the window, the Data Panel and export

- **The Data Panel works like Fusion's**: New Project; New Folder and Rename type the name on the
  card; folders can be moved, copied and deleted (to the computer's trash); a right-click
  anywhere has a menu. Save puts a new design in the folder open there and shows your projects.
- **A "+" beside the design tabs** makes a new design; a profile button at the top right opens
  Preferences, and so does Edit > Preferences.
- **Export USDZ** (a design in AR on a phone, with its colours); **Save As Mesh** is Fusion's
  dialog, with Send to 3D Print Utility; Export, Save As DXF and Insert start in the design's
  folder.

### Changed

- **New things go into the active component**, whatever you click: a sketch on another
  component's face, a New Body, planes, axes, points, primitives. A command aimed at another
  component's part (Shell, Hole, Thread, Fillet, a Cut) no longer makes it the active one. With
  the design's top row active, a sketch on a component's face is made at the top, as in Fusion:
  activate the component first to add to its body.
- **Extrude's operation follows one rule and keeps your choice**: Cut when the new shape starts
  in, or goes mostly into, a visible body of any component; Join when it builds on a body of the
  active component; New Body otherwise. Symmetric no longer turns a Cut into a Join, and an
  operation you picked is never changed.
- **On the Front plane a positive distance goes away from you**, as in Fusion: Extrude of a new
  sketch, Box, Cylinder, Coil and Offset Plane. What you made before keeps its side.
- **A design's first body is called Body1**, and **the first component you make is grounded**:
  to drag it, right-click > Unground From Parent (a joint ungrounds it by itself).
- **Select Through is on by default**, as in Fusion: a window drawn round a part takes its hidden
  edges too (switch it off under SELECT > Selection Filters).
- **Sketch selection**: a click selects only what you click; Ctrl+click adds or removes (it
  selected nothing before), Shift+click adds.
- **Sketch Snap works like Fusion's**: with Snap ticked, every point you click freely lands on a
  grid crossing, in every drawing tool (ends, middles, centres and guides come first); untick it
  for no pull. It used to pull from far away towards 50 mm lines. A line near 45 degrees gets no
  angle dimension.
- **The first dimension you type scales the whole sketch** (also when typed as a sum or a
  parameter), so a shape drawn by eye keeps its proportions (Preferences > General > Design >
  Scale entire sketch at first dimension).
- **Sketch axes have the origin's colours**: on the Front plane the upright axis is blue (Z), as
  in Fusion; it was green.
- **A sketch that is not fully dimensioned yet settles the same way every time.** When a
  constraint is added, the curves that are still free move as little as they can; before, the
  same steps could leave a short line a hair long or twice as long, depending on the run.
- **A new design opens like Fusion's**: Home view, Layout Grid on, with a red X line, a green Y
  line and an origin dot. Fit (F6) frames the design or the open sketch, never the grid.
- **Undo while a dialog is open cancels the dialog** (key, toolbar or menu, in every dialog);
  Redo there does nothing. In a sketch one Ctrl+Z takes back one line and never leaves it.
- **New bodies are drawn in the default look, Steel satin**, as In This Design lists it; plain
  grey bodies of older designs take it when opened.
- **Typing a number into a named dimension changes its parameter**: name it with "Width = 12",
  type 40 into it later and Width is 40 everywhere.
- **An inch design stays inches everywhere**: sketch grid, snap and drag steps, Thread, Fillet,
  Chamfer, Hardware, Motion Link, the "too big here" messages, the Insert dialogs and drawings;
  a tapped Hole starts as a Unified thread (1/4-20 UNC, not M6).
- **Smaller changes**: double-click a body's name to rename it (its icon makes it active); a
  Hole adds no sketch row to the browser; Group Features is now Create Group; the toolbar is in
  Fusion's order (ASSEMBLE after MODIFY); the command search lists each command once.

### Fixed: the 20 bugs of the book report

1. **Change Parameters' "+" did nothing** (a red "'bool' object" error): fixed, and the + and −
   buttons are no longer blank squares.
2. **An inch design went back to millimetres.** Not Undo's fault: rebuilding a chamfer or fillet
   with several sizes used a hidden helper design whose units FreeCAD copied into yours. Fixed.
3. **Deleting a sketch dimension moved formulas onto the wrong dimensions**: fixed; a dimension
   that follows a parameter is marked (ƒx).
4. **A negative parameter became 0**: fixed.
5. **A sketch on another component's face switched the active component**: fixed.
6. **Extrude's New Body went into the clicked face's component**: fixed.
7. **Offset Plane went into the clicked face's component**: fixed.
8. **Axis Through Cylinder went into the cylinder's component**: fixed.
9. **New Component ticked From Bodies by itself** when a step or face was selected (or, in a new
   design, offered its empty body): fixed; it says which bodies will move when you tick it.
10. **A new component's first extrude cut another component's body**: fixed. Fusion proposes Cut
    only when the shape lies mostly inside a body; the book's link barely overlaps the pin, so
    it is a New Body there.
11. **Edit Joint on an as-built joint was lost**: OK was silently refused, because joints made
    later were checked against parts the edit had rolled back. Later joints now wait during the
    edit, and a refused OK says why.
12. **Edit Joint Limits showed Rigid**: the same cause (the edit had just been cancelled); fixed.
13. **An as-built Slider without an axis became Rigid**: OK was refused, but a Rigid preview
    stayed that looked finished. No joint is kept until the type has what it needs.
14. **Joint references went stale ("Broken link", "?Face5")**: three causes fixed; a joint whose
    face is really gone says so and keeps its parts in place.
15. **A component inside a subassembly could not be picked from the browser** in As-built Joint
    and Rigid Group (the whole subassembly was taken): fixed.
16. **A body turned grey while its look was still listed**: FreeCAD reset the colours when the
    body's material was touched; the look is now put back at once, and dropping it again works.
17. **A face look dropped on an edge coloured the whole body**: it goes to the face next to the
    pointer now.
18. **Undo left an orphan "Combine 1"**: Combine was not the cause; Undo from the toolbar with a
    dialog open left the half-made step for Redo. Undo now cancels an open dialog.
19. **Gear with the book's 0.88 mm root fillet was refused, and OK "made a copy of the previous
    gear"**: the limit was stricter than Fusion's Spur Gear; it is now the same, so the book's
    gears build. A size that really does not fit is said next to the pointer.
20. **Edit Feature on a Gear step deleted it**: only while the Gear dialog was still open on
    that step; the timeline now asks you to finish the dialog first.

### Fixed: everything else the book ran into

- **A construction plane or a joint's symbol in front of a part no longer catches the click**:
  Project, Include 3D Geometry, Sketch Dimension, Fillet, Chamfer, Split Face, Emboss,
  As-built Joint, Physical Material and Appearance take the part behind it. Intersect on a
  construction plane brings in the line where it cuts the sketch (it showed an error).
- **Extrude**: "Sub shape not found: Sketch.InternalFace..." after a parameter changed a sketch
  (the areas are kept now); hair-thin slivers offered as profiles; a sketch pushed through All
  into a part after Flip came up as Join; a fin touching the board only along a curve made a
  second body; a profile was picked together with its face on a busy computer; a cut that only
  reached a hidden body said nothing about it; slow changes on lofted parts.
- **Box and Cylinder**: the height typed right after placing went into another size (the knob's
  -8 became its diameter); moving the mouse onto a size box froze the outline.
- **Commands that did nothing without a word now say why** next to the pointer (features,
  joints, Gear, the timeline, sketch constraints), and a dialog cancelled by another command
  says the change was not kept. A browser right-click no longer ends the command you are in.
- **MODIFY > Scale of a sketch failed now and then** with "conflicting constraints" (the dialog
  stayed open and the sketch was left half scaled), for example a sketch with an ellipse, or a
  triangle made twice as big. Every size is now changed at once.
- **Sketches**: one Ctrl+Z too many left the sketch, and Ctrl+Y closed it; a finished sketch was
  hidden after undo and redo; deleted projected edges came back; Fit zoomed out to 24 m; a
  dimension placed over an axis became an angle; Tangent popped up FreeCAD's "Constraint
  Substitution" box; pressing X stopped the Line chain; a click on the first corner did not
  always close the outline; a line with a typed length was not always exactly upright;
  "Width=5mm" typed in a slot's box ran its letters as shortcuts.
- **Fillet and Chamfer**: a size held at the largest that fits is always said; a fillet that
  cannot be built is refused at once instead of after many seconds; a size typed right after a
  click no longer waits behind the size search; "1/8" typed and OK clicked made a 1 in fillet;
  a part left slightly out of true by earlier steps can be chamfered.
- **Patterns and the timeline**: a pattern of features after a Box or Cylinder off the origin
  missed half its copies (the Geocache knurl); Create Group made the next change rebuild every
  step; after a timeline drag the part showed an unfinished step; CREATE > Pattern could vanish
  from the menu; Redo rebuilt a step (40 s for a knurl); a fast timeline drag did nothing.
- **Joints**: a round edge offered its seam as "(corner)"; a threaded hole's centre was 0.37 mm
  off; an O-ring's centre was inside the rubber; a bolt could go into its hole head first; a
  hover could keep another hole's rim; the lit dot was not always the one clicked; Rest did
  nothing after a drag; Enter closed Motion Study; copies of a patterned subassembly stayed
  bent after a Motion Study; moved parts loosened rigid groups.
- **Small things**: Draft dropped its pull direction; Section Analysis pressed twice made two
  sections, and with the design's top row active lost its section at OK; a hole dragged by its
  dot showed "-55 um"; a cancelled Create Sketch left an empty body; PLASTIC > Rest built on the
  wrong body; a cosmetic thread could turn the whole body a quarter turn; a gear placed on the
  origin landed a hair off it; Combine of mesh bodies sometimes made a body with holes.
- **Drawings**: a corner click beside a long view made no projected view; automatic views
  overlapped (a long assembly got none); balloons sat on one another; a section view landed on
  its base view; long part numbers ran into the next column; a circle clicked where its centre
  mark crosses gave no diameter; Export DXF of a section through two parts printed an error.
- **Export**: 3MF and OBJ files carry the colours you gave bodies and faces.
- **FreeCAD showing through**: its second recovery dialog after a crash, its pixels-per-inch
  question on SVG import, its "Bad base feature" box when Offset Plane started with a step
  selected and its "Solve failed" lines while a joint was previewed are gone; "&" no longer
  vanishes from names on buttons, and a long names button no longer pushes OK off the screen.

## 0.1.0-beta.3.3.10

### Fixed

- **The browser was see-through until the mouse went into it**, had no BROWSER title, and stayed
  over the Home tab. FreeCAD had put the panel the browser lives in into its "overlay" (its
  see-through panels that float over the 3D view) and remembers that in its settings; its keys
  Ctrl+Left / Right / Up / Down do it. While Fission 180 is on, the browser is kept out of
  FreeCAD's overlay (taken out again if anything moves it in), and those four keys do nothing.
  FreeCAD's own interface gets its settings back.
- **Going from a design to Home kept the browser and the timeline open.** Home now has the
  window to itself; both come back when you go back to a design (a browser you closed stays
  closed). Drawing tabs hide the timeline the same way.
- **Hovering a hidden body's row in the browser showed no ghost** while one of its sketches was
  shown. It does now. Section Analysis no longer draws cut faces for such a body's hidden solid.
- **Home made it look as if designs were in Documents\Fission 180 Designs when they were not.**
  A design saved in another folder (like a download you opened) was listed under This
  computer's heading. It now has its own row, Elsewhere on this computer, and its tile says
  which folder it is in; hover it for the full path, right-click > Show in Folder opens it.

## 0.1.0-beta.3.3.9

### New

- **Pattern and Mirror of several bodies at once.** Select several bodies (a box round them,
  Ctrl-clicks in the browser, or clicks while the dialog is open) and Rectangular Pattern,
  Circular Pattern, Pattern on Path and Mirror copy every one of them in one timeline step, as
  in Fusion. In the dialog a click adds a body and a click on a picked one drops it. Mirror
  with Operation Join joins each body with its own mirror image. Changing the quantity later
  keeps the copy bodies already made; deleting one of the original bodies keeps its copies as
  they were, and the step says why. The AI can do it too (`bodies` in its pattern tools).
- **The AI chat shows its answers word by word**, as they arrive, like Claude's and ChatGPT's
  own apps: Claude, ChatGPT, Gemini and local models (Ollama, LM Studio). Stop ends an answer
  at once, even in the middle of a sentence; the words already shown stay. If the connection
  drops in the middle of an answer, the chat says so. A local server that cannot stream works
  as before. The conversation keeps its newest lines in view unless you scrolled up to read.
- **The AI can use the SHEET METAL tab:** sheet metal rules, Flange (base, contour, edge),
  Lofted Flange, Bend, Hem, Join by Bend, Corner Closure, sheet metal Fillet and Chamfer,
  Convert to Sheet Metal, Unfold, Refold, Rip and Create Flat Pattern. It also tells you how
  big the flat sheet is, lists its bends, and saves the flat pattern as a DXF for a laser
  cutter.
- **The AI can use the PLASTIC tab:** Assign Plastic Rule (and change the rule), Boss with its
  screws, Rest, Snap Fit, Lip and Groove, and Design Advice (it only reads your part and lists
  moulding problems).
- **The AI can Fillet, Chamfer, Press Pull, Delete and Merge on surface bodies,** and change all
  of these steps afterwards, as a double-click in the timeline does.

### Fixed

- **The thin outline frame next to right-side panels** has been gone since 0.1.0-beta.3.3.5; a
  test now makes sure it stays gone, and it is off the known issues.

## 0.1.0-beta.3.3.8

### Fixed

- **Switching tools still failed while some dialogs were open.** Starting User Coordinate System
  (and editing other Part Design features with FreeCAD's own panel) made FreeCAD switch to its
  Part Design workbench, which turned the Fission 180 interface off: no ribbon, and no tool key
  (E, H, Q, F, M...) did anything until that panel closed. The interface now stays on, and a
  tool started from there finishes that panel first. A sweep of every SOLID tool followed by
  Extrude, Hole, Press Pull, Fillet, Shell and Move/Copy by their keys found no other case.
  The command search (S) and the browser's right-click commands now also end the running tool
  first (Fission 180's Line kept running under a tool started from the search).
- **Dragging an extrude into the part was slow to show the cut, and changed colours.** While
  the arrow was dragged the extrude stayed a Join, hidden inside the part, so nothing showed until
  you stopped; then the part turned see-through grey with a dark red block. Now it becomes a Cut
  as soon as the arrow goes into the part, and the cut looks the same while dragging as when you
  stop: see-through red, fainter red through the walls, the part keeping its colour. Press Pull
  pushing into a face looks the same way.
- **A shown sketch disappeared when its body was hidden.** In FreeCAD a hidden body hides its
  sketches. Now the body's eye hides only its solid while one of its sketches is shown, so you can
  hide every body and still show a sketch; the browser still shows the body as hidden.
- **Hovering a body in a tool that asks for bodies lit only one face.** In Move/Copy, Combine,
  Split Body, Scale, Interference, Center of Mass, Remove, Silhouette Split, Physical Material,
  Appearance, the Extrude "Bodies to Cut" row and Pattern / Mirror with Bodies, the whole body
  now lights up under the mouse. Boxes that pick faces or edges still light one face or edge.
- **Move/Copy took a "random" body of the ones selected first.** A box round several bodies
  selected each body once per face and edge, and the tool toggled it on and off again, so some
  dropped out. Now every selected body is taken, however it was selected (a box, the browser,
  Shift-clicks); Combine (the first is the Target, the others the Tools), Scale, Remove and
  Appearance take all of them too. A box drawn inside a tool's dialog adds the bodies it covers
  and no longer drops the ones already picked.

### Changed

- **Sketch Fillet no longer follows the mouse.** Click the corners you want (click one again to
  drop it), then drag the blue arrow or type the radius in the FILLET panel; nothing is made
  until OK or Enter, and all the fillets are one undo step.
- **Sketch Chamfer has a CHAMFER panel:** its type (Equal distance, Distance and angle, Two
  distances), the numbers, blue arrows to drag the distances, OK and Cancel.
- **Sketch Offset no longer follows the mouse:** drag its blue arrow (through the curve to switch
  sides), type the distance, or click where the offset should go.
- **Trim, Extend, Break, Project, Include 3D Geometry and Intersect** show a small panel saying
  what to click, with a Done button to finish.

## 0.1.0-beta.3.3.7

### Fixed

- **Extruding separate sketch areas made one body.** A New Body extrude of areas that do not
  touch now makes one body per separate piece, as Fusion does; areas that touch are one body.
  It is still one step in the timeline: editing it keeps each body, deleting it removes them.
- **Split Body split every separate piece of a body.** A body made of separate pieces (from
  older designs) split by a plane through one piece became a body per piece. Now only what the
  splitting tool crosses is split; the other pieces stay as they were.
- **Hidden sketches showed up while picking areas to extrude.** A sketch you hid stays hidden;
  only shown sketches offer their areas (the sketch of an extrude you edit still shows).
- **Clicking another tool sometimes did nothing.** FreeCAD's own commands refused to start
  while another command's panel was open (or, in a sketch, while a drawing tool ran), and the
  click was silently lost. Now the running command ends first (as in Fusion: its panel is
  finished, a sketch tool stops) and the new one starts; if a command really cannot start, a
  message says so. Drop-down menus no longer grey out commands just because another one is open.
- **The snap dot covered the midpoint triangle.** Inside a snap marker (the middle's triangle,
  an end's square) the dot is now small, so the marker stays readable.
- **A cut hidden inside the part could not be seen.** The red preview of a cut now also shows
  through the walls that hide it, fainter, as in Fusion.
- **The Split Body icon** has its blade line in the cut between the two pieces, not at the top.
- **Sketch Move/Copy did not work, or left orange dots behind.** It is now Fission 180's own
  tool, like Fusion's: it opens its MOVE/COPY panel every time (button or M), you pick curves by
  clicking or by dragging a box, and red / green arrows, a turn handle and a ball move them with
  the values shown live (X / Y Distance, Angle, Create Copy, Point to Point). Nothing is left
  behind, and one Ctrl+Z undoes it. Ctrl+V in a sketch hands the pasted curves to it too.
- **Moving or scaling sketch curves keeps them exactly where you put them:** dimensions show the
  new sizes, and ties to curves that stay are loosened instead of pulling them back.
- **A crash when closing a design while a sketch was open** (the right-angle marks read the 3D
  view after it was gone).

### New

- **Sketch Scale has its own panel:** pick curves (a box too), click a base point, and set the
  size as a factor (2, 0.5) or a percentage (150 %), or drag the blue arrow.
- **Sketch Rectangular and Circular Pattern have Fusion's panels:** pick curves by clicking or a
  box, see the copies before OK, drag blue arrows to space them or the white disc to set how far
  a circular pattern goes (360, 180, 90...), and undo the whole pattern in one step.
- **The body Circular Pattern's angle disc** can be dragged in Full too: dragging it turns the
  pattern into an Angle pattern that goes as far round as you drag.
- **Touchpads:** in the 3D view, drag two fingers to move the view, pinch to zoom around the
  pointer; a mouse wheel still zooms as before. Preferences > General > Navigation > Touchpad:
  Auto (default), Off (scrolling always zooms, as before) or On (scrolling always pans).
- **The browser acts on every selected body:** with several selected, a right-click's Hide /
  Show, Opacity, Delete, Remove, Isolate, Find in Window, Physical Material and Appearance apply to
  all of them, and clicking the eye of one hides or shows them all. A right-click no longer
  drops the others from the selection.

### Changed

- **Pattern and Mirror start with Bodies,** like the other body tools: a click on the part takes
  the whole body. Click a step in the timeline to pattern that feature instead.

- **AI: every body and sketch it makes must have a name.** Whatever AI you use (the chat panel or
  an AI app connected to Fission 180), it is told to name what it makes, the making tools take a
  name, and if it leaves something unnamed its next change is refused until it renames it.

## 0.1.0-beta.3.3.6

### New

- **Linux: Update now updates the AppImage itself.** Help > Check for Updates (or the update
  line on Home) > Update now downloads the new AppImage next to the one you run, checks it
  against its checksum, closes Fission 180 (it asks about unsaved designs first), puts the new
  AppImage in place of the old one under the same name and starts it. No terminal, no
  download folder; your menu entry and shortcuts keep working. If the AppImage is in a folder
  Fission 180 is not allowed to change, it says so and opens the release page instead (move
  the AppImage into a folder of your own, such as ~/Applications, and Update now works from
  then on).
  This works from this version on: an AppImage older than 0.1.0-beta.3.3.6 cannot replace
  itself, so download this one by hand once (make it executable, and put it where the old one
  was, under the same name).

## 0.1.0-beta.3.3.5

### Fixed

- **Linux: Fission 180 did not start on up-to-date systems** ("Could not initialize GLX", then
  it closed). The AppImage carried an old copy of a small graphics library (libdrm) that hid
  the newer one your system's graphics driver needs (seen on CachyOS with an AMD Radeon 680M).
  The AppImage now uses your system's copy. Linux users: download the new AppImage and replace
  the old file.
- **A thin line stayed on the 3D view where a dialog had been** (most visible on Linux). It
  was the frame of FreeCAD's empty Tasks area; it has no frame now.

### Changed

- **The toolbar fits narrow windows.** When the window is too narrow for every big icon, each
  group shows as many as fit, taking icons off the fullest groups first; nothing overlaps any
  more. Every command stays in its group's drop-down menu, and the icons come back as the
  window grows.
- **Any command can be taken off the toolbar.** A group's own icons can now be unpinned too
  (Unpin from Toolbar in its three-dot menu, or right-click its icon), and as many commands
  as you like can be pinned. Reset All Toolbar Customization (right-click the toolbar) puts
  everything back as it came.
- **Right-click a command in a drop-down menu** to get its options (Pin to Toolbar or Unpin,
  Change Keyboard Shortcut), the same as its three dots. It no longer runs the command.

### New

- **Interface size** (Preferences > General > Appearance): make the whole window (toolbar,
  panels, text, icons) smaller, for more room for the 3D view, or bigger: 75 % to 150 %, on top
  of your system's own display scaling. It shows the next time Fission 180 starts.

## 0.1.0-beta.3.3.4

### Fixed

- **Trim moved a spline.** When a spline ended on a line (not on its corner) and you trimmed
  that line, FreeCAD cut the line where the spline's hidden control-point circle crossed it,
  not at the spline's end, and tied what was left of the line to that circle, so the spline's
  end shifted. Trim now cuts lines, arcs and circles exactly where the curves crossing them
  are, joins what is left to them (to the spline's end itself when it ends there), and after
  every trim checks that nothing else in the sketch moved, even by a millionth of a
  millimetre. If something would move, the trim is not done and a note says so.
- **Spline points did not snap.** The spline tools now snap like the other tools: to ends,
  middles, centres, quadrants and crossings, to the grid and to the dashed alignment guides,
  with the snap dot. The point goes exactly there, and the spline's ends are joined to the
  point they snapped to.
- **The selected type in Feature Options was orange.** It is the theme's blue now.
- **Trim after the spline's green check.** Starting a tool after a spline now always stops
  FreeCAD's spline tool first, even when its pointer is not on the view. (Trim started from
  the ribbon, with T and from the right-click menu after the check in every test here.)

## 0.1.0-beta.3.3.3

### Fixed

- **OK in the right-click menu still lost a spline and left its orange points.** Fission 180
  decided "a spline is being drawn" from signs that can change while you draw (the mouse
  pointer's shape, the last command, FreeCAD's panel). When one of them said "no" at the
  moment you pressed OK, the spline was thrown away. Fission 180 now remembers the spline
  from your first click, as long as its points are in the sketch: OK in the right-click
  menu, the green check, Enter and Finish Sketch all make it, whatever else changed. And if
  FreeCAD's spline tool ever stops without making the spline, Fission 180 makes it from your
  points a moment later, so no loose points are left behind.
- **The green check beside a spline vanished when the pointer went onto it.** It is now
  placed by the spline's last point in the sketch, so it stays there until you click it.
- **A spline through three points looked like it left a dot behind.** With exactly three
  points, FreeCAD ties the middle one to the curve in a different way; Fission 180 now knows
  that point belongs to the spline (before, it could even be taken into the next spline).
- **Select in the toolbar closed the sketch.** Clicking Select while a sketch tool (Mirror,
  for example) was running left the sketch and went back to the SOLID tab. It now only ends
  the tool; the sketch stays open.

### Changed

- **Box selection in Mirror.** With Objects active, drag a box over the curves: left to right
  takes the curves fully inside the box, right to left takes every curve the box touches (as
  in Fusion). Shift adds to what is picked, Ctrl toggles.
- **Each sketch tool has its own icon.** Every way of drawing a rectangle, circle, arc,
  polygon, slot, spline and line has its own picture in the ribbon, the menus, the
  right-click menu and the Sketch Palette's Feature Options: the shape, with the points you
  click shown in blue.

## 0.1.0-beta.3.3.2

### Fixed

- **A spline could still vanish and leave its points behind.** 0.1.0-beta.3.3.1 fixed Finish
  Sketch, but Fission 180 still worked out "a spline is being drawn" from the last menu
  command. A spline started any other way (from the command search, FreeCAD's own menus),
  or right after the Line tool, was not recognised: the green check then ended the old line
  instead and the spline was thrown away. Fission 180 now also reads FreeCAD's own spline
  panel, the green check always belongs to the spline being drawn, and after every finish
  it checks that the spline really exists. If FreeCAD did not make it, Fission 180 makes it
  from the points you clicked, with its ends joined where you clicked them. Esc cancels a
  spline and now takes all of its points with it, so no dots are ever left behind.
- **Trim left pieces of a line at the corners under a spline.** A spline's control points
  have small helper circles; Trim stopped where they crossed the line, so the ends of a
  rectangle's top stayed behind. Trim (and Extend, Break) now ignore a spline's helpers: the
  piece that lights up is the piece that goes.
- **Command search ran the wrong command.** Typing "Control Point Spline" ran a FreeCAD
  command named "Toggle B-Spline Control Point Weight". The search now knows every tool by
  the name in Fission 180's menus, and the name you typed in full comes first.

### Changed

- **Mirror has Fusion's MIRROR panel.** Pick the Objects (click the curves), click Mirror
  Line's Select and the line (a line, a construction line, an axis or a projected line); the
  copies show where they will be; OK. The copies stay symmetric to the originals (move an
  original and its copy follows), and one Ctrl+Z takes the mirror back. Curves selected before
  Mirror are taken as the Objects.
- **Feature Options in the Sketch Palette.** While a rectangle, circle, arc, polygon, slot or
  spline tool runs, the palette lists its types (for example 2-Point, 3-Point and Center
  Rectangle); a click switches to that type and you go on drawing, as in Fusion.

## 0.1.0-beta.3.3.1

### Fixed

- **Finish Sketch threw away a spline you were still drawing.** If you clicked the points of a
  spline and then pressed the green Finish Sketch check (in the ribbon, the right-click menu or
  the Sketch Palette), the spline vanished and its points were left behind in the sketch. Only
  Enter made it. Finish Sketch now works like OK: the spline is made from the points you
  clicked, then the sketch closes. The same goes for the other tools that can be finished (a
  conic, an Offset with curves picked, a 3D spline).
- **Undoing a spline took two presses of Ctrl+Z.** The first one only took back how its ends
  were joined to other points; the spline stayed. One Ctrl+Z now takes the whole spline back
  (and Ctrl+Y brings it back whole).
- **No 90 degree mark where sketch lines meet at a right angle.** Where two lines meet at 90
  degrees and the sketch keeps it so (an upright line on a level one, or lines made
  perpendicular), a small square corner mark now shows at the corner, also where a line ends on
  the middle of another (a T). It stays the same size when you zoom and hides with **Show
  Constraints** in the Sketch Palette.
- **Fission 180's own sketch tools had no picture beside the pointer.** Trim (the scissors),
  Extend, Break, Fillet, Chamfer, Offset, 2-Point Circle, the tangent circles, Tangent Arc,
  Midpoint Line, 3-Point Rectangle, Edge Polygon, the slots, Conic Curve, Project to Surface,
  Collinear, Concentric, Midpoint, Curvature and the 3D Sketch tools only showed a plain cross.
  They now show the crosshair with the tool's own picture, like the other sketch tools.
- **The window title said "Fission 180 1.1.4".** 1.1.4 is the version of FreeCAD that Fission 180
  is built on, not Fission 180's. The title now says just **Fission 180** (with the design's
  name in front when one is open); Fission 180's own version is on the Home tab.

## 0.1.0-beta.3.3

### The new name: Fission 180

- **SciForge is now Fission 180.** The program, its window title, About box, splash screen,
  icon, menus, messages, installer, Start menu entry and this GitHub page all carry the new
  name, and it has a new logo: a circle splitting in two, with the spark of the split.
- **Nothing of yours is lost.** Designs saved by SciForge open as before (the names SciForge
  saved inside them are renamed when they open; saving writes the new ones). At the first start
  Fission 180 brings over SciForge's settings, shortcuts, Home list, places, AI keys, drawing
  templates and your own materials, and an AI app you connected to SciForge (Claude Desktop,
  Gemini CLI) is connected to Fission 180 instead. The AI connector is Fission 180's own now: a
  Claude Desktop extension made by SciForge no longer connects, so remove it in Claude
  (Settings > Extensions) and add Fission 180's from Preferences > AI.
- **The installer replaces SciForge**: it removes an installed SciForge (only the program, never
  your settings or designs), so you do not end up with two of them.
- The repository moves to `github.com/Luca0422git/Fission-180`; the old addresses keep working.

## 0.1.0-beta.3.2.1

### Fixed

- **Sketch value boxes: the arrow keys moved the view.** While you typed a value in a box
  beside the pointer (a fillet radius, a rectangle's width, a slot...), Left and Right panned
  the view instead of moving the typing cursor. The box now shows a cursor; Left, Right, Home
  and End move it, Backspace and Delete remove the character before or after it, and what you
  type goes in where the cursor is.
- **Picking another sketch tool did not stop the one running.** With Rectangle running,
  clicking Offset (or Mirror, a pattern, Move/Copy, Scale or a constraint) left Rectangle
  going: your clicks drew a rectangle instead of picking curves. Any sketch tool now replaces
  the one before, as in Fusion.
- **Sketch Fillet: several corners at once, and corners show when you point at them.** Click a
  corner, then more corners, then type the radius and press Enter: they are all rounded with
  the same radius in one step (one radius dimension; the others stay equal to it). With the
  pointer on a corner, both of its lines light up, the rounding it would get shows, and a dot
  sits on the corner. Enter with nothing typed now makes the fillet at the size shown.
- **Sketch Offset had no dialog and always took the whole chain.** Offset (O) now opens an
  OFFSET panel like Fusion's: untick **Chain Selection** to offset just one line (or pick
  several lines one by one; a click on a picked line drops it), choose **One Side** or
  **Symmetric** (both sides at once), **Flip** to change the side, type or drag the distance,
  then OK or Enter. Corners stay sharp (a rectangle offset is a bigger rectangle, not a rounded
  one), and the distance stays a dimension you can double-click and change later.
- **Snapping had no clear feedback.** While drawing, a white dot now shows exactly where the
  point will land when it snaps: on an end, a middle, a centre, a crossing, or on a line or
  curve.
- **A line at 90 degrees did not stay at 90 degrees when it ended on a curve.** Drawing a line
  straight out from another line (or level, or upright) onto an arc or circle used to end it
  wherever the pointer touched the curve, a degree or two off. The line now keeps its 90
  degrees (or level, or upright) and ends exactly where that meets the curve, with the
  constraints that keep it so.
- **Align was way off after splitting a body.** When you split a body with one of the XY / XZ
  / YZ planes, moved a piece and aligned it back, a click on the cut face could pick the plane
  drawn in the same place instead (or do nothing), and aligning to one of those planes threw
  the piece to the centre of the design or flipped it into the other piece. A click on the cut
  face now picks the face, so the piece goes back exactly where it was, and aligning to a plane
  just slides the piece straight onto it, keeping its side (Flip puts it on the other side).
- **A second click in the browser now renames.** Click a body, sketch or component (or another
  row that can be renamed) that is already selected, wait a moment, and its name opens for
  typing, as in Fusion and Windows Explorer. A quick double-click still edits the sketch or
  activates the body; clicks on the eye or the icon do what they always did.
- **A "Body" showed in the browser before anything was solid.** Starting a sketch in a new
  design listed a body although there were none yet (Fission 180 makes one to hold the sketch).
  It is no longer listed; it appears with your first extrude, as in Fusion. The sketch still
  shows under Sketches.

## 0.1.0-beta.3.2

**A full build after 0.1.0-beta.3.1.3.** The Linux AppImage needed a change in how it is
packed, so this version comes as a new installer: Fission 180's **Update now** downloads and runs
it (the AppImage: download the new one).

### Fixed

- **Renaming: the new name could end up after the old one.** Right after Rename (a timeline
  step or group, or a row in the browser) the 3D view takes the keyboard for a moment; the name
  field took it back, but the old name was no longer selected, so what you typed went after it
  ("Extrude 2Boss" instead of "Boss"). The old name now stays selected, and typing replaces it.
- **Closing a design could crash Fission180** in two cases: when its drawing was the tab you were
  looking at, and when a dialog with drag arrows (such as Point Probes on simulation results)
  was still open. Both close cleanly now.
- **Timeline playback went on after a command.** If you pressed Play on the timeline, then
  started a command (E for Extrude, say) and cancelled it quickly, the playback kept going and
  the design moved on under you. Starting a command now stops the playback at once, as in
  Fusion.

### Under the hood

- Fission 180's own tests now wait for what the program is doing instead of for fixed times, so
  they give the same result on every computer; they found the bugs above.

## 0.1.0-beta.3.1.3

### Fixed

- **Pan and orbit stopped working after dragging a component.** After you moved a component by
  dragging it in the 3D view (Component Drag), a middle-drag no longer panned and Shift +
  middle-drag no longer orbited, until you clicked an empty part of the view. FreeCAD's
  navigation saw the drag's mouse press but not its release, so it thought the left button was
  still held. It now gets the release too (without selecting anything), and panning and
  orbiting work right away.
- **The ViewCube could stay stuck to the mouse.** If the mouse button was let go somewhere the
  cube did not notice (for example as the window lost the mouse), the cube went on turning the
  view as the mouse moved, with no button held. A move without the button now ends the drag.

## 0.1.0-beta.3.1.2

### Fixed

- **Updating to a new full version could leave you with no Fission 180 (Windows).** If you had
  connected Fission 180 to Claude Desktop (or Gemini CLI, Claude Code), that app keeps Fission 180's
  AI connector running, a program from Fission 180's own folder. The installer deleted every file
  it could, stopped at the connector's files ("Failed to remove ... no files are in use") and
  gave up, with half of Fission 180 gone. Now the installer first stops the AI connector (it asks;
  the AI app starts it again the next time it opens), says which other program is still using
  the folder and lets you close it and click Retry, and only then replaces the old Fission 180, in
  one step: if anything still holds a file, nothing has been removed and your Fission 180 keeps
  working. Uninstalling stops the connector too. This version's installer has the fix; it is
  what **Update now** runs when you come from 0.1.0-beta.3 or older.

## 0.1.0-beta.3.1.1

### Fixed

- **Sketch Text: the TEXT panel was see-through.** In the floating panel on the right, a click
  on the Text box went through to the sketch behind it, so typing stopped working. The panel
  (and Measure's box in a sketch) now has its own background and takes the click.
- **Sketch Text: words stay inside the box you drew.** A word that runs past the frame's right
  edge goes on the next line (a word longer than the whole frame is broken). If the lines need
  more height than the frame has, the dialog says so. Texts in designs made before this keep
  their single line until you edit them.
- **Joint: OK right after picking a Type left the part moving.** The Joint dialog plays the
  new motion once when you pick a type (Revolute, Slider...). If OK came at the very moment
  that preview was about to start (easiest on a busy computer), it started after the dialog
  had closed: the part swung on its own, could stay a little turned, and Ctrl+Z no longer
  put it back. The preview now never starts once the dialog is closed.

## 0.1.0-beta.3.1

**A full build after beta 3, for VEX robots.** The program itself was built again with one
change to FreeCAD's own code, so it comes as a new installer: Fission 180's **Update now**
downloads and runs it (the AppImage: download the new one).

### Improved

- **Selectable/Unselectable** (right-click a body, mesh body or component in the browser, like
  Fusion): it stays visible but can no longer be clicked in the 3D view, so the screws and
  parts around a big frame are easy to pick. A small red mark on its icon shows it; the same
  entry turns it back. An unselectable component covers every body in it. Saved with the
  design, one Undo step; the browser still selects it.
- **Big assemblies open faster**: FreeCAD made a placement indicator (the axis cross of Show
  Placement) for every part and origin plane when a design opened, about 8 seconds of a
  300-part robot; it is now made only when someone turns Show Placement on.

## 0.1.0-beta.3

**The third beta.** Three new things: **stress simulation** (Fusion's Simulation workspace with
its Static Stress study, solved on your own computer), **Auto Timeline** (an AI turns a part
without a timeline, such as a STEP file or a simple mesh, into a real part with timeline
steps you can edit), and **VEX robotics assemblies** (snapping to the centre of square holes,
many STEP parts at once, Duplicate With Joints, and big assemblies much faster). Nothing in the
compiled program changed: if you have 0.1.0-beta.2 or later, **Update now** only replaces
Fission 180's own part.

### Simulation (Static Stress)

- **Workspace > Simulation** opens Fusion's SIMULATION workspace with its **SETUP** and
  **RESULTS** tabs; your studies are saved in the design, and **Design** takes you back.
- **New Simulation Study**: Static Stress. Fusion's other study types are listed greyed (they
  are not in Fission 180 yet). A study can be cloned (right-click > Clone Study) for another load
  case.
- **Study Materials** (try another material in the study only; yield or ultimate strength for
  the safety factor), **Study Settings** (mesh size, element type, adaptive mesh refinement,
  keep the results in the file or not), **Structural Constraints** (Fixed, Pin, Frictionless,
  Prescribed Displacement), **Structural Loads** (Force along the face, at an angle or along a
  direction; Pressure; Moment; Bearing Load; Remote Force; gravity, with Edit Gravity),
  **Automatic Contacts** (bodies that touch are bonded), **Local Mesh Control**, **Generate
  Mesh**, **DOF View** (arrows for every way a part could still move), **Load Case
  Attributes**, and **Pre-check** with a traffic light and a **Repair** button that opens what
  to fix. Every setup change is one Undo step; the values follow the design's units (mm, in...).
- **Solve runs on your own computer** (Fusion uses Autodesk's cloud), in the background: you can
  keep working, and **Cancel** stops it at any moment. **Job Status** lists your solves.
- **RESULTS**: the part coloured by **Safety Factor** (red is weak), von Mises and principal
  stresses, displacements and strains, with a legend you can change, units, **deformation scale**
  and **Animate** (save it as a GIF), **min / max** tags, **Surface** and **Point Probes**,
  **Slice Plane**, **Iso-surface**, **Reaction Force**, **Results Details** with a plain verdict
  ("meets the safety factor target", with the weakest body named), **Compare** up to four studies
  side by side, **Convergence Plot**, and a **Report** (a web page with the setup, the numbers and
  pictures). Right-click on the results for the results tools.
- **Out of date**: change the design or the setup after solving (a hole moved, a part turned)
  and the results say so; **Solve Again** brings them up to date.
- **Checked against hand calculations** (over 300 checks, on Linux and on Windows): beams,
  plates, tubes in torsion, gravity, two glued materials, pins and bearings, inch parts, very
  small and very large parts: within a few percent at the default mesh, and the reaction
  forces add up to the loads exactly. Thin walls get a note asking for a finer mesh, which
  then lands within about 1 %.
- **The AI can run studies too**: "hold the holes, push 1000 N on the top, solve and tell me
  the safety factor".

### Auto Timeline (AI)

- **Right-click a body > Rebuild with Timeline (AI)...** (also on the 3D view's right-click and in
  UTILITIES > AI). The part becomes a faint reference; a new body takes the rebuild. If
  Fission 180's chat has an AI set up, it opens with a ready message (you press Send); otherwise the
  message is copied for your AI app (Claude Desktop, Gemini CLI...).
- Fission 180 reads the part for the AI: its base shape and profile, holes (counterbores,
  countersinks, patterns), pockets, bosses, fillets, chamfers, revolved parts, and gives a step-by-
  step plan in Fusion's order. The AI builds it with the normal tools, so every step is a real
  timeline step, and checks itself after each one. The result really is parametric: make the
  rebuilt plate thicker and its pockets and holes move with its top face.
- **Compare with Reference** (UTILITIES > AI) shows how close the rebuild is: missing material in
  red, extra in green, and what to do next in words. **Finish Rebuild** gives the new part the
  original's name, place, material and spot in the timeline; joints, grounds and patterns that
  used the original move onto the rebuild (a VEX part keeps its joints). **Stop Rebuild...**
  gives a rebuild up. A design saved half way carries on when you open it again.
- Simple meshes (STL, OBJ, 3MF; closed, up to 10,000 triangles) work too. What Fission 180 cannot
  read (free-form surfaces, threads, raised or engraved text) is named, never guessed.

### VEX robotics and big assemblies

- **Square-hole centres**: in Joint, Joint Origin, As-built Joint, Align and Duplicate With
  Joints, a blue dot shows at the centre of any hole (square, hex, slot, the motor's square
  socket) under or near the mouse, and along a hole's walls. Fusion does not have this; VEX
  teams add points by hand there.
- **Ctrl** keeps the face you are on while you reach for its edge; **Shift** turns Align's dots
  off.
- **Insert STEP takes many files at once** (each becomes a part, laid out in a row, one Undo for
  all), the **Data Panel** uploads several files and drags STEP parts into the design, and
  **inserting the same file again** makes another copy of the same part ("screw:2"); a drawing's
  parts list counts the copies. Delete the first copy and the next one simply becomes the part.
- **Duplicate With Joints** (ASSEMBLE): click hole after hole to put more screws (with their nuts)
  in, each jointed like the first.
- **Big assemblies are much faster**: a 300-part robot opens in about 28 seconds (it took over
  two minutes), hovering a rail with 245 holes is instant, and driving a joint is live.
- **Aluminium AlMg3 (5754)** in the materials: the alloy next to the 5052 VEX metal is made
  of, so a stress test of a VEX part reads a realistic safety factor.
- A page for teams: [docs/fission180/vex.md](docs/fission180/vex.md).

### Fixed

- **Designs in inches:** a plain number typed into a dialog (Offset 1.5) or into a sketch's
  dimension or value box (a circle 1 across) was taken as millimetres. It is now in the
  design's units everywhere; type "20 mm" to give millimetres.
- **Closing a design while a tool waited for a click** (Extrude, Hole, Fillet, Offset...) left
  that tool's Undo step open: the next design's first edit went into it, and Undo then took
  back two edits at once under the other design's tool name. Fixed for every tool.

### Known problems

The list is in [docs/fission180/known-issues.md](docs/fission180/known-issues.md). New in this beta:
simulation does Static Stress only (one load case per study, bonded contacts only); opening a
300-part robot still takes about half a minute; Auto Timeline reads prismatic and turned parts,
not free-form ones.

## 0.1.0-beta.2.2

### Fixed

- **A joint lost its face when a later step changed the body.** A fillet (or another step)
  added after a joint renumbered the body's faces: the joint went red ("?Face6") and its part
  could jump. The joint now finds its face, edge or point again by its shape and place and
  keeps working. This is the likely cause of "deleting a joint breaks the body": deleting a
  joint itself (browser right-click, the Delete key, the timeline, Del in the 3D view) was
  tested every way and leaves both bodies exactly as they were, with their fillets still
  editable. If it still happens to you, please send the design.

### Improved

- **Drag a joint to set its limits.** In Edit Joint Limits (or the Joint dialog's Motion tab)
  a handle stands on the joint: a disc round its axis for a turn, an arrow for a slide. Drag
  it, or drag the moving part itself, and the joint moves with you. Tick Minimum, Maximum or
  Rest (or click into its box) and that value follows the drag. A faint amber ghost of the
  part shows where Minimum and Maximum are. OK keeps it as one undo step; Cancel puts
  everything back.
- **Hover a hidden body in the browser** and a faint see-through ghost of it shows in the 3D
  view (also hidden components and mesh bodies). Nothing about the body changes.
- **Fillet and Chamfer arrows are diagonal**, like Fusion's: the arrow stands on the middle of
  the round or bevel and points out of the part halfway between the two faces (Equal Distance
  chamfers, variable-radius points and Chord Length too). Two Distances keeps one arrow on
  each face.

## 0.1.0-beta.2.1

**A patch of 0.1.0-beta.2.** Only Fission 180's own files changed: **Help > Check for Updates >
Update now** installs it in about a minute.

### Fixed

- **Create Sketch on a face that a later step changed** (a Draft, a fillet or chamfer round
  it, Press Pull) showed the face's outline from before that step, so the purple outline was
  too big or in the wrong place. It now shows the face as it is. Suppressing or deleting that
  step later leaves the sketch and what you built on it in place, and the outline follows.
  Sketches made before this patch keep the outline they got: make them again to get the right
  one. (In 0.1.0-beta too.)
- **Hole > From Sketch** no longer drills at the circles of the face the sketch is on (a hole
  already in the face, a boss standing on it), only at the points and circles you drew.

## 0.1.0-beta.2

**The second beta.** Two new tabs, a complete SURFACE tab, a Data Panel like Fusion's, and a big
round of work on speed and on Fission 180 explaining itself. If you have 0.1.0-beta, **Update now**
only has to replace Fission 180's own part: the compiled program has not changed.

### New tabs and tools

- **SHEET METAL tab**: sheet metal rules (thickness, bend radius, K-factor, reliefs; a library
  and rules kept in the design), **Flange** (one command for base, contour and edge flanges),
  Bend, Hem (six kinds), Join by Bend, Corner Closure, Lofted Flange, sheet metal Fillet and
  Chamfer, Convert to Sheet Metal, Rip, Unfold and Refold, and **Create Flat Pattern** with
  **Export DXF** (bend lines on their own layers). Drawings get a Bend Table and Bend Notes.
- **PLASTIC tab**: plastic rules for each component (a library of 16, including FDM PLA and
  PETG) that Shell, Draft, Rib, Web and thin Extrude follow; Boss (with its screws), Rest, Rule
  Fillet, Snap Fit, Lip and Groove, and **Design Advice**.
- **The SURFACE tab is complete**: more of Fusion's options in Extrude, Revolve, Sweep, Loft,
  Patch, Offset, Untrim, Extend, Stitch, Trim and Ruled; SOLID's modify tools work on surface
  bodies (Fillet, Chamfer, Press Pull, Split Face, Merge, Replace Face, Move/Copy, Align, Scale,
  Pattern, Mirror); Environment Map analysis; Isoparametric Curve in sketches.
- **Draft takes curved and free-form walls** (splines, ellipses), not only flat and round ones.

### Designs, files and the browser

- **A Data Panel like Fusion's**: cards with pictures, search, sort, list or grid, and details
  with a design's versions and where it is used. **Drag a design into an open design** to
  insert a copy; drag files from your file manager onto the panel to add them.
- **Delete a design** from Home (the **...** on a tile, or the Delete key) and from the Data
  Panel. It goes to a trash folder in the same place, never deleted for good.
- **Opacity Control**: right-click a body or component in the browser.
- **Hovering over a body in the 3D view lights its row in the browser.**
- **Export and import reports**: after an export, a short card says what that file format does
  not keep; after an import, what did not come in.
- **Drawing PDFs** with layers you can switch on and off and text you can search.

### Faster, and it explains itself

- **Dragging never waits for the model**: Draft, Fillet, Chamfer, Shell, Press Pull and Extrude
  show a live picture while you drag; the exact result follows when the mouse rests.
- **Editing an earlier step rolls back the later ones while you edit**, as in Fusion.
- **Values stop at the limit**: Fillet, Chamfer, Draft, Shell, Press Pull, Thicken, a tapered or
  thin Extrude, Revolve, Coil, Pipe, Torus, Gear and sketch fillets stop at the largest value
  that works and say so, instead of failing.
- **Sketches explain themselves**: a conflict names the constraints involved and rings them in
  red; a padlock marks fully constrained sketches in the browser and the timeline, and the
  Sketch Palette says how many are left to define.
- **Big designs**: the browser and timeline re-read the design only after a change, and Undo /
  Redo on big parts take about a second instead of many.

### AI

- **117 AI tools** (there were 16), the same for the chat panel and for AI apps you connect,
  including tools the AI uses to check its own work (inspect the design, find geometry, check
  for problems, render a picture, compare two states), and a documentation library it can
  search.
- **Not yet**: the AI cannot use the new SHEET METAL and PLASTIC tabs, nor the SURFACE tab's
  Fillet, Chamfer, Press Pull, Delete and Merge on surface bodies. Its tools for them come
  next.

### Fixed

- **A crash when a design with a drawing closed** while the mouse pointer was on a view of
  the drawing sheet (closing with the keyboard, or the AI closing the design). It was in
  0.1.0-beta too.

### Known problems

The list is in [docs/fission180/known-issues.md](docs/fission180/known-issues.md). New in this beta:
the SHEET METAL and PLASTIC tabs are the least used parts of Fission 180 so far, and the AI cannot
use them yet.

## 0.1.0-beta

**The first public beta.** Fission 180 is parametric CAD that works the way people who know Fusion
expect it to, free and open source, built on FreeCAD 1.1.4. It is a beta: every feature is tested
by driving the real program, but it has had little use by anyone but its author, so expect rough
edges (read the known issues).

### What you can do

- **Design the Fusion way**: the ribbon (SOLID, SURFACE, MESH, UTILITIES, and SKETCH while
  sketching), the browser, the timeline with a rollback marker, the navigation bar and ViewCube,
  the `S` command search, Fusion's keys and mouse. Dark look by default, a light look in
  Preferences. Home tab with your recent designs, places and a design picture for each.
- **Sketches** with the sketch palette: lines, rectangles, circles, arcs, polygons, slots,
  splines, text; the Sketch Dimension tool; automatic constraints and snapping guides; trim,
  offset, mirror, patterns and more.
- **Solid modeling**: Extrude (all start and extent types, taper, thin), Revolve, Sweep, Loft,
  Rib, Web, Emboss, **Press Pull** (faces, edges, fillet faces, with a draggable arrow), Fillet
  and Chamfer, Shell, Draft, Scale, Combine, Split Body and Split Face, Replace Face, Move/Copy
  and Align, Hole and Thread (simple, counterbore, countersink, tapped, modeled threads),
  primitives (box, cylinder, sphere, torus, coil, pipe), gears, mirror and rectangular, circular
  and path patterns of features, faces and bodies.
- **Components and joints**: components, moving and copying them, rigid, revolute, slider,
  cylindrical, pin-slot, planar and ball joints, as-built joints, joint motion limits, joint drives.
- **Surfaces**: patch, stitch, unstitch, trim, extend, ruled, boundary fill, thicken, delete face.
- **Mesh**: insert, tessellate, repair, reduce, remesh, plane cut, separate and combine, face
  groups, direct edit.
- **Drawings**: base, projected, section, detail and broken views, dimensions with tolerances,
  balloons and parts list, export to PDF and DXF.
- **3D printing**: send to a slicer or export 3MF / STL; **hardware library** (screws, nuts, washers, heat-set inserts, magnets);
  insert STEP, DXF, SVG, canvas pictures, meshes; export everything to open formats.
- **Inspect**: measure, interference, section analysis, curvature, zebra and draft analysis,
  center of mass, construction planes, axes and points.
- **Parameters** you can use in every number field, and **version history** for each design.
- **AI features, off unless you use them**: a chat panel where you connect your own Claude,
  ChatGPT, Gemini or local (Ollama, LM Studio) key and ask it to build; and a connector so AI
  apps such as Claude Desktop can build in Fission 180 (off until you switch it on in Preferences,
  asks you before the first change in each session, every step is one Undo).
- **FreeCAD Tools**: FreeCAD's own workbenches one click away, with a "Back to Fission 180" bar.
- **An example design**: a Raspberry Pi 5 case, built with Fission 180, in
  [docs/fission180/examples/pi5-case](docs/fission180/examples/pi5-case/README.md).

### New in the way you get and look after Fission 180

- **Windows installer and portable download, and a Linux AppImage**, from the
  [Releases page](https://github.com/Luca0422git/Fission-180/releases). Fission 180 installs next to
  FreeCAD without touching it (its own settings folder, own installer entry).
- **Help > Report a Problem**: one dialog that gathers the useful details (versions, graphics
  card, recent Fission 180 messages, the last crash log) with your name and folders removed. You
  see everything first, then Save it, Copy it, or Open it on GitHub in your browser. Nothing is
  uploaded by Fission 180.
- **A crash log**: if Fission 180 closes unexpectedly, the next start shows a one-line note on Home
  with a button to report it.
- **Help > Check for Updates**, and a quiet check when Fission 180 starts (at most once a day, off in
  Preferences > General). A new version shows as an **update icon in the top right** of the window
  (next to the search button; it stays until you update) and as one line on Home with **Update
  now**, **What's new** and **Later**. Nothing is installed without your click.
- **A one-line welcome** on Home the first time you start it. It can be closed for good.
- **Version 0.1.0-beta** shown quietly on Home, in Fission 180 > Diagnostics, on the splash and in
  Help > About.
- **Privacy**: no accounts, no telemetry; the update check and the AI features you connect are
  the only things that go online ([docs/fission180/privacy.md](docs/fission180/privacy.md)).

### Known problems

The list is in [docs/fission180/known-issues.md](docs/fission180/known-issues.md). The ones to know
before you start: Windows will show "Windows protected your PC" for the unsigned installer
(the exact clicks are in the release notes and in the README); Press Pull is still work in
progress on complex curved shapes; Fission 180 has no macOS version and is English only.
