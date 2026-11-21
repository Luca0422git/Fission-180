# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights: UI sounds (docs/fission180/neon-lights-design.md 6.9, plan task B9).

Short synth blips (fission180/sounds/*.wav, made by tools/fission180/make_sounds.py) for a
button click, a menu opening, a command finished with OK, an error or warning message, and the
boot screen. Off by default (setting Sounds); the volume is the setting Volume (0-100).

Played without ever waiting for them, by the first way that works here:
1. Qt Multimedia (QSoundEffect) when PySide has it and the computer has a sound output (the
   official FreeCAD AppImage ships PySide6's QtMultimedia module but not Qt's library under
   it: the import fails and the next way is used). The module the probe found is the one
   played with;
2. on Windows, winsound.PlaySound(..., SND_ASYNC | SND_FILENAME);
3. on Linux, pw-play, paplay or aplay started with subprocess.Popen (never waited for;
   finished players are collected by a cheap timer, so none stays a zombie);
4. else nothing. play() never raises.

The way is chosen, and Qt's sound effects loaded, when Sounds comes on (prepare(), on the event
loop), not in the first click. A way that fails while playing is dropped with one warning and
the next way plays (the sound that failed included). Players without a volume option get a
copy of the sound at the volume, made once in Fission 180's folder of the person's FreeCAD data
folder.

The hooks (an application event filter) are installed only while Neon Lights and Sounds are
both on. Nothing plays while quiet() is in force (previews: the settings page's samples, the
preview picture of a save) or in tests unless a scenario switches sounds on itself.
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import time

from . import log, warn

NAMES = ("click", "menu", "done", "error", "boot")
SOUNDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
_GAP = 0.045  # seconds: the same sound again sooner than this is skipped (no machine-gunning)
_MAX_PROCS = 3  # players started and still running, at most
REAP_MS = 400  # finished players are collected this often while any runs
_LINUX_PLAYERS = ("pw-play", "paplay", "aplay")
_state = {
    "on": False,  # neon part enabled
    "filter": None,
    "backend": None,  # (kind, detail) once chosen; ("none", "") when silent
    "failed": set(),  # (kind, detail) of ways that failed this start: skipped from then on
    "qt": None,  # the QtMultimedia module the probe found (the one play uses)
    "effects": {},  # Qt: name -> QSoundEffect
    "reaper": None,  # a QTimer reaping finished players while any run
    "procs": [],
    "last": {},  # name -> time.monotonic() of the last play
    "quiet": 0,
    "played": [],  # (name, backend kind) of the last plays, for tests
}


def path(name):
    return os.path.join(SOUNDS, name + ".wav")


def _setting(name):
    try:
        from . import neon_settings

        return neon_settings.get(name)
    except Exception:
        from . import neon_settings

        return neon_settings.DEFAULTS[name]


def volume():
    try:
        return max(0, min(100, int(_setting("Volume"))))
    except Exception:
        return 60


def wanted():
    """Neon Lights on and the person switched sounds on."""
    try:
        from . import theme

        return bool(_state["on"] and theme.is_neon() and _setting("Sounds"))
    except Exception:
        return False


# -- backends ------------------------------------------------------------------------------
def _qt_multimedia():
    """The QtMultimedia module, from FreeCAD's PySide shim or PySide6 (the official AppImage
    ships PySide6's module without Qt's library under it: the import fails), or None."""
    for package in ("PySide", "PySide6"):
        try:
            module = __import__(package + ".QtMultimedia", fromlist=["QtMultimedia"])
            if hasattr(module, "QSoundEffect") and hasattr(module, "QMediaDevices"):
                return module
        except Exception:
            continue
    return None


def _qt_backend():
    """("qt", "") when Qt Multimedia imports and has a sound output, else None. The module
    found is kept: play uses that one, never another import."""
    module = _qt_multimedia()
    if module is None:
        return None
    try:
        if not module.QMediaDevices.audioOutputs():
            return None
    except Exception:
        return None
    _state["qt"] = module
    return ("qt", "")


def _windows_backend():
    if not sys.platform.startswith("win"):
        return None
    try:
        import winsound  # noqa: F401
    except Exception:
        return None
    return ("winsound", "")


def _linux_backend():
    if not sys.platform.startswith("linux"):
        return None
    for exe in _LINUX_PLAYERS:
        found = shutil.which(exe)
        if found and ("cmd", found) not in _state["failed"]:
            return ("cmd", found)
    return None


BACKENDS = (_qt_backend, _windows_backend, _linux_backend)


def backend():
    """(kind, detail): ("qt", ""), ("winsound", ""), ("cmd", "/usr/bin/pw-play") or
    ("none", ""). Chosen once per start (reset() chooses again); a way that failed is skipped
    and the next one is chosen (_failed())."""
    if _state["backend"] is None:
        chosen = ("none", "")
        for probe in BACKENDS:
            try:
                found = probe()
            except Exception:
                found = None
            if found and tuple(found) not in _state["failed"]:
                chosen = tuple(found)
                break
        _state["backend"] = chosen
        log("Neon Lights: sounds through %s" % (chosen[1] or chosen[0]))
    return _state["backend"]


def prepare():
    """Choose the way to play now and get it ready (Qt Multimedia: the sound effects loaded),
    so the first click does not pay for it: starting Qt Multimedia can stall the window.
    Called when Sounds comes on (enable/refresh), on the event loop. Never raises."""
    try:
        kind, _detail = backend()
        if kind == "qt":
            for name in NAMES:
                _effect(name)
    except Exception as exc:
        _failed(exc, "getting sounds ready")


def reset():
    """Forget the chosen way to play (tests; after a sound device came or went)."""
    _state["backend"] = None
    _state["failed"] = set()
    _state["effects"] = {}
    _state["qt"] = None


def _failed(exc, what):
    """The chosen way failed: one warning, then the next way (or silence) from now on."""
    chosen = _state["backend"] or ("none", "")
    if chosen[0] != "none":
        _state["failed"].add(chosen)
    _state["backend"] = None
    _state["effects"] = {}
    nxt = backend()
    warn("Neon Lights: sound %s through %s: %s (now through %s)"
         % (what, chosen[1] or chosen[0], exc, nxt[1] or nxt[0]))
    return nxt


def _cache_folder():
    """Where the volume copies go: Fission 180's folder in the person's FreeCAD data folder
    (per user, not the shared temporary folder); outside FreeCAD (tests) a private folder."""
    try:
        import FreeCAD as App

        return os.path.join(App.getUserAppDataDir(), "Fission180", "sounds")
    except Exception:
        if _state.get("cache") is None:
            _state["cache"] = tempfile.mkdtemp(prefix="fission180-sounds-")
        return _state["cache"]


def _scaled(name, vol):
    """A copy of the sound at `vol` percent (for players without a volume option), made once
    in the temporary folder."""
    if vol >= 100:
        return path(name)
    import array
    import wave

    folder = os.path.join(_cache_folder(), str(vol))
    target = os.path.join(folder, name + ".wav")
    if os.path.exists(target):
        return target
    os.makedirs(folder, mode=0o700, exist_ok=True)
    with wave.open(path(name), "rb") as src:
        params = src.getparams()
        frames = array.array("h", src.readframes(src.getnframes()))
    if sys.byteorder != "little":
        frames.byteswap()
    frames = array.array("h", (int(v * vol / 100) for v in frames))
    if sys.byteorder != "little":
        frames.byteswap()
    handle, partial = tempfile.mkstemp(prefix=name + ".", suffix=".part", dir=folder)
    try:
        with os.fdopen(handle, "wb") as raw, wave.open(raw, "wb") as dst:
            dst.setparams(params)
            dst.writeframes(frames.tobytes())
        os.replace(partial, target)
    except Exception:
        try:
            os.remove(partial)
        except OSError:
            pass
        raise
    return target


def _reap():
    """Finished players collected (no zombie processes). Returns how many still run."""
    _state["procs"] = [p for p in _state["procs"] if p.poll() is None]
    return len(_state["procs"])


def _reap_soon():
    """A cheap timer collects the players as they finish (every REAP_MS while any runs, then
    it stops), so none stays a zombie until the next sound."""
    try:
        from PySide import QtCore, QtWidgets

        if QtWidgets.QApplication.instance() is None:
            return
        timer = _state["reaper"]
        if timer is None:
            timer = QtCore.QTimer()
            timer.setInterval(REAP_MS)
            timer.timeout.connect(_reap_tick)
            _state["reaper"] = timer
        if not timer.isActive():
            timer.start()
    except Exception:
        pass  # outside Qt (tests): the next sound reaps


def _reap_tick():
    try:
        if not _reap() and _state["reaper"] is not None:
            _state["reaper"].stop()
    except Exception as exc:
        warn("Neon Lights: sounds: %s" % exc)


def _effect(name):
    module = _state["qt"]
    effect = _state["effects"].get(name)
    if effect is None:
        # QUrl from the same package as the module the probe found
        package = module.__name__.rsplit(".", 1)[0]
        QtCore = __import__(package + ".QtCore", fromlist=["QtCore"])  # noqa: N806

        effect = module.QSoundEffect()
        effect.setSource(QtCore.QUrl.fromLocalFile(path(name)))
        _state["effects"][name] = effect
    return effect


def _play_qt(name, vol):
    if _state["qt"] is None:
        raise RuntimeError("Qt Multimedia was not found by the probe")
    effect = _effect(name)
    effect.setVolume(vol / 100.0)
    effect.play()


def _play_winsound(name, vol):
    import winsound

    flags = winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT
    winsound.PlaySound(_scaled(name, vol), flags)


def _play_cmd(exe, name, vol):
    _reap()
    if len(_state["procs"]) >= _MAX_PROCS:
        return False
    base = os.path.basename(exe)
    if base == "pw-play":
        args = [exe, "--volume=%.2f" % (vol / 100.0), path(name)]
    elif base == "paplay":
        args = [exe, "--volume=%d" % int(65536 * vol / 100), path(name)]
    else:  # aplay has no volume option
        args = [exe, "-q", _scaled(name, vol)]
    kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    _state["procs"].append(subprocess.Popen(args, **kwargs))
    _reap_soon()
    return True


def play(name, force=False):
    """Play one of NAMES without waiting. Silent (returns None) when sounds are off, Neon
    Lights is off, a preview is being drawn (quiet()), there is no way to play, or anything
    goes wrong. force=True: play even when the setting is off (the settings page's "test"
    button); never during quiet()."""
    try:
        if name not in NAMES or _state["quiet"]:
            return None
        if not force and not wanted():
            return None
        try:
            from . import theme

            if theme._neon.get("normal"):  # a save drawing its preview picture
                return None
        except Exception:
            pass
        now = time.monotonic()
        if now - _state["last"].get(name, -1.0) < _GAP:
            return None
        vol = volume()
        if vol <= 0 or not os.path.exists(path(name)):
            return None
        _state["last"][name] = now
        for _attempt in range(len(BACKENDS) + len(_LINUX_PLAYERS) + 1):
            kind, detail = backend()
            if kind == "none":
                return None
            try:
                if not _play_with(kind, detail, name, vol):
                    return None
            except Exception as exc:
                _failed(exc, name)  # the next way plays it
                continue
            _state["played"].append((name, kind))
            del _state["played"][:-20]
            return kind
        return None
    except Exception as exc:
        warn("Neon Lights: sound %s: %s (sounds silent until the next start)" % (name, exc))
        _state["backend"] = ("none", "")
        return None


def _play_with(kind, detail, name, vol):
    if kind == "qt":
        _play_qt(name, vol)
    elif kind == "winsound":
        _play_winsound(name, vol)
    elif kind == "cmd":
        return _play_cmd(detail, name, vol)
    else:
        return False
    return True


@contextlib.contextmanager
def quiet():
    """No sound while this is in force (previews)."""
    _state["quiet"] += 1
    try:
        yield
    finally:
        _state["quiet"] -= 1


def played():
    """The last sounds played as (name, backend kind), newest last (tests)."""
    return list(_state["played"])


# -- the hooks -----------------------------------------------------------------------------
def _sound_for(obj, event):
    """Which sound an event should make, or None. Pure enough to test with stand-ins."""
    from PySide import QtCore, QtWidgets

    kind = event.type()
    if kind == QtCore.QEvent.Show:
        if isinstance(obj, QtWidgets.QMenu):
            return "menu"
        if isinstance(obj, QtWidgets.QMessageBox):
            icon = obj.icon()
            if icon in (QtWidgets.QMessageBox.Critical, QtWidgets.QMessageBox.Warning):
                return "error"
        return None
    if kind == QtCore.QEvent.MouseButtonRelease:
        if not isinstance(obj, QtWidgets.QAbstractButton) or not obj.isEnabled():
            return None
        if event.button() != QtCore.Qt.LeftButton:
            return None
        try:
            pos = event.position().toPoint()
        except AttributeError:
            pos = event.pos()
        if not obj.rect().contains(pos):
            return None  # released outside: not a click
        if _is_ok(obj):
            return "done"
        return "click"
    return None


def _is_ok(button):
    """The OK (accept) button of a command's dialog or a button box."""
    from PySide import QtWidgets

    parent = button.parentWidget()
    if isinstance(parent, QtWidgets.QDialogButtonBox):
        role = parent.buttonRole(button)
        return role in (QtWidgets.QDialogButtonBox.AcceptRole, QtWidgets.QDialogButtonBox.YesRole)
    return False


def _filter_class():
    from PySide import QtCore, QtWidgets

    # Every event of the application passes this filter while Sounds is on, so the test that
    # throws almost all of them away comes first and is as cheap as Python allows: the type
    # as a plain int against a frozenset (no enum objects made per event), then the class.
    wanted_types = frozenset(int(t.value if hasattr(t, "value") else t) for t in (
        QtCore.QEvent.Show, QtCore.QEvent.MouseButtonRelease))
    show = int(getattr(QtCore.QEvent.Show, "value", QtCore.QEvent.Show))
    shown_classes = (QtWidgets.QMenu, QtWidgets.QMessageBox)
    button_class = QtWidgets.QAbstractButton

    class _Hooks(QtCore.QObject):
        def eventFilter(self, obj, event):  # noqa: N802 (Qt's name)
            try:
                kind = event.type()
                kind = int(getattr(kind, "value", kind))
                if kind not in wanted_types:
                    return False
                if not isinstance(obj, shown_classes if kind == show else button_class):
                    return False
                name = _sound_for(obj, event)
                if name:
                    play(name)
            except Exception as exc:
                warn("Neon Lights: sound hook: %s" % exc)
                _remove_filter()
            return False

    return _Hooks


def _install_filter():
    if _state["filter"] is not None:
        return
    from PySide import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    hooks = _filter_class()()
    app.installEventFilter(hooks)
    _state["filter"] = hooks


def _remove_filter():
    hooks = _state["filter"]
    _state["filter"] = None
    if hooks is None:
        return
    try:
        from PySide import QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.removeEventFilter(hooks)
    except Exception:
        pass


def hooked():
    """True while the event filter is installed (tests)."""
    return _state["filter"] is not None


def _follow():
    if wanted():
        _install_filter()
        _prepare_soon()
    else:
        _remove_filter()


def _prepare_soon():
    """The way to play chosen and made ready on the event loop when Sounds comes on, not in
    the first click (prepare())."""
    if _state["backend"] is not None:
        return
    try:
        from PySide import QtCore

        QtCore.QTimer.singleShot(0, prepare)
    except Exception:
        prepare()


def enable():
    _state["on"] = True
    _follow()


def disable():
    _state["on"] = False
    _remove_filter()
    try:
        _reap()
        if _state["reaper"] is not None:
            _state["reaper"].stop()
    except Exception:
        pass
    for effect in _state["effects"].values():
        try:
            effect.stop()
        except Exception:
            pass
    _state["effects"] = {}


def refresh():
    """A setting changed (Sounds, Volume): the hooks follow."""
    _follow()
