# Touchscreen in the 3D view: design

Status: proposed 2026-11-23, waiting for Luca's approval.

## Why

Luca's CachyOS laptop has a touchscreen (he also uses Fission 180 on Windows). He wants to move
around a design with his fingers: "panning around while using the touchscreen ... That and
Zoom." Today Fission 180 only knows the mouse and the touchpad (touchpad_ui.py: two fingers on a
touchpad pan, a pinch zooms). On a touchscreen Qt turns one finger into a left mouse button, so
a finger drag draws a selection box and two fingers do nothing useful.

## What the fingers do (Luca's choices)

In a 3D view:

| Touch | Does |
|---|---|
| One finger dragged | orbits (turns) the view, as the mouse's orbit does (Constrained / Free and the pivot as set) |
| Two fingers dragged | pans |
| Two fingers pinched / spread | zooms, about the point between the fingers |
| One finger tapped | a left click there (selects; a double tap is a double click) |
| One finger held still about half a second | a right click there (the right-click menu) |
| Two fingers tapped together | a right click between them |

## Goals, non-goals, anti-goals

- Goals: the table above, on Linux (X11 and XWayland: the AppImage runs through xcb) and
  Windows, in every 3D view of a design.
- Non-goals: touch in panels, the browser, dialogs and menus (Qt already turns a tap into a
  click and a finger drag into scrolling there); a pen or stylus; three-finger gestures; an
  on-screen keyboard.
- Anti-goals: the mouse and the touchpad behave exactly as before; a tap never orbits a little
  (a finger has to move a few pixels before a drag starts); nothing changes in the looks.

## Approaches (Luca picked A)

- **A. Fission 180 reads the touch points itself.** The 3D view's drawing area accepts Qt's
  touch events; a pure module decides tap / long press / one-finger drag / two-finger
  pan-pinch / two-finger tap from the points and times; the window part moves the camera with
  the helpers the navigation bar and the touchpad already use (navigate_ui.pan_by,
  touchpad zoom at a point, orbit_ui's orbit) and sends taps and right clicks as mouse
  clicks. Full control over Luca's layout, the same on Windows and Linux, testable with
  simulated touch events.
- B. FreeCAD's own gestures (the viewer grabs Qt's pan and pinch gestures): only FreeCAD's
  "Gesture" navigation style reacts to them, which would change the mouse; Qt's pan
  recognizer behaves differently per platform; no one-finger orbit.
- C. Leave one finger to Qt's mouse emulation: a one-finger drag stays a selection box.

## My calls (to check)

1. **Sketches:** while a sketch is being edited, one finger works like the mouse (a tap places
   a point or picks, a drag drags geometry or a selection box); two fingers still pan and pinch.
   Orbiting a sketch by accident while drawing would be worse than not orbiting it at all.
2. **Drag handles:** a one-finger drag that starts on a drag handle (Extrude's arrow, a
   Move arrow, a Fillet handle) drags the handle like the mouse instead of orbiting.
3. **Thresholds:** a drag starts after 8 px of movement; a long press is 500 ms with the
   finger within 8 px; a two-finger tap is both fingers down and up within 300 ms, moving
   less than 8 px; a pinch starts when the fingers' distance changes by more than 4 %.
   Changing from one finger to two mid-gesture switches to pan/pinch, never back to orbit.
4. **Switch:** Preferences > General > Navigation gets "Touchscreen: On / Off" (On by default;
   Off gives Qt's old behaviour).

## Left to the builder

The exact Qt plumbing (WA_AcceptTouchEvents on each 3D view's QOpenGLWidget, the event filter,
how a synthesized click reaches FreeCAD: a mouse event sent to the viewer, as
FreeCAD's OverlayManager::interceptEvent does), how a drag handle is recognized under the
finger, and the tests: unit tests of the pure classifier and a GUI scenario driving each
gesture with simulated touch events (QTest touch sequences). Luca checks it on the real screen.
