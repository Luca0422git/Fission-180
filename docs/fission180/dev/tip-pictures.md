# Tooltip pictures: how to make them (wave 8)

Every ribbon command's expanded tooltip (fission180/tips_ui.py) shows a 320 x 200 picture from
`src/Mod/Fission180/fission180/icons/tips/`. The pictures are made by scripts in the real Fission
180, never by hand, and the PNGs are committed (a build does not make them).

- Data: `fission180/tips/<module>.py`, `TIPS = {"<command id>": {"summary", "what", "steps",
  "tips", "picture"}}` (the rules are at the top of `fission180/tips/__init__.py`).
- Script: `tools/fission180/tip_pictures_<module>.py`, one per data module, using the helpers
  of `tools/fission180/tip_pictures.py`.
- Run: `tools/fission180/make_tip_pictures.sh <module> [picture ...]` (a few pictures by name
  while you work on them: `make_tip_pictures.sh solid fillet chamfer`). It starts Fission 180
  on a virtual screen (Xvfb, the sandbox FreeCAD of the main checkout; `--freecad DIR` for
  another), makes each picture, writes the PNGs and
  `.fission180-cache/tip-pictures/<module>-report.json` (and the FreeCAD log beside it), and
  quits. A picture that fails is reported; the others are still made. About 2 s a picture.
- Check: `python3 -m unittest Fission180Tests.unit.test_tips.Coverage.test_module_<module>`
  (from `src/Mod/Fission180`): every command of the module's tabs has a complete entry and a
  picture of the right size. **Look at every picture** before you commit it (open the PNG).

## Look

One style for all: Fission 180's dark 3D view (#2a2a2a) behind, bodies in their normal grey
with their black edges, what the tool works on or makes in the **selection blue** (faces
#3b5bdb, edges a lighter blue, 4 px), an arrow in the accent blue between "Before" and "After".
The standard camera is Fission 180's Home view (isometric: top, front and right). Renders are
made about 3 times larger than the picture and scaled down (anti-aliased) and framed on what
they show, so a small demo part fills the picture; the before and after of one picture share
one scale, so a part that grows looks larger after.

Demo models small and clear: a block with an edge to fillet, a plate for a hole, two parts for
a joint. A picture that does not show what the tool does is worse than a picture of its dialog:
for settings, export, file and inspection tools grab the dialog (`dialog_picture`), or show the
model with the dialog beside it (`with_dialog`).

## A worked example: Fillet

```python
# tools/fission180/tip_pictures_solid.py
import tip_pictures as tp


@tp.picture("fillet.png")
def fillet():
    tp.new_design()                                # File > New Design, layout grid off
    box = tp.box(40, 30, 16)                       # a PartDesign box in Body1
    edge = tp.edge_at(box, (20, 30, 16))           # the top back edge, by a point near it
    tp.camera()                                    # the Home view, fitted; once per picture
    before = tp.render(highlight={box: [edge]})    # the edge drawn in the selection blue
    tip = tp.fillet(box, [edge], 6)                # the same feature Fission 180's Fillet makes
    after = tp.render(highlight={tip: tp.new_faces(box, tip)})   # the round face in blue
    return tp.before_after(before, after)          # side by side, an arrow between
```

`tools/fission180/make_tip_pictures.sh solid fillet` writes `fission180/icons/tips/fillet.png`
(about 10 KB) and the data entry names it: `"picture": "fillet.png"`.

## The helpers (`import tip_pictures as tp`)

Each picture is a function decorated with `@tp.picture("<name>.png")` that returns a Pillow
image of 320 x 200 (or a `Shot`, framed as the whole picture). The runner closes every design
and dialog before each one.

Designs and models
- `new_design(name)`: a new design as File > New Design makes it (Body1, the Home view).
- `box(l, w, h, at=(x, y, z))`, `cylinder(r, h, at)`: PartDesign primitives in the active body.
- `sketch(plane="XY", offset=0)`, `line(sk, a, b)`, `rect(sk, x0, y0, x1, y1)`,
  `circle(sk, cx, cy, r)`, `pad(sk, length)`: a sketch and its extrusion.
- `fillet(base, edges, r)`, `chamfer(base, edges, size)`: PartDesign dress-up features.
- `ai("<tool>", **args)`: any of Fission 180's AI tools on the active design, exactly as an AI
  app runs it through the bridge (the same code as the ribbon command's dialog): `tp.ai("hole",
  ...)`. Raises when the tool answers an error. The tools' arguments: `docs/ai/tools.md`.
- `run_command("Fission180_Fillet")`: a ribbon command as its button runs it.
- `hide(*objs)`, `show(*objs)`, `recompute()`, `settle()`, `wait(ms)`,
  `wait_for(condition, what)`; `doc()`, `body()`, `view()`.

Picking faces and edges (names like "Face3", "Edge7" of an object's Shape)
- `edge_at(obj, point)`, `face_at(obj, point)`: the one nearest a point (mm).
- `faces_facing(obj, direction)`: plane faces whose normal points that way.
- `new_faces(before, after)`: faces on surfaces `before` did not have (a fillet's round face,
  a hole's wall). `changed_faces(before, after)`: every face that is not exactly as before
  (also the ones only trimmed).

Camera and renders
- `camera(direction="iso", zoom=1.0)`: the Home view (or "top", "front", "right", ..., or a
  (x, y, z) direction looked along), fitted to what is shown, then zoomed. Call it once per
  picture, before the first render, while the scene shows its largest state if the parts
  change size a lot (or frame them yourself with `zoom`).
- `render(highlight={obj: [names]}, line_width=None, hide_origin=True)`: a `Shot` of the 3D
  view. Faces in the highlight are drawn in the selection blue over the model, edges as thick
  blue lines on top (pick edges the camera sees). The selection and hover are cleared and the
  origin hidden first.
- `finish(shot)`: one render as the whole picture.
- `before_after(before, after, labels=("Before", "After"))`: two renders at one scale with an
  arrow (labels=None for none).
- `side_by_side([shots], labels)`: two or three renders at one scale, no arrows (the options of
  one tool: Join / Cut / New Body).
- `text(image, xy, words)`, `arrow(image, x0, x1, y)`: small additions (keep words few: the
  tooltip has the text).

Dialogs
- `wait_for_panel()`: once a command's dialog is open, its widget (FreeCAD's task panel with
  its title and OK / Cancel); `task_panel()` returns it or None.
- `grab(widget)`: a widget as drawn now, as a Pillow image.
- `grab_modal(open_it)`: for a command that opens a modal window (Export, Preferences):
  runs `open_it()`, grabs the window once shown, closes it.
- `dialog_picture(image, area=None, scale=None)`: a grab as the picture: `area` (x, y, w, h)
  cut out first, scaled to fit (never enlarged; a tall dialog keeps its width and fades out at
  the bottom), on the view's dark grey.
- `with_dialog(shot, dialog_image)`: the model with the top of the dialog beside it.

Saving
- `save(image, name)` / `encode(image)`: what the runner does with the returned image: PNG,
  optimised, reduced to 256 (or fewer) colours only when that is what keeps it under 45 KB.

## Traps

- saveImage never draws FreeCAD's selection (it tints a selected body instead): the helpers
  clear the selection and draw their own highlight.
- A body passes its LineWidth on to its features: read every width before setting any (the
  helpers do; a script that changes widths itself must too).
- A file given to Fission 180 on its command line runs as a module named after the file,
  not `__main__` (the runner imports `tip_pictures` itself, so scripts and runner share it).
- Thick edge lines drawn by Coin lose half their width to the faces beside them; the helpers
  draw highlighted edges on the picture instead, from the camera's own projection.
