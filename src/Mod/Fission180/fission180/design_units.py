# SPDX-License-Identifier: LGPL-2.1-or-later
"""The design's units stay the design's (Document Settings > Units), and helpers that say
what they are.

Bug 2 of the book parity report (Fire Piston): "Set the design to Inch, then press Ctrl+Z on
any step: Document Settings shows mm again and every dialog takes mm. Ctrl+Y doesn't bring
inches back. It also happened without any Undo, after a Change Parameters edit and after some
Chamfer OKs."

The cause is in FreeCAD 1.1's window code, not in Undo. Whenever a property of any object
changes the way it is shown in the property editor (FreeCAD does that all the time while it
computes), Gui::Document::slotChangePropertyEditor calls
MainWindow::setUserSchema(that document's units), and setUserSchema writes them into the
*active* document. So a second document with other units overwrites the active design's
units: the hidden throw-away documents Fission 180 computes in (a fillet or chamfer with a
size per edge, a draft, an import, an export) are made with the default units (mm) while the
design stays the active document. Every rebuild of a Chamfer step (its OK, an Undo that
rebuilds, a Change Parameters edit) therefore set an inch design back to mm, and so did
another design open in a second tab. Reproduced with a hidden document and one property
write (scenario book_params_units).

The fix (Python only, no change to FreeCAD): Fission 180 keeps its own record of each
design's units, taken when the design is made or opened and changed only when the person
(or a script) sets them. A change of a design's `UnitSystem` that nobody asked for is put
back at once, and FreeCAD's application-wide unit schema (what its value boxes show) is set
to the active design's again a moment later.

Other builders: `design_is_inch(doc)` (Thread's default standard, ANSI in an inch design),
`length_unit(doc)`, `length_text(mm, doc)` and `hint(doc)` ("Type a value (in)").
"""

import FreeCAD as App

_units = {}  # document name -> the unit schema (index) the design was made with or given
_state = {"installed": False, "observer": None, "put_back": 0, "resync": False}


def schema_of(doc):
    """The index of the design's unit schema (0 = mm, 3 = inch...), or None."""
    try:
        return list(doc.getEnumerationsOfProperty("UnitSystem")).index(doc.UnitSystem)
    except Exception:
        return None


def length_unit(doc=None):
    """The design's length unit: "mm", "cm", "m", "in" or "ft"."""
    from . import browser_core

    doc = doc or App.ActiveDocument
    return browser_core.doc_length_unit(doc) if doc is not None else "mm"


def design_is_inch(doc=None):
    """True for a design in inches or feet (Fusion then offers ANSI threads first, inch
    drill sizes, inch grid steps)."""
    return length_unit(doc) in ("in", "ft")


is_inch = design_is_inch


def length_text(mm, doc=None, digits=None):
    """A length in the design's units: "25.4 mm", "1 in"."""
    from . import browser_core

    return browser_core.length_text(mm, doc or App.ActiveDocument, digits)


def hint(doc=None, kind="length"):
    """What a value box's tooltip says: the unit a plain number is read in."""
    if kind == "angle":
        return "Type a value (deg), a parameter or a formula"
    if kind == "number":
        return "Type a number, a parameter or a formula"
    return "Type a value (%s), a parameter or a formula" % length_unit(doc)


def set_units(doc, schema, as_default=False):
    """Give a design its units (the one way Fission 180 changes them)."""
    names = doc.getEnumerationsOfProperty("UnitSystem")
    _units[doc.Name] = int(schema)
    doc.UnitSystem = names[schema]
    App.Units.setSchema(schema)
    if as_default:
        App.ParamGet("User parameter:BaseApp/Preferences/Units").SetInt("UserSchema", schema)
    _grid_follows()


def _grid_follows():
    """The grids are in round numbers of the design's units: redrawn when they change."""
    if not App.GuiUp:
        return
    try:
        from . import grid_ui

        sketch = grid_ui.editing_sketch()
        if sketch is not None:
            grid_ui.apply_to_sketch(sketch)
        grid_ui.redraw_all()
    except Exception:
        pass


def remembered(doc):
    """The units Fission 180 holds this design to (a schema index), or None."""
    try:
        return _units.get(doc.Name)
    except Exception:
        return None


def put_back_count():
    """How often a design's units were put back since start (tests, the session log)."""
    return _state["put_back"]


def _asked_for(frame):
    """True when the Python statement that is running sets a document's UnitSystem itself
    (`doc.UnitSystem = ...`, setattr): the person's or a script's own choice, not FreeCAD
    carrying another document's units over."""
    import dis

    while frame is not None:
        try:
            code = frame.f_code
            if "UnitSystem" in code.co_names or "UnitSystem" in code.co_consts:
                at = frame.f_lasti
                last = None
                for ins in dis.get_instructions(code):
                    if ins.offset > at:
                        break
                    last = ins
                if last is not None:
                    if last.opname == "STORE_ATTR" and last.argval == "UnitSystem":
                        return True
                    if "CALL" in last.opname and "setattr" in code.co_names:
                        return True
        except Exception:
            return False
        # a statement inside this module's own observer is never the asker; one level up is
        # the statement that made FreeCAD send the change
        if frame.f_code.co_filename != __file__:
            return False
        frame = frame.f_back
    return False


class _Watch:
    def slotCreatedDocument(self, doc):
        _record(doc)

    def slotFinishRestoreDocument(self, doc):
        _record(doc)

    def slotDeletedDocument(self, doc):
        try:
            _units.pop(doc.Name, None)
        except Exception:
            pass

    def slotChangedDocument(self, doc, prop):
        if prop != "UnitSystem":
            return
        try:
            import sys

            _changed(doc, sys._getframe(1))
        except Exception as exc:
            from . import warn

            warn("units: %s" % exc)


def _record(doc):
    try:
        schema = schema_of(doc)
        if schema is not None:
            _units[doc.Name] = schema
    except Exception:
        pass


def _changed(doc, frame):
    now = schema_of(doc)
    held = _units.get(doc.Name)
    if now is None:
        return
    if held is None or now == held or getattr(doc, "Restoring", False) or _asked_for(frame):
        _units[doc.Name] = now
        return
    # nobody asked: FreeCAD wrote another document's units into this one
    from . import log

    names = doc.getEnumerationsOfProperty("UnitSystem")
    _state["put_back"] += 1
    log(
        "units: %s stays in %s (FreeCAD carried another document's units over)"
        % (doc.Label, names[held].split(" (")[0])
    )
    doc.UnitSystem = names[held]
    _resync_later()


def _resync_later():
    """FreeCAD's application-wide schema (what value boxes show) follows the active design
    again, once FreeCAD is done with what it was doing."""
    if _state["resync"]:
        return
    _state["resync"] = True
    try:
        from .compat import QtCore

        QtCore.QTimer.singleShot(0, resync)
    except Exception:
        resync()


def resync():
    _state["resync"] = False
    try:
        doc = App.ActiveDocument
        schema = schema_of(doc) if doc is not None else None
        if schema is not None and App.Units.getSchema() != schema:
            App.Units.setSchema(schema)
    except Exception as exc:
        from . import warn

        warn("units: the application's units were not put back: %s" % exc)


def install():
    """Start holding every design to its units (once; the GUI only: FreeCAD carries units
    over in its window code)."""
    if _state["installed"]:
        return
    _state["installed"] = True
    for doc in App.listDocuments().values():
        _record(doc)
    _state["observer"] = _Watch()
    App.addDocumentObserver(_state["observer"])
