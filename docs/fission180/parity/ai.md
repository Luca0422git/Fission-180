# Parity spec: AI apps building in Fission 180 (brief home-cloud-ai.md, milestone M3)

An AI app Luca chats with (Claude Desktop, Gemini CLI, Claude Code, Codex...) gets Fission 180's
tools through MCP (the Model Context Protocol) and builds in the open design while he
watches. Fusion has an AI assistant of its own but no connector for outside AI apps: this is
**beyond Fusion**; the design steps are the same code as Fission 180's dialogs.

Implemented in `src/Mod/Fission180/fission180/`:
- `ai/tools_core.py`: the 16 tools (get_design, screenshot, measure, create_sketch, extrude,
  revolve, fillet, chamfer, hole, pattern, shell, set_parameter, undo, redo, save, export),
  their JSON Schemas and descriptions for the model, the checks of their arguments (plain
  sentences: "radius must be a number above 0"), and how each becomes design steps.
- `ai/ops/`: the design steps (milestone M0: the golden models' code, so 434 reference parts
  prove what an AI builds).
- `ai/mcp_core.py`, `ai/fission180_mcp.py`: the MCP server an AI app starts (stdio; MCP
  versions 2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05). It runs with FreeCAD's own
  Python on Windows (python3 elsewhere), imports no FreeCAD, and passes each call to:
- `ai/bridge_core.py`, `ai/bridge.py`: the bridge inside Fission 180: 127.0.0.1 only, a random
  port and key in `<user data>/Fission180/ai/bridge.json`; calls run on Fission 180's own thread.
- `ai/installers.py`, `ai_ui.py`: Add an AI (Claude Desktop, Gemini CLI, a Claude Desktop
  extension `.mcpb`, the command line for other apps), the AI activity panel, Home's card.

Status: **built and tested with the real MCP server speaking to Fission 180 (scenario
`ai_bridge`, 43 checks); not yet tried with Claude Desktop or Gemini CLI on Windows.**

Tests: scenario `ai_bridge.py` (9 paths: the server starts and lists the tools, AI control
off by default, switched on and the first call asks, the 40 x 30 x 10 box with 3 mm rounded
edges in three calls (each one Undo step), get_design and a PNG screenshot, refused while a
command dialog is open, the activity panel and Undo last AI step, Stop AI control, Add an AI
for Gemini CLI and the Claude extension); unit tests `test_ai_tools_core.py`,
`test_ai_mcp_core.py`, `test_ai_bridge_core.py`, `test_ai_mcp_server.py` (the real server
against a fake bridge), `test_ai_installers.py`, `test_ai_ops_layout.py`.

## Sources (checked 2026-10-19)

- MCP specification, github.com/modelcontextprotocol/modelcontextprotocol: stdio transport
  (one JSON-RPC message per line), lifecycle and version negotiation, tools/list and
  tools/call, image content, batching removed (2025-06-18 changelog), schema 2025-11-25.
- MCPB (Claude Desktop extensions), github.com/modelcontextprotocol/mcpb MANIFEST.md:
  manifest_version 0.3, server type python, `${__dirname}`.
- Gemini CLI, github.com/google-gemini/gemini-cli docs/tools/mcp-server.md: `mcpServers` in
  `~/.gemini/settings.json`, `/mcp` lists them.
- Claude Code, code.claude.com/docs/en/mcp: `claude mcp add ... -- <command>`; Codex CLI:
  `codex mcp add NAME -- CMD` (openai/codex source).
- Claude Desktop's settings file `claude_desktop_config.json` (`%APPDATA%\Claude\` on
  Windows); the Linux path `~/.config/Claude/` is **not verified**.
- FreeCAD's user data folder (where bridge.json is): src/App/ApplicationDirectories.cpp.

## Behaviour

| What | Fission 180 |
|---|---|
| Off unless switched on | Preferences > AI > **Allow AI apps to control Fission180** (off). Off: nothing listens; the AI app's calls answer "Fission 180 is not running, or 'Allow AI apps to control Fission 180' is off". |
| Add an AI | Home's **+ Add an AI**, File > **Add an AI App**: Claude Desktop (**Set up** adds Fission 180 to its settings file, a backup kept; quit and restart Claude Desktop), **Install as Claude extension...** (a `.mcpb` file opened with Claude Desktop), Gemini CLI (Set up; `/mcp` lists it), another app (the command line to copy). Setting one up switches AI control on. **Remove** takes Fission 180 out again (backup kept). A settings file that is not valid JSON is never touched. |
| The first call of a session | Fission 180 asks: "An AI app wants to control Fission 180... Allow it for this session?" **Allow** / **Deny** (Deny is the default button). Denied: every call of the session is refused, in words. |
| Building | Each design-changing call is **one Undo step** named after it ("AI: Extrude 10 mm", "AI: Fillet 3 mm"), in the timeline like a step made by hand, built with the dialogs' code. A new step gets a readable id (Sketch1, Extrude1, Fillet1) the AI uses in later calls. A call that fails changes nothing and answers why ("extrude 'Extrude2': no sketch area contains [5, 5]"). With no design open, the first step starts one. |
| Seeing | **get_design**: bodies (volume, bounding box), the timeline with ids, parameters, sketches and their closed areas. **screenshot**: a PNG of the view (iso, front, top...) the AI looks at. **measure**: distance and angle between two picks. |
| Busy | While a command dialog, a sketch or a question is open in Fission 180, changing calls answer "Fission 180 is busy: ... Finish or cancel it first." |
| Files | **save** saves the design (a version) or to a path; **export** STEP / STL / 3MF. Writing over an existing file always asks the person (Allow / Deny). There is no tool that runs code. |
| AI activity | A panel (right) lists every call with its answer, newest first, errors in red; **Undo last AI step** (only when the newest step is the AI's) and **Stop AI control** (switches the option off at once). Home's card shows AI control on / off, the apps set up and when it was last used. |
| Security | The bridge listens on 127.0.0.1 only; every call carries the random key from bridge.json (owner-only file), compared in constant time; a request from a web page (an Origin header) is refused; keys are never logged. |

## To check on a real PC (Windows, Luca)

1. File > Add an AI App > Claude Desktop > Set up; restart Claude Desktop; ask "make me a
   40 x 30 x 10 box with 3 mm rounded edges": Fission 180 asks once, the box appears, three
   steps in the timeline, Undo removes them one by one.
2. The same with Install as Claude extension.
3. Gemini CLI: Set up, `/mcp` lists fission180.
4. The screenshot tool's picture shows the part (in the sandbox, without a graphics card,
   the off-screen picture left an empty frame on the 3D view: look whether it does on a PC).

## M4: the chat panel inside Fission 180

The same 16 tools, but the person chats inside Fission 180 with their own API key: no other app
needed. Fusion's own assistant is Autodesk's; here the person picks the AI.

Implemented in `src/Mod/Fission180/fission180/`:
- `ai/providers/`: one adapter per API (Anthropic Messages, OpenAI Responses, Google Gemini,
  any OpenAI-compatible server such as Ollama or LM Studio), each with its one default model
  and its models list from the provider's models endpoint.
- `ai/chat_core.py`: the conversation loop (the model asks for tools, Fission 180 answers,
  repeat until the model answers in words; at most 25 requests per message; Stop).
- `secrets_store.py`: keys kept for this user (Windows: DPAPI, encrypted for the Windows
  account; macOS Keychain; Linux Secret Service or a file only the owner can read).
- `ai/chat_ui.py`: the panel (right dock). File > **AI Chat**, Home's **Open chat panel**.

| What | Fission 180 |
|---|---|
| Pick the AI | Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Local or other (an address such as `http://localhost:11434/v1`; **List** asks the server for its models). |
| Key | Pasted once, **Save key** keeps it (encrypted on Windows); never written to the log or the Report view. A key the provider refuses is said in words ("the key was not accepted"). |
| Cost and privacy | The panel says plainly: API use is billed by the provider per use, separately from a chat subscription; the design's data and screenshots go to that provider; the local option is free and private. |
| Building | Every step the AI makes is one Undo step, as with AI apps. No "Allow this AI app?" question: the person typing is the one asking. The rest of the bridge's rules hold (busy while a dialog is open, overwriting a file asks). |
| Stop | Stops after the current step; the steps made stay in the timeline. |
| Answers | Shown word by word as they arrive (Claude, ChatGPT, Gemini, local models); Stop ends one at once. |

Tests: scenario `ai_chat.py` (a fake OpenAI-compatible server inside the test: List shows
its model, "make a 40 x 30 x 10 box" builds the box in two Undo steps, a model that never
stops is stopped with Stop, a Claude key saved, read back, never logged, removed); unit tests
`test_ai_providers.py` (each adapter against recorded answers), `test_ai_chat_core.py`
(the loop with a scripted model), `test_secrets_store.py`.

Not verified: the OpenAI default model name (`providers/openai.py`) and Gemini's exact
error words; the real services were not called from the sandbox.

### To check on a real PC (M4)

1. File > AI Chat > Claude, paste an Anthropic API key, Save key, ask for the 40 x 30 x 10
   box with 3 mm rounded edges: the steps appear, Undo removes them one by one.
2. The same with ChatGPT and Gemini keys, and with Ollama (`ollama pull qwen3:8b`, then
   Local or other, `http://localhost:11434/v1`, List).

## The AI panel (2026-10-19, Luca: reachable in a design, a clear X, a switch, the AIs added)

One panel at the right for everything AI (`fission180/ai_panel_ui.py`): **UTILITIES > AI**
(its own icon; a second click closes it), File > AI Panel, Home's **Open AI panel**.

| What | Fission 180 |
|---|---|
| Close | Its title bar: **AI** and an **X** (drawn like the browser's). |
| AI control | A switch at the top: the same option as Preferences > AI. It replaces the Stop AI control button. Home has the same switch. |
| Your AIs | The AI apps set up (Claude Desktop, Gemini CLI) and the chat AIs with a key kept (Claude, ChatGPT, Gemini) or a local model's address, each with its badge: Fission 180's own coloured square with letters (Cl, Ge, GPT, Lo), never a company's logo. As many as there are (the list scrolls). Double-click: a chat AI opens the Chat tab with it chosen; an app opens Add an AI on it. **+ Add an AI** under the list. Home lists the same AIs. |
| Chat, Activity | Two tabs: the chat panel and the activity list (Undo last AI step). File > AI Chat and AI Activity open the panel on their tab. A call from an AI app opens the panel on Activity when it was closed. |

Tests: scenario `ai_panel.py` (UTILITIES > AI opens and closes it, the X, the switch and
Home's, two chat keys listed with badges on the panel and Home, double-click picks Claude,
Home closes the browser and opens Preferences); `ai_bridge.py` Path 8 turns AI control off
with the switch.

## Documentation for AI models (2026-10-21, Luca: "give all the tools possible, with absolutely all the documentation available")

An AI that can read more about Fission 180 works better in it. Fusion has help pages for people;
Fission 180 also has documentation written for AI models, searchable by them, and checked
against the code: **beyond Fusion**.

Implemented in `src/Mod/Fission180/`:
- `docs/ai/`: the handbook (what Fission 180 is, Fusion's ideas mapped to it, coordinates and
  units, the timeline and history marker, bodies, components and joints, ids, how tool calls
  become undo steps, a good way to work), sketches, selectors (with a cookbook), checking,
  troubleshooting (the real failure messages and how to recover), 12 recipes (bracket,
  enclosure with lid, shaft with keyway, gear pair, flange with bolt pattern, threaded
  fastener, snap-fit, sheet-like part, revolved knob, lofted handle, surface patch,
  parametric plate), and generated pages: `tools.md`, one `reference/<tool>.md` per tool,
  `examples/golden-models.md` and a copy of the person's documents under `user/`.
- `fission180/ai/docs_core.py`: the library (BM25 search over every section, sections by
  anchor, pages, examples, the system prompt's index, the single-file export);
  `fission180/ai/tool_docs.py` writes the generated pages; `tools/fission180/make_ai_docs.py`
  runs it.
- Tools `docs_search`, `docs_read`, `examples_search` (the MCP server answers them itself, so
  they work while Fission 180 is closed); MCP resources `fission180://docs/<path>[#anchor]`,
  `fission180://examples/golden/<id>`, `fission180://handbook` (all in one file; `/compact`,
  `/full`); the chat panel's system prompt has a short index of the documents.
- One file for AI apps that load files: **+ Add an AI > Save AI handbook...** (writes the
  compact file to load, about 45 thousand tokens, and next to it the one with every tool's
  page, about 170 thousand; the dialog gives both sizes in tokens),
  `fission180-cli docs export FILE [--compact | --full]`.

| What | Fission 180 |
|---|---|
| Accurate | Every tool call in every document is run in real FreeCAD by the tests (`Fission180Tests/headless/docs_runner.py`, 320 calls in 17 documents), each with what its answer must contain; every tool's reference example answer is recorded in FreeCAD and checked again on every run; a unit test fails when a generated page is out of date or a `fission180://` link (anchor included) is broken. |
| Searchable | `docs_search` "cut does nothing" finds the troubleshooting section; the unit tests ask 25 realistic questions and check the right page is in the first three answers. |
| Complete | Every tool has a page with every argument (type, unit, default, limits), the answer, the errors and a complete example with its real answer; the person's own documentation is included. |

Fixed on the way (found by writing the documentation): Move/Copy rotate ignored `pivot`
(golden `bodies_move_rotate_pivot`); bounding boxes of free-form bodies were too big (lofts,
patches: FreeCAD's quick box includes the control points); a surface step that failed did
not say why; a surface body reported a volume; deleting a parameter used by another
parameter's formula was allowed (the formula broke); a step that changed nothing (a cut from
the top face without flip, a shell thicker than the part) answered "Done" with no warning.

Tests: `test_ai_docs_library.py`, `test_ai_docs_contract.py` (unit); the docs runner
(`run_tests.sh --only headless / base`); scenario `ai_docs_gui` (the reference examples that
need the window, the docs tools through the bridge, Save AI handbook... with a real click).

## Wave 8: how the AI decides, asks and works (builder ai-behaviour, 2026-11-13)

Luca (2026-11-13), after Claude first refused to turn an 8,486-triangle mesh ("Relic") into a
solid and then copied every polygon as features, while MESH > Convert Mesh did it in seconds:
"it needs to be able to ask the right questions before starting, and it needs to be able to
make decisions on what tools to use in a responsible and efficient way." Fusion's own AI
(Autodesk Assistant) is Autodesk's and works inside Fusion; this connector is **beyond
Fusion**: the decisions are Fission 180's rules, written down and tested.

### Behaviour spec and sources (checked 2026-11-13)

| What | Source | Kind |
|---|---|---|
| Autodesk Assistant in Fusion is a panel docked at the right; it answers questions about the design (volume, area), finds and highlights geometry, does batch actions, and in MANUFACTURE creates setups and toolpaths from words | autodesk.com Fusion blog, "April 2026 product update" and "March 2026 product update" (read through search excerpts) | Autodesk |
| Autodesk tells people to prompt the assistant with "ask me follow-up questions if anything is ambiguous": asking first is advice, not a built-in step | autodesk.com Fusion blog, "Autodesk Assistant in Fusion: a step-by-step guide" | Autodesk |
| Fusion has an MCP server of its own ("Fusion MCP") for AI apps working in Fusion locally | monoist.itmedia.co.jp, 2026-06-04 | Press |
| Picking SIMULATION without a study opens New Study | docs/fission180/parity/simulation.md | Autodesk |
| Claude Code cuts a server's instructions and an upfront tool's description after 4,096 characters; tool search is on by default (only the tool names and the instructions load at the start); `_meta` `anthropic/alwaysLoad` loads a tool upfront | code.claude.com/docs/en/mcp, "Tool search for MCP server authors", "Mark a tool to load upfront" | Anthropic docs |
| Claude Code shows MCP elicitation (form and URL) in interactive terminal sessions, declares `elicitation: {form, url}` to stdio servers (v2.1.287+), and cancels it in non-interactive sessions | code.claude.com/docs/en/mcp, "Respond to MCP elicitation requests", "Elicitation modes Claude Code declares" | Anthropic docs |
| Claude Desktop (chat): no official word on elicitation; a feature request was closed in April 2026 without a note; Cowork and the Code tab were reported to cancel elicitation at once (Aug-Sep 2026) | claudeissues.com #41110, #56243, #88901 (user reports) | Forum |
| Claude Desktop has "Tool access: Load tools when needed"; one report said it loaded about 75,000 tokens of tools for 155 tools anyway | claudeissues.com #41472, #25892 (user reports) | Forum |
| Gemini CLI's MCP client declares only `roots` (no elicitation) | github.com/google-gemini/gemini-cli, packages/core/src/tools/mcp-client.ts on main, read 2026-11-13 | Source |
| The plan-first protocol, the questions with defaults, the cost estimate, the repetition note | Fission 180's own rules (Luca's request) | Guess (ours) |

### What Fission 180 does

| What | Fission 180 |
|---|---|
| Plan a job | `plan_approach` (read-only, needs nothing open): the person's words and optionally what it is about (`target`, default the selection). It reads the design's facts cheaply (meshes and triangle counts, closed or not; bodies with their faces counted without building a face list, timeline or imported or converted mesh, sheet metal, thin plates; components, joints, studies, setups, storyboards, drawings, flat patterns, a rebuild going on, units, the workspace shown) and answers the goals, the route (tools in order with argument hints, where each is in the ribbon, the seconds it takes here), at most five questions with defaults (never the units or sizes the design has), the cost with `say_first` when it takes minutes, what to avoid, and notes (studies other than Static Stress, turning, photorealistic rendering, `.f3d` are not there). Rules: `fission180/ai/approach_core.py` (pure). |
| Relic's requests | "make this mesh a solid": `inspect_mesh` -> `mesh_prepare` repair (only if open) -> `convert_mesh` prismatic -> `check_design`, the question "an editable timeline or a solid?", never facet copying. "make it editable": `inspect_mesh` -> (reduce above 10,000 triangles) -> `start_rebuild` on the mesh -> `describe_reference` -> `compare_to_reference` after each feature -> `finish_rebuild`, with the note to offer `convert_mesh` first and to say so plainly when no plan can be read. |
| Ask the person | `ask_person`: answered by the MCP server itself. Where the AI app declared elicitation (form), the questions become the app's own form (`elicitation/create`, a flat object of text fields, choices as an enum, each default given); the answer, a decline or a cancel comes back in words; a tool call the app cancels stops waiting and cancels the form. Elsewhere (no elicitation, the chat panel, headless) it answers at once: ask in your reply. Never relied on. |
| Show a workspace | `show_workspace` (needs the window; not an undo step): design (and its tab), simulation (and SETUP / RESULTS; refused without a study: create_study first, as Fusion opens New Study there), manufacture, animation, drawing (the newest or one named), flat_pattern. The workspace menu's own code (`enter_workspace` / `leave_workspace`, `drawing_ui.open_drawing`, `flatpattern_ui.enter`); refused while a command dialog is open. `inspect_design` and `get_design` say which workspace and tab are shown (`workspace`, null without the window). Every tool works from any workspace (a body made while SIMULATION shows). |
| Find a tool | `list_tools` with `goal` (plain words, best first, from a table of goals and the tools' own words), `workspace` or `category`; filtered rows carry the tool's workspace and its purpose (the first sentence of its description). `get_help` topics `approach`, `workspaces`, and `tools` grouped by workspace. |
| The instructions | MCP `initialize` instructions start with "before you build" (plan_approach, one message of questions, never ask what you can measure, say when it takes minutes), "pick the cheapest tool", the workspaces and how to find tools, then the checking and selector essentials: 3,187 characters, inside Claude Code's 4,096 (unit test); the full rules follow for the apps that read them all. The chat panel's system prompt and the MCP prompts (`plan_job`, new; `model_part` starts with plan_approach) say the same. In Claude Code, `plan_approach`, `ask_person`, `list_tools`, `get_help` and `inspect_design` load upfront (`_meta` alwaysLoad). |
| The same small step again and again | The MCP server and the chat panel watch the changing calls: eight in a row of at most two kinds of small step (a sketch and an extrude per copy) add a note to the answer naming the faster route (one sketch, a pattern, convert_mesh for a mesh); said again only after sixteen more. A sketch of 150 points or more gets the same note. |

### Measured

- `plan_approach`: 1-35 ms headless on the runner's parts (the first call of a session loads
  the workspaces' modules: about 0.17 s); through the real MCP server and the bridge with the
  window, on a design with a mesh, a box and a two-component assembly: 0.17 s the first time,
  0.11-0.13 s after (scenario `ai_plan_approach`).
- `tools/list`: before wave 8 309,368 characters for 175 tools; with every builder's tools
  merged here 381,254 characters for 216 tools (descriptions 134,600, schemas 200,500), about
  95,000 tokens at 4 characters a token (more for JSON). 38 descriptions are longer than
  ai-common's 900 characters (17,200 characters over; the longest cam_edit 3,191,
  cam_operation 2,785, measure 2,756, create_sketch 2,558); none passes Claude Code's 4,096
  (unit test). The first sixteen tools' selector arguments now carry a summary instead of the
  whole selector help seven times (9,400 characters less). In Claude Code (tool search on)
  only the names and the instructions load at the start; Claude Desktop may load them all
  (report above).
- The MCP instructions: 8,614 characters, of which the essentials are the first 3,187; the
  chat panel's system prompt 7,294 characters with the documentation index.

### Tests

Unit: `test_ai_approach_core.py` (54 tests: 40 requests across every workspace, Relic's two,
a sheet metal bracket from nothing / a sheet metal body / a flat plate, a study with and
without its numbers and on a 3,000-face part, CNC, a lathe, print a part and a mesh, a part and
an assembly drawing, an exploded video, an animation of bodies, a hinge, a plastic enclosure,
fix, inspect, render, odd input; the search by goal; the repetition guard; the form),
`test_ai_mcp_core.py` (`AskPerson`, `Guard`, `Instructions`), `test_ai_mcp_server.py`
(`AskThroughTheApp`: the real server asks the app and gets the answer while it keeps reading).
Headless runner: `Fission180Tests/headless/approach_tools.py` (20 calls). Docs: the handbook's
new sections and troubleshooting's are run by the docs runner; reference examples for the
three tools. Scenario `ai_plan_approach` (72 checks, through the real MCP server and the
bridge; also passed with the 3D view 770 px tall).

## Wave 8 coverage: ai-behaviour

| Ribbon command | Tool (kind) |
|---|---|
| Workspace menu > Design | `show_workspace` workspace `design` |
| Workspace menu > Simulation | `show_workspace` `simulation` (a study first: `create_study`) |
| Workspace menu > Manufacture | `show_workspace` `manufacture` |
| Workspace menu > Animation | `show_workspace` `animation` |
| Workspace menu > Drawing (a drawing; From Design) | `show_workspace` `drawing` (`drawing`); `create_drawing` makes one |
| The DESIGN tabs SOLID, SURFACE, MESH, SHEET METAL, PLASTIC, UTILITIES | `show_workspace` `design`, `tab` |
| The SIMULATION tabs SETUP, RESULTS | `show_workspace` `simulation`, `tab` `setup` / `results` |
| The FLAT PATTERN tab (a flat pattern open) | `show_workspace` `flat_pattern` (`flat_pattern` makes one) |
| UTILITIES > AI > AI (the panel), Add an AI App, AI Chat, AI Activity | no tool: the person's own controls of AI apps (an AI must not switch itself on or add apps) |
| UTILITIES > AI > Rebuild with Timeline (AI)... | `start_rebuild` |
| UTILITIES > AI > Compare with Reference | `compare_to_reference` |
| UTILITIES > AI > Finish Rebuild | `finish_rebuild` |
| UTILITIES > AI > Stop Rebuild... | `delete_step` of the reference (the handbook says so) |
| UTILITIES > ADD-INS > Scripts and Add-Ins, Add-on Manager | no tool: there is no tool that runs code (an AI app must not run scripts) |
| UTILITIES > FREECAD > FreeCAD Tools | no tool: FreeCAD's own workbenches are outside Fission 180's behaviour |
| UTILITIES > UTILITY > Preferences, Project and Recovery Settings, Recover Documents, Fission 180 Diagnostics, Report a Problem | no tool: the person's own settings and reports |
| UTILITIES > UTILITY > Save As | `save_as` |
| UTILITIES > UTILITY > Version History | open: no tool lists or restores a design's versions yet (`save` makes a version) |
| UTILITIES > UTILITY > Command Search | no tool: `list_tools` with `goal` is the AI's search |
