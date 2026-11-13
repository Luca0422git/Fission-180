# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SURFACE tab's tooltip pictures (wave 8, builder tips-solid).

    tools/fission180/make_tip_pictures.sh surface [picture ...]

The tab's own 14 commands (the ones it shares with SOLID have their picture there). Each is a
small surface demo before and after the tool, built by Fission 180's own surface code
(tip_demos_solid.SURFACE: the golden models' sf_surface steps, the code the dialogs run), drawn
with tip_pictures_solid.model_picture.
"""

import tip_demos_solid as demos
import tip_pictures as tp
import tip_pictures_solid as solid

# tip_pictures_solid registered SOLID's pictures when it was imported: this script makes only
# the SURFACE tab's
del tp.PICTURES[:]

solid.register_models(demos.SURFACE)


@tp.picture("surface_reverse_normal.png")
def reverse_normal():
    """A surface's two sides told apart: Fission 180 draws the back of a surface body in
    another shade; the normal's side is marked with an arrow drawn from the face's own
    normal before and after."""
    tp.new_design()
    b = solid.run_steps(solid.builder(), demos.SURFACE["surface_extrude"]["before"])
    solid.run_steps(b, demos.SURFACE["surface_extrude"]["tool"])
    sheet = solid.owner(b.objects["w1"])
    tp.camera("iso", 0.9)
    before = arrow_shot(sheet)
    solid.run_steps(
        b,
        [demos.surface("rn", "reverse_normal", [], bodies=["w1"])],
    )
    after = arrow_shot(solid.owner(b.objects["w1"]))
    return tp.before_after(before, after)


def arrow_shot(body):
    """A render of a surface body with its normal at the middle of its face drawn as a blue
    arrow (the faces' outward side)."""
    face = body.Shape.Faces[0]
    u0, u1, v0, v1 = face.ParameterRange
    u, v = (u0 + u1) / 2, (v0 + v1) / 2
    point = face.valueAt(u, v)
    normal = face.normalAt(u, v)
    length = 12.0
    tip = point + normal * length
    side = normal.cross(tp._vec((0, 0, 1)))
    if side.Length < 1e-6:
        side = normal.cross(tp._vec((1, 0, 0)))
    side.normalize()
    head = [tip - normal * 3 + side * 2, tip, tip - normal * 3 - side * 2]
    shot = tp.render()
    project = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))

    def unit(p):
        x, y = project(p)
        return (x, y * tp.ASPECT)

    shot.edges.append([unit(point), unit(tip)])
    shot.edges.append([unit(p) for p in head])
    return shot
