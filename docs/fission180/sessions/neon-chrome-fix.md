# Neon Lights fix round `chrome-fix` (task B1 review fixes)

Branch `sf/neon-chrome-fix` (from `sf/neon-integration` aad96d3b). Report for the orchestrator,
written 2026-11-20.

## In plain words (for Luca)

- **Menus no longer turn black after switching to Neon Lights.** On Windows and on a Linux
  desktop with see-through windows, a menu, drop-down list, tooltip card or parameter names list
  that you had already opened in Dark became black glass with black corners once you switched to
  Neon Lights, until a restart. Now such a pop-up is shown with a solid dark ground instead (the
  same look as on screens without see-through windows); pop-ups opened for the first time in
  Neon Lights are still see-through glass. After a restart everything is glass again.
- **Error messages** now really show their text in the bright colour the design asks for.
- **Message boxes** are no longer kept in memory after they close.
- The **size test** (`neon_sizes`) now really finds cut-off text. It found some real problems in
  other builders' parts; see "Found by the new size check" below.

## What changed (files)

| File | What |
|---|---|
| `F/neon_popups.py` | New `see_through(widget)`: sets `WA_TranslucentBackground` only if the pop-up's native window does not exist yet (`not testAttribute(WA_WState_Created)`); an already-made pop-up gets the dynamic property `fission180Solid=True` and is re-polished. `enable()` goes once over the existing pop-ups (so a hidden menu made in Dark but never shown still gets glass). `disable()` clears the property. Message boxes: `_repolish()` re-polishes the box **and its children** when its kind changes; a box is unstyled (system icon back) and dropped from `_state["boxes"]` on a non-spontaneous Hide; `boxes()` for tests. |
| `F/neon_qss_chrome.py` | `QMenu[fission180Solid="true"]`, `QMainWindow > QMenu[fission180Solid="true"]` and `QToolTip[fission180Solid="true"]` get the solid `menu` ground. `TAB_FONT` (uppercase, 1 px letter spacing) feeds the `QTabBar::tab` rule; the generated text is byte-identical to before. |
| `F/tips_ui.py` | `neon_card_style(card)` picks glass or solid with `neon_popups.see_through(card)`. |
| `F/parameters_complete.py` | `_neon_look(widget)` likewise for the names list. |
| `T/gui/neon_sizes_child.py` | Tabs: `tab_clipped()` uses `initStyleOption` (callable from PySide6) - elided text counts as clipped, else the text's `horizontalAdvance` in the tab's font (bar font + `TAB_FONT` in Neon) against `subElementRect(SE_TabBarTabText)`. Every ribbon page is selected and measured in turn (front page restored). The check is absolute: anything clipped in Neon fails unless it is in `ALLOWED` (empty). Every clipped item in both looks is printed to the child's log. |
| `T/gui/scenarios/neon_chrome.py` | New steps (131 checks now): `own_border`, `dark_popups` / `early_to_neon` / `early_again` / `early_checked` / `early_dark`, the error label colour, closed boxes not kept. |

No shared file and no other builder's file was touched.

## Tests (proof for each finding)

1. **Black pop-ups**: `neon_chrome` shows a menu, a drop-down list, the tooltip card and the names
   list in Dark with `XDG_CURRENT_DESKTOP=KDE`, switches to Neon, shows the **same** widgets again:
   each has alpha buffer 8 or is marked solid without the translucent attribute; the corner and
   ground on screen are not black; the card's and the list's own styles have the solid ground; a
   menu made after the switch has alpha 8 and is see-through; back in Dark no mark is left.
   **Run against the old code** (created-check removed): fails exactly as reported - menu alpha
   `-1`, not solid, screen corner `#000000`; card and list styles `background: transparent`.
2. **Size check**: checked offscreen with PySide6 - an eliding tab bar reports
   `tab text elided to 'A rather long …'`, a `QTabBar::tab { width: 30px }` bar reports
   `tab text 108 > 6`, normal tabs report nothing. In FreeCAD it now walks every ribbon page.
3. **Error text colour**: the message label's palette colour is exactly the palette's `bright`
   (`#f8faff` in V, text is `#f2f4ff`). V's two colours are very close, so a pixel check on
   antialiased text cannot tell them apart; the palette check can.
4. **Boxes kept**: after closing a warning (V and Johnny) and an error, `neon_popups.boxes() == 0`
   and the warning has its system icon back.
5. **A widget's own border wins**: a line edit whose own style is
   `border: 1px solid #ff0000; border-image: none` keeps a 1 px red border and its own ground in
   Neon (no frame picture). Without `border-image: none` the app's frame picture replaces the
   border (edge seen `#110b13`, the frame's ground): **the settings page's own rules
   (`neon_prefs_ui.py`, settings fix builder) must add `border-image: none`** wherever they set a
   plain `border`. Nothing in my files can stop that: Qt merges properties a widget's own style
   does not set from the app style.
6. Capitals / letter spacing on buttons, tooltips and status bar: left as reported before.

Runs on the final code: `run_tests.sh --only unit` all passed (4118, incl. `test_theme_identity`);
`look_unchanged` PASS; `neon_switch` PASS; `neon_chrome` PASS (131); `check_waits` 0.
**`neon_sizes` FAILS**, on purpose, with the items below (it passed before only because it could
not see them).

## Found by the new size check (not in my files)

At Interface size 150 %, in Neon Lights:

- Ribbon group labels on pages that are not in front (shell, `neon_qss_shell.py`
  `#Fission180Ribbon QToolButton[role="group"]` with uppercase + 1 px spacing):
  `CONSTRAINTS ▾` 130 > 88 px, `CONTACTS ▾` 107 > 88, `MATERIALS ▾` 109 > 88,
  `SIMPLIFY ▾` 95 > 88, `INSPECT ▾` 91 > 88, `MANAGE ▾` 91 > 88. In Dark, `CONSTRAINTS ▾`
  (123 > 98), `CONTACTS ▾` (102 > 98) and `MATERIALS ▾` (103 > 98) are clipped too, by less
  (Dark must not change; the group is 10 px narrower in Neon).
- The task panel header `Extrude` (FreeCAD's `QSint::ActionLabel` in `TaskHeader`; panels,
  `neon_qss_panels.py`): 11 px high in Neon, 19 in Dark, its text needs 26 (150 % and 75 %).

I put none of them in `ALLOWED`: they are real cut-off text for B2/B3's fix builders. If the
orchestrator decides one is acceptable, add it to `ALLOWED` in `neon_sizes_child.py` with its
reason. The child logs (`scenario-neon_sizes_150.log`, `_75.log`) list every item.

## Facts found (Qt)

- `QWidget::setVisible` makes the native window **before** `ensurePolished()`, so a Polish
  event filter sees a fresh widget before creation only because QMenu and friends polish early
  (sizeHint). `WA_TranslucentBackground` set after creation gives no alpha (xcb: alpha buffer
  -1) and switches off the system background: a black window where the style is transparent.
- PySide6 lets Python call `QTabBar.initStyleOption(option, i)` on a C++-made tab bar; the
  option's `text` is already elided the way Qt paints it.
- `QStyleSheetStyle` counts the `QTabBar::tab` rule's font (text-transform, letter-spacing) in
  `tabSizeHint`, so a tab that does not elide never looks short against its hint; only a fixed
  `width`, or eliding, clips it.
- After changing a dynamic property on a parent, Qt does not re-polish its children: a rule like
  `QMessageBox[kind="x"] QLabel` needs the children unpolished/polished by hand.
