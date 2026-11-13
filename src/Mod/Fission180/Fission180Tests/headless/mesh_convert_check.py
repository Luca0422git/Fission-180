# SPDX-License-Identifier: LGPL-2.1-or-later
"""Convert Mesh built from the mesh's own edges (wave 8, ai-mesh: insert._solid_from_regions)
gives the same solid as the sewing it replaced, and a Plane Cut through many holes is closed
and quick (mesh._region_face, the Uniform fill of a complex cut), in real FreeCAD without a
window. Fission180Tests/unit/test_mesh_convert_freecad.py runs it.

    freecadcmd -c "from Fission180Tests.headless import mesh_convert_check as c; c.main()"
"""

import math
import os
import tempfile
import time

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def _bad(text):
    print("[Fission 180] mesh convert BAD %s" % text, flush=True)


def _plate_mesh(kind="holes", grid=(4, 3), deflection=(0.02, 0.5)):
    import Mesh

    from Fission180Tests.headless import mesh_tools

    folder = tempfile.mkdtemp(prefix="fission180-convert-")
    path = os.path.join(folder, "plate.stl")
    mesh_tools.write_stl(path, kind, deflection, grid=grid)
    return Mesh.Mesh(path)  # (read back as an STL file brings it: single precision)


def _same(new, old, what):
    counts = (len(new.Faces), len(new.Edges), len(new.Vertexes))
    before = (len(old.Faces), len(old.Edges), len(old.Vertexes))
    if counts != before:
        _bad("%s: faces, edges, corners %s, sewn %s" % (what, counts, before))
    if abs(new.Volume - old.Volume) > 1e-7 * old.Volume:
        _bad("%s: volume %.9g, sewn %.9g" % (what, new.Volume, old.Volume))
    if not new.isValid():
        _bad("%s: not a valid solid" % what)


@case
def prismatic_and_faceted_as_sewn():
    from fission180 import insert

    mesh = _plate_mesh()
    tol = max(1e-4, 1e-5 * mesh.BoundBox.DiagonalLength)
    for method in ("Prismatic", "Faceted"):
        began = time.time()
        new = insert._solid_from_regions(mesh, method == "Prismatic", tol)
        took = time.time() - began
        old = insert._sewn_solid(mesh, method, tol)
        _same(new, old, method)
        if method == "Prismatic":
            tops = [
                f for f in new.Faces if f.Surface.TypeId == "Part::GeomPlane"
                and abs(f.CenterOfMass.z - 5) < 1e-6
            ]  # fmt: skip
            if len(tops) != 1 or len(tops[0].Wires) != 13:
                _bad("the top is not one face with its 12 holes: %s" % [len(t.Wires) for t in tops])
        print("[Fission 180] mesh convert %s %.2f s" % (method, took), flush=True)
    solid = insert.solid_from_mesh(mesh, "Prismatic")
    expected = 80 * 60 * 5 - 12 * math.pi * 1.5**2 * 2
    if abs(solid.Volume - expected) > 2e-3 * expected:
        _bad("volume %.3f, the round holes' part %.3f" % (solid.Volume, expected))


@case
def an_open_mesh_is_refused_in_words():
    import Mesh

    from fission180 import insert

    mesh = _plate_mesh(grid=(1, 1))
    points, facets = mesh.Topology
    broken = Mesh.Mesh([[points[i] for i in f] for f in list(facets)[1:]])
    try:
        insert.solid_from_mesh(broken, "Prismatic")
        _bad("an open mesh became a solid")
    except insert.InsertError as exc:
        if "Repair" not in str(exc):
            _bad("the refusal does not say to repair: %s" % exc)


@case
def a_plane_cut_through_many_holes():
    from fission180 import mesh as mesh_mod

    mesh = _plate_mesh(grid=(10, 8))
    expected = 80 * 60 * 4 - 80 * math.pi * 1.5**2 * 1  # the round holes' part, 4 mm high
    for fill in ("Minimal", "Uniform"):
        began = time.time()
        kept, _other, _groups = mesh_mod.plane_cut_mesh(mesh, (0, 0, 4), (0, 0, 1), "Trim", fill)
        took = time.time() - began
        info = mesh_mod.analyze(kept)
        if not info["closed"]:
            _bad("%s: the cut is not closed: %s" % (fill, info))
        elif abs(info["volume"] - expected) > 2e-3 * expected:
            _bad("%s: volume %.3f, expected about %.3f" % (fill, info["volume"], expected))
        if took > 20:
            _bad("%s: a cut through 80 holes took %.1f s" % (fill, took))
        print("[Fission 180] mesh convert cut %s %.2f s" % (fill, took), flush=True)


@case
def a_region_face_whatever_the_loops_winding():
    from fission180 import mesh as mesh_mod

    outer = [(0, 0), (0, 10), (20, 10), (20, 0)]  # clockwise
    hole = [(5, 3), (8, 3), (8, 6), (5, 6)]  # counter-clockwise
    face = mesh_mod._region_face([outer, hole])
    if face is None or abs(face.Area - (200 - 9)) > 1e-9:
        _bad("region face: %s" % (face.Area if face is not None else None))
    if face is not None and face.normalAt(0, 0).z < 0.999:
        _bad("region face faces %s" % face.normalAt(0, 0))


def main():
    done = 0
    for fn in CASES:
        try:
            fn()
            done += 1
        except Exception as exc:
            import traceback

            _bad("%s raised %s\n%s" % (fn.__name__, exc, traceback.format_exc()))
    print("[Fission 180] mesh convert done %d" % done, flush=True)
