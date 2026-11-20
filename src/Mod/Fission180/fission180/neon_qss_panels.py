# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for command dialogs (FreeCAD's task panels) and Fission 180's other
panels (design 6.3; plan task B3 owns this file)."""


def qss(p, frames, fonts, translucent):
    from .neon_palette import rgba
    from .neon_qss_chrome import border

    v = dict(p)
    v.update(
        panel_frame=border(frames, "panel"),
        header_frame=border(frames, "header"),
        button_frame=border(frames, "button"),
        button_hover_frame=border(frames, "button_hover"),
        button_pressed_frame=border(frames, "button_pressed"),
        stripes=frames["stripes"],
        hover_fill=rgba(p["primary"], 0.16),
    )
    return """
/* -- Neon Lights: command dialogs (task panels) ------------------------------------------- */
Gui--TaskView--TaskView > QScrollArea {{ border: none; background: transparent; }}
QSint--ActionPanel, QSint--ActionPanel QScrollArea, QSint--ActionPanel QScrollArea > QWidget > QWidget {{
    background: {chrome}; }}
QSint--ActionGroup {{ background: {chrome}; }}
QSint--ActionGroup QFrame[class="header"] {{ background: transparent; {header_frame}
    background-image: url({stripes}); background-repeat: no-repeat; background-position: right center; }}
QSint--ActionGroup QToolButton[class="header"] {{ color: {primary_hot}; font-weight: bold; text-align: left;
    border: none; background: transparent; text-transform: uppercase; letter-spacing: 1px; }}
QSint--ActionGroup QFrame[class="header"] QLabel {{ color: {primary_hot}; background: transparent;
    text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }}
QSint--ActionGroup QFrame[class="content"] {{ background: {chrome}; border: 1px solid {line};
    border-top: none; }}
QSint--ActionGroup QFrame[class="content"] QTreeView, QSint--ActionGroup QFrame[class="content"] QListView,
QSint--ActionGroup QFrame[class="content"] QTableView {{ background: {field}; }}
QSint--ActionGroup QFrame[class="content"] QToolButton {{ background: transparent; color: {text};
    padding: 0px; min-height: 16px; {button_frame} }}
QSint--ActionGroup QFrame[class="content"] QToolButton:checked {{ color: {primary_hot}; {button_pressed_frame} }}
QSint--ActionGroup QFrame[class="content"] QToolButton:hover {{ color: {primary_hot}; {button_hover_frame} }}
QSint--ActionGroup QFrame[class="separator"] {{ background: transparent; }}
""".format(**v)
