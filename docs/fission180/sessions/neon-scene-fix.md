# Neon Lights fix round: the rest of the 3D view (`scene-fix`, 2026-11-20)

Branch `sf/neon-scene-fix` (from `sf/neon-integration` aad96d3b). Fixes the six problems the
independent reviewer found in B7 (`scene`), each proved by a test.

## In plain words (for Luca)

- When you switch look or preset, **everything already drawn in the 3D view now changes at
  once**: an open command's arrows and previews, the orbit-centre dot and the dashed hidden
  edges. Before, they kept the old colours until they were drawn again, and the orbit dot and
  the hidden edges could even end up neon in the little preview picture saved inside a design.
  Going back to Dark puts every one of them back exactly (checked pixel by pixel on screen).
- Saving is safer: if the part that normally takes the neon look off for the saved preview
  breaks, Fission 180 still saves a normal preview and turns neon back on afterwards.
- A colour you set yourself for selection or hover is no longer overwritten when you switch
  between Dark and Light (only switching Neon Lights on or off touches those).
- A few more things you see while modelling take the neon colours: Hole's disc while dragged,
  labels in the view, the faces picked by the mesh brush, the mesh cut line and Insert's
  calibrate line. Colours that mean something (simulation, analysis, toolpaths, section caps,
  component colours, centre of mass) stay as they are.

## What was done, problem by problem

1. **Scene parts already drawn keep the old look.**
   - `neon_scene.sweep(target)` / `repaint()`: walks every 3D view's top nodes that are not a
     view provider's (commands' arrows and previews, grid, orbit dot, display_ui's nodes) and
     maps each `SoMaterial` diffuse/emissive/ambient/specular and `SoBaseColor` colour from the
     look it was drawn in to the look in use (`neon_scene_core.colour_map`). It walks node kits
     through their catalog (a dragger's arrow lives in a kit; Coin's search actions stop at a
     kit and pivy's `getTail()` then returns the kit itself). In FreeCAD's `EditingRoot` (an
     open sketch's nodes) only Fission 180's own `Fission180*` nodes are touched.
   - Exact way back: every `Live` now has a code (its index) written about 1e-6 into its red
     channel in Neon Lights (`neon_scene_core.coded`, invisible on screen), so every neon colour
     traces back to one constant and its exact Dark value, even where roles share a neon
     colour (marker/rail/sketch_free are all "primary"). The map also follows the ways shapes
     are drawn from a constant: `handle_look_core.shaded`, `hot_colour`'s lightening and the
     `[c * k for c in COLOUR]` glows (k = 0.35 ... 0.75).
   - From Dark into neon two constants with one Dark value but different roles give the
     colour most constants share (documented in `colour_map`); never the other way.
   - `refresh`, `enable`, `theme_changed` (after leaving), `_before_save` and the after-save
     redraw all call `repaint()`; `disable` sweeps back to the normal colours. `repaint()` also
     redraws the hidden edges (`display_ui.recolour`, the material is now named
     `Fission180HiddenEdgeColour`) and the orbit dot (`orbit_ui.recolour`).
   - `handle_look.Paint` / `DiscPaint` keep the colour constant they were given (they kept
     `tuple(colour)`, frozen in the look of the moment: a hover after a switch put the old
     colour back).
   - `sketch_axes.shown()` compared FreeCAD's axis colour with a `Live` that reads neon, so in
     Neon Lights it always took FreeCAD's red/green instead of the origin hues; it compares
     with the Dark value now.
2. **Loose tests**: scenario `neon_scene` rewritten (71 checks). Extrude's own arrow is read
   from `ExtrudePanel.last.dragger.paints[0].material` and **on screen** (its pixels are found
   by painting its material magenta for one frame and comparing; removing a dragger from the
   scene crashed Coin). Extrude stays open while Dark -> V -> Johnny -> Dark: the arrow's hue
   follows, a repainted arrow looks like a new one, and in Dark its pixels and material are
   exactly the first ones. The orbit dot and the hidden edges are found by grabbing the view
   without their node: neon colour in V and Johnny, exact in Dark. Sketch curves are checked on
   screen (near the edge's middle: neon colour in V, Dark colour in Dark). Previews are saved
   with Extrude open and with a sketch open for editing.
3. **Save hooks**: `_before_save` schedules `_fallback` (0 ms, re-armed every 50 ms while a save
   is still going, at most 40 times); it acts only if `_after_save` never ran: turns
   `theme.normal_look` off (unless neon_view is inside its own `normal_look()`), repaints neon.
   And a document observer of neon_scene's own does the save's normal look (`normal_look`,
   FreeCAD's `BackgroundColor` setting, the hooks) when neon_view is off (e.g. failed at
   enable). Tests: a save with neon_scene's after-hook removed, and one with neon_view
   disabled: both previews equal Dark's and neon comes back.
4. **Dark <-> Light**: `sketch_mode.theme_changed` writes the neon names that LIGHT does not
   have (`SelectionColor`, `HighlightColor`, `EditedEdgeColor`...) only while Neon Lights is on
   or right after it was (`_state["neon_written"]`). Test: a person's own `SelectionColor`
   survives Dark -> Light -> Dark.
5. **`Live`**: kept (switching ~90 use sites to `theme.neon3d` was a bigger risk), with the
   operations documented in the class and pinned by `test_neon_scene_core.LiveOperations`.
   Note: **json and numpy read the look in use** (they iterate), not the Dark value as the review
   said (checked in FreeCAD's Python 3.11 and 3.13); `%`, `==`, `hash`, `repr`, `len`, `in`,
   `copy` and `pickle` read the stored Dark value. `c + t` and `t + c` now read the look in use
   (overridden). Rule in the doc: whatever is saved takes `normal()`. I checked that no `Live`
   is written into a property or json today (`sketch3d.BLUE` and `text_ui` already avoid it).
6. **Inline literal colours**: the search found far fewer than ~50 (most 3D colours were
   already constants). Swept, Dark values exact: `hole_ui` (disc while dragged, `arrow_hot`),
   `handles3d.TEXT` (`bright`), `mesh_pick_ui` picked faces (`cut`, `cut_glow`),
   `mesh_cut_ui.CUT_LOOK` (`pick`) and its cut line (`alert`), `insert_ui.GUIDE` (Calibrate's
   line, `hot`). Kept on purpose: `com_ui` (Fusion's black/white centre-of-mass sign),
   `section_ui` caps, `component_colors_ui`, `display_ui` ground plane and shadow (part of an
   Environment), fallbacks (`origin_look` defaults, `sketch_right_angles`, `live_shapes.colors`
   defaults), simulation / analysis / manufacture / plastic colours (legends).

FreeCAD's parameter map check (commit aad96d3b): of the neon sketch table only
`SketchFaceColor`, `SketchEdgeColor` and `SketchVertexColor` are copied into saved properties
(`ViewProviderSketch.cpp` parameter map); the table changes none of them.
`SelectionColor`/`HighlightColor` are read by `ViewProviderBuilder`/`ViewProviderAnnotation`
into node fields only (display), TechDraw's are in its own groups.

## Not done / found, for the orchestrator

- **neon_view (B6, bodies fix) leak, not fixed here (not my file):** `apply_document` on a
  PartDesign Body searches the body's whole subtree for "Edge" groups, so a sketch inside a
  body gets the neon outline and glow (against `_wants_outline`'s "not a sketch"). While that
  sketch is being edited, FreeCAD moves its nodes into the viewer's `EditingRoot`, so
  `remove_document` does not find them and **the saved preview shows a red glow round the
  sketch**. Seen in `neon_scene` with a body sketch open for editing during a save; the
  scenario now edits a sketch outside the body. Fix belongs in `neon_view._groups` (skip
  sketch view providers / search `EditingRoot` too).
- **Open-sketch preview:** saved in Neon Lights with a sketch open, the preview has no neon
  colour and FreeCAD's sketch colour settings are Dark's while it is drawn (both checked), but
  about 2% of its pixels, inside the open sketch (its shade and corner points), come out a
  little darker than in the Dark one. Not traced further; the scenario checks the two facts
  above for that save instead of a pixel comparison.
- **Pre-existing, every look:** opening and closing an Extrude changes later saved previews
  (about 1.6% of pixels: how the grid's axes and lines at height 0 show against the pad's
  bottom edge and a profile's shade; measured in Dark with no look change). So each neon
  preview is compared with a Dark one saved at the same point (with Extrude open).
- The scene builder's note "Editing a sketch after a save changes the grid in the next
  preview" is most likely this same depth effect.

## Facts found (FreeCAD / Coin / pivy)

- pivy `SoNode == SoNode` compares the C++ pointers; `int(node.this)` is a usable id.
- `SoSearchAction` with `SoBaseKit.setSearchingChildren(True)` returns paths whose `getTail()`
  is the kit (pivy has no `SoFullPath`); walk a kit with `getNodekitCatalog()` + `getPart(name,
  False)` instead.
- Removing a dragger's root from the scene graph and drawing crashed FreeCAD (segfault): Coin
  keeps paths to draggers. Change a material for a frame instead.
- `json.dumps` and `numpy.array` of a tuple subclass iterate it (they see an overridden
  `__iter__`); `%` formatting reads the stored items.
- `View3DInventorViewer.savePicture` (the preview) uses FreeCAD's `BackgroundColor` setting:
  a save's normal look must set it (neon_view does; neon_scene's own observer now too).
- The sketcher's colour parameters redraw an open sketch at once
  (`EditModeCoinManager::ParameterObserver::OnChange` -> `redrawViewProvider`).

## Guards (final run)

- `run_tests.sh --only unit` (with FreeCAD, incl. `test_theme_identity`'s FreeCAD part):
  4124 tests OK. `look_unchanged` (13), `neon_switch` (27), `neon_outlines` (14) and
  `neon_scene` (71 checks): PASS.

## Screenshots (docs/fission180/images/neon/)

- `scene-fix-v-extrude.png`: V, Extrude opened in Neon Lights: neon arrow, dashed hidden edges,
  orbit dot.
- `scene-fix-johnny-extrude.png`: Johnny, the same Extrude left open through Dark -> V -> Johnny:
  its arrow, the dot and the hidden edges follow.
- `scene-fix-v-sketch.png`: V, a sketch open for editing (the save with a sketch open).

## Files

Changed: `neon_scene.py`, `neon_scene_core.py`, `display_ui.py`, `orbit_ui.py`,
`handle_look.py`, `sketch_mode.py`, `sketch_axes.py`, `hole_ui.py`, `handles3d.py`,
`mesh_pick_ui.py`, `mesh_cut_ui.py`, `insert_ui.py`; tests `test_neon_scene_core.py`,
`gui/scenarios/neon_scene.py`. Shared or other builders' files: none (`neon_view.py` untouched;
the test adds a hook to its `save_hooks` list for one save and removes it).
