# SPDX-License-Identifier: LGPL-2.1-or-later
"""Preferences > Neon Lights (neon-lights-design.md 6.10, plan task B10), with real clicks.

1. In Dark the page is one line and "Switch to Neon Lights"; the button turns the window neon
   at once and the page fills (17 presets, the colours, the effects). Cancel after the switch
   puts Dark back; the second time OK keeps it.
2. Johnny in the gallery: the ribbon is Johnny's at once.
3. A primary of one's own (typed): the preset is "Custom (based on Johnny)", the window follows;
   an Outline of one's own reaches the palette; "#12345" is refused with a message next to its
   field and nothing changes.
   Extreme colours (Alert #1a0a10, Secondary #000000) keep the page's words readable; a white
   Text gets no "too faint" note; the text boxes keep their own 1 px frame (no squeezed
   nine-slice picture of the app style).
4. Saved as "Mine"; the parameters are written to disk and FreeCAD is really started again
   with a copy of this profile (Fission180Tests/gui/neon_settings_child.py): "Mine" is still
   chosen there, the colours still Custom.
5. Every switch toggles its setting and its part follows (refresh called; Hologram on the 3D
   view); a strength bar moves with the arrow keys.
6. Cancel puts back what the window opened with (colours, switches, strengths); Reset to
   preset drops one's own colours; saving under a taken name and Delete ask first; OK leaves
   only the palette in use in <UserAppData>/Fission180/neon/.
7. Back to Dark: no neon colour left.
"""

import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

s = {}
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MINE = {"primary": "#00ff88", "outline": "#ff00ff"}


def preferences():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.objectName() == "Fission180Preferences" and w.isVisible():
            return w
    return None


def page():
    d = preferences()
    return getattr(d, "neon", None) if d is not None else None


def find(cls, name):
    d = preferences()
    return d.findChild(cls, name) if d is not None else None


def ribbon_ground():
    from fission180 import shell

    ribbon = shell.ribbon()
    image = ribbon.grab().toImage()
    return QtGui.QColor(image.pixel(ribbon.width() - 6, ribbon.height() - 30)).name()


def palette_of(key, custom=None):
    from fission180 import neon_palette

    return neon_palette.derive(neon_palette.roles(key, custom))


def near(a, b, tolerance=10):
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return max(abs(ca.red() - cb.red()), abs(ca.green() - cb.green()), abs(ca.blue() - cb.blue())) <= tolerance


def style():
    return QtWidgets.QApplication.instance().styleSheet()


def save_picture(label):
    d = preferences()
    if d is not None:
        d.grab().save(os.path.join(h.OUT_DIR, "neon_settings-page-%s.png" % label))
    h.shot(label)


def open_preferences():
    """UTILITIES > Preferences (the design stays on screen behind the dialog)."""
    Gui.runCommand("Fission180_Preferences")


open_preferences.done = lambda: preferences() is not None
open_preferences.done_what = "the Preferences to open"


def open_neon_page():
    d = preferences()
    tree = d.findChild(QtWidgets.QTreeWidget, "Fission180PreferencesPages")
    def row():
        found = tree.findItems("Neon Lights", QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
        return found[0] if found else None

    wi.click_item(tree, row, what="the Neon Lights page")


open_neon_page.done = lambda: preferences() is not None and preferences().current_page() == "neon"
open_neon_page.done_what = "the Neon Lights page to show"


def _again(step, name):
    def again():
        step()

    again.__name__ = again.__qualname__ = name
    again.done = step.done
    again.done_what = step.done_what
    return again


# -- 1. Dark: one line and a button ---------------------------------------------------------
def setup():
    from fission180 import theme

    lc.setup()
    s["dark_ground"] = ribbon_ground()
    h.check("the look is Dark", theme.name() == "dark")


def dark_page():
    p = page()
    h.check("the Neon Lights page is there", p is not None)
    if p is None:
        return
    line = find(QtWidgets.QLabel, "Fission180NeonOffLine")
    button = find(QtWidgets.QPushButton, "Fission180NeonSwitch")
    h.check("in Dark: one line", line is not None and line.isVisible() and "Neon Lights" in line.text())
    h.check("... and Switch to Neon Lights", button is not None and button.isVisible())
    h.check("... no gallery shown", not find(QtWidgets.QWidget, "Fission180NeonGallery").isVisible())
    save_picture("dark")
    wi.click(button)


dark_page.done = lambda: page() is not None and page().showing()
dark_page.done_what = "the page to fill in for Neon Lights"


def cancel_switch():
    wi.click(find(QtWidgets.QPushButton, "Fission180PreferencesCancel"))


cancel_switch.done = lambda: preferences() is None
cancel_switch.done_what = "the Preferences to close"


def switch_undone():
    from fission180 import neon, theme

    h.check("Cancel after Switch to Neon Lights: Dark again", theme.current() == "dark" and theme.name() == "dark", theme.name())
    h.check("... Neon Lights' parts are off", not neon.active())
    h.check("... the ribbon is Dark's", ribbon_ground() == s["dark_ground"], ribbon_ground())


def neon_page():
    from fission180 import neon, neon_palette, theme

    h.check("the look is Neon Lights", theme.is_neon() and theme.current() == "neon")
    h.check("... its parts are on", neon.active() and not neon.failed(), neon.failed())
    combo = find(QtWidgets.QComboBox, "Fission180Pref_theme")
    h.check("General > Look says Neon Lights too", combo is not None and combo.currentData() == "neon")
    cards = [find(QtWidgets.QAbstractButton, "Fission180NeonPreset_" + k) for k in neon_palette.ORDER]
    h.check("17 presets in the gallery", all(c is not None and c.isVisible() for c in cards))
    johnny = cards[0]
    h.check(
        "a preset's tooltip says what it is after",
        johnny is not None and neon_palette.PRESETS["johnny"]["after"] in johnny.toolTip(),
        johnny.toolTip() if johnny else "",
    )
    h.check("V is chosen", cards[1].isChecked() and not johnny.isChecked())
    for role in ("primary", "secondary", "outline", "background", "text"):
        field = find(QtWidgets.QLineEdit, "Fission180NeonHex_" + role)
        h.check("a %s colour field" % role, field is not None and field.isVisible() and field.text().startswith("#"))
    alert = find(QtWidgets.QLineEdit, "Fission180NeonHex_alert")
    h.check("Alert is under More", alert is not None and not alert.isVisible())
    for key in ("Effects", "Glow", "ScanLines", "CRT", "Glitch", "ScanBand", "Hologram", "Boot",
                "Sounds", "HomeAnimation", "GlowStrength", "ScanLinesStrength", "CRTStrength",
                "GlitchStrength", "ViewStrength", "Volume"):
        h.check("a control for %s" % key, find(QtWidgets.QWidget, "Fission180Neon_" + key) is not None)
    h.check("the window is V's", near(ribbon_ground(), palette_of("v")["chrome"]), ribbon_ground())
    save_picture("v")


# -- 2. Johnny ------------------------------------------------------------------------------
def pick_johnny():
    card = find(QtWidgets.QAbstractButton, "Fission180NeonPreset_johnny")
    scroll_to(card)
    wi.click(card)


def scroll_to(widget):
    d = preferences()
    for area in d.findChildren(QtWidgets.QScrollArea):
        if area.isAncestorOf(widget) and area.isVisible():
            area.ensureWidgetVisible(widget, 20, 20)
    QtWidgets.QApplication.processEvents()


pick_johnny.done = lambda: palette_of("johnny")["chrome"] in style()
pick_johnny.done_what = "the window's style to be Johnny's"


def johnny_now():
    from fission180 import neon_settings

    h.check("Preset = Johnny (stored)", neon_settings.get("Preset") == "johnny")
    h.check("the ribbon repainted in Johnny's colour", near(ribbon_ground(), palette_of("johnny")["chrome"]), ribbon_ground())
    h.check("no V colour left in the style", palette_of("v")["chrome"] not in style())
    line = find(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("the page says Johnny", line is not None and "Johnny" in line.text() and "Custom" not in line.text(), line.text())
    h.check("Johnny's card is chosen", find(QtWidgets.QAbstractButton, "Fission180NeonPreset_johnny").isChecked())
    save_picture("johnny")


# -- 3. own colours -------------------------------------------------------------------------
def type_into(name, text):
    field = find(QtWidgets.QLineEdit, name)
    scroll_to(field)
    wi.click(field)
    field.selectAll()
    wi.key(field, QtCore.Qt.Key_Delete)
    wi.type_text(field, text)
    wi.key(field, QtCore.Qt.Key_Return)


def own_primary():
    type_into("Fission180NeonHex_primary", "#00ff88")


own_primary.done = lambda: palette_of("johnny", {"primary": "#00ff88"})["chrome"] in style()
own_primary.done_what = "the window to use the typed primary"


def custom_now():
    from fission180 import neon_settings

    line = find(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("the preset is Custom (based on Johnny)", "Custom (based on Johnny)" in line.text(), line.text())
    h.check("... stored", neon_settings.custom() == {"primary": "#00ff88"}, neon_settings.custom())
    h.check("no preset card is chosen", not any(
        c.isChecked() for c in preferences().findChildren(QtWidgets.QAbstractButton)
        if c.objectName().startswith("Fission180NeonPreset_")))
    h.check("the ribbon follows", near(ribbon_ground(), palette_of("johnny", {"primary": "#00ff88"})["chrome"]), ribbon_ground())


def own_outline():
    type_into("Fission180NeonHex_outline", "FF00FF")


own_outline.done = lambda: __import__("fission180.theme", fromlist=["x"]).palette().get("outline") == "#ff00ff"
own_outline.done_what = "the body outline colour to be the typed one"


def bad_hex():
    from fission180 import neon_settings

    s["before_bad"] = dict(neon_settings.custom())
    s["style_before_bad"] = style()
    type_into("Fission180NeonHex_secondary", "#12345")


def _bad_shown():
    m = find(QtWidgets.QLabel, "Fission180NeonHexMessage_secondary")
    return m is not None and m.isVisible() and "#12345" in m.text()


bad_hex.done = _bad_shown
bad_hex.done_what = "a message next to the Secondary field"


def bad_refused():
    from fission180 import neon_settings

    message = find(QtWidgets.QLabel, "Fission180NeonHexMessage_secondary")
    field = find(QtWidgets.QLineEdit, "Fission180NeonHex_secondary")
    h.check("#12345 is refused with a message", "not a colour" in message.text(), message.text())
    h.check("... the field is marked", field.property("invalid") is True)
    h.check("... nothing stored", neon_settings.custom() == s["before_bad"], neon_settings.custom())
    h.check("... the window unchanged", style() == s["style_before_bad"])
    save_picture("custom-refused")


def _contrast(widget, role, ground):
    from fission180 import neon_palette

    widget.ensurePolished()
    colour = widget.palette().color(role).name()
    return neon_palette.contrast(colour, ground), colour


def extreme_colours():
    """Review Focus: Alert #1a0a10 and Secondary #000000 must not make the page's words vanish."""
    more = find(QtWidgets.QPushButton, "Fission180NeonMore")
    scroll_to(more)
    wi.click(more)
    type_into("Fission180NeonHex_alert", "#1a0a10")
    type_into("Fission180NeonHex_secondary", "#000000")
    type_into("Fission180NeonHex_text", "#12345")  # (a refusal message to look at)


extreme_colours.done = lambda: (
    __import__("fission180.theme", fromlist=["x"]).palette().get("alert") == "#1a0a10"
    and __import__("fission180.theme", fromlist=["x"]).palette().get("secondary") == "#000000"
    and "#12345" in find(QtWidgets.QLabel, "Fission180NeonHexMessage_text").text()
)
extreme_colours.done_what = "the window in Alert #1a0a10 and Secondary #000000, and a refusal shown"


def extreme_readable():
    from fission180 import theme

    p = theme.palette()
    W, B = QtGui.QPalette.WindowText, QtGui.QPalette.ButtonText
    message = find(QtWidgets.QLabel, "Fission180NeonHexMessage_text")
    shown = [
        ("the refusal message (Alert)", message, W),
        ('"In use" (Secondary)', find(QtWidgets.QLabel, "Fission180NeonPresetName"), W),
        ("a strength value (Secondary)", page().strengths["GlowStrength"][1], W),
        ('"More" (Secondary)', find(QtWidgets.QPushButton, "Fission180NeonMore"), B),
    ]
    for what, widget, role in shown:
        ratio, colour = _contrast(widget, role, p["chrome"])
        h.check("%s readable on the panel" % what, ratio >= 4.5, "%s on %s: %.2f" % (colour, p["chrome"], ratio))
    page().readable_note.setVisible(True)  # (shown only for faint text: its colour is checked here)
    ratio, colour = _contrast(page().readable_note, W, p["chrome"])
    h.check("the readability note readable on the panel", ratio >= 4.5, "%s: %.2f" % (colour, ratio))
    h.check("... and the message is really on screen", message.isVisible() and message.width() > 20)
    save_picture("extreme")
    # the text boxes: their own 1 px frame, not the app style's nine-slice picture squeezed
    field = find(QtWidgets.QLineEdit, "Fission180NeonHex_primary")
    field.clearFocus()
    QtWidgets.QApplication.processEvents()
    image = field.grab().toImage()
    ratio = field.devicePixelRatioF()
    top = QtGui.QColor(image.pixel(int(field.width() * ratio / 2), 0)).name()
    inside = QtGui.QColor(image.pixel(int(4 * ratio), int(field.height() * ratio / 2))).name()
    h.check("a colour box's top edge is its own line colour", near(top, p["line"], 6), (top, p["line"]))
    h.check("... and inside is the field colour", near(inside, p["field"], 6), (inside, p["field"]))


def extreme_back():
    from fission180 import neon_settings

    for role in ("alert", "secondary"):
        neon_settings.set_custom(role, "")
    preferences().setFocus()
    page().load_values()
    type_into("Fission180NeonHex_text", "#ffffff")


extreme_back.done = lambda: __import__("fission180.theme", fromlist=["x"]).palette().get("secondary") != "#000000" \
    and __import__("fission180.neon_settings", fromlist=["x"]).custom().get("text") == "#ffffff"
extreme_back.done_what = "the preset's Alert and Secondary back and a white Text"


def white_text():
    from fission180 import neon_settings

    h.check('a white Text gets no "too faint" note', page().readable_note.isHidden())
    neon_settings.set_custom("text", "")
    more = find(QtWidgets.QPushButton, "Fission180NeonMore")
    if more.isChecked():
        wi.click(more)
    preferences().setFocus()
    page()._apply_colours()


white_text.done = lambda: __import__("fission180.neon_settings", fromlist=["x"]).custom() == MINE
white_text.done_what = "only Mine's own colours left"


# -- 4. a saved set survives a restart -----------------------------------------------------
def save_mine():
    name = find(QtWidgets.QLineEdit, "Fission180NeonSetName")
    scroll_to(name)
    wi.click(name)
    wi.type_text(name, "Mine")
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonSave"))


def _mine_chosen():
    p = page()
    return p is not None and p.chosen_set() == "Mine"


save_mine.done = _mine_chosen
save_mine.done_what = "Mine to be listed and chosen"


def close_ok():
    wi.click(find(QtWidgets.QPushButton, "Fission180PreferencesOK"))


close_ok.done = lambda: preferences() is None
close_ok.done_what = "the Preferences to close"


def _freecad():
    """The FreeCAD (or Fission 180) program this one is."""
    folders = []
    if os.environ.get("PREFIX"):
        folders.append(os.path.join(os.environ["PREFIX"], "bin"))  # the AppImage's own
    folders.append(os.path.join(App.getHomePath(), "bin"))
    for folder in folders:
        for name in ("Fission180", "fission180", "FreeCAD", "freecad"):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    return None


def restart():
    """A real restart: the parameters written to disk, then FreeCAD started again with a copy
    of this profile (neon_settings_child.py checks Mine there)."""
    App.saveParameter()
    path = os.path.join(App.getUserConfigDir(), "user.cfg")
    found = {}
    try:
        for group in ET.parse(path).getroot().iter("FCParamGroup"):
            if group.get("Name") == "Neon":
                for item in group:
                    found[item.get("Name")] = item.get("Value", item.text)
    except Exception as exc:
        h.check("user.cfg can be read", False, exc)
    h.check("on disk: Preset johnny", found.get("Preset") == "johnny", found)
    h.check("on disk: the own primary", found.get("Custom_primary") == "#00ff88", found)
    h.check("on disk: the set Mine", "Mine" in (found.get("SavedSets") or ""), found.get("SavedSets"))
    program = _freecad()
    h.check("the FreeCAD program is found", program is not None, App.getHomePath())
    profile = os.environ.get("FREECAD_USER_HOME") or os.path.dirname(App.getUserAppDataDir().rstrip("/"))
    copy = tempfile.mkdtemp(prefix="neon-settings-")
    shutil.copytree(profile, copy, dirs_exist_ok=True)
    name = "neon_settings_restart"
    out = os.environ.get("FISSION180_SMOKE_OUT") or tempfile.gettempdir()
    result = os.path.join(out, "%s-result.json" % name)
    if os.path.exists(result):
        os.remove(result)
    env = QtCore.QProcessEnvironment.systemEnvironment()
    env.insert("FREECAD_USER_HOME", copy)
    env.insert("FISSION180_SCENARIO", name)
    env.insert("FISSION180_SCENARIO_FILE", os.path.join(HERE, "neon_settings_child.py"))
    env.insert("FISSION180_SMOKE_OUT", out)
    process = QtCore.QProcess()
    process.setProcessEnvironment(env)
    process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    process.setStandardOutputFile(os.path.join(out, "scenario-%s.log" % name))
    process.start(program, [os.path.join(HERE, "scenario_launcher.py")])
    s["restart"] = {"process": process, "result": result, "profile": copy}


restart.done = lambda: s.get("restart") is not None and s["restart"]["process"].state() == QtCore.QProcess.NotRunning
restart.done_what = "the restarted FreeCAD to finish its checks"
restart.timeout_s = 600


def after_restart():
    job = s["restart"]
    try:
        with open(job["result"], "r", encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, ValueError) as exc:
        h.check("FreeCAD started again and gave its result", False,
                "%s (log: scenario-neon_settings_restart.log)" % exc)
        result = None
    if result is not None:
        h.check("FreeCAD started again and finished", bool(result.get("finished")))
        for item in result.get("checks", []):
            h.check("[restart] %s" % item.get("name"), item.get("ok"), item.get("detail", ""))
        h.check("the restart's own checks all ran", any("Mine is still chosen" in (i.get("name") or "")
                                                        for i in result.get("checks", [])))
    shutil.rmtree(job["profile"], ignore_errors=True)


def mine_still_chosen():
    p = page()
    line = find(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("Mine is still chosen", p is not None and p.chosen_set() == "Mine", p.chosen_set() if p else None)
    h.check("... Custom (based on Johnny)", line is not None and "Custom (based on Johnny)" in line.text())
    s["at_open"] = settings_now()


def settings_now():
    from fission180 import neon_prefs_ui, neon_settings

    out = {key: neon_settings.get(key) for key in neon_prefs_ui._SNAPSHOT_KEYS}
    out["custom"] = neon_settings.custom()
    return out


# -- 5. switches and strengths ------------------------------------------------------------
SWITCH_PART = {
    "Effects": "neon_effects", "Glow": "neon_effects", "ScanLines": "neon_effects",
    "CRT": "neon_effects", "Glitch": "neon_effects", "ScanBand": "neon_effects",
    "Boot": "neon_boot", "Sounds": "neon_sound", "HomeAnimation": "neon_home",
}


def count_refreshes():
    s["calls"] = {}
    s["originals"] = {}
    for part in set(SWITCH_PART.values()):
        module = __import__("fission180." + part, fromlist=["x"])
        original = module.refresh
        s["originals"][part] = original

        def counted(part=part, original=original):
            s["calls"][part] = s["calls"].get(part, 0) + 1
            return original()

        module.refresh = counted


def switches():
    from fission180 import neon_settings, neon_view

    for key, part in SWITCH_PART.items():
        check = find(QtWidgets.QCheckBox, "Fission180Neon_" + key)
        if not check.isEnabled():  # (ScanBand needs Scan lines on)
            neon_settings.put("ScanLines", True)
            page().load_values()
        before = neon_settings.get(key)
        calls = s["calls"].get(part, 0)
        scroll_to(check)
        wi.click(check, QtCore.QPoint(8, check.height() // 2))
        h.check("%s toggles" % key, neon_settings.get(key) == (not before) == check.isChecked(), neon_settings.get(key))
        h.check("... and %s follows" % part, s["calls"].get(part, 0) > calls, s["calls"])
        wi.click(check, QtCore.QPoint(8, check.height() // 2))
        h.check("... and back", neon_settings.get(key) == before)
    master = find(QtWidgets.QCheckBox, "Fission180Neon_Effects")
    wi.click(master, QtCore.QPoint(8, master.height() // 2))
    h.check("effects off: their switches are greyed",
            not find(QtWidgets.QCheckBox, "Fission180Neon_Glow").isEnabled()
            and not find(QtWidgets.QSlider, "Fission180Neon_GlowStrength").isEnabled())
    wi.click(master, QtCore.QPoint(8, master.height() // 2))
    holo = find(QtWidgets.QCheckBox, "Fission180Neon_Hologram")
    scroll_to(holo)
    wi.click(holo, QtCore.QPoint(8, holo.height() // 2))
    h.check("Hologram bodies on", neon_view.hologram() and holo.isChecked())
    wi.click(holo, QtCore.QPoint(8, holo.height() // 2))
    h.check("... and off", not neon_view.hologram())
    bar = find(QtWidgets.QSlider, "Fission180Neon_GlowStrength")
    before = neon_settings.get("GlowStrength")
    calls = s["calls"].get("neon_effects", 0)
    scroll_to(bar)
    wi.key(bar, QtCore.Qt.Key_Right)
    h.check("Glow strength + 5 with the arrow key", neon_settings.get("GlowStrength") == before + 5, neon_settings.get("GlowStrength"))
    h.check("... the effects follow", s["calls"].get("neon_effects", 0) > calls)
    wi.click(bar, QtCore.QPoint(bar.width() // 4, bar.height() // 2))
    h.check("a click on the bar sets about a quarter", 20 <= neon_settings.get("GlowStrength") <= 30, neon_settings.get("GlowStrength"))
    save_picture("effects")


def put_back_refresh():
    for part, original in s.get("originals", {}).items():
        __import__("fission180." + part, fromlist=["x"]).refresh = original


# -- 6. Cancel and Reset -----------------------------------------------------------------
def try_then_cancel():
    from fission180 import neon_settings

    s["kept"] = (neon_settings.get("Preset"), neon_settings.custom(), neon_settings.get("GlowStrength"))
    s["kept_style"] = style()
    card = find(QtWidgets.QAbstractButton, "Fission180NeonPreset_the_grid")
    scroll_to(card)
    wi.click(card)


try_then_cancel.done = lambda: palette_of("the_grid")["chrome"] in style()
try_then_cancel.done_what = "The Grid on screen"


def cancel():
    wi.click(find(QtWidgets.QPushButton, "Fission180PreferencesCancel"))


cancel.done = lambda: preferences() is None
cancel.done_what = "the Preferences to close"


def cancelled():
    from fission180 import neon_settings

    now = (neon_settings.get("Preset"), neon_settings.custom(), neon_settings.get("GlowStrength"))
    h.check("Cancel put the colours back", now[:2] == s["kept"][:2], now)
    back = settings_now()
    h.check("... the strengths changed in this window are back (GlowStrength)",
            back["GlowStrength"] == s["at_open"]["GlowStrength"] != s["kept"][2],
            (back["GlowStrength"], s["at_open"]["GlowStrength"], s["kept"][2]))
    h.check("... and every switch and strength as the window opened", back == s["at_open"],
            {k: (back.get(k), v) for k, v in s["at_open"].items() if back.get(k) != v})
    h.check("... and the window", palette_of("the_grid")["chrome"] not in style()
            and palette_of("johnny", {"primary": "#00ff88", "outline": "#ff00ff"})["chrome"] in style())


def reset():
    button = find(QtWidgets.QPushButton, "Fission180NeonReset")
    scroll_to(button)
    wi.click(button)


reset.done = lambda: palette_of("johnny")["chrome"] in style()
reset.done_what = "Johnny's own colours back"


def reset_done():
    from fission180 import neon_settings

    h.check("Reset to preset: no own colours", neon_settings.custom() == {})
    line = find(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("... the page says Johnny", "Custom" not in line.text() and "Johnny" in line.text(), line.text())
    h.check("... Mine is not chosen now", page().chosen_set() is None)
    s["mine_item"] = True


def rename_and_delete():
    p = page()
    lst = find(QtWidgets.QListWidget, "Fission180NeonSetList")
    scroll_to(lst)
    wi.click_item(lst, lambda: (lst.findItems("Mine", QtCore.Qt.MatchExactly) or [None])[0], what="Mine")
    h.check("clicking Mine brings its colours back", p.chosen_set() == "Mine")
    name = find(QtWidgets.QLineEdit, "Fission180NeonSetName")
    name.clear()
    wi.click(name)
    wi.type_text(name, "Toxic")
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonRename"))
    names = [lst.item(i).text() for i in range(lst.count())]
    h.check("renamed to Toxic", names == ["Toxic"] and p.chosen_set() == "Toxic", names)
    from fission180 import neon_settings

    stored = neon_settings.saved_sets()
    name.clear()
    wi.click(name)
    wi.type_text(name, "Toxic")
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonSave"))
    h.check("Save under a name in use asks first", "Toxic" in p.asking() and "Replace" in p.asking(), p.asking())
    h.check("... nothing replaced yet", neon_settings.saved_sets() == stored)
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonConfirmNo"))
    h.check("... Keep it: the set is as it was", neon_settings.saved_sets() == stored and not p.asking())
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonDelete"))
    h.check("Delete asks first", "Delete" in p.asking() and "Toxic" in p.asking(), p.asking())
    h.check("... still listed", lst.count() == 1)
    save_picture("delete-asks")
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonConfirmYes"))
    h.check("deleted after Yes", lst.count() == 0 and neon_settings.saved_sets() == [])


rename_and_delete.done = lambda: palette_of("johnny", {"primary": "#00ff88", "outline": "#ff00ff"})["chrome"] in style()
rename_and_delete.done_what = "Mine's colours on screen"


def to_v_and_ok():
    card = find(QtWidgets.QAbstractButton, "Fission180NeonPreset_v")
    scroll_to(card)
    wi.click(card)
    wi.click(find(QtWidgets.QPushButton, "Fission180PreferencesOK"))


to_v_and_ok.done = lambda: preferences() is None and palette_of("v")["chrome"] in style()
to_v_and_ok.done_what = "V kept with OK"


def folders_tidied():
    from fission180 import neon_settings, neon_style, theme

    base = neon_settings.neon_folder()
    left = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
    mine = os.path.basename(neon_style.folder(theme.palette()))
    h.check("OK left only the palette in use in Fission180/neon/", left == [mine], left)
    h.check("... whose pictures are there", any(n.startswith("frames") for n in os.listdir(os.path.join(base, mine))))
    s["old_windows"] = len(neon_prefs_pages())


def neon_prefs_pages():
    from fission180 import neon_prefs_ui

    return neon_prefs_ui.pages()


def windows_freed():
    h.check("closed Preferences windows are freed (one page left at most)", len(neon_prefs_pages()) <= 1,
            len(neon_prefs_pages()))


# -- 7. back to Dark -------------------------------------------------------------------------
def back_to_dark():
    lc.set_look("dark")


def dark_again():
    from fission180 import neon, theme

    h.check("Dark again", theme.name() == "dark" and not neon.active())
    h.check("no neon colour left", palette_of("v")["chrome"] not in style())
    h.check("the ribbon is Dark's again", ribbon_ground() == s["dark_ground"], ribbon_ground())


h.run(
    "neon_settings",
    [setup, open_preferences, open_neon_page, dark_page, cancel_switch, switch_undone,
     _again(open_preferences, "open_again"), _again(open_neon_page, "neon_page_again"),
     _again(dark_page, "switch_again"), neon_page, pick_johnny, johnny_now,
     own_primary, custom_now, own_outline, bad_hex, bad_refused, extreme_colours, extreme_readable,
     extreme_back, white_text, save_mine, close_ok, restart,
     after_restart, _again(open_preferences, "open_after_restart"),
     _again(open_neon_page, "neon_page_after_restart"), mine_still_chosen, count_refreshes,
     switches, put_back_refresh, try_then_cancel, cancel, cancelled,
     _again(open_preferences, "open_after_cancel"), _again(open_neon_page, "neon_page_after_cancel"), reset,
     reset_done, rename_and_delete, to_v_and_ok, folders_tidied, _again(open_preferences, "open_once_more"),
     windows_freed, cancel, back_to_dark, dark_again],
    paced_by="state",
)
