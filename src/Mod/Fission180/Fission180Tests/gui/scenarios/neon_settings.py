# SPDX-License-Identifier: LGPL-2.1-or-later
"""Preferences > Neon Lights (neon-lights-design.md 6.10, plan task B10), with real clicks.

1. In Dark the page is one line and "Switch to Neon Lights"; the button turns the window neon
   at once and the page fills (17 presets, the colours, the effects).
2. Johnny in the gallery: the ribbon is Johnny's at once.
3. A primary of one's own (typed): the preset is "Custom (based on Johnny)", the window follows;
   an Outline of one's own reaches the palette; "#12345" is refused with a message next to its
   field and nothing changes.
4. Saved as "Mine"; the parameters are written to disk and the look starts again the way it
   does at a restart (theme.restore / apply): "Mine" is still chosen, the colours still Custom.
5. Every switch toggles its setting and its part follows (refresh called; Hologram on the 3D
   view); a strength bar moves with the arrow keys.
6. Cancel puts back what the window opened with; Reset to preset drops one's own colours.
7. Back to Dark: no neon colour left.
"""

import os
import xml.etree.ElementTree as ET

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

s = {}


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


dark_page.done = lambda: page() is not None and page().stack.currentWidget() is page().on_page
dark_page.done_what = "the page to fill in for Neon Lights"


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


def restart():
    """What a restart reads: the parameters as written to disk; then the look started again."""
    from fission180 import theme

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
    theme.restore()
    theme.apply()
    QtWidgets.QApplication.processEvents()


def after_restart():
    from fission180 import neon, theme

    h.check("Neon Lights again after the start", theme.is_neon() and neon.active())
    h.check("the window has Mine's colours",
            palette_of("johnny", {"primary": "#00ff88", "outline": "#ff00ff"})["chrome"] in style())


def mine_still_chosen():
    p = page()
    line = find(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("Mine is still chosen", p is not None and p.chosen_set() == "Mine", p.chosen_set() if p else None)
    h.check("... Custom (based on Johnny)", line is not None and "Custom (based on Johnny)" in line.text())


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
    wi.click(find(QtWidgets.QPushButton, "Fission180NeonDelete"))
    h.check("deleted", lst.count() == 0)


rename_and_delete.done = lambda: palette_of("johnny", {"primary": "#00ff88", "outline": "#ff00ff"})["chrome"] in style()
rename_and_delete.done_what = "Mine's colours on screen"


def to_v_and_ok():
    card = find(QtWidgets.QAbstractButton, "Fission180NeonPreset_v")
    scroll_to(card)
    wi.click(card)
    wi.click(find(QtWidgets.QPushButton, "Fission180PreferencesOK"))


to_v_and_ok.done = lambda: preferences() is None and palette_of("v")["chrome"] in style()
to_v_and_ok.done_what = "V kept with OK"


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
    [setup, open_preferences, open_neon_page, dark_page, neon_page, pick_johnny, johnny_now,
     own_primary, custom_now, own_outline, bad_hex, bad_refused, save_mine, close_ok, restart,
     after_restart, _again(open_preferences, "open_after_restart"),
     _again(open_neon_page, "neon_page_after_restart"), mine_still_chosen, count_refreshes,
     switches, put_back_refresh, try_then_cancel, cancel, cancelled,
     _again(open_preferences, "open_after_cancel"), _again(open_neon_page, "neon_page_after_cancel"), reset, reset_done, rename_and_delete, to_v_and_ok, back_to_dark, dark_again],
    paced_by="state",
)
