# Wave 8 (2026-11-13): an AI that can use all of Fission 180, efficiently. Rules for every builder

Luca (the owner, a beginner who only tests) had Claude rebuild a part from a mesh ("Relic", an
STL of 8,486 triangles) through Fission 180's AI connector. Claude first refused to turn the mesh
into a regular solid; pushed, it tried to copy every polygon as features. In another file Luca
used the MESH tab's **Convert Mesh** himself and got a good solid in a fraction of the time.
Fission 180 also froze for minutes on the AI's calls (fixed in 0.1.0-beta.4.0.3, see below).
Luca (2026-11-13):

> "Claude needs access to ALL the tools, and it should be able to work efficiently, not
> stupidly. It needs access to the surface tools, mesh tools, sheet metal, plastic AND separate
> workspaces. I want it to be able to simulate, manufacture, animate and draw. It needs to be
> able to ask the right questions before starting, and it needs to be able to make decisions on
> what tools to use in a responsible and efficient way."

So: **every command of the ribbon that does something to a design, a drawing, a study, a CAM
setup or an animation must be reachable by an AI tool**, with the same code the dialog uses, and
the AI must be told (by the tools' own answers and by the documentation it reads) how to pick
the right tool, what to ask the person first, and what is fast or slow. Pure selection and view
helpers (Window / Freeform / Paint Selection, Select Other, Component Drag) need no tool.

The release this builds on is **0.1.0-beta.4.0.3** (committed on `develop` here, not pushed:
long AI calls no longer pile work behind them; describe_reference skips OpenCASCADE's
defeaturing on parts of more than 1,500 faces). The merger sets the version.

Read first, in this order: `CLAUDE.md`, `docs/fission180/dev/briefs/common.md` (every rule there
applies unless this file says otherwise), this file, your own brief
(`docs/fission180/dev/briefs/ai-<area>.md`), `docs/fission180/dev/feature-guide.md`,
`docs/fission180/dev/gui-tests.md`, `docs/fission180/parity/ai.md` (the AI connector, to the
end), `fission180/ai/catalog/__init__.py`, `registry.py` and `kit.py` (how a tool is defined and
registered), one tool file of your area and its actions / ops (how an action answers),
`fission180/ai/executor.py`, `Fission180Tests/headless/runner.py` (every tool once) and
`agent_e2e.py` (an agent through MCP), `Fission180Tests/unit/test_ai_catalog.py`, and
`src/Mod/Fission180/docs/ai/` (handbook, recipes, troubleshooting: what an AI reads).
`MEMORY.md` is 8,600 lines: `grep` it for your files, do not read it whole.

## How a tool is made here (keep to it)

- A tool = a catalogue entry (name, title, category, ribbon path, description, JSON schema,
  examples, read-only / changes-design / writes-files flags, availability) + an action or op
  that runs **the same code as the ribbon command's dialog** (never a second implementation
  that can drift). A changing call is one undo step named "AI: <what>". Wrong arguments and
  impossible requests answer with a plain sentence that says what to do instead.
- Names are permanent once released: pick them with care (verb_noun or the ribbon's word,
  lower case, like the existing ones). Prefer one tool with a `kind` for a ribbon group whose
  commands share arguments (as `surface`, `cam_operation`, `add_load` do) over ten tools; a
  person's mental model is the ribbon, so the description lists the ribbon names it covers.
- Descriptions are read by the model on every turn: say what it does, when to use it and when
  NOT (and which tool instead), the arguments' units, and how long it takes on big parts if it
  can be slow. No filler. Keep each under about 900 characters; details go to docs_read pages.
- Answers carry numbers the AI can check (volumes, counts, ids of what was made) and, where the
  next step is obvious, say it ("Next: convert_mesh with method prismatic").
- Everything an AI does goes through the bridge on Fission 180's window thread: a call blocks
  the window while it runs. **Measure** every tool you add on a realistic big case and write the
  seconds in your parity doc; anything over 5 s gets a note in its description and, where it can,
  a cheaper `detail` level.
- Every new tool: a case in `Fission180Tests/headless/runner.py` (every tool once, in your own
  block), unit tests for its pure parts, its schema in the catalogue tests (they run by
  themselves), and at least one GUI scenario that calls it **through the real MCP server and the
  bridge** like an AI app does (copy the `Mcp` class pattern of `ai_agent_e2e.py`), checking the
  result on the model.
- Coverage: add a table to `docs/fission180/parity/ai.md`, section "## Wave 8 coverage: <your
  area>": every ribbon command of your area -> the tool (and kind) that reaches it, or "no tool:
  <why>" (selection helpers only). The merger checks the tables against `ribbon_config.py`.

## Builders and what each owns

Only the owner edits a file. Six builders run at the same time.

| Builder | Branch | Owns |
|---|---|---|
| ai-mesh | `sf/ai-mesh` | new `fission180/ai/catalog/mesh_tools.py`, `ai/actions/mesh_actions.py`, `ai/ops/mesh_ops.py`; `ai/catalog/rebuild_tools.py`, `ai/actions/rebuild_actions.py` (the AI side of rebuilds of meshes); `mesh*.py`, `insert.py` mesh functions, `recognize_mesh.py` (smallest changes, only what the tools need); `docs/ai/recipes/mesh-to-solid.md` (new), `docs/ai/recipes/reverse-engineer.md` (its mesh parts) |
| ai-design | `sf/ai-design` | `ai/catalog/create_tools.py`, `modify_tools.py`, `sketch_tools.py`, `more_tools.py` (surface, construct, assemble, insert), new `ai/catalog/design2_tools.py` + `ai/actions/design2_actions.py` + `ai/ops/design2_ops.py` if you need room; `ai/actions/assemble_actions.py`, `sketch_actions.py`, `view_actions.py`; the existing `ai/ops/*` of those areas; new `ai/actions/analysis_actions.py` (INSPECT's analyses); design recipes in `docs/ai/recipes/` you add |
| ai-drawing | `sf/ai-drawing` | `ai/actions/drawing_actions.py`, the drawing tools in `ai/catalog/history_tools.py` (only those entries), new `ai/catalog/drawing_tools.py` if you move or add them; `docs/ai/recipes/` drawing recipes |
| ai-workspaces | `sf/ai-workspaces` | `ai/catalog/simulate_tools.py`, `manufacture_tools.py`, `animation_tools.py`, `sheetmetal_tools.py`, `plastic_tools.py`; their `ai/actions/*` and `ai/ops/*`; new tools for UTILITIES > MAKE (3D Print, Export Everything); recipes for those workspaces |
| ai-behaviour | `sf/ai-behaviour` | `ai/catalog/__init__.py` (all but each builder's own registration lines), `kit.py` shared texts, `ai/mcp_core.py`, `ai/mcp_resources.py`, `ai/docs_core.py`, `ai/chat_core.py` (the chat's system prompt), new `fission180/ai/approach_core.py` + its tool, the workspace tool, `docs/ai/handbook.md`, `docs/ai/README.md`, `docs/ai/recipes/index.md`, `docs/ai/troubleshooting.md` |
| ai-speed | `sf/ai-speed` | `ai/bridge.py`, `ai/bridge_core.py`, `ai/executor.py`, `ai/fission180_mcp.py`, `ai/headless.py`, `ai/geometry_facts.py`, `ai/actions/inspect_actions.py`, `ai/actions/verify_actions.py`, `ai/ops/inspect_ops.py`, `rebuild.py`, `rebuild_core.py`, `recognize*.py` (all but `recognize_mesh.py`), `ai_ui.py`, `ai_panel_ui.py` (the "working" display) |

- **Registering a tool** (`ai/catalog/__init__.py` imports, `CATEGORIES`, the tool order,
  `NEEDS`): add only your own lines, each in a block that starts with a comment naming your
  builder (`# wave 8, ai-mesh`). ai-behaviour owns the rest of that file and may reorder blocks
  at the end; tell it (in your report) what you added.
- **`Fission180Tests/headless/runner.py`, `test_ai_catalog.py`, `docs/fission180/parity/ai.md`:**
  shared; add your own blocks only, never reformat.
- **A file of another builder:** smallest possible change, listed in your report under "Shared
  files touched" with the reason. Worktrees share one repository: you may `git merge` a sibling's
  `sf/ai-<area>` branch into yours when you need its committed code. Never commit to it.
- **Generated docs** (`src/Mod/Fission180/docs/ai/tools.md`, `docs/ai/reference/*`,
  `docs/fission180/parity-checklist.md`): regenerate last, in a commit of their own
  (`python3 tools/fission180/make_ai_docs.py`, `python3 tools/fission180/parity.py`); the merger
  regenerates them again.
- **Do not edit** `MEMORY.md`, `CHANGELOG.md`, `docs/fission180/known-issues.md`, `VERSION`,
  `README.md`. Your session log: `docs/fission180/sessions/ai-<area>.md` (what you found, what you
  built, measurements, FreeCAD traps, gaps), ending with "## Changelog lines" (one plain sentence
  per change, for a beginner) and "## Known issues".
- Copy Fusion's behaviour, never its assets, wording or code. Every log line starts
  `[Fission 180]`; no exception may escape a command, timer or handler.

## Machine, tests, time

- FreeCAD 1.1.4 is at `/home/user/Fission-180/.fission180-cache/freecad` (`--freecad`; do not
  download another). Your own `--out` folder inside your worktree.
- 4 CPUs and 15 GB shared by six builders: **one scenario at a time**, never the whole suite,
  never `--only base` (the merger runs it). A scenario that times out under load is re-run alone
  before you conclude anything. Kill only your own processes (match your `--out` path).
- GitHub's 3D view is 1538 x 770, this sandbox's 1538 x 769 (gui-tests.md, fix-7): a scenario
  that clicks into the 3D view is also run once in a throwaway copy with the main window 1 px
  taller before you call it done.
- Before finishing: unit tests (`tools/fission180/run_tests.sh --only unit`, never plain
  unittest: it skips the FreeCAD-backed tests), the headless runner (`--only headless`), golden
  models (`--only golden`) if you touched geometry code, each of your scenarios, and every older
  scenario that uses the files you changed (one at a time). Re-read your whole diff adversarially.
- Lint: `/root/.local/bin/black -l 100 <files>`,
  `/root/.local/bin/flake8 --max-line-length=100 --extend-ignore=E203,E741 <files>`.
- Work only in your worktree, on your branch `sf/ai-<area>` (create it where your worktree
  starts; if `git log` there does not show the commit of this brief, `git merge develop` first).
  Commit working increments at least every hour, most certain first. NEVER push. NEVER
  `git stash`. Do not touch other worktrees. Never end your turn while a test run of yours runs.

## Your final message (the report the merger reads)

Branch and commits; the coverage table of your area (ribbon command -> tool / kind, or why
none); the tools added or changed (name, one line, measured seconds on a big case); proofs
(scenarios with check counts, PASS/FAIL; headless runner; unit; golden if run); shared files
touched; what is still open, with evidence; and a short plain-language "what changed for the
person" for Luca.
