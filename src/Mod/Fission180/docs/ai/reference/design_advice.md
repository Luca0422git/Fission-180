# `design_advice`: Design advice

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > INSPECT > Design Advice. Category: Plastic. Read-only. Needs a solid body.

## What it does

Fusion's Design Advice, read only: check plastic bodies for moulding problems against their plastic rule and say where: walls too thin or too thick (thickness), thickness that varies too much (variation), faces with too little draft for the pull direction (draft), knife edges (knife) and undercuts (undercut). bodies: step ids (default: the visible bodies of components with a plastic rule, else every visible solid body); pull: [x, y, z] the mould's pull direction (default +Z), flip: the other way; checks: which checks (default all). Answers per body the rule, how many faces / edges each check found, and the issues (face or edge, with a ref selector, its centre and the value) up to limit. Nothing is added to the design.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `bodies` | array of strings |  |  | at least 1 item(s) | the bodies (default: see above) |
| `pull` | array of 3 numbers |  |  |  | the pull direction (default [0, 0, 1]) |
| `flip` | boolean |  | `false` |  | pull the other way |
| `checks` | array of strings |  |  | at least 1 item(s) | the checks to run (default all) |
| `limit` | integer |  | `40` | >= 1, <= 500 | the most issues listed |

## Answer

A plain sentence, then JSON with: `pull`, `checks`, `summary`, `bodies`, `counts`, `issues`, `issues_listed`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: faces without enough draft to come out of the mould along +Z

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "diameter": 16, "height": 10}}
]
```

The call:

```json
{"tool": "design_advice", "args": {"checks": ["draft"]}}
```

The answer:

```text
{
 "pull": [0.0, 0.0, 1.0],
 "checks": ["draft"],
 "summary": "Issues: Draft 1",
 "bodies": [{"id": "Body", "label": "Body1", "rule": "Default (mm)"}],
 "counts": {"draft": 1},
 "issues": [
  {
   "check": "Draft",
   "body": "Body",
   "element": "Face1",
   "issue": "Draft 0.00 deg",
   "center_mm": [0.0, 0.0, 5.0],
   "ref": {"type": "cylinder", "radius": 8.0, "count": 1, "body": "Body"}
  }
 ],
 "issues_listed": "1 of 1"
}
```

## More argument examples

- every moulding issue of the design's plastic bodies:
  `{}`
- faces without enough draft:
  `{"checks": ["draft"], "pull": [0, 0, 1]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
