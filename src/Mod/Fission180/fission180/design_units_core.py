# SPDX-License-Identifier: LGPL-2.1-or-later
"""What follows from a design's units, without FreeCAD (unit tested): the grid and the
drag steps of an inch design are round numbers of inches.

The book parity report (Fire Piston): "In an inch design the sketch grid / snap is still
metric (points jumped to 10 mm / 100 mm steps)." The grid's settings are kept in millimetres
(Grid Settings, Set Increments); while a setting is still Fusion's default, a design in
inches or feet gets the default of its own units instead (1 in for 10 mm, 0.1 in for 1 mm).
"""

MM_PER_UNIT = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}
GRID_DEFAULT_MM = 10.0  # Major Grid Spacing as Fission 180 starts with it
INCREMENT_DEFAULT_MM = 1.0  # Linear Increment as Fission 180 starts with it
# the same defaults in a design that is not metric
GRID_DEFAULTS = {"in": 25.4, "ft": 304.8}  # 1 in, 1 ft
INCREMENT_DEFAULTS = {"in": 2.54, "ft": 3.048}  # 0.1 in, 0.01 ft


def per_unit(unit):
    """Millimetres in one of the design's length unit."""
    return MM_PER_UNIT.get(unit, 1.0)


def grid_spacing(setting_mm, unit):
    """The major grid spacing (mm) for a design in `unit`: the setting, or the design's own
    default while the setting is the default."""
    if abs(float(setting_mm) - GRID_DEFAULT_MM) < 1e-9:
        return GRID_DEFAULTS.get(unit, GRID_DEFAULT_MM)
    return float(setting_mm)


def increment(setting_mm, unit):
    """The linear drag step (mm) for a design in `unit` (see grid_spacing)."""
    if abs(float(setting_mm) - INCREMENT_DEFAULT_MM) < 1e-9:
        return INCREMENT_DEFAULTS.get(unit, INCREMENT_DEFAULT_MM)
    return float(setting_mm)


def adaptive_step(view_height_mm, unit, grid_step):
    """The adaptive grid's major spacing (mm) as a round number of the design's units
    (1, 2, 5 x 10^n inches in an inch design). `grid_step(height)` gives the round number
    for a height (nav_core.grid_step)."""
    per = per_unit(unit)
    return grid_step(float(view_height_mm) / per) * per


# -- whose units a running statement sets (design_units._asked_for) -----------------------------
_BASE_LOADS = ("LOAD_FAST", "LOAD_FAST_CHECK", "LOAD_NAME", "LOAD_GLOBAL", "LOAD_DEREF")
_UNKNOWN = object()


def store_target(frame, attribute="UnitSystem"):
    """(True, obj) when the statement running in Python frame `frame` is `obj.<attribute> =
    ...` and obj can be read back from the frame (a name, or a chain of attributes on one:
    `doc`, `self.doc`); (False, None) when it is no such statement or obj cannot be told.

    FreeCAD's window code writes the units of the document whose property changed into the
    ACTIVE design (design_units): a statement that sets ANOTHER document's units (a throw-away
    document's, a design in another tab) then changes the active design's too, with that very
    statement running. Telling which document the statement sets keeps the guard from taking
    that carried-over change for the person's or a script's own choice (fix-2)."""
    import builtins
    import dis

    if frame is None:
        return False, None
    try:
        code = frame.f_code
        if attribute not in code.co_names:
            return False, None
        seen = []
        for ins in dis.get_instructions(code):
            if ins.offset > frame.f_lasti:
                break
            seen.append(ins)
        if not seen or seen[-1].opname != "STORE_ATTR" or seen[-1].argval != attribute:
            return False, None
        chain = []
        for ins in reversed(seen[:-1]):
            if ins.opname == "LOAD_ATTR":
                chain.append(ins.argval)
                continue
            if ins.opname == "LOAD_FAST_LOAD_FAST":  # (Python 3.13: two loads in one)
                name = ins.argval[1]
            elif ins.opname in _BASE_LOADS:
                name = ins.argval
            else:
                return False, None
            break
        else:
            return False, None
        found = _UNKNOWN
        for space in (frame.f_locals, frame.f_globals, vars(builtins)):
            if name in space:
                found = space[name]
                break
        if found is _UNKNOWN:
            return False, None
        for attr in reversed(chain):
            found = getattr(found, attr)
        return True, found
    except Exception:
        return False, None
