You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: how the AI decides, asks and works (builder ai-behaviour, branch `sf/ai-behaviour`)

Luca: "It needs to be able to ask the right questions before starting, and it needs to be able
to make decisions on what tools to use in a responsible and efficient way." With Relic (a mesh of
8,486 triangles) Claude first refused to make a solid, then copied every polygon; the right tool
(Convert Mesh) was one call away but out of its reach and out of its mind. Five builders are
adding tools for every workspace now (about 172 tools today, more coming). You make the AI use
them well.

### What to build
1. **`plan_approach`** (name it as you see fit; permanent), read-only: input = what the person
   asked for (their words) and optionally the body / mesh / component / drawing it is about.
   It reads the design's facts (meshes and their triangles, solids and their faces, has a
   timeline or not, sheet metal / plastic rules, components and joints, studies, CAM setups,
   drawings, units) and answers, from rules in a pure, unit-tested `fission180/ai/approach_core.py`:
   - the route: which workspace(s) and which tools in which order, the cheapest that does the
     job (examples: "make this mesh a solid" -> inspect_mesh, mesh_prepare repair if needed,
     convert_mesh prismatic; "make it editable" -> rebuild with a timeline only if
     describe_reference can read a plan, else main shapes by hand; "will it break" -> a static
     stress study; "make it on my CNC" -> MANUFACTURE; "for laser cutting" -> SHEET METAL);
   - **the questions to ask the person before starting**, only the ones the request and the
     design leave open and that change the result (purpose; editable timeline or just a solid;
     the sizes / tolerances that matter; units; material and how it will be made; keep the
     original?), worded for a beginner, at most about five, with sensible defaults stated;
   - cost: the slow steps with expected seconds for this design's size (use ai-speed's
     measurements and your own), and what to avoid (never one feature per mesh facet; patterns
     for repeats; user parameters for key sizes; summary detail first on big parts).
   It must answer in well under a second.
2. **The instructions every AI app reads** (`catalog.INSTRUCTIONS`, `WORKFLOW`, `OVERVIEW`, the
   MCP `initialize` instructions, prompts in `mcp_core.py`, the chat panel's system prompt in
   `chat_core.py`, `docs/ai/handbook.md`): a short "before you build" protocol (call plan_approach
   for any job bigger than a single step; ask its open questions in one message; do not ask what
   you can measure; then work), a "pick the cheapest tool that does the job" section, and where to
   find every workspace's tools. Check whether MCP elicitation (`elicitation/create`, the server
   asking the person a question through the AI app) is supported by Claude Desktop, Claude Code
   and Gemini CLI as of now (WebSearch; say what you found and the source); offer it where it is
   supported, never rely on it.
3. **Workspaces:** a tool to show a workspace in the window (DESIGN / SIMULATION / MANUFACTURE /
   ANIMATION / DRAWING / flat pattern...) so the person sees what the AI does, and `get_design`
   or `inspect_design` saying which workspace is shown. Tools of a workspace work from any
   workspace (an AI does not need to switch first); say so.
4. **Finding tools:** with 200+ tools, `list_tools` / `get_help` must let an AI find the right one
   by workspace and by goal ("round the edges", "make it hollow", "turn a mesh into a solid"),
   with each tool's one-line purpose; keep `tools/list` descriptions within the budget of
   ai-common.md and move long detail to docs pages. Check the total size of `tools/list` in
   tokens and keep it reasonable (measure; say the number).
5. **Guard rails in the answers** where they are cheap and general: a call that repeats the same
   tiny operation many times in a row (the facet-copying pattern) gets a note pointing to the
   faster route; a request that will take minutes (a big study, a big mesh) says so before it
   starts when the AI asked plan_approach.

### Proof
Unit tests of approach_core's rules (at least 25 requests across every workspace, including
Relic's "make this mesh a solid" and "make it editable", a sheet metal bracket, a study, CAM,
an animation, a drawing); a GUI scenario through the real MCP server and bridge
(`ai_plan_approach.py`) on a design with a mesh, a solid and an assembly; the instructions'
size measured; every example in the docs run by the docs runner.
