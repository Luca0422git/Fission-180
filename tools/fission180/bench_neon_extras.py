# SPDX-License-Identifier: LGPL-2.1-or-later
"""Measures what Neon Lights' extras cost the window (neon_home, neon_boot, neon_sound).

Run it with FreeCAD's own Python, off screen (no window, no FreeCAD started):

  FC=.fission180-cache/freecad/squashfs-root
  QT_QPA_PLATFORM=offscreen PYTHONPATH=$FC/usr/Ext:src/Mod/Fission180 \\
      $FC/usr/bin/python tools/fission180/bench_neon_extras.py [--root DIR] [--frames N]

--root: a folder holding another copy of the `fission180` package (for example an older
commit's, from `git archive`) to measure that one instead.

It prints, for 1600x900 and 3000x1700:
- Home's moving background: milliseconds of work per frame (the frame's own work and Qt
  painting it, the see-through list over it included) and the share of one core that makes
  at the background's frame rate;
- the boot screen: milliseconds per frame in each part of its timeline;
- the sound hook: microseconds the application event filter adds to each event.
"""

import argparse
import os
import sys
import time


def _args():
    a = argparse.ArgumentParser()
    a.add_argument("--root", default=None)
    a.add_argument("--frames", type=int, default=120)
    return a.parse_args()


ARGS = _args()
if ARGS.root:
    sys.path.insert(0, os.path.abspath(ARGS.root))

from PySide import QtCore, QtWidgets  # noqa: E402

APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from fission180 import neon_boot, neon_home, neon_sound  # noqa: E402

COLOURS = {"background": "#0b0d17", "primary": "#ff2a6d", "secondary": "#05d9e8",
           "grid": "#05d9e8", "text": "#e8f6ff", "alert": "#ff3b3b"}
neon_home._colours = lambda: dict(COLOURS)
neon_boot._palette = lambda: dict(COLOURS)
neon_boot._fonts = lambda: ("Monospace", "Sans Serif")
SIZES = ((1600, 900), (3000, 1700))


def _flush():
    APP.processEvents()


def _home_page(w, h):
    """A stand-in for Home: a page with a see-through scroll area holding a list of rows."""
    page = QtWidgets.QWidget()
    page.setObjectName("Fission180Home")
    page.resize(w, h)
    lay = QtWidgets.QHBoxLayout(page)
    scroll = QtWidgets.QScrollArea()
    scroll.setObjectName("Fission180HomeScroll")
    scroll.setWidgetResizable(True)
    rows = QtWidgets.QWidget()
    rows.setObjectName("Fission180HomeRows")
    col = QtWidgets.QVBoxLayout(rows)
    for i in range(40):
        col.addWidget(QtWidgets.QLabel("Design %02d  -  last opened today  -  12 bodies" % i))
    scroll.setWidget(rows)
    lay.addWidget(scroll, 3)
    lay.addWidget(QtWidgets.QLabel("AI"), 1)
    page.setStyleSheet(neon_home.SEE_THROUGH_QSS)
    page.scroll = scroll
    page.show()
    _flush()
    return page


def bench_home(w, h, frames):
    page = _home_page(w, h)
    b = neon_home._backdrop_class()(page)
    _flush()
    fps = neon_home.FPS
    new = hasattr(b, "advance")
    start = time.perf_counter()
    for i in range(frames):
        if new:
            b.advance(i / float(fps))
        else:  # the old _tick's work (it reads its own clock)
            b.update()
            for vp in b.viewports():
                vp.update()
        _flush()
    per = (time.perf_counter() - start) * 1000.0 / frames
    page.close()
    page.deleteLater()
    _flush()
    return per, fps


PHASES = (("mark glitching in", 0, 520), ("typing, bar filling", 520, 1750),
          ("bar finishing", 1750, 2000), ("fade", 2000, 2499))


def bench_boot(w, h, frames):
    """ms a frame in each part of the boot screen's timeline (the window under it: a stand-in
    with a column of buttons)."""
    window = QtWidgets.QWidget()
    window.resize(w, h)
    lay = QtWidgets.QVBoxLayout(window)
    for i in range(30):
        lay.addWidget(QtWidgets.QPushButton("Tool %d" % i))
    window.show()
    _flush()
    b = neon_boot._widget_class()(window)
    b.show()
    _flush()
    new = hasattr(b, "step")
    out = []
    for _name, t0, t1 in PHASES:
        start = time.perf_counter()
        for i in range(frames):
            t = t0 + (t1 - t0) * i / float(frames)
            if new:
                b.step(t)
            else:  # the old _tick's work (it reads its own clock)
                b.t = t
                b.update()
            _flush()
        out.append((time.perf_counter() - start) * 1000.0 / frames)
    b.timer.stop()
    window.close()
    window.deleteLater()
    _flush()
    return out


def bench_filter(events=200000):
    target = QtCore.QObject()
    kinds = [QtCore.QEvent.Type.Move, QtCore.QEvent.Type.Paint, QtCore.QEvent.Type.Show,
             QtCore.QEvent.Type.MouseMove, QtCore.QEvent.Type.User]

    def run():
        evs = [QtCore.QEvent(kinds[i % len(kinds)]) for i in range(len(kinds))]
        start = time.perf_counter()
        for i in range(events):
            QtCore.QCoreApplication.sendEvent(target, evs[i % len(evs)])
        return (time.perf_counter() - start) * 1e6 / events

    base = run()
    hooks = neon_sound._filter_class()()
    APP.installEventFilter(hooks)
    with_filter = run()
    APP.removeEventFilter(hooks)
    return base, with_filter


def main():
    print("Home background (stand-in Home page, see-through list):")
    for w, h in SIZES:
        per, fps = bench_home(w, h, ARGS.frames)
        print("  %dx%d: %.2f ms a frame at %d fps = %.1f%% of a core" % (w, h, per, fps, per * fps / 10.0))
    print("Boot screen (ms a frame; %d fps):" % neon_boot.FPS)
    for w, h in SIZES:
        out = bench_boot(w, h, ARGS.frames // 4)
        print("  %dx%d: " % (w, h) + ", ".join("%s %.2f" % (p[0], ms) for p, ms in zip(PHASES, out)))
    base, with_filter = bench_filter()
    print("Sound hook: %.2f us an event without it, %.2f us with it (+%.2f us)"
          % (base, with_filter, with_filter - base))


main()
