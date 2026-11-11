# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Hardware...: put a standard part into the design (a screw, a set screw, a
shoulder screw, a nut, a washer, an O-ring, a ball bearing, a retaining ring, a pin, a key, a
standoff, a heat-set insert, a magnet), metric or inch, and make the hole it needs, in one
step (hardware.py does the work). It stands in for Fusion's Insert McMaster-Carr Component and
Insert Fastener with Fission 180's own offline parts.

1. Pick what: type words and a size into Search ("set screw m3", "6202", "o-ring 012",
   "1/4-20 pan") and click a result, or use Units, Type, Standard, Size and Length. Thread
   offers a size's fine pitch, Modeled threads cuts the real thread (off: a plain
   cylinder, like Fusion's cosmetic threads).
2. Place on: click a hole (its rim, its wall, its countersink or chamfer), a round edge, a
   shaft or a flat face. On a hole the part goes on its axis and takes the hole's size by
   itself (Fusion's Size Automatic), a countersunk head seats in the countersink, a head in
   its counterbore; every other hole like it on that face is filled too (All holes like it:
   Fusion's Select Similar), each further hole clicked gets one more (a hole clicked again
   is emptied). A flat face: the part goes where it was clicked. Nothing clicked: OK puts
   the part at the origin and opens Move (as Fusion's Insert McMaster-Carr Component does).
3. "Make the hole too" (on for a flat face, off by itself on a hole that is there) drills
   the matching hole as a normal Hole step. Flip turns the part round, Offset slides it
   along its axis, "Rigid joint" holds it to the component it was put on.

OK keeps everything as one undo step, Cancel or Esc removes it, Enter is OK. Problems are
said in the dialog, which then stays open. Double-click the Hardware step in the timeline
to change it later (its holes follow).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, components, hardware, hardware_place, hole, log, preview
from . import hardware_core as core
from . import hole_common as common
from . import ui_icon_path, warn
from .compat import QtCore, QtWidgets
from .taskui import DistanceField, Panel


def _pairs(rows):
    """(label, value) pairs for a drop-down from hardware_core's (value, label) rows."""
    return [(label, value) for value, label in rows]


WAITING = hardware_place.WAITING
AT_ORIGIN = "Nothing clicked yet: OK puts it at the origin and opens Move."
NOT_KEPT = ("flip", "make_hole", "sink_head", "seat", "offset")  # start fresh on every insert


def _safe(method):
    """Never let an exception out of a Qt signal handler."""

    def wrapper(self, *args):
        try:
            return method(self, *args)
        except Exception as exc:
            warn("Hardware: %s" % exc)
            try:
                self.message.setText("⚠ %s" % exc)
            except Exception:
                pass
        return None

    wrapper.__name__ = method.__name__
    return wrapper


class _SearchKeys(QtCore.QObject):
    """Enter in the Search box takes the first result (FreeCAD would press OK), Down goes
    into the list."""

    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    self.panel._search_enter()
                    return True
                if key == QtCore.Qt.Key_Down and self.panel.results.count():
                    self.panel.results.setFocus()
                    self.panel.results.setCurrentRow(0)
                    return True
        except Exception as exc:
            warn("Hardware search: %s" % exc)
        return False


def design_is_inch(doc):
    try:
        from . import insert

        return insert.design_unit(doc) in ("Inch", "Foot")
    except Exception:
        return False


class HardwarePanel(Panel):
    title = "Hardware"
    icon = "hardware"
    last = None
    remembered = {}  # the next insert of this session starts with the last one's choices

    def __init__(self, doc, feature=None, selection=None):
        super().__init__(doc, "Insert Hardware" if feature is None else "Edit Hardware")
        HardwarePanel.last = self
        self.escape = preview.EscapeCancels(self)
        self.undo_guard = preview.UndoCancels(self)
        self.enter = preview.EnterFinishes(self)
        self.target = feature
        self.editing = feature is not None
        self.picks = []  # (object, sub, point): the first place, then the further ones
        self.place0 = None  # what the first place is (hardware_place.spot)
        self.manual_sink = False
        self.auto_hole_off = False  # "Make the hole too" was unticked by a click on a hole
        self.note = ""
        self.error = ""
        self.found = []
        self._quiet = False
        self.observer = None
        self.gate = None
        if feature is not None:
            try:
                Gui.Selection.clearSelection()
            except Exception:
                pass
            pick, self.options = hardware.read(feature)
            if pick is not None:
                self.picks = [pick] + hardware.more_of(feature)
                try:
                    self.place0 = hardware.spot(*pick)
                except Exception:
                    self.place0 = None
            self.manual_sink = True  # as it was left
        else:
            self.options = core.with_defaults(dict(HardwarePanel.remembered))
            if not HardwarePanel.remembered and design_is_inch(doc):
                self.options = core.change_standard(self.options, "asme_shcs")
        self._build_form()
        self._show_options()
        self._watch()
        if feature is None:
            self._start(selection)
        else:
            self._show_status_text()

    # -- form -----------------------------------------------------------------------------------
    def _build_form(self):
        form = self.layout
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Fission180Hardware_search")
        self.search.setPlaceholderText("set screw m3, 6202, o-ring 012, 1/4-20 pan ...")
        self.search.setToolTip(
            "Words and a size: the kind of part, then M3, 1/4-20, #10, a bearing's number, "
            "an O-ring's dash number; a length as x20 or 3/4\""
        )
        self.search.setClearButtonEnabled(True)
        self._search_keys = _SearchKeys(self)
        self.search.installEventFilter(self._search_keys)
        form.addRow("Search", self.search)
        self.results = QtWidgets.QListWidget()
        self.results.setObjectName("Fission180Hardware_results")
        self.results.setMaximumHeight(130)
        self.results.setVisible(False)
        form.addRow(self.results)
        self.system = QtWidgets.QComboBox()
        self.system.setObjectName("Fission180Hardware_units")
        form.addRow("Units", self.system)
        self.kind = common.combo(_pairs(core.KINDS), self.options["kind"])
        self.kind.setObjectName("Fission180Hardware_type")
        form.addRow("Type", self.kind)
        self.standard = QtWidgets.QComboBox()
        self.standard.setObjectName("Fission180Hardware_standard")
        form.addRow("Standard", self.standard)
        self.size = QtWidgets.QComboBox()
        self.size.setObjectName("Fission180Hardware_size")
        form.addRow("Size", self.size)
        self.thread = QtWidgets.QComboBox()
        self.thread.setObjectName("Fission180Hardware_thread")
        self.thread_label = QtWidgets.QLabel("Thread")
        form.addRow(self.thread_label, self.thread)
        self.length = QtWidgets.QComboBox()
        self.length.setObjectName("Fission180Hardware_length")
        self.length_label = QtWidgets.QLabel("Length")
        form.addRow(self.length_label, self.length)
        self.variant = common.combo(_pairs(core.VARIANTS), self.options["variant"])
        self.variant.setObjectName("Fission180Hardware_variant")
        self.variant_label = QtWidgets.QLabel("Seals")
        form.addRow(self.variant_label, self.variant)
        self.modeled = QtWidgets.QCheckBox("Modeled threads")
        self.modeled.setObjectName("Fission180Hardware_modeled")
        self.modeled.setToolTip(
            "Cut the real thread (slower). Off: a plain cylinder at the thread's size, like "
            "a cosmetic thread"
        )
        form.addRow("", self.modeled)
        self.place = common.SelectionField(self, "place", "Select a hole, an edge or a face")
        self.place.button.setToolTip(WAITING)
        form.addRow("Place on", self.place.widget)
        self.hint = QtWidgets.QLabel(AT_ORIGIN)
        self.hint.setObjectName("Fission180Hardware_hint")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #9aa4b2;")
        form.addRow("", self.hint)
        self.similar = QtWidgets.QCheckBox("All holes like it")
        self.similar.setObjectName("Fission180Hardware_similar")
        self.similar.setToolTip("Fill every hole of the same size that opens on the same face")
        form.addRow("", self.similar)
        self.flip = QtWidgets.QCheckBox("Flip")
        self.flip.setObjectName("Fission180Hardware_flip")
        self.flip.setToolTip("Turn the part round on its axis")
        form.addRow("", self.flip)
        self.offset = DistanceField(self.options["offset"], on_change=self._value_typed)
        self.offset.widget.setObjectName("Fission180Hardware_offset")
        self.offset.widget.setToolTip(
            "Slide the part along its axis: out of the part is plus (an O-ring down into "
            "its groove: minus)"
        )
        form.addRow("Offset", self.offset.widget)
        self.make_hole = QtWidgets.QCheckBox("Make the hole too")
        self.make_hole.setObjectName("Fission180Hardware_make_hole")
        self.make_hole.setToolTip(
            "Drill the hole this part needs as a Hole step in the part you clicked"
        )
        form.addRow("", self.make_hole)
        self.sink = QtWidgets.QCheckBox("Head sunk in")
        self.sink.setObjectName("Fission180Hardware_sink")
        self.sink.setToolTip(
            "The head goes into a counterbore (socket, button, pan and hexagon heads) or a "
            "countersink (countersunk heads)"
        )
        form.addRow("", self.sink)
        self.fit = common.combo(_pairs(core.FITS), self.options["fit"])
        self.fit.setObjectName("Fission180Hardware_fit")
        self.fit_label = QtWidgets.QLabel("Fit")
        form.addRow(self.fit_label, self.fit)
        self.hole_depth = common.combo(_pairs(core.HOLE_DEPTHS), self.options["hole_depth"])
        self.hole_depth.setObjectName("Fission180Hardware_hole_depth")
        self.hole_depth_label = QtWidgets.QLabel("Hole depth")
        form.addRow(self.hole_depth_label, self.hole_depth)
        self.clearance = DistanceField(self.options["clearance"], on_change=self._value_typed)
        self.clearance.widget.setObjectName("Fission180Hardware_clearance")
        self.clearance.widget.setToolTip("How much wider than the magnet its pocket is")
        self.clearance_label = QtWidgets.QLabel("Clearance")
        form.addRow(self.clearance_label, self.clearance.widget)
        self.joint = QtWidgets.QCheckBox("Rigid joint to what it is placed on")
        self.joint.setObjectName("Fission180Hardware_joint")
        self.joint.setToolTip(
            "Hold the part to the component it was put on, so it moves with it (an "
            "as-built rigid joint)"
        )
        form.addRow("", self.joint)
        self.hole_info = QtWidgets.QLabel("")
        self.hole_info.setObjectName("Fission180Hardware_hole_info")
        self.hole_info.setWordWrap(True)
        form.addRow("Hole", self.hole_info)
        self.name = QtWidgets.QLineEdit()
        self.name.setReadOnly(True)
        self.name.setObjectName("Fission180Hardware_name")
        form.addRow("Name", self.name)
        self.finish_layout()
        self.search.textChanged.connect(self._search_typed)
        self.results.itemClicked.connect(self._result_clicked)
        self.results.itemActivated.connect(self._result_clicked)
        self.system.currentIndexChanged.connect(self._system_changed)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self.standard.currentIndexChanged.connect(self._standard_changed)
        self.size.currentIndexChanged.connect(self._size_changed)
        for box in (self.thread, self.length, self.variant, self.fit, self.hole_depth):
            box.currentIndexChanged.connect(self._changed)
        for box in (self.flip, self.make_hole, self.modeled, self.joint):
            box.toggled.connect(self._changed)
        self.sink.toggled.connect(self._sink_toggled)
        self.similar.toggled.connect(self._similar_toggled)

    def _show_options(self):
        """Put self.options into the fields (no signals)."""
        o = self.options
        std = o["standard"]
        self._quiet = True
        try:
            system = core.system_of(std)
            have = core.systems(o["kind"])
            common.fill_combo(self.system, [(lb, s) for s, lb in core.SYSTEMS if s in have], system)
            common.set_combo(self.kind, o["kind"])
            common.fill_combo(self.standard, _pairs(core.standards(o["kind"], system)), std)
            common.fill_combo(
                self.size, [(core.size_label(std, s), s) for s in core.sizes(std)], o["size"]
            )
            threads = core.designations(std, o["size"])
            chosen = core.designation(o)
            common.fill_combo(
                self.thread,
                [(d.label, d.label) for d in threads],
                chosen.label if chosen is not None else None,
            )
            lengths = core.lengths(std, o["size"])
            current = None
            for v in lengths:  # (an inch length: the list's own number for it)
                if abs(v - float(o.get("length") or 0.0)) < 1e-6:
                    current = v
            common.fill_combo(
                self.length, [(core.length_label(std, v), v) for v in lengths], current
            )
            common.set_combo(self.variant, o["variant"])
            self.modeled.setChecked(bool(o["modeled"]))
            self.similar.setChecked(bool(o["similar"]))
            self.flip.setChecked(bool(o["flip"]))
            self.offset.set_value(float(o["offset"]))
            self.make_hole.setChecked(bool(o["make_hole"]))
            self.sink.setChecked(bool(o["sink_head"]))
            common.set_combo(self.fit, o["fit"])
            common.set_combo(self.hole_depth, o["hole_depth"])
            self.clearance.set_value(float(o["clearance"]))
            self.joint.setChecked(bool(o["joint"]))
        finally:
            self._quiet = False
        self._update_visibility()
        self._show_names()

    def _update_visibility(self):
        o = self.options
        kind = o["kind"]
        screw = kind == "screw"
        can_hole = kind in core.HOLE_KINDS
        hole_on = bool(o["make_hole"]) and can_hole
        shown = {
            (self.thread, self.thread_label): self.thread.count() > 1 and kind != "insert",
            (self.length, self.length_label): core.has_length(o["standard"]),
            (self.variant, self.variant_label): kind == "bearing",
            (self.modeled,): hardware.hardware_shapes.can_thread(o),
            (self.make_hole,): can_hole,
            (self.sink,): screw,
            (self.fit, self.fit_label): hole_on and kind in ("screw", "nut", "washer"),
            (self.hole_depth, self.hole_depth_label): hole_on and screw,
            (self.clearance.widget, self.clearance_label): hole_on and kind == "magnet",
            (self.hint,): not self.picks and not self.editing,
        }
        for widgets, visible in shown.items():
            for widget in widgets:
                widget.setVisible(visible)

    def _show_names(self):
        try:
            self.name.setText(core.name(self.options))
        except Exception:
            self.name.setText("")
        self.hole_info.setText(self._hole_text())

    def _hole_text(self):
        try:
            want = core.hole_options(self.options)
        except core.HardwareError as exc:
            return str(exc)
        if want is None:
            return "None"
        if want["tap_type"] == "tapped":
            return "Tapped %s, %g deep" % (core.thread_name(self.options), want["depth"])
        if want["tap_type"] == "clearance":
            text = "Clearance %g mm" % core.clearance(self.options)
            if want["hole_type"] == "counterbore":
                text += ", counterbore %g x %g" % (want["cbore_diameter"], want["cbore_depth"])
            elif want["hole_type"] == "countersink":
                text += ", countersink %g x %g deg" % (want["csink_diameter"], want["csink_angle"])
            if want["extent"] == "all":
                return text + ", through all"
            return text + ", %g deep" % want["depth"]
        return "%g mm, %g deep, flat bottom" % (want["diameter"], want["depth"])

    def _collect(self):
        o = self.options
        o["kind"] = self.kind.currentData()
        o["standard"] = self.standard.currentData() or o["standard"]
        o["size"] = self.size.currentData() or o["size"]
        threads = core.designations(o["standard"], o["size"])
        picked = self.thread.currentData()
        o["thread"] = picked if threads and picked and picked != threads[0].label else ""
        if core.has_length(o["standard"]) and self.length.currentData() is not None:
            o["length"] = float(self.length.currentData())
        o["variant"] = self.variant.currentData()
        o["modeled"] = self.modeled.isChecked()
        o["similar"] = self.similar.isChecked()
        o["flip"] = self.flip.isChecked()
        o["offset"] = float(self.offset.value())
        o["make_hole"] = self.make_hole.isChecked() and o["kind"] in core.HOLE_KINDS
        o["sink_head"] = self.sink.isChecked()
        o["fit"] = self.fit.currentData()
        o["hole_depth"] = self.hole_depth.currentData()
        o["clearance"] = abs(float(self.clearance.value()))
        o["joint"] = self.joint.isChecked()

    # -- search ---------------------------------------------------------------------------------
    @_safe
    def _search_typed(self, text):
        self.found = core.search(text)
        self.results.clear()
        for result in self.found:
            self.results.addItem(result["label"])
        self.results.setVisible(bool(self.found))
        if text.strip() and not self.found:
            self.message.setText(
                "Nothing found for “%s”. Try the kind of part and a size: set screw m3, "
                "bearing 608, o-ring 012." % text.strip()
            )
        elif self.message.text().startswith("Nothing found"):
            self.message.setText("")

    @_safe
    def _result_clicked(self, item):
        row = self.results.row(item)
        if 0 <= row < len(self.found):
            self._take_result(self.found[row])

    def _search_enter(self):
        if self.found:
            row = max(0, self.results.currentRow())
            self._take_result(self.found[row])

    @_safe
    def _take_result(self, result):
        o = core.change_standard(self.options, result["standard"])
        o["size"] = result["size"]
        for key in ("length", "thread", "variant"):
            if key in result:
                o[key] = result[key]
        if "length" not in result and core.has_length(o["standard"]):
            o["length"] = core.fit_length(o["standard"], o["size"], o.get("length"))
        self.options = core.with_defaults(o)
        self.manual_sink = False
        self._reseat()  # (the size asked for stays, whatever hole was clicked)
        self._show_options()
        self._rebuild()

    # -- choices --------------------------------------------------------------------------------
    def _switch(self, standard):
        self.options = core.change_standard(self.options, standard)
        self.manual_sink = False
        self._refit()
        self._show_options()
        self._rebuild()

    @_safe
    def _system_changed(self, *_):
        if self._quiet:
            return
        system = self.system.currentData()
        now = core.std(self.options["standard"])
        found = core.standards(now["kind"], system)
        if not found:
            return
        same = [k for k, _label in found if core.std(k)["noun"] == now["noun"]]
        self._switch(same[0] if same else found[0][0])

    @_safe
    def _kind_changed(self, *_):
        if self._quiet:
            return
        kind = self.kind.currentData()
        system = core.system_of(self.options["standard"])
        found = core.standards(kind, system) or core.standards(kind)
        self._switch(found[0][0])

    @_safe
    def _standard_changed(self, *_):
        if self._quiet:
            return
        self._switch(self.standard.currentData())

    @_safe
    def _size_changed(self, *_):
        if self._quiet:
            return
        o = self.options
        o["size"] = self.size.currentData()
        o["thread"] = ""
        if core.has_length(o["standard"]):
            o["length"] = core.fit_length(o["standard"], o["size"], o.get("length"))
        self._reseat()
        self._show_options()
        self._rebuild()

    @_safe
    def _changed(self, *_):
        if self._quiet:
            return
        self._collect()
        self._reseat()
        self._update_visibility()
        self._rebuild()

    @_safe
    def _sink_toggled(self, *_):
        if self._quiet:
            return
        self.manual_sink = True  # the person decides: the hole no longer sets the seat
        self._collect()
        self.options["seat"] = None
        self._update_visibility()
        self._rebuild()

    @_safe
    def _similar_toggled(self, on):
        if self._quiet:
            return
        self._collect()
        if on and self.picks and self.place0 is not None:
            self._add_similar(self.picks[0][0], self.place0)
        elif not on and len(self.picks) > 1:
            self.picks = self.picks[:1]  # only the one clicked
        self._rebuild()

    @_safe
    def _value_typed(self, _value):
        if self._quiet:
            return
        self._collect()
        self._rebuild()

    # -- placing --------------------------------------------------------------------------------
    def activate(self, name):
        self.place.set_active(True)

    def clear_field(self, name):
        """The x of Place on: the part goes away until a new place is clicked."""
        if self.editing:
            self.message.setText("Click a new place for it (a hole, an edge or a face).")
            return
        if self.target is not None:
            try:
                hardware.remove(self.target)
            except Exception as exc:
                warn("Hardware: %s" % exc)
            self.target = None
            self.schedule()
        self.picks = []
        self.place0 = None
        self.options["seat"] = None
        self.place.set_text("")
        self.message.setText("")
        self._update_visibility()

    def _own_parts(self):
        return hardware.occurrences(self.target) if self.target is not None else []

    def allow(self, obj, name):
        """What lights up and can be clicked: faces and edges of the parts' solids, never the
        hardware itself."""
        if not name.startswith(("Face", "Edge")):
            return False
        body = hole.owner_body(obj) if obj.TypeId != "PartDesign::Body" else obj
        if body is None:
            return False
        try:
            if any(hardware.is_hardware(o) for o in body.Group):
                return False
            if components.container_of(body) in self._own_parts():
                return False
        except Exception:
            return False
        return True

    def _watch(self):
        panel = self

        class Observer:
            def addSelection(self, doc, obj, sub, pnt):
                # Deferred: nothing is built inside FreeCAD's click handling.
                QtCore.QTimer.singleShot(30, panel._selection_changed)

        self.observer = Observer()
        Gui.Selection.addObserver(self.observer)
        self.gate = common.install_gate(self)

    def _unwatch(self):
        if self.observer is not None:
            try:
                Gui.Selection.removeObserver(self.observer)
            except Exception:
                pass
            self.observer = None
        common.remove_gate(self.gate)
        self.gate = None

    def _start(self, selection=None):
        self.activate("place")
        found = list(selection) if selection is not None else []
        try:
            Gui.Selection.clearSelection()
        except Exception:
            pass
        for obj, short, point in found:
            if short.startswith(("Face", "Edge")) and self.allow(obj, short):
                self._clicked(obj, short, point)
                break
        if self.target is not None:
            self._timer.stop()
            self._recompute()

    @_safe
    def _selection_changed(self):
        if self._closed:
            return
        found = common.picks(self.doc)
        if not found:
            return
        Gui.Selection.clearSelection()
        for obj, short, point in found:
            if short.startswith(("Face", "Edge")):
                self._clicked(obj, short, point)
                break

    def _own_holes(self):
        return hardware.holes_of(self.target) if self.target is not None else []

    def _clicked(self, obj, short, point):
        if not self.allow(obj, short):
            return
        own = [h for h in self._own_holes() if h is obj]
        try:
            place = hardware.spot(obj, short, point)
        except core.HardwareError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        self.manual_sink = False
        self.note = ""
        if own:
            # A click on this part's own hole (the preview): the same face of the part
            # before that hole, at the place clicked (its rim: the hole's axis).
            base = own[0].BaseFeature
            body = place["body"]
            if place["face_point"] is None:
                return
            local = hole.to_local(body, place["face_point"])
            rotation = body.getGlobalPlacement().Rotation.inverted()
            name = hole.base_face_at(base, local, rotation.multVec(place["normal"]))
            if name is None:
                return
            self.picks = [(base, name, App.Vector(place["center"]))]
            self.place0 = dict(place, rim=False, is_hole=False, cone=None, cbore_depth=None)
            self.options["seat"] = None
        elif place["rim"]:
            pick = (obj, place["face"] or short, App.Vector(place["center"]))
            same = [p for p in self.picks if self._same_place(p, pick)]
            holes = bool(self.picks) and self.place0 is not None and self.place0["rim"]
            if same and len(self.picks) > 1:
                was_first = self._same_place(self.picks[0], pick)
                self.picks = [p for p in self.picks if p not in same]  # clicked again: emptied
                if was_first:
                    self.place0 = hardware.spot(*self.picks[0])
            elif same:
                pass
            elif holes and place["is_hole"] and self.place0["is_hole"]:
                self.picks.append(pick)  # one more hole
                if self.similar.isChecked():
                    self._add_similar(obj, place)
            else:
                self.picks = [pick]
                self.place0 = place
                self._fit_existing(place)
                if self.similar.isChecked():
                    self._add_similar(obj, place)
        else:
            self.picks = [(obj, short, App.Vector(point) if point is not None else None)]
            self.place0 = place
            self.options["seat"] = None
            if self.auto_hole_off and self.options["kind"] in core.HOLE_KINDS:
                # a flat face has no hole yet: the part's hole is made again
                self.auto_hole_off = False
                self.options["make_hole"] = True
                self.options["sink_head"] = core.default_sink(self.options["standard"])
                self._show_options()
        self._update_visibility()
        self._rebuild()

    @staticmethod
    def _same_place(a, b):
        return (
            a[0] is b[0] and a[2] is not None and b[2] is not None and (a[2] - b[2]).Length < 1e-5
        )

    def _add_similar(self, obj, place):
        """Fusion's Select Similar: the other holes like this one on the same face."""
        try:
            for sub, centre in hardware_place.similar(obj, place):
                pick = (obj, sub, App.Vector(centre))
                if not any(self._same_place(p, pick) for p in self.picks):
                    self.picks.append(pick)
        except Exception as exc:
            warn("Hardware: %s" % exc)

    def _fit_existing(self, place):
        """A hole (or a shaft) that is already there: no second hole, and the part takes its
        size (Fusion's Size: Automatic); a retaining ring turns into the kind that fits (a
        shaft's or a bore's)."""
        o = self.options
        standard = core.standard_for_place(o["standard"], place["is_hole"])
        if standard != o["standard"]:
            o = self.options = core.change_standard(o, standard)
        size = None
        for diameter in (place["hole_diameter"], place["diameter"]):
            if diameter is None or size is not None:
                continue
            size = core.size_for_hole(
                o["standard"], diameter, current=o["size"], is_hole=place["is_hole"]
            )
        self.note = ""
        if size is None and o["kind"] != "key":
            self.note = "No %s size fits this %g mm %s: the size stays %s. Pick the size." % (
                core.std(o["standard"])["noun"].lower(),
                round(place["hole_diameter"] or 0.0, 3),
                "hole" if place["is_hole"] else "shaft",
                core.size_label(o["standard"], o["size"]),
            )
        elif size is not None and size != o["size"]:
            o["size"] = size
            o["thread"] = ""
            if core.has_length(o["standard"]):
                o["length"] = core.fit_length(o["standard"], size, o.get("length"))
        if o["make_hole"]:
            self.auto_hole_off = True
        o["make_hole"] = False
        self._reseat()
        self._show_options()

    def _refit(self):
        """After another kind of part was chosen: it takes the clicked hole's size again."""
        if self.place0 is not None and self.place0["rim"] and not self.editing:
            self._fit_existing(self.place0)

    def _reseat(self):
        """How deep the head sits in the hole that was clicked (its counterbore, its
        countersink), unless the person set Head sunk in by hand or a new hole is made."""
        o = self.options
        place = self.place0
        if place is None or not place["rim"] or o["make_hole"] or self.manual_sink:
            if not self.manual_sink:
                o["seat"] = None
            return
        o["sink_head"], o["seat"] = core.seat_for_hole(
            o,
            {
                "is_hole": place["is_hole"],
                "diameter": place["diameter"],
                "hole_diameter": place["hole_diameter"],
                "cbore_depth": place["cbore_depth"],
                "cone": place["cone"],
                "shoulder": place.get("shoulder", False),
            },
        )

    # -- building -------------------------------------------------------------------------------
    def _rebuild(self):
        """Make or change the part (and its holes) for the options and places now."""
        self._show_names()
        if not self.picks and self.target is None:
            return
        try:
            first = self.picks[0] if self.picks else None
            if self.target is None:
                self.target = hardware.make(self.doc, first, self.options, more=self.picks[1:])
            else:
                hardware.update(self.target, pick=first, options=self.options, more=self.picks[1:])
            self.error = ""
        except core.HardwareError as exc:
            self.error = str(exc)
        except Exception as exc:
            self.error = "The part cannot go there: %s" % exc
        self._show_status_text()
        self.schedule()

    def _place_text(self):
        if not self.picks:
            return ""
        obj, short, _point = self.picks[0]
        owner = hole.owner_body(obj) if obj.TypeId != "PartDesign::Body" else obj
        where = owner.Label if owner is not None else obj.Label
        if len(self.picks) > 1:
            return "%d holes (%s)" % (len(self.picks), where)
        if self.place0 is not None and self.place0["rim"]:
            return "%s (%s)" % ("Hole" if self.place0["is_hole"] else "Round edge", where)
        return "%s (%s)" % (short, where)

    def _show_status_text(self):
        if self.error:
            self.message.setText("⚠ " + self.error)
        elif getattr(self, "note", ""):
            self.message.setText(self.note)
        else:
            self.message.setText("")
        if self.picks:
            self.place.set_text(self._place_text())

    def _recompute(self):
        if self._closed:
            return
        try:
            preview.recompute(self.doc)
            text = self.problem()
            if text:
                self.message.setText("⚠ " + text)
            else:
                self._show_status_text()
        except Exception as exc:
            try:
                self.message.setText(str(exc))
            except RuntimeError:
                pass

    def problem(self):
        if self.error:
            return self.error
        for obj in [self.target] + self._own_holes():
            if obj is None:
                continue
            state = list(getattr(obj, "State", []))
            if "Invalid" in state or "Error" in state:
                return "%s: %s" % (obj.Label, obj.getStatusString())
        for own in self._own_holes():
            if hole.misses(own):
                return "The hole misses the part: click a face of the part."
        return ""

    def feature(self):
        return self.target

    # -- OK / Cancel ----------------------------------------------------------------------------
    def accept(self):
        if self._closed:
            return True
        at_origin = False
        if self.target is None:
            # Nothing clicked: the part comes in at the origin, then Move places it (as
            # Fusion's Insert McMaster-Carr Component ends).
            try:
                self._collect()
                self.target = hardware.make(self.doc, None, self.options)
                at_origin = True
            except Exception as exc:
                self.message.setText("⚠ %s" % exc)
                return False
        self._timer.stop()
        try:
            preview.recompute(self.doc)
        except Exception as exc:
            warn("Hardware: %s" % exc)
        text = self.problem()
        if text:
            self.message.setText("⚠ " + text)
            return False
        try:
            hardware.join(self.target)
        except Exception as exc:
            log("hardware: no joint (%s)" % exc)
        # The next insert starts with this part's choices; what a click decided by itself
        # (no second hole on a rim, the head's seat), Flip and Offset start fresh.
        HardwarePanel.remembered = {k: v for k, v in self.options.items() if k not in NOT_KEPT}
        doc_name = self.doc.Name
        part = hardware.component_of(self.target)
        part_name = part.Name if part is not None else ""
        self.cleanup()
        preview.end_transaction(self.doc)
        self._close()
        log("%s done" % self.title)
        if at_origin and part_name:
            try:
                from . import exchange_ui

                exchange_ui.place_after(doc_name, part_name)
            except Exception as exc:
                warn("Hardware: the move could not start: %s" % exc)
        return True

    def reject(self):
        if self._closed:
            return True
        self._timer.stop()
        body = self.picks[0][0] if self.picks else None
        self.cleanup()
        preview.end_transaction(self.doc, abort=True)
        try:
            preview.recompute(self.doc)
            if body is not None:
                hole.show_tip(hole.owner_body(body))
        except Exception:
            pass
        self._close()
        return True

    def cleanup(self):
        self._unwatch()
        try:
            self.search.removeEventFilter(self._search_keys)
        except Exception:
            pass
        for guard in (self.escape, self.undo_guard, self.enter):
            try:
                guard.remove()
            except Exception:
                pass
        super().cleanup()


class HardwareCommand:
    def GetResources(self):
        return {
            "MenuText": "Hardware...",
            "ToolTip": "Insert a standard part as its own component: screws, set screws, "
            "nuts, washers, O-rings, ball bearings, retaining rings, pins, keys, standoffs, "
            "heat-set inserts and magnets, metric or inch, on a hole, a shaft or a face, "
            "with the hole it needs",
            "Pixmap": ui_icon_path("hardware"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            found = common.picks(App.ActiveDocument)  # a rim or face picked first
            if not commands.finish_open_dialog():
                return
            Gui.Control.showDialog(HardwarePanel(App.ActiveDocument, selection=found))
            log("hardware started")
        except Exception as exc:
            warn("Hardware failed to start: %s" % exc)


def edit(feature):
    """Open the Hardware dialog on an existing part (timeline double-click)."""
    try:
        if Gui.Control.activeDialog() and not commands.finish_open_dialog():
            return
        _keep_part_active(feature)
        Gui.Control.showDialog(HardwarePanel(feature.Document, feature=feature))
    except Exception as exc:
        warn("could not edit %s: %s" % (feature.Label, exc))


def _keep_part_active(feature):
    """The timeline makes the component of a step being edited the active one; for a
    hardware part that would leave its component active afterwards (new sketches would go
    into the screw). The part it was put into stays the active one (Guess)."""
    try:
        from . import bodies

        pick = hardware.pick_of(feature)
        body = bodies.body_of(pick[0]) if pick is not None else None
        if body is not None:
            components.activate_body(body)
    except Exception as exc:
        warn("Hardware: %s" % exc)


COMMANDS = {"Fission180_Hardware": HardwareCommand}
EDITORS = {"Fission180::" + hardware.KIND: edit}
