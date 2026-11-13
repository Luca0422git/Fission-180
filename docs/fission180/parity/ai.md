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


## Wave 8 coverage: design (builder ai-design, 2026-11-13)

Luca (2026-11-13): "Claude needs access to ALL the tools, and it should be able to work
efficiently, not stupidly." Every command of the DESIGN workspace's SOLID, SURFACE and SKETCH
groups (CREATE, MODIFY, CONSTRUCT, INSPECT, INSERT, ASSEMBLE) now reaches an AI tool that
runs the code its dialog runs; the table at the end lists each command and its tool. Fusion
has no connector for outside AI apps at all (its own assistant is Autodesk's): **beyond
Fusion**. The behaviour each tool copies is the Fission 180 dialog's, itself specified (with
sources) in the area's parity doc: joints.md (as-built joints, joint origins, rigid groups,
motion links, contact sets, motion studies, positions), vex-assembly.md (Duplicate With
Joints), insert.md (Decal, Canvas, Insert SVG), derive in misc.md, direct.md (base features),
inspect.md / surface.md (the analyses), sketch.md (the SKETCH tools).

### What an AI is told, and what Fusion does (sources)

| Behaviour | Fission 180 for an AI | Source |
|---|---|---|
| As-built Joint joins two components where they stand; Joint moves the first onto the second | as_built_joint (nothing moves) / joint (the first moves); their descriptions send the AI to the other | Autodesk help "As-built Joint" / "Joint" |
| Rigid Group locks components together; one group instead of a rigid joint per pair | rigid_group | Autodesk help "Rigid Group" |
| Motion Link ties two joints' motions by two values (a gear pair, rack and pinion, a screw with Link with Same Joint) | motion_link, values [first, second], the same joint twice for a screw | Autodesk help "Motion Link" |
| Contact: Enable Contact Sets / Enable All Contact / Disable Contact, New Contact Set; parts stop where they touch | contact (mode, new_set); drive_joint now stops at the touch, as the Drive Joints dialog does (it went through before) | Autodesk help "Contact Sets"; Forum (all-contact slow on big assemblies) |
| Capture Position / Revert Position after components were moved | position (capture / revert) | Autodesk help "Capture Position" |
| Motion Study: joint values at steps 0..100, played back | motion_study answers where things stand at the steps asked, then puts the assembly back | Autodesk help "Motion Study" |
| Duplicate With Joints copies a jointed part into more places | duplicate_with_joints, one place per copy | Autodesk help "Duplicate With Joints" |
| Decal: a picture on faces, follows them, no geometry | decal, sized by width; refuses a point off the face | Autodesk help "Decal" |
| Canvas: a reference image on a plane, calibrated | canvas, sized by width (the real size: calibration's result) | Autodesk help "Canvas", "Calibrate" |
| Insert SVG: curves into a sketch, centred, Z angle clockwise | insert_svg (SVG and DXF); its angle counter-clockwise for both (the dialog's Z Angle turns an SVG clockwise) | Autodesk help "Insert SVG" |
| Derive / Insert Derive: linked copies of another design's bodies, sketches, planes, parameters | derive (source: Insert Derive; into: Derive); list: true shows what there is | Autodesk help "Derive" |
| Base feature: direct edits inside a parametric design | base_feature start / finish; the bodies made in between become base features | Autodesk help "Base Feature" |
| Compute All recomputes the design, lists failures | compute_all | Autodesk help "Compute All" |
| INSPECT analyses colour the model | analysis answers numbers (draft classes per face, the tightest inner round, curvature, reach, crease / G1 edges, combs, isocurves) with refs; nothing is left in the design | Autodesk help "Draft Analysis", "Zebra Analysis", "Minimum Radius Analysis", ...; the numbers are Fission 180's (beyond Fusion) |
| Display Component Colors / Component Color Swatch / Cycle Component Color | component_colors (on, swatch, cycle); always answers each component's colour | Autodesk help "Display Component Colors" |
| User Coordinate System | coordinate_system (origin, axes, or attached to a face / plane / corner) | Autodesk help "User Coordinate System" (Guess: attachment modes are FreeCAD's) |
| Offset Face | press_pull offset_face: true (the same move, an Offset Face step) | Autodesk help "Offset Face" |
| Texture Map Controls | appearance texture_map | Autodesk help "Texture Map Controls" |
| SKETCH tools | sketch_draw / sketch_modify / sketch_pattern / sketch_project, each kind the tool's own build() | Autodesk help per tool (sketch.md) |

### How the tools run the dialogs' code

- ASSEMBLE: joints.py's create_as_built_joint, create_joint_origin, create_rigid_group,
  create_motion_link, set_contact_mode / create_contact_set, capture_position /
  revert_position, create_motion_study + study_pose (the dialog's playback),
  duplicate_joints.duplicate, each followed by what the dialog's OK does (solve, limits,
  rest value, baseline).
- INSERT: decal.make + set_options, insert.make_canvas + set_canvas_options, insert.read_curves
  / transformed_geometry / new_sketch / add_geometry, derive.read_source + derive.derive;
  in the window the decal's and canvas's view providers are attached as the dialogs do.
- SKETCH: each tool class of sketch_draw_tools.py, sketch_fillet_tool.py,
  sketch_chamfer_tool.py, sketch_offset_tool.py, sketch_mirror_tool.py,
  sketch_pattern_tool.py, sketch_move_tool.py is made without its window part (no
  `__init__`: no view, no panel) with the clicks and values its build() reads, and build()
  runs; values given become dimensions as typed values do. Extend / Break run
  sketch_build.extend_curve / break_curve; Project / Include / Intersect sketch.addExternal or
  sketch_external.project_across (another body); Project to Surface sketch_project.make;
  Isoparametric Curve surface_iso.make; Curvature and Unfix the constraint tools' own
  constrain / _unfix.
- INSPECT: the analysis dialogs' formulas (analysis_core.draft_angle / draft_class,
  concave_radius, reachable_points; surface_analysis's face normals and curvatures signed as
  face_mesh signs them) on a 6 x 6 grid of each curved face's parameters (a flat face: its
  normal); accessibility's obstacles meshed in one go (MeshPart) and each group of points
  tested only against the triangles in its column.

### Measured (seconds, this sandbox, 4 CPUs shared with five builders)

| Tool | Case | Seconds |
|---|---|---|
| analysis draft | a plate with 750 countersunk holes: 1,506 faces, 3,762 edges | 2.6 - 3.0 |
| analysis minimum_radius | the same | 1.4 - 2.3 |
| analysis curvature_map | the same | 1.3 - 1.9 |
| analysis zebra / environment_map | the same (one point per edge above 1,000 edges) | 4.0 |
| analysis accessibility | the same, 6,000 points against a 1/400 mesh | 12.4 - 13.7 |
| analysis curvature_comb | the same, 750 circular edges | 1.4 - 1.7 |
| analysis isocurve | the same, 25 faces | 1.5 - 2.1 |
| analysis draft, picture: true | the same; the picture is render's (software) | 24.6 - 30.8 |
| analysis (each kind) | the test parts (a box, a plate with a hole) | 0.01 - 1.3 |
| as_built_joint, rigid_group, motion_link, contact, position, joint_origin | the 6-component arm assembly | 0.01 - 0.34 each |
| duplicate_with_joints, motion_study (3 steps) | the same | 0.05, 0.04 |
| decal | a 30 mm label on a face with 64 holes (the decal is meshed over the whole face, twice: on its making and with its size, as in the dialog) | 12.9 (6 per build) |
| decal, canvas, insert_svg (5 curves), derive, coordinate_system, compute_all | small designs | 0.02 - 0.22 |
| compute_all, canvas, coordinate_system | a plate with 100 holes | 0.42, 0.02, 0.05 |
| sketch_project (project) | its top face: 104 curves | 0.12 |
| sketch_pattern (rectangular 10 x 10), sketch_modify (offset) | a circle | 0.70, 0.48 |
| insert_svg | a DXF of 101 curves | 0.88 |
| derive | the 100-hole plate's body | 0.19 |
| sketch_draw / modify / pattern / project | each kind on small sketches | 0.01 - 0.2 |

### Tests

- Headless: `Fission180Tests/headless/design_tools.py` (ASSEMBLY, INSERT, ANALYSIS, SKETCH blocks;
  run by runner.py after the other sessions): every new tool and kind, the refusals in words,
  and checks on the model with numbers computed by hand (joint values, slider travel 1 mm for
  10 degrees, the arm stopped by contact between -15 and -5 degrees, the canvas 100 x 50 mm,
  the decal 30 x 15 mm, the SVG's 2 closed areas, the derived 24000 mm3 body, draft classes
  1 / 1 / 4 / 0 on a box, the 4 mm hole as the tightest round, 1600 / 4926 mm2 reached, 8 G1
  edges on a rounded block, the incircle of a triangle, a slot's arcs...).
- GUI, through the real MCP server and the AI bridge like an AI app (`ai_design_steps.py`):
  `ai_design_assembly` (64 checks), `ai_design_insert` (48), `ai_design_analysis` (48),
  `ai_design_sketch` (70).
- Unit: `test_ai_catalog.DesignWorkspace` (every ribbon command of the area has a coverage row
  naming real tools; the SKETCH kinds are the tools' classes; the analysis kinds the dialogs').
- Documentation: a reference example per new tool (recorded), recipes
  `recipes/hinged-assembly.md` and `recipes/check-before-making.md` run by the docs runner.

### Every command of the area -> its tool

The same rows are `COVERAGE` in `fission180/ai/catalog/design2_tools.py` (checked against
`ribbon_config.py` by `test_ai_catalog`).

| Ribbon command | Tool (kind) |
|---|---|
| SOLID > CREATE > Create Sketch | create_sketch / create_curve_sketch |
| SOLID > CREATE > Derive | derive (into: new or a saved design) |
| SOLID > CREATE > Extrude | extrude |
| SOLID > CREATE > Revolve | revolve |
| SOLID > CREATE > Sweep | sweep |
| SOLID > CREATE > Loft | loft |
| SOLID > CREATE > Rib | rib |
| SOLID > CREATE > Web | web |
| SOLID > CREATE > Emboss | emboss |
| SOLID > CREATE > Text | create_sketch (face) + sketch_text |
| SOLID > CREATE > Hole | hole |
| SOLID > CREATE > Thread | thread |
| SOLID > CREATE > Box | primitive (box) |
| SOLID > CREATE > Cylinder | primitive (cylinder) |
| SOLID > CREATE > Sphere | primitive (sphere) |
| SOLID > CREATE > Torus | primitive (torus) |
| SOLID > CREATE > Coil | coil |
| SOLID > CREATE > Gear | gear |
| SOLID > CREATE > Pipe | pipe |
| SOLID > CREATE > Thicken | surface (thicken) |
| SOLID > CREATE > Boundary Fill | surface (boundary_fill) |
| SOLID > CREATE > Create Base Feature | base_feature (start) |
| SOLID > CREATE > Finish Base Feature | base_feature (finish) |
| SOLID > CREATE > Joint Origin | joint_origin |
| SOLID > CREATE > Rectangular Pattern | rectangular_pattern |
| SOLID > CREATE > Circular Pattern | circular_pattern |
| SOLID > CREATE > Pattern on Path | pattern_on_path |
| SOLID > CREATE > Mirror | mirror |
| SOLID > MODIFY > Press Pull | press_pull |
| SOLID > MODIFY > Fillet | fillet / fillet_sets / rule_fillet / full_round_fillet |
| SOLID > MODIFY > Chamfer | chamfer / fillet_sets (chamfer) |
| SOLID > MODIFY > Shell | shell |
| SOLID > MODIFY > Draft | draft |
| SOLID > MODIFY > Offset Face | press_pull (offset_face) |
| SOLID > MODIFY > Delete | delete_face / delete_bodies / delete_step |
| SOLID > MODIFY > Remove | remove_bodies |
| SOLID > MODIFY > Texture Map Controls | appearance (texture_map) |
| SOLID > MODIFY > Replace Face | replace_face |
| SOLID > MODIFY > Split Face | split_face |
| SOLID > MODIFY > Split Body | split_body |
| SOLID > MODIFY > Silhouette Split | silhouette_split |
| SOLID > MODIFY > Scale | scale |
| SOLID > MODIFY > Combine | combine |
| SOLID > MODIFY > Move/Copy | move_copy |
| SOLID > MODIFY > Align | align |
| SOLID > MODIFY > Physical Material | physical_material |
| SOLID > MODIFY > Appearance | appearance |
| SOLID > MODIFY > Manage Materials | list_materials (reading the libraries); physical_material / appearance assign from them; no tool for the person's favourites and own looks (their settings, not the design) |
| SOLID > MODIFY > Change Parameters | set_parameter / list_parameters / set_model_parameter / delete_parameter |
| SOLID > MODIFY > Compute All | compute_all |
| SOLID > CONSTRUCT > User Coordinate System | coordinate_system |
| SOLID > CONSTRUCT > Offset Plane | construct_plane (OffsetPlane) |
| SOLID > CONSTRUCT > Plane at Angle | construct_plane (PlaneAtAngle) |
| SOLID > CONSTRUCT > Tangent Plane | construct_plane (TangentPlane) |
| SOLID > CONSTRUCT > Midplane | construct_plane (Midplane) |
| SOLID > CONSTRUCT > Plane Tangent to Face at Point | construct_plane (PlaneAtPoint) |
| SOLID > CONSTRUCT > Plane Through Two Edges | construct_plane (PlaneTwoEdges) |
| SOLID > CONSTRUCT > Plane Through Three Points | construct_plane (PlaneThreePoints) |
| SOLID > CONSTRUCT > Plane Along Path | construct_plane (PlaneAlongPath) |
| SOLID > CONSTRUCT > Axis Through Cylinder/Cone/Torus | construct_axis (AxisCylinder) |
| SOLID > CONSTRUCT > Axis Perpendicular to Face at Point | construct_axis (AxisNormal) |
| SOLID > CONSTRUCT > Axis Through Two Planes | construct_axis (AxisTwoPlanes) |
| SOLID > CONSTRUCT > Axis Through Two Points | construct_axis (AxisTwoPoints) |
| SOLID > CONSTRUCT > Axis Through Edge | construct_axis (AxisEdge) |
| SOLID > CONSTRUCT > Point at Vertex | construct_point (PointVertex) |
| SOLID > CONSTRUCT > Point Through Two Edges | construct_point (PointTwoEdges) |
| SOLID > CONSTRUCT > Point Through Three Planes | construct_point (PointThreePlanes) |
| SOLID > CONSTRUCT > Point at Center of Circle/Sphere/Torus | construct_point (PointCenter) |
| SOLID > CONSTRUCT > Point at Edge and Plane | construct_point (PointEdgePlane) |
| SOLID > CONSTRUCT > Point Along Path | construct_point (PointAlongPath) |
| SOLID > INSPECT > Measure | measure / query_geometry |
| SOLID > INSPECT > Interference | interference |
| SOLID > INSPECT > Curvature Comb Analysis | analysis (curvature_comb) |
| SOLID > INSPECT > Zebra Analysis | analysis (zebra) |
| SOLID > INSPECT > Draft Analysis | analysis (draft) |
| SOLID > INSPECT > Curvature Map Analysis | analysis (curvature_map) |
| SOLID > INSPECT > Isocurve Analysis | analysis (isocurve) |
| SOLID > INSPECT > Accessibility Analysis | analysis (accessibility) |
| SOLID > INSPECT > Minimum Radius Analysis | analysis (minimum_radius) |
| SOLID > INSPECT > Environmental Map Analysis | analysis (environment_map) |
| SOLID > INSPECT > Section Analysis | section_analysis |
| SOLID > INSPECT > Center of Mass | center_of_mass |
| SOLID > INSPECT > Display Component Colors | component_colors (on) |
| SOLID > INSPECT > Component Color Swatch | component_colors (swatch) |
| SOLID > INSPECT > Properties | physical_properties |
| SOLID > INSERT > Decal | decal |
| SOLID > INSERT > Canvas | canvas |
| SOLID > INSERT > Insert SVG | insert_svg |
| SOLID > INSERT > Insert DXF | import_file (.dxf) / insert_svg (.dxf, placed) |
| SOLID > INSERT > Insert Mesh | import_file (.stl / .obj / .3mf) |
| SOLID > INSERT > Insert Component | import_file (.FCStd: a linked component) |
| SOLID > INSERT > Insert Derive | derive (source) |
| SOLID > INSERT > Insert STEP | import_file (.step / .iges) |
| SOLID > INSERT > Hardware... | insert_hardware |
| SOLID > INSERT > Insert Catalogue Part... | no tool: it opens a supplier's website in the person's browser; the STEP file they download comes in with import_file |
| SOLID > ASSEMBLE > New Component | new_component |
| SOLID > ASSEMBLE > Joint | joint |
| SOLID > ASSEMBLE > As-built Joint | as_built_joint |
| SOLID > ASSEMBLE > Joint Origin | joint_origin |
| SOLID > ASSEMBLE > Rigid Group | rigid_group |
| SOLID > ASSEMBLE > Duplicate With Joints | duplicate_with_joints |
| SOLID > ASSEMBLE > Drive Joints | drive_joint |
| SOLID > ASSEMBLE > Motion Link | motion_link |
| SOLID > ASSEMBLE > Enable Contact Sets | contact (mode sets) |
| SOLID > ASSEMBLE > Enable All Contact | contact (mode all) |
| SOLID > ASSEMBLE > Disable Contact | contact (mode off) |
| SOLID > ASSEMBLE > New Contact Set | contact (new_set) |
| SOLID > ASSEMBLE > Motion Study | motion_study |
| SOLID > ASSEMBLE > Capture Position | position (capture) |
| SOLID > ASSEMBLE > Revert Position | position (revert) |
| SURFACE > CREATE > New Component | new_component |
| SURFACE > CREATE > Create Sketch | create_sketch / create_curve_sketch |
| SURFACE > CREATE > Create Base Feature | base_feature (start) |
| SURFACE > CREATE > Derive | derive |
| SURFACE > CREATE > Extrude | surface (extrude) |
| SURFACE > CREATE > Revolve | surface (revolve) |
| SURFACE > CREATE > Sweep | surface (sweep) |
| SURFACE > CREATE > Loft | surface (loft) |
| SURFACE > CREATE > Patch | surface (patch) |
| SURFACE > CREATE > Ruled | surface (ruled) |
| SURFACE > CREATE > Offset | surface (offset) |
| SURFACE > CREATE > Thicken | surface (thicken) |
| SURFACE > CREATE > Boundary Fill | surface (boundary_fill) |
| SURFACE > CREATE > Rectangular Pattern | rectangular_pattern |
| SURFACE > CREATE > Circular Pattern | circular_pattern |
| SURFACE > CREATE > Pattern on Path | pattern_on_path |
| SURFACE > CREATE > Mirror | mirror |
| SURFACE > MODIFY > Replace Face | replace_face |
| SURFACE > MODIFY > Split Face | split_face |
| SURFACE > MODIFY > Split Body | split_body |
| SURFACE > MODIFY > Silhouette Split | silhouette_split |
| SURFACE > MODIFY > Scale | scale |
| SURFACE > MODIFY > Combine | combine |
| SURFACE > MODIFY > Move/Copy | move_copy |
| SURFACE > MODIFY > Align | align |
| SURFACE > MODIFY > Physical Material | physical_material |
| SURFACE > MODIFY > Appearance | appearance |
| SURFACE > MODIFY > Manage Materials | list_materials (reading the libraries); physical_material / appearance assign from them; no tool for the person's favourites and own looks (their settings, not the design) |
| SURFACE > MODIFY > Change Parameters | set_parameter / list_parameters / set_model_parameter / delete_parameter |
| SURFACE > MODIFY > Compute All | compute_all |
| SURFACE > MODIFY > Press Pull | surface_modify (press_pull) |
| SURFACE > MODIFY > Fillet | surface_modify (fillet) |
| SURFACE > MODIFY > Chamfer | surface_modify (chamfer) |
| SURFACE > MODIFY > Trim | surface (trim) |
| SURFACE > MODIFY > Untrim | surface (untrim) |
| SURFACE > MODIFY > Extend | surface (extend) |
| SURFACE > MODIFY > Stitch | surface (stitch) |
| SURFACE > MODIFY > Unstitch | surface (unstitch) |
| SURFACE > MODIFY > Reverse Normal | surface (reverse_normal) |
| SURFACE > MODIFY > Merge | surface_modify (merge) |
| SURFACE > MODIFY > Delete | surface_modify (delete_face) / delete_bodies |
| SKETCH > CREATE > Line | add_to_sketch (curves: line) / create_curve_sketch |
| SKETCH > CREATE > Midpoint Line | sketch_draw (midpoint_line) |
| SKETCH > CREATE > 2-Point Rectangle | create_sketch / add_to_sketch (rect) |
| SKETCH > CREATE > 3-Point Rectangle | sketch_draw (rectangle_3point) |
| SKETCH > CREATE > Center Rectangle | create_sketch / add_to_sketch (center_rect) |
| SKETCH > CREATE > Center Diameter Circle | create_sketch / add_to_sketch (circle) |
| SKETCH > CREATE > 2-Point Circle | sketch_draw (circle_2point) |
| SKETCH > CREATE > 3-Point Circle | sketch_draw (circle_3point) |
| SKETCH > CREATE > 2-Tangent Circle | sketch_draw (circle_2tangent) |
| SKETCH > CREATE > 3-Tangent Circle | sketch_draw (circle_3tangent) |
| SKETCH > CREATE > 3-Point Arc | sketch_draw (arc_3point) |
| SKETCH > CREATE > Center Point Arc | add_to_sketch (curves: arc) |
| SKETCH > CREATE > Tangent Arc | sketch_draw (tangent_arc) |
| SKETCH > CREATE > Circumscribed Polygon | sketch_polygon |
| SKETCH > CREATE > Inscribed Polygon | sketch_polygon (circumscribed: false) |
| SKETCH > CREATE > Edge Polygon | sketch_draw (edge_polygon) |
| SKETCH > CREATE > Ellipse | sketch_draw (ellipse) / add_to_sketch (ellipse) |
| SKETCH > CREATE > Center to Center Slot | sketch_draw (slot_center_to_center) |
| SKETCH > CREATE > Overall Slot | sketch_draw (slot_overall) |
| SKETCH > CREATE > Center Point Slot | sketch_draw (slot_center_point) |
| SKETCH > CREATE > Three Point Arc Slot | sketch_draw (arc_slot) |
| SKETCH > CREATE > Center Point Arc Slot | sketch_draw (arc_slot_center_point) |
| SKETCH > CREATE > Fit Point Spline | sketch_draw (fit_point_spline) |
| SKETCH > CREATE > Control Point Spline | sketch_draw (control_point_spline) |
| SKETCH > CREATE > Conic Curve | sketch_draw (conic) |
| SKETCH > CREATE > Point | add_to_sketch (curves: point) |
| SKETCH > CREATE > Text | sketch_text |
| SKETCH > CREATE > Mirror | sketch_pattern (mirror) |
| SKETCH > CREATE > Circular Pattern | sketch_pattern (circular) |
| SKETCH > CREATE > Rectangular Pattern | sketch_pattern (rectangular) |
| SKETCH > CREATE > Project | sketch_project (project) |
| SKETCH > CREATE > Intersect | sketch_project (intersect) |
| SKETCH > CREATE > Include 3D Geometry | sketch_project (include_3d) |
| SKETCH > CREATE > Project to Surface | sketch_project (project_to_surface) |
| SKETCH > CREATE > Isoparametric Curve | sketch_project (isoparametric) |
| SKETCH > CREATE > Sketch Dimension | sketch_dimension |
| SKETCH > MODIFY > Fillet | sketch_modify (fillet) |
| SKETCH > MODIFY > Chamfer | sketch_modify (chamfer) |
| SKETCH > MODIFY > Offset | sketch_modify (offset) |
| SKETCH > MODIFY > Trim | sketch_trim |
| SKETCH > MODIFY > Extend | sketch_modify (extend) |
| SKETCH > MODIFY > Break | sketch_modify (break) |
| SKETCH > MODIFY > Sketch Scale | scale (sketch) |
| SKETCH > MODIFY > Move/Copy | sketch_pattern (move_copy) |
| SKETCH > MODIFY > Change Parameters | set_parameter / set_sketch_dimension |
| SKETCH > CONSTRAINTS > Coincident | sketch_constraint (coincident) |
| SKETCH > CONSTRAINTS > Collinear | sketch_constraint (collinear) |
| SKETCH > CONSTRAINTS > Concentric | sketch_constraint (concentric) |
| SKETCH > CONSTRAINTS > Midpoint | sketch_constraint (midpoint) |
| SKETCH > CONSTRAINTS > Fix/Unfix | sketch_constraint (fix / unfix) |
| SKETCH > CONSTRAINTS > Parallel | sketch_constraint (parallel) |
| SKETCH > CONSTRAINTS > Perpendicular | sketch_constraint (perpendicular) |
| SKETCH > CONSTRAINTS > Horizontal/Vertical | sketch_constraint (horizontal / vertical) |
| SKETCH > CONSTRAINTS > Tangent | sketch_constraint (tangent) |
| SKETCH > CONSTRAINTS > Curvature | sketch_constraint (curvature) |
| SKETCH > CONSTRAINTS > Equal | sketch_constraint (equal) |
| SKETCH > CONSTRAINTS > Symmetry | sketch_constraint (symmetric) |
| SKETCH > FINISH SKETCH > Finish Sketch | no tool: the AI's sketch tools never leave a sketch open (each call draws and closes) |
| SKETCH > FINISH SKETCH > Toggle Construction | sketch_modify (toggle_construction) |
