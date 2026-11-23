# SPDX-License-Identifier: LGPL-2.1-or-later
"""An event filter on every 3D view's drawing area and viewer, kept track of on the widgets
themselves (2026-11-23). touchpad_ui and touch_ui kept a list of the Python objects of the
widgets they were on; PySide soon calls such an object "deleted" although the widget lives on
(seen right after a new design opens), so the list said a view had no filter while it had one,
and turning Fission 180's interface off left the filter on those views (the touchscreen then
still turned the view). Now each widget carries a property naming the filter on it, and
turning off looks at the views that are open now."""

import itertools

from . import warn

_ids = itertools.count(1)


def token(filt):
    """The filter's name for the property (given once)."""
    name = filt.objectName()
    if not name:
        name = "fission180-filter-%d" % next(_ids)
        filt.setObjectName(name)
    return name


def views():
    """(drawing area, viewer) widgets of every open 3D view; [] while the window is not
    there (orbit_ui._view_widgets)."""
    try:
        from .orbit_ui import _view_widgets

        return _view_widgets()
    except Exception:
        return []


def install(filt, key, prepare=None):
    """`filt` on every open view's drawing area and viewer that does not have it yet;
    `prepare(widget)` first (touch_ui: the drawing area takes touch). Returns how many it
    went on."""
    if filt is None:
        return 0
    name = token(filt)
    added = 0
    for widget in views():
        try:
            if widget.property(key) == name:
                continue
            if prepare is not None:
                prepare(widget)
            widget.installEventFilter(filt)
            widget.setProperty(key, name)
            added += 1
        except RuntimeError:
            pass  # the view of a design being closed
        except Exception as exc:
            warn("view filter %s: %s" % (key, exc))
    return added


def remove(filt, key, undo=None):
    """`filt` off every open view (and the property with it); `undo(widget)` after."""
    if filt is None:
        return
    name = token(filt)
    for widget in views():
        try:
            if widget.property(key) != name:
                continue
            widget.removeEventFilter(filt)
            widget.setProperty(key, None)
            if undo is not None:
                undo(widget)
        except RuntimeError:
            pass
        except Exception as exc:
            warn("view filter %s: %s" % (key, exc))


def on(widget, filt, key):
    """Whether `filt` is on `widget`."""
    try:
        return filt is not None and widget is not None and widget.property(key) == token(filt)
    except RuntimeError:
        return False


def count(filt, key):
    """How many open views' widgets carry `filt`."""
    return sum(1 for w in views() if on(w, filt, key))
