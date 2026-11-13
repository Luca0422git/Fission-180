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
| Show a workspace | `show_workspace` (needs the window; not an undo step): design (and its tab), simulation (and SETUP / RESULTS; refused without a study: create_study first, as Fusion opens New Study there; RESULTS refused before a solve), manufacture, animation, drawing (the newest or one named), flat_pattern (the design's other workspaces left first). The workspace menu's own code (`enter_workspace` / `leave_workspace`, `drawing_ui.open_drawing`, `flatpattern_ui.enter`); refused while a command dialog is open. `inspect_design` and `get_design` say which workspace and tab are shown (`workspace`, null without the window). Every tool works from any workspace (a body made while SIMULATION shows). |
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

Unit: `test_ai_approach_core.py` (55 tests: 41 requests across every workspace, Relic's two,
a sheet metal bracket from nothing / a sheet metal body / a flat plate, a study with and
without its numbers and on a 3,000-face part, CNC, a lathe, print a part and a mesh, a part and
an assembly drawing, an exploded video, an animation of bodies, a hinge, a plastic enclosure,
fix, inspect, render, odd input; the search by goal; the repetition guard; the form),
`test_ai_mcp_core.py` (`AskPerson`, `Guard`, `Instructions`), `test_ai_mcp_server.py`
(`AskThroughTheApp`: the real server asks the app and gets the answer while it keeps reading).
Headless runner: `Fission180Tests/headless/approach_tools.py` (20 calls). Docs: the handbook's
new sections and troubleshooting's are run by the docs runner; reference examples for the
three tools. Scenario `ai_plan_approach` (81 checks, through the real MCP server and the
bridge: plans, the selection, every workspace, a flat pattern, busy, the form, the guard; the
72-check version also passed with the 3D view 770 px tall). Found on the way: Finish Flat
Pattern brought a drawing's tab in front of the 3D view (fixed in `flatpattern_ui.enter`).

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

## Wave 8 coverage: workspaces (SIMULATION, MANUFACTURE, ANIMATION, SHEET METAL, PLASTIC, UTILITIES > MAKE)

Builder ai-workspaces, 2026-11-13 (brief `docs/fission180/dev/briefs/ai-workspaces.md`). Luca:
"I want it to be able to simulate, manufacture, animate and draw." Every command of these tabs
that changes or measures something is reachable by a tool or a `kind`, through the workspaces'
own code; the display-only ones the AI also reaches (so the person sees what it looks at).
Session log: `docs/fission180/sessions/ai-workspaces.md`.

### Fusion's behaviour copied (sources)

| What | Fusion | Fission 180's AI tool | Source |
|---|---|---|---|
| Surface Probes | values on the outer surface where clicked; any number; follow the result shown | `study_probe on`: over picked faces / edges / corners / bodies, min / max (with where) / mean | Autodesk ([surface probes](https://help.autodesk.com/cloudhelp/ENU/Fusion-Simulate/files/SIM-SURFACE-PROBE-CONCEPT.htm)) |
| Point Probes | like surface probes, but can be moved inside the part | `study_probe points`: interpolated in the element the point is in | Autodesk ([point probes](https://help.autodesk.com/cloudhelp/ENU/Fusion-Simulate/files/SIM-POINT-PROBE-CONCEPT.htm)) |
| Slice Plane | cuts the model and hides what is in front, to see inside | `study_probe section` (the numbers on the cut), `show_study_results slice` (the display) | Autodesk ([inspect tools](https://help.autodesk.com/cloudhelp/ENU/Fusion-Simulate/files/SIM-RESULT-INSPECT-CONCEPT.htm)) |
| Results inspect menu | Surface Probes, Point Probes, Reaction Force, Slice Plane under INSPECT | study_probe, study_results reactions | Autodesk ([results tools course](https://autodesk.com/learn/ondemand/course/fusion360-simulation-applications-for-static-stress-analysis-professional/unit/W2TZxQi5gihEssk3isY3V)) |
| Stock comparison | Simulate's stock colorization "comparison": red where too much was removed (gouge), blue where stock is left | `cam_simulate` gouges (area, deepest, where, operation) and stock_left_on_model | Forum ([stock comparison](https://forums.autodesk.com/t5/fusion-manufacture-forum/how-to-use-cam-stock-simulation-comparison/td-p/8729081), [gouges](https://forums.autodesk.com/t5/fusion-manufacture-forum/simulation-not-showing-gouges/td-p/12550018)) |
| Collisions | red marks on the simulation timeline; Stop on collision | `cam_simulate` collisions (rapid moves into material; holder not checked) | Autodesk course ([simulate toolpaths](https://autodesk.com/learn/ondemand/course/fusion360-cam-2.5-axis-milling-cert-prep/unit/6Fkkn1acs0ElISWkLycZR)) |
| Setup Sheet | a page of the setup's tools and operations for the machinist | `cam_setup_sheet` (Fission 180's own sheet, setup_sheet_html) | Guess (no official page found; Fission 180's MANUFACTURE parity doc) |
| Auto Explode: All Levels | explodes every level down to the leaf parts; a selected assembly's subassemblies too | `anim_explode levels all` | Autodesk ([all levels](https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/ANI-EXPLODE-ALL-LEVELS.htm), [transform](https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/ANI-TRANSFORM.htm)) |
| Storyboard, scratch zone | a clean storyboard; actions are put at the playhead out of the scratch zone; reversing an explode gives an assembly | `at` (0 = scratch zone), anim_storyboard reverse | Autodesk ([explode activity](https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/GUID-CCBE4164-214A-4931-B7FB-DA4DC1F3B40B.htm), [animation deep-dive](https://www.autodesk.com/products/fusion-360/blog/fusion-360-animation-deep-dive/)) |
| VIEW | with View on, orbit / pan / zoom past the scratch zone is recorded as a View action | `anim_view`: a View action from a standard view or a direction, fitted, by numbers | Guess (Fission 180's ANIMATION parity doc; the camera row) |
| 3D Print | the bodies as a mesh to a print utility or a file | `print_part` (a slicer found on this computer, asked first; or a file) | Fission 180's insert-export parity doc |

### SIMULATION: SETUP tab

| Ribbon command | Tool (kind) |
|---|---|
| STUDY > New Simulation Study | `create_study` (`copy_of`: the browser's Clone Study) |
| SIMPLIFY > Simplify | no tool: greyed in Fission 180 (not built; a study uses the design as it is) |
| MATERIALS > Study Materials | `set_study_material` (and `study_setup` reads them) |
| MATERIALS > Manage Physical Materials | SOLID's Manage Materials: ai-design's `list_materials` / `physical_material` |
| CONSTRAINTS > Structural Constraints | `add_constraint` (fixed, pin, frictionless, displacement) |
| LOADS > Structural Loads | `add_load` (force, pressure, moment, bearing, remote_force) |
| LOADS > Toggle Gravity On/Off | `study_settings` (gravity, gravity_direction) |
| LOADS > Linear / Angular Global Load, Point Mass (Auto / Manual) | no tool: greyed in Fission 180 (not built) |
| CONTACTS > Automatic Contacts | `study_setup` (contact_tolerance: Generate's list with gaps) + `study_settings` contact_tolerance (OK keeps it) |
| CONTACTS > Manual Contacts, Bolt Connector, Rigid Body Connector | no tool: greyed in Fission 180 (not built) |
| CONTACTS > Contact Manager | `study_setup` (contacts, overlapping, touching only at an edge or corner) |
| DISPLAY > DOF View | `study_setup` (free_motions: how each piece could still move) |
| DISPLAY > Show Mesh | `study_mesh` (show) |
| MANAGE > Settings | `study_settings` |
| MANAGE > Local Mesh Control | `local_mesh_control`; changed / suppressed / deleted with `edit_study_item` |
| MANAGE > Load Case Attributes | `study_setup` (items: kind, values, what it is on, status) |
| SOLVE > Pre-check | `precheck_study` |
| SOLVE > Solve | `solve_study` (waits; says how long it took; Stop cancels it with ai-speed's safe points) |
| SOLVE > Generate Mesh | `study_mesh` |
| SOLVE > Job Status | no tool: the AI's solve and mesh wait for their job and answer its outcome and time; `study_results` says whether a study is solved and out of date |
| browser: study > Delete | `delete_study` |
| browser: constraint / load / mesh control > Edit, Suppress, Delete | `edit_study_item` |

### SIMULATION: RESULTS tab

| Ribbon command | Tool (kind) |
|---|---|
| RESULT TOOLS > Animate | `show_study_results` animate |
| RESULT TOOLS > Results Details | `study_results` (verdict, per body, extremes) |
| RESULT TOOLS > Convergence Plot | `study_results` convergence (after adaptive refinement) |
| RESULT TOOLS > Legend Min/Max | `show_study_results` legend_range |
| RESULT TOOLS > Compare | `show_study_results` compare |
| RESULT TOOLS > Report | `study_report` (pictures with the window) |
| DEFORMATION > Undeformed, Actual, Adjusted x 0.5, Adjusted, Adjusted x 2, Adjusted x 5 | `show_study_results` deformation |
| DISPLAY > Show Mesh, Undeformed Model, Loads and Constraints | `show_study_results` mesh, undeformed_model, loads |
| INSPECT > Surface Probes | `study_probe` on |
| INSPECT > Show Min/Max | `study_results` (min / max with where), `show_study_results` min_max |
| INSPECT > Reaction Force | `study_results` reactions |
| INSPECT > Slice Plane | `study_probe` section (numbers), `show_study_results` slice (display) |
| INSPECT > Point Probes | `study_probe` points |
| INSPECT > Iso-surface | `show_study_results` iso_surface |
| INSPECT > Solver Data | `study_results` solver, solve_seconds |
| INSPECT > Measure | `measure` |
| FINISH RESULTS > Finish Results | `show_study_results` finish |

### MANUFACTURE: MILLING tab

| Ribbon command | Tool (kind) |
|---|---|
| SETUP > New Setup | `cam_setup` (stock relative / fixed / solid / preceding; WCS orientation model / z_x / z_y / x_y, origin stock_point / model_point / model_origin / selected; post program, comment, wcs_offset G54-G59) |
| 2D > 2D Adaptive Clearing, 2D Pocket, Face, 2D Contour, Slot, Trace, Bore, Circular, Engrave, 2D Chamfer | `cam_operation` kind adaptive2d, pocket2d, face, contour2d, slot, trace, bore, circular, engrave, chamfer2d |
| 2D > Thread | no tool: greyed in Fission 180 (thread milling not built) |
| 3D > Adaptive Clearing, Pocket Clearing, Parallel, Contour | `cam_operation` kind adaptive3d, pocket3d, parallel, contour3d |
| 3D > Scallop, Pencil, Spiral, Radial | no tool: greyed (FreeCAD's CAM engine has no such strategy) |
| DRILLING > Drill | `cam_operation` kind drill |
| ACTIONS > Generate | `cam_generate` |
| ACTIONS > Simulate | `cam_simulate` (collisions, gouges, stock left on the part, per operation) |
| ACTIONS > Post Process | `cam_post` (grbl, linuxcnc, mach3_mach4, fanuc, marlin, centroid, smoothie, rrf, refactored_masso_g3; checked) |
| ACTIONS > Setup Sheet | `cam_setup_sheet` |
| MANAGE > Tool Library | `cam_tools` (read), `cam_tool_library` (add, edit, delete, copy, new_library, delete_library) |
| browser: setup / operation > Edit, Suppress, Delete; Setups | `cam_edit`, `cam_delete`, `cam_setups` |

### ANIMATION

| Ribbon command | Tool (kind) |
|---|---|
| STORYBOARD > New Storyboard (and a storyboard tab's Duplicate, Reverse, Rename, Delete) | `anim_storyboard` action new, duplicate, reverse, rename, delete, activate |
| TRANSFORM > Transform Components | `anim_transform` |
| TRANSFORM > Restore Home | `anim_restore_home` |
| TRANSFORM > Auto Explode: One Level / All Levels | `anim_explode` levels one / all |
| TRANSFORM > Manual Explode | `anim_manual_explode` |
| TRANSFORM > Show/Hide | `anim_show_hide` |
| ANNOTATION > Create Callout | `anim_callout` |
| VIEW > View | `anim_view` |
| PUBLISH > Publish Video | `anim_publish_video` (frame by frame with safe points) |
| ANIMATION TIMELINE: Edit Start/End, drag a bar, Delete; reading | `anim_action`; `anim_storyboards` |

### SHEET METAL and FLAT PATTERN

| Ribbon command | Tool (kind) |
|---|---|
| CREATE > Flange | `flange` (kind base, contour, edge) |
| CREATE > Lofted Flange, Bend, Hem, Join by Bend | `lofted_flange`, `bend`, `hem`, `join_by_bend` |
| CREATE > Create Flat Pattern | `flat_pattern` |
| CREATE > New Component, Create Sketch, Extrude, Hole, Pattern, Mirror, Derive | the SOLID tools (`new_component`, `create_sketch`, `extrude`, `hole`, `pattern`..., `mirror`; Derive: ai-design) |
| MODIFY > Fillet, Chamfer | `sheet_metal_fillet`, `sheet_metal_chamfer` |
| MODIFY > Unfold, Refold, Rip, Corner Closure, Convert to Sheet Metal | `unfold`, `refold`, `rip`, `corner_closure`, `convert_to_sheet_metal` |
| MODIFY > Sheet Metal Rules | `sheet_metal_rule` (new from a rule, edit, active; wave 8: `bodies` swaps a body's rule, `delete` removes a design rule). The person's own library rules on this computer: no tool (an AI does not change the person's library) |
| MODIFY > Press Pull, Combine, Replace Face, Split Face, Split Body, Move/Copy, Align, Delete, Physical Material, Appearance, Manage Materials, Change Parameters, Compute All | the SOLID tools of the same names (ai-design) |
| FLAT PATTERN > Export DXF | `export_flat_pattern` |
| FLAT PATTERN > Finish Flat Pattern | no tool: it leaves a display mode (the AI reads the flat pattern from flat_pattern / export_flat_pattern; ai-behaviour's workspace tool shows workspaces) |

### PLASTIC

| Ribbon command | Tool (kind) |
|---|---|
| SETUP > Assign Plastic Rule, Manage Plastic Rules | `plastic_rule` (rule; set edits the design's copy) |
| CREATE > Boss, Snap Fit, Lip, Rest | `boss` (and `boss_fastener`), `snap_fit`, `lip`, `rest` |
| CREATE > Extrude, Revolve, Sweep, Loft, Rib, Web, Emboss, Hole, Thread, Thicken, Mirror, Pattern | the SOLID tools |
| MODIFY > Rule Fillet | `rule_fillet` with the plastic rule's nominal_radius as radius (plastic_rule answers it) |
| MODIFY > Fillet, Chamfer, Shell, Draft, Scale, Combine, Offset Face, ... | the SOLID tools |
| INSPECT > Design Advice | `design_advice` |

### UTILITIES > MAKE

| Ribbon command | Tool |
|---|---|
| 3D Print | `print_part` (send_to file, slicer, prusaslicer, bambustudio, orcaslicer, cura; format, unit, refinement) |
| Export | `export` |
| Export Everything | `export_everything` |

### Tools added or changed, measured

Measured headless (FreeCAD 1.1.4, 4 shared CPUs under the load of ten builders): a 200 x 40 x 20
beam with 10 holes at mesh size 2.5 % (16,729 nodes; 23,152 with two fillets), six touching
boxes, a 200 x 150 x 12 plate with a pocket and 48 holes (four operations), 20 components, a
210 x 110 plate with 200 filleted holes (about 1,400 faces, 270,000 triangles).

| Tool | What | Seconds (big case) |
|---|---|---|
| `study_probe` | points / faces / section numbers | 10 points 0.45; 13 faces 2.1 (the exact distance per node took 12); a section 0.02 |
| `study_report` | the HTML report (pictures with the window) | 0.02 (0.8 with pictures, bracket) |
| `study_mesh` | Generate Mesh (+ Show Mesh) | 1.9 (16,729 nodes) |
| `study_setup` | Load Case Attributes, contacts, DOF View | 0.06; 0.13 with six bodies and a contact tolerance |
| `edit_study_item` | Edit / Suppress / Delete an item | 0.01 |
| `show_study_results` | the RESULTS display (window) | under 0.3 a call (bracket, 2,438 nodes) |
| `create_study` copy_of | Clone Study | 0.01 |
| `study_results` (+ Solver Data, convergence) | | 0.05 |
| `solve_study` (now says how long) | | 9.3 (16,729 nodes) |
| `cam_simulate` (+ gouges, stock left) | | 4.0 (4 operations, 48 holes) |
| `cam_setup_sheet` | Setup Sheet | 0.5 |
| `cam_tool_library` | Tool Library changes | 0.03 |
| `anim_view` | View action | 0.03 (20 components) |
| `anim_action` | timeline edits | 0.02 |
| `anim_publish_video` (safe points) | | about 1 (49 frames, 320 x 240) |
| `print_part` | 3D Print | 11 (Medium), 21 (High): the dialog's meshing and writing |
| `export_everything` | Export Everything | 23 to 29 |
| `sheet_metal_rule` bodies / delete | | 0.2 |

Tests: headless `Fission180Tests/headless/ai_workspaces.py` (105 calls, run by `runner.py`);
unit `test_ai_workspaces_core.py` (18); GUI scenarios through the real MCP server and the
bridge: `ai_workspace_simulate` (66 checks), `ai_workspace_manufacture` (45),
`ai_workspace_animation` (39), `ai_workspace_sheetmetal` (33), `ai_workspace_plastic` (36);
the reference examples of every new tool (`tool_examples.py`, `show_study_results` with the
window in `ai_docs_gui`); recipes `static-stress.md` (extended), `mill-pocketed-plate.md`,
`exploded-view-video.md`, `laser-cut-bracket.md`, `plastic-enclosure.md`, every call run by the
documentation runner.

## Wave 8 coverage: mesh

Builder ai-mesh, 2026-11-13 (brief `docs/fission180/dev/briefs/ai-mesh.md`). Luca gave Claude a
mesh body "Relic" (an STL of 8,486 triangles, a plate with a field of small round dots); it
refused to make it a solid, then copied polygons as sketch features, while MESH > Convert
Mesh did it by hand in seconds. Now every MESH tab command is reachable by a tool, with the
code its dialog runs; the rebuild of a mesh says plainly when it reads no plan and gives the
two honest routes. Session log: `docs/fission180/sessions/ai-mesh.md`.

### Fusion's behaviour copied (sources)

| What | Fusion | Fission 180's AI tool | Source |
|---|---|---|---|
| Convert Mesh methods | Faceted: one face per mesh face; Prismatic: for parts made with solid tools, face groups used to infer prismatic features; Organic: scans, a Fusion extension | `convert_mesh` method faceted / prismatic (flat faces merged; round areas stay facets: no surface fitting); organic refused by the schema (it does not exist here) | Autodesk ([Convert Mesh](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-CONVERT-TO-SOLID.htm), [convert a mesh to a solid](https://www.autodesk.com/products/fusion-360/blog/convert-mesh-to-solid-surface-body-fusion-360/)) |
| Operation Parametric / Base Feature | the converted body follows the mesh, or is made once | `operation` parametric / base_feature | Autodesk ([Convert Mesh](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-CONVERT-TO-SOLID.htm)) |
| Face groups before Prismatic | Generate Face Groups, Combine Face Groups and Direct Edit align groups to features; a failed conversion says to | `mesh_prepare` generate / create / combine face groups, `mesh_modify` direct_edit | Autodesk ([Mastering Mesh Conversion](https://www.autodesk.com/products/fusion-360/blog/generate-face-groups-fusion/), [Generate Face Groups](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-GENERATE-FACE-GROUPS.htm)) |
| Prismatic on organic shapes | does not work; repair a broken mesh first | inspect_mesh's advice: repair first; for domes / free-form, convert keeps facets and the rebuild says it reads no plan | Forum ([cannot convert](https://forums.autodesk.com/t5/fusion-design-validate-document/quot-cannot-convert-mesh-body-to-solid-or-surface-body-quot/m-p/10460309), [difficulty converting](https://forums.autodesk.com/t5/fusion-design-validate-document/difficulty-converting-mesh-to-solid-body/m-p/13239464/highlight/true)) |
| Big meshes | Convert warns above about 10,000 faces (slow) | `convert_mesh` says its time and refuses over about a minute unless `allow_slow`, with the reduce call that fits | Guess (Fission 180's insert parity doc: `insert.FACET_WARNING`) |
| The MESH tab's dialogs | Repair, Remesh, Reduce, Plane Cut, Shell, Smooth, Combine, Separate, Reverse Normal, Direct Edit, Erase and Fill, Delete Faces, Make Closed Mesh, face groups, Tessellate, Section Sketch | one step each, the dialog's values | `docs/fission180/parity/mesh.md` (its sources) |
| An AI connector | Fusion has none for outside AI apps | beyond Fusion | - |

### The MESH tab

| Ribbon command | Tool (kind) |
|---|---|
| CREATE > Insert Mesh | `import_file` (STL / OBJ / 3MF, unit) |
| CREATE > Tessellate | `tessellate` (refinement low / medium / high / custom, max_edge_length) |
| CREATE > Create Mesh Section Sketch | `mesh_section_sketch` (plane XY / XZ / YZ or a construction plane, distance) |
| PREPARE > Create Face Group | `mesh_prepare` kind create_face_group (faces) |
| PREPARE > Generate Face Groups | `mesh_prepare` kind generate_face_groups (method fast / accurate, angle, min_size, tolerance) |
| PREPARE > Combine Face Groups | `mesh_prepare` kind combine_face_groups (groups, or faces in them) |
| PREPARE > Repair | `mesh_prepare` kind repair (repair_type close_holes / stitch_and_remove / wrap / rebuild, rebuild_type, density, offset); its analysis: `inspect_mesh` |
| MODIFY > Remesh | `mesh_modify` kind remesh |
| MODIFY > Reduce | `mesh_modify` kind reduce (target tolerance / proportion / face_count) |
| MODIFY > Plane Cut | `mesh_modify` kind plane_cut (trim / split_body / split_faces, fill, flip, distance, angle_x, angle_y) |
| MODIFY > Shell | `mesh_modify` kind shell |
| MODIFY > Smooth | `mesh_modify` kind smooth (groups / faces) |
| MODIFY > Combine | `mesh_modify` kind combine (tools, join / cut / intersect / merge, keep_tools) |
| MODIFY > Separate | `mesh_modify` kind separate (mesh_shells / all_face_groups / select_face_groups, keep_body) |
| MODIFY > Reverse Normal | `mesh_modify` kind reverse_normal (groups / faces) |
| MODIFY > Direct Edit | `mesh_modify` kind direct_edit (edits: delete, erase_fill, group, reverse, move, smooth) |
| MODIFY > Erase and Fill | `mesh_modify` kind erase_and_fill (faces, fill, density) |
| MODIFY > Delete Faces | `mesh_modify` kind delete_faces (faces) |
| MODIFY > Make Closed Mesh | `mesh_prepare` kind make_closed |
| CONVERT > Convert Mesh | `convert_mesh` (method, operation, allow_slow) |
| Browser: Rebuild with Timeline (AI)... on a mesh | `start_rebuild`, `describe_reference`, `compare_to_reference`, `finish_rebuild` (rebuild_tools, mesh-aware since wave 8) |

Faces of a mesh are named by face group, points on its surface, a ray or a box (with an
optional facing filter), never by a triangle's number; they are kept as the dialogs keep a
click (the picked triangles' centres, or their face groups). The tools' answers carry the
triangles, size, closed or what is wrong, volume and, on a last line, the time ("Took about
2 s.").

### Speed

Every mesh tool on the Relic stand-in (a plate with a grid of 3 mm holes, as STL; the
sandbox's 4 CPUs shared by ten builders, so a person's PC is usually faster;
`Fission180Tests/headless/mesh_tools.py` `measure_speed`), seconds per call, each change
undone after it:

| Call | 876 triangles | 8,972 triangles | 47,612 triangles | 93,612 triangles |
|---|---|---|---|---|
| inspect_mesh | 0.01 | 0.17 | 0.84 | 2.26 |
| inspect_mesh groups | 0.01 | 0.14 | 1.02 | 2.69 |
| convert_mesh | 0.17 | 1.83 | 11 | 27 |
| convert_mesh faceted | 0.47 | 5.44 | 28 | 66 |
| mesh_prepare repair | 0.02 | 0.35 | 2.24 | 4.18 |
| mesh_prepare generate_face_groups | 0.01 | 0.12 | 0.68 | 1.12 |
| mesh_prepare create_face_group | 0.02 | 0.11 | 0.72 | 1.12 |
| mesh_prepare make_closed | 1.36 | 1.89 | 2.48 | 2.54 |
| mesh_modify remesh | 0.13 | 0.04 | 0.18 | 0.24 |
| mesh_modify reduce | 0.00 | 0.05 | 0.36 | 0.45 |
| mesh_modify plane_cut XY through the holes, fill minimal | 0.03 | 0.46 | 5.24 | 14 |
| mesh_modify plane_cut YZ, fill uniform | 0.44 | 0.10 | 1.98 | 0.55 |
| mesh_modify shell | 0.02 | 0.19 | 1.35 | 1.38 (refused) |
| mesh_modify smooth | 0.00 | 0.06 | 0.37 | 0.75 |
| mesh_modify reverse_normal | 0.00 | 0.05 | 0.29 | 0.59 |
| mesh_modify erase_and_fill | 0.02 | 0.20 | 1.40 | 3.08 |
| mesh_modify delete_faces | 0.01 | 0.09 | 0.64 | 1.40 |
| mesh_modify direct_edit | 0.01 | 0.11 | 0.81 | 1.55 |
| mesh_section_sketch | 0.00 | 0.02 | 0.15 | 0.25 |
| start_rebuild | 0.13 | 2.10 | - | - |
| describe_reference | 0.27 | 3.69 | - | - |

"(refused)": a 0.5 mm shell does not fit there (its inside wall would cross itself): the
refusal in words, in about a second.

Before wave 8 Convert Mesh sewed one face per triangle: 9,000 triangles 5.9 s, 76,000
4 min 40 s; Plane Cut through 425 holes 152 s (Minimal) and minutes (Uniform). A fillet of
four edges of the converted 9,000-triangle plate (2,326 faces): 11 to 15 s (OpenCASCADE).
describe_reference on the dome plate (8,812 triangles, no plan): 56 s and 1.47 million
characters before, 11 s and about 6,000 characters now; compare_to_reference of a
facet-copying rebuild against it: 336 s before, under a second now (the warning and the
volumes).

### Tests

Unit `test_mesh_ai.py` (28), `test_mesh_convert_freecad.py` (`headless/mesh_convert_check.py`:
the new conversion is the sewn one, a cut through 80 holes closed and quick); the headless
runner's block `headless/mesh_tools.py` (67 calls: every tool and kind, the repair route,
the rebuild of both stand-ins, the refusals); scenarios `ai_mesh_relic` and `ai_mesh_repair`
through the real MCP server and the bridge; recipe `recipes/mesh-to-solid.md` (46 calls run
by the documentation runner); the six tools' reference examples.

### Still open

- Fusion's Prismatic fits cylinders, cones and spheres to face groups; Fission 180's merges flat
  faces only (round areas stay facets): true round holes need the rebuild route.
- `edit_step` does not change a MESH step's values (undo and call again; the timeline's
  double-click opens its dialog).
- start_rebuild's 10,000-triangle limit for a mesh (rebuild.py) and its words date from the
  sewing conversion; 50,000 triangles now convert in about 11 s.
