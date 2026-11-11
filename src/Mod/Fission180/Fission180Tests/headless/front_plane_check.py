# SPDX-License-Identifier: LGPL-2.1-or-later
"""One direction rule on the Front plane (wave 7 follow-up, builder extrude-2), in real
FreeCAD without a window; run by Fission180Tests/unit/test_front_plane_freecad.py. Prints
"front check BAD <what>" for every failed check and "front check done <n>" at the end.

Fusion's Front plane looks to +Y, FreeCAD's XZ plane to -Y. A Box, Cylinder, Coil or Offset
Plane made in its dialog notes that it counts Fusion's way ("front" in its options / values);
one made before, or from code without the note (the AI tools, the golden models, scripts),
counts FreeCAD's way as it always did. Numbers by hand:

solids    a box 4 x 5 x 10 at (2, 3), a cylinder d 4 x 10 at (20, 3) and a coil 30 high on
          each origin plane, without and with the note: only on the Front plane the note
          turns them over to +Y (the box then lies at z -8..-3: Fusion's sketch y is -Z
          there); read back and edited, each keeps its side
planes    an Offset Plane of 10 from each origin plane, without and with the note, and a
          second one offset 10 from it: +10 / +20 along Fusion's normal with the note; a
          formula typed for the distance is read back as typed
ai        the extrude step of the AI tools and golden models counts along FreeCAD's normal
          (-Y on XZ), also on a sketch that a person's Extrude marked Fusion's way: One
          Side 5, Two Sides 3 / 7 and a Start offset build the same solid on both
"""

import FreeCAD as App

from fission180 import coil, construct, extrude, primitives

V = App.Vector
_count = [0]
ROLES = (("XY_Plane", 2), ("XZ_Plane", 1), ("YZ_Plane", 0))


def _print(ok, what):
    _count[0] += 1
    print("front check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _span(shape, axis):
    b = shape.BoundBox
    lo = (b.XMin, b.YMin, b.ZMin)[axis]
    hi = (b.XMax, b.YMax, b.ZMax)[axis]
    return round(lo, 3), round(hi, 3)


def _doc(name):
    doc = App.newDocument(name)
    body = doc.addObject("PartDesign::Body", "Body")
    planes = {getattr(o, "Role", ""): o for o in body.Origin.OutList}
    return doc, body, planes


def _fusion_way(role, noted):
    """True when a step on this plane lies on the other side than FreeCAD's normal."""
    return noted and role == "XZ_Plane"


def solids():
    doc, body, planes = _doc("front_solids")
    for role, axis in ROLES:
        ref = (planes[role], "")
        for noted in (False, True):
            tag = "%s%s" % (role[:2], ", noted" if noted else "")
            # FreeCAD's normal is +Z, -Y, +X: 10 along it is 0..10 on Z and X, -10..0 on Y
            plain = (-10.0, 0.0) if role == "XZ_Plane" else (0.0, 10.0)
            want = (0.0, 10.0) if _fusion_way(role, noted) else plain
            options = {"x": 2.0, "y": 3.0, "length": 4.0, "width": 5.0, "height": 10.0}
            options["operation"] = "new_body"
            if noted:
                options["front"] = True
            box = primitives.make("box", ref, options)
            doc.recompute()
            _print(_span(box.Shape, axis) == want, "box on %s: %s" % (tag, _span(box.Shape, axis)))
            _print(abs(box.Shape.Volume - 200.0) < 1e-6, "box on %s: 200 mm3" % tag)
            if role == "XZ_Plane":
                # in the plane: FreeCAD's sketch y is +Z (3..8), Fusion's is -Z (-8..-3)
                side = (-8.0, -3.0) if noted else (3.0, 8.0)
                _print(_span(box.Shape, 2) == side, "box on %s: z %s" % (tag, _span(box.Shape, 2)))
            tool = primitives.tool_shape("box", ref, options)
            _print(
                _span(tool, axis) == want, "box on %s: its preview solid lies the same way" % tag
            )
            _kind, _ref, back = primitives.read(box)
            _print(
                bool(back.get("front")) == noted and abs(back["height"] - 10.0) < 1e-9,
                "box on %s: read back (height %s, noted %s)"
                % (tag, back["height"], back.get("front")),
            )
            primitives.update(box, options=dict(back, height=15.0))
            doc.recompute()
            longer = tuple(v * 1.5 for v in want)
            _print(
                _span(box.Shape, axis) == longer,
                "box on %s: a height of 15 keeps its side %s" % (tag, _span(box.Shape, axis)),
            )
            options = {"x": 20.0, "y": 3.0, "diameter": 4.0, "height": 10.0}
            options["operation"] = "new_body"
            if noted:
                options["front"] = True
            cyl = primitives.make("cylinder", ref, options)
            doc.recompute()
            _print(
                _span(cyl.Shape, axis) == want, "cylinder on %s: %s" % (tag, _span(cyl.Shape, axis))
            )
            options = dict(coil.DEFAULTS)
            options.update(x=40.0, y=0.0, height=30.0, revolutions=3.0, operation="new_body")
            if noted:
                options["front"] = True
            spring = coil.make(ref, options)
            doc.recompute()
            lo, hi = _span(spring.Shape, axis)
            up = (hi > 30.0 and lo > -5.0) if want[1] > 0 else (lo < -30.0 and hi < 5.0)
            _print(
                up, "coil on %s rises %s (%s .. %s)" % (tag, "+" if want[1] > 0 else "-", lo, hi)
            )
    bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    _print(not bad, "no step in error (%s)" % bad)
    App.closeDocument(doc.Name)


def planes():
    doc, body, origin = _doc("front_planes")
    for role, axis in ROLES:
        for noted in (False, True):
            tag = "%s%s" % (role[:2], ", noted" if noted else "")
            sign = -1.0 if role == "XZ_Plane" and not noted else 1.0
            values = {"distance": 10.0}
            if noted:
                values["front"] = True
            first = construct.make(body, "OffsetPlane", [(origin[role], "")], values)
            doc.recompute()
            at = "xyz"[axis]
            got = round(getattr(first.Placement.Base, at), 6)
            _print(got == 10.0 * sign, "offset plane 10 from %s lies at %s %g" % (tag, at, got))
            read = construct.read(first)
            _print(
                abs(read[3]["distance"] - 10.0) < 1e-9 and bool(read[3].get("front")) == noted,
                "offset plane from %s reads 10 back (%s)" % (tag, read[3]),
            )
            second = construct.make(body, "OffsetPlane", [(first, "")], values)
            doc.recompute()
            got = round(getattr(second.Placement.Base, at), 6)
            _print(got == 20.0 * sign, "a plane 10 from that one lies at %s %g" % (at, got))
            _print(
                extrude.is_front_plane(second) == (role == "XZ_Plane"),
                "a plane offset from %s is %sa Front plane"
                % (tag, "" if role == "XZ_Plane" else "not "),
            )
            key, refs, points, values_, formulas = construct.read(first)
            construct.update(first, key, refs, values_, points, {"distance": "4 mm + 3 mm"})
            doc.recompute()
            got = round(getattr(first.Placement.Base, at), 6)
            _print(got == 7.0 * sign, "a formula 4 mm + 3 mm puts it at %s %g" % (at, got))
            read = construct.read(first)
            text = (read[4].get("distance") or "").replace(" ", "")
            _print(
                text == "4mm+3mm" and abs(read[3]["distance"] - 7.0) < 1e-9,
                "the formula reads back as typed (%r, %s)"
                % (read[4].get("distance"), read[3]["distance"]),
            )
    bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    _print(not bad, "no plane in error (%s)" % bad)
    App.closeDocument(doc.Name)


def ai():
    from fission180.ai.ops import core

    for marked in (False, True):
        tag = "a sketch marked Fusion's way" if marked else "a plain sketch"
        doc = App.newDocument("front_ai_%d" % marked)
        builder = core.Builder(doc)
        cases = (
            ("one", {"distance": 5}, (-5.0, 0.0)),
            ("two", {"direction": "two_sides", "distance": 3, "distance2": 7}, (-3.0, 7.0)),
            ("off", {"distance": 5, "start": "offset", "start_offset": 2}, (-7.0, -2.0)),
            ("flip", {"distance": 5, "flip": True}, (0.0, 5.0)),
        )
        for i, (name, more, want) in enumerate(cases):
            x0 = 20.0 * i
            sketch = {"op": "sketch", "id": "s_" + name, "plane": "XZ"}
            sketch["geometry"] = [{"rect": [x0, 0, x0 + 10, 10]}]
            builder.run(sketch)
            doc.recompute()
            sk = builder.objects["s_" + name]
            if marked:
                _print(extrude.adopt_fusion_side(sk), "%s: marked" % name)
                _print(extrude.fusion_side(sk) == -1.0, "%s: it counts Fusion's way now" % name)
            step = {"op": "extrude", "id": "e_" + name, "profile": "s_" + name}
            step["operation"] = "new_body"
            step.update(more)
            builder.run(step)
            doc.recompute()
            feature = builder.objects["e_" + name]
            got = _span(feature.Shape, 1)
            _print(
                got == want,
                "the AI's extrude (%s) on %s: y %s, expected %s" % (name, tag, got, want),
            )
        App.closeDocument(doc.Name)


def main():
    for case in (solids, planes, ai):
        try:
            case()
        except Exception as exc:
            import traceback

            traceback.print_exc()
            _print(False, "%s raised %s" % (case.__name__, exc))
    print("front check done %d" % _count[0], flush=True)
