# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for Qt's own widgets everywhere in the window (design 6.3; plan task B1
owns this file): the window ground, menus and drop-downs, tooltips, lists and trees, tabs,
scroll bars, text boxes, buttons, dialogs, message boxes, check boxes, group boxes, sliders,
progress bars. FreeCAD's own windows (Report view, Python console, its Preferences) get it
too, as far as an application style sheet reaches.

Every selector of theme._QSS that is not a task panel's or one of Fission 180's own bars is
here (neon_qss_panels.py and neon_qss_shell.py have the others).

Sizes: paddings plus frame borders stay within a pixel or two of Dark's, so a dialog laid out
for Dark has room for its text in Neon Lights too (scenario neon_sizes checks it)."""


# The font of a tab's text (QTabBar::tab below; scenario neon_sizes measures tabs with it).
TAB_FONT = {"uppercase": True, "letter_spacing": 1}


def border(frames, piece):
    """A nine-slice border-image rule for `piece` (neon_frames)."""
    from . import neon_frames

    (st, sr, sb, sl), (bt, br, bb, bl) = neon_frames.slices(piece)
    horizontal, vertical = neon_frames.REPEAT.get(piece, ("stretch", "stretch"))
    if (bt, br, bb, bl) == (bt, bt, bt, bt):
        width = "%dpx" % bt
    else:
        width = "%dpx %dpx %dpx %dpx" % (bt, br, bb, bl)
    return "border-image: url(%s) %d %d %d %d %s %s; border-width: %s;" % (
        frames[piece], st, sr, sb, sl, horizontal, vertical, width
    )


def picture(frames, piece):
    """A whole picture stretched over a part (no slices: rails, handles)."""
    return "border-image: url(%s) 0 0 0 0 stretch stretch; border-width: 0px;" % frames[piece]


def segment_strength(p):
    """How opaque a progress bar's lit segments are: as bright as the percentage written over
    them allows (contrast 4 with the text; a bright yellow gets fainter segments)."""
    from .neon_palette import contrast, mix

    for percent in range(60, 25, -5):
        if contrast(p["text"], mix(p["field"], p["primary"], percent / 100.0)) >= 4.0:
            return percent / 100.0
    return 0.3


def qss(p, frames, fonts, translucent):
    """The style for palette `p`; `translucent`: pop-ups can be see-through (a compositing
    window manager), else they get a solid ground so no corner shows black."""
    from . import neon_frames
    from .neon_palette import rgba

    menu_ground = "transparent" if translucent else p["menu"]
    tip_ground = "transparent" if translucent else p["menu"]
    v = dict(p)
    v.update(
        menu_frame=border(frames, "menu"),
        menu_item_frame=border(frames, "menu_item"),
        tip_frame=border(frames, "tooltip"),
        button_frame=border(frames, "button"),
        button_hover_frame=border(frames, "button_hover"),
        button_pressed_frame=border(frames, "button_pressed"),
        button_default_frame=border(frames, "button_default"),
        field_frame=border(frames, "field"),
        field_focus_frame=border(frames, "field_focus"),
        panel_frame=border(frames, "panel"),
        tab_active_frame=border(frames, "tab_active"),
        progress_frame=border(frames, "progress"),
        message_frame=border(frames, "message"),
        message_warning_frame=border(frames, "message_warning"),
        message_error_frame=border(frames, "message_error"),
        handle_v=picture(frames, "scroll_handle"),
        handle_h=picture(frames, "scroll_handle_h"),
        rail_v=picture(frames, "rail_v"),
        rail_h=picture(frames, "rail_h"),
        slider_handle=picture(frames, "slider_handle"),
        menu_ground=menu_ground,
        tip_ground=tip_ground,
        check=frames["check"],
        check_on=frames["check_on"],
        radio=frames["radio"],
        radio_on=frames["radio_on"],
        arrow_down=frames["arrow_down"],
        hover_fill=rgba(p["primary"], 0.16),
        selected_fill=rgba(p["primary"], 0.24),
        line_soft=rgba(p["primary"], 0.35),
        segment=rgba(p["primary"], segment_strength(p)),
        default_text=neon_frames.on_colour(p, neon_frames.default_fill(p)),
        tab_font="%sletter-spacing: %spx;" % (
            "text-transform: uppercase; " if TAB_FONT["uppercase"] else "", TAB_FONT["letter_spacing"]
        ),
    )
    return """
/* -- Neon Lights: Qt's widgets ------------------------------------------------------------ */
QMainWindow, QMainWindow > QWidget {{ background: {chrome}; color: {text}; }}
QWidget {{ color: {text}; selection-background-color: {primary}; selection-color: {background}; }}
QToolTip {{ background: {tip_ground}; color: {text}; padding: 2px 6px 3px 6px; {tip_frame} }}
/* a pop-up whose window was made before Neon Lights was on has no alpha channel: solid
   (neon_popups.see_through marks it) */
QToolTip[fission180Solid="true"] {{ background: {menu}; }}

QMenuBar {{ background: {chrome}; color: {text}; }}
QMenuBar::item {{ background: transparent; padding: 3px 8px; }}
QMenuBar::item:selected {{ background: {hover_fill}; color: {primary_hot}; }}
/* Menus: glass with a cut-corner glowing frame; the hovered entry gets a bright bar on the
   left that fades to the right (neon_frames "menu_item"). */
QMenu {{ background: {menu_ground}; color: {text}; padding: 1px 0px; {menu_frame} }}
/* a menu made with the main window as its parent also matches "QMainWindow > QWidget" above,
   which would give it a solid ground (no glass); this one comes later and wins */
QMainWindow > QMenu {{ background: {menu_ground}; }}
QMenu[fission180Solid="true"], QMainWindow > QMenu[fission180Solid="true"] {{ background: {menu}; }}
QMenu::item {{ padding: 4px 26px 4px 8px; border-width: 0px 0px 0px 4px; border-style: solid;
    border-color: transparent; background: transparent; }}
QMenu::item:selected {{ color: {primary_hot}; {menu_item_frame} }}
QMenu::item:disabled {{ color: {disabled}; }}
QMenu::separator {{ height: 1px; background: {line_soft}; margin: 3px 10px 3px 14px; }}
QMenu::icon {{ padding-left: 6px; }}
QMenu::indicator {{ width: 12px; height: 12px; left: 4px; }}
QMenu::indicator:non-exclusive:unchecked {{ image: url({check}); }}
QMenu::indicator:non-exclusive:checked {{ image: url({check_on}); }}
QMenu::indicator:exclusive:unchecked {{ image: url({radio}); }}
QMenu::indicator:exclusive:checked {{ image: url({radio_on}); }}

QDockWidget {{ color: {text}; titlebar-close-icon: none; }}
QDockWidget::title {{ background: {chrome}; padding: 6px 8px; text-align: left; }}
QTreeView, QTreeWidget, QListView, QListWidget, QTableView {{
    background: {view}; color: {text}; border: none; alternate-background-color: {alternate};
    selection-background-color: {selected_fill}; selection-color: {primary_hot}; }}
QTreeView::item:hover {{ background: {hover_fill}; }}
QTreeView::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}
QListView::item:hover {{ background: {hover_fill}; }}
QListView::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}
QTableView {{ gridline-color: {line}; }}
QHeaderView::section {{ background: {header}; color: {text_dim}; border: none;
    border-bottom: 1px solid {line}; border-right: 1px solid {line_soft}; padding: 4px;
    text-transform: uppercase; letter-spacing: 0.6px; }}
QTableCornerButton::section {{ background: {header}; border: none; }}

/* no frame (FreeCAD's overlay docks are tab widgets that size themselves from it) */
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: {chrome}; color: {text_dim}; padding: 6px 14px; border: none;
    {tab_font} }}
QTabBar::tab:selected {{ color: {primary_hot}; {tab_active_frame} }}
QTabBar::tab:hover {{ color: {text}; }}

QStatusBar {{ background: {chrome}; color: {text_dim}; border-top: 1px solid {line}; }}
QStatusBar QLabel {{ color: {text_dim}; }}

/* Scroll bars: a thin rail with a cut-corner handle on it. */
QScrollBar:vertical, QScrollBar:horizontal {{ background: {chrome}; border: none; width: 10px; height: 10px; }}
QScrollBar::handle {{ background: transparent; border-radius: 0px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:vertical {{ margin: 1px 2px; {handle_v} }}
QScrollBar::handle:horizontal {{ margin: 2px 1px; {handle_h} }}
QScrollBar::handle:hover {{ background: {hover_fill}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; {rail_v} }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; {rail_h} }}

/* Text boxes: dark slots with a cut corner, a mark at the start and a glowing bottom rule;
   the focused one glows (field_focus). */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox, QTextEdit, QPlainTextEdit {{
    background: transparent; color: {text}; padding: 0px 3px; {field_frame}
    selection-background-color: {primary}; selection-color: {background}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QAbstractSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {{ {field_focus_frame} }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{ color: {disabled}; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ background: transparent; border: none;
    width: 14px; }}
QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {{ width: 8px; height: 8px; }}
QAbstractSpinBox::down-arrow {{ image: url({arrow_down}); }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox::down-arrow {{ image: url({arrow_down}); width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{ background: {menu}; color: {text}; border: 1px solid {primary};
    selection-background-color: {selected_fill}; selection-color: {primary_hot}; outline: none; }}
QComboBox QAbstractItemView::item {{ border-width: 0px 0px 0px 4px; border-style: solid;
    border-color: transparent; padding: 2px 4px; }}
QComboBox QAbstractItemView::item:selected {{ color: {primary_hot}; {menu_item_frame} }}

/* Buttons: cut corners, a bright notch on the lower cut; OK (the default) is filled with the
   primary colour. */
QPushButton {{ background: transparent; color: {text}; padding: 1px 10px; {button_frame} }}
QPushButton:hover {{ color: {primary_hot}; {button_hover_frame} }}
QPushButton:pressed {{ {button_pressed_frame} }}
QPushButton:default {{ color: {default_text}; font-weight: bold; {button_default_frame} }}
QPushButton:default:hover {{ color: {default_text}; {button_default_frame} }}
QPushButton:disabled {{ color: {disabled}; {button_frame} }}
QPushButton:checked {{ color: {primary_hot}; {button_pressed_frame} }}
QPushButton::menu-indicator {{ image: url({arrow_down}); width: 8px; height: 8px;
    subcontrol-position: right center; right: 4px; }}
/* Every dialog has the look's ground (see theme._QSS for why). */
QDialog, QMessageBox, QInputDialog {{ background: {chrome}; color: {text}; }}
QDialog QToolButton {{ background: transparent; color: {text}; padding: 0px 4px; {button_frame} }}
QDialog QToolButton:hover {{ color: {primary_hot}; {button_hover_frame} }}
QDialog QToolButton:pressed, QDialog QToolButton:checked {{ {button_pressed_frame} }}
QDialog QToolButton:disabled {{ color: {disabled}; }}
QDialog QToolButton[autoRaise="true"] {{ background: transparent; border: none; border-image: none; }}
QDialog QToolButton[autoRaise="true"]:hover {{ background: {hover_fill}; }}
/* Message boxes (neon_popups names their kind when they open): a hazard-stripe header for a
   warning, a red frame for an error, the primary colour for the others. */
QMessageBox[fission180Kind="info"] {{ {message_frame} }}
QMessageBox[fission180Kind="warning"] {{ {message_warning_frame} }}
QMessageBox[fission180Kind="error"] {{ {message_error_frame} }}
QMessageBox QLabel {{ color: {text}; }}
QMessageBox[fission180Kind="error"] QLabel#qt_msgbox_label {{ color: {bright}; }}

QCheckBox, QRadioButton, QLabel, QGroupBox {{ color: {text}; background: transparent; }}
QCheckBox::indicator {{ width: 13px; height: 13px; border: none; background: transparent;
    image: url({check}); }}
QCheckBox::indicator:hover {{ image: url({check}); }}
QCheckBox::indicator:checked {{ image: url({check_on}); }}
QCheckBox::indicator:disabled {{ image: url({check}); }}
QCheckBox:hover, QRadioButton:hover {{ color: {primary_hot}; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {disabled}; }}
QRadioButton::indicator {{ width: 13px; height: 13px; image: url({radio}); }}
QRadioButton::indicator:checked {{ image: url({radio_on}); }}
/* Group boxes: a HUD panel with ruler ticks; its title in capitals on the frame. */
QGroupBox {{ margin-top: 10px; padding-top: 8px; text-transform: uppercase; letter-spacing: 1px;
    {panel_frame} }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {primary_hot}; }}
QGroupBox::indicator {{ width: 13px; height: 13px; image: url({check}); }}
QGroupBox::indicator:checked {{ image: url({check_on}); }}

/* Progress bars: segmented. */
QProgressBar {{ background: transparent; color: {text}; text-align: center; min-height: 12px;
    {progress_frame} }}
QProgressBar::chunk {{ background: {segment}; width: 5px; margin: 1px; }}
/* Sliders: a thin rail, lit up to the handle; the handle a cut-corner block. */
QSlider::groove:horizontal {{ height: 2px; background: {line}; }}
QSlider::sub-page:horizontal {{ background: {primary}; height: 2px; }}
QSlider::handle:horizontal {{ background: transparent; width: 8px; height: 16px; margin: -7px 0px;
    {slider_handle} }}
QSlider::groove:vertical {{ width: 2px; background: {line}; }}
QSlider::add-page:vertical {{ background: {primary}; width: 2px; }}
QSlider::handle:vertical {{ background: {primary_hot}; height: 8px; margin: 0px -6px; }}
QSplitter::handle {{ background: {line}; }}
QToolBox::tab {{ background: {header}; color: {text}; padding: 3px 6px; text-transform: uppercase;
    letter-spacing: 0.6px; border-bottom: 1px solid {line}; }}
QToolBox::tab:selected {{ color: {primary_hot}; border-bottom: 1px solid {primary}; }}
QCalendarWidget QWidget {{ alternate-background-color: {alternate}; }}
""".format(**v)
