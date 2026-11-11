# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the MANUFACTURE workspace draws over the design: the active setup's stock
(see-through), its work coordinate system (X red, Y green, Z blue at the origin), the
toolpaths of the operations picked in the browser (cutting moves blue, rapid moves yellow,
ramps / helixes / lead-ins green, straight plunges red: FreeCAD's engine does not mark
lead-ins, so every cutting move that also changes height counts as one), an open operation's
five heights as coloured planes, and Simulate's stock and tool.

Only drawn: Coin nodes in the 3D view, never document objects (nothing in the file, nothing
in the undo history), never picked (a click goes through them to the face behind).
"""

import FreeCADGui as Gui

from . import warn
from . import manufacture_core as core

CUT = (0.16, 0.47, 1.0)
RAPID = (1.0, 0.84, 0.10)
LEAD = (0.20, 0.80, 0.32)
PLUNGE = (0.95, 0.26, 0.20)
KIND_COLORS = {"cut": CUT, "rapid": RAPID, "lead": LEAD, "plunge": PLUNGE}
STOCK_COLOR = (0.55, 0.72, 0.95)
MAX_POINTS = 400000
SIM_GRID = 140  # the simulated stock is drawn with at most this many points a side

STATE = {
    "root": None,
    "view": None,
    "doc": None,
    "parts": {},  # name -> SoSeparator under the root's transform
    "counts": {},  # what is drawn (tests): {"stock": 1, "paths": moves, "planes": n...}
    "key": None,
}


# what counts() says of each drawn part
PART_COUNTS = {
    "setup": ("stock", "triad", "origin"),
    "paths": ("paths", "kinds"),
    "heights": ("planes", "heights"),
    "marks": ("marks",),
    "simulation": ("simulation", "tool_at"),
}


def _coin():
    from pivy import coin

    return coin


def _view(doc):
    try:
        gdoc = Gui.getDocument(doc.Name) if doc is not None else None
        view = gdoc.ActiveView if gdoc is not None else None
        if view is None or not hasattr(view, "getSceneGraph"):
            return None
        return view
    except Exception:
        return None


def _ensure_root(doc):
    coin = _coin()
    view = _view(doc)
    if view is None:
        return None
    if STATE["root"] is not None and STATE["view"] is view:
        return STATE["root"]
    clear()
    root = coin.SoSeparator()
    root.setName("Fission180CamView")
    pick = coin.SoPickStyle()
    pick.style = coin.SoPickStyle.UNPICKABLE
    root.addChild(pick)
    root.addChild(coin.SoTransform())  # the setup's coordinates -> the design's
    try:
        view.getSceneGraph().addChild(root)
    except Exception as exc:
        warn("manufacture view: %s" % exc)
        return None
    STATE.update(root=root, view=view, doc=doc.Name, parts={}, counts={}, key=None)
    return root


def clear():
    """Take everything away (leaving the workspace, another design in front)."""
    root, view = STATE["root"], STATE["view"]
    STATE.update(root=None, view=None, doc=None, parts={}, counts={}, key=None)
    if root is None or view is None:
        return
    try:
        view.getSceneGraph().removeChild(root)
    except Exception:
        pass  # the view went with its document


def counts():
    return dict(STATE["counts"])


def _set_part(doc, name, node):
    root = _ensure_root(doc)
    if root is None:
        return False
    old = STATE["parts"].pop(name, None)
    if old is not None:
        try:
            root.removeChild(old)
        except Exception:
            pass
    if node is not None:
        root.addChild(node)
        STATE["parts"][name] = node
    return True


def drop(name):
    root = STATE["root"]
    old = STATE["parts"].pop(name, None)
    for key in PART_COUNTS.get(name, (name,)):
        STATE["counts"].pop(key, None)
    if root is not None and old is not None:
        try:
            root.removeChild(old)
        except Exception:
            pass


def _place(placement):
    coin = _coin()
    root = STATE["root"]
    if root is None:
        return
    transform = root.getChild(1)
    base, rot = placement.Base, placement.Rotation.Q
    transform.translation.setValue(coin.SbVec3f(base.x, base.y, base.z))
    transform.rotation.setValue(coin.SbRotation(rot[0], rot[1], rot[2], rot[3]))


def _lines(polylines, color, width=2.0):
    coin = _coin()
    sep = coin.SoSeparator()
    look = coin.SoBaseColor()
    look.rgb.setValue(*color)
    sep.addChild(look)
    light = coin.SoLightModel()
    light.model = coin.SoLightModel.BASE_COLOR
    sep.addChild(light)
    style = coin.SoDrawStyle()
    style.lineWidth = width
    sep.addChild(style)
    points, counts_ = [], []
    for line in polylines:
        if len(line) < 2:
            continue
        points.extend(line)
        counts_.append(len(line))
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(points), points)
    sep.addChild(coords)
    lineset = coin.SoLineSet()
    lineset.numVertices.setValues(0, len(counts_), counts_)
    sep.addChild(lineset)
    return sep


def _box_edges(b):
    x0, y0, z0, x1, y1, z1 = b
    bottom = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z0)]
    top = [(x, y, z1) for x, y, _z in bottom]
    posts = [[(x, y, z0), (x, y, z1)] for x, y, _z in bottom[:4]]
    return [bottom, top] + posts


def _faces(triangles_points, triangles, color, transparency):
    coin = _coin()
    sep = coin.SoSeparator()
    look = coin.SoMaterial()
    look.diffuseColor.setValue(*color)
    look.transparency.setValue(transparency)
    sep.addChild(look)
    hints = coin.SoShapeHints()
    hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
    sep.addChild(hints)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(triangles_points), triangles_points)
    sep.addChild(coords)
    faces = coin.SoIndexedFaceSet()
    index = []
    for tri in triangles:
        index.extend([int(tri[0]), int(tri[1]), int(tri[2]), -1])
    faces.coordIndex.setValues(0, len(index), index)
    sep.addChild(faces)
    return sep


def _box_faces(b, color, transparency):
    x0, y0, z0, x1, y1, z1 = b
    pts = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b_, c, d in quads:
        tris += [(a, b_, c), (a, c, d)]
    return _faces(pts, tris, color, transparency)


def _triad(length):
    coin = _coin()
    sep = coin.SoSeparator()
    for axis, color in (
        ((1, 0, 0), (0.92, 0.20, 0.20)),
        ((0, 1, 0), (0.25, 0.75, 0.25)),
        ((0, 0, 1), (0.25, 0.45, 0.95)),
    ):
        tip = tuple(c * length for c in axis)
        sep.addChild(_lines([[(0.0, 0.0, 0.0), tip]], color, 3.5))
        head = coin.SoSeparator()
        look = coin.SoBaseColor()
        look.rgb.setValue(*color)
        head.addChild(look)
        move = coin.SoTranslation()
        move.translation.setValue(*tip)
        head.addChild(move)
        turn = coin.SoRotation()
        turn.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0), coin.SbVec3f(*axis)))
        head.addChild(turn)
        cone = coin.SoCone()
        cone.bottomRadius = length * 0.07
        cone.height = length * 0.22
        head.addChild(cone)
        sep.addChild(head)
    ball = coin.SoSphere()
    ball.radius = length * 0.06
    white = coin.SoBaseColor()
    white.rgb.setValue(0.95, 0.95, 0.95)
    sep.addChild(white)
    sep.addChild(ball)
    return sep


def show_setup(doc, frame, stock=True):
    """The setup's stock and its work coordinate system."""
    coin = _coin()
    if _ensure_root(doc) is None:
        return False
    _place(frame.placement)
    sep = coin.SoSeparator()
    b = frame.stock_box
    if stock:
        if frame.stock_solid is not None:
            try:
                points, tris = frame.stock_solid.tessellate(0.2)
                sep.addChild(_faces([(p.x, p.y, p.z) for p in points], tris, STOCK_COLOR, 0.82))
            except Exception as exc:
                warn("manufacture view: stock: %s" % exc)
        else:
            sep.addChild(_box_faces(b, STOCK_COLOR, 0.82))
        sep.addChild(_lines(_box_edges(b), (0.35, 0.55, 0.90), 1.5))
    size = core.box_size(b)
    length = max(4.0, 0.18 * max(size))
    on_top = coin.SoAnnotation()  # the axes show through the part
    on_top.addChild(_triad(length))
    sep.addChild(on_top)
    _set_part(doc, "setup", sep)
    STATE["counts"]["stock"] = 1 if stock else 0
    STATE["counts"]["triad"] = 1
    STATE["counts"]["origin"] = [round(c, 4) for c in frame.placement.Base]
    return True


def show_paths(doc, frame, segment_lists):
    """The toolpaths (lists of manufacture_core.moves()) in their kinds' colours."""
    coin = _coin()
    if _ensure_root(doc) is None:
        return 0
    _place(frame.placement)
    by_kind = {}
    total = points = 0
    for segments in segment_lists:
        for seg in segments:
            if points > MAX_POINTS:
                break
            by_kind.setdefault(seg["kind"], []).append(seg["points"])
            points += len(seg["points"])
            total += 1
    if not total:
        drop("paths")
        return 0
    sep = coin.SoSeparator()
    for kind, lines in by_kind.items():
        sep.addChild(_lines(lines, KIND_COLORS.get(kind, CUT), 1.0 if kind == "rapid" else 2.0))
    _set_part(doc, "paths", sep)
    STATE["counts"]["paths"] = total
    STATE["counts"]["kinds"] = {k: len(v) for k, v in by_kind.items()}
    return total


def show_heights(doc, frame, heights):
    """An open operation's heights as see-through planes over the stock ({key: z})."""
    coin = _coin()
    if _ensure_root(doc) is None:
        return 0
    _place(frame.placement)
    b = frame.stock_box
    pad = 0.06 * max(b[3] - b[0], b[4] - b[1])
    sep = coin.SoSeparator()
    n = 0
    for key in core.HEIGHT_KEYS:
        if heights.get(key) is None:
            continue
        z = float(heights[key])
        pts = [
            (b[0] - pad, b[1] - pad, z),
            (b[3] + pad, b[1] - pad, z),
            (b[3] + pad, b[4] + pad, z),
            (b[0] - pad, b[4] + pad, z),
        ]
        color = core.HEIGHT_COLORS[key]
        sep.addChild(_faces(pts, [(0, 1, 2), (0, 2, 3)], color, 0.78))
        sep.addChild(_lines([pts + [pts[0]]], color, 1.5))
        n += 1
    _set_part(doc, "heights", sep)
    STATE["counts"]["planes"] = n
    STATE["counts"]["heights"] = {
        k: round(float(v), 4) for k, v in heights.items() if v is not None
    }
    return n


def show_marks(doc, frame, polylines, color=(1.0, 0.45, 0.1)):
    """What an open dialog marks on the model (the contours picked, the holes found)."""
    if _ensure_root(doc) is None:
        return 0
    _place(frame.placement)
    if not polylines:
        drop("marks")
        return 0
    coin = _coin()
    top = coin.SoAnnotation()
    top.addChild(_lines(polylines, color, 3.0))
    _set_part(doc, "marks", top)
    STATE["counts"]["marks"] = len(polylines)
    return len(polylines)


# -- Simulate ---------------------------------------------------------------------------------
def show_simulation(doc, frame, stock, tool, position):
    """The simulated stock (a manufacture_sim.Stock) as a surface and the tool at `position`."""
    coin = _coin()
    if _ensure_root(doc) is None:
        return False
    _place(frame.placement)
    heights = stock.heights
    ny, nx = heights.shape
    sy = max(1, int(-(-ny // SIM_GRID)))
    sx = max(1, int(-(-nx // SIM_GRID)))
    grid = heights[::sy, ::sx]
    rows, cols = grid.shape
    x0, y0 = stock.box[0] + 0.5 * stock.cell, stock.box[1] + 0.5 * stock.cell
    points = []
    values = grid.tolist()
    for iy in range(rows):
        y = y0 + iy * sy * stock.cell
        row = values[iy]
        for ix in range(cols):
            points.append((x0 + ix * sx * stock.cell, y, row[ix]))
    sep = coin.SoSeparator()
    look = coin.SoMaterial()
    look.diffuseColor.setValue(0.80, 0.68, 0.45)
    sep.addChild(look)
    hints = coin.SoShapeHints()
    hints.vertexOrdering = coin.SoShapeHints.COUNTERCLOCKWISE
    hints.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
    hints.creaseAngle = 0.6
    sep.addChild(hints)
    coords = coin.SoCoordinate3()
    coords.point.setValues(0, len(points), points)
    sep.addChild(coords)
    mesh = coin.SoQuadMesh()
    mesh.verticesPerRow = cols
    mesh.verticesPerColumn = rows
    sep.addChild(mesh)
    sep.addChild(_lines(_box_edges(stock.box), (0.45, 0.38, 0.25), 1.0))
    if tool is not None and position is not None:
        radius = float(tool["diameter"]) / 2.0
        length = max(float(tool.get("flute_length") or 10.0), 2.0 * radius) * 1.6
        tool_sep = coin.SoSeparator()
        colour = coin.SoMaterial()
        colour.diffuseColor.setValue(0.85, 0.85, 0.88)
        tool_sep.addChild(colour)
        move = coin.SoTranslation()
        move.translation.setValue(position[0], position[1], position[2] + length / 2.0)
        tool_sep.addChild(move)
        turn = coin.SoRotation()
        turn.rotation.setValue(coin.SbRotation(coin.SbVec3f(0, 1, 0), coin.SbVec3f(0, 0, 1)))
        tool_sep.addChild(turn)
        cylinder = coin.SoCylinder()
        cylinder.radius = radius
        cylinder.height = length
        tool_sep.addChild(cylinder)
        sep.addChild(tool_sep)
    _set_part(doc, "simulation", sep)
    STATE["counts"]["simulation"] = len(points)
    STATE["counts"]["tool_at"] = [round(c, 4) for c in position] if position is not None else None
    return True


def simulating():
    return "simulation" in STATE["parts"]
