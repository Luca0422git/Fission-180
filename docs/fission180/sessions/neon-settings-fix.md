# Neon Lights wave, fix round for builder `settings` (`settings-fix`)

Branch `sf/neon-settings-fix` (from `sf/neon-integration` aad96d3b, all ten builders merged).
An independent reviewer found eight problems in Preferences > Neon Lights. All are fixed, and
each has a test that fails on the old code and passes now.

## What was fixed (in plain words)

1. **Words on the page stay readable whatever colours you choose.** The refusal message, "In
   use", the readability note, the strength percentages, the "More" button, the section titles,
   the banner, a hovered button and the chosen colour set were painted in the raw colour you
   picked. With Alert #1a0a10 the refusal message vanished, with Secondary #000000 the
   percentages and "More" did. Each one now goes through `neon_palette.readable(...)` against what
   it is drawn on (`neon_prefs_core.INKS` / `inks(p)`); a colour that is readable already is kept
   as it is. A refused colour box also gets a readable border.
2. **No false "too faint" note.** The page compared the typed Text with the look's version of
   it, but the look also changes every colour by a hair to keep them unique (#ffffff came back
   #fbfafa), so a white text got the note. Now the typed colour itself is measured against the
   panel colours (ratio 4.5).
3. **Cancel undoes "Switch to Neon Lights".** The page remembers the look when the window
   opens; Cancel puts it back (and the Neon settings too). OK/Apply keep it.
4. **Saved colour sets are never lost without a word.** Saving under a name that is taken and
   Delete now ask first, inside the page: "A colour set called X exists already. Replace its
   colours ...? [Replace] [Keep it]" and "Delete the colour set X? This cannot be undone.
   [Delete] [Keep it]". Nothing changes until you say yes. (Saved sets still stay as soon as you
   save them, like files; they are not part of Cancel.)
5. **The live preview no longer leaves files behind.** Every colour you try makes a folder of
   pictures in `<UserAppData>/Fission180/neon/<8 letters>/`. On Apply, OK and Cancel, the new
   `neon_settings.prune_unused()` deletes every such folder except the one of the colours in use.
   It only deletes folders named like those 8 letters directly inside `Fission180/neon/`; files,
   links and anything else are left alone, and it refuses any other folder. (The other modules
   check whether their files exist before using them, so a folder removed and needed again is
   simply made again.)
6. **Leaks and double work.** Each colour picker is now deleted when it closes. When Preferences
   opens again, the closed window before it is deleted (it belonged to the main window, so each
   opening kept one more alive, and a look change restyled all of their hidden pages). A look
   change now restyles only a page that is on screen. A colour change brings the page up to date
   once instead of twice.
7. **The text boxes, buttons and list keep their own thin frame.** They set their own border but
   the app's Neon style also gives these widgets a nine-slice frame picture (`border-image`),
   which got squeezed into the 1 px border. The page now says `border-image: none` wherever it
   sets its own border. Checked on screen: the top edge of a colour box is the line colour; without
   the fix it is the frame picture's colour (#0b1417 instead of #098750).
8. **Tests.** Cancel is now checked to bring back every switch and strength as the window
   opened (GlowStrength 25 -> 70, ScanLines, ...), not only the colours. The **restart is real**:
   the scenario writes the settings to disk, copies the profile and starts a second FreeCAD with
   it (like `neon_sizes` does); that FreeCAD (`Fission180Tests/gui/neon_settings_child.py`) opens
   in Neon Lights with Mine's colours and its Preferences show "Mine" chosen and "Custom (based on
   Johnny)". Its checks come back into `neon_settings`' result as `[restart] ...`.

## Tests

- Unit: `test_neon_prefs_core.py` +4 (white text is not called faint for all 17 presets, faint
  text is, every ink readable on its ground for all presets x 5 extreme colour sets, readable
  colours kept); `test_neon_settings.py` +3 (only unused palette folders go; never outside
  `Fission180/neon`, links/files kept; `has_set`). The two readability tests fail on the old
  `neon_prefs_core.py`.
- Scenario `neon_settings` now 132 checks (was 99): Cancel after Switch (Dark again, parts off,
  ribbon Dark's); extreme colours (Alert #1a0a10, Secondary #000000) with the message, "In use",
  a value, "More" and the note measured at >= 4.5 on the panel; a colour box's border on screen;
  white Text without the note; the real restart; Cancel restores all switches/strengths; Save
  over a taken name and Delete ask, "Keep it" keeps, "Delete" deletes; after OK only V's folder
  is left in `Fission180/neon/`; opening Preferences again leaves at most one page alive.
- Proof the new checks bite: with the old page code the scenario fails at "Cancel after Switch to
  Neon Lights: Dark again" (it stayed Neon); with `border-image: none` removed it fails at "a
  colour box's top edge is its own line colour".
- Runs (each green): `--only unit` (4,125 tests), `test_theme_identity.py`, `look_unchanged`
  (x2), `neon_switch` (x3), `neon_settings` (x4), `misc_preferences` (x2).

## Files

Mine: `F/neon_prefs_ui.py`, `F/neon_prefs_core.py`, `F/neon_settings.py` (`has_set`,
`neon_folder`, `prune_folders`, `prune_unused`), `F/preferences_ui.py` (`show()` deletes the closed
window before; 7 lines), `T/gui/scenarios/neon_settings.py`, new `T/gui/neon_settings_child.py`
(the restarted FreeCAD; outside `scenarios/` so it is not run on its own, like
`neon_sizes_child.py`), `T/unit/test_neon_prefs_core.py`, `T/unit/test_neon_settings.py`.
No shared or other builders' files touched.

## Facts found

- `QDialog` parented to the main window is never deleted when closed; `WA_DeleteOnClose` (or a
  `deleteLater()` when the next one opens) is needed. `QColorDialog` with `WA_DeleteOnClose` is
  deleted by `done()`.
- A second FreeCAD started with `QProcess` and `FREECAD_USER_HOME=<copy of the profile>` plus
  `FISSION180_SCENARIO_FILE=<child>.py` and `scenario_launcher.py` gives a real restart inside a
  scenario; it took about 30 s here.

## Screenshots (`docs/fission180/images/neon/`)

- `settings-fix-extreme-colours.png`: Alert #1a0a10, Secondary #000000 and a refused `#12345`:
  the message, "More" and the note stay readable.
- `settings-fix-delete-asks.png`: Delete asks first, in the page.
- `settings-fix-fields.png`: the colour boxes with their own thin frames (Custom based on Johnny).
