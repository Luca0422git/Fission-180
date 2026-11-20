# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for Fission 180's own bars (design 6.3; plan task B2 owns this file):
the ribbon, the document tabs, the browser, the timeline and the navigation bar.

What a style sheet cannot draw (the tab's glowing underline with its chamfered end, the
brackets around group names, the navigation bar's HUD frame, the timeline's marker beam and
chips, the browser's selection bar) is painted by the widgets themselves while Neon Lights is
on (neon_shell_paint)."""

# opacity of `primary` in a browser row that is selected / under the mouse: the ::item rules
# below and the indent, which browser_ui.drawBranches paints itself
ROW_SELECTED = 0.22
ROW_HOVER = 0.10
# The workspace button (ribbon_ui, a fixed 136 x 74): its font size, letter spacing and side
# padding in px. Orbitron is wide: at 12 px with 2 px spacing MANUFACTURE did not fit
# (ribbon_ui.WORKSPACE_LABELS must all fit: neon_shell checks it with the font's metrics).
WORKSPACE_FONT_PX = 10
WORKSPACE_SPACING = 1
WORKSPACE_PAD = 6


def close_svg(p, hover=False):
    """The document tabs' close button in Neon Lights (16 x 16): a chamfered key with a thin
    cross; on hover it lights up in `alert`."""
    line = p["alert"] if hover else p["primary_dim"]
    cross = p["primary_hot"] if not hover else p.get("bright", p["primary_hot"])
    fill = p["alert"] if hover else p["primary"]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
        '<path d="M4 1.5 H14.5 V12 L12 14.5 H1.5 V4 Z" fill="%s" fill-opacity="%s" stroke="%s" '
        'stroke-width="1"/>'
        '<path d="M5.5 5.5 L10.5 10.5 M10.5 5.5 L5.5 10.5" stroke="%s" stroke-width="1.6" '
        'stroke-linecap="square"/>'
        "</svg>" % (fill, "0.35" if hover else "0.08", line, cross)
    )


def _close_images(p, frames):
    """{"close": path, "close_hover": path} written next to Neon Lights' frame pictures (the
    folder is made per palette); {} without frames."""
    import os

    if not frames:
        return {}
    folder = os.path.dirname(next(iter(frames.values())))
    out = {}
    for name, hover in (("close", False), ("close_hover", True)):
        path = os.path.join(folder, "doc_tab_%s.svg" % name)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(close_svg(p, hover))
        out[name] = path.replace("\\", "/")
    return out


def _values(p, frames, fonts):
    from .neon_palette import mix, rgba
    from .neon_qss_chrome import border

    v = dict(p)
    v.update(
        tab_active_frame=border(frames, "tab_active") if frames else "",
        hover_fill=rgba(p["primary"], 0.16),
        hover_glow=(
            "qradialgradient(cx:0.5, cy:0.5, radius:0.62, fx:0.5, fy:0.5, stop:0 %s, stop:0.55 %s, "
            "stop:1 %s)" % (rgba(p["primary"], 0.42), rgba(p["primary"], 0.14), rgba(p["primary"], 0.0))
        ),
        pressed_fill=rgba(p["primary"], 0.28),
        selected_fill=rgba(p["primary"], ROW_SELECTED),
        row_hover=rgba(p["primary"], ROW_HOVER),
        tab_fill=rgba(p["primary"], 0.10),
        docbar=mix(p["background"], p["primary"], 0.03),
        ribbon=(
            "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %s, stop:1 %s)"
            % (p["chrome"], mix(p["chrome"], p["background"], 0.45))
        ),
        workspace_frame=border(frames, "button_default") if frames else "",
        display=fonts[1] or fonts[0] or "",
        ws_px=WORKSPACE_FONT_PX,
        ws_spacing=WORKSPACE_SPACING,
        ws_pad=WORKSPACE_PAD,
    )
    v["display_rule"] = ("font-family: \"%s\";" % v["display"]) if v["display"] else ""
    images = _close_images(p, frames)
    v["close_rules"] = (
        "#Fission180DocumentTabs::close-button { image: url(%s); subcontrol-position: right; }\n"
        "#Fission180DocumentTabs::close-button:hover { image: url(%s); }"
        % (images["close"], images["close_hover"])
        if images
        else ""
    )
    return v


def qss(p, frames, fonts, translucent):
    v = _values(p, frames, fonts)
    return """
/* -- Neon Lights: ribbon ------------------------------------------------------------------ */
#Fission180Ribbon {{ background: {chrome}; border: none; border-bottom: 1px solid {line}; }}
#Fission180RibbonCommands {{ background: {ribbon}; }}
#Fission180Ribbon QToolButton {{ background: transparent; border: none; color: {text}; }}
#Fission180Ribbon QToolButton:hover {{ background: {hover_glow}; border-radius: 0px; color: {primary_hot}; }}
#Fission180Ribbon QToolButton:pressed {{ background: {pressed_fill}; }}
#Fission180Ribbon QToolButton:disabled {{ color: {disabled}; }}
#Fission180Ribbon QToolButton[role="tab"] {{ color: {text_dim}; padding: 3px 18px 4px 18px; font-size: 13px;
    letter-spacing: 2px; text-transform: uppercase; font-weight: bold; border-bottom: 2px solid transparent; }}
#Fission180Ribbon QToolButton[role="tab"]:checked {{ color: {primary_hot}; background: {tab_fill}; }}
#Fission180Ribbon QToolButton[role="tab"]:hover {{ background: transparent; color: {primary_hot}; }}
#Fission180Ribbon QToolButton[role="group"] {{ color: {primary}; font-size: 12px; letter-spacing: 1px;
    padding: 1px 6px; text-transform: uppercase; }}
#Fission180Ribbon QToolButton[role="group"]:hover, #Fission180Ribbon QToolButton[role="group"]:pressed,
#Fission180Ribbon QToolButton[role="group"][open="true"] {{ background: {selected_fill}; color: {primary_hot}; }}
#Fission180Ribbon QToolButton[role="workspace"] {{ background: transparent; color: {primary_hot};
    font-weight: bold; font-size: {ws_px}px; padding: 0px {ws_pad}px; letter-spacing: {ws_spacing}px;
    {display_rule} {workspace_frame} }}
#Fission180Ribbon QToolButton[role="workspace"]:hover {{ background: {hover_glow}; color: {bright}; }}
#Fission180Ribbon QFrame[role="separator"] {{ background: {primary_dim}; }}
#Fission180Ribbon QLabel[role="document"] {{ color: {text}; font-size: 13px; }}
#Fission180Ribbon QWidget[role="docbar"] {{ background: {docbar}; border-bottom: 1px solid {primary_dim}; }}

/* -- Neon Lights: document tabs (the designs open, in the top bar) ------------------------ */
#Fission180DocumentTabs::tab {{ background: transparent; color: {text_dim}; border: none;
    border-bottom: 2px solid transparent; padding: 6px 14px; }}
#Fission180DocumentTabs::tab:hover {{ background: {row_hover}; color: {primary_hot}; }}
#Fission180DocumentTabs::tab:selected {{ background: {tab_fill}; color: {primary_hot};
    border-bottom: 2px solid {primary}; }}
{close_rules}

/* -- Neon Lights: browser ----------------------------------------------------------------- */
#Fission180Browser {{ font-size: 13px; background: {view}; }}
#Fission180Browser::item {{ height: 26px; }}
#Fission180Browser::item:hover {{ background: {row_hover}; }}
#Fission180Browser::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}

/* -- Neon Lights: timeline and navigation bar --------------------------------------------- */
#Fission180Timeline, #Fission180Timeline QWidget {{ background: {chrome}; }}
#Fission180Timeline {{ border-top: 1px solid {primary_dim}; }}
#Fission180Timeline QToolButton {{ background: transparent; border: none; border-radius: 0px; padding: 2px; }}
#Fission180Timeline QToolButton:hover {{ background: {hover_glow}; }}
#Fission180Timeline QToolButton[state="tip"] {{ background: {pressed_fill}; border-bottom: 2px solid {primary}; }}
#Fission180Timeline QFrame[role="marker"] {{ background: transparent; border-radius: 0px; }}
#Fission180NavBar {{ background: {chrome}; border-radius: 0px; border: none; }}
#Fission180NavBar QToolButton {{ background: transparent; border: none; padding: 3px; }}
#Fission180NavBar QToolButton:hover {{ background: {hover_glow}; border-radius: 0px; }}
#Fission180NavBar QToolButton:checked {{ background: {pressed_fill}; }}
""".format(**v)


def timeline(p):
    """Rules the timeline adds to its own style sheet while Neon Lights is on (its own sheet
    beats the app's): the steps as dark chips that light up, the warning and error tints in
    the palette's alert."""
    from .neon_palette import mix, rgba

    v = dict(p)
    v.update(
        chip_hover=rgba(p["primary"], 0.18),
        chip_selected=rgba(p["primary"], 0.30),
        warning_fill=rgba(mix(p["alert"], p["text"], 0.35), 0.22),
        error_fill=rgba(p["alert"], 0.26),
    )
    return """
#Fission180Timeline QToolButton[role="step"] {{ background: transparent; border: 1px solid transparent;
    border-radius: 0px; }}
#Fission180Timeline QToolButton[role="step"]:hover {{ background: {chip_hover}; }}
#Fission180Timeline QToolButton[role="step"][status="warning"] {{ background: {warning_fill}; border: 1px solid transparent; }}
#Fission180Timeline QToolButton[role="step"][status="error"] {{ background: {error_fill}; border: 1px solid transparent; }}
#Fission180Timeline QToolButton[role="step"][selected="true"] {{ background: {chip_selected}; border: 1px solid transparent; }}
#Fission180Timeline QFrame[role="drop"] {{ background: {secondary}; }}
#Fission180Timeline QFrame[role="group_end"] {{ background: {secondary_dim}; border-radius: 0px; }}
#Fission180Timeline QFrame[role="drop"][refused="true"] {{ background: {alert}; }}
#Fission180Timeline QLineEdit {{ background: {field}; border: 1px solid {primary}; color: {text}; padding: 1px 3px; }}
""".format(**v)
