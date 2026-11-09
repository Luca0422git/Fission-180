# SPDX-License-Identifier: LGPL-2.1-or-later
"""Every body and sketch an AI makes gets a name (Luca, 2026-11-09: "no matter what AI, they
dont automatically name the bodies they make. Can we have a rule that makes it MANDATORY to name
the bodies and sketches it creates?").

A rule in the instructions alone is a wish; this makes it a rule for every AI, whichever app
it talks through (the chat panel, an AI app over MCP, the command line): executor.run notes
the bodies and sketches a call made (their names as FreeCAD gave them, "Body2", "Sketch003"),
tells the AI in the answer to rename them, and refuses its next change to the design until it
has ("rename", "undo" and reading tools still work). A body or sketch counts as named once its
name is no longer the one it was made with.
"""

import os

from .. import log

FREE_TOOLS = ("rename", "undo", "redo")  # what an AI may still call while names are owed
_OWED = {}  # design name -> {object name: the label it was made with}
from .catalog import NAMEABLE, SKETCH_TOOLS  # noqa: E402  (the tools that take a "name")
FORCE = None  # a test of the rule itself: True turns it on whatever the environment says


def enforced():
    """The rule is on for every AI; Fission 180's own test runs (run_tests.sh) drive the tools
    like scripts and turn it off with FISSION180_AI_NAMES=off, except the tests of the rule."""
    if FORCE is not None:
        return bool(FORCE)
    return os.environ.get("FISSION180_AI_NAMES", "").strip().lower() != "off"


def _kind(obj):
    try:
        if obj.TypeId == "PartDesign::Body":
            return "body"
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            return "sketch"
    except Exception:
        pass
    return ""


def snapshot(doc):
    """{object name} of the bodies and sketches of a design (None without a design)."""
    if doc is None:
        return None
    try:
        return {o.Name for o in doc.Objects if _kind(o)}
    except Exception:
        return None


def _alive(doc, name):
    try:
        return doc.getObject(name) is not None
    except Exception:
        return False


def owed(doc):
    """[(object, kind)] still to be named in this design, oldest first."""
    if doc is None:
        return []
    table = _OWED.get(doc.Name, {})
    found = []
    for name in list(table):
        obj = doc.getObject(name) if _alive(doc, name) else None
        if obj is None or obj.Label != table[name]:
            table.pop(name, None)  # undone, deleted, or named: nothing owed
            continue
        found.append((obj, _kind(obj)))
    return sorted(found, key=lambda item: item[0].ID)


def _list(items):
    return ", ".join("%s (a %s)" % (obj.Label, kind) for obj, kind in items)


def refusal(items):
    return (
        "Not done: name what you made first. In Fission 180 every body and sketch an AI makes "
        "must have a name that says what it is (mandatory). Call rename for %s (target: its "
        "id, name: for example \"Base plate\", \"Mounting bracket\", \"Hole pattern sketch\"), "
        "then try this again." % _list(items)
    )


def made_since(doc, before):
    """The bodies and sketches made since `before` (snapshot), oldest first."""
    if doc is None or before is None:
        return []
    try:
        return sorted((o for o in doc.Objects if _kind(o) and o.Name not in before), key=lambda o: o.ID)
    except Exception:
        return []


def apply_name(tool, name, made):
    """The call's own "name" on what it made: the sketch for a sketch tool, the body (bodies,
    numbered) for the others; a sketch a body tool made gets "<name> sketch"."""
    name = (name or "").strip() if isinstance(name, str) else ""
    if not name or tool not in NAMEABLE:
        return
    first = "sketch" if tool in SKETCH_TOOLS else "body"
    mine = [o for o in made if _kind(o) == first]
    for i, obj in enumerate(mine):
        obj.Label = name if i == 0 else "%s %d" % (name, i + 1)
    if first == "body":
        for i, obj in enumerate(o for o in made if _kind(o) == "sketch"):
            obj.Label = "%s sketch" % name if i == 0 else "%s sketch %d" % (name, i + 1)


def note_made(doc, before, made=None):
    """After a change went through: remember the bodies and sketches it made that still have
    the name FreeCAD gave them. Returns the sentence for the answer ("" when none)."""
    if doc is None or before is None:
        return ""
    if made is None:
        made = made_since(doc, before)
    made = [o for o in made if _default_label(o)]
    if not made:
        return ""
    table = _OWED.setdefault(doc.Name, {})
    for obj in made:
        table[obj.Name] = obj.Label
    items = sorted(((o, _kind(o)) for o in made), key=lambda item: item[0].ID)
    log("AI: owes names for %s" % ", ".join(o.Name for o, _ in items))
    return (
        "\nRequired next: name what this made, with rename: %s. Every body and sketch an AI "
        "makes must have a descriptive name; your next change is refused until they have."
        % ", ".join("%s (a %s, id %s)" % (o.Label, k, o.Name) for o, k in items)
    )


def _default_label(obj):
    """True while the label is the one FreeCAD makes up ("Body", "Body2", "Sketch003")."""
    import re

    label = obj.Label or ""
    return bool(re.fullmatch(r"(Body|Sketch) ?\d*", label)) or label == obj.Name


def forget(doc_name):
    _OWED.pop(doc_name, None)
