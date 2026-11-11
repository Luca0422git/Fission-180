# SPDX-License-Identifier: LGPL-2.1-or-later
"""The hardware library (INSERT > Hardware...): the rules of the standard parts. Pure Python
(no FreeCAD, unit tested); hardware_tables.py holds the dimension tables, hardware_shapes.py
builds the solids from these numbers, hardware.py puts them into the design and hardware_ui.py
is the dialog.

It stands in for Fusion's Insert McMaster-Carr Component and Insert Fastener: Fission 180's own
parts, made offline from the public standards, metric and inch. Nothing here comes from a
supplier's catalogue. The families (the standard each table follows is in hardware_tables.py):

  screws        socket head cap, button head, countersunk / flat head, low head, hexagon
                head, pan head (Phillips and slotted): ISO 4762, 7380-1, 10642, DIN 7984, ISO
                4017, 7045, 1580; ASME B18.3, B18.2.1, B18.6.3
  set screws    cup, flat, cone and dog point: ISO 4026 - 4029; ASME B18.3
  shoulder screws   ISO 7379; ASME B18.3
  nuts          hexagon, thin (jam), nylon insert lock: ISO 4032, 4035, 7040; ASME B18.2.2,
                B18.6.3, B18.16.6
  washers       plain and split lock: ISO 7089, DIN 127; ASME B18.21.1 (SAE, USS, lock)
  O-rings       AS568 dash numbers; metric inside diameter x cross section
  ball bearings 60 / 62 / 63 / 68 / 69 series and miniature sizes (ISO 15), inch R series
  retaining rings   DIN 471 (shaft), DIN 472 (bore); ASME B18.27.1 basic external / internal
  dowel pins    ISO 2338; ASME B18.8.2          keys   DIN 6885 A; ASME B17.1
  standoffs and spacers, heat-set inserts, round magnets   commercial sizes (Guess)

Threads: the pitch of a size comes from thread_tables.py (the Thread and Hole tools' rows).
A part's thread is cosmetic (a plain cylinder at the nominal diameter) unless "Modeled
threads" is on; hardware_shapes.py then cuts it with the Thread tool's own code.

The hole each one gets when "Make the hole too" is on (hardware.py makes it a Hole step):

  screws     a clearance hole (ISO 273 / ASME B18.2.8, Fusion's Close / Normal / Loose fit);
             with "Head sunk in": a counterbore for socket, hexagon, button, low and pan heads,
             a countersink for countersunk heads (the head's theoretical diameter: flush)
  set screws a tapped hole of the screw's thread, as deep as the screw is long
  nuts, washers   a clearance hole for the screw that goes through them
  inserts    the insert's hole diameter, 1 mm deeper than the insert (Guess), flat bottom
  magnets    the magnet's diameter + a clearance (0.2 mm by default, Guess), flat bottom
  everything else   no hole (the part goes into a hole, a bore or a groove that is there)

Where a part sits (its own frame: z = 0 is the clicked face, +z points out of the part):
  screws     the head on the face (in the counterbore / countersink when sunk), the shank
             down into the part; set screws, pins, bearings, inserts, magnets in the hole,
             their top flush with the face; nuts, washers, O-rings, rings, keys, standoffs
             on the face. "Offset" then slides the part along the axis.
"""

import math
import re
from fractions import Fraction

from . import hardware_tables as T
from . import hole_tables, thread_tables

SQRT3 = math.sqrt(3.0)
INCH = T.INCH
LENGTH_SERIES = T.LENGTH_SERIES  # (kept: the old name)


class HardwareError(ValueError):
    """The part cannot be made as asked; the message says why and what to do."""


KINDS = (
    ("screw", "Screw"),
    ("setscrew", "Set screw"),
    ("shoulder", "Shoulder screw"),
    ("nut", "Nut"),
    ("washer", "Washer"),
    ("oring", "O-ring"),
    ("bearing", "Ball bearing"),
    ("ring", "Retaining ring"),
    ("pin", "Dowel pin"),
    ("key", "Key"),
    ("standoff", "Standoff / spacer"),
    ("insert", "Heat-set insert"),
    ("magnet", "Magnet"),
)
SYSTEMS = (("metric", "Metric"), ("inch", "Inch"))
FITS = (("close", "Close"), ("normal", "Normal"), ("loose", "Loose"))
HOLE_DEPTHS = (("all", "Through All"), ("length", "Screw length"))
VARIANTS = (("open", "Open"), ("zz", "Shielded (ZZ)"), ("2rs", "Sealed (2RS)"))

INSERT_EXTRA_DEPTH = 1.0  # the hole is this much deeper than the insert (Guess)
MAGNET_CLEARANCE = 0.2  # mm on the diameter (Guess: printed holes come out small)
BUTTON_CBORE_EXTRA = 1.0  # a head without a table row gets a counterbore of dk + this (Guess)
RING_GAP = 30.0  # degrees a retaining ring is open (Guess: drawn simply, without lugs)
PAN_ROUND = 0.4  # a pan head's top edge is rounded with this share of its height (Guess)

# kept names (older code and tests read the tables through this module)
ISO_4762 = T.ISO_4762
ISO_7380 = T.ISO_7380
ISO_10642 = T.ISO_10642
ISO_4032 = T.ISO_4032
ISO_7089 = T.ISO_7089
INSERTS = T.INSERTS
MAGNETS = T.MAGNETS
AS568 = T.as568()
ORING_METRIC = T.oring_metric()

# -- the standards -----------------------------------------------------------------------------
STANDARDS = {}
STANDARD_ORDER = []


def _add(key, kind, system, label, noun, source, table, **more):
    STANDARDS[key] = dict(
        key=key, kind=kind, system=system, label=label, noun=noun, source=source, table=table
    )
    STANDARDS[key].update(more)
    STANDARD_ORDER.append(key)


M, I = "metric", "inch"
_add("iso4762", "screw", M, "Socket head cap screw (ISO 4762)", "Socket Head Cap Screw",
     "ISO 4762", T.ISO_4762, head="socket", words="shcs allen cap hex socket")  # fmt: skip
_add("iso7380", "screw", M, "Button head screw (ISO 7380)", "Button Head Screw",
     "ISO 7380-1", T.ISO_7380, head="button", words="bhcs dome round allen socket")  # fmt: skip
_add("iso10642", "screw", M, "Countersunk screw (ISO 10642)", "Countersunk Screw",
     "ISO 10642", T.ISO_10642, head="flat", angle=90.0,
     words="flat head fhcs csk allen socket")  # fmt: skip
_add("din7984", "screw", M, "Low head socket cap screw (DIN 7984)", "Low Head Cap Screw",
     "DIN 7984", T.DIN_7984, head="low", words="low profile socket allen")  # fmt: skip
_add("iso4017", "screw", M, "Hex head screw (ISO 4017)", "Hex Head Screw",
     "ISO 4017", T.ISO_4017, head="hex", words="hex bolt hexagon cap")  # fmt: skip
_add("iso7045", "screw", M, "Pan head screw, Phillips (ISO 7045)", "Phillips Pan Head Screw",
     "ISO 7045", T.ISO_7045, head="pan_ph", words="pan cross recess machine")  # fmt: skip
_add("iso1580", "screw", M, "Pan head screw, slotted (ISO 1580)", "Slotted Pan Head Screw",
     "ISO 1580", T.ISO_1580, head="pan_sl", words="pan slot machine")  # fmt: skip
_add("asme_shcs", "screw", I, "Socket head cap screw (ASME B18.3)", "Socket Head Cap Screw",
     "ASME B18.3", T.ASME_SHCS, head="socket", words="shcs allen cap hex socket unc")  # fmt: skip
_add("asme_bhcs", "screw", I, "Button head screw (ASME B18.3)", "Button Head Screw",
     "ASME B18.3", T.ASME_BHCS, head="button", words="bhcs dome round allen socket")  # fmt: skip
_add("asme_fhcs", "screw", I, "Flat head screw (ASME B18.3)", "Flat Head Screw",
     "ASME B18.3", T.ASME_FHCS, head="flat", angle=82.0,
     words="countersunk fhcs csk allen socket")  # fmt: skip
_add("asme_lhcs", "screw", I, "Low head socket cap screw (ASME B18.3)", "Low Head Cap Screw",
     "ASME B18.3", T.ASME_LHCS, head="low", words="low profile socket allen")  # fmt: skip
_add("asme_hex", "screw", I, "Hex cap screw (ASME B18.2.1)", "Hex Cap Screw",
     "ASME B18.2.1", T.ASME_HEX, head="hex", words="hex bolt hexagon head")  # fmt: skip
_add("asme_pan_ph", "screw", I, "Pan head screw, Phillips (ASME B18.6.3)",
     "Phillips Pan Head Screw", "ASME B18.6.3", T.ASME_PAN, head="pan_ph",
     words="pan cross recess machine")  # fmt: skip
_add("asme_pan_sl", "screw", I, "Pan head screw, slotted (ASME B18.6.3)",
     "Slotted Pan Head Screw", "ASME B18.6.3", T.ASME_PAN, head="pan_sl",
     words="pan slot machine")  # fmt: skip
for _point, _iso, _label in (
    ("cup", "ISO 4029", "Cup"),
    ("flat", "ISO 4026", "Flat"),
    ("cone", "ISO 4027", "Cone"),
    ("dog", "ISO 4028", "Dog"),
):
    _add("iso" + _iso[-4:], "setscrew", M, "%s point set screw (%s)" % (_label, _iso),
         "%s Point Set Screw" % _label, _iso, T.ISO_SET, point=_point,
         words="setscrew grub socket allen")  # fmt: skip
for _point, _label in (("cup", "Cup"), ("flat", "Flat"), ("cone", "Cone"), ("dog", "Half dog")):
    _add("asme_ss_" + _point, "setscrew", I, "%s point set screw (ASME B18.3)" % _label,
         "%s Point Set Screw" % _label, "ASME B18.3", T.ASME_SET, point=_point,
         words="setscrew grub socket allen")  # fmt: skip
_add("iso7379", "shoulder", M, "Shoulder screw (ISO 7379)", "Shoulder Screw", "ISO 7379",
     T.ISO_7379, words="shoulder bolt stripper")  # fmt: skip
_add("asme_shoulder", "shoulder", I, "Shoulder screw (ASME B18.3)", "Shoulder Screw",
     "ASME B18.3", T.ASME_SHOULDER, words="shoulder bolt stripper")  # fmt: skip
_add("iso4032", "nut", M, "Hex nut (ISO 4032)", "Hex Nut", "ISO 4032", T.ISO_4032,
     words="hexagon")  # fmt: skip
_add("iso4035", "nut", M, "Thin hex nut / jam nut (ISO 4035)", "Thin Hex Nut", "ISO 4035",
     T.ISO_4035, words="jam hexagon")  # fmt: skip
_add("iso7040", "nut", M, "Nylon insert lock nut (ISO 7040)", "Nylon Lock Nut", "ISO 7040",
     T.ISO_7040, words="locknut nyloc nylock hex")  # fmt: skip
_add("asme_nut", "nut", I, "Hex nut (ASME B18.2.2)", "Hex Nut", "ASME B18.2.2", T.ASME_NUT,
     words="hexagon machine")  # fmt: skip
_add("asme_jam", "nut", I, "Jam nut (ASME B18.2.2)", "Jam Nut", "ASME B18.2.2", T.ASME_JAM,
     words="thin hex")  # fmt: skip
_add("asme_locknut", "nut", I, "Nylon insert lock nut (ASME B18.16.6)", "Nylon Lock Nut",
     "ASME B18.16.6", T.ASME_LOCKNUT, words="locknut nyloc nylock hex")  # fmt: skip
_add("iso7089", "washer", M, "Plain washer (ISO 7089)", "Flat Washer", "ISO 7089",
     T.ISO_7089, words="flat plain")  # fmt: skip
_add("din127", "washer", M, "Split lock washer (DIN 127)", "Split Lock Washer", "DIN 127",
     T.DIN_127, split=True, words="spring")  # fmt: skip
_add("asme_washer_sae", "washer", I, "Flat washer, SAE (ASME B18.21.1)", "Flat Washer (SAE)",
     "ASME B18.21.1", T.ASME_WASHER_SAE, words="plain narrow")  # fmt: skip
_add("asme_washer_uss", "washer", I, "Flat washer, USS (ASME B18.21.1)", "Flat Washer (USS)",
     "ASME B18.21.1", T.ASME_WASHER_USS, words="plain wide")  # fmt: skip
_add("asme_lockwasher", "washer", I, "Split lock washer (ASME B18.21.1)", "Split Lock Washer",
     "ASME B18.21.1", T.ASME_LOCKWASHER, split=True, words="spring")  # fmt: skip
_add("as568", "oring", I, "O-ring, dash number (AS568)", "O-Ring", "SAE AS568", AS568,
     words="oring o ring seal dash")  # fmt: skip
_add("oring_metric", "oring", M, "O-ring, metric (inside x section)", "O-Ring", "ISO 3601",
     ORING_METRIC, words="oring o ring seal")  # fmt: skip
_add("bearing", "bearing", M, "Deep groove ball bearing (ISO 15)", "Ball Bearing", "ISO 15",
     T.BEARINGS, words="bearing deep groove radial")  # fmt: skip
_add("bearing_inch", "bearing", I, "Ball bearing, inch R series", "Ball Bearing", "ABMA 12",
     T.BEARINGS_INCH, words="bearing deep groove radial")  # fmt: skip
_add("din471", "ring", M, "External retaining ring (DIN 471)", "External Retaining Ring",
     "DIN 471", T.DIN_471, external=True, words="circlip snap shaft")  # fmt: skip
_add("din472", "ring", M, "Internal retaining ring (DIN 472)", "Internal Retaining Ring",
     "DIN 472", T.DIN_472, external=False, words="circlip snap bore")  # fmt: skip
_add("asme_ring_ext", "ring", I, "External retaining ring (ASME B18.27.1)",
     "External Retaining Ring", "ASME B18.27.1", T.ASME_RING_EXT, external=True,
     words="circlip snap shaft")  # fmt: skip
_add("asme_ring_int", "ring", I, "Internal retaining ring (ASME B18.27.1)",
     "Internal Retaining Ring", "ASME B18.27.1", T.ASME_RING_INT, external=False,
     words="circlip snap bore")  # fmt: skip
_add("iso2338", "pin", M, "Dowel pin (ISO 2338)", "Dowel Pin", "ISO 2338", T.ISO_2338,
     words="parallel")  # fmt: skip
_add("asme_dowel", "pin", I, "Dowel pin (ASME B18.8.2)", "Dowel Pin", "ASME B18.8.2",
     T.ASME_DOWEL, words="parallel")  # fmt: skip
_add("din6885", "key", M, "Parallel key (DIN 6885 A)", "Key", "DIN 6885", T.DIN_6885,
     round_ends=True, words="feather machine")  # fmt: skip
_add("asme_key", "key", I, "Square key (ASME B17.1)", "Key", "ASME B17.1", T.ASME_KEY,
     round_ends=False, words="machine parallel")  # fmt: skip
_add("standoff_hex", "standoff", M, "Hex standoff, threaded through", "Hex Standoff",
     "commercial", T.STANDOFF_HEX, words="spacer pillar")  # fmt: skip
_add("spacer_round", "standoff", M, "Round spacer, unthreaded", "Round Spacer", "commercial",
     T.SPACER_ROUND, words="standoff sleeve")  # fmt: skip
_add("insert", "insert", M, "Heat-set insert (3D printing)", "Heat-Set Insert", "commercial",
     T.INSERTS, words="threaded brass heat set")  # fmt: skip
_add("magnet", "magnet", M, "Round magnet", "Magnet", "commercial", T.MAGNETS,
     words="disc neodymium")  # fmt: skip
STANDARD_ORDER = tuple(STANDARD_ORDER)
del M, I

LENGTH_KINDS = ("screw", "setscrew", "shoulder", "pin", "key", "standoff")
THREADED_KINDS = ("screw", "setscrew", "shoulder", "nut", "standoff", "insert")
HOLE_KINDS = ("screw", "setscrew", "nut", "washer", "insert", "magnet")  # "make the hole"

DEFAULTS = {
    "kind": "screw",
    "standard": "iso4762",
    "size": "3",
    "length": 10.0,
    "thread": "",  # "" = the size's coarse thread; else a thread_tables label
    "modeled": False,  # threads: cosmetic (a plain cylinder) or modeled
    "variant": "zz",  # a bearing: open | zz | 2rs
    "flip": False,
    "offset": 0.0,  # along the axis, out of the part
    "seat": None,  # set when an existing hole decides how deep the head sits
    "make_hole": True,
    "fit": "normal",
    "sink_head": True,
    "hole_depth": "all",
    "clearance": MAGNET_CLEARANCE,
    "joint": True,  # hold the part to what it was placed on (a rigid joint)
    "similar": True,  # fill every hole like the one clicked on that face
}
DEFAULT_SIZES = {
    "magnet": "6x3",
    "as568": "012",
    "oring_metric": "10x2",
    "bearing": "608",
    "bearing_inch": "R4",
    "din471": "10",
    "din472": "22",
    "din6885": "4x4",
    "iso7379": "8",
}
MATERIALS = {  # material.LIBRARY keys tried in this order
    "insert": ("brass", "copper"),
    "oring": ("rubber", "nbr"),
    "standoff": ("aluminium",),
}
LOOKS = {  # appearance.LIBRARY keys
    "screw": "cast_iron",
    "setscrew": "cast_iron",
    "shoulder": "cast_iron",
    "nut": "steel_satin",
    "washer": "steel_satin",
    "oring": "rubber_black",
    "bearing": "steel_polished",
    "ring": "cast_iron",
    "pin": "steel_polished",
    "key": "steel_satin",
    "standoff": "aluminium_satin",
    "insert": "brass",
    "magnet": "steel_polished",
}


# -- reading the tables -------------------------------------------------------------------------
def std(standard):
    if standard not in STANDARDS:
        raise HardwareError("Unknown hardware standard %r." % (standard,))
    return STANDARDS[standard]


def standards(kind, system=None):
    """[(key, label)] of the standards of a kind (and a unit system), in the dialog's order."""
    return [
        (k, STANDARDS[k]["label"])
        for k in STANDARD_ORDER
        if STANDARDS[k]["kind"] == kind and system in (None, STANDARDS[k]["system"])
    ]


def systems(kind):
    """The unit systems a kind comes in, metric first."""
    found = {STANDARDS[k]["system"] for k in STANDARD_ORDER if STANDARDS[k]["kind"] == kind}
    return [s for s, _ in SYSTEMS if s in found]


def kind_of(standard):
    return std(standard)["kind"]


def system_of(standard):
    return std(standard)["system"]


def is_inch(standard):
    return system_of(standard) == "inch"


def _mixed(text):
    """1.125 for "1 1/8", 0.25 for "1/4", None for anything else."""
    try:
        return float(sum(Fraction(part) for part in str(text).split()))
    except (ValueError, ZeroDivisionError):
        return None


def _size_number(size):
    size = str(size)
    if size.startswith("#"):
        try:
            return 0.060 + 0.013 * int(size[1:])
        except ValueError:
            return 1e9
    if size.upper().startswith(("R", "MR")):
        digits = re.sub(r"\D", "", size)
        return float(digits or 0) + (1e5 if size.upper().startswith("MR") else 2e5)
    if "x" in size:
        a, _, b = size.partition("x")
        try:
            return float(a) * 1000.0 + float(b)
        except ValueError:
            return 1e9
    value = _mixed(size)
    return value if value is not None else 1e9


def sizes(standard):
    """The sizes of a standard, smallest first ("2", "2.5", "#10", "1/4", "6x3", "012")."""
    s = std(standard)
    if s["kind"] == "oring":
        return sorted(s["table"], key=lambda k: (s["table"][k][1], s["table"][k][0]))
    if s["kind"] == "bearing":
        return list(s["table"])
    return sorted(s["table"], key=_size_number)


def row(standard, size):
    table = STANDARDS[standard]["table"] if standard in STANDARDS else {}
    if size not in table:
        some = [size_label(standard, s) for s in sizes(standard)] if standard in STANDARDS else []
        if len(some) > 14:
            some = some[:12] + ["...", some[-1]]
        raise HardwareError(
            "%s has no size %s. Pick one of: %s."
            % (STANDARDS.get(standard, {"label": standard})["label"], size, ", ".join(some))
        )
    return table[size]


def _unit(standard):
    return INCH if is_inch(standard) else 1.0


def fraction(inches):
    """An inch value the way it is said: "3/4", "1 1/4", "0.196"."""
    f = Fraction(int(round(float(inches) * 64.0)), 64)
    if abs(float(f) - float(inches)) > 1e-4:
        return ("%.3f" % inches).rstrip("0").rstrip(".")
    whole, rest = divmod(f.numerator, f.denominator)
    if not rest:
        return "%d" % whole
    part = "%d/%d" % (rest, f.denominator)
    return "%d %s" % (whole, part) if whole else part


def _inches(mm):
    return ("%.3f" % (mm / INCH)).rstrip("0").rstrip(".")


def thread_size(standard, size):
    """The thread size a part has or goes with ("3", "#10", "1/4"), or None."""
    s = std(standard)
    if s["kind"] == "shoulder":
        return row(standard, size)[1]
    if s["kind"] in ("screw", "setscrew", "nut", "washer", "standoff", "insert"):
        return size
    return None


def thread_standard(standard):
    """thread_tables' / hole_tables' name for a part's unit system."""
    return "ansi" if is_inch(standard) else "iso"


def designations(standard, size):
    """The threads a size comes in (thread_tables.Designation), coarse first; [] for a part
    without a thread."""
    if kind_of(standard) not in THREADED_KINDS:
        return []
    return thread_tables.designations(thread_standard(standard), thread_size(standard, size))


def designation(options):
    """The thread of a part: the one named in options["thread"], else the coarse one."""
    o = options
    found = designations(o["standard"], o["size"])
    for d in found:
        if d.label == o.get("thread"):
            return d
    return found[0] if found else None


def thread_diameter(standard, size):
    """The nominal diameter (mm) of the screw a part has or goes with."""
    key = thread_size(standard, size)
    found = thread_tables.designations(thread_standard(standard), key) if key else []
    if found:
        return found[0].diameter
    number = _size_number(key or size)
    return number * _unit(standard)


def size_label(standard, size):
    """What the Size box shows: "M3", "#10", "1/4", "-012 (0.364 x 0.070 in)", "6202 (15 x
    35 x 11)", "6 x 3 mm"."""
    s = std(standard)
    kind, inch = s["kind"], s["system"] == "inch"
    if kind == "magnet":
        return "%g x %g mm" % T.MAGNETS[size]
    if kind == "oring":
        inside, section = s["table"][size]
        if inch:
            return "-%s (%s x %s in)" % (size, ("%.3f" % inside), ("%.3f" % section))
        return "%g x %g mm" % (inside, section)
    if kind == "bearing":
        d, big, b, _bs = s["table"][size]
        if inch:
            return "%s (%s x %s x %s in)" % (size, fraction(d), fraction(big), fraction(b))
        return "%s (%g x %g x %g)" % (size, d, big, b)
    if kind == "shoulder":
        thread = designations(standard, size)
        name = thread[0].label.split(" ")[0] if thread else ""
        return "%s in (%s)" % (size, name) if inch else "%s mm (%s)" % (size, name.split("x")[0])
    if kind in ("ring", "pin") or standard == "asme_key":
        return "%s in" % size if inch else "%s mm" % size
    if kind == "key":
        return "%s mm" % size.replace("x", " x ")
    return size if inch else "M%s" % size


def default_size(standard):
    found = sizes(standard)
    wanted = DEFAULT_SIZES.get(standard, "1/4" if is_inch(standard) else "3")
    return wanted if wanted in found else found[0]


def has_length(standard):
    return kind_of(standard) in LENGTH_KINDS


def lengths(standard, size):
    """The standard lengths a part comes in, mm (the length series within its range)."""
    if not has_length(standard):
        return []
    lo, hi = row(standard, size)[-1]
    if is_inch(standard):
        return [v * INCH for v in T.INCH_LENGTH_SERIES if lo - 1e-9 <= v <= hi + 1e-9]
    return [float(v) for v in T.LENGTH_SERIES if lo - 1e-9 <= v <= hi + 1e-9]


def length_label(standard, length):
    """A length as the dialog and the names show it: "10 mm", "3/4 in"."""
    if is_inch(standard):
        return "%s in" % fraction(float(length) / INCH)
    return "%g mm" % float(length)


def _reference(standard, size):
    """The diameter the default length goes by."""
    kind = kind_of(standard)
    r = row(standard, size)
    return float(r[0]) * _unit(standard) if kind != "standoff" else thread_diameter(standard, size)


def default_length(standard, size):
    """About 3.3 times the diameter (M3 -> 10), the nearest standard length."""
    found = lengths(standard, size)
    if not found:
        return 0.0
    d = _reference(standard, size)
    return min(found, key=lambda v: (abs(v - 3.3 * d), v))


def dims(standard, size, variant=None):
    """The part's sizes (mm) by name."""
    s = std(standard)
    kind = s["kind"]
    r = row(standard, size)
    u = _unit(standard)
    if kind == "screw":
        head = s["head"]
        if head == "hex":
            d, af, k = (v * u for v in r[:3])
            return {"d": d, "af": af, "k": k, "dk": 2.0 * af / SQRT3, "head": head}
        if head in ("pan_ph", "pan_sl"):
            if s["system"] == "inch":
                d, dk, k_slot, k_cross, n, t, m = (v * u for v in r[:7])
                k = k_cross if head == "pan_ph" else k_slot
            elif head == "pan_ph":
                d, dk, k, m = r[:4]
                n = t = 0.0
            else:
                d, dk, k, n, t = r[:5]
                m = 0.0
            out = {"d": d, "dk": dk, "k": k, "head": head, "r": PAN_ROUND * k}
            if head == "pan_ph":  # the recess drawn simply: two crossed slots (Guess)
                out.update(m=m, b=0.18 * m, q=0.5 * k)
            else:
                out.update(n=n, t=t)
            return out
        d, dk, k, hexagon, t = (v * u for v in r[:5])
        out = {"d": d, "dk": dk, "k": k, "s": hexagon, "t": t, "head": head}
        if head == "flat":
            out["angle"] = s["angle"]
            # the head is the cone the standard's angle gives (a table rounds its height)
            out["k"] = round((dk - d) / 2.0 / math.tan(math.radians(s["angle"] / 2.0)), 9)
        return out
    if kind == "setscrew":
        if s["system"] == "inch":
            d, hexagon, t, cup, dog, dog_z = (v * u for v in r[:6])
            flat, tip = cup, 0.1 * d
        else:
            d, hexagon, t, flat, cup, tip, dog, dog_z = r[:8]
        return {
            "d": d, "s": hexagon, "t": t, "point": s["point"], "dp": flat, "dv": cup,
            "dt": tip, "dog": dog, "dog_z": dog_z,
        }  # fmt: skip
    if kind == "shoulder":
        d1, thread, b, dk, k, hexagon, t = r[:7]
        d1, b, dk, k, hexagon, t = (v * u for v in (d1, b, dk, k, hexagon, t))
        return {
            "d1": d1, "d": thread_diameter(standard, size), "b": b, "dk": dk, "k": k,
            "s": hexagon, "t": t, "thread": thread,
        }  # fmt: skip
    if kind == "nut":
        d, across, m = (v * u for v in r)
        return {"d": d, "s": across, "m": m, "e": 2.0 * across / SQRT3}
    if kind == "washer":
        d1, d2, h = (v * u for v in r)
        out = {"d1": d1, "d2": d2, "h": h}
        if s.get("split"):
            out["gap"] = 0.6 * h
        return out
    if kind == "oring":
        inside, section = (v * u for v in r)
        return {"id": inside, "cs": section}
    if kind == "bearing":
        d, big, b, shielded = (v * u for v in r)
        return {"d": d, "D": big, "B": b if (variant or "zz") == "open" else shielded}
    if kind == "ring":
        if s["system"] == "inch":
            thickness, free, groove, width = (v * u for v in r)
            nominal_d = _mixed(size) * u
            beam = 0.11 * nominal_d + 0.02 * u
        else:
            thickness, free, beam, groove, width = r
            nominal_d = float(size)
        return {
            "d1": nominal_d, "s": thickness, "d3": free, "b": beam, "d2": groove, "m": width,
            "external": bool(s["external"]),
        }  # fmt: skip
    if kind == "pin":
        d, c = (v * u for v in r[:2])
        return {"d": d, "c": c}
    if kind == "key":
        b, h = (v * u for v in r[:2])
        return {"b": b, "h": h, "round_ends": bool(s["round_ends"])}
    if kind == "standoff":
        if standard == "standoff_hex":
            return {"d": r[0], "af": r[1]}
        return {"d1": r[0], "d2": r[1]}
    if kind == "insert":
        d, outside, length, hole = r
        return {"d": d, "outside": outside, "length": length, "hole": hole}
    diameter, thickness = r
    return {"diameter": diameter, "thickness": thickness}


def nominal(standard, size):
    """The screw diameter a part goes with (other parts: their own main diameter), mm."""
    kind = kind_of(standard)
    if kind in ("screw", "setscrew", "nut", "washer", "standoff", "insert"):
        return thread_diameter(standard, size)
    dm = dims(standard, size)
    for key in ("d1", "d", "id", "diameter", "b"):
        if key in dm:
            return dm[key]
    return 0.0


# -- options -------------------------------------------------------------------------------------
def default_sink(standard):
    """Socket, low and countersunk heads go into the part by default; button, pan and
    hexagon heads are made to sit on the face (Guess)."""
    s = std(standard)
    return s["kind"] == "screw" and s["head"] in ("socket", "flat", "low")


def with_defaults(options=None):
    given = options or {}
    o = dict(DEFAULTS)
    o.update({k: v for k, v in given.items() if v is not None})
    if o["standard"] not in STANDARDS:
        found = standards(o["kind"]) if o["kind"] in dict(KINDS) else []
        o["standard"] = found[0][0] if found else "iso4762"
    o["kind"] = kind_of(o["standard"])
    if o["size"] not in STANDARDS[o["standard"]]["table"]:
        o["size"] = default_size(o["standard"])
    if has_length(o["standard"]):
        try:
            o["length"] = float(o["length"])
        except (TypeError, ValueError):
            o["length"] = default_length(o["standard"], o["size"])
    if given.get("sink_head") is None:
        o["sink_head"] = default_sink(o["standard"])
    if o["variant"] not in dict(VARIANTS):
        o["variant"] = "zz"
    for key in ("flip", "make_hole", "sink_head", "modeled", "joint", "similar"):
        o[key] = bool(o[key])
    if o["kind"] not in HOLE_KINDS:
        o["make_hole"] = False
    o["clearance"] = float(o["clearance"])
    try:
        o["offset"] = float(o["offset"])
    except (TypeError, ValueError):
        o["offset"] = 0.0
    o["seat"] = given.get("seat")
    if o["seat"] is not None:
        o["seat"] = float(o["seat"])
    o["thread"] = str(o["thread"] or "")
    return o


def change_standard(options, standard):
    """The options for another standard: its default size (the same size when it has it),
    length and head setting."""
    o = with_defaults(options)
    table = std(standard)["table"]
    size = o["size"] if o["size"] in table else default_size(standard)
    o.update(
        standard=standard,
        kind=kind_of(standard),
        size=size,
        sink_head=default_sink(standard),
        seat=None,
        thread="",
    )
    if has_length(standard):
        o["length"] = fit_length(standard, size, o.get("length"))
    return with_defaults(o)


def fit_length(standard, size, length):
    """The length kept when the size changes: the same one when the new size has it, else
    the new size's default."""
    found = lengths(standard, size)
    try:
        length = float(length)
    except (TypeError, ValueError):
        length = None
    if length is not None and any(abs(v - length) < 1e-6 for v in found):
        return length
    return default_length(standard, size)


def socket_depth(options):
    """How deep a set screw's hexagon socket is: the standard's depth, less in a short screw
    (it must leave the point whole)."""
    o = options
    dm = dims(o["standard"], o["size"])
    return min(dm["t"], o["length"] - point_height(dm, o["length"]) - 0.2 * dm["d"])


def point_height(dm, length):
    """Height of a set screw's point (the cup's depth for a cup point). A cone point is 90
    degrees, 120 degrees on a screw no longer than its diameter (ISO 4027 and ASME B18.3
    blunt the cone of the short lengths the same way)."""
    point = dm["point"]
    if point == "flat":
        return (dm["d"] - dm["dp"]) / 2.0
    if point == "cone":
        sharp = (dm["d"] - dm["dt"]) / 2.0
        return sharp if length > dm["d"] + 1e-9 else sharp / math.tan(math.radians(60.0))
    if point == "dog":
        return dm["dog_z"]
    return dm["dv"] / 2.0 / math.tan(math.radians(60.0))


def check(options):
    """Raise HardwareError when the options cannot make a part; returns the options."""
    o = with_defaults(options)
    row(o["standard"], o["size"])
    kind = o["kind"]
    if has_length(o["standard"]):
        if o["length"] <= 0:
            raise HardwareError("The length must be more than 0.")
        dm = dims(o["standard"], o["size"])
        if kind == "screw" and dm["head"] == "flat" and o["length"] <= dm["k"]:
            raise HardwareError("A countersunk screw's length counts its head: make it longer.")
        if kind == "setscrew" and socket_depth(o) < 0.15 * dm["d"]:
            raise HardwareError("That set screw is too short for its point: make it longer.")
        if kind == "pin" and o["length"] <= 2.0 * dm["c"]:
            raise HardwareError("That pin is too short: make it longer.")
        if kind == "key" and dm["round_ends"] and o["length"] < dm["b"]:
            raise HardwareError("A key with round ends cannot be shorter than it is wide.")
    if o["fit"] not in dict(FITS):
        raise HardwareError("The fit must be Close, Normal or Loose.")
    if o["hole_depth"] not in dict(HOLE_DEPTHS):
        raise HardwareError("The hole depth must be Through All or Screw length.")
    if kind == "magnet" and not 0.0 <= o["clearance"] < 5.0:
        raise HardwareError("The magnet's clearance must be between 0 and 5 mm.")
    if o["modeled"] and kind in THREADED_KINDS and kind != "insert" and designation(o) is None:
        raise HardwareError("No thread is known for this size: untick Modeled threads.")
    return o


def thread_name(options):
    """The thread as a name starts with it: "M3", "M6x0.75" (a fine pitch), "1/4-20"."""
    o = options
    found = designations(o["standard"], o["size"])
    if not found:
        return ("%s" if is_inch(o["standard"]) else "M%s") % o["size"]
    chosen = designation(o)
    if is_inch(o["standard"]):
        return chosen.label.split(" ")[0]
    return chosen.label if chosen is not found[0] else "M%s" % thread_size(o["standard"], o["size"])


def name(options):
    """The part's name, the way a person asks for it: "M3 x 10 Socket Head Cap Screw",
    "1/4-20 x 3/4 in Socket Head Cap Screw", "O-Ring AS568-012", "Ball Bearing 6202-2RS"."""
    o = with_defaults(options)
    s = std(o["standard"])
    kind, inch, noun = s["kind"], s["system"] == "inch", s["noun"]
    if kind == "magnet":
        return "Magnet %g x %g" % T.MAGNETS[o["size"]]
    if kind == "oring":
        if inch:
            return "O-Ring AS568-%s" % o["size"]
        return "O-Ring %s" % o["size"].replace("x", " x ")
    if kind == "bearing":
        suffix = {"open": "", "zz": "-ZZ", "2rs": "-2RS"}[o["variant"]]
        return "%s %s%s" % (noun, o["size"], suffix)
    if kind == "ring":
        return "%s %s %s" % (noun, o["size"], "in" if inch else "mm")
    long = length_label(o["standard"], o["length"]) if has_length(o["standard"]) else ""
    if not inch:
        long = long.replace(" mm", "")
    if kind == "pin":
        return "%s %s x %s" % (noun, o["size"], long)
    if kind == "key":
        return "%s %s x %s" % (noun, o["size"].replace("x", " x "), long)
    if kind == "shoulder":
        return "%s x %s %s (%s)" % (o["size"], long, noun, thread_name(o))
    if kind in ("screw", "setscrew", "standoff"):
        return "%s x %s %s" % (thread_name(o), long, noun)
    return "%s %s" % (thread_name(o), noun)


def description(options):
    """What the parts list's Description shows: the standard the part follows."""
    o = with_defaults(options)
    source = std(o["standard"])["source"]
    return "" if source == "commercial" else source


def material_keys(options):
    """The material library keys to try for a part, best first."""
    return MATERIALS.get(with_defaults(options)["kind"], ()) + ("steel",)


def look_key(options):
    return LOOKS.get(with_defaults(options)["kind"], "steel_satin")


# -- threads -------------------------------------------------------------------------------------
def thread_length(options):
    """How much of a screw is threaded, from its tip (mm): the standard thread length
    2 d + 6 mm (inch: 2 d + 1/4 in), the whole shank when the screw is shorter; a set
    screw's and a hexagon head screw's (ISO 4017) whole length; a shoulder screw's thread."""
    o = with_defaults(options)
    dm = dims(o["standard"], o["size"])
    kind = o["kind"]
    if kind == "shoulder":
        return dm["b"]
    if kind == "setscrew":
        return o["length"] - (dm["dog_z"] if dm["point"] == "dog" else 0.0)
    if kind != "screw":
        return 0.0
    shank = o["length"] - (dm["k"] if dm["head"] == "flat" else 0.0)
    if o["standard"] == "iso4017":
        return shank
    usual = 2.0 * dm["d"] + (0.25 * INCH if is_inch(o["standard"]) else 6.0)
    return min(shank, usual)


# -- the hole ------------------------------------------------------------------------------------
def head_cut(options):
    """The counterbore or countersink a sunk screw head sits in: {"hole_type", "diameter",
    "depth" | "angle"}, or None (not a screw, or the head sits on the face)."""
    o = with_defaults(options)
    if o["kind"] != "screw" or not o["sink_head"]:
        return None
    size = o["size"]
    family = thread_standard(o["standard"])
    dm = dims(o["standard"], size)
    head = dm["head"]
    key = {"socket": "socket_head", "flat": "countersunk", "hex": "hex_head"}.get(head)
    if o["standard"] in ("iso4762", "iso10642", "iso4017") or is_inch(o["standard"]):
        found = hole_tables.head_cut(family, key, size) if key else None
        if found is not None:
            return found
    if head == "flat":
        return {"hole_type": "countersink", "diameter": round(dm["dk"], 4), "angle": dm["angle"]}
    if is_inch(o["standard"]):  # dk + 1/32 in, as deep as the head
        return {
            "hole_type": "counterbore",
            "diameter": round(dm["dk"] + INCH / 32.0, 4),
            "depth": round(dm["k"], 4),
        }
    return {  # dk + 1 mm, as deep as DIN 974-1's rule
        "hole_type": "counterbore",
        "diameter": round(dm["dk"] + BUTTON_CBORE_EXTRA, 4),
        "depth": hole_tables._cbore_depth(dm["k"], dm["d"]),
    }


def clearance(options):
    """The clearance hole's diameter for the screw that goes through (ISO 273 / ASME
    B18.2.8)."""
    o = with_defaults(options)
    d = thread_diameter(o["standard"], o["size"])
    key = thread_size(o["standard"], o["size"]) or o["size"]
    return hole_tables.clearance_diameter(thread_standard(o["standard"]), key, d, o["fit"])


def seat_in_cone(dk, head_angle, top_diameter, cone_half_angle, hole_diameter):
    """How high a countersunk head's top stands above the face (negative: below it) in a
    countersink or chamfer `top_diameter` wide at the face whose wall makes
    `cone_half_angle` degrees with the axis, over a hole `hole_diameter` wide. The head (a
    cone of `head_angle` degrees in all, `dk` wide at its top) comes down until it touches:
    with matching angles its top lies where the countersink is as wide as the head."""
    a = math.tan(math.radians(cone_half_angle))
    b = math.tan(math.radians(head_angle / 2.0))
    if a <= 1e-9 or b <= 1e-9:
        return 0.0
    if a > b + 1e-9:
        # the countersink opens wider than the head: the head rests on the hole's edge
        depth_of_edge = (top_diameter - hole_diameter) / 2.0 / a
        return (dk - hole_diameter) / 2.0 / b - depth_of_edge
    if dk <= top_diameter:
        return -(top_diameter - dk) / 2.0 / a  # (matching or steeper wall) the rim of the head
    return (dk - top_diameter) / 2.0 / b  # wider than the countersink: on its top edge


def seat(options):
    """Height of the part's seat above the clicked face (its frame's z). A sunk socket or
    button head sits at the bottom of its counterbore, a sunk countersunk head flush with the
    face; a countersunk head not sunk sits with its cone on the face. A hole that is there
    already decides it (options["seat"]). Everything else sits at 0."""
    o = with_defaults(options)
    if o["seat"] is not None and not o["make_hole"]:
        return o["seat"]
    if o["kind"] != "screw":
        return 0.0
    dm = dims(o["standard"], o["size"])
    if dm["head"] == "flat":
        return 0.0 if o["sink_head"] else dm["k"]
    cut = head_cut(o)
    if cut is not None and cut["hole_type"] == "counterbore":
        return -float(cut["depth"])
    return 0.0


def seat_for_hole(options, place):
    """(Head sunk in, seat) of a part put on a hole or a shaft that is already there.
    `place`: {"is_hole", "diameter" (of the opening), "hole_diameter", "cbore_depth",
    "cone" ({"top_diameter", "half_angle"}), "shoulder"}. A countersunk head seats in the
    countersink or chamfer (seat_in_cone), on the edge of a plain hole otherwise; any other
    head that fits goes to the floor of a counterbore, else it sits on the face. A bearing
    put on a shaft at a shoulder stands on the shoulder."""
    o = with_defaults(options)
    kind = o["kind"]
    if kind == "bearing":
        if place.get("shoulder") and not place.get("is_hole"):
            return False, dims(o["standard"], o["size"], o["variant"])["B"]
        return False, None
    if kind != "screw" or not place.get("is_hole"):
        return (o["sink_head"] if kind == "screw" else False), None
    dm = dims(o["standard"], o["size"])
    cone = place.get("cone")
    hole_d = place.get("hole_diameter") or dm["d"]
    in_cbore = (
        place.get("cbore_depth") is not None and dm["dk"] <= place.get("diameter", 0.0) + 1e-6
    )
    if dm["head"] == "flat":
        if cone:
            high = seat_in_cone(
                dm["dk"], dm["angle"], cone["top_diameter"], cone["half_angle"], hole_d
            )
            return True, high
        on_edge = seat_in_cone(dm["dk"], dm["angle"], hole_d, 89.0, hole_d)
        if in_cbore:
            return True, on_edge - float(place["cbore_depth"])
        return on_edge <= 1e-9, on_edge
    if in_cbore:
        return True, -float(place["cbore_depth"])
    return False, 0.0


def hole_options(options):
    """The Hole step the part needs (hole.py options), or None when "make the hole" is off
    or the part gets none."""
    o = check(options)
    kind = o["kind"]
    if not o["make_hole"] or kind not in HOLE_KINDS:
        return None
    base = {"drill_point": "flat", "flip": False}
    if kind == "insert":
        dm = dims(o["standard"], o["size"])
        return dict(
            base,
            tap_type="simple",
            hole_type="simple",
            diameter=dm["hole"],
            extent="distance",
            depth=round(dm["length"] + INSERT_EXTRA_DEPTH, 4),
        )
    if kind == "magnet":
        dm = dims(o["standard"], o["size"])
        return dict(
            base,
            tap_type="simple",
            hole_type="simple",
            diameter=round(dm["diameter"] + o["clearance"], 4),
            extent="distance",
            depth=dm["thickness"],
        )
    family = thread_standard(o["standard"])
    chosen = designation(o)
    if kind == "setscrew":
        return dict(
            base,
            tap_type="tapped",
            standard=family,
            size=o["size"],
            designation=chosen.label if chosen is not None and o["thread"] else "",
            hole_type="simple",
            extent="distance",
            depth=round(o["length"], 4),
            full_tap=True,
            modeled=False,
        )
    out = dict(
        base,
        tap_type="clearance",
        standard=family,
        size=o["size"],
        designation="",  # hole.py takes the size's coarse thread (M3x0.5)
        fit=o["fit"],
        hole_type="simple",
        extent="all",
        depth=10.0,
        fastener="",
    )
    cut = head_cut(o) if kind == "screw" else None
    if cut is not None:
        out["hole_type"] = cut["hole_type"]
        if cut["hole_type"] == "counterbore":
            head = dims(o["standard"], o["size"])["head"]
            out.update(
                fastener="hex_head" if head == "hex" else "socket_head",
                cbore_diameter=cut["diameter"],
            )
            out["cbore_depth"] = cut["depth"]
        else:
            out.update(fastener="countersunk", csink_diameter=cut["diameter"])
            out["csink_angle"] = cut["angle"]
    if kind == "screw" and o["hole_depth"] == "length":
        out["extent"] = "distance"
        depth = o["length"]  # a countersunk screw's length counts its head
        if dims(o["standard"], o["size"])["head"] != "flat":
            depth -= seat(dict(o, seat=None))  # the shank starts at the counterbore's bottom
        out["depth"] = round(depth, 4)
    return out


# -- automatic size (Fusion's Size: Automatic, from the hole clicked) ---------------------------
def head_fits_rim(standard, size, diameter):
    """True when a round edge this wide is the top of the counterbore or countersink this
    screw's head sinks into (wider than any clearance hole for it): the head goes in."""
    if kind_of(standard) != "screw":
        return False
    loose = hole_tables.clearance_diameter(
        thread_standard(standard), size, thread_diameter(standard, size), "loose"
    )
    return float(diameter) > loose + 0.1


RING_PARTNER = {
    "din471": "din472",
    "din472": "din471",
    "asme_ring_ext": "asme_ring_int",
    "asme_ring_int": "asme_ring_ext",
}


def standard_for_place(standard, is_hole):
    """A retaining ring clicked onto a shaft is an external one, into a bore an internal
    one: the standard that fits what was clicked."""
    s = std(standard)
    if s["kind"] == "ring" and bool(s["external"]) == bool(is_hole):
        return RING_PARTNER[standard]
    return standard


def size_for_hole(standard, diameter, current=None, is_hole=True):
    """The size of `standard` that goes with a round hole (or, `is_hole` off, a shaft) of
    this diameter, or None. Screws, nuts, washers: a clearance hole (between the screw's
    diameter and its loose fit), a tapped hole for it (a little under the screw's diameter),
    the counterbore or countersink of its head. An insert's hole, a magnet's pocket, a pin's
    hole. A bearing by its outside diameter in a bore, by its bore on a shaft; an O-ring and
    a retaining ring the same way. When several fit equally well (6 x 2 and 6 x 3 magnets,
    M2.5 and M3 inserts share a hole), `current` wins."""
    s = std(standard)
    kind = s["kind"]
    diameter = float(diameter)
    family = thread_standard(standard)
    best = None
    for size in sizes(standard):
        if kind == "magnet":
            d = T.MAGNETS[size][0]
            lo, hi, target = d - 0.05, d + 0.6, d + MAGNET_CLEARANCE
        elif kind == "insert":
            hole = T.INSERTS[size][3]
            lo, hi, target = hole - 0.3, hole + 0.3, hole
        elif kind == "bearing":
            dm = dims(standard, size)
            target = dm["D"] if is_hole else dm["d"]
            lo, hi = target - 0.06, target + 0.06
        elif kind == "ring":
            if bool(s["external"]) == bool(is_hole):
                return None
            target = dims(standard, size)["d1"]
            lo, hi = target - 0.06, target + 0.06
        elif kind == "oring":
            dm = dims(standard, size)
            if current in s["table"] and abs(dm["cs"] - dims(standard, current)["cs"]) > 1e-6:
                continue  # the cross section stays: only the diameter follows the click
            if is_hole:  # in a bore: its outside diameter fills it
                target = dm["id"] + 2.0 * dm["cs"]
                lo, hi = target - 0.5 * dm["cs"], target + 0.5 * dm["cs"]
            else:  # on a shaft: stretched a little
                target = dm["id"]
                lo, hi = target - 0.02 * target, target + 0.5 * dm["cs"]
        elif kind in ("pin", "shoulder"):
            target = dims(standard, size)["d" if kind == "pin" else "d1"]
            lo, hi = target - 0.06, target + 0.3
        elif kind == "key":
            return None
        else:
            d = thread_diameter(standard, size)
            key = thread_size(standard, size) or size
            lo = 0.75 * d
            hi = hole_tables.clearance_diameter(family, key, d, "loose") + 0.1
            # a clearance hole of any fit, or the tap drill of its threads (thread_tables)
            drills = tuple(t.drill for t in thread_tables.designations(family, key)) or (0.84 * d,)
            target = (
                tuple(hole_tables.clearance_diameter(family, key, d, fit) for fit, _ in FITS)
                + drills
            )
            if kind == "setscrew":
                hi, target = d + 0.05, drills
            if kind == "screw":
                cut = head_cut({"standard": standard, "size": size, "sink_head": True})
                if cut is not None and abs(diameter - cut["diameter"]) <= 0.3:
                    lo, hi = cut["diameter"] - 0.3, cut["diameter"] + 0.3
                    target = cut["diameter"]
        if lo - 1e-9 <= diameter <= hi + 1e-9:
            targets = target if isinstance(target, tuple) else (target,)
            score = min(abs(diameter - t) for t in targets)
            score -= 1e-6 if size == current else 0.0
            if best is None or score < best[0]:
                best = (score, size)
    return best[1] if best else None


# -- sizes and volumes of the solids (hardware_shapes.py builds exactly these) ------------------
def hex_area(s):
    """Area of a regular hexagon s across the flats."""
    return SQRT3 / 2.0 * s * s


def cap_radius(base_radius, height):
    """Radius of the sphere a cap of this base radius and height is cut from."""
    return (base_radius * base_radius + height * height) / (2.0 * height)


def frustum(height, r1, r2):
    """Volume of a cone frustum."""
    return math.pi * height / 3.0 * (r1 * r1 + r1 * r2 + r2 * r2)


def round_edge_cut(radius, r):
    """What rounding the top edge of a cylinder (radius `radius`) with radius r removes: the
    corner between a square and its quarter circle, turned about the axis (Pappus)."""
    area = r * r * (1.0 - math.pi / 4.0)
    centroid = (r / 6.0) / (1.0 - math.pi / 4.0)  # from the quarter circle's centre
    return 2.0 * math.pi * (radius - r + centroid) * area


def slit_area(gap, r_in, r_out):
    """Area of a straight slit `gap` wide cut radially through a flat ring."""

    def part(a):
        return gap / 2.0 * math.sqrt(a * a - gap * gap / 4.0) + a * a * math.asin(gap / (2.0 * a))

    return part(r_out) - part(r_in)


def dome_socket(dk, k, s, t, steps=2000):
    """What a hexagon socket s across the flats, t deep from the top, takes out of a button
    head (a spherical cap dk wide and k high): the socket's walls end where the dome falls
    away, so it is less than hex_area(s) * t. Over each twelfth of the hexagon (polar angle
    phi from a flat's middle, out to (s / 2) / cos(phi)) the depth below the dome is
    integrated in closed form; Simpson's rule takes it round the angle."""
    big = cap_radius(dk / 2.0, k)
    a = big - t  # the socket's floor, measured up from the sphere's centre
    if a >= big:
        return 0.0
    edge = math.sqrt(max(0.0, big * big - a * a))  # where the floor meets the dome

    def radial(rho):
        # integral of (sqrt(R^2 - r^2) - a) r dr from 0 to rho, written without the
        # difference of two cubes of R (a wide, flat dome lost every digit that way)
        rho = min(rho, edge)
        b = math.sqrt(max(0.0, big * big - rho * rho))
        cubes = rho * rho / (big + b) * (big * big + big * b + b * b) / 3.0  # (R^3 - b^3) / 3
        return cubes - a * rho * rho / 2.0

    n = steps if steps % 2 == 0 else steps + 1
    hi = math.pi / 6.0
    h = hi / n
    total = 0.0
    for i in range(n + 1):
        phi = i * h
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        total += w * radial((s / 2.0) / math.cos(phi))
    return 12.0 * total * h / 3.0


def bearing_section(dm):
    """How a bearing is drawn: (ring thickness, ball diameter, number of balls, how deep
    the shields sit below the faces). Fission 180's own proportions (Guess): each ring 0.3 of
    the section, the balls 0.6 of it (they dip into both rings)."""
    section = (dm["D"] - dm["d"]) / 2.0
    ring = 0.3 * section
    ball = min(0.6 * section, 0.85 * dm["B"])
    pitch = (dm["D"] + dm["d"]) / 2.0
    count = max(5, int(math.pi * pitch / (1.5 * ball)))
    return ring, ball, count, 0.1 * dm["B"]


def volume(options):
    """The solid's volume (mm3) with cosmetic threads, worked out by hand from the shapes
    hardware_shapes.py builds; None for the two shapes without a simple formula (a slotted
    pan head, an open bearing)."""
    o = with_defaults(options)
    dm = dims(o["standard"], o["size"], o["variant"])
    kind = o["kind"]
    pi = math.pi
    length = o["length"] if has_length(o["standard"]) else 0.0
    if kind == "nut":
        return (hex_area(dm["s"]) - pi * dm["d"] ** 2 / 4.0) * dm["m"]
    if kind == "washer":
        flat = pi / 4.0 * (dm["d2"] ** 2 - dm["d1"] ** 2)
        if "gap" in dm:
            flat -= slit_area(dm["gap"], dm["d1"] / 2.0, dm["d2"] / 2.0)
        return flat * dm["h"]
    if kind == "insert":
        return pi / 4.0 * (dm["outside"] ** 2 - dm["d"] ** 2) * dm["length"]
    if kind == "magnet":
        return pi / 4.0 * dm["diameter"] ** 2 * dm["thickness"]
    if kind == "oring":
        return 2.0 * pi * pi * ((dm["id"] + dm["cs"]) / 2.0) * (dm["cs"] / 2.0) ** 2
    if kind == "bearing":
        if o["variant"] == "open":
            return None
        ring, _ball, _count, recess = bearing_section(dm)
        whole = pi / 4.0 * (dm["D"] ** 2 - dm["d"] ** 2) * dm["B"]
        groove = pi / 4.0 * ((dm["D"] - 2 * ring) ** 2 - (dm["d"] + 2 * ring) ** 2) * recess
        return whole - 2.0 * groove
    if kind == "ring":
        inner, outer = ring_diameters(dm)
        return pi / 4.0 * (outer**2 - inner**2) * dm["s"] * (1.0 - RING_GAP / 360.0)
    if kind == "pin":
        r, c = dm["d"] / 2.0, dm["c"]
        return pi * r * r * (length - 2.0 * c) + 2.0 * frustum(c, r, r - c)
    if kind == "key":
        b = dm["b"]
        if dm["round_ends"]:
            return (b * (length - b) + pi * b * b / 4.0) * dm["h"]
        return b * length * dm["h"]
    if kind == "standoff":
        if "af" in dm:
            return (hex_area(dm["af"]) - pi * dm["d"] ** 2 / 4.0) * length
        return pi / 4.0 * (dm["d2"] ** 2 - dm["d1"] ** 2) * length
    if kind == "setscrew":
        r = dm["d"] / 2.0
        socket = hex_area(dm["s"]) * socket_depth(o)
        h = point_height(dm, length)
        point = dm["point"]
        if point == "cup":
            return pi * r * r * length - pi / 3.0 * (dm["dv"] / 2.0) ** 2 * h - socket
        if point == "dog":
            return pi * r * r * (length - h) + pi * (dm["dog"] / 2.0) ** 2 * h - socket
        tip = (dm["dp"] if point == "flat" else dm["dt"]) / 2.0
        return pi * r * r * (length - h) + frustum(h, r, tip) - socket
    if kind == "shoulder":
        head = pi * dm["dk"] ** 2 / 4.0 * dm["k"] - hex_area(dm["s"]) * dm["t"]
        return head + pi * dm["d1"] ** 2 / 4.0 * length + pi * dm["d"] ** 2 / 4.0 * dm["b"]
    d, dk, k, head = dm["d"], dm["dk"], dm["k"], dm["head"]
    shank = pi * d * d / 4.0 * length
    if head == "hex":
        return hex_area(dm["af"]) * k + shank
    if head == "pan_ph":
        cross = 2.0 * dm["m"] * dm["b"] * dm["q"] - dm["b"] ** 2 * dm["q"]
        return pi * dk * dk / 4.0 * k - round_edge_cut(dk / 2.0, dm["r"]) - cross + shank
    if head == "pan_sl":
        return None
    socket = hex_area(dm["s"]) * dm["t"]
    if head in ("socket", "low"):
        return pi * dk * dk / 4.0 * k - socket + shank
    if head == "button":
        big = cap_radius(dk / 2.0, k)
        dome = pi * k * k * (3.0 * big - k) / 3.0
        return dome - dome_socket(dk, k, dm["s"], dm["t"]) + shank
    return frustum(k, dk / 2.0, d / 2.0) - socket + pi * d * d / 4.0 * (length - k)


def ring_diameters(dm):
    """(inside, outside) diameter of a retaining ring as it lies free."""
    if dm["external"]:
        return dm["d3"], dm["d3"] + 2.0 * dm["b"]
    return dm["d3"] - 2.0 * dm["b"], dm["d3"]


def extent(options):
    """(bottom, top) of the solid along its own z before the seat and flip are applied."""
    o = with_defaults(options)
    dm = dims(o["standard"], o["size"], o["variant"])
    kind = o["kind"]
    length = o["length"] if has_length(o["standard"]) else 0.0
    if kind == "nut":
        return 0.0, dm["m"]
    if kind == "washer":
        return 0.0, dm["h"]
    if kind == "insert":
        return -dm["length"], 0.0
    if kind == "magnet":
        return -dm["thickness"], 0.0
    if kind == "oring":
        return 0.0, dm["cs"]
    if kind == "bearing":
        return -dm["B"], 0.0
    if kind == "ring":
        return 0.0, dm["s"]
    if kind in ("pin", "setscrew"):
        return -length, 0.0
    if kind == "key":
        return 0.0, dm["h"]
    if kind == "standoff":
        return 0.0, length
    if kind == "shoulder":
        return -length - dm["b"], dm["k"]
    if dm["head"] == "flat":
        return -length, 0.0
    return -length, dm["k"]


# -- search (the dialog's Search box) ------------------------------------------------------------
_METRIC_SIZE = re.compile(r"^m(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?(?:x(\d+(?:\.\d+)?))?$")
_INCH_SIZE = re.compile(r"^(#\d+|\d+/\d+|\d+)-(\d+)$")
_INCH_LENGTH = re.compile(r'^(\d+(?:\.\d+)?|\d+/\d+|\d+-\d+/\d+)(?:"|in|inch)$')
_METRIC_LENGTH = re.compile(r"^(?:x|l)?(\d+(?:\.\d+)?)mm$|^x(\d+(?:\.\d+)?)$")
_SUFFIX = {"zz": "zz", "2z": "zz", "z": "zz", "2rs": "2rs", "rs": "2rs", "open": "open"}


def _words_of(standard):
    s = STANDARDS[standard]
    text = " ".join(
        (s["label"], s["noun"], s["source"], s.get("words", ""), dict(KINDS)[s["kind"]])
    )
    text += " " + s["system"] + (" imperial unified" if s["system"] == "inch" else " iso")
    return set(re.findall(r"[a-z0-9.]+", text.lower()))


def _word_fits(word, words):
    return any(w == word or (len(word) >= 3 and w.startswith(word)) for w in words)


def search(text, limit=40):
    """What the Search box finds: [{"standard", "size", "length" (maybe), "thread" (maybe),
    "variant" (maybe), "label"}], best first. Words name the part ("set screw", "o-ring",
    "bearing", "pan phillips"), the rest its size: "m3", "m3x10", "1/4-20", "#10", "6202",
    "608zz", "-012" or "as568-012", "10x2", a length as "x20", "20mm" or 3/4"."""
    text = (text or "").lower().replace("o-ring", "oring").replace("o ring", "oring")
    text = text.replace("heat-set", "heat set").replace(",", " ").replace("×", "x")
    tokens = [t for t in re.split(r"\s+", text.strip()) if t]
    if not tokens:
        return []
    words, size_keys, wanted = [], [], {}
    for token in tokens:
        metric = _METRIC_SIZE.match(token)
        inch = _INCH_SIZE.match(token)
        if metric:
            size_keys.append(("metric", metric.group(1)))
            for extra in (metric.group(2), metric.group(3)):
                if extra is None:
                    continue
                pitches = [d.pitch for d in thread_tables.designations("iso", metric.group(1))]
                if any(abs(float(extra) - p) < 1e-9 for p in pitches):
                    wanted["pitch"] = float(extra)
                else:
                    wanted["length"] = float(extra)
            continue
        if inch:
            size_keys.append(("inch", inch.group(1)))
            wanted["tpi"] = int(inch.group(2))
            continue
        if token.startswith("as568"):
            token = token[5:].lstrip("-") or "as568"
            if token == "as568":
                words.append("as568")
                continue
        found = _INCH_LENGTH.match(token)
        if found:
            wanted["length"] = _mixed(found.group(1).replace("-", " ")) * INCH
            continue
        found = _METRIC_LENGTH.match(token)
        if found:
            wanted["length"] = float(found.group(1) or found.group(2))
            continue
        bare = token.lstrip("-")
        variant = None
        for suffix, value in _SUFFIX.items():
            stem = bare[: -len(suffix)].rstrip("-")
            if bare.endswith(suffix) and stem and re.match(r"^(\d|m?r\d)", bare):
                variant, bare = value, bare[: -len(suffix)].rstrip("-")
                break
            if token == suffix:
                variant, bare = value, ""
                break
        if variant:
            wanted["variant"] = variant
            if not bare:
                continue
        if re.match(r"^(#?\d[\d./x]*|m?r\d[\d-]*)$", bare):
            size_keys.append(("any", bare))
            continue
        words.append(token)
    results = []
    for standard in STANDARD_ORDER:
        s = STANDARDS[standard]
        have = _words_of(standard)
        if not all(_word_fits(w, have) for w in words):
            continue
        table = s["table"]
        picked = []
        for system, key in size_keys:
            if system not in ("any", s["system"]):
                picked = None
                break
            match = [k for k in table if k.lower() == key or k.lower() == key.zfill(3)]
            if system == "any" and s["kind"] in THREADED_KINDS + ("washer",):
                # a bare number names a thread only with its M or # ("m3", "#10", "1/4")
                match = [k for k in match if "/" in k or k.startswith("#")]
            if not match:
                picked = None
                break
            picked = match
        if picked is None:
            continue
        if not size_keys:
            if not words:
                continue
            picked = sizes(standard) if len(results) == 0 and _narrow(words) else None
            if picked is None:
                picked = [default_size(standard)]
        for size in picked:
            o = {"standard": standard, "size": size}
            if has_length(standard):
                found = lengths(standard, size)
                if "length" in wanted:
                    near = [v for v in found if abs(v - wanted["length"]) < 1e-3]
                    if not near:
                        continue
                    o["length"] = near[0]
                else:
                    o["length"] = default_length(standard, size)
            threads = designations(standard, size)
            if "tpi" in wanted or "pitch" in wanted:
                fit = [
                    d
                    for d in threads
                    if ("tpi" in wanted and abs(INCH / d.pitch - wanted["tpi"]) < 0.05)
                    or ("pitch" in wanted and abs(d.pitch - wanted["pitch"]) < 1e-9)
                ]
                if not fit:
                    continue
                if fit[0] is not threads[0]:
                    o["thread"] = fit[0].label
            if s["kind"] == "bearing" and "variant" in wanted:
                o["variant"] = wanted["variant"]
            o["label"] = name(o)
            results.append(o)
            if len(results) >= limit:
                return results
    return results


def _narrow(words):
    """True when the words name one family only (its every size is then listed)."""
    fits = [k for k in STANDARD_ORDER if all(_word_fits(w, _words_of(k)) for w in words)]
    return len(fits) == 1
