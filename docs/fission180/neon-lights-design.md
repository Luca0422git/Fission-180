# Neon Lights: design (2026-11-20)

A third look for Fission 180, next to Dark and Light: a cyberpunk, neon-glow skin over the whole
program, with colour presets, custom colours, coloured body outlines, hologram bodies and
switchable screen effects. Design agreed with Luca in the session of 2026-11-20; the build plan
and the builders' briefs follow from this file.

## 1. Why

Luca, in his words: "Fission 180 is looking and feeling really good. it feels just like using
Fusion. I love it. but i kinda like to show off. And Fusion is what everyone and their mother has
seen ... since this is MY software, i want it to also FEEL like something I would make. and when
people walk past me, i want them to look at my screen and ask themselves 'what program is he
using? that looks sick!'" He loves cyberpunk UI: "Everything is rough around the edges,
industrial, but also so eye catching. I love the neon glow."

So the success test is a person walking past: the screen must be unmistakably *not* Fusion,
striking at a glance, and still a CAD program Luca can do real work in every day.

## 2. What Luca decided

| Topic | Decision |
|---|---|
| Name | **Neon Lights**, a new choice in Preferences > General > Look |
| Scope | "a COMPLETE overhaul of EVERY UI element ... new icons, menu transparency, dropdown animation, the whole nine yards". Positions stay where they are, but shapes may differ: "dont be afraid of making the UI a bit different" |
| Colours | Preset colour themes with pop-culture names ("Johnny (Yellow and blue), V (red and blue), etc."), and fully custom colours |
| Body outlines | The colour of the edges drawn on bodies can be changed ("instead of just having black") |
| The models | **Both**: neon trim by default (normal shaded bodies, glowing outlines, dark background, glowing grid), plus a **Hologram bodies** switch (dark see-through glass bodies with bright glowing edges) |
| Effects | CRT, scan lines, glow, an occasional glitch, each one switchable. **Everywhere, lighter over the 3D view**; the glitch never fires while he drags, picks or types |
| Font | **A techy font everywhere** (open-licence only) |
| Extras | **Boot-up sequence**, **UI sounds**, **animated Home tab**, each with its own switch |
| Dark and Light | "I like the current look of Fission. Dont change any of that. Only make changes to the NEW themes" |

## 3. Goals, non-goals, anti-goals

**Goals**
- Every surface of the window changes when Neon Lights is on: ribbon, tabs, menus, drop-downs,
  tooltips, browser, timeline, navigation bar, ViewCube, every command dialog, Home, Data Panel,
  Preferences, message boxes, the sketch palette, the measure box, scroll bars, check boxes, text
  boxes, progress bars, the status bar, FreeCAD's own windows inside Fission 180 (Report view,
  Python console, its Preferences) as far as an application style sheet reaches.
- New icons for the whole set (426 today), in a neon line-art language.
- The 3D view: dark background, neon grid, coloured and glowing body outlines, neon selection and
  hover colours, neon sketch colours, neon arrows/handles/previews, hologram bodies on demand.
- Presets + custom colours + per-effect switches and strengths, all applied live.
- Switching back to Dark or Light returns exactly today's look, with nothing left over.

**Non-goals**
- No change to how anything *works*: same commands, dialogs, options, shortcuts, positions.
- No change to what is saved: a design made in Neon Lights opens exactly the same in Dark, on
  another computer, or in plain FreeCAD. Drawings stay black on white paper; exports, PDFs and
  STEP/STL files are untouched by the look.
- No Fusion parity requirement for this look (it is deliberately not Fusion; Dark keeps Fusion
  parity). To be recorded in MEMORY.md's Decisions log.
- The Windows Open / Save file window is drawn by Windows and cannot be restyled; it stays as is.

**Anti-goals (it fails even if it technically works when...)**
- Dark or Light change in any visible way (colour, size, spacing, icon, font, behaviour).
- It is too dim or too busy to model in: values, small text or fine edges become hard to read,
  or an effect hides what is under the mouse.
- It is slow: orbiting, previews or typing lag because of the effects (a parity bug by the spec's
  own rule: "treat lag as a parity bug").
- It feels like a recoloured Dark: same rounded grey boxes with pink text. The shapes, icons, font
  and motion must change too.
- It copies someone's art: the reference sheets Luca sent are watermarked stock vectors, and
  Cyberpunk 2077 is CD Projekt's. We take the *style* (cut corners, brackets, hazard stripes,
  scan lines, glow), never their shapes, logos, fonts, sounds or wording.

## 4. Constraints

- `CLAUDE.md` rules: new code in `src/Mod/Fission180/`; `[Fission 180]` log prefix; no exception
  escapes a command, timer or event handler; explain changes to Luca in plain language.
- **Python only** (no FreeCAD core change), so it can ship without the 4-hour full build. A C++
  change only if a measured performance problem has no Python route (then core-patches.md).
- Real FreeCAD 1.1.4 (PySide6 6.8.3, Qt 6.8) on Windows 10/11 first, Linux second. Qt's SVG
  renderer is SVG Tiny: **no SVG filters** (no blur), so glow in icons and frames is drawn as
  layered translucent strokes. The official FreeCAD AppImage has the PySide6 QtMultimedia module
  but not Qt's Multimedia library, so sound needs a fallback (section 6.10).
- Translucent pop-ups need a compositing window manager on Linux; without one, fall back to
  opaque pop-ups (detect, never show black corners).
- The existing theme machinery (`fission180/theme.py`) is the base: `THEMES`, `_use()`, the
  application style sheet `_QSS`, `translate()` with its colour tables and the `setStyleSheet`
  hook (about 205 panels write dark colours in their own style sheets and are translated
  automatically), `keep_and_set` / `give_back` for FreeCAD viewer settings, the `theme_changed()`
  calls (`sketch_mode`, `shell`, `home_ui`), `ui_icon_path()` (light icon copies made in the
  user folder). Interface size (`prefs` "Interface size") must keep working in Neon Lights.
- Tests run in the sandbox under xvfb (`tools/fission180/run_tests.sh`), and on GitHub CI.

## 5. Approaches considered

1. **Colour swap only** (a third palette in `theme.py`, like Light). Cheap, but no cut corners, no
   glow, no motion, no new icons: exactly the "recoloured Dark" anti-goal. Rejected.
2. **A skin layer on top of the existing theme machinery, all in Python** (picked). A neon palette
   and translation table; generated SVG frame pieces used by the style sheet as nine-slice
   `border-image`s (cut corners, brackets, faux glow); a `QProxyStyle` and a few event filters
   where a style sheet cannot reach (pop-up translucency and animation, focus glow); a new
   neon icon set from the same recipe system as today's icons; a see-through effects layer over
   the main window; Coin (3D scene) changes for outlines, glow, grid and hologram. Ships as
   Python, tweakable without a rebuild, and Dark/Light code paths stay untouched.
3. **A new Qt style in C++ inside FreeCAD's core.** Fastest drawing and full control, but every
   tweak needs the 4-hour build, and it changes FreeCAD's core for a cosmetic feature. Kept only
   as a fallback for a measured performance problem.

## 6. The design

### 6.1 Switching and where it lives

- `theme.THEMES` becomes `("dark", "light", "neon")`; the Look choice in Preferences gets
  "Neon Lights (cyberpunk, your colours)". Switching is live, as today.
- Neon code lives in new files (suggested split, the plan decides): `neon_palette.py` (presets,
  roles, custom colours, pure logic, unit tested), `neon_style.py` (style sheet, frame SVGs,
  proxy style, pop-up animation), `neon_icons.py` (runtime recolouring of the neon icon set),
  `neon_view.py` (3D scene: background, grid, outlines, glow, hologram, overlays),
  `neon_effects.py` (scan lines, CRT, glitch layer), `neon_boot.py`, `neon_sound.py`,
  `neon_home.py`, `neon_prefs_ui.py`. `theme.py` only learns that a third look exists and
  hands over to them when it is chosen; its Dark and Light tables, `_QSS` and behaviour stay
  byte-for-byte the same.
- Leaving Neon Lights (to Dark, to Light, or switching Fission 180 off) removes every neon piece:
  style, proxy style, event filters, effects layer, timers, fonts, icon set, 3D changes.

### 6.2 Colours: roles, presets, custom

Every neon colour comes from a small set of **roles**, so a preset is just a handful of values:

| Role | Used for |
|---|---|
| `primary` | the main glow: frames, active tab, focused field, selected rows, icons' main lines |
| `secondary` | the second accent: hover, icon accents, timeline markers, progress, links |
| `alert` | warnings and errors (hazard stripes, error boxes); amber or red that does not clash |
| `background` | the near-black ground of panels and the 3D view (tinted per preset) |
| `text` | body text (light, slightly tinted); dim and disabled text derived from it |
| `outline` | body edges in the 3D view (defaults to `primary`, can be set on its own) |

Derived shades (panel fill, hover fill, lines, dim text...) are computed from the roles in
`neon_palette.py`, with a minimum contrast for text against its ground (WCAG AA, 4.5:1 for small
text) enforced in code: a custom colour too dark to read is lifted, never shown unreadable.

**Presets** (names are references only: no logos, artwork, fonts or quotes from the works):

| Preset | Primary | Secondary | After |
|---|---|---|---|
| Johnny | yellow `#FCEE0A` | electric blue `#00C2FF` | Luca's suggestion (Cyberpunk 2077) |
| V | neon red `#FF003C` | cyan-blue `#00E5FF` | Luca's suggestion (Cyberpunk 2077) |
| Night City | hot pink `#FF2A6D` | cyan `#05D9E8` | the classic cyberpunk pair |
| Judy | magenta `#FF4FD8` | teal `#2DF5C8` | Cyberpunk 2077 |
| Arasaka | blood red `#FF1E1E` | steel white `#E6E8EB` | Cyberpunk 2077's corporation |
| The Grid | cyan `#6FF3FF` | orange `#FF9A1F` | Tron: Legacy |
| Replicant | orange `#FF7A18` | teal `#19C3B3` | Blade Runner 2049 |
| Red Pill | code green `#00FF41` | deep green `#00B32C` | The Matrix |
| Kaneda | red `#FF2340` | sky blue `#42C8FF` | Akira |
| Section 9 | aqua `#00FFC8` | violet `#9B5CFF` | Ghost in the Shell |
| Outrun | magenta `#FF2BD6` | sunset orange `#FFB000` | synthwave |
| Vaporwave | pink `#FF71CE` | cyan `#01CDFE` | vaporwave |
| Miami | pink `#FF3EA5` | aqua `#00F6FF` | Hotline Miami |
| Pip-Boy | phosphor green `#18FF6D` | pale green `#A8FFC8` | Fallout |
| Mainframe | amber `#FFB000` | pale amber `#FFE0A0` | old amber terminals |
| Augmented | gold `#F7B500` | orange `#FF7A00` | Deus Ex |
| Upside Down | red `#FF1E1E` | blue `#3D6BFF` | Stranger Things |

Background and text per preset are tuned by the builder (near-black, tinted toward the preset;
Night City and Outrun lean deep blue/purple, Red Pill and Pip-Boy pure black). The default
preset is **V**. The builder may adjust exact values for readability and glow; names stay.

**Custom**: picking any colour turns the preset into "Custom (based on V)"; Luca can set
primary, secondary, outline, background and text with a colour picker (alert under "More").
"Reset to preset" puts the preset back. Up to a few custom sets can be saved under his own
names (stored in Fission 180's preferences group, `Mod/Fission180/Neon`).

### 6.3 Shapes: what changes on screen

Positions and sizes stay; the shapes are new. The look language (original, from the style of
the references): cut (chamfered) corners instead of round ones; thin glowing frame lines with
small corner brackets and tick marks; hazard stripes for warnings; segmented bars; squared
check boxes; dark translucent fills; uppercase, letter-spaced headings.

| Element | Neon Lights |
|---|---|
| Ribbon | dark translucent bar; tab names uppercase in the techy font; the active tab has a glowing underline with a chamfered end; group labels between small bracket marks; hover = soft glow behind the icon |
| Menus and drop-downs | see-through dark glass (about 85% opaque), chamfered glowing frame, items light up with a primary bar on the left; **open with a short animation** (fade + slide/unfold, about 120 ms; a quick "scan" line across on open); the same for combo-box lists and the ribbon's group drop-downs |
| Tooltips | small HUD card: cut corner, bracket corners, monospace-ish title |
| Command dialogs (task panels) | chamfered frame, header strip with a stripe pattern and the title in caps, fields as dark slots with a glowing bottom line on focus, OK as a primary-coloured chamfered button |
| Browser and timeline | glowing tree lines like circuit traces; selected row = primary bar + tint; timeline steps as chamfered chips with a glow, the history marker as a bright vertical beam |
| Navigation bar, ViewCube | HUD frame; ViewCube drawn as a glowing wireframe cube with techy labels |
| Home, Data Panel, Preferences | the same frames and fonts; Home gets the animated background (6.9) |
| Message boxes | warnings with a hazard-stripe header in `alert`; errors red with a brief glitch on appear |
| Scroll bars, sliders, progress | thin neon rails; segmented progress bars |
| Check boxes, radio buttons | squares/diamonds with a neon fill and tick |

Frames come from small SVG pieces generated per preset (in the user folder, like today's light
icons) and used as nine-slice `border-image` in the style sheet; the glow is baked into them as
layered translucent strokes. Where a style sheet cannot do it (pop-up translucency and
animation, focus glow on fields), a `QProxyStyle` and event filters do it, installed only while
Neon Lights is on.

### 6.4 Font

An open-licence (SIL OFL) squared sci-fi font for **all** text, downloaded from the Google Fonts
repository on GitHub with its licence file and shipped in `fission180/fonts/`. First choice
**Chakra Petch** (squared, readable at small sizes, clear digits); a display face such as
**Orbitron** for big titles (Home, boot screen). Loaded with `QFontDatabase.addApplicationFont`
only in Neon Lights, at the size Interface size asks for. Values in fields must stay easy to
read: if the sample shows a problem with small digits, the builder proposes a fix (a slightly
larger size, or a mono face for numbers) and Luca decides. No font from Cyberpunk 2077.

### 6.5 Icons

A **new neon icon set** for all 426 ribbon/menu/browser icons: line art (outlines, not filled
blocks), angular, two-tone (`primary` for the object, `secondary` for the accent, `alert` for
warnings), with a faux glow (a wider translucent copy of each line under it). Made by the same
recipe system as today (`tools/fission180/make_icons.py` and the `icons_*.py` recipe files): a
neon renderer for the recipes' building blocks plus hand-made recipes for the most-seen icons
(the ribbon's visible buttons, browser, timeline, navigation bar). Written with placeholder
colours into `fission180/icons/neon/`, recoloured per preset at runtime into the user folder (as
`ui_icon_path` does for light icons). Today's icons in `icons/ui/` are not touched. A missing
neon icon falls back to a recoloured copy of the normal one, never to a blank.

### 6.6 The 3D view

- **Background**: near-black tinted with the preset (optionally a faint vertical gradient), via
  `keep_and_set` like today's background.
- **Grid** (`grid_ui.py`): minor lines dim `primary`, major lines brighter, the origin axes in
  their usual X/Y/Z hues but neon.
- **Body outlines**: edges in the `outline` colour, with a **glow** (a second, wider, translucent
  pass under each edge line) when the Glow effect is on. **Display only**: the colours saved in
  the design (each body's `LineColor`) must not change, switching looks must not mark a design as
  modified, and nothing may enter the undo history. The builder finds the mechanism (overriding
  the line material in the scene graph is preferred; changing `LineColor` and putting it back
  around every save is the fallback, only if it provably never leaks into a saved file).
- **Hologram bodies** (switch, default off; also a quick toggle in the navigation bar while Neon
  Lights is on): faces become dark tinted glass (see-through), edges bright `outline` with glow;
  a rim light that brightens faces seen edge-on (a GLSL shader through Coin) if it works on
  Windows Intel/AMD/NVIDIA and Linux; a flat translucent material otherwise. Display only, like
  the outlines; appearances and materials come back exactly when it is switched off.
- **Selection and hover** colours, **sketch** colours (`sketch_mode`), the **arrows, handles,
  previews and overlays** (`handles3d`, `preview`, about 50 files that colour the scene) take
  neon colours: shared helpers map the existing colours to neon roles (like `translate()` does
  for style sheets), files with their own colours are swept.
- Measure's dots/labels follow too (see the note in MEMORY.md's known issues about their size).

### 6.7 Effects

One see-through layer over the main window (clicks pass straight through it), painting:

| Effect | What it does | Default |
|---|---|---|
| Glow | the soft halo on frames, icons and body edges | on |
| Scan lines | fine horizontal lines (cached, not repainted per frame); an optional slow rolling bright band | on (band off) |
| CRT | dark vignette in the corners and a faint screen-edge curve shading (no real warping of the window) | on |
| Glitch | every 40-120 s at random, for 80-150 ms: a strip of the window shifts sideways with a red/cyan split | on |

Each has a switch and a strength slider, plus one master switch. Over the 3D view every effect
draws at about 40% strength. The glitch **never** fires while a mouse button is held, while a
drag or pick is going on, while a text field has focus, while a command dialog is waiting for a
value, during a recompute, or in tests. Effects pause when the window is not active or minimized.

**Speed budget**: with every effect on, orbiting a 3,000-face part may not take more than 10%
longer per frame than with effects off, and an idle window may not use more than about 2% of a
CPU core. Measured in a scenario; if an effect cannot meet it, it gets cheaper or goes off by
default, and Luca hears about it.

### 6.8 Boot-up sequence (switch, default on in Neon Lights)

When Fission 180 starts in Neon Lights: about 2.5 s over the already-loaded window: the Fission
180 mark glitches in, a few lines of "system boot" text type out (original wording), a segmented
bar fills, then it dissolves. Any click or key skips it. It never delays loading or a file
opened from the command line, never shows during tests, and shows once per start.

### 6.9 UI sounds (switch, default off) and the animated Home (switch, default on)

- **Sounds**: short original synth blips (button, menu open, command done, error, boot), made by
  a script in `tools/fission180/` (synthesized, so no licences) as small WAV files in
  `fission180/sounds/`. Volume slider. Played without blocking the window: Qt Multimedia if
  present; else `winsound` on Windows; else `pw-play` / `paplay` / `aplay` on Linux; else
  silent. Never an error if there is no sound device.
- **Animated Home**: a slowly moving neon perspective grid and a faint data stream behind Home's
  content, drawn only while Home is visible and the window active (about 30 frames a second at
  most, paused otherwise).

### 6.10 Settings

When Look = Neon Lights, Preferences shows a **Neon Lights** section: a gallery of preset
swatches; colour pickers (Primary, Secondary, Outline, Background, Text; Alert under "More");
save/rename/delete custom sets; Hologram bodies; the four effects with switches and strengths,
plus the master switch; Boot-up sequence; UI sounds + volume; Animated Home. Every change shows
at once in the real window behind it. Stored under `Mod/Fission180/Neon`.

### 6.11 Safety rules

- **Dark and Light stay identical**, guarded by tests: their style sheet, colour tables and icon
  files are byte-for-byte what they were on `develop` before this work; a screenshot of the main
  window, a command dialog and a menu in Dark matches the one taken before the work.
- Switching Neon -> Dark -> Neon -> Light leaves no trace (style, fonts, event filters, timers,
  effects layer, 3D changes, viewer settings).
- Designs are unchanged by the look: a design saved in Neon Lights with Hologram on opens with the
  same colours, line colours and transparency in Dark; switching looks never marks a design
  modified or adds an undo step.
- Every neon timer, event filter and paint routine catches and logs (`[Fission 180]`) and turns
  the failing effect off rather than breaking the window.

### 6.12 Tests and showing Luca

- Unit tests for the pure logic (palette roles, contrast lifting, preset storage, the icon and
  frame recolouring, the glitch scheduler's "never while busy" rules).
- GUI scenarios: switch looks back and forth (the Dark/Light identity checks above); every preset
  applies; custom colours persist after a restart; outlines and Hologram never change a saved
  design; clicks pass through the effects layer; the glitch never fires during a drag; the speed
  budget; boot sequence skips on a click; sounds never raise without a sound device; Home
  animation stops when Home is hidden.
- A **showcase scenario** that takes screenshots of the main surfaces in a few presets (ribbon
  with a menu open, a command dialog, sketch mode, Hologram, Home), sent to Luca for review.

### 6.13 Delivery

- Branch `sf/neon-lights` (from `develop`), merged into `develop` when its tests are green, as
  move-speed was.
- **First a sample** (font, a few icons, a menu, one dialog, the 3D view in two presets) as real
  screenshots for Luca's OK, before the builders redraw everything.
- Then builders work in parallel, each owning its own files (the plan lists them).
- Release: all in Fission 180's own files, so it can go out without the full build; Luca decides
  when and under which number.

## 7. Left to the builders (decide, write down why, test)

- The mechanism for display-only outline colours and Hologram (6.6), the rim-light shader and its
  fallback, and how the edge glow pass is built.
- How pop-up translucency and animation are hooked (proxy style vs. event filters), and the
  compositor detection on Linux.
- Exact preset shades within the stated hues, the derived shades, frame piece geometry.
- The neon renderer for icon recipes and which icons get hand-made recipes.
- Effect painting technique and caching, within the speed budget.

## 8. Calls made in the design (Luca to check)

- Default preset **V**; default effects: Glow, Scan lines (no rolling band), CRT and Glitch on;
  Hologram off; Boot-up on; Sounds off; Animated Home on.
- The preset list and names in 6.2 (17 presets + Custom, saved custom sets).
- Chakra Petch + Orbitron as fonts (to be confirmed by the sample).
- A Hologram quick toggle in the navigation bar while Neon Lights is on.
- Glitch every 40-120 s, 80-150 ms long; effects at about 40% over the 3D view.
- The speed budget (10% per frame, about 2% idle CPU).
