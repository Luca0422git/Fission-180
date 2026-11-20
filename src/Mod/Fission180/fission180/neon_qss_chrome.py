# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' style for Qt's own widgets everywhere in the window (design 6.3; plan task B1
owns this file): the window ground, menus and drop-downs, tooltips, lists and trees, tabs,
scroll bars, text boxes, buttons, dialogs, check boxes, group boxes, progress bars.

Every selector of theme._QSS that is not a task panel's or one of Fission 180's own bars is
here (neon_qss_panels.py and neon_qss_shell.py have the others)."""


def border(frames, piece):
    """A nine-slice border-image rule for `piece` (neon_frames)."""
    from . import neon_frames

    s, b = neon_frames.SLICE[piece], neon_frames.BORDER[piece]
    return "border-image: url(%s) %d %d %d %d stretch stretch; border-width: %dpx;" % (
        frames[piece], s, s, s, s, b
    )


def qss(p, frames, fonts, translucent):
    """The style for palette `p`; `translucent`: pop-ups can be see-through (a compositing
    window manager), else they get a solid ground so no corner shows black."""
    from .neon_palette import rgba

    menu_ground = "transparent" if translucent else p["menu"]
    tip_ground = "transparent" if translucent else p["menu"]
    v = dict(p)
    v.update(
        menu_frame=border(frames, "menu"),
        tip_frame=border(frames, "tooltip"),
        button_frame=border(frames, "button"),
        button_hover_frame=border(frames, "button_hover"),
        button_pressed_frame=border(frames, "button_pressed"),
        button_default_frame=border(frames, "button_default"),
        field_frame=border(frames, "field"),
        field_focus_frame=border(frames, "field_focus"),
        panel_frame=border(frames, "panel"),
        tab_active_frame=border(frames, "tab_active"),
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
    )
    return """
/* -- Neon Lights: Qt's widgets ------------------------------------------------------------ */
QMainWindow, QMainWindow > QWidget {{ background: {chrome}; color: {text}; }}
QWidget {{ color: {text}; selection-background-color: {primary}; selection-color: {background}; }}
QToolTip {{ background: {tip_ground}; color: {text}; padding: 3px 6px; {tip_frame} }}

QMenuBar {{ background: {chrome}; color: {text}; }}
QMenuBar::item:selected {{ background: {hover_fill}; color: {primary_hot}; }}
QMenu {{ background: {menu_ground}; color: {text}; padding: 2px 0px; {menu_frame} }}
QMenu::item {{ padding: 4px 26px 4px 10px; border-left: 2px solid transparent; }}
QMenu::item:selected {{ background: {hover_fill}; color: {primary_hot}; border-left: 2px solid {primary}; }}
QMenu::item:disabled {{ color: {disabled}; }}
QMenu::separator {{ height: 1px; background: {line_soft}; margin: 3px 10px; }}
QMenu::icon {{ padding-left: 6px; }}

QDockWidget {{ color: {text}; titlebar-close-icon: none; }}
QDockWidget::title {{ background: {chrome}; padding: 6px 8px; text-align: left; }}
QTreeView, QTreeWidget, QListView, QListWidget, QTableView {{
    background: {view}; color: {text}; border: none; alternate-background-color: {alternate};
    selection-background-color: {selected_fill}; selection-color: {primary_hot}; }}
QTreeView::item:hover {{ background: {hover_fill}; }}
QTreeView::item:selected {{ background: {selected_fill}; color: {primary_hot}; }}
QHeaderView::section {{ background: {header}; color: {text_dim}; border: none;
    border-bottom: 1px solid {line}; padding: 4px; text-transform: uppercase; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: {chrome}; color: {text_dim}; padding: 6px 14px; border: none;
    text-transform: uppercase; letter-spacing: 1px; }}
QTabBar::tab:selected {{ color: {primary_hot}; {tab_active_frame} }}
QTabBar::tab:hover {{ color: {text}; }}

QStatusBar {{ background: {chrome}; color: {text_dim}; border-top: 1px solid {line}; }}
QScrollBar:vertical, QScrollBar:horizontal {{ background: {chrome}; border: none; width: 10px; height: 10px; }}
QScrollBar::handle {{ background: {primary_dim}; border-radius: 0px; min-height: 24px; min-width: 24px;
    margin: 2px; }}
QScrollBar::handle:hover {{ background: {primary}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox, QTextEdit, QPlainTextEdit {{
    background: transparent; color: {text}; padding: 0px 3px; {field_frame}
    selection-background-color: {primary}; selection-color: {background}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QAbstractSpinBox:focus,
QTextEdit:focus, QPlainTextEdit:focus {{ {field_focus_frame} }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{ color: {disabled}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox::down-arrow {{ image: url({arrow_down}); width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{ background: {menu}; color: {text}; border: 1px solid {primary};
    selection-background-color: {selected_fill}; selection-color: {primary_hot}; outline: none; }}
QPushButton {{ background: transparent; color: {text}; padding: 1px 10px; {button_frame} }}
QPushButton:hover {{ color: {primary_hot}; {button_hover_frame} }}
QPushButton:pressed {{ {button_pressed_frame} }}
QPushButton:default {{ color: {primary_hot}; font-weight: bold; {button_default_frame} }}
QPushButton:disabled {{ color: {disabled}; }}
/* Every dialog has the look's ground (see theme._QSS for why). */
QDialog, QMessageBox, QInputDialog {{ background: {chrome}; color: {text}; }}
QDialog QToolButton {{ background: transparent; color: {text}; padding: 0px 4px; {button_frame} }}
QDialog QToolButton:hover {{ color: {primary_hot}; {button_hover_frame} }}
QDialog QToolButton:pressed, QDialog QToolButton:checked {{ {button_pressed_frame} }}
QDialog QToolButton:disabled {{ color: {disabled}; }}
QDialog QToolButton[autoRaise="true"] {{ background: transparent; border: none; border-image: none; }}
QDialog QToolButton[autoRaise="true"]:hover {{ background: {hover_fill}; }}
QCheckBox, QRadioButton, QLabel, QGroupBox {{ color: {text}; background: transparent; }}
QCheckBox::indicator {{ width: 13px; height: 13px; border: none; background: transparent;
    image: url({check}); }}
QCheckBox::indicator:hover {{ image: url({check}); }}
QCheckBox::indicator:checked {{ image: url({check_on}); }}
QCheckBox::indicator:disabled {{ image: url({check}); }}
QRadioButton::indicator {{ width: 13px; height: 13px; image: url({radio}); }}
QRadioButton::indicator:checked {{ image: url({radio_on}); }}
QGroupBox {{ margin-top: 10px; padding-top: 8px; {panel_frame} }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {primary_hot};
    text-transform: uppercase; letter-spacing: 1px; }}
QProgressBar {{ background: {field}; color: {text}; border: 1px solid {line}; text-align: center; height: 12px; }}
QProgressBar::chunk {{ background: {primary}; width: 6px; margin: 1px; }}
QSlider::groove:horizontal {{ height: 2px; background: {line}; }}
QSlider::sub-page:horizontal {{ background: {primary}; }}
QSlider::handle:horizontal {{ background: {primary_hot}; width: 8px; margin: -6px 0px; }}
QSplitter::handle {{ background: {line}; }}
QMessageBox QLabel {{ color: {text}; }}
""".format(**v)
