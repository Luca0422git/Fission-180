"""Command search popup (press S). Type a few letters, Enter to run."""

import FreeCADGui as Gui

from . import search_core, warn
from .compat import QtCore, QtWidgets


def _fission180_keys():
    """{command: key} Fission 180 binds itself (the current map, after Change Keyboard Shortcut):
    FreeCAD's own shortcut of those commands is parked while Fission 180 is on."""
    try:
        from . import config, shortcuts

        keys = {}
        for name, key in shortcuts.current_map().items():
            keys[name] = key
            better = config.PREFERRED.get(name)
            if better:
                keys[better] = key
        return keys
    except Exception:
        return {}


def _ribbon_entries(available):
    """Fission 180's menu entries under the names its menus show (Fusion's: "Control Point
    Spline", not FreeCAD's "B-spline by control points"), each with the command it runs."""
    from . import ribbon_config as cfg
    from .ribbon_ui import resolve

    out, seen = [], set()
    try:
        for tab in cfg.TABS:
            for group in tab["groups"]:
                for item in cfg.iter_items(group["items"]):
                    resolved = resolve(item.get("command"), available)
                    if resolved is None or resolved[0] == "__menu__" or resolved[1] is not None:
                        continue
                    key = (item["label"], resolved[0])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(
                        {
                            "name": resolved[0],
                            "text": item["label"],
                            "shortcut": item.get("key") or "",
                            "ribbon": True,
                        }
                    )
    except Exception as exc:
        warn("search: menu entries: %s" % exc)
    return out


# Fusion's names for tools Fission 180 lists under another name: typing Fusion's finds them
# (book parity report: "Parts List" is TABLES > Table, the Spur Gear add-in is CREATE > Gear).
ALSO_CALLED = (
    ("Parts List", "Fission180_DrawingTable"),
    ("Spur Gear", "Fission180_Gear"),
    ("Add-Ins", "Fission180_ScriptsAddIns"),
    ("Fit to View", "Fission180_Fit"),
    ("New Design", "Fission180_NewDesign"),
)


def _also_called(available, entries):
    listed = {e["text"].lower() for e in entries}
    out = []
    for text, name in ALSO_CALLED:
        if name in available and text.lower() not in listed:
            out.append({"name": name, "text": text, "shortcut": "", "ribbon": True})
    return out


def _build_entries():
    available = set(Gui.listCommands())
    entries = _ribbon_entries(available)
    entries += _also_called(available, entries)
    ours = _fission180_keys()
    for name in Gui.listCommands():
        text, shortcut = name, ""
        try:
            info = Gui.Command.get(name).getInfo()
            text = (info.get("menuText") or name).replace("&", "")
            shortcut = info.get("shortcut") or ""
        except Exception:
            pass
        if name in ours:
            shortcut = ours[name]
        entries.append({"name": name, "text": text, "shortcut": shortcut})
    return entries


class CommandSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Popup)
        self.setMinimumWidth(520)
        self._entries = _build_entries()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self._edit = QtWidgets.QLineEdit()
        self._edit.setPlaceholderText("Search commands...")
        self._list = QtWidgets.QListWidget()
        self._list.setMinimumHeight(300)
        layout.addWidget(self._edit)
        layout.addWidget(self._list)

        self._edit.textChanged.connect(self._refresh)
        self._edit.installEventFilter(self)
        self._list.itemActivated.connect(self._run_item)
        self._list.itemClicked.connect(self._run_item)
        self._refresh("")

    def _refresh(self, query):
        self._list.clear()
        for entry in search_core.rank(query, self._entries):
            label = entry["text"]
            if entry["shortcut"]:
                label += "    [%s]" % entry["shortcut"]
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, entry["name"])
            item.setToolTip(entry["name"])
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            row = self._list.currentRow()
            if key == QtCore.Qt.Key_Down:
                self._list.setCurrentRow(min(row + 1, self._list.count() - 1))
                return True
            if key == QtCore.Qt.Key_Up:
                self._list.setCurrentRow(max(row - 1, 0))
                return True
            if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                item = self._list.currentItem()
                if item is not None:
                    self._run_item(item)
                return True
        return super().eventFilter(obj, event)

    def _run_item(self, item):
        name = item.data(QtCore.Qt.UserRole)
        label = item.text()  # (read now: the row goes with the closed popup)
        self.close()
        # (ribbon_ui.run records it, as the ribbon, the menus and the keys do: Repeat, and the
        # sketch knows which tool runs; a spline started here was lost on OK: Luca, 2026-11-04)
        # Run after the popup has closed so commands that open dialogs work; the running
        # tool ends first, as with the ribbon and the keys (ribbon_ui.run: it stayed, or
        # FreeCAD asked about the dialog already open)
        QtCore.QTimer.singleShot(0, lambda: _run(name, label))


def _run(name, label):
    try:
        from . import ribbon_ui

        ribbon_ui.run((name, None), label)
    except Exception as exc:
        warn("search: %s" % exc)


def show():
    main = Gui.getMainWindow()
    dialog = CommandSearchDialog(main)
    geo = main.geometry()
    dialog.move(geo.center().x() - 260, geo.top() + 120)
    dialog.show()
    dialog._edit.setFocus()
