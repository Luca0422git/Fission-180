<!-- A copy of docs/fission180/known-issues.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Known issues in Fission 180 0.1.0-beta.4

This is a beta: it works, but it is not finished. These are the things you are most likely to
run into, each with what you can do about it. The list is kept short on purpose and is updated
with every release (see [CHANGELOG.md](../../CHANGELOG.md)). Not on the list? Please report it:
**Help > Report a Problem** in Fission 180, or the
[Issues page](https://github.com/Luca0422git/Fission-180/issues).

**Save often.** If Fission 180 closes unexpectedly, Home offers to bring back unsaved work the next
time you start it, but treat that as a safety net, not a plan.

## Things that look or feel unfinished

- **Press Pull is work in progress on complex shapes.** On planes and cylinders it is solid. On
  curved or freeform faces, or with many faces picked at once, it can be slow and the result can
  look odd. Fission 180 says so in a small yellow warning on the Press Pull button and in its
  dialog. *Workaround:* use Fillet, Chamfer, Offset Face or Extrude for those faces, or press
  Undo (Ctrl+Z) when a result looks wrong.
- **English only.** Fission 180's own screens, menus and messages are in English; there are no
  translations yet.
- **The SHEET METAL and PLASTIC tabs** are still the least used so far. A few of Fusion's options
  are not there yet (for example weld corner reliefs, and a flat pattern for a Brake Form
  lofted flange), and Design Advice is slow on big parts. The details are in
  [parity/sheet-metal.md](parity/sheet-metal.md) and [parity/plastic.md](parity/plastic.md).
- **Simulation has Fusion's Static Stress study only**, one set of loads per study (make a
  second study for another load case), and bodies that touch are glued together (no sliding or
  separating contacts). Its numbers are checked against hand calculations, but they are only as
  good as the setup and the mesh: thin walls at the default mesh come out a little too stiff,
  and Fission 180 then says so in a note (a finer mesh in Study Settings fixes it). A very fine
  mesh (over about 150,000 nodes) takes minutes and a lot of memory; the solve's message warns
  first. While a big study is handed to the solver and its results are read back, the window
  can stop answering for about 3 seconds; the solve itself runs in the background.
  *Workaround:* start coarse, then refine where the colours change most (Local Mesh Control)
  and compare.
- **The ANIMATION workspace is new in this beta.** It moves components only (a design of plain
  bodies has nothing to animate), and a component hidden in Design stays hidden in every
  storyboard. Publish Video writes AVI (plays in VLC and Windows' players): MP4 stays greyed
  until the free ffmpeg program is installed (the entry's tip says where to get it).
  *Workaround:* in Design, right-click the bodies > Create Components from Bodies, and show
  what should be seen; use AVI or PNG pictures, or install ffmpeg.
- **The MANUFACTURE workspace is new in this beta** and mills only. With holding tabs, 2D
  Contour has no lead-in or lead-out; "In control" compensation (G41 / G42) is not offered;
  Stock From preceding setup is the whole block (safe, a little slower); 3D Adaptive Clearing
  uses a FreeCAD feature FreeCAD itself calls experimental. *Workaround:* cut the tabs' contour
  as a second operation without tabs; simulate 3D Adaptive before running it.
- **Auto Timeline needs an AI** (Fission 180's chat with your own key, or an AI app connected to
  Fission 180), and it reads blocks, plates, turned parts, holes, pockets, bosses, fillets and
  chamfers. Free-form shapes (lofts, sweeps, sculpted surfaces) and threads are listed as "not
  read" for you or the AI to build by hand, and a mesh over 10,000 triangles is refused.
  *Workaround:* MESH > Reduce, or export the mesh coarser, and build the free-form parts
  yourself; Stop Rebuild (UTILITIES > AI) gives a rebuild up.
- **Big robots open slowly.** A 300-part VEX robot takes about half a minute to open on the
  test machine (it took over two minutes in beta 2). Much of what is left is FreeCAD building
  a small axis marker for every body, which needs a change to the compiled program. On such a
  robot the browser can take a second or so to catch up after Ctrl+Z.
  *Workaround:* none needed; once open, hovering, joints and Drive Joints are quick.
- **Some steps of the book still take a while** (Fusion: seconds). The 25-groove knurl takes
  20 to 50 seconds to build when you press OK, up to a few minutes on a busy computer, with a
  progress window and Cancel; dragging a modeled thread before its chamfer takes 10 to 25
  seconds, with no progress note.
- **Seam lines** show on round faces and where the halves of the Saturn V's thruster cones meet;
  a click on such a line while sketching projects it. *Workaround:* click a little beside it.
- **Construction geometry can be in the way.** A construction plane is drawn as large as its
  whole part, not as its face, and a few tools (Joint, Project to Surface) still take the first
  thing under the pointer. After a saved design is opened, a coil's small section triangle can
  show again. *Workaround:* hide the planes (the Construction folder's eye) while you click
  behind them; right-click the triangle in the browser > Hide.

## Not built (yet)

- **Not all of Fusion's features.** Fission 180 covers the Design workspace: sketches, solid and
  surface modeling, patterns, components and joints, mesh, drawings, 3D printing, and more;
  the Simulation workspace's Static Stress study; Animation; and Manufacture's milling. It
  does **not** have Render (scenes, environments, rendered pictures), sculpting (T-splines),
  the other simulation studies (thermal, vibration modes, buckling, nonlinear, event, shape
  optimization), turning, multi-axis or additive CAM, thread milling, electronics, Generative
  Design, or cloud collaboration. Some options inside the tools that do exist are shown greyed
  out with the reason. For example, the Fillet options Setback corners, Curvature (G2)
  continuity and Asymmetric radius, and the Chamfer corner types Miter and Blend, need work
  that OpenCASCADE (FreeCAD's geometry engine) does not do yet.
- **No `.f3d` files.** Fusion's own file format is closed, so Fission 180 cannot open it. *Workaround:*
  in Fusion, export **STEP** (solid parts) or **3MF / STL** (meshes) and open it from Home (Open...) or
  use INSERT > Insert STEP. You get the shapes, not Fusion's timeline.
- **No macOS version.** Windows 10/11 (64-bit) and Linux (x86-64) only.
- **Cloud accounts.** Fission 180 does not sign in to Dropbox, OneDrive or Google Drive. A "cloud
  place" is the folder your own cloud app keeps in sync. *Workaround:* install the cloud app and
  pick its folder under Home > Connect a cloud or NAS.
- **Components.** External components (a component in a file of its own) and Create Selection
  Set are not built. A part inside a copy of a subassembly cannot be moved or jointed on its
  own, nor a mirrored component edited on its own. *Workaround:* save the part as its own
  design and use INSERT > Insert into Current Design; change the original, and every copy and
  mirror follows. Details: [parity/components.md](parity/components.md).
- **A sketch pattern cannot be edited after OK.** Its copies stay tied to the original, but
  there is no pattern to double-click and change. Copies of splines and ellipses are placed but
  not tied. *Workaround:* undo the pattern, or delete the copies and pattern again.
- **Drawings.** Templates cannot be edited; Hole and Thread notes, weld symbols and revision
  tables are missing; an exploded view shows the end of its storyboard only; a balloon's arrow
  does not follow its part when the design changes. *Workaround:* make a storyboard that ends
  at the stage you want; delete the balloon and place it again.
- **Export DWG needs a converter program** (LibreDWG, the ODA File Converter or QCAD) installed
  on the computer; with one, each sheet is its own DWG. *Workaround:* without one, take the DXF
  the dialog offers: AutoCAD and other DWG programs open it.
- **Fusion's keyboard layout is copied, not all of it.** The cheat sheet lists what works:
  [cheat-sheet.md](cheat-sheet.md).

## Where Fission 180 still works differently from Fusion

- **A few of the book's rounds cannot be built**: where a tube leaves a round housing almost
  tangent (the Tesla Turbine's inlet; it sometimes builds after the design is reopened), and a
  small round on a face that ends at modeled threads (the Pizza Cutter's Wheel Bracket), on the
  edges the threads run out through. *Workaround:* move the tube a little or try a smaller
  round; leave the edges next to the threads out, or make the round before the threads.
- **A modeled thread has one face per turn** on each flank (Fusion has one face for the whole
  flank), so picking "the thread" face by face takes many clicks. *Workaround:* Offset Face and
  Press Pull take the whole thread with one click.
- **Symmetric patterns count differently.** A sketch pattern's Quantity is all the instances (5
  gives 5, as in the book); a pattern of features, bodies or components counts each side (3
  gives 5; Fusion's rule there is not documented). *Workaround:* for 5 in all, type 3.
- **Two sketch preferences are on although Fusion's default is not known:** "Auto project edges
  on reference" (a click on a model edge while you draw projects it) and "Scale entire sketch at
  first dimension" (not when the sketch has a spline, a fixed curve or anything projected).
  *Workaround:* switch either off in Preferences > General > Design; tell us Fusion's default.
- **In sketches, Snap moves a click to the nearest grid crossing**, up to half a grid spacing
  away, and deleting one automatically projected edge of a face removes all of them.
  *Workaround:* zoom in (the grid gets finer) or untick Snap; project the edges you want with P.
- **A point clicked on the middle of an arc** (the Carabiner's slot end) is put on the arc but
  not held at its middle. *Workaround:* dimension it (an angle, or a distance to another point).
- **In the Line, Circle and Rectangle tools, a new parameter cannot be made in the value box**
  ("Width=5mm"; a name there must start with "="). Fission 180's own tools (slots, polygons,
  arcs, 2-Point Circle) and Sketch Dimension take it. *Workaround:* make the parameter first,
  or type it into the dimension afterwards.
- **Rectangular Pattern takes its second direction from the Direction 2 box only** (Fusion takes
  two edges in a row). *Workaround:* click the Direction 2 box, then the second edge.
- **Combine leaves the bodies it used up in the browser, hidden** (Fusion removes them).
- **Duplicate With Joints refuses a screw put in by Hardware.** *Workaround:* put the other
  screws in with Hardware too ("All holes like it"), or joint the screw by hand (J) first.
- **A mirrored component is listed as the same part number** as its original in a drawing's
  parts list (Fusion makes the mirrored part a new part number).
- **Revolve, Sweep, Loft, Coil and the primitives** look only at their own body to choose Cut,
  so pushed into another body they stay New Body or Join. A Gear on the Front plane still grows
  towards the front, and so do the AI tools' steps there. *Workaround:* pick Cut in the
  Operation list; type a negative thickness for the Gear.
- **A step made on a body of another component** is listed in that component's timeline, not
  the active one's as in Fusion (a note says so on OK). *Workaround:* activate that component,
  or the design's top row, to see the step.
- **The Move dialog and a pattern of components take a parameter's value once** and do not
  follow it later. *Workaround:* type the parameter again after changing it.
- **Hardware**: a nut or washer cannot be clicked onto a screw, a sketch point is no place for a
  part, and there is no preview under the pointer. *Workaround:* click the face or the round
  edge the part sits on, or press OK without a place and move the part.
- **Appearances are drawn, not rendered**: patterns show light and dark only, wood grain can
  show seams on a free-form face, and Texture Map Controls has no handles in the 3D view.
  *Workaround:* type the offset, rotation and scale (try Cylindrical or Planar against seams).
- **Joint limits' Flip** puts the limits on the other side of the joint's zero; Autodesk's help
  only says it "swaps" them. If Fusion does something else with two limits on, tell us.

## Things to watch out for

- **Check every CNC program before it runs on a machine**: simulate it, read the G-code, and make
  the first run in the air above the part. Fission 180 cannot know your machine, clamps or tool
  lengths, and Simulate checks rapid moves of the cutter only, not the holder or the shaft.
- **Hardware sizes come from the published standards**, and a few families were not checked
  against a second source (ISO 7040 lock nuts, ISO 2338 pins, set screw points, inch low and
  flat head socket screws, jam nuts): check a size on the supplier's sheet before ordering.
- **Designs made before 0.1.0-beta.4** keep what they had: sketches already extruded on the
  Front plane and planes offset from it keep their old side, and older sketches still show
  FreeCAD's helper circles and labels on polygons, splines and ellipses.
- **The command search (S) can run a greyed command without a word** (in Manufacture,
  S > "Study Materials" does nothing). Use the ribbon or the workspace menu.
- **Windows warns about the installer** ("Windows protected your PC") because it is not signed
  with a paid certificate. It is normal; the exact clicks are in
  [smartscreen.md](smartscreen.md).
- **Your antivirus may flag Fission 180 by mistake** (same reason; see the same page).
- **Linux: AI keys are not encrypted** unless your system's key store is available to Fission 180
  (see [privacy.md](privacy.md)). Fission 180 says so next to the key field. Use a key with a
  spending limit you are comfortable with.
- **A design file whose faces were renamed by a big edit.** After a large change to an early step,
  a later step that was attached to a specific face or edge can lose it. Fission 180 says in the
  timeline which step needs its face picked again. It does not mean the file is damaged.
- **Designs in a folder that a backup program syncs (for example Documents with OneDrive or
  Google Drive backup).** Some of these folders refuse FreeCAD's normal way of saving a file.
  Fission 180 works around it by saving directly in those folders. If a save ever seems to do
  nothing, check the folder for a file ending in `.FCStd.` and a long code (a half-finished
  save) and tell us which backup program you use.
- **Sketch Rotate still snaps with Ctrl** the way FreeCAD does; hold Ctrl as you would in
  FreeCAD. Fusion's "Pin to Shortcuts" is not built.
- **Updating by "Update now"** is the part least tested on other people's computers. If an
  update fails, Fission 180 keeps a backup of your previous version
  (see [quick-update.md](quick-update.md)) and the manual way (download the new installer)
  always works.

## Reporting something that is not on this list

Help > Report a Problem puts everything useful (version, Windows or Linux version, graphics card,
recent Fission 180 messages) in one place, with your name and folders removed, and lets you look at
it before anything goes anywhere. More in the [README](../../README.md#reporting-problems-and-ideas).
