# SPDX-License-Identifier: LGPL-2.1-or-later
"""Appearance (Modify > Appearance, A) with a Fusion-like dialog:

  Apply To        Bodies/Components / Faces
  In This Design  the looks the design has: its default look first, then the ones in use and
                  the ones kept (a duplicate). Click one to pick it again, double-click to
                  edit it (appearance_edit_ui.py), right-click: Edit, Duplicate, Rename,
                  Delete, Select Objects Applied To, Add to Favorites
  Library         a search box, a category list (All, Favorites, My Appearances, Metal,
                  Plastic, Wood, Paint, Glass...) and the looks with their names
                  (appearance_library.py); right-click: Add to / Remove from Favorites
  Custom          any colour: type #RRGGBB or move the R / G / B sliders
  Remove          a click then takes a look away again instead of giving one

Pick a look (click it), then click bodies (or faces) in the 3D view: each click gives it
that look at once. Or drag a look onto a body or a face, as in Fusion. Bodies or faces
selected before the command get the first look picked. OK keeps all of it as one undo step,
Cancel / Esc puts every look back. A face keeps its look through later steps while it is
still there.

Apply To Faces never colours a whole body: a drop or click that lands on an edge takes the
face next to the pointer, and says so when there is none. A look given to a body whose
faces have looks of their own asks first, as Fusion does: Keep them over the new look, or
Remove them.

The document side is appearance.py. This module also keeps the looks on screen: its watch
puts a body's stored look back whenever anything else has written the colours FreeCAD draws
from (book parity report, bug 16).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import appearance, appearance_library, appearance_textures, bodies, bodies_gui
from . import ui_icon_path, warn
from .bodies_panel import BodyPanel, start as _start
from .compat import QtCore, QtGui, QtWidgets

APPLY_TO = [("Bodies/Components", "bodies"), ("Faces", "faces")]
SWATCH = 28
ALL, FAVORITES, MINE = "All", "Favorites", "My Appearances"
_ICONS = {}


def swatch_pixmap(look, size=SWATCH):
    """A look's picture: its colour with its pattern, a highlight for a shiny one, a stroke
    for a see-through one."""
    key = (
        size,
        tuple(round(c, 3) for c in look["color"]),
        look.get("texture") or "",
        round(float(look.get("shininess", 0.5)), 2),
        round(float(look.get("transparency", 0.0)), 2),
    )
    if key in _ICONS:
        return _ICONS[key]
    r, g, b = [int(round(c * 255)) for c in look["color"]]
    image = QtGui.QImage(size, size, QtGui.QImage.Format_RGB32)
    image.fill(QtGui.QColor(r, g, b))
    name = look.get("texture")
    at = appearance_textures.function(name) if name else None
    if at is not None:
        # (half a repeat across the swatch, so the pattern can be told at this size)
        for y in range(size):
            for x in range(size):
                shade = appearance_textures.blend(
                    look["color"], at((x + 0.5) / size * 0.5, (y + 0.5) / size * 0.5)
                )
                image.setPixelColor(
                    x, y, QtGui.QColor(*[max(0, min(255, int(round(c * 255)))) for c in shade])
                )
    pixmap = QtGui.QPixmap.fromImage(image)
    painter = QtGui.QPainter(pixmap)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        shine = float(look.get("shininess", 0.5))
        if shine > 0.3:  # a highlight, brighter for shinier looks
            light = QtGui.QColor(255, 255, 255, int(60 + 120 * shine))
            painter.setBrush(light)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(size // 5, size // 6, size // 3, size // 4)
        if look.get("transparency", 0.0) > 0.2:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 160), 1))
            painter.drawLine(0, size, size, 0)
        painter.setPen(QtGui.QPen(QtGui.QColor("#1b1f24"), 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(0, 0, size - 1, size - 1)
    finally:
        painter.end()
    _ICONS[key] = pixmap
    return pixmap


def swatch_icon(look):
    return QtGui.QIcon(swatch_pixmap(look))


class _EnterTakes(QtCore.QObject):
    """Event filter: Enter / Return in a field runs `action` and goes no further."""

    def __init__(self, action):
        super().__init__()
        self.action = action

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress and event.key() in (
                QtCore.Qt.Key_Return,
                QtCore.Qt.Key_Enter,
            ):
                self.action()
                return True
        except Exception as exc:
            warn("colour field: %s" % exc)
        return False


MIME = "application/x-fission180-look"


def look_of(mime):
    """The look carried by a drag (a swatch of the Appearance dialog), or None."""
    import json

    try:
        if mime is None or not mime.hasFormat(MIME):
            return None
        return json.loads(bytes(mime.data(MIME)).decode("utf-8"))
    except Exception:
        return None


def mime_of(look):
    import json

    mime = QtCore.QMimeData()
    mime.setData(MIME, QtCore.QByteArray(json.dumps(look).encode("utf-8")))
    return mime


class _SwatchList(QtWidgets.QListWidget):
    """Swatches; dragging one carries its look (drop it on a body or a face)."""

    def mimeTypes(self):
        return [MIME]

    def mimeData(self, items):
        look = items[0].data(QtCore.Qt.UserRole) if items else None
        return mime_of(dict(look)) if look else QtCore.QMimeData()


class _DropTaker(QtCore.QObject):
    """Event filter on the 3D view's drawing widget: accepts a swatch dragged from the
    Appearance dialog and hands the drop to the dialog."""

    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def eventFilter(self, obj, event):
        try:
            kind = event.type()
            if kind not in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove, QtCore.QEvent.Drop):
                return False
            panel = self.panel
            if panel is None or panel._closed:
                return False
            look = look_of(event.mimeData())
            if look is None:
                return False
            if kind == QtCore.QEvent.Drop:
                position = event.position().toPoint()
                QtCore.QTimer.singleShot(
                    0, lambda: panel._guarded(lambda: panel.dropped(look, position))
                )
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            return True
        except Exception as exc:
            warn("appearance drop: %s" % exc)
            return False


def _gl_widget():
    area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    if area is None:
        return None
    sub = area.activeSubWindow() or (area.subWindowList() or [None])[-1]
    if sub is None:
        return None
    for widget in sub.findChildren(QtWidgets.QWidget):
        if widget.metaObject().className() == "QOpenGLWidget":
            return widget
    return None


# Pixels round the pointer looked at, nearest first, for the face next to an edge.
_NEAR = [(0, 0)] + [
    (dx * radius, dy * radius)
    for radius in (3, 6, 10)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))
]


class AppearancePanel(BodyPanel):
    title = "Appearance"
    icon = "appearance"
    needs_pick = ()

    def picks_bodies(self):
        """Apply To Bodies: the body under the pointer lights up whole (body_hover); Faces:
        the face."""
        try:
            return self.apply_to.currentData() == "bodies"
        except Exception:
            return False

    def __init__(self, doc):
        self.look = None
        self.removing = False
        self.editor = None
        self.pending = []  # selection made before the command, waiting for the first look
        super().__init__(doc, "Appearance")
        self.pending = [(o, s) for o, s, _p in bodies_gui.selection_entries() if o.Document is doc]
        bodies_gui.clear_selection()
        # Faces clicked first: Apply To Faces. A box round bodies also brings their edges:
        # that means the bodies (each gets the look once), not the faces it happened to see.
        if (
            self.pending
            and any(s.startswith("Face") for _o, s in self.pending)
            and not any(s.startswith(("Edge", "Vertex")) for _o, s in self.pending)
        ):
            from . import hole_common

            hole_common.set_combo(self.apply_to, "faces")
        self._fill_design()
        self._drop_widget = None
        self._install_drop()
        self.info.setText(
            "Pick a look, then click bodies (or faces) to give them that look (or drag it "
            "onto them)."
            if not self.pending
            else "Pick a look for the selection."
        )

    # -- form --------------------------------------------------------------------------------------
    def build_form(self):
        self.apply_to, _ = self.combo("Apply To", APPLY_TO, "bodies", self._apply_to_changed)
        self.remove = QtWidgets.QPushButton("Remove")
        self.remove.setObjectName("Fission180LookRemove")
        self.remove.setCheckable(True)
        self.remove.setToolTip(
            "Take a look away again: click a body to show its material's look, or (Apply To "
            "Faces) a face to show the body's look"
        )
        self.remove.toggled.connect(lambda on: self._guarded(lambda: self._remove_toggled(on)))
        self.layout.addRow("", self.remove)
        self.layout.addRow(QtWidgets.QLabel("<b>In This Design</b>"))
        self.design = self._list(rows=2)
        self.design.setObjectName("Fission180LooksInDesign")
        self.design.itemDoubleClicked.connect(
            lambda item: self._guarded(lambda: self.edit_look(item.data(QtCore.Qt.UserRole)))
        )
        self.design.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.design.customContextMenuRequested.connect(
            lambda pos: self._guarded(lambda: self._design_menu(pos))
        )
        self.layout.addRow(self.design)
        self.layout.addRow(QtWidgets.QLabel("<b>Library</b>"))
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Fission180LookSearch")
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip(
            'Type part of a name ("oak", "anod red"): the list shows the matches'
        )
        self.search.textChanged.connect(lambda *_: self._guarded(self._fill_library))
        # Enter in the search box must not reach the task panel (it would press OK).
        self._search_enter = _EnterTakes(lambda: self._guarded(self._fill_library))
        self.search.installEventFilter(self._search_enter)
        self.category = QtWidgets.QComboBox()
        self.category.setObjectName("Fission180LookCategory")
        for name in [ALL, FAVORITES, MINE] + appearance_library.CATEGORIES:
            self.category.addItem(name, name)
        self.category.currentIndexChanged.connect(lambda *_: self._guarded(self._fill_library))
        row = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(self.search, 1)
        line.addWidget(self.category)
        self.layout.addRow(row)
        self.library = self._list(rows=6, names=True)
        self.library.setObjectName("Fission180LookLibrary")
        self.library.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.library.customContextMenuRequested.connect(
            lambda pos: self._guarded(lambda: self._library_menu(pos))
        )
        self.layout.addRow(self.library)
        self.found = QtWidgets.QLabel("")
        self.found.setStyleSheet("color: #b8c7d9;")
        self.layout.addRow(self.found)
        self._fill_library()
        self.layout.addRow(QtWidgets.QLabel("<b>Custom</b>"))
        row = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        self.hex = QtWidgets.QLineEdit("#808080")
        self.hex.setMaxLength(7)
        self.hex.setToolTip("Type a colour as #RRGGBB, then Enter")
        self.hex.editingFinished.connect(lambda: self._guarded(self._hex_typed))
        # Enter in the colour field takes the colour; it must not reach the task panel,
        # which would take it as OK and close the dialog.
        self._enter_filter = _EnterTakes(lambda: self._guarded(self._hex_typed))
        self.hex.installEventFilter(self._enter_filter)
        self.preview_swatch = QtWidgets.QLabel()
        self.preview_swatch.setFixedSize(SWATCH, SWATCH)
        self.use_custom = QtWidgets.QPushButton("Use")
        self.use_custom.setToolTip("Pick this colour as the look")
        self.use_custom.clicked.connect(lambda *_: self._guarded(self._custom_picked))
        line.addWidget(self.preview_swatch)
        line.addWidget(self.hex, 1)
        line.addWidget(self.use_custom)
        self.layout.addRow("Colour", row)
        self.sliders = []
        for name in ("R", "G", "B"):
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 255)
            slider.setValue(128)
            slider.valueChanged.connect(lambda *_: self._guarded(self._slid))
            self.layout.addRow(name, slider)
            self.sliders.append(slider)
        self._paint_custom()
        self.chosen = QtWidgets.QLabel("")
        self.chosen.setStyleSheet("color: #b8c7d9;")
        self.layout.addRow("Look", self.chosen)

    def _list(self, rows, names=False):
        view = _SwatchList()
        view.setIconSize(QtCore.QSize(SWATCH, SWATCH))
        if names:  # the library: a list with the names, as long as it gets
            view.setViewMode(QtWidgets.QListView.ListMode)
            view.setUniformItemSizes(True)
            view.setFixedHeight(rows * (SWATCH + 6) + 8)
        else:
            view.setViewMode(QtWidgets.QListView.IconMode)
            view.setGridSize(QtCore.QSize(SWATCH + 14, SWATCH + 14))
            view.setResizeMode(QtWidgets.QListView.Adjust)
            view.setFixedHeight(rows * (SWATCH + 14) + 8)
        view.setMovement(QtWidgets.QListView.Static)
        view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        view.itemClicked.connect(lambda item: self._guarded(lambda: self._swatch_clicked(item)))
        view.setDragEnabled(True)  # Fusion: drag a look onto a body or a face
        view.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        return view

    def _add(self, view, look, named=False):
        item = QtWidgets.QListWidgetItem(swatch_icon(look), look["label"] if named else "")
        item.setToolTip(look["label"])
        item.setData(QtCore.Qt.UserRole, look)
        view.addItem(item)
        return item

    def _fill_design(self):
        self.design.clear()
        for look, used in appearance.looks_in_design(self.doc):
            item = self._add(self.design, look)
            where = bodies_gui.body_text(used) if used else "not on anything"
            item.setToolTip("%s (%s)" % (look["label"], where))

    def library_looks(self):
        """The looks the library list shows now: the category's, narrowed by the search."""
        category = self.category.currentData() if hasattr(self, "category") else ALL
        if category == FAVORITES:
            source = appearance.favorite_looks()
        elif category == MINE:
            source = appearance.my_looks()
        elif category == ALL:
            source = appearance.library() + appearance.my_looks()
        else:
            source = appearance_library.in_category(category)
        return appearance_library.search(self.search.text(), source)

    def _fill_library(self):
        looks = self.library_looks()
        self.library.clear()
        for look in looks:
            self._add(self.library, look, named=True)
        text = self.search.text().strip()
        if not looks:
            where = self.category.currentText()
            if text:
                self.found.setText(
                    'No look called "%s" in %s. Try fewer letters, or All.' % (text, where)
                )
            elif where == FAVORITES:
                self.found.setText("No favourites yet: right-click a look > Add to Favorites.")
            elif where == MINE:
                self.found.setText("None yet: right-click a look of the design > Add to Favorites.")
            else:
                self.found.setText("")
        else:
            self.found.setText("%d looks" % len(looks) if text else "")

    def items(self, view=None):
        view = view or self.library
        return [view.item(i) for i in range(view.count())]

    def item_for(self, label):
        """The library swatch with this name, among the ones listed now (tests)."""
        for item in self.items():
            if item.data(QtCore.Qt.UserRole)["label"] == label:
                return item
        return None

    # -- picking a look --------------------------------------------------------------------------
    def _swatch_clicked(self, item):
        look = item.data(QtCore.Qt.UserRole)
        if look:
            self._choose(dict(look))

    def _choose(self, look):
        self.look = look
        if self.remove.isChecked():
            self.remove.setChecked(False)
        self.chosen.setText(look["label"])
        self.info.setText("Click bodies (or faces) to give them this look.")
        if self.pending:
            pending, self.pending = self.pending, []
            whole = self.picks_bodies()
            given = []
            for obj, short in pending:
                if whole:  # Apply To Bodies: each body once, however many of its faces came
                    body = bodies.body_of(obj)
                    if any(body is b for b in given):
                        continue
                    given.append(body)
                self._give(obj, short)

    def _remove_toggled(self, on):
        self.removing = bool(on)
        if on:
            self.look = None
            self.chosen.setText("(remove)")
            self.info.setText(
                "Click a face to take its own look away."
                if self.apply_to.currentData() == "faces"
                else "Click a body to take its Appearance away (its material's look shows)."
            )
        elif self.look is None:
            self.chosen.setText("")
            self.info.setText("Pick a look, then click bodies (or faces).")

    def _rgb(self):
        return [s.value() / 255.0 for s in self.sliders]

    def _paint_custom(self):
        r, g, b = [int(round(c * 255)) for c in self._rgb()]
        pixmap = QtGui.QPixmap(SWATCH, SWATCH)
        pixmap.fill(QtGui.QColor(r, g, b))
        self.preview_swatch.setPixmap(pixmap)

    def _slid(self):
        r, g, b = [int(round(c * 255)) for c in self._rgb()]
        self.hex.blockSignals(True)
        self.hex.setText("#%02X%02X%02X" % (r, g, b))
        self.hex.blockSignals(False)
        self._paint_custom()

    def _hex_typed(self):
        text = self.hex.text().strip().lstrip("#")
        try:
            if len(text) != 6:
                raise ValueError
            values = [int(text[i : i + 2], 16) for i in (0, 2, 4)]
        except ValueError:
            self.message.setText("⚠ Type a colour as #RRGGBB (for example #3366CC).")
            return
        self.message.setText("")
        self._quiet = True
        try:
            for slider, value in zip(self.sliders, values):
                slider.setValue(value)
        finally:
            self._quiet = False
        self._paint_custom()

    def _custom_picked(self):
        self._choose(appearance.custom(self._rgb()))

    def _apply_to_changed(self):
        if self.removing:
            self._remove_toggled(True)

    # -- clicks ------------------------------------------------------------------------------------
    def picked(self, obj, short, point):
        if self.removing:
            self.message.setText("")
            self._take_away(obj, short)
            return
        if self.look is None:
            self.pending.append((obj, short))
            self.message.setText("Pick a look first (click one), then click.")
            return
        self.message.setText("")
        self._give(obj, short)

    def _pointer(self):
        """Where the pointer is on the 3D view (widget pixels), or None."""
        widget = self._drop_widget or _gl_widget()
        if widget is None:
            return None
        return widget.mapFromGlobal(QtGui.QCursor.pos())

    def _hit(self, widget, x, y):
        """(object, short element name) drawn at a pixel of the 3D view, or None."""
        ratio = widget.devicePixelRatioF()
        info = self.view.getObjectInfo((x * ratio, (widget.height() - y) * ratio))
        if not info or not info.get("Object"):
            return None
        obj = self.doc.getObject(info["Object"])
        if obj is None:
            return None
        from . import hole_common

        return hole_common.resolve(obj, info.get("Component", "") or "")

    def face_near(self, position, body=None):
        """(object, "FaceN") of the face at the pointer, or next to it within a few pixels
        (the pointer is on an edge or a corner): Apply To Faces takes that face, as Fusion,
        where only faces can be hit, does. None when there is no face of `body` there."""
        widget = self._drop_widget or _gl_widget()
        if widget is None or position is None:
            return None
        for dx, dy in _NEAR:
            hit = self._hit(widget, position.x() + dx, position.y() + dy)
            if hit is None or not hit[1].startswith("Face"):
                continue
            if body is not None and bodies.body_of(hit[0]) is not body:
                continue
            return hit
        return None

    def _face_of(self, obj, short, position):
        """The face a click or drop in Faces mode means: the face itself, or the face next
        to the edge or corner it landed on. (object, name) or None (said in the dialog)."""
        if short.startswith("Face"):
            return obj, short
        found = self.face_near(
            position if position is not None else self._pointer(), bodies.body_of(obj)
        )
        if found is None:
            self.message.setText(
                "⚠ That landed on an edge, not on a face, and no look was changed. Drop (or "
                "click) inside the face; zoom in when the face is small."
            )
        return found

    def _tip_face(self, body, obj, short):
        """The face as the body's end step names it (a face of an earlier step is found on
        the body as it is now), or (None, None)."""
        feature = obj if not bodies.is_body(obj) else body.Tip
        if feature is not body.Tip:
            from . import profile_pick

            face = profile_pick.global_face(obj, short)
            name = profile_pick.face_name_in(body.Tip, face) if face is not None else None
            if not name:
                self.message.setText(
                    "⚠ That face is no longer on the body as it is now: click the body itself."
                )
                return None, None
            feature, short = body.Tip, name
        return feature, short

    def _give(self, obj, short, position=None):
        body = bodies.body_of(obj)
        if body is None or self.look is None:
            return False
        look = appearance.adopt(self.doc, self.look)
        if self.apply_to.currentData() == "faces":
            found = self._face_of(obj, short, position)
            if found is None:
                return False
            feature, name = self._tip_face(body, *found)
            if feature is None:
                return False
            appearance.set_faces(body, feature, [name], look)
            what = "a face of %s" % body.Label
        else:
            keep = False
            count = appearance.face_count(body)
            if count:
                answer = self._ask_faces(body, count)
                if answer is None:
                    self.note.setText("%s: nothing changed" % body.Label)
                    return False
                keep = answer == "keep"
            appearance.set_body(body, look, keep_faces=keep)
            what = body.Label
        # (force: a look dropped on something that has it already is put on again)
        appearance.apply(body, force=True)
        self.look = look
        self._fill_design()
        self.note.setText("%s: %s" % (what, look["label"]))
        return True

    def _take_away(self, obj, short):
        body = bodies.body_of(obj)
        if body is None:
            return
        if self.apply_to.currentData() == "faces":
            found = self._face_of(obj, short, None)
            if found is None:
                return
            feature, name = self._tip_face(body, *found)
            if feature is None:
                return
            gone = appearance.remove_faces(body, feature, [name])
            text = "its own look taken away" if gone else "that face has no look of its own"
            self.note.setText("a face of %s: %s" % (body.Label, text))
        else:
            data = appearance.get(body)
            if data.get("body"):
                appearance.set_body(body, None, keep_faces=True)
                self.note.setText("%s: Appearance taken away" % body.Label)
            else:
                self.note.setText("%s has no Appearance of its own" % body.Label)
        appearance.apply(body, force=True)
        bodies_gui.sync(self.doc)
        self._fill_design()

    def _ask_faces(self, body, count):
        """Fusion's question when a look goes on a body whose faces have looks of their own:
        "keep", "remove" or None (Cancel)."""
        box = QtWidgets.QMessageBox(Gui.getMainWindow())
        box.setObjectName("Fission180KeepFaceLooks")
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setWindowTitle("Appearance")
        box.setText(
            "%s has %d face%s with a look of %s own."
            % (body.Label, count, "" if count == 1 else "s", "its" if count == 1 else "their")
        )
        box.setInformativeText(
            "Keep: those faces keep their looks over the new one.\n"
            "Remove: the whole body gets the new look."
        )
        keep = box.addButton("Keep", QtWidgets.QMessageBox.AcceptRole)
        remove = box.addButton("Remove", QtWidgets.QMessageBox.DestructiveRole)
        box.addButton(QtWidgets.QMessageBox.Cancel)
        box.setDefaultButton(keep)
        box.exec()
        clicked = box.clickedButton()
        try:
            from . import preferences_ui

            QtCore.QTimer.singleShot(0, preferences_ui.refocus_main)
        except Exception:
            pass
        if clicked is keep:
            return "keep"
        if clicked is remove:
            return "remove"
        return None

    def can_finish(self):
        return ""

    # -- the looks of the design: edit, duplicate, rename, delete ----------------------------------
    def _look_at(self, view, pos):
        item = view.itemAt(pos)
        return dict(item.data(QtCore.Qt.UserRole)) if item is not None else None

    def _design_menu(self, pos):
        look = self._look_at(self.design, pos)
        if look is None:
            return
        menu = QtWidgets.QMenu(self.design)
        menu.setObjectName("Fission180LookMenu")
        menu.addAction("Edit", lambda: self._guarded(lambda: self.edit_look(look)))
        menu.addAction("Duplicate", lambda: self._guarded(lambda: self.duplicate_look(look)))
        menu.addAction("Rename", lambda: self._guarded(lambda: self.edit_look(look, True)))
        menu.addAction("Delete", lambda: self._guarded(lambda: self.delete_look(look)))
        menu.addSeparator()
        menu.addAction(
            "Select Objects Applied To", lambda: self._guarded(lambda: self.select_users(look))
        )
        menu.addAction("Add to Favorites", lambda: self._guarded(lambda: self.favorite(look)))
        menu.exec(self.design.viewport().mapToGlobal(pos))

    def _library_menu(self, pos):
        look = self._look_at(self.library, pos)
        if look is None:
            return
        menu = QtWidgets.QMenu(self.library)
        menu.setObjectName("Fission180LookMenu")
        if look["key"] in appearance.favorites():
            menu.addAction(
                "Remove from Favorites", lambda: self._guarded(lambda: self.unfavorite(look))
            )
        else:
            menu.addAction("Add to Favorites", lambda: self._guarded(lambda: self.favorite(look)))
        menu.exec(self.library.viewport().mapToGlobal(pos))

    def favorite(self, look):
        appearance.add_favorite(look)
        self._fill_library()
        self.note.setText("%s: added to Favorites" % look["label"])

    def unfavorite(self, look):
        appearance.set_favorite(look["key"], False)
        self._fill_library()
        self.note.setText("%s: removed from Favorites" % look["label"])

    def edit_look(self, look, rename=False):
        """Open the look editor on a look of the design (double-click, Edit, Rename)."""
        if not look:
            return None
        from . import appearance_edit_ui

        if self.editor is not None:
            self.editor.finish(True)
        self.editor = appearance_edit_ui.LookEditor(self, look, rename)
        self.editor.show()
        self.editor.raise_()
        self.editor.activateWindow()
        return self.editor

    def look_changed(self, key, new):
        """The editor changed a look: every body and face that has it follows at once."""
        appearance.replace_look(self.doc, key, new)
        if self.look is not None and self.look.get("key") == key:
            self.look = dict(new)
            self.chosen.setText(new["label"])
        appearance.sync(self.doc)
        self._fill_design()

    def editor_closed(self, editor):
        if self.editor is editor:
            self.editor = None

    def duplicate_look(self, look):
        made = appearance.duplicate(self.doc, look["key"])
        if made is None:
            return None
        self._fill_design()
        self.note.setText("%s made: it is in In This Design" % made["label"])
        return made

    def delete_look(self, look):
        try:
            changed = appearance.delete_look(self.doc, look["key"])
        except appearance.LookInUse as exc:
            self.message.setText("⚠ %s" % exc)
            return False
        self.message.setText("")
        if self.look is not None and self.look.get("key") == look["key"]:
            self.look = None
            self.chosen.setText("")
        bodies_gui.sync(self.doc)
        self._fill_design()
        text = "%s deleted" % look["label"]
        if changed:
            text += " (taken off %s)" % ", ".join(b.Label for b in changed)
        self.note.setText(text)
        return True

    def select_users(self, look):
        """Select Objects Applied To: the bodies that show the look are selected (and lit
        up) in the 3D view and the browser. Not taken as picks."""
        found = appearance.users(self.doc, look["key"])
        self._syncing = True
        try:
            Gui.Selection.clearSelection()
            for body, _faces, _whole in found:
                Gui.Selection.addSelection(body)
        finally:
            QtCore.QTimer.singleShot(60, self._selection_shown)
        if found:
            self.note.setText(
                "%s is on %s" % (look["label"], ", ".join(b.Label for b, _f, _w in found))
            )
        else:
            self.note.setText("%s is not on anything" % look["label"])

    def _selection_shown(self):
        self._syncing = False

    # -- drag and drop -------------------------------------------------------------------------
    def _install_drop(self):
        """The 3D view takes a swatch dropped on it (Fusion drags looks onto the part)."""
        try:
            widget = _gl_widget()
            if widget is None:
                return
            self._drop_widget = widget
            self._drop_filter = _DropTaker(self)
            self._drop_accepted = widget.acceptDrops()
            widget.setAcceptDrops(True)
            widget.installEventFilter(self._drop_filter)
        except Exception as exc:
            warn("appearance drag and drop unavailable: %s" % exc)

    def remove_handles(self):
        if self.editor is not None:
            try:
                self.editor.finish(True)
            except Exception:
                pass
            self.editor = None
        widget = getattr(self, "_drop_widget", None)
        if widget is not None:
            try:
                widget.removeEventFilter(self._drop_filter)
                widget.setAcceptDrops(self._drop_accepted)
            except Exception:
                pass
            self._drop_widget = None

    def dropped(self, look, position):
        """A swatch dropped at widget pixel `position`: the body or face there takes it."""
        widget = self._drop_widget
        if widget is None:
            return False
        hit = self._hit(widget, position.x(), position.y())
        if hit is None and self.apply_to.currentData() == "faces":
            hit = self.face_near(position)
        if hit is None:
            self.message.setText("⚠ Drop the look on a body or a face: nothing was there.")
            return False
        self.message.setText("")
        self._choose(look)
        return self._give(hit[0], hit[1], position)

    def after_close(self, ok):
        super().after_close(ok)
        try:
            appearance.sync(self.doc)
        except Exception as exc:
            warn("appearance: %s" % exc)


class AppearanceCommand:
    def GetResources(self):
        return {
            "MenuText": "Appearance",
            "ToolTip": "Give bodies or faces a look: metals, plastics, woods, paints, glass, "
            "leather, carbon fibre or any colour",
            "Pixmap": ui_icon_path("appearance"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            _start(AppearancePanel)
        except Exception as exc:
            warn("Appearance could not start: %s" % exc)


COMMANDS = {"Fission180_Appearance": AppearanceCommand}


# -- the looks stay on screen ---------------------------------------------------------------------
class _Watch:
    """FreeCAD rewrites the colours it draws a body's steps in on its own (whenever the
    body's material is written, or even only read through Python, every step goes back to
    the material's grey), and other code may too. Whenever the colours of anything were
    written by something else than appearance.apply(), the bodies that have a stored look are
    looked at a moment later and put right; a step that comes into view gets its pattern.
    Every slot only schedules work (nothing is done inside FreeCAD's callbacks)."""

    def __init__(self):
        self.pending = {}  # document name -> names of the bodies to look at
        self.all_pending = False

    def colours_written(self):
        if self.all_pending or appearance.writing():
            return
        self.all_pending = True
        QtCore.QTimer.singleShot(0, self._run_all)

    def later(self, body):
        doc_name = body.Document.Name
        names = self.pending.setdefault(doc_name, set())
        first = not names
        names.add(body.Name)
        if first:
            QtCore.QTimer.singleShot(0, lambda: self._run(doc_name))

    def _run_all(self):
        self.all_pending = False
        try:
            for doc_name, names in list(appearance.managed_names().items()):
                self._apply(doc_name, names)
        except Exception as exc:
            warn("appearance: %s" % exc)

    def _run(self, doc_name):
        names = self.pending.pop(doc_name, set())
        try:
            self._apply(doc_name, names)
        except Exception as exc:
            warn("appearance: %s" % exc)

    def _apply(self, doc_name, names):
        if doc_name not in App.listDocuments():
            return
        doc = App.getDocument(doc_name)
        if getattr(doc, "Recomputing", False) or getattr(doc, "Restoring", False):
            return  # (bodies_gui's sync follows the recompute; _opened the restore)
        for name in list(names):
            body = doc.getObject(name)
            if body is not None and bodies.alive(body):
                appearance.apply(body)


class _ViewWatch:
    """Gui.addDocumentObserver: a view's colours were written. The view object itself is
    never touched here: FreeCAD tells of changes to a view that has no object yet (one being
    made), and reading its Object then crashes FreeCAD 1.1."""

    def slotChangedObject(self, vobj, prop):
        if prop == "ShapeAppearance":
            _WATCH["work"].colours_written()


class _DesignWatch:
    """App.addDocumentObserver: a body's material was written (FreeCAD then rewrites its
    steps' colours), a step came into view; a design opened (its looks are put on once it
    has loaded) or closed."""

    def slotChangedObject(self, obj, prop):
        try:
            if prop not in ("ShapeMaterial", "Visibility"):
                return
            body = bodies.body_of(obj)
            if body is None or (obj is body and prop == "Visibility"):
                return
            if _has_look(body):
                _WATCH["work"].later(body)
        except Exception:
            pass

    def slotCreatedDocument(self, doc):
        try:
            name = doc.Name
            QtCore.QTimer.singleShot(0, lambda: _opened(name))
        except Exception:
            pass

    def slotDeletedDocument(self, doc):
        try:
            appearance.forget(doc.Name)
            _WATCH["work"].pending.pop(doc.Name, None)
        except Exception:
            pass


def _has_look(body):
    try:
        if appearance.managed(body):
            return True
        return bool(getattr(body, appearance.PROP, "")) or (
            appearance.edited_default(body.Document) is not None
        )
    except Exception:
        return False


def _opened(name, tries=0):
    """A design just opened: its looks (and their patterns, which are not in the file) are
    put on once it has loaded."""
    try:
        if name not in App.listDocuments():
            return
        doc = App.getDocument(name)
        if getattr(doc, "Restoring", False) or getattr(doc, "Recomputing", False):
            if tries < 100:
                QtCore.QTimer.singleShot(100, lambda: _opened(name, tries + 1))
            return
        if any(getattr(b, appearance.PROP, "") for b in bodies.list_bodies(doc)) or (
            appearance.edited_default(doc) is not None
        ):
            gdoc = Gui.getDocument(name)
            was = bool(gdoc.Modified) if gdoc is not None else False
            appearance.sync(doc)
            if gdoc is not None and not was:
                gdoc.Modified = False  # the design is as it was saved
    except Exception as exc:
        warn("appearance: %s" % exc)


_WATCH = {"work": None, "view": None, "design": None}


def install_watch():
    if _WATCH["work"] is None and App.GuiUp:
        _WATCH["work"] = _Watch()
        _WATCH["view"] = _ViewWatch()
        Gui.addDocumentObserver(_WATCH["view"])
        _WATCH["design"] = _DesignWatch()
        App.addDocumentObserver(_WATCH["design"])


try:
    install_watch()
except Exception as _exc:  # pragma: no cover - only without a GUI
    warn("appearance watch not installed: %s" % _exc)
