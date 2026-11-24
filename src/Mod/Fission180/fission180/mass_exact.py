# SPDX-License-Identifier: LGPL-2.1-or-later
"""Volumes, areas and mass properties of shapes with free-form geometry, measured exactly.

Luca's NREAL AIR HMD benchmark (2026-11-23): OpenCASCADE's default measuring (BRepGProp, what
FreeCAD's Volume, Area, CenterOfMass and MatrixOfInertia use) integrates each face with a
fixed number of points per span of its curves; on a spline wall that is 1e-4 to 3e-4 off,
and differently for the two kinds of the same wall (an extruded sketch spline, a STEP file's
B-spline surface): a rebuilt temple housing read 2903.63 mm3 against the original's 2902.63
mm3 although their faces lie within 0.22 um. FreeCAD has no Python call for OpenCASCADE's
adaptive measuring. Cut into slabs, each face spans less of its splines and the same fixed
integration is exact: a 40 x 6 mm spline wall was 2.7e-4 off in one piece, 2e-11 in four
(0.03 s).

So a shape with free-form geometry (a surface other than plane, cylinder, cone, sphere and
torus, or an edge other than a line or circle) is cut by planes across the longest side of its
box into 4, then 8 (then 16) pieces, until two counts agree. A shape without free-form geometry, a
shape of more than MAX_FACES faces, a cut that fails, or pieces that do not add up to within
1 % of FreeCAD's own number keep FreeCAD's own number. Needs FreeCAD (Part); no Qt.
"""

import time

ANALYTIC_SURFACES = ("Plane", "Cylinder", "Cone", "Sphere", "Toroid")
ANALYTIC_CURVES = ("Line", "LineSegment", "Circle", "ArcOfCircle")
COUNTS = (4, 8, 16)  # pieces tried, until two counts agree
AGREE = 1e-8  # relative (numbers are shown to 6 digits)
MAX_FACES = 400  # (each count is a General Fuse of the whole shape)
SLOW_S = 2.0  # a count that took longer than this is the last one tried
SANE = 0.01  # the pieces must add up to FreeCAD's own number within 1 %


def free_form(shape):
    """The shape has a face or an edge OpenCASCADE's fixed integration does not measure
    exactly."""
    try:
        for face in shape.Faces:
            if type(face.Surface).__name__ not in ANALYTIC_SURFACES:
                return True
        for edge in shape.Edges:
            try:
                if type(edge.Curve).__name__ not in ANALYTIC_CURVES:
                    return True
            except Exception:
                continue  # (a degenerate edge has no curve)
    except Exception:
        return False
    return False


def _worth_it(shape):
    try:
        return (
            not shape.isNull()
            and shape.countElement("Face") <= MAX_FACES
            and free_form(shape)
        )
    except Exception:
        return False


def _planes(shape, count):
    """count - 1 planes across the longest side of the shape's box, evenly spaced, each far
    bigger than the shape."""
    import FreeCAD as App
    import Part

    box = shape.BoundBox
    lengths = (box.XLength, box.YLength, box.ZLength)
    axis = lengths.index(max(lengths))
    size = 2.0 * (1.0 + box.DiagonalLength)
    lo = (box.XMin, box.YMin, box.ZMin)[axis]
    hi = (box.XMax, box.YMax, box.ZMax)[axis]
    normal = App.Vector(*[1.0 if k == axis else 0.0 for k in range(3)])
    out = []
    for i in range(1, count):
        at = App.Vector(box.Center)
        setattr(at, "xyz"[axis], lo + (hi - lo) * i / count)
        plane = Part.makePlane(size, size, App.Vector(0, 0, 0), normal)
        plane.translate(at - plane.CenterOfMass)
        out.append(plane)
    return out


def _split(shape, count):
    """The shape's own pieces, cut by the planes in one General Fuse (a common per slab took
    ten times as long: 2.5 s on a forged lever of 409 faces, 0.25 s this way)."""
    _result, pieces = shape.generalFuse(_planes(shape, count))
    return list(pieces[0])


def _converged(shape, measure, plain):
    """(value, pieces): measure(pieces) of the shape cut into pieces, cut finer until two
    counts agree; (plain, None) when it cannot be done. shape: one solid or one face (the
    General Fuse names the pieces of those, not of a compound's or a shell's)."""
    began = time.perf_counter()
    last = None
    value, pieces = plain, None
    try:
        for count in COUNTS:
            cut = _split(shape, count)
            total = measure(cut)
            if abs(total - plain) > SANE * max(1.0, abs(plain)):
                return plain, None  # (a cut that lost or doubled material)
            value, pieces = total, cut
            if last is not None and abs(total - last) <= AGREE * max(1.0, abs(total)):
                break
            last = total
            if time.perf_counter() - began > SLOW_S:
                break
    except Exception:
        return plain, None
    return value, pieces


def _volumes(pieces):
    return sum(s.Volume for piece in pieces for s in piece.Solids)


def _outside_area(pieces):
    """The pieces' faces without the cuts: a face two pieces share is a cut (measured the same
    on both sides, so taking both away leaves exactly the original faces' area)."""
    seen = {}
    for piece in pieces:
        for face in piece.Faces:
            key = face.hashCode()
            entry = seen.setdefault(key, [face, 0])
            entry[1] += 1
    return sum(face.Area for face, n in seen.values() if n == 1)


def _face_area(face):
    plain = face.Area
    if plain <= 0 or not _worth_it(face):
        return plain
    return _converged(face, lambda pieces: sum(p.Area for p in pieces), plain)[0]


def _solid_area(solid):
    plain = solid.Area
    if plain <= 0 or not _worth_it(solid):
        return plain
    return _converged(solid, _outside_area, plain)[0]


def _solid_volume(solid):
    plain = solid.Volume
    if plain <= 0 or not _worth_it(solid):
        return plain
    return _converged(solid, _volumes, plain)[0]


def volume(shape):
    """The volume of the shape's solids (mm3), exact for free-form ones."""
    try:
        return sum(_solid_volume(s) for s in shape.Solids)
    except Exception:
        return 0.0


def area(shape):
    """The area of the shape's faces (mm2), exact for free-form ones."""
    try:
        kind = shape.ShapeType
        if kind == "Face":
            return _face_area(shape)
        if kind == "Solid":
            return _solid_area(shape)
        solids = shape.Solids
        if solids and sum(len(s.Faces) for s in solids) == len(shape.Faces):
            return sum(_solid_area(s) for s in solids)
        return sum(_face_area(f) for f in shape.Faces)
    except Exception:
        try:
            return shape.Area
        except Exception:
            return 0.0


def _rows(matrix):
    return [
        [matrix.A11, matrix.A12, matrix.A13],
        [matrix.A21, matrix.A22, matrix.A23],
        [matrix.A31, matrix.A32, matrix.A33],
    ]


def solid_properties(solid):
    """{volume, area, center (x, y, z), inertia (3 x 3 rows, mm^5: density 1, about the
    centre, OpenCASCADE's signs)} of one solid, exact for a free-form one."""
    plain = {
        "volume": solid.Volume,
        "area": solid.Area,
        "center": tuple(solid.CenterOfMass),
        "inertia": _rows(solid.MatrixOfInertia),
    }
    if plain["volume"] <= 0 or not _worth_it(solid):
        return plain
    total, pieces = _converged(solid, _volumes, plain["volume"])
    if not pieces or total <= 0:
        return plain
    parts = []
    for piece in pieces:
        for s in piece.Solids:
            v = s.Volume
            if v > 0:
                parts.append((v, s.CenterOfMass, _rows(s.MatrixOfInertia)))
    if not parts:
        return plain
    weight = sum(v for v, _c, _m in parts)
    centre = [sum(v * c[k] for v, c, _m in parts) / weight for k in range(3)]
    inertia = [[0.0] * 3 for _ in range(3)]
    for v, c, m in parts:
        d = [c[k] - centre[k] for k in range(3)]
        dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2]
        for i in range(3):
            for j in range(3):
                # (the parallel axis theorem; the products carry OpenCASCADE's minus sign)
                inertia[i][j] += m[i][j] + v * ((dd if i == j else 0.0) - d[i] * d[j])
    return {
        "volume": total,
        "area": _solid_area(solid),
        "center": tuple(centre),
        "inertia": inertia,
    }
