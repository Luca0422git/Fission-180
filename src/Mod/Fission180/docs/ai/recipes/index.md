# Recipes: common parts step by step

Each recipe builds a real part with Fission 180's tools, one call at a time, and checks it with
numbers. Every call in every recipe is run by Fission 180's tests in real FreeCAD (the
`expect` part of a call is what its answer must contain, not a tool argument), so the
arguments, the ids the answers report and the numbers are known to be right. Copy the
calls, change the sizes, and check with the same tools.

| Recipe | What it shows |
|---|---|
| [L bracket with mounting holes](fission180://docs/recipes/bracket.md) | a side profile extruded, inside fillet, outside chamfer, holes into two faces, material and mass |
| [Enclosure with a lid](fission180://docs/recipes/enclosure-with-lid.md) | rounded box, shell, a second body, fillet sets, a plug with clearance, interference, STL per body |
| [Stepped shaft with a keyway](fission180://docs/recipes/shaft-with-keyway.md) | revolve, a slot cut from a tangent plane with flip, chamfers with any_of, shoulder fillet |
| [A pair of meshing spur gears](fission180://docs/recipes/gear-pair.md) | gear maths, two gears, interference, rotating a body about a pivot, components, ground |
| [Flange with a bolt circle](fission180://docs/recipes/flange-bolt-pattern.md) | revolved turned part, one hole then a circular pattern, fillet and chamfer on circles |
| [Threaded fastener (hex bolt M8 x 30)](fission180://docs/recipes/threaded-fastener.md) | polygon, extrude down with flip, modeled thread, diff_design to prove a change |
| [Cantilever snap-fit hook](fission180://docs/recipes/snap-fit.md) | a side profile extruded symmetric, root fillet picked by coordinates |
| [Sheet-like U bracket](fission180://docs/recipes/sheet-like-part.md) | open profile, thin extrude, bends as fillet sets, hole through sheet |
| [Revolved knob with grip grooves](fission180://docs/recipes/revolved-knob.md) | revolve, a cut then a circular pattern of it, bore from below, hole vs cut direction |
| [Lofted handle](fission180://docs/recipes/lofted-handle.md) | loft through three profiles, ellipses, checking the size, diff of a cut |
| [Curved panel from a surface patch](fission180://docs/recipes/surface-patch.md) | 3D boundary curves, surface patch, thicken, surface bodies |
| [Parametric mounting plate](fission180://docs/recipes/parametric-plate.md) | user parameters, sketch dimensions and model parameters with expressions, a pattern that follows, change and verify |
| [Is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md) | a simulation study: fixed holes, a force, pre-check, solve, safety factor and reactions, thicken and solve again |
| [A fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md) | drawing views, every dimension kind (sizes, ordinates, baseline), a fit and tolerances, centre marks, datum and position tolerance, section and detail, title block, checking with get_drawing and its picture, DXF |
| [An assembly drawing with an exploded view](fission180://docs/recipes/assembly-drawing.md) | components, a storyboard, an exploded view, a parts list with balloons, Renumber and Align Balloons, the parts list as CSV |
| [A sheet metal drawing](fission180://docs/recipes/sheet-metal-drawing.md) | the flat pattern drawn with its size, a bend table, bend notes, the folded part beside it, CSV and DXF |
| [Rebuild a part that has no timeline](fission180://docs/recipes/reverse-engineer.md) | reverse engineering: an imported STEP or mesh part rebuilt as timeline steps with start_rebuild, describe_reference, compare_to_reference after every feature, finish_rebuild |

Looking for something else? `examples_search` finds recipes and the golden models (about
450 small designs with measured results) by words, tool or op, and
[the golden model index](fission180://docs/examples/golden-models.md) lists them by feature.
