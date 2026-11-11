# SPDX-License-Identifier: LGPL-2.1-or-later
"""A body's name with its component (fission180/bodies.py clear_name, shown_name, named), in
real FreeCAD without a window; run by Fission180Tests/unit/test_body_names_freecad.py. Prints
"names check BAD <what>" for every failed check and "names check done <n>" at the end.

Bodies are numbered per component, like Fusion's: the design's first body and each
component's first body are all "Body1". The design here: Body1 and Body2 at the top, the
components Bracket (Body1) and Pin (Body1, Body2), and a second component also called Pin
(Body1).
"""

import FreeCAD as App

from fission180 import bodies, components

_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("names check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def main():
    try:
        _run()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        _print(False, "raised %s" % exc)
    print("names check done %d" % _count[0], flush=True)


def _run():
    # as the app sets it at start-up (theme.py): two objects may have the same label
    App.ParamGet("User parameter:BaseApp/Preferences/Document").SetBool("DuplicateLabels", True)
    doc = App.newDocument("body_names")
    top1 = bodies.new_body(doc)
    top2 = bodies.new_body(doc)
    bracket = components.new_component(doc)
    bracket.Label = "Bracket"
    b1 = components.new_body_in(doc, bracket, "Body1")
    pin = components.new_component(doc)
    pin.Label = "Pin"
    p1 = components.new_body_in(doc, pin, "Body1")
    p2 = components.new_body_in(doc, pin, "Body2")
    twin = components.new_component(doc)
    twin.Label = "Pin"
    t1 = components.new_body_in(doc, twin, "Body1")
    doc.recompute()
    labels = [b.Label for b in (top1, top2, b1, p1, p2, t1)]
    _print(
        labels == ["Body1", "Body2", "Body1", "Body1", "Body2", "Body1"],
        "numbered per component (%s)" % labels,
    )
    same_part_name = twin.Label == pin.Label

    _print(bodies.clear_name(top1) == "Body1", "at the top: %s" % bodies.clear_name(top1))
    _print(bodies.clear_name(b1) == "Body1 (Bracket)", "in Bracket: %s" % bodies.clear_name(b1))
    _print(bodies.clear_name(p2) == "Body2 (Pin)", "in Pin: %s" % bodies.clear_name(p2))

    # what a dialog shows
    _print(bodies.shown_name(top1) == "Body1", "shown, top: %s" % bodies.shown_name(top1))
    _print(bodies.shown_name(b1) == "Body1 (Bracket)", "shown, Bracket: %s" % bodies.shown_name(b1))
    shown = bodies.list_names([top1, b1, p1, t1])
    _print(len(set(shown)) == 4, "four bodies called Body1 are told apart (%s)" % shown)
    if same_part_name:
        _print(
            p1.Name in bodies.shown_name(p1) and t1.Name in bodies.shown_name(t1),
            "two components of one name: the object name is added (%s, %s)"
            % (bodies.shown_name(p1), bodies.shown_name(t1)),
        )
    only = bodies.new_body(doc)  # "Body3": nobody else has it
    _print(only.Label == "Body3" and bodies.shown_name(only) == "Body3", "a name of its own")

    # what a name finds
    found, why = bodies.named(doc, "Body1 (Bracket)")
    _print(found == [b1] and not why, "Body1 (Bracket) finds Bracket's body")
    found, why = bodies.named(doc, "Body1")
    _print(found == [top1] and not why, "plain Body1 is the body at the top (%s)" % why)
    found, why = bodies.named(doc, "Body2 (Pin)")
    _print(found == [p2] and not why, "Body2 (Pin)")
    found, why = bodies.named(doc, b1.Name)
    _print(found == [b1] and not why, "by its object name")
    found, why = bodies.named(doc, "Body3")
    _print(found == [only] and not why, "a label only one body has")
    found, why = bodies.named(doc, "Body9")
    _print(not found and "no body called Body9" in why and "Body1 (Bracket)" in why, why)
    found, why = bodies.named(doc, "")
    _print(not found and bool(why), "an empty name: %s" % why)
    if same_part_name:
        found, why = bodies.named(doc, "Body1 (Pin)")
        _print(
            len(found) == 2 and p1.Name in why and t1.Name in why,
            "Body1 (Pin) is two bodies: the answer says what to write (%s)" % why,
        )
    # only bodies inside components share a label: ambiguous, and said so
    doc.removeObject(top1.Name)
    doc.recompute()
    found, why = bodies.named(doc, "Body1")
    _print(
        len(found) >= 2 and "with its component" in why and "Body1 (Bracket)" in why,
        "plain Body1 with no such body at the top: %s" % why,
    )

    # the AI tools take the same names
    from fission180.ai import executor

    _print(executor.resolve(doc, "Body1 (Bracket)") is b1, "the AI tools find Body1 (Bracket)")
    try:
        executor.resolve(doc, "Body1")
        _print(False, "the AI tools refuse an ambiguous Body1")
    except Exception as exc:
        _print("with its component" in str(exc), "the AI tools say what to write: %s" % exc)
    from fission180.ai.ops import core

    builder = core.Builder.attach(doc, top2)
    _print(builder.objects.get("Body1 (Bracket)") is b1, "the step language knows the name too")
    App.closeDocument(doc.Name)
