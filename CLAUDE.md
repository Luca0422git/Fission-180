# Fission 180: instructions for Claude sessions

Fission 180 is a fork of FreeCAD that aims for Autodesk Fusion-level parametric CAD.

Before doing anything else in a session:

1. Read `MEMORY.md` (progress, decisions, known issues, what is next).
2. Read `docs/fission180/feature-outline.md` (the spec; sections 0-5 are mandatory).
3. At the end of the session, update `MEMORY.md` (status checkboxes, findings, session log).

Rules that are easy to forget:

- Work on and push to the `develop` branch (Luca's choice), whatever branch name the session
  was given. Do not open pull requests unless Luca asks.
- `Release` holds released builds only: it is fast-forwarded to a tested `develop` commit, and
  tagged `fission180-v<version>`, only when Luca gives the green light for that release. Never
  commit to it directly or force-push it (`docs/fission180/dev/briefs/beta-release.md`).
- Bug fixes in Fission 180's own files go out as **patch releases** (no 4-hour build): set the next
  number in `src/Mod/Fission180/VERSION` (`0.1.0-beta.2` -> `0.1.0-beta.2.1`) and its
  `_FALLBACK_VERSION`, add its CHANGELOG section, push `develop`; when the tests are green Luca
  runs Actions > Fission 180 patch release, which tags, publishes and moves `Release` itself
  (`docs/fission180/patch-release.md`).

- New code goes in `src/Mod/Fission180/`. Any change to FreeCAD's own files gets a `FISSION180:`
  comment and an entry in `docs/fission180/core-patches.md`.
- Every Fission 180 log line is prefixed `[Fission 180]`. Never let an exception escape a command,
  timer or event handler.
- The owner is a beginner: explain changes in plain language.
- Real FreeCAD can run in the sandbox: `tools/fission180/get_freecad.sh` then
  `tools/fission180/run_tests.sh` (unit tests, golden models, GUI smoke test under xvfb).
- Copy Fusion's behavior, never its assets, wording or code.
- The project was called **SciForge** until 0.1.0-beta.3.2.1 (renamed 2026-11-04). People see
  "Fission 180"; code and files say `Fission180` / `fission180`. The old name stays only where
  old designs, settings, keys and installs are read: `fission180/legacy.py`,
  `secrets_store.OLD_SERVICE`, the installer's `Fission180RemoveSciForge`, the tags of releases
  published as SciForge (`sciforge-v...`) and `Fission180Tests/fixtures/before_rename/`. Keep them.
