# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion-style tooltips for every ribbon command (wave 8, tips-ui): the texts and pictures.

Hovering a ribbon command shows a small tooltip at once (its name, `summary`, its key); held
still a moment longer it grows into the expanded one (`picture`, `what`, `steps`, `tips`).
The widget is fission180/tips_ui.py; this package is plain data and pure Python (unit tested:
Fission180Tests/unit/test_tips.py).

One data module per ribbon tab family, each `TIPS = {"<command id>": {...}}`:

    solid, surface                        (builder tips-solid)
    sketch, drawing, utilities            (tips-sketch-drawing)
    mesh, sheet_metal, plastic,           (tips-workspaces)
    simulation, manufacture, animation

A command id is the first command name of a ribbon item (ribbon_config: "Fission180_Fillet",
or the first of a tuple); one that appears in several tabs has one entry, in the module of
the tab it appears in first (TABS order: SOLID before SURFACE before the rest). An entry has
exactly these keys:

    "summary"  one sentence, at most 110 characters (the small tooltip)
    "what"     what it does and when to use it, 1 to 3 sentences, at most 400 characters
    "steps"    2 to 6 short steps, each at most 120 characters ("Select the edges to round.")
    "tips"     0 to 3 short hints, each at most 160 characters (a modifier key, a common
               mistake, a related tool)
    "picture"  a file name in fission180/icons/tips/ (PNG, 320 x 200, at most 45 KB), made by
               tools/fission180/tip_pictures_<module>.py (docs/fission180/dev/tip-pictures.md)

get(command_id) and all() give the entries; problems() says what is wrong with one (the unit
test's yardstick). A module that is missing or broken is skipped: a command without an entry
keeps its plain tooltip.
"""

import importlib
import importlib.util
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the fission180 package
PICTURE_DIR = os.path.join(ROOT, "icons", "tips")

MODULES = (
    "solid",
    "surface",
    "sketch",
    "drawing",
    "utilities",
    "mesh",
    "sheet_metal",
    "plastic",
    "simulation",
    "manufacture",
    "animation",
)
# ribbon tab id (ribbon_config.TABS) -> the data module its commands' tooltips live in
TAB_MODULES = {
    "solid": "solid",
    "surface": "surface",
    "mesh": "mesh",
    "sheet_metal": "sheet_metal",
    "flat_pattern": "sheet_metal",
    "plastic": "plastic",
    "utilities": "utilities",
    "sketch": "sketch",
    "drawing": "drawing",
    "sim_setup": "simulation",
    "sim_results": "simulation",
    "cam_milling": "manufacture",
    "anim_animation": "animation",
}

KEYS = ("summary", "what", "steps", "tips", "picture")
SUMMARY_MAX = 110
WHAT_MAX = 400
WHAT_SENTENCES = (1, 3)
STEPS = (2, 6)
STEP_MAX = 120
TIPS = (0, 3)
TIP_MAX = 160
PICTURE_SIZE = (320, 200)
PICTURE_BYTES = 45 * 1024

_STATE = {"tips": None, "errors": [], "owners": {}}


# -- the ribbon's commands ---------------------------------------------------------------------
def command_id(entry):
    """The id a ribbon item's tooltip is filed under: its first command name ("Name#2"
    without the #2), or None for an item without a command (greyed: not in Fission 180 yet)."""
    if not entry:
        return None
    command = entry.get("command")
    if not command:
        return None
    first = command if isinstance(command, str) else (command[0] if command else None)
    if not first or first.startswith("__"):
        return None
    return first.split("#")[0]


def ribbon_commands(config=None):
    """Every command of the ribbon's tabs, once, in TABS order: [(command id, label, tab id,
    data module)]. The data module is the one of the first tab it appears in."""
    if config is None:
        from .. import ribbon_config as config
    out, seen = [], set()
    for tab in config.TABS:
        module = TAB_MODULES.get(tab["id"])
        for grp in tab["groups"]:
            for entry in config.iter_items(grp["items"]):
                ident = command_id(entry)
                if ident is None or ident in seen:
                    continue
                seen.add(ident)
                out.append((ident, entry["label"], tab["id"], module))
    return out


# -- checking an entry -------------------------------------------------------------------------
def _sentences(text):
    """How many sentences a text has (ends of sentence: . ! ? followed by a space or the end;
    "e.g." and numbers like 0.5 are not ends)."""
    count = 0
    clean = text.replace("e.g.", "eg").replace("i.e.", "ie").replace("etc.", "etc")
    for i, char in enumerate(clean):
        if char in ".!?" and (i + 1 == len(clean) or clean[i + 1] in " \n"):
            count += 1
    return count or (1 if clean.strip() else 0)


def picture_info(path):
    """(width, height, bytes) of a PNG file, read from its header (no Pillow), or None when
    it is missing or not a PNG."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            head = handle.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", head[16:24])
    return (width, height, size)


def picture_path(tip_or_name):
    """The picture file of an entry (or a picture's file name), "" for none."""
    name = tip_or_name.get("picture", "") if isinstance(tip_or_name, dict) else tip_or_name
    if not name or not isinstance(name, str):
        return ""
    return os.path.join(PICTURE_DIR, os.path.basename(name))


def problems(ident, tip, check_picture=True):
    """What is wrong with an entry, as plain sentences ([] when it is complete)."""
    out = []
    if not isinstance(tip, dict):
        return ["%s: the entry is not a dict" % ident]
    missing = [k for k in KEYS if k not in tip]
    extra = [k for k in tip if k not in KEYS]
    if missing:
        out.append("%s: missing %s" % (ident, ", ".join(missing)))
    if extra:
        out.append("%s: unknown keys %s" % (ident, ", ".join(sorted(extra))))

    def text(key, limit):
        value = tip.get(key)
        if key not in tip:
            return None
        if not isinstance(value, str) or not value.strip():
            out.append("%s: %s is empty or not text" % (ident, key))
            return None
        if len(value) > limit:
            out.append("%s: %s has %d characters (at most %d)" % (ident, key, len(value), limit))
        if value != value.strip() or "  " in value:
            out.append("%s: %s has extra spaces" % (ident, key))
        return value

    summary = text("summary", SUMMARY_MAX)
    if summary is not None and _sentences(summary) != 1:
        out.append("%s: summary is %d sentences (one)" % (ident, _sentences(summary)))
    what = text("what", WHAT_MAX)
    if what is not None:
        n = _sentences(what)
        if not WHAT_SENTENCES[0] <= n <= WHAT_SENTENCES[1]:
            out.append("%s: what is %d sentences (1 to 3)" % (ident, n))
    for key, (low, high), limit in (("steps", STEPS, STEP_MAX), ("tips", TIPS, TIP_MAX)):
        if key not in tip:
            continue
        items = tip[key]
        if not isinstance(items, (list, tuple)):
            out.append("%s: %s is not a list" % (ident, key))
            continue
        if not low <= len(items) <= high:
            out.append("%s: %d %s (%d to %d)" % (ident, len(items), key, low, high))
        for i, item in enumerate(items):
            if not isinstance(item, str) or not item.strip():
                out.append("%s: %s %d is empty or not text" % (ident, key, i + 1))
            elif len(item) > limit:
                out.append(
                    "%s: %s %d has %d characters (at most %d)"
                    % (ident, key, i + 1, len(item), limit)
                )
    name = tip.get("picture")
    if "picture" in tip:
        if not isinstance(name, str) or not name.endswith(".png") or os.path.basename(name) != name:
            out.append("%s: picture must be a plain .png file name, not %r" % (ident, name))
        elif check_picture:
            info = picture_info(picture_path(name))
            if info is None:
                out.append("%s: picture %s is missing (or not a PNG)" % (ident, name))
            else:
                width, height, size = info
                if (width, height) != PICTURE_SIZE:
                    out.append(
                        "%s: picture %s is %dx%d (%dx%d)"
                        % ((ident, name, width, height) + PICTURE_SIZE)
                    )
                if size > PICTURE_BYTES:
                    out.append(
                        "%s: picture %s is %d bytes (at most %d)"
                        % (ident, name, size, PICTURE_BYTES)
                    )
    return out


# -- where a tooltip goes (tips_ui.py; pure, unit tested) -----------------------------------------
GAP = 4  # pixels between a tooltip and what it belongs to


def place(anchor, size, screen, beside=False, gap=GAP):
    """Where a tooltip of `size` (w, h) goes for `anchor` (x, y, w, h, screen pixels) inside
    `screen` (the available area, x, y, w, h): under it, or above when there is no room
    below (a ribbon button); beside=True: to its right, or its left when there is no room (a
    drop-down menu's row, the anchor being the whole menu's width on that row, so the menu
    stays uncovered). Always inside the screen. Returns (x, y)."""
    ax, ay, aw, ah = anchor
    w, h = size
    sx, sy, sw, sh = screen
    right, bottom = sx + sw, sy + sh
    if beside:
        x = ax + aw + gap
        if x + w > right:
            x = ax - gap - w
        y = ay
    else:
        x = ax
        y = ay + ah + gap
        if y + h > bottom:
            y = ay - gap - h
    x = max(sx, min(x, right - w))
    y = max(sy, min(y, bottom - h))
    return (int(x), int(y))


def numbered(steps):
    """The steps as the expanded tooltip writes them: "1. Select ...", one per line."""
    return "\n".join("%d. %s" % (i + 1, step) for i, step in enumerate(steps or []))


def bulleted(hints):
    return "\n".join("\u2022 %s" % hint for hint in hints or [])


# -- loading -----------------------------------------------------------------------------------
def _load():
    tips, errors, owners = {}, [], {}
    for name in MODULES:
        full = "%s.%s" % (__name__, name)
        try:
            if importlib.util.find_spec(full) is None:
                continue  # (not written yet)
            module = importlib.import_module(full)
        except Exception as exc:
            errors.append("tips/%s.py did not load: %s" % (name, exc))
            continue
        data = getattr(module, "TIPS", None)
        if not isinstance(data, dict):
            errors.append("tips/%s.py has no TIPS dict" % name)
            continue
        for ident, tip in data.items():
            if ident in tips:
                errors.append(
                    "%s has entries in tips/%s.py and tips/%s.py (kept the first)"
                    % (ident, owners[ident], name)
                )
                continue
            tips[ident] = tip
            owners[ident] = name
    _STATE.update(tips=tips, errors=errors, owners=owners)
    if errors:
        try:
            from .. import log

            for line in errors:
                log("tooltips: %s" % line)
        except Exception:
            pass
    return tips


def _tips():
    if _STATE["tips"] is None:
        _load()
    return _STATE["tips"]


def reload():
    """Read the data modules again (after a module was changed)."""
    import sys

    for name in MODULES:
        sys.modules.pop("%s.%s" % (__name__, name), None)
    _STATE["tips"] = None
    return _tips()


def get(ident):
    """The entry of a command id (a copy), or None when it has none. A copy, with
    "picture_path" added: the picture's full path ("" when the file is missing)."""
    tip = _tips().get(ident)
    if not isinstance(tip, dict):
        return None
    out = dict(tip)
    path = picture_path(tip)
    out["picture_path"] = path if path and os.path.isfile(path) else ""
    return out


def for_entry(entry):
    """The entry of a ribbon item (ribbon_config.item), or None."""
    ident = command_id(entry)
    return get(ident) if ident else None


def all():  # noqa: A001  (the brief's name: tips.all())
    """Every entry: {command id: entry} (copies)."""
    return {ident: dict(tip) for ident, tip in _tips().items() if isinstance(tip, dict)}


def owner(ident):
    """The data module ("solid", ...) an entry was read from, or ""."""
    _tips()
    return _STATE["owners"].get(ident, "")


def load_errors():
    """What went wrong reading the data modules (plain sentences)."""
    _tips()
    return list(_STATE["errors"])


def report(config=None, check_picture=True):
    """Every ribbon command against the data: {"missing": [(id, label, tab, module)],
    "problems": [sentences], "misplaced": [(id, found in, belongs in)], "unknown": [ids of
    entries no ribbon command has]}."""
    commands = ribbon_commands(config)
    data = _tips()
    missing, faults, misplaced = [], [], []
    for ident, label, tab, module in commands:
        tip = data.get(ident)
        if tip is None:
            missing.append((ident, label, tab, module))
            continue
        faults += problems(ident, tip, check_picture)
        found = _STATE["owners"].get(ident, "")
        if module and found and found != module:
            misplaced.append((ident, found, module))
    known = {c[0] for c in commands}
    unknown = sorted(i for i in data if i not in known)
    return {
        "missing": missing,
        "problems": faults,
        "misplaced": misplaced,
        "unknown": unknown,
        "errors": load_errors(),
    }
