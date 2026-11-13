You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: the AI works fast, and the window stays alive (builder ai-speed, branch `sf/ai-speed`)

Luca (2026-11-13): with Claude working through MCP, "even Fission itself becomes unresponsive. I
have to wait a long time for it to finally respond, and by the time it's back, it's really laggy
and becomes unresponsive again." Measured on his design (a rebuild of a 3,209-face mesh solid)
with the window up: describe_reference 220 s (fixed in 4.0.3: no defeaturing above 1,500
faces, now 15 s), compare_to_reference 13 s, check_design 10 s, inspect_design 7 s. Every AI call
runs on the window's thread (`ai/bridge.py` `_pump`), so the window is frozen meanwhile; 4.0.3
already drops calls nobody waits for and answers "busy" after 20 s.

### What to build
1. **A benchmark** (`Fission180Tests/headless/ai_speed_bench.py`, run by `run_tests.sh` with an
   option of its own, not in `base`): every read-only tool and the common changing tools on three
   big designs made by the test: a mesh-derived solid of about 3,000 faces with a rebuild started
   (Relic-like: a plate with a grid of small round dots, tessellated, converted), a B-rep part of
   about 2,000 faces (patterns of holes and fillets), and an assembly of about 100 components with
   joints. Seconds per tool, written to a report; the slowest named.
2. **Make the slow ones fast**: target under 2 s for inspect / query / check / compare on these
   designs, profile (cProfile) and fix the causes (caching per document state, avoiding repeated
   `shape.Faces` on big shapes (0.1 s per call on 3,000 faces), O(n^2) matching, needless
   booleans), never by returning less. Where a call is inherently long, keep it honest.
3. **The window stays alive during a long call**: a safe way for long Python work on the window's
   thread to let the window repaint and show "AI: working on <tool> (12 s)" with a Stop button
   (AI panel / status bar), without letting a click change the design mid-call and without timers
   (autosave, the bridge's own pump, others) running into a half-made change. Design it
   carefully, write down every re-entrancy risk you checked, and test it. Stop ends the call at
   the next safe point with an honest answer ("stopped by the person; nothing was changed" or what
   was done). On Windows a window that pumps no messages for 5 s is marked "Not responding": the
   design must avoid that for long Python loops (one long OpenCASCADE call cannot be split; say so).
4. **The connector's side** (`fission180_mcp.py`): progress notifications (MCP
   `notifications/progress`) for long calls where the AI app asked for them, so the app shows the
   call is alive; check what Claude Desktop / Claude Code do with them (WebSearch, cite).

### Proof
The benchmark's before / after table in your session log; unit tests for every pure part; a GUI
scenario (`ai_speed_alive.py`) where a long call runs through the real MCP server and bridge, the
window repaints and shows the working line, a click does not change the design, Stop works, and
autosave does not save mid-call; the existing `ai_bridge`, `ai_bridge_busy`, `ai_agent_e2e`,
`rebuild_*` scenarios and the headless rebuild / recognize runs still pass.
