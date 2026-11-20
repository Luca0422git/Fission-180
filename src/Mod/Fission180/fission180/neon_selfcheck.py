# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon self-check (Fission 180 > Diagnostics > Neon self-check; neon-lights-design.md 6.13,
plan task B8).

For Luca's hardware checks: a sample part of about 3,000 faces is orbited 120 frames with the
effects off, with every effect on, and with Hologram on; the idle CPU use is measured for 5 s;
the rim-light shader's self-test, the Neon parts that failed and the computer's platform and
graphics card are listed. The result is plain text to copy and paste back.

It works in a design of its own that is closed afterwards without saving; the designs open
before stay as they were, and the effect and Hologram settings are put back.
"""

import platform
import statistics
import sys
import time

from . import log, warn

FRAMES = 120
WARMUP = 10
IDLE_S = 5.0
STEP_DEG = 3.0
FRAME_BUDGET = 0.10  # effects may add 10% frame time while orbiting
IDLE_BUDGET = 0.02  # about 2% of a core while idle
DOC_NAME = "Fission180NeonSelfCheck"


def sample_shape():
    """A "circuit board" of 500 small blocks of different heights: 3,000 faces."""
    import Part

    blocks = []
    for i in range(25):
        for j in range(20):
            height = 1.0 + ((i * 7 + j * 13) % 9) * 0.6
            blocks.append(Part.makeBox(3.2, 3.2, height, _vec(i * 4.0, j * 4.0, 0)))
    return Part.makeCompound(blocks)


def _vec(x, y, z):
    import FreeCAD as App

    return App.Vector(x, y, z)


def _pump(seconds=0.0):
    from .compat import QtWidgets

    end = time.perf_counter() + seconds
    QtWidgets.QApplication.processEvents()
    while time.perf_counter() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)  # on purpose: an idle window is what is measured


def _orbit(view, frames):
    """Seconds per frame of `frames` camera turns, each drawn before the next."""
    from pivy import coin

    from .compat import QtWidgets

    cam = view.getCameraNode()
    start = cam.orientation.getValue()
    step = coin.SbRotation(coin.SbVec3f(0, 0, 1), STEP_DEG * 3.14159265 / 180.0)
    times = []
    try:
        for i in range(WARMUP + frames):
            t0 = time.perf_counter()
            cam.orientation.setValue(cam.orientation.getValue() * step)
            view.redraw()
            QtWidgets.QApplication.processEvents()
            if i >= WARMUP:
                times.append(time.perf_counter() - t0)
    finally:
        cam.orientation.setValue(start)
    return times


def _frame_line(label, times):
    if not times:
        return "  %-26s (not measured)" % label
    ms = [t * 1000.0 for t in times]
    ms_sorted = sorted(ms)
    p95 = ms_sorted[min(len(ms_sorted) - 1, int(len(ms_sorted) * 0.95))]
    return "  %-26s median %6.2f ms  mean %6.2f ms  95%% %6.2f ms  worst %6.2f ms  (%d frames)" % (
        label, statistics.median(ms), statistics.mean(ms), p95, max(ms), len(ms))


def _idle_cpu(seconds):
    """Share of one CPU core the whole program used while nothing happened."""
    _pump(0.3)
    c0, t0 = time.process_time(), time.perf_counter()
    _pump(seconds)
    c1, t1 = time.process_time(), time.perf_counter()
    return max(0.0, (c1 - c0) / max(1e-6, (t1 - t0)))


def gpu_string(view=None):
    """The graphics card and OpenGL driver, as OpenGL reports them (a small context of our own,
    made the way Qt makes the 3D view's, so it names the same card and driver)."""
    try:
        from .compat import QtGui

        ctx = QtGui.QOpenGLContext()
        share = QtGui.QOpenGLContext.globalShareContext()
        if share is not None:
            ctx.setShareContext(share)
            ctx.setFormat(share.format())
        if not ctx.create():
            return "unknown (no OpenGL context)"
        surface = QtGui.QOffscreenSurface()
        surface.setFormat(ctx.format())
        surface.create()
        if not ctx.makeCurrent(surface):
            return "unknown (OpenGL context not usable)"
        try:
            f = ctx.functions()
            names = []
            for code in (0x1F00, 0x1F01, 0x1F02):  # GL_VENDOR, GL_RENDERER, GL_VERSION
                value = f.glGetString(code)
                if isinstance(value, (bytes, bytearray)):
                    value = value.decode("ascii", "replace")
                names.append(str(value) if value else "?")
            fmt = ctx.format()
            kinds = QtGui.QSurfaceFormat.OpenGLContextProfile
            profile = {kinds.CoreProfile: "core", kinds.CompatibilityProfile: "compatibility"}.get(
                fmt.profile(), "no profile")
            return "%s | %s | OpenGL %s (%s)" % (names[0], names[1], names[2], profile)
        finally:
            ctx.doneCurrent()
            surface.destroy()
    except Exception as exc:
        return "unknown (%s: %s)" % (type(exc).__name__, exc)


def _platform_lines(view):
    from .compat import QtCore, QtGui

    lines = []
    try:
        import FreeCAD as App

        from . import __version__

        fc = ".".join(str(p) for p in App.Version()[:3])
        lines.append("Fission 180 %s on FreeCAD %s" % (__version__, fc))
    except Exception:
        pass
    lines.append("Platform: %s (%s), Python %s, Qt %s" % (
        platform.platform(), platform.machine(), sys.version.split()[0], QtCore.qVersion()))
    try:
        app = QtGui.QGuiApplication.instance()
        screen = app.primaryScreen()
        size = screen.size()
        lines.append("Window system: %s, screen %dx%d at %.2fx" % (
            app.platformName(), size.width(), size.height(), screen.devicePixelRatio()))
    except Exception:
        pass
    lines.append("Graphics: %s" % gpu_string(view))
    return lines


def shader_line():
    """What the rim-light shader's self-test says (neon_shader, builder `bodies`)."""
    try:
        from . import neon_shader
    except ImportError:
        return "not in this version (no neon_shader)"
    except Exception as exc:
        return "could not load: %s" % exc
    test = getattr(neon_shader, "self_test", None)
    if test is None:
        return "no self-test in this version"
    try:
        result = test()
    except Exception as exc:
        return "FAILED (%s: %s)" % (type(exc).__name__, exc)
    if isinstance(result, tuple) and result:
        ok, why = bool(result[0]), " ".join(str(r) for r in result[1:])
    elif isinstance(result, dict):
        ok, why = bool(result.get("ok", result.get("passed"))), str(result.get("why", result.get("reason", "")))
    else:
        ok, why = bool(result), ""
    return ("passed" if ok else "FAILED") + (" (%s)" % why if why else "")


def _verdict(ratio, budget):
    return "OK" if ratio <= budget else "OVER BUDGET"


def run(progress=None):
    """Run the self-check and return its report (plain text). progress(text) is called between
    the stages (for a status line); nothing here raises."""
    say = progress or (lambda text: None)
    lines = ["Neon self-check (paste this back to Claude)", "=" * 44]
    try:
        lines += _run(say)
    except Exception as exc:
        warn("Neon self-check: %s" % exc)
        lines.append("The self-check stopped: %s: %s" % (type(exc).__name__, exc))
    report = "\n".join(lines)
    log("Neon self-check finished (the report is in the Diagnostics window)")
    return report


def _run(say):
    import FreeCAD as App
    import FreeCADGui as Gui

    from . import neon, neon_effects, neon_settings, theme

    out = []
    neon_on = theme.is_neon()
    out.append("Look: %s%s" % (theme.name(), "" if neon_on else " (switch to Neon Lights for the effect numbers)"))
    previous = App.ActiveDocument.Name if App.ActiveDocument else None
    hologram_before = bool(neon_settings.get("Hologram"))
    doc = App.newDocument(DOC_NAME)
    try:
        say("Making the sample part...")
        part = doc.addObject("Part::Feature", "NeonSample")
        part.Shape = sample_shape()
        doc.recompute()
        faces = len(part.Shape.Faces)
        view = Gui.getDocument(doc.Name).activeView()
        view.viewIsometric()
        view.fitAll()
        _pump(0.3)
        out += _platform_lines(view)
        out.append("Sample part: %d faces, %d frames per run, %.0f degrees a frame" % (faces, FRAMES, STEP_DEG))
        out.append("")
        out.append("Orbit, time per frame:")
        say("Orbit with the effects off...")
        neon_effects.measure(False)
        _pump(0.2)
        off = _orbit(view, FRAMES)
        out.append(_frame_line("effects off", off))
        on = holo = []
        if neon_on:
            say("Orbit with every effect on...")
            neon_effects.measure(True)
            _pump(0.2)
            before = neon_effects.stats()
            on = _orbit(view, FRAMES)
            after = neon_effects.stats()
            out.append(_frame_line("every effect on", on))
            painting = (after["paint_s"] - before["paint_s"]) * 1000.0 / max(1, len(on))
            share = painting / max(1e-6, statistics.median(off) * 1000.0)
            out.append("  %-26s %6.2f ms a frame (%d paints), %.1f%% of a frame with effects off" % (
                "  of which layer painting", painting, after["paints"] - before["paints"], 100 * share))
            say("Orbit with Hologram on...")
            from . import neon_view

            neon_view.set_hologram(True)
            _pump(0.3)
            holo = _orbit(view, FRAMES)
            out.append(_frame_line("effects + Hologram on", holo))
            neon_view.set_hologram(hologram_before)
            _pump(0.2)
        if off and on:
            ratio = statistics.median(on) / max(1e-9, statistics.median(off)) - 1.0
            out.append("  Effects add %+.1f%% per frame (budget %d%%): %s" % (
                100 * ratio, 100 * FRAME_BUDGET, _verdict(ratio, FRAME_BUDGET)))
        if off and holo:
            ratio = statistics.median(holo) / max(1e-9, statistics.median(off)) - 1.0
            out.append("  Effects + Hologram add %+.1f%% per frame" % (100 * ratio))
        out.append("")
        say("Idle CPU with the effects off (5 s)...")
        neon_effects.measure(False)
        idle_off = _idle_cpu(IDLE_S)
        out.append("Idle CPU (whole program, share of one core, %.0f s each):" % IDLE_S)
        out.append("  effects off        %5.1f%%" % (100 * idle_off))
        if neon_on:
            say("Idle CPU with the effects as set (5 s)...")
            neon_effects.refresh()
            neon_effects._state["force_active"] = True  # running as if the window were active
            neon_effects._pause_or_go()
            idle_on = _idle_cpu(IDLE_S)
            added = idle_on - idle_off
            band = " (rolling band on)" if neon_settings.get("ScanBand") else ""
            out.append("  effects as set     %5.1f%%%s" % (100 * idle_on, band))
            out.append("  Effects add %+.1f%% of a core (budget about %d%%): %s" % (
                100 * added, 100 * IDLE_BUDGET, _verdict(added, IDLE_BUDGET + 0.005)))
            st = neon_effects.stats()
            out.append("  Effects layer: %d paints, %d still-picture builds so far" % (st["paints"], st["rebuilds"]))
    finally:
        try:
            neon_settings.put("Hologram", hologram_before)
            neon_effects.refresh()
        except Exception as exc:
            warn("Neon self-check: put settings back: %s" % exc)
        try:
            App.closeDocument(doc.Name)
            if previous and previous in App.listDocuments():
                App.setActiveDocument(previous)
                Gui.setActiveDocument(previous)
        except Exception as exc:
            warn("Neon self-check: close the sample design: %s" % exc)
        _pump(0.1)
    out.append("")
    out.append("Rim-light shader self-test: %s" % shader_line())
    failed = neon.failed()
    if failed:
        out.append("Neon parts switched off:")
        out.extend("  - %s: %s" % (k, v) for k, v in sorted(failed.items()))
    else:
        out.append("Neon parts switched off: none")
    return out
