# SPDX-License-Identifier: LGPL-2.1-or-later
"""The light preview of a heavy pattern.

A pattern's dialog used to build the real copies after every key and every drag. For the
book's knurl (25 times a swept groove and its mirror, crossing each other) that is half a
minute of geometry kernel per value typed; the parity report's tester saw "the live preview
kept the app busy for more than 30 s" (6 copies) and a 25 times pattern that "never
finished". Autodesk's blog on the compute options speaks of a preview that "shows exactly
what you want" while OK gives another result: Fusion's preview is not the built feature
either.

So when the copies would be slow to build (heavy()), the dialog shows them as shaded copies
of the faces the picked features made (Ghosts), the pattern step stays the part before it
(pattern.LIGHT), and OK builds the copies once, with a progress window and Cancel
(pattern_progress.py). Light copies cost a few milliseconds whatever their number.

No Qt and no document here but the Ghosts' drawing.
"""

import FreeCAD as App

from . import warn

# What a copy of a face costs the kernel, roughly: a flat or round face 1, a swept or
# free-form one CURVED times that, a long sweep (a surface of many poles) more again. Above
# HEAVY the dialog previews light. The Geocache knurl's groove and its mirror are 4 swept
# faces of 12 poles (32 a copy): the Circular Pattern's first 3 are built (0.8 s), 6 and
# more are light (6: 2 s, 25: half a minute). The Fire Piston's 1.5 turn grooves have 24
# poles and cross each other three times: light from the first copy (6 take 100 s). A row
# of 40 plain holes scores about 100.
CURVED = 8
HEAVY = 150
SIMPLE = ("Plane", "Cylinder", "Cone", "Sphere", "Toroid")
MAX_TRIANGLES = 400000  # more is not drawn (the dialog says how many copies there will be)
GHOST = (0.12, 0.53, 0.90)


def weight(face):
    """About how hard a copy of this face is for the kernel (1 = a flat face)."""
    try:
        surface = face.Surface
        name = surface.TypeId.split("Geom")[-1]
        if name in SIMPLE:
            return 1.0
        if name == "BSplineSurface":
            poles = surface.NbUPoles * surface.NbVPoles
            return CURVED * max(1.0, poles / 12.0) ** 2
    except Exception:
        pass
    return float(CURVED)


def score(faces, copies):
    return int(copies) * sum(weight(face) for face in faces)


def heavy(faces, copies):
    """True when building `copies` copies of `faces` would keep a person waiting."""
    return score(faces, copies) > HEAVY


def move_matrix(move):
    """The App.Matrix of one of pattern.placements()'s moves: a placement, or
    ("mirror", point, normal)."""
    if isinstance(move, tuple):
        _tag, point, normal = move
        n = App.Vector(normal)
        n.normalize()
        d = 2.0 * point.dot(n)
        m = App.Matrix()
        m.A11, m.A12, m.A13, m.A14 = 1 - 2 * n.x * n.x, -2 * n.x * n.y, -2 * n.x * n.z, d * n.x
        m.A21, m.A22, m.A23, m.A24 = -2 * n.y * n.x, 1 - 2 * n.y * n.y, -2 * n.y * n.z, d * n.y
        m.A31, m.A32, m.A33, m.A34 = -2 * n.z * n.x, -2 * n.z * n.y, 1 - 2 * n.z * n.z, d * n.z
        return m
    return move.toMatrix()


def global_matrices(moves, body_placement):
    """The moves (body coordinates) as matrices on global points."""
    to_global = body_placement.toMatrix()
    to_body = body_placement.inverse().toMatrix()
    return [to_global.multiply(move_matrix(move)).multiply(to_body) for move in moves]


class Ghosts:
    """The copies of a light preview: the faces shaded see-through blue at every copy. One
    Coin node for all of them; not clickable."""

    def __init__(self, view):
        from pivy import coin

        self.coin = coin
        self.view = view
        self.count = 0  # copies drawn (the tests look at it)
        self.root = coin.SoSeparator()
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        offset = coin.SoPolygonOffset()
        offset.factor = -1.0
        offset.units = -1.0
        self.root.addChild(offset)
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*GHOST)
        material.emissiveColor.setValue(*[c * 0.5 for c in GHOST])
        material.transparency.setValue(0.35)
        self.root.addChild(material)
        hints = coin.SoShapeHints()  # a mirrored copy is wound the other way: light both sides
        hints.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
        self.root.addChild(hints)
        self.coords = coin.SoCoordinate3()
        self.mesh = coin.SoIndexedFaceSet()
        self.root.addChild(self.coords)
        self.root.addChild(self.mesh)
        self._cache = {}
        view.getSceneGraph().addChild(self.root)

    def _mesh_of(self, face):
        key = face.hashCode()
        if key not in self._cache:
            try:
                self._cache[key] = face.tessellate(0.1)
            except Exception:
                self._cache[key] = ([], [])
        return self._cache[key]

    def show(self, faces, matrices):
        """Draw `faces` (global coordinates) at every matrix. Returns the copies drawn."""
        points, index = [], []
        drawn = 0
        try:
            meshes = [self._mesh_of(face) for face in faces]
            per_copy = sum(len(triangles) for _p, triangles in meshes)
            for matrix in matrices:
                if per_copy == 0 or (drawn + 1) * per_copy > MAX_TRIANGLES:
                    break
                for pts, triangles in meshes:
                    start = len(points)
                    for p in pts:
                        q = matrix.multVec(p)
                        points.append((q.x, q.y, q.z))
                    for a, b, c in triangles:
                        index += [start + a, start + b, start + c, -1]
                drawn += 1
            self.coords.point.setNum(0)
            self.mesh.coordIndex.setNum(0)
            if points:
                self.coords.point.setValues(0, len(points), points)
                self.mesh.coordIndex.setValues(0, len(index), index)
        except Exception as exc:
            warn("pattern preview: %s" % exc)
        self.count = drawn
        return drawn

    def clear(self):
        self.show([], [])

    def remove(self):
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass
