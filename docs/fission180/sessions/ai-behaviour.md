# Wave 8, builder ai-behaviour: how the AI decides, asks and works (2026-11-13)

Brief: `docs/fission180/dev/briefs/ai-behaviour.md` (with `ai-common.md`). Branch
`sf/ai-behaviour`. Luca: "It needs to be able to ask the right questions before starting, and
it needs to be able to make decisions on what tools to use in a responsible and efficient way."

## What I found

- **The instructions were cut in Claude Code.** Claude Code passes a server's instructions to
  the model only up to 4,096 characters (code.claude.com/docs/en/mcp, "Tool search for MCP
  server authors"); ours were 7,767, so the second half (the end of the selector rules, picks,
  sketch planes, curves, checking, documentation) never reached Claude there. Now the
  essentials come first (3,187 characters) and the full rules after them.
- **Claude Code loads MCP tools on demand** (tool search, on by default): at the start the
  model sees only the tool names and the instructions. So the instructions must say when to
  look for which tool, and the tools an AI needs first (plan_approach, ask_person, list_tools,
  get_help, inspect_design) are marked `_meta` `anthropic/alwaysLoad`.
- **Claude Desktop may load every tool every turn** (a user report: about 75,000 tokens for 155
  tools). `tools/list` is 381,254 characters for 216 tools with every builder's branch merged
  (about 95,000 tokens at 4 characters a token): descriptions 134,600, schemas 200,500; 38
  descriptions are longer than ai-common's 900 characters (17,200 characters over; the
  longest: cam_edit 3,191, cam_operation 2,785, measure 2,756, create_sketch 2,558,
  insert_hardware 2,115, flange 2,096). The first sixteen tools carried the whole selector help seven times (14,000
  characters): now a summary (9,400 characters saved); the rest is the other builders'.
- **MCP elicitation** (the server asking the person through the AI app): Claude Code shows it
  (form and URL) in interactive terminal sessions and declares `elicitation: {form, url}` to
  stdio servers (v2.1.287+); Claude Desktop's chat has no official support (Cowork and the Code
  tab were reported to cancel it at once); Gemini CLI's client declares only `roots`. So
  `ask_person` offers it and never relies on it.
- **Why Claude refused Relic, then copied facets**: nothing it read said that a mesh becomes a
  solid in one call, nor that a mesh *can* be printed or measured as it is; the only mesh route
  it knew was a rebuild (start_rebuild, many calls, "one feature per facet" was nowhere
  forbidden). The instructions, the handbook, plan_approach and the repetition note now all say
  it. (The mesh tools themselves are builder ai-mesh's.)
- Fission 180's Convert Mesh prismatic merges coplanar triangles only; round faces stay
  facets (`insert.solid_from_mesh`: FreeCAD has no surface fitting). So converting a mesh does
  not make describe_reference read its holes: the editable route starts the rebuild on the
  mesh itself and offers convert_mesh as the fast honest alternative.

## What I built

- `fission180/ai/approach_core.py` (pure): the goals (mesh to solid, editable, new part, one
  change, plastic, sheet metal, assembly, strength, print, CNC, drawing, animation, fix,
  inspect) found by word rules; each goal's route from the design's facts; the questions (at
  most five, each with a default, skipped when the request or the design answers them); the
  cost table (seconds per thousand faces / triangles, measured where a source is named); what
  is not in Fission 180; list_tools' search by goal (`GOALS`, `find_tools`); the repetition
  guard (`RepeatWatch`); the elicitation form (`form_schema`, `answers_text`).
- `catalog/approach_tools.py`, `actions/approach_actions.py`: `plan_approach` (facts read in
  one pass, faces with `countElement`, never a face list; 0.1-0.17 s through the bridge),
  `ask_person` (the MCP server answers it: `mcp_core.ask_person`, `request_client`),
  `show_workspace` (the workspace menu's code; refused while busy and for SIMULATION without a
  study). `inspect_design` / `get_design` say which workspace is shown.
- `catalog/__init__.py`: the instructions rewritten (ESSENTIALS first: before you build, the
  cheapest tool, workspaces and finding tools, check, selector summary), help topics `approach`
  and `workspaces`, `tools` grouped by workspace, `tool_list` by goal / workspace with each
  tool's purpose, `ALWAYS_LOAD`, list_tools' category takes every category.
- `mcp_core.py`: the session (the client's elicitation capability at initialize), requests to
  the client and their answers routed back (`set_sender`, a one-line hook in
  `fission180_mcp.Server.run`), the repetition note on changing calls. `chat_core.py`: the same
  protocol in the chat panel's system prompt, and the note. `mcp_resources.py`: prompt
  `plan_job`; `model_part` starts with plan_approach.
- Docs: handbook sections "Before you build", "Pick the cheapest tool", "Workspaces" (their
  calls run in the docs runner), README "Start here" step 0, recipes index, troubleshooting
  "Slow calls, and the same small step again and again".

## Measurements

| What | Seconds |
|---|---|
| plan_approach, headless, runner's parts | 0.001-0.035 (first call of a session 0.17: modules load) |
| plan_approach through the real MCP server and the bridge, window up, a mesh + box + 2-component assembly | 0.17 first, 0.11-0.13 after |
| list_tools with goal | 0.005-0.008 |
| show_workspace | under 0.1 (the scenario's calls) |

## FreeCAD / Fission 180 traps

- `TopoShape.countElement("Face")` is instant where `len(shape.Faces)` builds every face
  (0.008 s at 726 faces, 0.1 s at 3,000); `shape.Volume` + `Area` cost 0.13 s at 726 faces, so
  "is it a thin plate" is only measured on bodies of at most 200 faces.
- `Mesh.isSolid()` is 0.05 s at 78,000 triangles: checked up to 300,000.
- `simulation_ui.enter_workspace()` opens New Study a moment later when the design has none;
  an AI call would then find Fission 180 busy. show_workspace refuses SIMULATION without a
  study instead (create_study first), as Fusion's New Study comes up there too.
- A read-only tool is not refused by the bridge while a dialog is open (only changing ones
  are); show_workspace checks `host.busy()` itself, or entering a workspace would finish the
  person's open dialog.
- An extrude of a sketch that does not touch the active body makes a new body (Join away
  from the body = New Body): eight dots extruded in the air made eight bodies.
- The docs runner and the headless runner read the JSON of an answer from its first `{`: a
  plan's sentence must not contain braces (the "Next:" line names the tool only).
- A TechDraw page's `ViewObject.Visibility` is its tab: Create Flat Pattern hid every shown
  object and showed them again at Finish, which closed a drawing's tab and opened it again in
  front of the 3D view (and the camera could not be put back: "finish flat pattern:
  setCamera"). `flatpattern_ui.enter` now leaves TechDraw objects alone; found by
  ai_plan_approach (a drawing shown, then a flat pattern); flatpattern_drawing (42 checks) and
  flatpattern_environment (27) still pass.

## Changelog lines

- Before a job of more than one step, an AI connected to Fission 180 now plans it with a new
  tool, plan_approach: which tools in which order (the cheapest that does the job), the
  questions to ask you first, and how long the slow steps take on your design.
- An AI asks its questions in one message, each with a sensible default, and never asks what
  it can measure; in Claude Code (terminal) it can show them as a small form (ask_person).
- An AI that turns a mesh into a solid is told to use Convert Mesh in one call, and gets a
  note when it starts making the same small step again and again (copying facets).
- An AI can show you the workspace it works in (show_workspace: DESIGN and its tabs,
  SIMULATION, MANUFACTURE, ANIMATION, a drawing, a flat pattern); every tool works from any
  workspace.
- An AI finds the right tool by what it does ("round the edges", "make it hollow") with
  list_tools.
- Claude Code now reads Fission 180's whole "how to work" text (it used to cut it in half).
- Finishing a flat pattern no longer brings an open drawing's tab in front of the 3D view.

## Known issues

- Claude Desktop may still load all 216 tools' descriptions every turn (about 95,000 tokens);
  38 tool descriptions are longer than the 900-character budget (owned by the other builders).
- plan_approach's cost table is partly guessed (marked in `approach_core.COSTS`); ai-speed's
  benchmark (`ai_speed_bench.py`) was not on its branch yet when this was written.
- Version History (UTILITIES > UTILITY) has no AI tool (listing or restoring a design's
  versions).
- ask_person through Claude Desktop answers "ask in your reply" (no elicitation there).
