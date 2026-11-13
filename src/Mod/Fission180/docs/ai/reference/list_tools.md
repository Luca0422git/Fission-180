# `list_tools`: List tools

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: (Fission 180's command list). Category: Help. Read-only. Needs nothing.

## What it does

Find tools: by goal in plain words (goal "round the edges", "make it hollow", "turn a mesh into a solid": the best tools first), by workspace (design, simulation, manufacture, animation, drawing; any: help, files, the view) or by category; each with its purpose, its Fusion command, whether it changes the design and whether it can run now (and why not). Every tool works from any workspace. Without arguments: every tool, by category (no purposes: filter for those).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `category` | `help` \| `document` \| `inspect` \| `sketch` \| `create` \| `modify` \| `surface` \| `sheet_metal` \| `plastic` \| `construct` \| `assemble` \| `timeline` \| `parameters` \| `import_export` \| `drawing` \| `view` \| `simulate` \| `manufacture` \| `animation` \| `rebuild` |  |  |  |  |
| `workspace` | `design` \| `simulation` \| `manufacture` \| `animation` \| `drawing` \| `any` |  |  |  | the workspace whose tools to list |
| `goal` | string |  |  |  | what you want to do, in plain words |

## Answer

A plain sentence, then JSON with: `tools`, `count`. The example below shows a real one.

## Errors

- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: by category

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "list_tools", "args": {"category": "inspect"}}
```

The answer:

```text
12 tools of category inspect. Every tool works from any workspace.
{
 "tools": [
  {
   "name": "get_design",
   "title": "Get design",
   "category": "inspect",
   "ribbon": "BROWSER (the design's bodies, sketches, parameters) and TIMELINE",
   "read_only": true,
   "workspace": "design",
   "purpose": "Describe the open Fission 180 design",
   "available": true
  },
  {
   "name": "measure",
   "title": "Measure",
   "category": "inspect",
   "ribbon": "INSPECT > Measure",
   "read_only": true,
   "workspace": "design",
   "purpose": "Measure between two picks a and b of the current body or the origin",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  },
  {
   "name": "physical_properties",
   "title": "Physical properties",
   "category": "inspect",
   "ribbon": "BROWSER > a body > Properties (INSPECT)",
   "read_only": true,
   "workspace": "design",
   "purpose": "Physical properties of bodies, as Fusion's Properties",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  },
  {
   "name": "center_of_mass",
   "title": "Center of mass",
   "category": "inspect",
   "ribbon": "INSPECT > Center of Mass",
   "read_only": true,
   "workspace": "design",
   "purpose": "The centre of mass of bodies together (Fusion's Center of Mass), weighted by their materials.",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  },
  {
   "name": "interference",
   "title": "Interference",
   "category": "inspect",
   "ribbon": "INSPECT > Interference",
   "read_only": true,
   "workspace": "design",
   "purpose": "Find where bodies overlap (Fusion's Interference)",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  },
  {
   "name": "section_analysis",
   "title": "Section analysis",
   "category": "inspect",
   "ribbon": "INSPECT > Section Analysis",
   "read_only": true,
   "workspace": "design",
   "purpose": "Cut the design with a plane to look inside (Fusion's Section Analysis)",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  },
  {
   "name": "inspect_design",
... (66 more lines)
```

## Example 2: the tools for a goal in plain words, best first

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "list_tools", "args": {"goal": "make it hollow"}}
```

The answer:

```text
The tools for 'make it hollow', best first: shell. Every tool works from any workspace.
{
 "tools": [
  {
   "name": "shell",
   "title": "Shell",
   "category": "modify",
   "ribbon": "SOLID > MODIFY > Shell",
   "read_only": false,
   "workspace": "design",
   "purpose": "Hollow the current body out with a wall thickness (Fission 180's Shell).",
   "available": false,
   "why_not": "No design is open: call new_design or open_design first (or create_sketch, which starts a new design)."
  }
 ],
 "count": 1
}
```

## More argument examples

- the tools that hollow a part, best first:
  `{"goal": "make it hollow"}`
- the Modify tools and which can run now:
  `{"category": "modify"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
