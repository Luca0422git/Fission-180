# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for Fission 180's own bars (design 6.3; plan task B2 owns this file):
the ribbon, the browser, the timeline and the navigation bar."""


def qss(p, frames, fonts, translucent):
    from .neon_palette import rgba
    from .neon_qss_chrome import border

    v = dict(p)
    v.update(
        tab_active_frame=border(frames, "tab_active"),
        hover_fill=rgba(p["primary"], 0.16),
        pressed_fill=rgba(p["primary"], 0.28),
        selected_fill=rgba(p["primary"], 0.22),
        workspace_frame=border(frames, "button_default"),
        display=fonts[1] or fonts[0] or "",
    )
    return """
/* -- Neon Lights: ribbon ------------------------------------------------------------------ */
#Fission180Ribbon {{ background: {chrome}; border: none; border-bottom: 1px solid {line}; }}
#Fission180Ribbon QToolButton {{ background: transparent; border: none; color: {text}; }}
#Fission180Ribbon QToolButton:hover {{ background: {hover_fill}; border-radius: 0px; color: {primary_hot}; }}
#Fission180Ribbon QToolButton:pressed {{ background: {pressed_fill}; }}
#Fission180Ribbon QToolButton:disabled {{ color: {disabled}; }}
#Fission180Ribbon QToolButton[role="tab"] {{ color: {text_dim}; padding: 3px 18px 4px 18px; font-size: 13px;
    letter-spacing: 2px; text-transform: uppercase; font-weight: bold; border-bottom: 2px solid transparent; }}
#Fission180Ribbon QToolButton[role="tab"]:checked {{ color: {primary_hot}; border-bottom: 2px solid {primary}; }}
#Fission180Ribbon QToolButton[role="tab"]:hover {{ background: transparent; color: {primary_hot}; }}
#Fission180Ribbon QToolButton[role="group"] {{ color: {primary}; font-size: 12px; letter-spacing: 1px;
    padding: 1px 6px; text-transform: uppercase; }}
#Fission180Ribbon QToolButton[role="group"]:hover, #Fission180Ribbon QToolButton[role="group"]:pressed,
#Fission180Ribbon QToolButton[role="group"][open="true"] {{ background: {selected_fill}; color: {primary_hot}; }}
#Fission180Ribbon QToolButton[role="workspace"] {{ background: transparent; color: {primary_hot};
    font-weight: bold; font-size: 12px; padding: 0px 8px; letter-spacing: 1px; {workspace_frame} }}
#Fission180Ribbon QFrame[role="separator"] {{ background: {primary_dim}; }}
#Fission180Ribbon QLabel[role="document"] {{ color: {text}; font-size: 13px; }}
#Fission180Ribbon QWidget[role="docbar"] {{ background: {background}; border-bottom: 1px solid {primary_dim}; }}

/* -- Neon Lights: browser ----------------------------------------------------------------- */
#Fission180Browser {{ font-size: 13px; background: {view}; }}
#Fission180Browser::item {{ height: 26px; }}
#Fission180Browser::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}

/* -- Neon Lights: timeline and navigation bar --------------------------------------------- */
#Fission180Timeline, #Fission180Timeline QWidget {{ background: {chrome}; }}
#Fission180Timeline {{ border-top: 1px solid {line}; }}
#Fission180Timeline QToolButton {{ background: transparent; border: none; border-radius: 0px; padding: 2px; }}
#Fission180Timeline QToolButton:hover {{ background: {hover_fill}; }}
#Fission180Timeline QToolButton[state="tip"] {{ background: {pressed_fill}; border-bottom: 2px solid {primary}; }}
#Fission180Timeline QFrame[role="marker"] {{ background: {marker}; border-radius: 0px; }}
#Fission180NavBar {{ background: {chrome}; border-radius: 0px; border: 1px solid {primary_dim}; }}
#Fission180NavBar QToolButton {{ background: transparent; border: none; padding: 3px; }}
#Fission180NavBar QToolButton:hover {{ background: {hover_fill}; border-radius: 0px; }}
""".format(**v)
