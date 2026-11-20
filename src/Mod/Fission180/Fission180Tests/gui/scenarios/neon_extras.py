# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' extras (neon-lights-design.md 6.8, 6.9; plan task B9), with real clicks.

1. The boot screen: never on its own in tests; asked for, it covers the loaded window, types its
   lines and fills its bar; a click skips it, and so does a key.
2. UI sounds: no hook while Sounds is off (the default); on, a menu opening, a button click,
   a command's OK and a warning message each play their sound (through a stand-in player);
   with this machine's real ways to play (xvfb: no sound device) play() never raises.
3. The animated Home: behind Home's page while Home is in front, at most 30 frames a second;
   stopped when the design's tab is clicked, running again back on Home; the setting off
   takes it away.
4. Back to Dark: no boot screen, no sound hook, no Home background is left.
"""

import os

import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

s = {}


def set_preset(key):
    from fission180 import neon_settings, preferences_ui

    neon_settings.put("Preset", key)
    preferences_ui._apply("neon")
    QtWidgets.QApplication.processEvents()


# -- 1. the boot screen --------------------------------------------------------------------
def setup():
    lc.setup()
    from fission180 import neon_boot, neon_sound

    lc.set_look("neon")
    h.check("tests never get the boot screen on their own", neon_boot.widget() is None)
    h.check("... nor when asked without force", neon_boot.show() is None)
    h.check("sounds are off by default: no hook", not neon_sound.hooked())


setup.done = lambda: __import__("fission180.theme").theme.is_neon()
setup.done_what = "Neon Lights to be on"


def boot_starts():
    from fission180 import neon_boot

    s["boot"] = neon_boot.show(force=True)
    h.check("the boot screen is up", neon_boot.widget() is not None)


def _boot_far():
    from fission180 import neon_boot

    w = neon_boot.widget()
    # the bar is past half and the text lines are typed (the screen's own clock)
    return w is not None and w.t >= 1450


boot_starts.done = _boot_far
boot_starts.done_what = "the boot screen to type its lines and fill half its bar"
boot_starts.while_busy = True  # its 30 fps timer runs


def boot_shown():
    from fission180 import neon_boot

    w = neon_boot.widget()
    if w is None:
        h.check("the boot screen is still up", False)
        return
    window = Gui.getMainWindow()
    h.check("it covers the whole window", w.geometry() == window.rect(), (w.geometry(), window.rect()))
    h.check("... painted frames", w.frames > 5, w.frames)
    h.check("... typed lines", len(neon_boot.typed(w.t)) >= 3, neon_boot.typed(w.t))
    h.check("... a lit bar", neon_boot.segments(w.t) > neon_boot.SEGMENTS // 2, neon_boot.segments(w.t))
    h.check("... the window's design is loaded behind it", Gui.ActiveDocument is not None)
    h.shot("boot")
    s["shot_boot"] = True


boot_shown.while_busy = True


def boot_click():
    from fission180 import neon_boot

    w = neon_boot.widget()
    if w is not None:
        wi.click(w, QtCore.QPoint(w.width() // 3, w.height() // 3))


boot_click.done = lambda: __import__("fission180.neon_boot").neon_boot.widget() is None
boot_click.done_what = "a click to skip the boot screen"
boot_click.while_busy = True


def boot_again_for_a_key():
    from fission180 import neon_boot

    h.check("a click skipped it before its end", s["boot"] is not None)
    neon_boot.show(force=True)


boot_again_for_a_key.done = lambda: __import__("fission180.neon_boot").neon_boot.widget() is not None
boot_again_for_a_key.done_what = "the boot screen to come up again"
boot_again_for_a_key.while_busy = True


def boot_key():
    from fission180 import neon_boot

    w = neon_boot.widget()
    if w is not None:
        wi_key(w, QtCore.Qt.Key_Space)


def wi_key(widget, key):
    from PySide6 import QtTest

    QtTest.QTest.keyClick(widget, key)


boot_key.done = lambda: __import__("fission180.neon_boot").neon_boot.widget() is None
boot_key.done_what = "a key to skip the boot screen"
boot_key.while_busy = True


# -- 2. sounds -----------------------------------------------------------------------------
def sounds_on():
    from fission180 import neon_settings, neon_sound

    neon_settings.put("Sounds", True)
    neon_sound.refresh()
    h.check("Sounds on: the hook is in", neon_sound.hooked())
    # A stand-in player (exits at once), so the test hears nothing and needs no sound card.
    true = "/bin/true" if os.path.exists("/bin/true") else "/usr/bin/true"
    s["backends"] = neon_sound.BACKENDS
    neon_sound.reset()
    neon_sound.BACKENDS = (lambda: ("cmd", true),)
    neon_sound._state["played"] = []


def _played(name):
    from fission180 import neon_sound

    return any(n == name for n, _kind in neon_sound.played())


def menu_sound():
    button = lc.group_label("create")
    h.check("the CREATE drop-down is there", button is not None)
    if button is None:
        return
    h.when(lambda: QtWidgets.QApplication.activePopupWidget() is not None,
           lambda: QtWidgets.QApplication.activePopupWidget().close(), "the CREATE menu")
    wi.click(button)


menu_sound.done = lambda: _played("menu") and QtWidgets.QApplication.activePopupWidget() is None
menu_sound.done_what = "the menu sound, and the menu closed"


def click_sound():
    from fission180 import home_ui, neon_sound

    neon_sound._state["last"] = {}
    home_ui.show()


click_sound.done = lambda: __import__("fission180.home_ui").home_ui.is_active()
click_sound.done_what = "Home in front"


def click_a_button():
    from fission180 import home_ui

    page = home_ui.view()
    # The search box's neighbour "Preferences" opens a window; "+ Connect" too. The New design
    # button makes a design: a plain click with a sound, then the design is closed after.
    s["docs_before"] = set(__import__("FreeCAD").listDocuments())
    wi.click(page.new_button)


click_a_button.done = lambda: _played("click") and len(__import__("FreeCAD").listDocuments()) > len(s["docs_before"])
click_a_button.done_what = "the click sound and the new design"


def ok_sound():
    import FreeCAD as App

    for name in set(App.listDocuments()) - s["docs_before"]:
        App.closeDocument(name)
    dialog = QtWidgets.QDialog(Gui.getMainWindow())
    dialog.setObjectName("Fission180TestOkDialog")
    box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, dialog)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(QtWidgets.QLabel("A command's dialog"))
    layout.addWidget(box)
    dialog.show()
    s["dialog"] = dialog
    s["ok"] = box.button(QtWidgets.QDialogButtonBox.Ok)


ok_sound.done = lambda: s["ok"].isVisible()
ok_sound.done_what = "the dialog with OK"


def press_ok():
    wi.click(s["ok"])


press_ok.done = lambda: _played("done") and not s["dialog"].isVisible()
press_ok.done_what = "the 'done' sound and the dialog closed by OK"


def warning_sound():
    box = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, "Fission 180", "A warning",
                                QtWidgets.QMessageBox.Ok, Gui.getMainWindow())
    box.setModal(False)
    box.show()
    s["warning"] = box


warning_sound.done = lambda: _played("error")
warning_sound.done_what = "the 'error' sound for a warning message"


def real_players_never_raise():
    from fission180 import neon_sound

    s["warning"].close()
    neon_sound.BACKENDS = s["backends"]
    neon_sound.reset()
    neon_sound._state["last"] = {}
    kind = neon_sound.backend()[0]
    results = [neon_sound.play(n) for n in neon_sound.NAMES]
    h.check("this machine's way to play was found without an error", kind in ("qt", "cmd", "winsound", "none"), kind)
    h.check("... and play() returned at once for every sound", all(r in (None, kind) for r in results), results)
    h.note("info", "sounds here play through: %s" % (neon_sound.backend(),))
    for proc in neon_sound._state["procs"]:
        try:
            proc.kill()
        except Exception:
            pass


def sounds_off():
    from fission180 import neon_settings, neon_sound

    neon_settings.put("Sounds", False)
    neon_sound.refresh()
    h.check("Sounds off: the hook is gone", not neon_sound.hooked())
    h.expect_no_errors("the sounds")


# -- 3. the animated Home ------------------------------------------------------------------
def home_front():
    from fission180 import home_ui

    home_ui.show()
    # xvfb has no window manager: after the test's dialog and message box closed nothing gives
    # the main window its activation back (a desktop does). The background runs only while
    # the window is active, so it is given back here, as replay_a_steps.keys_to_window does.
    main = Gui.getMainWindow()
    if QtWidgets.QApplication.activeWindow() is not main:
        main.raise_()
        main.activateWindow()


home_front.done = lambda: (
    __import__("fission180.home_ui").home_ui.is_active()
    and QtWidgets.QApplication.activeWindow() is Gui.getMainWindow()
)
home_front.done_what = "Home in front"


def _page():
    from fission180 import home_ui

    return home_ui.view()


def _see_through(page):
    """Until builder "panels" makes Home's own panels transparent in Neon Lights: the same
    here (its rule added to the page's style sheet), so the picture shows the background
    through the page. back_to_dark() puts the page's style sheet back."""
    from fission180 import neon_home

    s["home_qss"] = page.property("fission180Qss")
    rule = neon_home.SEE_THROUGH_QSS
    page.setStyleSheet((s["home_qss"] or "") + "\n" + rule)
    # Qt keeps whether each widget is opaque from when it was styled; a style sheet changed
    # afterwards (only here: panels styles Home see-through from the start) needs it worked
    # out again, or the screen keeps the old opaque picture over the background.
    for w in page.findChildren(QtWidgets.QWidget):
        if w.objectName() != neon_home.NAME and not w.autoFillBackground():
            w.setAutoFillBackground(True)
            w.setAutoFillBackground(False)
    page.update()


def home_animates():
    from fission180 import neon_home

    page = _page()
    neon_home.attach(page)  # home_ui calls it (builder panels); here again: it is idempotent
    h.check("Home has the backdrop", neon_home.backdrop(page) is not None)


def _running():
    from fission180 import neon_home

    return neon_home.running(_page())


home_animates.done = _running
home_animates.done_what = "the Home background's timer to run"


def _why():
    from fission180 import neon_home

    return neon_home.stopped_because(_page())
home_animates.while_busy = True


def home_rate():
    from fission180 import neon_home

    b = neon_home.backdrop(_page())
    s["frames0"] = b.frames
    s["clock"] = QtCore.QElapsedTimer()
    s["clock"].start()


def _twenty_frames():
    from fission180 import neon_home

    b = neon_home.backdrop(_page())
    return b is not None and b.frames >= s["frames0"] + 20


home_rate.done = _twenty_frames
home_rate.done_what = "twenty frames of the Home background"
home_rate.while_busy = True


def home_rate_checked():
    from fission180 import neon_home

    b = neon_home.backdrop(_page())
    ms = max(1, s["clock"].elapsed())
    fps = (b.frames - s["frames0"]) * 1000.0 / ms
    h.check("at most 30 frames a second", fps <= 31.0, "%.1f fps" % fps)
    h.check("... the backdrop takes no clicks",
            b.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))
    widgets = [c for c in _page().children() if isinstance(c, QtWidgets.QWidget)]
    h.check("... it is under Home's content (the first child drawn)", widgets and widgets[0] is b)
    set_preset("johnny")
    _see_through(_page())


home_rate_checked.while_busy = True
home_rate_checked.done = lambda: _running()
home_rate_checked.done_what = "the Home background in Johnny's colours"


def _floor_on_screen():
    """The screen's pixels of a strip of the floor inside Home's list (scroll area)."""
    page = _page()
    scroll = page.scroll
    top = scroll.mapToGlobal(QtCore.QPoint(scroll.width() // 3, scroll.height() - 160))
    image = QtWidgets.QApplication.primaryScreen().grabWindow(0, top.x(), top.y(), 4, 150).toImage()
    return [image.pixel(1, y) for y in range(image.height())]


def home_moves():
    s["floor0"] = _floor_on_screen()
    from fission180 import neon_home

    s["frames_shot"] = neon_home.backdrop(_page()).frames


home_moves.done = lambda: (
    __import__("fission180.neon_home").neon_home.backdrop(_page()).frames >= s["frames_shot"] + 6
    and _floor_on_screen() != s["floor0"]
)
home_moves.done_what = "the floor to move on screen inside Home's list (not only in a grab)"
home_moves.while_busy = True


def home_shot():
    h.shot("home-johnny")

home_shot.while_busy = True


def design_tab():
    bar = h.document_tabs()
    index = [i for i in range(bar.count()) if bar.tabText(i).startswith("LookUnchanged")]
    h.check("the design has a tab", bool(index), [bar.tabText(i) for i in range(bar.count())])
    if index:
        wi.click(bar, bar.tabRect(index[0]).center())


design_tab.done = lambda: not _running() and not __import__("fission180.home_ui").home_ui.is_active()
design_tab.done_what = "the Home background to stop with the design in front"
design_tab.while_busy = True


def stopped_on_design():
    from fission180 import neon_home

    b = neon_home.backdrop(_page())
    h.check("Home's background is stopped (no timer)", b is not None and not b.timer.isActive())
    s["frames_stopped"] = b.frames if b is not None else 0


def back_home():
    bar = h.document_tabs()
    from fission180 import home_ui

    index = [i for i in range(bar.count()) if bar.tabText(i).startswith(home_ui.TITLE)]
    h.check("Home has a tab", bool(index), [bar.tabText(i) for i in range(bar.count())])
    if index:
        wi.click(bar, bar.tabRect(index[0]).center())


back_home.done = _running
back_home.done_what = "the Home background to run again on Home"
back_home.while_busy = True


def animation_setting_off():
    from fission180 import neon_home, neon_settings

    neon_settings.put("HomeAnimation", False)
    neon_home.refresh()
    h.check("HomeAnimation off: no backdrop", neon_home.backdrop(_page()) is None)
    h.check("... nothing of it left in the page",
            _page().findChild(QtWidgets.QWidget, neon_home.NAME) is None)
    neon_settings.put("HomeAnimation", True)
    neon_home.refresh()
    h.check("on again: the backdrop is back", neon_home.backdrop(_page()) is not None)


animation_setting_off.done = _running
animation_setting_off.done_what = "the Home background running again"
animation_setting_off.while_busy = True


# -- 4. Dark again -------------------------------------------------------------------------
def back_to_dark():
    page = _page()
    if page is not None and s.get("home_qss"):
        page.setStyleSheet(s["home_qss"])
    set_preset("v")
    lc.set_look("dark")


def nothing_left():
    from fission180 import neon_boot, neon_home, neon_sound, theme

    h.check("the look is Dark", theme.name() == "dark")
    h.check("no boot screen", neon_boot.widget() is None)
    h.check("no sound hook", not neon_sound.hooked())
    page = _page()
    if page is not None:
        h.check("no Home background", neon_home.backdrop(page) is None)
        h.check("... no widget of it", page.findChild(QtWidgets.QWidget, neon_home.NAME) is None)
    h.check("a sound now plays nothing", neon_sound.play("click") is None)
    h.check("the boot screen will not come", neon_boot.show() is None)
    h.expect_no_errors("Neon Lights' extras")


h.run(
    "neon_extras",
    [
        setup, boot_starts, boot_shown, boot_click, boot_again_for_a_key, boot_key,
        sounds_on, menu_sound, click_sound, click_a_button, ok_sound, press_ok, warning_sound,
        real_players_never_raise, sounds_off,
        home_front, home_animates, home_rate, home_rate_checked, home_moves, home_shot, design_tab,
        stopped_on_design, back_home, animation_setting_off,
        back_to_dark, nothing_left,
    ],
    paced_by="state",
)
