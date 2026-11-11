<!-- A copy of docs/fission180/parity/appearance.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Parity spec: appearances, physical materials, Properties, the selection read-out

Wave 7 (2026-11-11, branch `sf/book-looks`), from the book parity report
(`docs/fission180/dev/research/book-parity-report.txt`: bugs 16 and 17, "Appearances and
materials", and the projects' appearance steps). The older first pass of Appearance and
Physical Material is in `parity/bodies.md`; where the two differ, this page is the newer one.

Sources are marked **Autodesk** (help.autodesk.com / autodesk.com pages, read through search
excerpts: the sandbox cannot open them), **Forum** (Autodesk Community), **Book** (the report
quoting *Mastering Autodesk Fusion*, 2nd ed.) or **Guess** (from memory of the program, not
confirmed).

Code (all in `src/Mod/Fission180/fission180/`):

| File | What |
|---|---|
| `appearance.py` | the stored looks (a JSON property of each body), the design's own looks, favourites, putting them on screen |
| `appearance_library.py` | the library: 200 looks in 12 categories, search |
| `appearance_textures.py` | 18 patterns computed by arithmetic (no image file) |
| `appearance_mapping.py` | where a pattern lands on a body (Texture Map Controls' arithmetic) |
| `appearance_draw.py` | a pattern in the 3D view (Coin) |
| `appearance_ui.py` | the Appearance dialog; the watch that keeps looks on screen |
| `appearance_edit_ui.py` | the look editor |
| `appearance_map_ui.py` | Texture Map Controls |
| `material.py`, `material_ui.py`, `materials_ui.py` | physical materials, the Physical Material dialog, Manage Materials |
| `properties_core.py`, `properties_ui.py` | Properties |
| `properties_readout_ui.py` | the selection read-out |
| `opacity.py`, `component_colors_ui.py` | Opacity Control; Display Component Colors and the Component Color Swatch |

## Behaviour spec

| # | Fusion | Source | Fission 180 |
|---|---|---|---|
| 1 | Appearance (A): Apply To Bodies/Components or Faces; drag an appearance and drop it on a component, body or face in the browser or the canvas | **Autodesk** "Apply appearances to components, bodies, and faces in a design" | The same dialog. Drop on the canvas or on a row of the browser (a body's row; a component's row gives the look to every body in it), or click a look then click bodies / faces. A drop on a component in the canvas goes to the body under the pointer. |
| 2 | A face's appearance wins over its body's, a body's over its component's | **Forum** "How to change appearanceSourceType of a face?" (API answer) | A face's look is drawn over the body's look; a body's Appearance over its material's look; a body with neither shows the design's default look. |
| 3 | An appearance given to a body or component that has appearances on faces: a question, Keep (the faces keep theirs) / Remove (the whole body takes the new one) / Cancel | **Autodesk** Render activity "Apply materials" and the help page above (the parent-component case) | The same question (own wording): Keep / Remove / Cancel, as **a row of the Appearance dialog** (Fusion shows a box; here nothing modal: a script, a remote hand or the AI is never frozen by it). One drop asks once, also for a component's row with several bodies; OK waits for the answer; nothing changes before it. The AI tool `appearance` says it in the call (`keep_face_looks`). The report said "Fusion keeps face looks under a body look": it does when the person answers Keep; it asks. Before, a body look silently removed every face look. |
| 4 | With Apply To Faces only faces can be hit | **Guess** (Fusion's selection filter) | A drop or click that lands on an edge or corner takes the face next to the pointer (the pixels round it are looked at, nearest first, on the same body); with no face there it says so and changes nothing. It never colours the body (bug 17). |
| 5 | Removing an override: "Remove Appearance Override" on the body or face | **Forum** / **Autodesk** Configurations page (search excerpts) | The dialog's Remove button: a click then takes a face's own look away (the body's shows), or with Apply To Bodies the body's Appearance (its material's look shows). Not in the browser's right-click menu. |
| 6 | "In This Design" lists the design's appearances from the start (the default material's, Steel - Satin) | **Book** (Classic Donut) | It starts with "Steel, satin (default)": the look every body shows until it is given one, and **exactly the library's Steel, satin**: a new body is drawn in it (FreeCAD's part colour preferences are set to the look at start: `appearance.use_default_look`; until 2026-11-11 a new body was FreeCAD's lighter grey and the swatch showed that grey). Bodies of older designs saved in that grey take the default look on opening (`adopt_default`); a body with a look is never touched; the theme (dark / light) changes nothing of it. Editing the default look changes every body still on it, and bodies made later. |
| 7 | Double-click an appearance under In This Design (or right-click > Edit): a small editor with the colour (sliders or RGB), the texture's Scale and Rotation; Advanced opens the material editor (reflectance, roughness, relief pattern (bump), cut-outs...) | **Autodesk** blog "Making it look good: apply and edit materials", help "Edit appearances using the Material Editor" | The look editor: Name, a colour wheel + Brightness + R G B + #RRGGBB, Pattern, Scale %, Rotation, and Advanced: Shine, See-through, Glow. Relief pattern, roughness map and cut-outs are listed greyed with the reason (only a renderer shows them). Every change shows at once on everything that has the look. |
| 8 | Right-click an appearance: Edit, Duplicate, Delete, Select Objects Applied To, Add to Favorites ... | **Autodesk** (Duplicate: "right-click the appearance you want to duplicate"), the rest **Guess** | Edit, Duplicate, Rename (the editor on the name), Delete, Select Objects Applied To, Add to Favorites. Delete takes the look off what has it; refused for the default look and for a look bodies get from their physical material (it says why). |
| 9 | The libraries are read-only; an edited appearance lives in the design; favourites and "My Appearances" are the user's | **Autodesk** "Manage materials in a design" (search excerpt) | Library looks are never changed. A library look dropped into a design that holds an edited look of the same origin comes in beside it as "Name (1)". Add to Favorites of an edited look keeps it under My Appearances. |
| 10 | A search box over the library | **Book** ("Search Anodized") | A search box (every word typed must be in the name or the category) and a category list: All, Favorites, My Appearances and the 12 categories. The list shows the names. |
| 11 | Categories such as Metal, Paint, Wood, Fabric, Glass, Plastic... | **Autodesk** blog / tutorials (Metal, Paint, Wood, Fabric, Glass confirmed) | Metal, Plastic, Wood, Paint, Glass, Leather and Cloth, Rubber, Ceramic, Carbon Fibre, Stone, Emissive, Other. Generic material names; none of Autodesk's own wording where it is distinctive. |
| 12 | Textured appearances (wood, leather, brushed metal, carbon fibre, mesh with cut-outs) | **Book** | 18 patterns: wood grain (4), leather (2), cloth, brushed (2), carbon weave (2), mesh (2), knurled, foam beads, mottled, speckled, metallic flake. The 3D view shows a pattern's light and dark over the look's colour. It shows no relief, no roughness map, no reflection of surroundings, and a mesh's holes are drawn dark, not open: those belong to rendering (out of scope). |
| 13 | Texture Map Controls: pick a body, a projection (Automatic, Box, Cylindrical, Planar, Spherical; 3D Texture for solid woods), an Axis (not for Automatic and Box), and drag handles that move, turn and size the map | **Autodesk** "Adjust texture mapping" | MODIFY > Texture Map Controls: Body, Projection (the five; no 3D Texture), Axis, Offset U / V, Rotation, Scale, Reset. No drag handles: the numbers are typed. The map belongs to the body (all its textured looks). |
| 14 | Physical Material: drag a material onto a body or component (canvas or browser); libraries read-only; a material is edited as a copy (Favorites) | **Autodesk** "Manage materials in a design" (search excerpt), **Forum** "Autodesk Physical Materials Locked?" | Click a material then bodies, or drag it onto a body in the 3D view or onto a body's / component's row of the browser. Double-click (or right-click > Edit a Copy) a material: a copy with its own name and density under My Materials. Only the density of the copy can be set; its other values are those of the material it copies. |
| 15 | A physical material brings its appearance unless the body has one of its own | **Guess** (everyday use), **Book** | The same: `material.assign` stores the material's look under the body's Appearance. |
| 16 | Properties (right-click a component or body): Area, Density, Mass, Volume, Physical Material and more (centre of mass, moments of inertia) | **Forum** / third-party tips (search excerpts): Mass, Area, Volume, Physical Material, centre of mass, moments of inertia. Bounding Box and Copy to Clipboard: **Guess**. A component's Properties carries its part number (**Autodesk** "Properties", ASM-PROPERTIES: right-click a component > Properties, shared part numbers; the API's `Component.partNumber`, `.name`, `.description`); the three labels: **Guess** | **General**: Part Number, Part Name, Description of the one component selected, typed in the dialog (Enter), stored on the component (an occurrence: on its original), one undo step each; the Part Number starts as the name; the drawing's parts list shows the Part Number and the Description (`drawing._part_name`, `Label2`: the properties the parts list read already). Then Area, Density, Mass, Volume, Physical Material, Appearance; Bounding Box (Length X, Width Y, Height Z); Center of Mass; Moment of Inertia at Center of Mass and at Origin; Copy to Clipboard (the General lines too). It follows the selection; nothing selected: the whole design (its name shown, greyed). |
| 17 | A selected face shows its area (and loop length) at the bottom right, an edge its length, two things their distance and angle | **Forum** "default measurement info in the bottom right corner", **Autodesk** "Measure reference", **Book** | The read-out in the strip under the 3D view, at the right: Area + Loop Length, Length (+ Radius), Position, Volume + Area for a body, Distance (+ Angle when not parallel) for two. |
| 18 | Display Component Colors (INSPECT, Shift+N): each component in its own colour; Component Color Swatch (timeline Settings): the swatches in the Browser and Timeline even when the canvas colours are off | **Autodesk** "Color code components and features" | Display Component Colors was there. Component Color Swatch is in the timeline's Settings menu (the gear) and under INSPECT: it marks each component's colour **on its browser row** (a small square before the activate ring; the design's row too) **and on its timeline steps** (a bar along the step's foot; a joint: both components' colours side by side), whether the canvas colours are on or not (off by default: **Guess**). **Cycle Component Color** (right-click a component, while colours show in the canvas or as marks: **Forum**, an Autodesk reply) gives it the next colour no other component has; stored in the design, one undo step. `browser_ui.ROW_COLORS` and `timeline_ui.STEP_COLORS` are the hooks `component_colors_ui` registers in. The report looked for a gear "at the bottom right": that is the timeline's Settings. |

## Why looks were lost (bug 16) and how they are kept

Found with FreeCAD 1.1.4 (probe scenarios, 2026-11-11):

- Whenever a body's `ShapeMaterial` is **written** (even with the value it has), and whenever a
  physical value of it is only **read** through Python (`body.ShapeMaterial.getPhysicalValue(...)`,
  `hasPhysicalProperty(...)`), FreeCAD writes the material's colour (grey) on the body's view,
  and the body's view copies it to **every step** of the body. A step's own `ShapeMaterial`
  does not do this; `.Name` and `.UUID` are safe to read.
- FreeCAD only does it while its view's own memory of "the material's appearance" is still
  the default one or equal to what is drawn, so it happens on the first material write after
  a design is opened, and at other moments that looked random to a person (the report saw it
  "after Isolate / Exit Isolate + Move"; none of those alone does it: 23 single operations
  were tried).
- `appearance.apply()` used to remember, per step, what it had applied (the solid's hash, the
  look's text, the number of colours) and skipped a step whose record matched, so the grey
  stayed and dropping the same look again did nothing.

Now the stored look is the only truth: `apply()` compares the colours FreeCAD draws from with
the stored looks every time (only the matching of faces to their looks is remembered), after
every recompute, undo and redo as before; `appearance_ui`'s watch calls it as soon as a
body's material was touched (FreeCAD tells the design's observers of the read too) and when
a step comes into view; a look dropped on something that has it is written again.

The watch is on the design side only. A Python observer of the views
(`Gui.addDocumentObserver` with `slotChangedObject`) was tried and must not be used: FreeCAD
1.1 then builds a view's Python object while the view is still being constructed, the object
stays one of the base type for good (`Gui.ViewProviderGeometryObject`), and every step made
afterwards has lost PartDesign's `makeTemporaryVisible` (Scale, Fillet... fail with "object
has no attribute 'makeTemporaryVisible'"); reading such a view's `Object` crashes FreeCAD.

## How a pattern is drawn

FreeCAD's face drawing (`SoBrepFaceSet`) sends no texture coordinates: a texture put before it
shows as one flat tint. So a pattern is a second, plain face set on the very same triangles
(read from the step's own display), a hair in front, unlit, never picked: black or white with
the pattern's strength as alpha. The face below keeps its colour, its light and the highlight
of a hovered or selected face, which show through. The node sits inside the step's display, so
it follows the step's eye, place, display mode (it is off under an analysis or component
colours, which switch the faces off) and the copies of its component. It is as see-through as
the body (Opacity Control). It is rebuilt when the step's solid changes and is not saved in
the file (drawn again when a design opens).

## Physical materials

FreeCAD's library has cards with a density for steels, aluminium, copper, titanium and the
common plastics. It has only colour cards (no density) called Brass, Gold, Bronze, Silver,
Chrome... `material.OWN` states the values of those and of the others the book needs (Brass
8.5 g/cm3, Gold 19.32, Carbon Fibre 1.6, anodized aluminium 2.7, Oak 0.75...: typical handbook
values); each is made in FreeCAD's User material library (folder `Fission180Library`) the first
time a body is made of it, because a design stores only a material's id. A design opened on a
computer where one is missing gets it made again.

## Missing / not built

- "Remove Appearance Override" in the browser's menu (the dialog's Remove button does it).
- Texture Map Controls' drag handles in the 3D view (the numbers are typed); the "3D Texture"
  projection.
- Relief (bump), roughness maps, cut-outs, image files as textures, reflections: rendering.
- The look editor cannot load a picture as a pattern (the patterns are the built-in ones).
- Editing a material of your own in place (make another copy), and values other than the
  density on a copy. (Manage Materials > New Appearance picks its colour on the look
  editor's colour wheel with a brightness slider since 2026-11-11; a code can still be
  typed.)
- (Built 2026-11-11, library-2: the swatch marks in the browser and the timeline, Cycle
  Component Color, Part Number / Part Name / Description, the default look on new bodies.)
- Cycle Component Color for the design's own row (the top component keeps the first colour).
- "Properties" in the right-click menu of a **body** needs one line in the browser's menu
  list (`browser_core.MENUS["body"]`); the component's entry is there (components work).
  Until then: select the body, INSPECT > Properties.
