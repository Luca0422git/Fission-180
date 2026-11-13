You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: DRAWINGS for the AI (builder ai-drawing, branch `sf/ai-drawing`)

The AI has six drawing tools (`create_drawing`, `add_drawing_view` kinds base / projected /
section / detail, `add_drawing_dimension` types linear / aligned / radius / diameter / angular,
`add_drawing_annotation` kinds text / parts_list / center_marks, `export_drawing` pdf / dxf,
`get_drawing`). The DRAWING tab (`ribbon_config.DRAWING_*`) has much more. Without a tool
(2026-11-13 audit by name; check each): Break View, Breakout Section View, Exploded View (from an
animation storyboard), Edit View, Title Block, Rotate (a view), Centerline, Center Mark Pattern,
Edge Extension, Arc Length / Ordinate / Baseline / Chain Dimension, Edit Dimension, Leader, Bend
Note, Surface Texture, Feature Control Frame, Datum Identifier, Bend Table, Balloon, Renumber,
Align Balloons, Export DWG, Export CSV (the parts list), and the sheet commands (new sheet,
sheet size / scale) if the ribbon or the browser has them.

### What to build
Every drawing command reachable by a tool (or a `kind` of an existing one, keeping the existing
names and argument shapes working), through the code of `drawing*.py`, with the rules of
ai-common.md. A drawing is only useful to an AI if it can check it: `get_drawing` should list
every view (scale, position, its model), dimension (value, which edges), annotation, balloon and
table row, so the AI can verify its own work without a picture; and `render` (or a drawing
picture) must work for a sheet. Recipes: "a fully dimensioned part drawing", "an assembly drawing
with an exploded view, balloons and a parts list", "a sheet metal drawing with flat pattern, bend
table and bend notes".

### Proof
Headless runner cases for every tool and kind; GUI scenarios through the real MCP server and
bridge (`ai_drawing_*.py`): a part drawing (views, every dimension kind, centerlines, a leader,
symbols, title block, PDF and DWG export when a converter is present, else the plain refusal), an
assembly drawing (exploded view from a storyboard, balloons, renumber, parts list, CSV), a sheet
metal drawing (flat pattern view, bend table, bend notes). Check the drawing's content with
`get_drawing`, not with pixels.
