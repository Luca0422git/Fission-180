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

## Wave 8 coverage: drawing

Builder ai-drawing (2026-11-13; brief `docs/fission180/dev/briefs/ai-drawing.md`). Every
command of the DRAWING tab (`ribbon_config.DRAWING_*`), File > New Drawing and the sheet bar
reach an AI tool that runs the code its dialog runs (`fission180/ai/actions/drawing_actions.py`
on `drawing.py`, `drawing_annot.py`, `drawing_tools.py`, `drawing_sheets.py`,
`drawing_breakout.py`, `drawing_exploded.py`, `drawing_export.py`, `flatpattern_drawing.py`);
the six tools of before keep their names and argument shapes (`catalog/drawing_tools.py`, moved
from `history_tools.py`). An AI checks a drawing without a picture: `get_drawing` lists every
sheet, view (scale, place, size, what it shows, section line and depth, break, breakout,
storyboard), dimension (type, value, the text written, what it measures), annotation, balloon,
table row and centre mark; with `picture` it returns a PNG of the sheet drawn from its DXF, with
or without the window (`fission180/ai/drawing_picture.py`: Fission 180's own stroke font).

### Behaviour (what Fusion does; drawing commands themselves: `drawings.md`)

| # | Fusion | Source |
|---|---|---|
| 1 | The commands, their options and clicks are the DRAWING workspace's (drawings.md rows 1-28 and its Part 3) | Autodesk, Forum (see drawings.md) |
| 2 | Fusion's own API reaches drawings only partly and in preview (creating a drawing, some views; no sheets, few annotations): a script cannot make a full drawing | Autodesk: Fusion API "DrawingDimensions Object Preview", "CreateDrawingInput Object Preview", "Views Object Preview"; Forum: "API Drawing Sheet Implementation" (many requests to expand the Drawing API, a slow process) |
| 3 | Fusion's Drawing Automation (Auto Dimensions, automated views, Autodesk Assistant) makes views and dimensions by itself; Automation Preferences set the views' style and automated centre marks | Autodesk blog "AI drawing automation in Autodesk Fusion", "From 3D Model to Manufacturing Drawing: Automate Documentation with Autodesk Assistant"; Autodesk "Automation preferences reference" (DWG-REF-AUTO-PREFERENCES) |
| 4 | An outside AI app driving every drawing command | none: beyond Fusion (Fusion's assistant is Autodesk's own) |
| 5 | Where a person drops a view, the paper is free; projected views sit beside their parent on its axes, a section beside its cut line | Guess (what every Fusion tutorial shows; drawings.md rows 8, 10) |

### Ribbon command -> tool (kind)

| Ribbon | Command | Tool (kind / arguments) |
|---|---|---|
| File | New Drawing > From Design | `create_drawing` (bodies, contents full_assembly / visible_only, flat_pattern, standard, sheet, units, title_block, automatic or base_view + projected) |
| File | New Drawing > From Animation | `create_drawing` storyboard (with automatic: every view exploded) |
| CREATE | Base View | `add_drawing_view` base (orientation, scale, style, bodies / flat_pattern) |
| CREATE | Projected View | `add_drawing_view` projected (parent, direction) |
| CREATE | Section View | `add_drawing_view` section (parent, line of 2+ points: straight, half, offset, aligned; side; depth_mode / depth) |
| CREATE | Detail View | `add_drawing_view` detail (parent, center, radius, scale) |
| CREATE | Break View | `add_drawing_view` break (parent, start, end, gap) |
| CREATE | Breakout Section View | `add_drawing_view` breakout (parent, boundary, depth / through_all) |
| CREATE | Exploded View | `add_drawing_view` exploded (storyboard, default the front one) |
| MODIFY | Edit View (double-click a view) | `edit_drawing_view` (orientation, style, tangent_edges, scale, label / show_label, center_marks, storyboard / Model, section depth_mode / depth / hatch, a break's gap, a breakout's depth / through_all / remove_breakout) |
| MODIFY | Title Block (double-click it) | `edit_title_block` values |
| MODIFY | Move | `modify_drawing` move (items, by or to) |
| MODIFY | Rotate | `modify_drawing` rotate (items, angle) |
| MODIFY | Delete (and the browser's Delete of a drawing) | `modify_drawing` delete (items; a drawing's id: the whole drawing) |
| GEOMETRY | Centerline | `add_drawing_geometry` centerline |
| GEOMETRY | Center Mark | `add_drawing_geometry` center_mark (picks, or every circle); also `add_drawing_annotation` center_marks (kept) |
| GEOMETRY | Center Mark Pattern | `add_drawing_geometry` center_mark_pattern |
| GEOMETRY | Edge Extension | `add_drawing_geometry` edge_extension |
| DIMENSIONS | Dimension | `add_drawing_dimension` (no type: inferred from the picks) |
| DIMENSIONS | Linear / Aligned / Angular / Radius / Diameter Dimension | `add_drawing_dimension` type linear / aligned / angular / radius / diameter |
| DIMENSIONS | Arc Length Dimension | `add_drawing_dimension` type arc_length |
| DIMENSIONS | Ordinate Dimension | `add_drawing_dimension` type ordinate (origin, picks, axis x / y / both, at) |
| DIMENSIONS | Baseline / Chain Dimension | `add_drawing_dimension` type baseline / chain (from, picks) |
| DIMENSIONS | Edit Dimension (double-click a dimension) | `edit_drawing_dimension` (override, prefix, suffix, precision, tolerance, upper, lower, fit, fit_member, fit_display, tol_precision, basic, reference, at) |
| TEXT | Text | `add_drawing_annotation` text |
| TEXT | Leader | `add_drawing_annotation` leader |
| TEXT | Bend Note | `add_drawing_annotation` bend_note |
| SYMBOLS | Surface Texture / Feature Control Frame / Datum Identifier | `add_drawing_symbol` surface_texture / feature_control_frame / datum_identifier |
| TABLES | Table, Parts List | `add_drawing_annotation` parts_list |
| TABLES | Bend Table | `add_drawing_annotation` bend_table |
| TABLES | Balloon | `add_drawing_annotation` balloon (view, component) |
| TABLES | Renumber / Align Balloons | `edit_balloons` renumber / align |
| EXPORT | Export PDF / DXF / DWG / CSV | `export_drawing` format pdf / dxf / dwg / csv (sheets all / current, table) |
| Sheet bar | +, New Sheet, Rename, Move Left / Right (drag), Delete Sheet | `drawing_sheet` add / rename / move / delete |
| Browser | Drawings: Rename | `rename` (existing tool) |
| Browser | Drawings: Open Drawing (its tab) | no tool: showing a tab changes nothing (a view helper); `get_drawing` picture shows the sheet |
| Sheet | Dragging a view, a dimension's text or a symbol | `modify_drawing` move |

No command of the DRAWING tab is without a tool.

### Tools (seconds measured headless on 4 CPUs shared by six builders)

The big case: an assembly of 15 plates 104 x 104 x 10 with 64 holes each (1,050 faces),
exploded by a storyboard, on an A2 sheet. TechDraw's hidden-line removal is the cost of every
view; with the window it runs in TechDraw's threads and the tools wait for it with the window
drawing meanwhile (`_idle`), so the next call finds the view's lines.

| Tool | What | Plate (s) | Big case (s) |
|---|---|---|---|
| `create_drawing` | a drawing, its views laid out by their parts' sizes (each view drawn once) at the largest scale that fits, or Fusion's automatic block | 0.1 | 19 (base + 2 projected), 41 - 65 (automatic, 4 views) |
| `add_drawing_view` | base / projected / section / detail / break / breakout / exploded; placed on free paper, beside its parent or along its cut line on the side with room; says when it overlaps or reaches off the sheet | 0.05 - 0.4 | detail 4 - 6, section 30, exploded 30 - 52, breakout 72 - 78 |
| `edit_drawing_view` | Edit View | 0.2 | 40 - 65 (a new scale: the view and its projected views drawn again) |
| `modify_drawing` | Move, Rotate, Delete | 0.03 | move 1.3 (was 92) |
| `edit_title_block` | Title Block | 0.01 | - |
| `drawing_sheet` | the sheet bar | 0.03 | - |
| `add_drawing_dimension` | every kind; the text placed outside the view, stacked, when no `at` | 0.01 | 1.4 - 1.9; 18 ordinates 1.6 - 2.8 |
| `edit_drawing_dimension` | Edit Dimension | 0.01 | - |
| `add_drawing_annotation` | text, leader, bend note, parts list, bend table, balloon, centre marks | 0.01 - 0.15 | parts list of 15 components 45 (each balloon drew its view again; fixed: 0.7 for 5 components) |
| `add_drawing_geometry` | centre marks, centre lines, patterns, edge extensions | 0.05 | 64 centre marks 3 - 5 |
| `add_drawing_symbol` | surface texture, feature control frame, datum | 0.01 | - |
| `edit_balloons` | Renumber, Align Balloons | 0.01 | - |
| `get_drawing` | everything back; `edges` (one `view`'s); `picture` | 0.01; picture 0.4 | 0.1; edges 2.2 - 2.6 (510 kB: give `view`); picture 12 - 15 (A2, 1200 px) |
| `export_drawing` | PDF (window), DXF, DWG (with a converter), CSV | 0.1 | DXF 7.6 - 11; CSV 0.01 |

Found on the way and fixed: a section view took 3 s on a plate with two holes and more than
10 minutes on the big case (the window stopped all that time; a person's Section View pays it
after OK too): `drawing_depth._covered` measured each point against the whole compound of
lines with `distToShape` (20 ms a point); the lines are now sorted into a grid and a point is
measured to the few near it, straight ones by plain sums (`drawing_depth._Near`, the same lines
switched off): 0.4 s, 30 s on the big case. Setting a view's X or Y made TechDraw work out its
lines again at the next recompute: a Move of the big case's base view took 92 s (its projected
views follow it), the AI's layout drew each view twice; `drawing.set_place` moves a view and
marks it up to date (Move, `keep_aligned`, the AI): 1.3 s. A balloon touched its view the same
way: the parts list of the big case took 45 s. A flat pattern's bend table was not in the DXF (nor in the picture);
two bends with their middles one above the other (a tray's front and back) put their
identifiers on one another; a projected view of a first-angle drawing could be placed off
the sheet (fixed fractions of the sheet), a section on its parent (a cut line's normal was
not the default side); Create Drawing's Automatic and the AI share `drawing.add_automatic_views`.

### Proofs

- Headless runner block `Fission180Tests/headless/drawing_tools.py` (124 calls: a part, an
  assembly with a storyboard, a sheet metal tray; every tool and kind, each answer checked on
  the drawing, each change one undo step named "AI: ...", the refusals in words).
- GUI scenarios through the real MCP server and the bridge (`Fission180Tests/gui/ai_drawing_steps.py`):
  `ai_drawing_part` (67 checks), `ai_drawing_assembly` (45), `ai_drawing_sheetmetal` (33),
  checked with `get_drawing`, never with pixels.
- Unit tests `test_ai_drawing_tools.py` (19: the rules, the lists against the drawing code's,
  the placements, the picture); reference examples of every new tool
  (`Fission180Tests/docs/tool_examples.py`); recipes `part-drawing.md`, `assembly-drawing.md`,
  `sheet-metal-drawing.md`, every call run by the docs runner.

### Not built (and why)

| Fusion | Why |
|---|---|
| Drawing Automation's Auto Dimensions (Fusion dimensions a view by itself) | Not a command of Fission 180's ribbon; the AI dimensions with `add_drawing_dimension` from `get_drawing`'s elements (recipe part-drawing.md) |
| Opening a drawing's tab from the AI | A view helper: nothing changes; the person opens it in the browser, the AI looks with `get_drawing` picture |
| Sheet size per sheet, templates | Not built in the drawing workspace either (drawings.md, Known gaps) |
| The picture's text in the sheet's own font, every character | The picture uses Fission 180's stroke font (capitals, digits, the drawing symbols; other characters as a box): it is for checking, the PDF is the drawing |
