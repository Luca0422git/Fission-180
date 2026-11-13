# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltip pictures of the MESH tab (wave 8, builder tips-workspaces):
tools/fission180/make_tip_pictures.sh mesh [picture ...].

Each picture is a mesh body (as Insert Mesh makes one) and the MESH step the command makes
(fission180/mesh.py: mesh.new_step, the same step objects the dialogs make and compute), shown
before and after; faces the step made or works on are drawn in the selection blue, triangles
are shown where the tool is about them (Flat Lines). Face groups show in their own colours,
as Fission 180 draws them."""

import math

import tip_pictures as tp
import tip_pictures_workspaces as ws


# -- demo meshes -------------------------------------------------------------------------------
def part_shape():
    """A block with a round boss and rounded top edges: what a scanned part looks like."""
    import FreeCAD as App
    import Part

    block = Part.makeBox(40, 30, 12)
    top = [
        e
        for e in block.Edges
        if abs(e.BoundBox.ZMin - 12) < 1e-6 and abs(e.BoundBox.ZMax - 12) < 1e-6
    ]
    block = block.makeFillet(3, top)
    boss = Part.makeCylinder(7, 8, App.Vector(20, 15, 11))
    return block.fuse(boss).removeSplitter()


def triangles(shape, surface=0.08, angle=12.0):
    from fission180 import mesh

    found, _groups = mesh.tessellate_shape(shape, surface, angle)
    return found


def fine_part():
    """The part with even, small triangles (as a scan has): a brush pick looks round."""
    from fission180 import mesh

    found, _groups = mesh.tessellate_shape(part_shape(), 0.08, 12.0, 2.0)
    return found


def near(point, radius):
    """A test for facets_where: centres within `radius` of `point`."""
    target = _v(*point)
    return lambda c: (c - target).Length < radius


def mesh_body(found, label="Scan", lines=False):
    """A mesh body as Insert Mesh makes it."""
    from fission180 import insert

    obj = insert.make_mesh_body(tp.doc(), found, "", label=label)
    tp.recompute()
    show_lines(obj, lines)
    return obj


def show_lines(obj, on=True):
    try:
        obj.ViewObject.DisplayMode = "Flat Lines" if on else "Shaded"
    except Exception:
        pass


def step(kind, source, **values):
    """A MESH step on `source`, as the command's dialog makes it, computed."""
    from fission180 import mesh

    obj = mesh.new_step(tp.doc(), kind, source)
    for name, value in values.items():
        setattr(obj, name, value)
    tp.recompute()
    mesh.apply_colours(obj)
    tp.settle()
    return obj


def facets_where(found, test):
    """Indexes of the triangles whose centre passes test(centre)."""
    import FreeCAD as App

    out = []
    for i, facet in enumerate(found.Facets):
        pts = facet.Points
        centre = App.Vector(
            sum(p[0] for p in pts) / 3.0, sum(p[1] for p in pts) / 3.0, sum(p[2] for p in pts) / 3.0
        )
        if test(centre):
            out.append(i)
    return out


def centres(found, indexes):
    import FreeCAD as App

    out = []
    for i in indexes:
        pts = found.Facets[i].Points
        out.append(
            App.Vector(
                sum(p[0] for p in pts) / 3.0,
                sum(p[1] for p in pts) / 3.0,
                sum(p[2] for p in pts) / 3.0,
            )
        )
    return out


def marker(found, indexes, name="TipMarks"):
    """A hidden object holding the given triangles as faces: passed to tp.render's highlight,
    they are drawn in the selection blue over the mesh."""
    import Mesh
    import Part

    piece = Mesh.Mesh([found.Facets[i].Points for i in indexes])
    shape = Part.Shape()
    shape.makeShapeFromMesh(piece.Topology, 0.01)
    obj = tp.doc().addObject("Part::Feature", name)
    obj.Shape = shape
    obj.ViewObject.Visibility = False
    return obj


def mark(found, indexes, name="TipMarks"):
    """{marker: its face names} for tp.render's highlight."""
    if not indexes:
        return {}
    obj = marker(found, indexes, name)
    return {obj: ["Face%d" % (i + 1) for i in range(len(obj.Shape.Faces))]}


def new_triangles(before, after):
    """Indexes of `after`'s triangles whose centre lies on none of `before`'s triangles'
    centres (what a step added: a filled hole, a cap)."""
    seen = set()
    for c in centres(before, range(before.CountFacets)):
        seen.add((round(c.x, 3), round(c.y, 3), round(c.z, 3)))
    out = []
    for i, c in enumerate(centres(after, range(after.CountFacets))):
        if (round(c.x, 3), round(c.y, 3), round(c.z, 3)) not in seen:
            out.append(i)
    return out


def result(obj):
    from fission180 import mesh

    return mesh.global_mesh(obj)


def plane_shape(origin, normal, size):
    """A square of the given size on a plane (a stand-in for the plane the cut is on)."""
    import FreeCAD as App
    import Part

    n = App.Vector(*normal)
    n.normalize()
    helper = App.Vector(1, 0, 0) if abs(n.x) < 0.9 else App.Vector(0, 1, 0)
    u = n.cross(helper)
    u.normalize()
    v = n.cross(u)
    o = App.Vector(*origin)
    h = size / 2.0
    pts = [o + u * a + v * b for a, b in ((-h, -h), (h, -h), (h, h), (-h, h), (-h, -h))]
    return Part.Face(Part.makePolygon(pts))


def show_plane(origin, normal, size):
    obj = tp.doc().addObject("Part::Feature", "TipPlane")
    obj.Shape = plane_shape(origin, normal, size)
    obj.ViewObject.ShapeColor = (0.30, 0.62, 0.95)
    obj.ViewObject.Transparency = 60
    tp.recompute()
    return obj


# -- CREATE ------------------------------------------------------------------------------------
@tp.picture("mesh_tessellate.png")
def tessellate():
    tp.new_design("Part")
    feature = tp.doc().addObject("Part::Feature", "Part")
    feature.Shape = part_shape()
    tp.recompute()
    tp.camera()
    before = tp.render()
    made = step("Tessellate", feature, Refinement="Low")
    show_lines(made)
    tp.hide(feature)
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_section_sketch.png")
def section_sketch():
    import FreeCAD as App

    from fission180 import mesh_cut_ui

    tp.new_design("Scan")
    body = mesh_body(triangles(part_shape()))
    tp.camera()
    plane = show_plane((20, 15, 6), (0, 0, 1), 46)
    before = tp.render()
    tp.doc().removeObject(plane.Name)
    frame = App.Placement(App.Vector(0, 0, 6), App.Rotation())
    sketch = mesh_cut_ui.make_section_sketch(tp.doc(), body, frame, None)
    tp.recompute()
    edges = ["Edge%d" % (i + 1) for i in range(len(sketch.Shape.Edges))]
    try:
        body.ViewObject.Transparency = 55
    except Exception:
        pass
    after = tp.render(highlight={sketch: edges})
    return tp.before_after(before, after)


# -- PREPARE -----------------------------------------------------------------------------------
@tp.picture("mesh_create_face_group.png")
def create_face_group():
    tp.new_design("Scan")
    found = fine_part()
    body = mesh_body(found)
    chosen = facets_where(found, near((32, 8, 12), 6.0))
    tp.camera()
    before = tp.render(highlight=mark(found, chosen))
    step("MeshCreateFaceGroup", body, Picks=centres(found, chosen))
    after = tp.render()
    return tp.before_after(before, after)


def _v(x, y, z):
    import FreeCAD as App

    return App.Vector(x, y, z)


@tp.picture("mesh_face_groups.png")
def face_groups():
    tp.new_design("Scan")
    body = mesh_body(triangles(part_shape()))
    tp.camera()
    before = tp.render()
    step("MeshFaceGroups", body, Method="Fast")
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_combine_face_groups.png")
def combine_face_groups():
    tp.new_design("Scan")
    body = mesh_body(triangles(part_shape()))
    grouped = step("MeshFaceGroups", body, Method="Fast")
    found = result(grouped)
    # the boss's round side and its top: two groups that touch
    side = facets_where(found, lambda c: c.z > 12.5 and c.z < 18.5)
    top = facets_where(found, lambda c: c.z > 18.9)
    picks = centres(found, side[:1] + top[:1])
    tp.camera()
    before = tp.render(highlight=mark(found, side + top))
    step("MeshCombineFaceGroups", grouped, Picks=picks)
    after = tp.render()
    return tp.before_after(before, after)


def holed(found, count=3):
    """The mesh with a few patches of triangles taken out (holes, as a bad scan has)."""
    import Mesh

    spots = [_v(8, 8, 12), _v(32, 22, 12), _v(40, 15, 6)][:count]
    keep = []
    for i, c in enumerate(centres(found, range(found.CountFacets))):
        if all((c - s).Length > 4.0 for s in spots):
            keep.append(found.Facets[i].Points)
    return Mesh.Mesh(keep)


@tp.picture("mesh_repair.png")
def repair():
    tp.new_design("Scan")
    broken = holed(triangles(part_shape()))
    body = mesh_body(broken)
    tp.camera()
    before = tp.render()
    fixed = step("MeshRepair", body, RepairType="Close Holes")
    after = tp.render(highlight=mark(result(fixed), new_triangles(broken, result(fixed))))
    return tp.before_after(before, after)


# -- MODIFY ------------------------------------------------------------------------------------
@tp.picture("mesh_remesh.png")
def remesh():
    tp.new_design("Scan")
    body = mesh_body(triangles(part_shape(), 0.3, 30), lines=True)
    tp.camera()
    before = tp.render()
    made = step("MeshRemesh", body, RemeshType="Uniform", Density=0.12)
    show_lines(made)
    after = tp.render()
    return tp.before_after(before, after)


def sphere(radius=15, sampling=50):
    import Mesh

    return Mesh.createSphere(radius, sampling)


@tp.picture("mesh_reduce.png")
def reduce():
    tp.new_design("Scan")
    body = mesh_body(sphere(15, 40), lines=True)
    tp.camera()
    before = tp.render()
    made = step("MeshReduce", body, Target="Proportion", Proportion=12.0)
    show_lines(made)
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_plane_cut.png")
def plane_cut():
    tp.new_design("Scan")
    found = triangles(part_shape())
    body = mesh_body(found)
    tp.camera()
    plane = show_plane((20, 15, 9), (0, 0, 1), 46)
    before = tp.render()
    tp.doc().removeObject(plane.Name)
    cut = step(
        "MeshPlaneCut",
        body,
        Plane=(_xy_plane(), [""]),
        Distance=9.0,
        CutType="Trim",
        FillType="Uniform",
    )
    after = tp.render(highlight=mark(result(cut), _cap(result(cut), 9.0)))
    return tp.before_after(before, after)


def _xy_plane():
    for obj in tp.doc().Objects:
        if getattr(obj, "Role", "") == "XY_Plane":
            return obj
    raise RuntimeError("no XY plane")


def _cap(found, z):
    return facets_where(found, lambda c: abs(c.z - z) < 1e-3)


@tp.picture("mesh_shell.png")
def shell():
    """The hollowed body drawn see-through: its new inside wall in blue."""
    import Part

    tp.new_design("Scan")
    found = triangles(Part.makeBox(40, 30, 20))
    body = mesh_body(found)
    tp.camera()
    before = tp.render()
    hollow = step("MeshShell", body, Thickness=3.0)
    inside = result(hollow)
    inner = new_triangles(found, inside)
    if not inner:
        from fission180 import mesh

        raise RuntimeError("the shell made no inside wall: %s" % mesh.problem(hollow))
    try:
        hollow.ViewObject.Transparency = 60
    except Exception:
        pass
    after = tp.render(highlight=mark(inside, inner))
    return tp.before_after(before, after)


def noisy(radius=15, sampling=40, amount=0.05, seed=3):
    import random

    import Mesh

    from fission180 import mesh

    rng = random.Random(seed)
    points, facets = mesh.topology(Mesh.createSphere(radius, sampling))
    moved = [tuple(c * (1 + rng.uniform(-amount, amount)) for c in p) for p in points]
    return mesh.from_topology(moved, facets)


@tp.picture("mesh_smooth.png")
def smooth():
    tp.new_design("Scan")
    body = mesh_body(noisy())
    tp.camera()
    before = tp.render()
    step("MeshSmooth", body, Smoothness=0.5)
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_combine.png")
def combine():
    import FreeCAD as App
    import Part

    tp.new_design("Scan")
    target = mesh_body(triangles(Part.makeBox(30, 20, 10)), "Base")
    tool = mesh_body(triangles(Part.makeCylinder(7, 12, App.Vector(30, 10, 4))), "Knob")
    tool.ViewObject.ShapeColor = (0.23, 0.36, 0.86)
    tp.camera()
    before = tp.render()
    step("MeshCombine", target, Tools=[tool], Operation="Join")
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_separate.png")
def separate():
    import FreeCAD as App
    import Mesh
    import Part

    tp.new_design("Scan")
    both = Mesh.Mesh()
    both.addMesh(triangles(Part.makeBox(20, 20, 10)))
    both.addMesh(triangles(Part.makeCylinder(8, 14, App.Vector(36, 10, 0))))
    body = mesh_body(both)
    tp.camera()
    before = tp.render()
    made = step("MeshSeparate", body, SeparateType="Mesh Shells")
    from fission180 import mesh

    # what the Separate dialog does after its preview: one more body per piece
    found = mesh._cache(made).get("pieces") or []
    pieces = mesh.set_piece_count(made, len(found), body.Label)
    tp.recompute()
    marks = {}
    for piece in pieces[1:]:
        marks.update(mark(result(piece), list(range(result(piece).CountFacets)), "TipPiece"))
    after = tp.render(highlight=marks)
    return tp.before_after(before, after)


@tp.picture("mesh_reverse_normal.png")
def reverse_normal():
    """An inside-out body (its faces turned in: drawn dark, the browser flags it) and the same
    body with its faces turned round."""
    from fission180 import mesh

    tp.new_design("Scan")
    inside_out = mesh.reverse_mesh(triangles(part_shape()))
    body = mesh_body(inside_out)
    tp.camera()
    before = tp.render()
    step("MeshReverseNormal", body)
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_direct_edit.png")
def direct_edit():
    tp.new_design("Scan")
    found = fine_part()
    body = mesh_body(found)
    tp.camera()
    shot = tp.render(highlight=mark(found, facets_where(found, near((32, 8, 12), 6.0))))
    import FreeCADGui as Gui

    Gui.Selection.addSelection(tp.doc().Name, body.Name)
    tp.run_command("Fission180_MeshDirectEdit")
    panel = tp.wait_for_panel()
    tp.settle()
    return tp.with_dialog(shot, ws.trim_panel(tp.grab(panel)), width=160)


def bumped():
    """A plate whose top has a spike (a scanning error) in its middle."""
    import Mesh
    import Part

    from fission180 import mesh

    plate = mesh.remesh_mesh(triangles(Part.makeBox(40, 30, 6)), "Uniform", 0.25)
    points, facets = mesh.topology(plate)
    moved = []
    for p in points:
        x, y, z = p
        d = math.hypot(x - 20, y - 15)
        if z > 5.99 and d < 6:
            z += 6 * (1 - d / 6.0)
        moved.append((x, y, z))
    del Mesh
    return mesh.from_topology(moved, facets)


@tp.picture("mesh_erase_fill.png")
def erase_fill():
    tp.new_design("Scan")
    found = bumped()
    body = mesh_body(found, lines=False)
    bump = facets_where(
        found, lambda c: c.z > 6.01 or (c.z > 5.9 and math.hypot(c.x - 20, c.y - 15) < 6.5)
    )
    tp.camera()
    before = tp.render(highlight=mark(found, bump))
    filled = step("MeshEraseFill", body, Picks=centres(found, bump), FillType="Uniform")
    after = tp.render(highlight=mark(result(filled), new_triangles(found, result(filled))))
    return tp.before_after(before, after)


@tp.picture("mesh_delete_faces.png")
def delete_faces():
    tp.new_design("Scan")
    found = fine_part()
    body = mesh_body(found)
    chosen = facets_where(found, near((40, 15, 6), 5.0))
    tp.camera()
    before = tp.render(highlight=mark(found, chosen))
    step("MeshDeleteFaces", body, Picks=centres(found, chosen))
    after = tp.render()
    return tp.before_after(before, after)


@tp.picture("mesh_make_closed.png")
def make_closed():
    tp.new_design("Scan")
    broken = holed(triangles(part_shape()))
    body = mesh_body(broken)
    tp.camera()
    before = tp.render()
    step("MeshRepair", body, RepairType="Rebuild", RebuildType="Accurate", Density=96)
    after = tp.render()
    return tp.before_after(before, after)


# -- CONVERT -----------------------------------------------------------------------------------
@tp.picture("mesh_convert.png")
def convert():
    from fission180 import insert

    tp.new_design("Scan")
    body = mesh_body(triangles(part_shape(), 0.3, 30), lines=True)
    tp.camera()
    before = tp.render()
    solid, made = insert.convert_mesh(body, "Prismatic", True)
    tp.recompute()
    tp.hide(body)
    after = tp.render()
    return tp.before_after(before, after)
