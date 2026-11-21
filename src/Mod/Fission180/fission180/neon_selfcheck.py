# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon self-check (Fission 180 > Diagnostics > Neon self-check; neon-lights-design.md 6.13,
plan task B8).

For Luca's hardware checks: a sample part of about 3,000 faces is orbited 120 frames with the
effects off, with every effect on, with Sounds on too, and with Hologram on; the idle CPU use is
measured for 5 s; the rim-light shader's self-test, the Neon parts that failed and the
computer's platform and graphics card are listed. The result is plain text to copy and paste
back, with a verdict in plain words.

How the speed is judged: a frame's time on the clock is held to the screen's refresh rate on most
graphics cards (vsync: 60 frames a second means at least 16.7 ms, whatever the work), so two runs
can look the same while one works much harder. The verdict therefore uses the processor time of
the program's main thread per frame (time.thread_time(): Qt, Coin and the effects all run
there), next to how often the effects layer painted during the orbit and how long that took.

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


class Run:
    """One orbit: per frame the clock time (`wall`) and the main thread's processor time
    (`cpu`), in seconds, and the effects layer's paints and painting time during it."""

    def __init__(self):
        self.wall, self.cpu = [], []
        self.paints = 0
        self.band = 0  # frames of the rolling band meanwhile (each repaints its strip)
        self.paint_s = 0.0

    def frames(self):
        return len(self.wall)

    def add(self, other):
        self.wall += other.wall
        self.cpu += other.cpu
        self.paints += other.paints
        self.band += other.band
        self.paint_s += other.paint_s


def _quiet(limit_s=5.0):
    """Wait (at most limit_s) until the window has stopped moving: no effects-layer paint for
    0.5 s. A design just opened slides its panels in for a moment; those repaints are not the
    orbit's."""
    from . import neon_effects

    end = time.perf_counter() + limit_s
    last, still_since = neon_effects.stats()["paints"], time.perf_counter()
    while time.perf_counter() < end:
        _pump(0.05)
        now = neon_effects.stats()["paints"]
        if now != last:
            last, still_since = now, time.perf_counter()
        elif time.perf_counter() - still_since >= 0.5:
            return


def _orbit(view, frames, warmup=WARMUP):
    """`frames` camera turns, each drawn before the next (a Run), after `warmup` turns."""
    from pivy import coin

    from . import neon_effects
    from .compat import QtWidgets

    cam = view.getCameraNode()
    start = cam.orientation.getValue()
    step = coin.SbRotation(coin.SbVec3f(0, 0, 1), STEP_DEG * 3.14159265 / 180.0)
    run = Run()
    before = None
    band0 = 0
    try:
        for i in range(warmup + frames):
            if i == warmup:
                before = neon_effects.stats()
                band0 = neon_effects.band_steps()
            t0, c0 = time.perf_counter(), time.thread_time()
            cam.orientation.setValue(cam.orientation.getValue() * step)
            view.redraw()
            QtWidgets.QApplication.processEvents()
            if i >= warmup:
                run.wall.append(time.perf_counter() - t0)
                run.cpu.append(time.thread_time() - c0)
        after = neon_effects.stats()
        run.paints = after["paints"] - before["paints"]
        run.paint_s = after["paint_s"] - before["paint_s"]
        run.band = neon_effects.band_steps() - band0
    finally:
        cam.orientation.setValue(start)
    return run


def _median_ms(values):
    return statistics.median(values) * 1000.0 if values else 0.0


def _frame_line(label, run):
    if not run or not run.frames():
        return "  %-28s (not measured)" % label
    wall = sorted(t * 1000.0 for t in run.wall)
    p95 = wall[min(len(wall) - 1, int(len(wall) * 0.95))]
    n = run.frames()
    band = " (rolling band %d frames)" % run.band if run.band else ""
    return ("  %-28s processor %6.2f ms   clock %6.2f ms (95%% %6.2f, worst %6.2f)   "
            "layer %d paints %5.2f ms%s   (%d frames)") % (
        label, _median_ms(run.cpu), _median_ms(run.wall), p95, wall[-1],
        run.paints, run.paint_s * 1000.0 / max(1, n), band, n)


def _ratio(run, base):
    return _median_ms(run.cpu) / max(1e-6, _median_ms(base.cpu)) - 1.0


def _refresh_hz():
    try:
        from .compat import QtGui

        return float(QtGui.QGuiApplication.primaryScreen().refreshRate())
    except Exception:
        return 0.0


def _vsync_note(base):
    """A line when the clock times look held to the screen's refresh rate (or None)."""
    hz = _refresh_hz()
    if hz <= 1 or not base.frames():
        return None
    period = 1000.0 / hz
    wall = _median_ms(base.wall)
    if abs(wall - period) <= 0.08 * period:
        return ("  (the clock times sit at the screen's %.0f Hz refresh: the graphics card waits for "
                "the screen, so they cannot show the effects' cost; the processor time does)" % hz)
    return None


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


BLOCKS = 6  # each setting's 120 frames are taken in 6 blocks of 20, in turn with the others
BLOCK_WARMUP = 3
LABELS = {
    "off": "effects off",
    "on": "every effect on",
    "band": "  + the rolling band",
    "sounds": "effects + Sounds on",
    "holo": "effects + Hologram on",
    "forced": "  (3D-view part forced on)",
}


def _sounds_follow():
    try:
        from . import neon_sound

        neon_sound.refresh()
    except Exception as exc:
        warn("Neon self-check: sounds: %s" % exc)


def _setting(name, neon_effects, neon_settings, hologram_before):
    """Put the effects, Sounds and Hologram as the run `name` wants them."""
    from . import neon_view, theme

    if name == "off":
        neon_effects.measure(False)
    else:
        neon_effects.measure(True, band=name == "band")
        neon_effects.set_view_part(True if name == "forced" else None)
    sounds = name == "sounds"
    if bool(neon_settings.get("Sounds")) != sounds:
        neon_settings.put("Sounds", sounds)
        _sounds_follow()
    if theme.is_neon():
        neon_view.set_hologram(name == "holo")


def _view_part_words(neon_effects):
    if neon_effects.view_part_on():
        return "drawn by the 3D view itself (on the graphics card)"
    cfg = neon_effects._state.get("cfg") or {}
    if cfg.get("view_s", 1) <= 0:
        return "none (View strength 0)"
    if neon_effects.software_gl():
        return "skipped: this computer draws OpenGL without a graphics card (software)"
    return "none"


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
        _quiet()  # (a design just opened slides its panels in for a moment)
        names = ["off"]
        if neon_on:
            names += ["on", "band", "sounds", "holo"]
            neon_effects.measure(True)
            if neon_effects.software_gl() and not neon_effects.view_part_on():
                names.append("forced")  # what the part over the 3D view would cost here
            out.append("  Effects over the 3D view: %s" % _view_part_words(neon_effects))
        runs = {name: Run() for name in names}
        sounds_before = bool(neon_settings.get("Sounds"))
        try:
            # short blocks taken in turn: the computer's own ups and downs (other programs,
            # heat) fall on every setting alike instead of on one run
            for block in range(BLOCKS):
                for name in names:
                    say("Orbit, %s (%d of %d)..." % (LABELS[name], block + 1, BLOCKS))
                    _setting(name, neon_effects, neon_settings, hologram_before)
                    runs[name].add(_orbit(view, FRAMES // BLOCKS, warmup=BLOCK_WARMUP))
        finally:
            _setting("off", neon_effects, neon_settings, hologram_before)
            neon_settings.put("Sounds", sounds_before)
            _sounds_follow()
        off = runs.pop("off")
        out.append(_frame_line("effects off", off))
        for name in names[1:]:
            out.append(_frame_line(LABELS[name], runs[name]))
        note = _vsync_note(off)
        if note:
            out.append(note)
        if runs:
            out.append("")
            out.append("Processor time per frame against effects off (budget +%d%%):" % (100 * FRAME_BUDGET))
            for key in ("on", "band", "sounds", "holo", "forced"):
                label = LABELS[key]
                if key in runs:
                    ratio = _ratio(runs[key], off)
                    out.append("  %-28s %+6.1f%%  %s" % (label, 100 * ratio, _verdict(ratio, FRAME_BUDGET)))
            verdicts = [_ratio(runs[k], off) for k in ("on", "sounds") if k in runs]
            worst = max(verdicts)
            other = max(runs[k].paints - runs[k].band for k in ("on", "sounds") if k in runs)
            out.append("")
            if worst <= FRAME_BUDGET:
                out.append("VERDICT: the effects fit the speed budget on this computer: turning the view")
                out.append("costs %+.0f%% processor time per frame (at most +%d%% allowed); the effects layer"
                           % (100 * worst, 100 * FRAME_BUDGET))
                out.append("repainted %d times in %d frames besides the rolling band's own frames."
                           % (max(0, other), FRAMES))
            else:
                out.append("VERDICT: the effects are OVER the speed budget on this computer: turning the view")
                out.append("costs %+.0f%% processor time per frame (at most +%d%% allowed). Please paste this"
                           % (100 * worst, 100 * FRAME_BUDGET))
                out.append("report back; meanwhile Settings > Neon Lights > View strength 0 makes the")
                out.append("effects over the 3D view free.")
            if "band" in runs:
                ratio = _ratio(runs["band"], off)
                out.append("The rolling band (Settings > Neon Lights > Moving scan band, off unless switched")
                out.append("on) is judged on its own: %+.0f%% (%s). It moves 25 times a second, and each"
                           % (100 * ratio, "within the budget" if ratio <= FRAME_BUDGET else "over the budget"))
                out.append("move makes the window put its whole picture together again.")
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
            if theme.is_neon():
                from . import neon_view

                neon_view.set_hologram(hologram_before)
            else:
                neon_settings.put("Hologram", hologram_before)
            neon_effects.set_view_part(None)
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
