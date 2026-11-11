# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion-style profile picking for Extrude.

Every closed region of a sketch is a profile (a circle inside a rectangle gives the
ring and the disc; crossing curves split regions too). The regions are FreeCAD's own
sketch regions ("InternalFaceN", see extrude.regions), so what is shaded here is
exactly what the extrude links to.

ProfilePicker(view, sketches, on_pick) shades the regions, lights one up under the
mouse and calls on_pick(sketch, "InternalFaceN") when the user clicks inside it. A
region hidden behind a face of the part is not picked (the face is), unless the picker
is made with through=True (Extrude, Revolve, Sweep, Loft: a shown sketch's profile wins
over the body in front of it, like Fusion's). set_selected() shows the picked ones in a
stronger blue, show_faces() highlights picked body faces.
Mouse events come through FreeCAD's view.addEventCallback, which runs Python safely
(unlike raw pivy callbacks, see taskui.ArrowDragger).
"""

import time

import FreeCAD as App
import FreeCADGui as Gui

from . import warn

FILL = (0.45, 0.77, 1.0)  # Fusion-like profile blue
PICKED = (0.12, 0.53, 0.90)
IDLE_TRANSPARENCY = 0.65
HOVER_TRANSPARENCY = 0.35
PICKED_TRANSPARENCY = 0.25
DIMMED_TRANSPARENCY = 0.85  # picked, while a red cut preview must show through
GHOST_TRANSPARENCY = 0.88  # a region seen through the part in front of it (through=True)
NEAR_PIXELS = 4  # a click this close to a region still picks it (a thin slot, a small hole)


def sketch_faces(sketch):
    """Faces (global coordinates) of every region of a sketch, or []."""
    from . import extrude

    try:
        return [face for _sub, face in extrude.regions(sketch)]
    except Exception as exc:
        warn("no profile for %s: %s" % (sketch.Label, exc))
        return []


def mouse_ray(view, position):
    """(point, direction) of the line under the mouse, pointing into the screen."""
    point = view.getPoint(tuple(position))
    if view.getCameraType() == "Perspective":
        eye = App.Vector(*view.getCameraNode().position.getValue().getValue())
        direction = point - eye
        direction.normalize()
        return point, direction
    return point, view.getViewDirection()


def ray_plane(view, position, base, normal):
    """(hit point, distance along the ray) where the mouse ray meets a plane, or None."""
    point, direction = mouse_ray(view, position)
    denom = direction.dot(normal)
    if abs(denom) < 1e-9:
        return None
    t = (base - point).dot(normal) / denom
    return point + direction * t, t


def ray_hit(view, position, face):
    """Point where the mouse ray at `position` crosses the plane of `face`, or None."""
    hit = ray_hit_t(view, position, face)
    return hit[0] if hit else None


def ray_hit_t(view, position, face):
    normal = face.Surface.Axis if hasattr(face.Surface, "Axis") else face.normalAt(0, 0)
    return ray_plane(view, position, face.CenterOfMass, normal)


def inside(face, point, tol=1e-4):
    try:
        return face.isInside(point, tol, True)
    except Exception:
        return False


def hidden_by(shape, point, direction):
    """True if `shape` (a solid) is between the viewer and `point` (looking along
    `direction`): then a click there hits the part, not the sketch area."""
    import Part

    if shape is None or shape.isNull() or not shape.Solids:
        return False
    reach = shape.BoundBox.DiagonalLength + (shape.BoundBox.Center - point).Length + 1.0
    gap = 1e-3 * max(1.0, reach)
    start = point - direction * reach
    end = point - direction * gap
    try:
        common = shape.common(Part.makeLine(start, end))
        return common.Length > gap
    except Exception:
        return False


def handle_at(view, position, radius=3):
    """True if the front-most thing under the mouse is a drag handle (a Coin dragger: the
    blue arrows, the taper disc). A press there drags the handle; it is not a pick."""
    from pivy import coin

    try:
        viewer = view.getViewer()
        manager = viewer.getSoRenderManager()
        action = coin.SoRayPickAction(manager.getViewportRegion())
        action.setPoint(coin.SbVec2s(int(position[0]), int(position[1])))
        action.setRadius(radius)
        action.apply(manager.getSceneGraph())
        point = action.getPickedPoint()
        if point is None:
            return False
        path = point.getPath()  # read now: the path dies with the action
        dragger = coin.SoDragger.getClassTypeId()
        return any(path.getNode(i).isOfType(dragger) for i in range(path.getLength()))
    except Exception:
        return False


class TextArea:
    """A whole sketch text as one pickable area (Fusion picks a text as one profile): its
    letters' faces (global), answering what ProfilePicker asks of a face."""

    def __init__(self, faces):
        self.faces = list(faces)
        self.Surface = self.faces[0].Surface
        self.CenterOfMass = self.faces[0].CenterOfMass
        self.Area = sum(f.Area for f in self.faces)

    def isInside(self, point, tol, check_face):
        return any(f.isInside(point, tol, check_face) for f in self.faces)

    def tessellate(self, tol):
        import FreeCAD as _App

        points, triangles = [], []
        for face in self.faces:
            verts, tris = face.tessellate(tol)
            base = len(points)
            points += [_App.Vector(v) for v in verts]
            triangles += [(base + a, base + b, base + c) for a, b, c in tris]
        return points, triangles


def text_areas(sketch):
    """[(text, TextArea)] of a sketch's texts (global coordinates)."""
    from . import extrude, text

    found = []
    for obj in text.texts_of(sketch):
        try:
            if "Touched" in obj.State or obj.Shape.isNull():
                obj.recompute()
            faces = [extrude._to_global(f, obj) for f in obj.Shape.Faces]
        except Exception as exc:
            warn("no profile for %s: %s" % (obj.Label, exc))
            continue
        if faces:
            found.append((obj, TextArea(faces)))
    return found


class ProfilePicker:
    """A press on a drag handle (an arrow in front of a region) drags the handle: it is no
    pick of the region behind it.

    clicks_through=True (Extrude): while the regions are offered, the sketches' own lines
    and faces let clicks through. The shaded regions here take the clicks, and an arrow
    behind a sketch (a cut going down into the part, with the sketch kept in view until OK)
    stays grabbable, as Fusion's arrows always are. Off for the other dialogs: Sweep and
    Loft pick sketch lines as paths and rails, so FreeCAD must still find them.

    on_curve (a thin extrude): the visible sketches' curves can be clicked too; a click
    within a few pixels of a curve calls on_curve(sketch, "EdgeN") instead of picking the
    area beside it. show_curves() draws the picked curves.

    through=True (Extrude, Revolve, Sweep, Loft; the book report: "clicking where a body
    face is in front of a profile picks the FACE - Fusion prefers the sketch profile",
    profiles in a sketch on the middle plane of a part, profiles of a sketch whose body is
    hidden): a region the part is in front of is picked all the same, and is drawn as a
    faint blue seen through the part, so the person sees what the click takes. Only a
    region that is already picked gives the click to the face in front of it (a click on
    a face further on ends the extrusion there; a picked region is dropped by a click
    where it can be seen).

    A click that misses every region by a few pixels (NEAR_PIXELS) takes the region next
    to it, when no face of a part is under the mouse: a thin slot or a small hole is only a
    few pixels wide in a fitted view."""

    CURVE_PIXELS = 6  # a click this close to a sketch curve picks the curve

    def __init__(
        self,
        view,
        sketches,
        on_pick,
        occluder=None,
        clicks_through=False,
        on_curve=None,
        through=False,
    ):
        from pivy import coin

        self.coin = coin
        self.view = view
        self.on_pick = on_pick
        self.on_curve = on_curve
        self.occluder = occluder  # () -> the part (global) that can hide regions
        self.through = bool(through)
        self.ghost_root = None  # the regions once more, seen through the part (through)
        self.ghosts = []  # their materials, one for each of self.regions (None: not drawn)
        self.regions = []  # (sketch, sub, face, material)
        self.curves = []  # (sketch, sub, [global points along the curve]) for on_curve
        self.selected = set()  # {(sketch name, sub)}
        self.dimmed = False  # picked profiles faded (a red cut preview is shown over them)
        self.face_materials = []  # materials of the highlighted body faces
        self.unpickable = []  # (sketch's root node, pick style) put in while offered
        self.last_click = 0.0  # time of the last click that picked a region
        self.last_click_at = None  # ...and where on the screen it was (Coin pixels)
        self.presses = 0  # presses of the left button in the view while offered
        self.region_press = -1  # ...the one that picked a region
        self.paused = False  # a dialog's other selection box takes the clicks now
        self.root = coin.SoSeparator()
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        # drawn a hair in front of the part's faces: FreeCAD pushes those back with the
        # default offset (factor 1, units 1); the same push here made the shaded areas of
        # a sketch on a face fight the face for the same pixels (Luca: "Faces that are
        # sketched on have z-fighting")
        offset = coin.SoPolygonOffset()
        offset.factor.setValue(-1.0)
        offset.units.setValue(-1.0)
        self.root.addChild(offset)
        self.face_root = coin.SoSeparator()  # picked body faces
        self.root.addChild(self.face_root)
        self.curve_root = coin.SoSeparator()  # picked (and hovered) sketch curves
        self.root.addChild(self.curve_root)
        self.hover_root = coin.SoSeparator()
        self.root.addChild(self.hover_root)
        self.hovered_curve = None
        if self.through:
            # Drawn after everything else, without the depth test: a faint blue where the
            # part is in front of a region (it shares the region's material, so it lights
            # up and turns "picked" with it).
            self.ghost_root = coin.SoAnnotation()
            ghost_look = coin.SoMaterialBinding()
            ghost_look.value = coin.SoMaterialBinding.OVERALL
            self.ghost_root.addChild(ghost_look)
        from . import extrude

        for sketch in sketches:
            try:
                found = extrude.regions(sketch)
            except Exception as exc:
                warn("no profile for %s: %s" % (sketch.Label, exc))
                continue
            # the areas only the face's projected edges bound are the face's (Auto
            # project): a click there takes the face (extrude.face_areas); slivers of no
            # area are no profiles (extrude.sliver_areas)
            own = extrude.face_areas(sketch) | extrude.sliver_areas(sketch)
            found = [(sub, face) for sub, face in found if sub not in own]
            for sub, face in found:
                self.regions.append((sketch, sub, face, self._add_face(face, self.root)))
                self._add_ghost(face)
            if on_curve is not None and _visible(sketch):
                self._offer_curves(sketch)
                if not found and clicks_through:
                    self._let_clicks_through(sketch)  # its curves are picked here
            if found and clicks_through:
                self._let_clicks_through(sketch)
            texts = text_areas(sketch)  # a text is one more profile (its sub is "")
            for obj, area in texts:
                self.regions.append((obj, "", area, self._add_face(area, self.root)))
                self._add_ghost(area)
                if clicks_through:
                    self._let_clicks_through(obj)
        self.hovered = None
        if self.ghost_root is not None:
            self.root.addChild(self.ghost_root)
        view.getSceneGraph().addChild(self.root)
        self.callbacks = [
            ("SoMouseButtonEvent", view.addEventCallback("SoMouseButtonEvent", self._button)),
            ("SoLocation2Event", view.addEventCallback("SoLocation2Event", self._moved)),
        ]

    def _let_clicks_through(self, sketch):
        """The sketch's own drawing cannot be picked while the picker is on (a Coin pick
        style in the sketch's own scene nodes, taken out again by remove(); nothing about
        the sketch itself changes). Its lines are under RootNode; its shaded areas
        (FreeCAD 1.1's SoSketchFaces) under the separate Annotation node."""
        for attr in ("RootNode", "Annotation"):
            try:
                root = getattr(sketch.ViewObject, attr)
                if root is None:
                    continue
                style = self.coin.SoPickStyle()
                style.style = self.coin.SoPickStyle.UNPICKABLE
                root.insertChild(style, 0)
                self.unpickable.append((root, style))
            except Exception:
                pass  # no view of the sketch: nothing to click there anyway

    # -- sketch curves (thin extrude) ---------------------------------------------------
    def _offer_curves(self, sketch):
        from . import curves

        try:
            count = len(sketch.Shape.Edges)
        except Exception:
            return
        for i in range(1, count + 1):
            edge = curves.edge_of(sketch, "Edge%d" % i)
            if edge is None:
                continue
            try:
                points = edge.discretize(Deflection=0.05) if edge.Length > 0 else []
            except Exception:
                points = []
            if len(points) < 2:
                try:
                    points = edge.discretize(24)
                except Exception:
                    continue
            self.curves.append((sketch, "Edge%d" % i, points))

    def _screen(self, point):
        x, y = self.view.getPointOnViewport(App.Vector(point))
        return float(x), float(y)

    def curve_at(self, position):
        """(sketch, "EdgeN") of the curve within CURVE_PIXELS of the mouse, nearest first;
        None when there is none (or the part hides it)."""
        import math

        if not self.curves:
            return None
        px, py = float(position[0]), float(position[1])
        best = None
        for sketch, sub, points in self.curves:
            try:
                screen = [self._screen(p) for p in points]
            except Exception:
                continue
            for (ax, ay), (bx, by), a, b in zip(screen, screen[1:], points, points[1:]):
                dx, dy = bx - ax, by - ay
                length2 = dx * dx + dy * dy
                t = 0.0 if length2 < 1e-12 else ((px - ax) * dx + (py - ay) * dy) / length2
                t = max(0.0, min(1.0, t))
                d = math.hypot(px - (ax + dx * t), py - (ay + dy * t))
                if d <= self.CURVE_PIXELS and (best is None or d < best[0]):
                    best = (d, sketch, sub, a + (b - a) * t)
        if best is None:
            return None
        if self.occluder is not None:
            try:
                shape = self.occluder()
            except Exception:
                shape = None
            _start, direction = mouse_ray(self.view, position)
            if hidden_by(shape, best[3], direction):
                return None
        return best[1], best[2]

    def _line(self, parent, points, color, width):
        coin = self.coin
        sep = coin.SoSeparator()
        style = coin.SoDrawStyle()
        style.lineWidth = width
        sep.addChild(style)
        material = coin.SoBaseColor()
        material.rgb.setValue(*color)
        sep.addChild(material)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(points), [(p.x, p.y, p.z) for p in points])
        sep.addChild(coords)
        line = coin.SoLineSet()
        line.numVertices.setValue(len(points))
        sep.addChild(line)
        parent.addChild(sep)

    def show_curves(self, keys):
        """Draw the picked curves {(sketch name, "EdgeN")} in the picked blue."""
        self.curve_root.removeAllChildren()
        for sketch, sub, points in self.curves:
            if (sketch.Name, sub) in keys:
                self._line(self.curve_root, points, PICKED, 5)

    def _hover_curve(self, hit):
        if hit == self.hovered_curve:
            return
        self.hovered_curve = hit
        self.hover_root.removeAllChildren()
        if hit is None:
            return
        for sketch, sub, points in self.curves:
            if (sketch, sub) == hit:
                self._line(self.hover_root, points, FILL, 4)

    def _add_face(self, face, parent, color=FILL, transparency=IDLE_TRANSPARENCY):
        coin = self.coin
        points, triangles = face.tessellate(0.2)
        sep = coin.SoSeparator()
        material = coin.SoMaterial()
        material.diffuseColor.setValue(*color)
        material.emissiveColor.setValue(color[0] * 0.4, color[1] * 0.4, color[2] * 0.4)
        material.transparency.setValue(transparency)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(points), [(p.x, p.y, p.z) for p in points])
        faces = coin.SoIndexedFaceSet()
        index = []
        for a, b, c in triangles:
            index += [a, b, c, -1]
        faces.coordIndex.setValues(0, len(index), index)
        sep.addChild(material)
        sep.addChild(coords)
        sep.addChild(faces)
        parent.addChild(sep)
        return material

    def _add_ghost(self, face):
        """The region once more in the see-through layer (through=True); called once for
        each region, right after it was added to self.regions."""
        self.ghosts.append(None)
        if self.ghost_root is None:
            return
        try:
            coin = self.coin
            points, triangles = face.tessellate(0.2)
            sep = coin.SoSeparator()
            material = coin.SoMaterial()
            material.diffuseColor.setValue(*FILL)
            material.emissiveColor.setValue(FILL[0] * 0.4, FILL[1] * 0.4, FILL[2] * 0.4)
            material.transparency.setValue(GHOST_TRANSPARENCY)
            coords = coin.SoCoordinate3()
            coords.point.setValues(0, len(points), [(p.x, p.y, p.z) for p in points])
            faces = coin.SoIndexedFaceSet()
            index = []
            for a, b, c in triangles:
                index += [a, b, c, -1]
            faces.coordIndex.setValues(0, len(index), index)
            sep.addChild(material)
            sep.addChild(coords)
            sep.addChild(faces)
            self.ghost_root.addChild(sep)
            self.ghosts[-1] = material
        except Exception as exc:
            warn("profile shading: %s" % exc)

    def set_through(self):
        """Turn `through` on for a picker that was made without it (the sweep and loft
        pickers are made by curve_pick): the see-through layer is built for the regions
        there are."""
        if self.through:
            return
        coin = self.coin
        self.through = True
        self.ghost_root = coin.SoAnnotation()
        look = coin.SoMaterialBinding()
        look.value = coin.SoMaterialBinding.OVERALL
        self.ghost_root.addChild(look)
        self.ghosts = []
        for region in self.regions:
            self._add_ghost(region[2])
        self.root.addChild(self.ghost_root)
        for region in self.regions:
            self._paint(region, region is self.hovered)

    # -- what is under the mouse ------------------------------------------------------
    def _region_hit(self, position):
        """((sketch, sub, face, material), point) of the region exactly under the mouse;
        the smallest wins (a hole inside a plate). None when there is none."""
        best = None
        for region in self.regions:
            face = region[2]
            hit = ray_hit_t(self.view, position, face)
            if hit is None:
                continue
            point, _t = hit
            if inside(face, point) and (best is None or face.Area < best[0][2].Area):
                best = (region, point)
        return best

    def _region_near(self, position):
        """As _region_hit, for a click that missed every region by a few pixels: the
        smallest region within NEAR_PIXELS (a thin slot, a 10-pixel hole)."""
        x, y = float(position[0]), float(position[1])
        best = None
        for reach in (2, NEAR_PIXELS):
            for dx, dy in (
                (reach, 0),
                (-reach, 0),
                (0, reach),
                (0, -reach),
                (reach, reach),
                (reach, -reach),
                (-reach, reach),
                (-reach, -reach),
            ):
                hit = self._region_hit((x + dx, y + dy))
                if hit is not None and (best is None or hit[0][2].Area < best[0][2].Area):
                    best = hit
            if best is not None:
                return best
        return None

    def _part_at(self, position):
        """True when something other than a sketch is under the mouse (a face, an edge)."""
        try:
            info = self.view.getObjectInfo((int(position[0]), int(position[1])))
            if not info or not info.get("Object"):
                return False
            doc = App.getDocument(info["Document"])
            obj = doc.getObject(info["Object"])
            return not (obj is not None and obj.isDerivedFrom("Sketcher::SketchObject"))
        except Exception:
            return False

    def _is_hidden(self, position, point):
        """True if the part (the occluder) is in front of `point` under the mouse."""
        if self.occluder is None:
            return False
        try:
            shape = self.occluder()
        except Exception:
            shape = None
        _start, direction = mouse_ray(self.view, position)
        return hidden_by(shape, point, direction)

    def region_at(self, position, check_hidden=False, near=False):
        """(sketch, sub, face, material) under the mouse; the smallest region wins (a hole
        inside a plate). With check_hidden, a region behind the part is not returned
        (through=True: only when it is already picked, see the class). near: a click a few
        pixels beside a region takes it."""
        best = self._region_hit(position)
        if best is None and near:
            best = self._region_near(position)
        if best is None:
            return None
        if check_hidden and self._is_hidden(position, best[1]):
            region = best[0]
            if not self.through or (region[0].Name, region[1]) in self.selected:
                return None  # the part is in front of the region: the face gets the click
        return best[0]

    # -- looks --------------------------------------------------------------------------
    def _picked_transparency(self):
        return DIMMED_TRANSPARENCY if self.dimmed else PICKED_TRANSPARENCY

    def _paint(self, region, hovered=False):
        material = region[3]
        if (region[0].Name, region[1]) in self.selected:
            color, transparency = PICKED, self._picked_transparency()
        else:
            color = FILL
            transparency = HOVER_TRANSPARENCY if hovered else IDLE_TRANSPARENCY
        material.diffuseColor.setValue(*color)
        material.emissiveColor.setValue(color[0] * 0.4, color[1] * 0.4, color[2] * 0.4)
        material.transparency.setValue(transparency)
        self._paint_ghost(region, color, hovered)

    def _paint_ghost(self, region, color, hovered):
        """The see-through copy takes the region's colour (stronger under the mouse and
        when picked), so a region behind the part answers the mouse like any other."""
        if self.ghost_root is None:
            return
        try:
            index = next(i for i, r in enumerate(self.regions) if r is region)
            material = self.ghosts[index] if index < len(self.ghosts) else None
            if material is None:
                return
            picked = (region[0].Name, region[1]) in self.selected
            material.diffuseColor.setValue(*color)
            material.emissiveColor.setValue(color[0] * 0.4, color[1] * 0.4, color[2] * 0.4)
            see = GHOST_TRANSPARENCY - (0.2 if picked else 0.0) - (0.15 if hovered else 0.0)
            material.transparency.setValue(see)
        except Exception:
            pass

    def set_selected(self, keys):
        """Show these regions {(sketch name, sub)} as picked."""
        self.selected = set(keys)
        for region in self.regions:
            self._paint(region, region is self.hovered)

    def show_faces(self, faces):
        """Highlight picked body faces (global coordinates)."""
        self.face_root.removeAllChildren()
        self.face_materials = []
        for face in faces:
            try:
                self.face_materials.append(
                    self._add_face(face, self.face_root, PICKED, self._picked_transparency())
                )
            except Exception as exc:
                warn("could not highlight a face: %s" % exc)

    def dim_picked(self, dim):
        """Fade the picked profiles' blue (while the dialog shows a cut in red: the strong
        blue on the profile plane hid the red), or bring it back."""
        dim = bool(dim)
        if dim == self.dimmed:
            return
        self.dimmed = dim
        for region in self.regions:
            self._paint(region, region is self.hovered)
        for material in self.face_materials:
            try:
                material.transparency.setValue(self._picked_transparency())
            except Exception:
                pass

    # -- events -------------------------------------------------------------------------
    def _moved(self, info):
        try:
            if self.on_curve is not None and not self.paused:
                curve = self.curve_at(info["Position"])
                self._hover_curve(curve)
                if curve is not None:
                    info = None  # on a curve: no area lights up under it
            hit = None if (self.paused or info is None) else self.region_at(info["Position"])
            if hit is not self.hovered:
                previous, self.hovered = self.hovered, hit
                if previous is not None:
                    self._paint(previous)
                if hit is not None:
                    self._paint(hit, hovered=True)
        except Exception as exc:
            warn("profile hover: %s" % exc)

    def _button(self, info):
        try:
            if info.get("Button") != "BUTTON1" or info.get("State") != "DOWN" or self.paused:
                return
            self.presses += 1
            # (On the press: FreeCAD's selection takes the release and stops it there.)
            position = tuple(info["Position"])
            if handle_at(self.view, position):
                return  # a drag handle sits in front of the region: the press drags it
            if self.on_curve is not None:
                curve = self.curve_at(position)
                if curve is not None:
                    self.last_click = time.time()
                    self.on_curve(curve[0], curve[1])
                    return
            hit = self.region_at(position, check_hidden=True)
            if hit is None and not self._part_at(position):
                # beside a thin slot or a small hole, with no face of a part under the
                # mouse (a click on a face next to an area means the face)
                hit = self.region_at(position, check_hidden=True, near=True)
            if hit is not None:
                self.last_click = time.time()
                self.last_click_at = position
                self.region_press = self.presses
                self.on_pick(hit[0], hit[1])
        except Exception as exc:
            warn("profile pick: %s" % exc)

    def clicked_region_recently(self, seconds=0.6):
        return time.time() - self.last_click < seconds

    def clicked_region_at(self, point, seconds=5.0, pixels=4.0):
        """True when the click that selected `point` (a 3D point FreeCAD's selection gives)
        is the very click this picker took on a region: the same spot on the screen, not
        long ago. FreeCAD selects the face under a region on the same click's release; on a
        busy computer that came more than clicked_region_recently's 0.6 s later, and the
        face was picked too (a sketch on a face, the book's Tesla Turbine nozzle holes: one
        of five hole profiles came with the face it lies on)."""
        try:
            at = getattr(self, "last_click_at", None)
            if at is None or point is None or time.time() - self.last_click >= seconds:
                return False
            if self.region_press != self.presses:
                return False  # a later click at the same spot (a face to end on) is its own
            x, y = self.view.getPointOnViewport(App.Vector(point))[:2]
            return abs(float(x) - at[0]) <= pixels and abs(float(y) - at[1]) <= pixels
        except Exception:
            return False

    def remove(self):
        for kind, callback in self.callbacks:
            try:
                self.view.removeEventCallback(kind, callback)
            except Exception:
                pass
        self.callbacks = []
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass
        for root, style in self.unpickable:
            try:
                index = root.findChild(style)
                if index >= 0:
                    root.removeChild(index)
            except Exception:
                pass  # the sketch was deleted with its scene
        self.unpickable = []
        self.regions = []
        self.ghosts = []


def _visible(sketch):
    try:
        view = sketch.ViewObject
        return bool(view.Visibility) if view is not None else bool(sketch.Visibility)
    except Exception:
        return False


def shown_part(base, to_global):
    """The solid of the step `base` in design coordinates, for a picker's occluder; None
    when there is none or its body is hidden (a hidden body is in front of nothing: with
    the body hidden its sketch's profiles could not be clicked, the book report's nozzle)."""
    try:
        if base is None or base.Shape.isNull():
            return None
        from . import bodies, extrude

        body = extrude.owner_body(base)
        if body is not None and not bodies.is_shown(body):
            return None
        return to_global(base.Shape, base)
    except Exception:
        return None


# -- which sketches can be extruded ------------------------------------------------------------
def used_sketches(doc):
    """Names of sketches some extrude-like feature already uses as its profile."""
    used = set()
    for obj in doc.Objects:
        # Sections: the other profiles of FreeCAD's Loft (they were offered again as unused)
        for prop in ("Profile", "Profiles", "Sections", "Support"):
            if prop not in obj.PropertiesList:
                continue
            value = getattr(obj, prop)
            for linked in _linked_objects(value):
                if linked.isDerivedFrom("Sketcher::SketchObject") and obj is not linked:
                    used.add(linked.Name)
    return used


def _linked_objects(value):
    if value is None:
        return []
    if hasattr(value, "Name"):
        return [value]
    found = []
    if isinstance(value, (list, tuple)):
        for item in value:
            if hasattr(item, "Name"):
                found.append(item)
            elif isinstance(item, (list, tuple)) and item and hasattr(item[0], "Name"):
                found.append(item[0])
    return found


def candidate_sketches(body, extra=(), include_hidden=False):
    """Sketches whose profiles are offered: every visible sketch of the document, and
    `extra` (the sketches of the extrude being edited, the sketch it was started from). A
    hidden sketch stays hidden, as in Fusion (Luca 2026-11-09: "when selecting a sketch to
    extrude, hidden sketches will be displayed. they should be hidden"); before, the body's
    unused sketches were offered even when hidden.
    include_hidden: the body's hidden unused sketches too, for curve_pick.prepare_regions,
    which turns on the areas of every sketch a dialog may come to offer before its undo step
    (a dialog can show a hidden sketch; its areas made inside the step emptied the Redo list:
    sweep_loft_qa_sweep P4, CI #26)."""
    doc = body.Document if body is not None else App.ActiveDocument
    if doc is None:
        return []
    used = used_sketches(doc)
    found, seen = [], set()

    def add(obj):
        if obj.Name not in seen:
            seen.add(obj.Name)
            found.append(obj)

    for obj in extra:
        add(obj)
    if body is not None:
        for obj in body.Group:  # the body's unused sketches first (their order is kept)
            if obj.isDerivedFrom("Sketcher::SketchObject") and obj.Name not in used:
                if include_hidden or _visible(obj):
                    add(obj)
    for obj in doc.Objects:
        if not obj.isDerivedFrom("Sketcher::SketchObject"):
            continue
        try:
            visible = obj.ViewObject.Visibility if obj.ViewObject is not None else obj.Visibility
        except Exception:
            visible = getattr(obj, "Visibility", False)
        if visible:
            add(obj)
    return found


def only_visible_profiles(body):
    """[(sketch, "InternalFaceN")]: Fusion's own automatic pick. "If there is one visible
    sketch, and if that sketch contains one profile, Extrude will auto-select that profile"
    (an Autodesk community manager; Autodesk's help: "only one profile visible in your
    design"). So: when exactly one of the shown sketches has areas, the areas Extrude takes
    from it by itself (its one area: extrude.taken_by_itself), else []. Whatever body or
    component the sketch is in (the book's nozzle: a new component's polygon was not
    picked, because it was not in the body Extrude looked in)."""
    from . import extrude

    try:
        doc = body.Document if body is not None else App.ActiveDocument
        if doc is None:
            return []
        having = []
        for obj in doc.Objects:
            if not obj.isDerivedFrom("Sketcher::SketchObject") or not _visible(obj):
                continue
            if extrude.profile_regions(obj) or text_areas(obj):
                having.append(obj)
                if len(having) > 1:
                    return []
        if len(having) != 1 or text_areas(having[0]):
            return []
        return [(having[0], name) for name in extrude.taken_by_itself(having[0])]
    except Exception as exc:
        warn("automatic profile: %s" % exc)
        return []


# -- faces picked in the 3D view ----------------------------------------------------------------
def same_face(a, b, tol=1e-6):
    """Geometric identity check that survives re-computation (same surface, size, position)."""
    if a.isSame(b):
        return True
    if a.Surface.TypeId != b.Surface.TypeId:
        return False
    if abs(a.Area - b.Area) > tol * max(1.0, a.Area):
        return False
    return (a.CenterOfMass - b.CenterOfMass).Length < 1e-5


def face_name_in(feature, face_global):
    """ "FaceN" of `feature`'s shape that is the same as the picked face, or None."""
    shape = feature.Shape
    face = face_global
    body = feature.getParentGeoFeatureGroup()
    if body is not None:
        face = face_global.copy()
        face.transformShape(body.getGlobalPlacement().inverse().toMatrix())
    for i, candidate in enumerate(shape.Faces, start=1):
        if same_face(face, candidate):
            return "Face%d" % i
    return None


def resolve(sel_obj, name):
    """(object, short element name) for a selection entry, through "Body.Pad.Face6" paths.
    A face picked on a Body is resolved to the Body's Tip."""
    obj, short = sel_obj, name
    if "." in name:
        path, short = name.rsplit(".", 1)
        inner = sel_obj.getSubObject(path + ".", retType=1)
        obj = inner if inner is not None else obj
    if (
        obj is not None
        and obj.TypeId == "PartDesign::Body"
        and short.startswith(("Face", "Edge", "Vertex"))
    ):
        obj = obj.Tip
    return obj, short


def picks():
    """[(object, short element name)] of the current selection ("" = the whole object)."""
    found = []
    for sel in Gui.Selection.getSelectionEx():
        for name in list(sel.SubElementNames) or [""]:
            obj, short = resolve(sel.Object, name)
            if obj is not None:
                found.append((obj, short))
    return found


GLYPH_TYPES = (
    "App::Plane",
    "App::Line",
    "App::Origin",
    "PartDesign::Plane",
    "PartDesign::Line",
    "Part::DatumPlane",
    "Part::DatumLine",
)
POINT_TYPES = ("App::Point", "PartDesign::Point", "Part::DatumPoint")


def is_glyph(obj):
    """True for an origin or construction plane / axis: the squares and lines drawn over
    the design. A click on one, in a box that cannot use it, is meant for what is behind
    it (the book report: "the offset plane's yellow square is drawn over the part and
    takes clicks meant for the face behind it")."""
    try:
        return obj.TypeId in GLYPH_TYPES
    except Exception:
        return False


def is_point_object(obj):
    """True for the origin point and construction points."""
    try:
        return obj.TypeId in POINT_TYPES
    except Exception:
        return False


def coin_pixel(widget, pos):
    """The Coin pixel (x, y from the bottom left) of a Qt position in the view's widget."""
    ratio = widget.devicePixelRatioF() or 1.0
    return (pos.x() * ratio, (widget.height() - pos.y()) * ratio)


def under(view, pixel, radius=None):
    """[(object, short element name, point)] of everything under the Coin pixel, the
    nearest first (FreeCAD's getObjectsInfo; "Body.Pad.Face6" paths resolved like
    resolve()). [] when nothing is there."""
    spot = (int(round(pixel[0])), int(round(pixel[1])))
    try:
        infos = view.getObjectsInfo(spot, radius) if radius else view.getObjectsInfo(spot)
    except Exception:
        return []
    found = []
    for info in infos or []:
        try:
            doc = App.getDocument(info["Document"])
            obj = doc.getObject(info["Object"])
            if obj is None:
                continue
            name = str(info.get("Component", "") or "")
            parent = info.get("ParentObject")
            if parent is not None and info.get("SubName"):
                obj, name = parent, str(info["SubName"])
            obj, short = resolve(obj, name)
            if obj is None:
                continue
            found.append((obj, short, App.Vector(info["x"], info["y"], info["z"])))
        except Exception:
            continue
    return found


def behind_glyphs(view, pixel, usable):
    """The first thing under the pixel that `usable(obj, short)` accepts, looking through
    origin / construction planes and axes only (a body in front still hides what is behind
    it). None when the nearest non-glyph thing is not usable."""
    for obj, short, point in under(view, pixel):
        if usable(obj, short):
            return obj, short, point
        if not is_glyph(obj):
            return None
    return None


def global_face(obj, short):
    """The face `short` of `obj` in global coordinates, or None."""
    from . import extrude

    try:
        face = obj.Shape.getElement(short)
    except Exception:
        return None
    return extrude._to_global(face, obj)
