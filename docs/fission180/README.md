# Fission 180: start here

Fission 180 is a fork (a copy we are allowed to change) of FreeCAD 1.1.4, being reshaped until it
works the way Fusion users expect (Fusion is Autodesk's trademark; Fission 180 is not affiliated with
Autodesk). The plan is in [feature-outline.md](feature-outline.md); progress
is tracked in [MEMORY.md](../../MEMORY.md).

## Releases

Releases (0.1.0-beta and later) follow the brief [dev/briefs/beta-release.md](dev/briefs/beta-release.md):
all work goes to `develop`; the `Release` branch only ever receives a tested `develop` commit, on
Luca's green light, and the tag `fission180-v<version>` on that commit starts the build that
publishes the GitHub release (section 1 of the brief has the exact steps). The user-facing side
is the repository's [README.md](../../README.md), the [CHANGELOG.md](../../CHANGELOG.md) (the
release notes are made from its newest section), [known-issues.md](known-issues.md),
[privacy.md](privacy.md) and [smartscreen.md](smartscreen.md) (the fixed "Windows protected your
PC" text, also in the README and in every release's notes). Screenshots for the README are made
by `tools/fission180/screenshots.sh`. `tools/fission180/check_links.py` checks the links in those
documents (it also runs as a unit test).

## Getting a Fission 180 build to test (Windows)

You never need to compile anything yourself. GitHub builds it:

1. On GitHub, open the repository, click **Actions**, then **Fission 180 build** in the left list.
2. Click **Run workflow**, pick `windows` (or `both`), and press the green button.
3. Wait. A full build takes a few hours (the C++ part of FreeCAD is large). Quick checks run
   first (about 10 minutes, including the test models on FreeCAD for Windows); when one fails,
   the run stops there instead of compiling for hours.
4. When the run is finished, open it and scroll to **Artifacts**. Two downloads:
   - `Fission180-Windows-installer-...`: GitHub wraps it in a .zip; inside is
     `Fission180_..._installer.exe`. Run it: it installs to `C:\Program Files\Fission180`, adds a
     Start menu entry (and a desktop icon if you tick it) and an uninstaller in Windows'
     "Installed apps". A FreeCAD on the same PC stays as it is (see "Compatibility" below).
   - `Fission180-Windows-portable-...`: a `.7z` inside. Unpack it (7-Zip) anywhere, for example
     `C:\Fission180`, and run `bin\Fission180.exe`. Nothing is installed or registered.
   The build is uploaded before its tests run, so it is there even when a test failed (the
   run then has a red cross). Then ask Claude what failed before relying on it: the same
   test models already passed on FreeCAD for Windows before compiling, so a failure here is
   usually in the compiled part, which a quick update cannot fix.
5. Fission 180 opens in its own interface (the Fission 180 workbench is the start workbench). The
   Start page is still FreeCAD's for now.

About cost: the repository is public (since 2026-10-10), and GitHub's standard build machines are
free for public repositories, so builds cost nothing. A full build still takes a few hours, so it
is started by hand (or by a `fission180-v*` tag) rather than on every change. The automatic test
run (**Fission 180 tests**) takes about 40 minutes (6 machines side by side, one of them Windows) and
runs on every push.

Linux: the same run uploads `Fission180-Linux-...` with an `.AppImage`: make it executable and
run it (`./Fission180_....AppImage`; `--appimage-extract` unpacks it when FUSE is missing).

## Compatibility: Fission 180 next to FreeCAD

Fission 180 is a separate program since the branding pass (2026-10-13, `core-patches.md` #8 to
#13). On one PC, Fission 180 and FreeCAD do not see each other:

| | Fission 180 | FreeCAD 1.1 |
|---|---|---|
| Program | `Fission180.exe`, `Fission180Cmd.exe` (Linux: `fission180`, `fission180cmd`) | `FreeCAD.exe` |
| Install folder (installer) | `C:\Program Files\Fission180` | `C:\Program Files\FreeCAD 1.1` |
| Settings, add-ons, macros | `%APPDATA%\Fission180` (Linux: `~/.config/Fission180`, `~/.local/share/Fission180`) | `%APPDATA%\FreeCAD` |
| Registry / uninstall entry | `Fission180` keys only | `FreeCAD` keys only |
| `.FCStd` double-click | Only if ticked in the installer (off by default) | Unchanged |
| Window title, About, splash | Fission 180, with FreeCAD credited | FreeCAD |

What this means in practice:

- **A fresh settings folder.** The first start of a Fission 180 build is like a first start:
  FreeCAD's settings, add-ons and macros are not copied (and not touched). Fission 180 sets its own
  theme and keys, so there is little to carry over; copy `%APPDATA%\FreeCAD\Macro` by hand if
  you need your macros.
- **Designs are shared.** `.FCStd` files open in both; a design saved by Fission 180 opens in
  FreeCAD 1.1 (Fission 180's features are FreeCAD features). File > Open in either program.
- **The quick update works on both layouts** (`quick-update.md`): the installed Fission 180 is found
  by itself; a portable build or an older FreeCAD-named folder is picked in the dialog.
- **Fusion files** (`.f3d`) cannot be opened; export STEP (solids) or 3MF/STL (meshes) from
  Fusion. The Fusion-to-Fission180 keys and mouse are in `cheat-sheet.md`.
- **Uninstalling** Fission 180 (Windows "Installed apps") removes the program folder and, only if
  you tick it, `%APPDATA%\Fission180`; FreeCAD's files and settings are never removed.
- The window title says `Fission 180 1.1.4`: 1.1.4 is the FreeCAD core inside; Fission 180's own
  build number is in Fission 180 > Diagnostics.

## Getting updates without rebuilding (most of the time)

See [quick-update.md](quick-update.md): download `Fission180-quick-update-...` from the newest green
**Fission 180 tests** run and install it with `install_update.ps1` (about a minute). A full build is
only needed when FreeCAD's C++ core changes; MEMORY.md says when.

## What to send back after testing

1. **View > Panels > Report view**: copy everything, especially lines starting with `[Fission 180]`.
2. **Fission 180 > Diagnostics**: copy the text.
3. A screenshot if something looks wrong.

## What the automatic tests check

Every push runs **Fission 180 tests** (Actions tab). It uses the official FreeCAD 1.1.4 plus the
Fission 180 module and checks:

- **Unit tests**: the parts of Fission 180 that are plain logic (search ranking, timeline rules,
  golden-model format).
- **Golden models**: about 280 reference parts (bracket, enclosure, flange, holes, fillets, shells,
  patterns, Press Pull, Extrude on a face, and "edit an early step" cases). Each is rebuilt step
  by step and its volume, area, size and face count are compared with values worked out by hand.
  The report appears on the run's summary page.
- **GUI smoke test**: starts the real FreeCAD window on a virtual screen, switches to Fission 180,
  checks toolbars, shortcuts and the timeline, and saves a screenshot (download
  `fission180-test-output-base` from the run).
- **GUI journey test**: uses Fission 180 the way a person does, with real mouse clicks and drags:
  Create Sketch by clicking a plane, Extrude by clicking inside the profile and dragging the
  arrow, Press Pull by clicking a face, a second sketch on a face, a cut, a face extrude.
  Screenshots `journey-*.png` are in `fission180-test-output-base`.
- **GUI scenarios**: about 130 complete workflows (one per feature, plus the "try to break
  it" rounds), each with real clicks, typing and keys, checking volumes worked out by hand
  and that no error or pop-up appears. They are split over 4 machines; the reports and
  screenshots are in `fission180-test-output-scenarios-1` to `-4`.
- The quick update is only built when all five parts pass.

## Folder map

| Folder | What |
|---|---|
| `src/Mod/Fission180/` | Fission 180's own module (workbench, timeline, search, tests) |
| `src/Mod/Fission180/Fission180Tests/golden/` | the golden models and how to write them |
| `docs/fission180/` | the outline, this guide, the list of changes to FreeCAD's code |
| `tools/fission180/` | scripts for running tests |
| `prototype/forge-freecad/` | the original "Forge" draft, kept for history |
| everything else | FreeCAD's source code |
