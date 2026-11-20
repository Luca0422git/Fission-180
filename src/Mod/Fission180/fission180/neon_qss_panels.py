# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for command dialogs (FreeCAD's task panels) and Fission 180's other
panels (design 6.3; plan task B3 owns this file).

Two halves:

- qss(): the rules joined into the app's style sheet (neon_style.qss): FreeCAD's task panels
  (a header strip with hazard stripes and the title in caps, fields as dark slots that glow on
  focus, OK as a filled primary button) and the panels that have no style of their own.
- style(widget, text, part): what a Fission 180 panel calls instead of setStyleSheet(text)
  for its own style sheet. In Dark and Light it is exactly setStyleSheet(text). In Neon
  Lights the panel gets `text` in neon colours (theme.translate) plus the neon rules of
  `part` (BLOCKS below): cut corners, glowing frames, caps titles. A widget's own style sheet
  beats the app's, so these rules must live on the widget itself. theme_changed() (a
  theme.LISTENERS module) does it again for every such widget after each look or preset
  switch, so nothing keeps an old preset and Dark gets its own text back exactly.

The frame pieces of neon_frames (B1) are used as they are; the pieces only these panels need
(a filled primary button, the header strip, the hazard tile) are drawn here.
"""

import os

from . import warn

PROP_TEXT = "fission180NeonText"  # the style sheet the panel asked for (dark colours)
PROP_PART = "fission180NeonPart"  # which BLOCKS entry it gets in Neon Lights
PROP_ROLE = "fission180NeonRole"  # colour(): the palette role of the widget's text in Neon Lights

# -- this file's own frame pieces ----------------------------------------------------------
# piece -> (width, height, slice in image px, border in screen px)
SIZES = {
    "ok": (48, 32, 8, 4),
    "ok_hover": (48, 32, 8, 4),
    "ok_pressed": (48, 32, 8, 4),
    "strip": (96, 32, 10, 5),
    "hazard": (72, 24, 0, 0),
    "slot": (48, 32, 8, 4),
    "chip": (48, 32, 8, 4),
    "chip_hover": (48, 32, 8, 4),
    "chip_on": (48, 32, 8, 4),
    "box": (64, 48, 12, 6),
}
PIECES = tuple(SIZES)


def _pts(x, y, w, h, c, corners):
    out = []
    out += [(x, y + c), (x + c, y)] if "tl" in corners else [(x, y)]
    out += [(x + w - c, y), (x + w, y + c)] if "tr" in corners else [(x + w, y)]
    out += [(x + w, y + h - c), (x + w - c, y + h)] if "br" in corners else [(x + w, y + h)]
    out += [(x + c, y + h), (x, y + h - c)] if "bl" in corners else [(x, y + h)]
    return " ".join("%g,%g" % p for p in out)


def _poly(points, fill="none", fill_opacity=1.0, stroke="none", width=0.0, opacity=1.0):
    return (
        '<polygon points="%s" fill="%s" fill-opacity="%g" stroke="%s" stroke-width="%g" '
        'stroke-opacity="%g" stroke-linejoin="miter" />'
        % (points, fill, fill_opacity, stroke, width, opacity)
    )


def _line(x1, y1, x2, y2, colour, width, opacity=1.0):
    return (
        '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g" '
        'stroke-opacity="%g" stroke-linecap="butt" />' % (x1, y1, x2, y2, colour, width, opacity)
    )


def _svg(w, h, body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s'
        "</svg>" % (w, h, w, h, "".join(body))
    )


def ink(p):
    """Text on a primary-filled button: the darker of the look's ground and black, or its
    light text when the primary colour is a dark one (a person's own colours)."""
    from .neon_palette import contrast

    dark = p["background"]
    if contrast(dark, p["primary"]) >= 4.5:
        return dark
    if contrast("#000000", p["primary"]) >= contrast(p["text"], p["primary"]):
        return "#000000"
    return p["text"]


def svg(piece, p):
    """The SVG text of one of this file's pieces in palette `p`. Pure."""
    from .neon_palette import mix

    w, h, s, _b = SIZES[piece]
    primary, hot = p["primary"], p["primary_hot"]
    if piece in ("ok", "ok_hover", "ok_pressed"):
        fill = {"ok": primary, "ok_hover": hot, "ok_pressed": mix(primary, p["background"], 0.3)}[piece]
        pts = _pts(2, 2, w - 4, h - 4, 6, ("tl", "br"))
        body = [
            _poly(pts, stroke=primary, width=4.0, opacity=0.25),
            _poly(pts, fill=fill, stroke=hot, width=1.6),
            # a notch of the ground in the cut corner, like a cartridge's
            _line(w - 9, h - 6, w - 6, h - 9, p["background"], 1.4, 0.8),
        ]
        return _svg(w, h, body)
    if piece == "strip":
        # the header strip: a dark band, a solid primary tab on the left with a cut end,
        # a glowing line under it and tick marks at the right end
        body = [
            # (translucent: the hazard stripes under it, the header's background-image, show)
            _poly(_pts(1, 1, w - 2, h - 3, 7, ("tr",)), fill=p["header"], fill_opacity=0.55,
                  stroke=p["line"], width=1.2),
            _poly(_pts(1, 1, 7, h - 3, 4, ("br",)), fill=primary),
            _line(1, h - 2, w - 1, h - 2, primary, 4.0, 0.25),
            _line(1, h - 1.6, w - 1, h - 1.6, hot, 1.6),
            _line(w - 6, 4, w - 6, 9, primary, 1.4),
            _line(w - 10, 4, w - 10, 7, primary, 1.4, 0.7),
        ]
        return _svg(w, h, body)
    if piece == "hazard":
        body = []
        step = 10
        for x in range(-h, w + h, step):
            body.append(
                _poly("%g,%g %g,%g %g,%g %g,%g" % (x, h, x + 5, h, x + 5 + h, 0, x + h, 0),
                      fill=primary, fill_opacity=0.42)
            )
        return _svg(w, h, body)
    if piece == "slot":
        # a sunk value slot: dark, no frame but a line under it with a square end (the line a
        # little dim, so the focused field's glowing frame stands out from it)
        body = [
            _poly(_pts(1, 1, w - 2, h - 2, 4, ("br",)), fill=p["field"], stroke=p["line"], width=1.0,
                  opacity=0.6),
            _line(1, h - 2, w - 7, h - 2, primary, 2.0, 0.7),
            _line(1, h - 2, 6, h - 2, hot, 2.4),
        ]
        return _svg(w, h, body)
    if piece in ("chip", "chip_hover", "chip_on"):
        on = piece == "chip_on"
        fill = {"chip": p["button"], "chip_hover": p["hover"], "chip_on": mix(p["button"], primary, 0.45)}[piece]
        stroke = {"chip": p["primary_dim"], "chip_hover": primary, "chip_on": hot}[piece]
        pts = _pts(2, 2, w - 4, h - 4, 5, ("tr", "bl"))
        body = []
        if piece != "chip":
            body.append(_poly(pts, stroke=primary, width=4.0, opacity=0.22))
        body.append(_poly(pts, fill=fill, stroke=stroke, width=1.6))
        if on:
            body.append(_line(4, h - 4, 4, 10, hot, 2.4))
        return _svg(w, h, body)
    if piece == "box":
        # a HUD box: translucent dark glass, a thin frame, bracket corners in the secondary
        g, c = 2.0, 8.0
        pts = _pts(g, g, w - 2 * g, h - 2 * g, c, ("tl", "br"))
        k = 9.0
        sec = p["secondary"]
        body = [
            _poly(pts, stroke=primary, width=4.0, opacity=0.18),
            _poly(pts, fill=p["menu"], fill_opacity=0.94, stroke=p["primary_dim"], width=1.4),
            _line(w - g, g + 3, w - g, g + 3 + k, sec, 2.2),
            _line(w - g - 3, g, w - g - 3 - k, g, sec, 2.2),
            _line(g, h - g - 3, g, h - g - 3 - k, sec, 2.2),
            _line(g + 3, h - g, g + 3 + k, h - g, sec, 2.2),
        ]
        return _svg(w, h, body)
    raise KeyError(piece)


def write(p, folder):
    """This file's pieces of palette `p` as SVG files in `folder` (made once): {piece: path}."""
    os.makedirs(folder, exist_ok=True)
    out = {}
    for piece in PIECES:
        path = os.path.join(folder, piece + ".svg")
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(svg(piece, p))
        out[piece] = path.replace("\\", "/")
    return out


def _border(path, piece):
    s, b = SIZES[piece][2], SIZES[piece][3]
    return "border-image: url(%s) %d %d %d %d stretch stretch; border-width: %dpx;" % (path, s, s, s, s, b)


def values(p, frames, fonts, mine):
    """The names the rules below use: the palette's colours, frame rules, fonts."""
    from .neon_palette import rgba
    from .neon_qss_chrome import border

    display = fonts[1] if fonts and len(fonts) > 1 else ""
    v = dict(p)
    v.update(
        panel_frame=border(frames, "panel"),
        header_frame=border(frames, "header"),
        button_frame=border(frames, "button"),
        button_hover_frame=border(frames, "button_hover"),
        button_pressed_frame=border(frames, "button_pressed"),
        field_frame=border(frames, "field"),
        field_focus_frame=border(frames, "field_focus"),
        menu_frame=border(frames, "menu"),
        check=frames["check"],
        check_on=frames["check_on"],
        ok_frame=_border(mine["ok"], "ok"),
        ok_hover_frame=_border(mine["ok_hover"], "ok_hover"),
        ok_pressed_frame=_border(mine["ok_pressed"], "ok_pressed"),
        strip_frame=_border(mine["strip"], "strip"),
        slot_frame=_border(mine["slot"], "slot"),
        chip_frame=_border(mine["chip"], "chip"),
        chip_hover_frame=_border(mine["chip_hover"], "chip_hover"),
        chip_on_frame=_border(mine["chip_on"], "chip_on"),
        box_frame=_border(mine["box"], "box"),
        hazard=mine["hazard"],
        ink=ink(p),
        display=('font-family: "%s";' % display) if display else "",
        hover_fill=rgba(p["primary"], 0.16),
        selected_fill=rgba(p["primary"], 0.26),
        secondary_fill=rgba(p["secondary"], 0.12),
        alert_fill=rgba(p["alert"], 0.16),
        line_soft=rgba(p["primary"], 0.35),
        fit_small=FIT_SMALL,
    )
    return v


# -- the app's style sheet part ---------------------------------------------------------------
def qss(p, frames, fonts, translucent):
    """The rules joined into the app's style in Neon Lights (neon_style.qss)."""
    import os as _os

    mine = write(p, _os.path.join(_os.path.dirname(frames["panel"]), "panels"))
    v = values(p, frames, fonts, mine)
    return """
/* -- Neon Lights: command dialogs (task panels) ------------------------------------------- */
Gui--TaskView--TaskView > QScrollArea {{ border: none; background: transparent; }}
QSint--ActionPanel, QSint--ActionPanel QScrollArea, QSint--ActionPanel QScrollArea > QWidget > QWidget {{
    background: {chrome}; }}
QSint--ActionGroup {{ background: {chrome}; }}
QSint--ActionGroup QFrame[class="header"] {{ background: transparent; {strip_frame}
    border-top-width: 1px; border-bottom-width: 2px;
    background-image: url({hazard}); background-repeat: no-repeat; background-position: right center;
    background-origin: padding; }}
QSint--ActionGroup QToolButton[class="header"] {{ color: {primary_hot}; font-weight: bold; text-align: left;
    border: none; background: transparent; text-transform: uppercase; letter-spacing: 1.5px; {display}
    font-size: 11px; padding: 0px; }}
QSint--ActionGroup QFrame[class="header"] QLabel {{ color: {primary_hot}; background: transparent;
    text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold; {display} }}
/* a long title made to fit before the hazard stripes (fit_titles): tighter, then smaller,
   then the stripes left out */
QSint--ActionGroup QToolButton[class="header"][fission180Fit="1"] {{ letter-spacing: 0.5px; }}
QSint--ActionGroup QToolButton[class="header"][fission180Fit="2"] {{ letter-spacing: 0px; font-size: {fit_small}px; }}
QSint--ActionGroup QToolButton[class="header"][fission180Fit="3"] {{ letter-spacing: 0px; font-size: {fit_small}px; }}
QSint--ActionGroup QFrame[class="header"][fission180Fit="3"] {{ background-image: none; }}
QSint--ActionGroup QFrame[class="content"] {{ background: {chrome}; border: 1px solid {line};
    border-top: none; }}
QSint--ActionGroup QFrame[class="content"] QTreeView, QSint--ActionGroup QFrame[class="content"] QListView,
QSint--ActionGroup QFrame[class="content"] QTableView {{ background: {field}; }}
QSint--ActionGroup QFrame[class="content"] QToolButton {{ background: transparent; color: {text};
    padding: 0px; min-height: 16px; {chip_frame} }}
QSint--ActionGroup QFrame[class="content"] QToolButton:checked {{ color: {primary_hot}; {chip_on_frame} }}
QSint--ActionGroup QFrame[class="content"] QToolButton:hover {{ color: {primary_hot}; {chip_hover_frame} }}
QSint--ActionGroup QFrame[class="separator"] {{ background: transparent; }}
QSint--ActionGroup QFrame[class="content"] QLineEdit, QSint--ActionGroup QFrame[class="content"] QAbstractSpinBox,
QSint--ActionGroup QFrame[class="content"] QComboBox {{ {slot_frame} }}
QSint--ActionGroup QFrame[class="content"] QLineEdit:focus,
QSint--ActionGroup QFrame[class="content"] QAbstractSpinBox:focus,
QSint--ActionGroup QFrame[class="content"] QComboBox:focus {{ color: {primary_hot}; {field_focus_frame} }}
/* OK / Cancel of a command dialog: OK is the filled primary button */
Gui--TaskView--TaskView QDialogButtonBox QPushButton {{ text-transform: uppercase; letter-spacing: 1px;
    font-weight: bold; }}
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="OK"],
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="&OK"] {{ color: {ink}; {ok_frame} }}
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="OK"]:hover,
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="&OK"]:hover {{ color: {ink}; {ok_hover_frame} }}
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="OK"]:pressed,
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="&OK"]:pressed {{ color: {ink}; {ok_pressed_frame} }}
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="OK"]:disabled,
Gui--TaskView--TaskView QDialogButtonBox QPushButton[text="&OK"]:disabled {{ color: {disabled}; {button_frame} }}

/* -- Neon Lights: the command search (S) --------------------------------------------------- */
QDialog#Fission180Search {{ background: {menu}; {box_frame} }}
QDialog#Fission180Search QLineEdit {{ color: {primary_hot}; font-size: 14px; {slot_frame} }}
QDialog#Fission180Search QListWidget {{ background: transparent; border: none; }}
QDialog#Fission180Search QListWidget::item {{ padding: 3px 6px; border-left: 2px solid transparent; }}
QDialog#Fission180Search QListWidget::item:selected {{ background: {selected_fill}; color: {primary_hot};
    border-left: 2px solid {primary}; }}
QDialog#Fission180Search QListWidget::item:hover {{ background: {hover_fill}; }}
""".format(**v)


# -- the panels' own style sheets ---------------------------------------------------------------
def _home(v, widget):
    return """
#Fission180Home {{ background: {view}; }}
#Fission180HomeHeading {{ color: {primary_hot}; {display} font-size: 22px; letter-spacing: 3px;
    text-transform: uppercase; }}
#Fission180HomeVersion {{ color: {secondary}; letter-spacing: 1px; }}
#Fission180HomeTitle {{ color: {primary_hot}; {display} font-size: 14px; letter-spacing: 2px;
    text-transform: uppercase; }}
#Fission180HomePath {{ color: {text_dim}; letter-spacing: 0.5px; }}
#Fission180HomeLine {{ background: {primary_dim}; }}
#Fission180HomeEmpty {{ color: {text_dim}; }}
#Fission180HomeList::item {{ border-radius: 0px; border-bottom: 2px solid transparent; }}
#Fission180HomeList::item:hover {{ background: {hover_fill}; border-bottom: 2px solid {primary_dim}; }}
#Fission180HomeList::item:selected {{ background: {selected_fill}; color: {primary_hot};
    border-bottom: 2px solid {primary}; }}
#Fission180HomeNew {{ background: transparent; color: {ink}; border: none; padding: 2px 14px;
    text-transform: uppercase; letter-spacing: 1px; {ok_frame} }}
#Fission180HomeNew:hover {{ background: transparent; {ok_hover_frame} }}
#Fission180HomeNew:pressed {{ {ok_pressed_frame} }}
#Fission180HomeRecovery {{ background: {alert_fill}; border-radius: 0px; border-left: 3px solid {alert}; }}
#Fission180HomeClear, #Fission180HomeConnect, #Fission180HomePlaceMenu {{ color: {secondary};
    letter-spacing: 0.5px; border-image: none; }}
#Fission180HomeClear:hover, #Fission180HomeConnect:hover, #Fission180HomePlaceMenu:hover {{
    color: {secondary_hot}; }}
#Fission180HomeAI {{ background: {chrome}; border-left: 1px solid {line}; }}
#Fission180HomeAIStatus {{ color: {text_dim}; }}
#Fission180HomeAIs {{ background: {field}; border: 1px solid {primary_dim}; }}
#Fission180HomeAIs::item {{ padding: 3px; }}
#Fission180HomeAIs::item:hover {{ background: {hover_fill}; }}
""".format(**v) + _see_through()


def _see_through():
    """Home's scroll area, rows and list see-through, so neon_home's animated backdrop (a child
    at the bottom of the page) shows; never the page itself (neon_home.SEE_THROUGH)."""
    from . import neon_home

    return neon_home.SEE_THROUGH_QSS + "\n"


def _home_update(v, widget):
    return """
#Fission180HomeUpdate {{ background: {secondary_fill}; border-radius: 0px; border-left: 3px solid {secondary}; }}
#Fission180HomeUpdateText {{ color: {text}; }}
#Fission180HomeUpdateNow {{ background: transparent; color: {ink}; border: none; padding: 1px 10px;
    text-transform: uppercase; letter-spacing: 1px; {ok_frame} }}
#Fission180HomeUpdateNow:hover {{ background: transparent; {ok_hover_frame} }}
#Fission180HomeUpdateLink {{ color: {secondary}; text-transform: uppercase; letter-spacing: 1px;
    border-image: none; }}
#Fission180HomeUpdateLink:hover {{ color: {secondary_hot}; }}
""".format(**v)


def _home_notice(v, widget):
    name = widget.objectName() if widget is not None else ""
    if not name:
        return ""
    return """
#{name} {{ background: {alert_fill}; border-radius: 0px; border-left: 3px solid {alert}; }}
""".format(name=name, **v)


def _ai(v, widget):
    return """
#Fission180AITitle {{ background: {chrome}; border-bottom: 1px solid {primary}; }}
#Fission180AITitle QLabel {{ color: {primary_hot}; {display} letter-spacing: 2px; text-transform: uppercase; }}
#Fission180AIClose {{ border-radius: 0px; }}
#Fission180AIClose:hover {{ background: {hover_fill}; }}
#Fission180AIToggle {{ color: {text}; letter-spacing: 0.5px; }}
#Fission180AIToggle::indicator {{ border-radius: 0px; background: {button}; border: 1px solid {primary_dim}; }}
#Fission180AIToggle::indicator:checked {{ background: {primary}; border: 1px solid {primary_hot}; }}
#Fission180AIToggleState {{ color: {secondary}; letter-spacing: 1px; text-transform: uppercase; }}
#Fission180AIApps {{ background: {field}; border: 1px solid {primary_dim}; }}
#Fission180AIApps::item:hover {{ background: {hover_fill}; }}
#Fission180AIApps::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}
#Fission180AIAppsTitle {{ color: {secondary}; text-transform: uppercase; letter-spacing: 1.5px; }}
""".format(**v)


def _palette_box(name):
    def block(v, widget):
        return """
#{name} {{ background: {chrome}; border: 1px solid {primary_dim}; border-radius: 0px; }}
#{name} QLabel[role="title"] {{ color: {primary_hot}; {display} letter-spacing: 2px;
    text-transform: uppercase; background-color: {header}; border-bottom: 1px solid {primary};
    background-image: url({hazard}); background-repeat: no-repeat; background-position: right center; }}
#{name} QToolButton[role="section"] {{ color: {secondary}; text-transform: uppercase; letter-spacing: 1px; }}
#{name} QPushButton[role="finish"] {{ background: transparent; color: {ink}; border: none;
    padding: 2px 10px; text-transform: uppercase; letter-spacing: 1px; {ok_frame} }}
#{name} QPushButton[role="finish"]:hover {{ background: transparent; {ok_hover_frame} }}
#{name} QPushButton[role="finish"]:pressed {{ {ok_pressed_frame} }}
#{name} QToolButton[role="option"] {{ background: transparent; border: none; padding: 0px; {chip_frame} }}
#{name} QToolButton[role="option"]:hover {{ background: transparent; {chip_hover_frame} }}
#{name} QToolButton[role="option"]:checked {{ background: transparent; color: {ink}; {chip_on_frame} }}
#{name} QCheckBox::indicator {{ border: none; border-radius: 0px; background: transparent; image: url({check}); }}
#{name} QCheckBox::indicator:hover {{ border: none; image: url({check}); }}
#{name} QCheckBox::indicator:checked {{ border: none; background: transparent; image: url({check_on}); }}
#{name} QCheckBox::indicator:disabled {{ border: none; background: transparent; image: url({check}); }}
""".format(name=name, **v)

    return block


def _measure_results(v, widget):
    return """
QTreeWidget {{ background: {field}; color: {text}; border: 1px solid {primary_dim}; }}
QTreeWidget::item {{ color: {text}; border-bottom: 1px solid {line_soft}; }}
QTreeWidget::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}
QHeaderView::section {{ color: {secondary}; background: {header}; text-transform: uppercase;
    letter-spacing: 1px; border: none; border-bottom: 1px solid {primary}; }}
""".format(**v)


def _marking(v, widget):
    return """
#Fission180MarkingMenu QToolButton#Fission180MarkingSlot {{ background: transparent; color: {text};
    border: none; border-radius: 0px; padding: 0px 4px; letter-spacing: 0.5px; {chip_frame} }}
#Fission180MarkingMenu QToolButton#Fission180MarkingSlot:hover {{ background: transparent; color: {primary_hot};
    {chip_hover_frame} }}
#Fission180MarkingMenu QToolButton#Fission180MarkingSlot:disabled {{ color: {disabled}; }}
#Fission180MarkingMenu QListWidget#Fission180MarkingList {{ background: transparent; color: {text};
    border: none; {box_frame} }}
#Fission180MarkingMenu QListWidget#Fission180MarkingList::item:hover {{ background: {hover_fill};
    color: {primary_hot}; }}
""".format(**v)


def _arrow_value(v, widget):
    return """
QLineEdit#Fission180ArrowValue {{ background: {field}; color: {primary_hot}; border: 1px solid {primary};
    border-image: none; border-radius: 0px; selection-background-color: {primary}; selection-color: {ink}; }}
QLineEdit#Fission180ArrowValue:focus {{ border: 1px solid {primary_hot}; background: {header}; }}
""".format(**v)


def _data_upload(v, widget):
    return """
QPushButton#Fission180DataPanelUpload {{ background: transparent; color: {ink}; border: none;
    border-radius: 0px; padding: 0px 8px; font-weight: bold; {ok_frame} }}
QPushButton#Fission180DataPanelUpload:hover {{ {ok_hover_frame} }}
QPushButton#Fission180DataPanelUpload:pressed {{ {ok_pressed_frame} }}
""".format(**v)


def _dim_label(v, widget):
    return "QLabel {{ color: {text_dim}; letter-spacing: 0.5px; }}".format(**v)


def _caption(v, widget):
    return "QLabel {{ color: {secondary}; text-transform: uppercase; letter-spacing: 1.5px; }}".format(**v)


def _role_colour(v, widget):
    """The colour of the palette role the widget asked for through colour() (none: no rule)."""
    role = widget.property(PROP_ROLE) if widget is not None else None
    if not role or role not in v:
        return ""
    return "\nQWidget {{ color: {0}; }}".format(v[role])


BLOCKS = {
    "home": _home,
    "home_update": _home_update,
    "home_notice": _home_notice,
    "ai": _ai,
    "sketch_palette": _palette_box("Fission180SketchPalette"),
    "measure_in_sketch": _palette_box("Fission180MeasureInSketch"),
    "measure_results": _measure_results,
    "marking": _marking,
    "arrow_value": _arrow_value,
    "data_upload": _data_upload,
    "dim_label": _dim_label,
    "caption": _caption,
    "role_colour": _role_colour,
}

_assets = {}  # palette digest -> values() (the pieces are files: made once per palette)


def block(part, p, widget=None):
    """The neon rules of `part` (BLOCKS) for palette `p`."""
    from . import neon_frames, neon_palette, neon_style

    key = neon_palette.digest({k: p.get(k) for k in neon_palette.ROLES})
    v = _assets.get(key)
    if v is None:
        base = neon_style.folder(p)
        frames = neon_frames.write(p, os.path.join(base, "frames"))
        mine = write(p, os.path.join(base, "frames", "panels"))
        v = values(p, frames, neon_style.fonts(), mine)
        _assets[key] = v
    return BLOCKS[part](v, widget)


def _set_raw(widget, text):
    """setStyleSheet without theme's hook (the text is in the look's colours already)."""
    from . import theme
    from .compat import QtWidgets

    original = theme._state.get("hook") or QtWidgets.QWidget.setStyleSheet
    original(widget, text)


def style(widget, text, part):
    """A panel's own style sheet `text` (written in Dark's colours, or baked from theme's
    colours) on `widget`: exactly widget.setStyleSheet(text) in Dark and Light; in Neon
    Lights `text` in neon colours plus the rules of BLOCKS[part]. Remembered on the widget,
    so theme_changed() redoes it after a look or preset switch."""
    from . import theme

    try:
        widget.setProperty(PROP_TEXT, text)
        widget.setProperty(PROP_PART, part)
    except RuntimeError:
        return
    if not theme.is_neon():
        widget.setStyleSheet(text)
        return
    try:
        neon_text = theme.translate(wrap(text)) + block(part, theme.palette(), widget)
        _set_raw(widget, neon_text)
        if text and "#" in text:
            widget.setProperty("fission180Qss", text)  # theme's own restyle starts from this
    except RuntimeError:
        pass
    except Exception as exc:
        warn("Neon Lights: panel style %s: %s" % (part, exc))
        try:
            widget.setStyleSheet(text)
        except RuntimeError:
            pass


def wrap(text):
    """A style sheet of property lines only ("color: #fff;") as a rule ("* { color: #fff; }"),
    so rules can be added after it: Qt reads "props + rule" as one broken sheet, retries it
    wrapped in "* {...}" and the added rule is lost."""
    if text and text.strip() and "{" not in text:
        return "* { %s }\n" % text.strip()
    return text


def colour(widget, text, role=None):
    """`text` (a style sheet in Dark's colours, e.g. "color: #9fd2ff;") on `widget`, and in
    Neon Lights its text colour the palette's `role` instead (None: theme.translate's colours).
    Dark's literal is what is remembered, so leaving Neon Lights with the panel open gives the
    exact Dark colour back, and a preset switch the new preset's colour."""
    try:
        widget.setProperty(PROP_ROLE, role or "")
    except RuntimeError:
        return
    style(widget, text, "role_colour")


def restyle_all():
    """Every panel styled through style(), again in the look in use."""
    from .compat import QtWidgets

    for widget in QtWidgets.QApplication.allWidgets():
        try:
            part = widget.property(PROP_PART)
            if not part:
                continue
            style(widget, widget.property(PROP_TEXT) or "", part)
        except RuntimeError:
            pass
        except Exception as exc:
            warn("Neon Lights: panel restyle: %s" % exc)


# -- long dialog titles ------------------------------------------------------------------------
# The title of a command dialog is in caps, letter-spaced, in the display face; a long one
# ("CREATE MESH SECTION SKETCH", 279 px) ran into the hazard stripes at the strip's right end.
# fit_titles() gives such a title a tighter spacing, then a smaller size, and as a last resort
# leaves the stripes out (property fission180Fit, rules in qss()).
FIT_SPACING = (1.5, 0.5, 0.0, 0.0)  # letter-spacing (px) of each level, as in the rules
FIT_SMALL = 11  # font size (px) of levels 2 and 3
FIT_GAP = 6  # px kept between the title's end and the stripes
PROP_FIT = "fission180Fit"
_fit = {"filter": None, "views": []}


def fit_level(widths, room):
    """The first level (0-2) whose title width in `widths` fits in `room` px; 3 (no stripes)
    when none does."""
    for level, width in enumerate(widths[:3]):
        if width <= room:
            return level
    return 3


def stripes_left(header):
    """The x (in the header strip) where the hazard stripes start."""
    return header.width() - SIZES["strip"][3] - SIZES["hazard"][0]


def _title_widths(title):
    """The title's text width at each level (from its font as the style sheet sets it)."""
    from .compat import QtGui

    text = title.text().replace("&", "").upper()
    out = []
    for level in range(3):
        font = QtGui.QFont(title.font())
        font.setCapitalization(QtGui.QFont.AllUppercase)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, FIT_SPACING[level])
        if level >= 2:
            font.setPixelSize(FIT_SMALL)
        out.append(QtGui.QFontMetrics(font).horizontalAdvance(text))
    return out


def _title_of(header):
    from .compat import QtWidgets

    for child in header.findChildren(QtWidgets.QToolButton):
        if child.property("class") == "header":
            return child
    return None


def _set_fit(widget, level):
    value = str(level) if level else ""
    if (widget.property(PROP_FIT) or "") == value:
        return False
    widget.setProperty(PROP_FIT, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
    return True


def fit_title(header):
    """Make `header`'s title (a command dialog's) fit before its hazard stripes."""
    from . import theme

    title = _title_of(header)
    if title is None:
        return
    if not theme.is_neon():
        _set_fit(title, 0)
        _set_fit(header, 0)
        return
    start = title.x() + (title.iconSize().width() + 4 if not title.icon().isNull() else 0) + 2
    level = fit_level(_title_widths(title), stripes_left(header) - FIT_GAP - start)
    changed = _set_fit(title, level)
    changed = _set_fit(header, 3 if level == 3 else 0) or changed
    if changed:
        title.updateGeometry()


def _headers(root):
    from .compat import QtWidgets

    return [w for w in root.findChildren(QtWidgets.QFrame) if w.property("class") == "header"]


def fit_titles():
    """Every open command dialog's title (see fit_title); also watches the task views for
    dialogs opened later (a filter on the task view's widgets only, not the whole app)."""
    from . import theme

    try:
        neon = theme.is_neon()
        for view in _task_views():
            if neon:
                _watch(view)
            else:
                _unwatch(view)
            for header in _headers(view):
                fit_title(header)
    except Exception as exc:
        warn("Neon Lights: dialog titles: %s" % exc)


def _task_views():
    from .compat import QtWidgets

    try:
        import FreeCADGui as Gui

        main = Gui.getMainWindow()
    except Exception:
        return []
    if main is None:
        return []
    return [
        w for w in main.findChildren(QtWidgets.QWidget)
        if w.metaObject().className() == "Gui::TaskView::TaskView"
    ]


def _make_filter():
    from .compat import QtCore

    kinds = (QtCore.QEvent.Show, QtCore.QEvent.Resize, QtCore.QEvent.LayoutRequest)

    class TitleWatch(QtCore.QObject):
        def eventFilter(self, obj, event):  # noqa: N802 (Qt's name)
            try:
                kind = event.type()
                if kind == QtCore.QEvent.ChildAdded:
                    child = event.child()
                    if child is not None and child.isWidgetType():
                        _watch(child)
                elif kind in kinds and obj.isWidgetType() and obj.property("class") == "header" \
                        and obj.metaObject().className() != "QSint::ActionLabel":
                    header = obj
                    QtCore.QTimer.singleShot(0, lambda: _fit_alive(header))
            except Exception as exc:  # never break a dialog
                warn("Neon Lights: dialog title: %s" % exc)
            return False

    return TitleWatch()


def _fit_alive(header):
    try:
        fit_title(header)
    except RuntimeError:
        pass  # the dialog closed meanwhile
    except Exception as exc:
        warn("Neon Lights: dialog title: %s" % exc)


def _watch(widget):
    """The title watcher on `widget` and everything in it (once each)."""
    from .compat import QtWidgets

    if _fit["filter"] is None:
        _fit["filter"] = _make_filter()
    for each in [widget] + widget.findChildren(QtWidgets.QWidget):
        if not each.property("fission180FitWatched"):
            each.setProperty("fission180FitWatched", True)
            each.installEventFilter(_fit["filter"])


def _unwatch(widget):
    """The title watcher off again (Dark and Light: no filter left on the task view)."""
    from .compat import QtWidgets

    if _fit["filter"] is None:
        return
    for each in [widget] + widget.findChildren(QtWidgets.QWidget):
        if each.property("fission180FitWatched"):
            each.setProperty("fission180FitWatched", None)
            each.removeEventFilter(_fit["filter"])


def theme_changed():
    """A look or preset switch (theme.LISTENERS): the panels again in the new colours."""
    _assets.clear()
    restyle_all()
    fit_titles()
