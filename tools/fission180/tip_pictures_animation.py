# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltip pictures of the ANIMATION workspace (wave 8, builder tips-workspaces):
tools/fission180/make_tip_pictures.sh animation [picture ...].

A small assembly (a base, its lid, two side pins; a two-part hinge for All Levels) is made of
components, the ANIMATION workspace is entered, and the storyboard actions are recorded by
Fission 180's own animation steps (fission180/ai/ops/animation_ops.py: the code the dialogs
run). Each picture shows the storyboard at its start and at its end (the playhead moved, as a
person scrubs), the components that move drawn in the selection blue; the dialogs and the
timeline are shown as Fission 180 shows them."""

import tip_pictures as tp
import tip_pictures_workspaces as ws

BLUE = tuple(c / 255.0 for c in tp.BLUE)
BACK = (-0.7, -1, -0.75)  # from the back right: the hinge on the back shows


def assembly(hinge=False):
    """Base, Lid (on the base), Right and Left pins; with hinge, a Hinge component holding
    two leaves on the back. Returns the builder (its objects: base, lid, right, left...)."""
    tp.new_design("Box")
    b = ws.builder()
    ws.build(
        b,
        {
            "op": "sf_primitive",
            "id": "b_base",
            "kind": "box",
            "plane": "XY",
            "x": 0,
            "y": 0,
            "length": 60,
            "width": 40,
            "height": 10,
            "operation": "new_body",
        },
        {
            "op": "sf_primitive",
            "id": "b_lid",
            "kind": "box",
            "plane": "XY",
            "x": 0,
            "y": 0,
            "length": 60,
            "width": 40,
            "height": 4,
            "operation": "new_body",
        },
        {
            "op": "sf_primitive",
            "id": "b_right",
            "kind": "box",
            "plane": "XY",
            "x": 60,
            "y": 15,
            "length": 12,
            "width": 10,
            "height": 6,
            "operation": "new_body",
        },
        {
            "op": "sf_primitive",
            "id": "b_left",
            "kind": "box",
            "plane": "XY",
            "x": -12,
            "y": 15,
            "length": 12,
            "width": 10,
            "height": 6,
            "operation": "new_body",
        },
        {"op": "components_from_bodies", "id": "base", "bodies": ["b_base"], "label": "Base"},
        {"op": "components_from_bodies", "id": "lid", "bodies": ["b_lid"], "label": "Lid"},
        {"op": "components_from_bodies", "id": "right", "bodies": ["b_right"], "label": "Right"},
        {"op": "components_from_bodies", "id": "left", "bodies": ["b_left"], "label": "Left"},
        {
            "op": "component_move",
            "id": "m_lid",
            "components": ["lid"],
            "move_type": "translate",
            "dz": 10,
        },
    )
    if hinge:
        _hinge(b)
    # the empty first body of the new design is not a part of the assembly
    return b


def _hinge(b):
    """A Hinge component on the back of the base holding two leaves (a subassembly)."""
    from fission180 import bodies, components

    ws.build(
        b,
        {
            "op": "sf_primitive",
            "id": "b_leaf1",
            "kind": "box",
            "plane": "XY",
            "x": 18,
            "y": 40,
            "length": 10,
            "width": 3,
            "height": 12,
            "operation": "new_body",
        },
        {
            "op": "sf_primitive",
            "id": "b_leaf2",
            "kind": "box",
            "plane": "XY",
            "x": 32,
            "y": 40,
            "length": 10,
            "width": 3,
            "height": 12,
            "operation": "new_body",
        },
    )
    doc = tp.doc()
    hinge = components.new_component(doc, "Hinge")
    leaves = [bodies.body_of(b.objects[k]) for k in ("b_leaf1", "b_leaf2")]
    made = components.from_bodies(doc, leaves, parent=hinge)
    made[0].Label, made[1].Label = "Leaf 1", "Leaf 2"
    b.objects["hinge"] = hinge
    tp.recompute()


def enter():
    from fission180 import animation_ui

    if not animation_ui.enter_workspace():
        raise RuntimeError("the ANIMATION workspace did not open")
    tp.settle()


def leave():
    try:
        from fission180 import animation_ui

        animation_ui.leave_workspace()
        tp.settle()
    except Exception as exc:
        tp.log("leaving ANIMATION: %s" % exc)


def at(t):
    """Show the storyboard at time t (the playhead moved there; the camera stays)."""
    from fission180 import animation_ui

    animation_ui.set_playhead(t, camera=False)
    tp.settle()


def paint(b, keys, colour=BLUE):
    """Draw the bodies of the named components in a colour (back to grey with colour=None)."""
    from fission180 import bodies

    for key in keys:
        comp = b.objects[key]
        for obj in comp.OutListRecursive if hasattr(comp, "OutListRecursive") else []:
            if bodies.is_body(obj) or obj.TypeId.startswith("PartDesign::"):
                try:
                    obj.ViewObject.ShapeColor = colour or (0.8, 0.8, 0.8)
                except Exception:
                    pass
    tp.settle()


def start_and_end(b, end, moved, camera=(-1, 1, -0.8)):
    """The storyboard at 0 and at `end`, one camera for both (framed on the end)."""
    at(end)
    ws.look(camera)
    at(0)
    before = tp.render()
    at(end)
    paint(b, moved)
    after = tp.render()
    return tp.before_after(before, after, labels=("Start", "End"))


def storyboard(b):
    ws.build(b, {"op": "anim_storyboard", "id": "sb1"})


def picture_of_panel(open_it, shot=None, width=160):
    """A command's dialog, beside a render of the model when one is given."""
    open_it()
    panel = tp.wait_for_panel()
    tp.settle()
    image = ws.trim_panel(tp.grab(panel))
    if shot is None:
        return tp.dialog_picture(image)
    return tp.with_dialog(shot, image, width=width)


# -- STORYBOARD --------------------------------------------------------------------------------
@tp.picture("anim_new_storyboard.png")
def new_storyboard():
    b = assembly()
    del b
    enter()
    try:
        ws.look((-1, 1, -0.8))
        shot = tp.render()
        return picture_of_panel(lambda: tp.run_command("Fission180_AnimNewStoryboard"), shot)
    finally:
        leave()


# -- TRANSFORM ---------------------------------------------------------------------------------
@tp.picture("anim_transform.png")
def transform():
    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(
            b,
            {
                "op": "anim_transform",
                "storyboard": "sb1",
                "at": 2,
                "of": ["lid"],
                "move": [0, 0, 25],
                "axis": [0, 0, 1],
                "angle": 45,
                "pivot": [30, 20, 0],
            },
        )
        return start_and_end(b, 2, ["lid"])
    finally:
        leave()


@tp.picture("anim_restore_home.png")
def restore_home():
    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(
            b,
            {
                "op": "anim_transform",
                "storyboard": "sb1",
                "at": 2,
                "of": ["lid"],
                "move": [0, 0, 30],
            },
            {"op": "anim_restore_home", "storyboard": "sb1", "at": 4, "of": ["lid"]},
        )
        at(2)
        ws.look((-1, 1, -0.8))
        before = tp.render()
        at(4)
        paint(b, ["lid"])
        after = tp.render()
        return tp.before_after(before, after, labels=("Moved", "Home"))
    finally:
        leave()


@tp.picture("anim_explode_one.png")
def explode_one():
    b = assembly(hinge=True)
    enter()
    try:
        storyboard(b)
        ws.build(b, {"op": "anim_explode", "storyboard": "sb1", "at": 2, "levels": "one"})
        return start_and_end(b, 2, ["lid", "right", "left", "hinge"], camera=BACK)
    finally:
        leave()


@tp.picture("anim_explode_all.png")
def explode_all():
    b = assembly(hinge=True)
    enter()
    try:
        storyboard(b)
        ws.build(b, {"op": "anim_explode", "storyboard": "sb1", "at": 2, "levels": "all"})
        return start_and_end(b, 2, ["lid", "right", "left", "hinge"], camera=BACK)
    finally:
        leave()


@tp.picture("anim_explode_manual.png")
def explode_manual():
    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(
            b,
            {
                "op": "anim_manual_explode",
                "storyboard": "sb1",
                "at": 2,
                "picks": [{"of": "right", "axis": "X+"}, {"of": "lid", "axis": "Z+"}],
                "distance": 25,
            },
        )
        return start_and_end(b, 2, ["right", "lid"])
    finally:
        leave()


@tp.picture("anim_show_hide.png")
def show_hide():
    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(
            b, {"op": "anim_show_hide", "storyboard": "sb1", "at": 2, "of": ["lid"], "show": False}
        )
        at(0)
        ws.look((-1, 1, -0.8))
        paint(b, ["lid"])
        before = tp.render()
        at(2)
        after = tp.render()
        return tp.before_after(before, after, labels=("Start", "Lid hidden"))
    finally:
        leave()


# -- ANNOTATION --------------------------------------------------------------------------------
@tp.picture("anim_callout.png")
def callout():
    from fission180 import animation, animation_ui

    b = assembly()
    enter()
    try:
        storyboard(b)
        doc = tp.doc()
        animation.add_callout(
            doc,
            animation_ui.current(doc),
            1.0,
            "Lid: ABS",
            (50, 30, 14),
            b.objects["lid"],
        )
        animation_ui.refresh(camera=False)
        at(1)
        ws.look((-1, 1, -0.8))
        shot = tp.render()
        # framed on the callout (its pin and its words), with the part around it
        import FreeCAD as App

        x, y = tp._projector(tp.view(), (1.0, 1.0 / tp.ASPECT))(App.Vector(50, 30, 14))
        y *= tp.ASPECT
        box = (x - 0.28, y - 0.2, x + 0.22, y + 0.2)
        return tp._frame(shot, box, tp.SIZE, margin=0.0)
    finally:
        leave()


# -- VIEW --------------------------------------------------------------------------------------
@tp.picture("anim_view.png")
def view():
    """The ANIMATION TIMELINE with the View row a camera move was recorded on."""
    from fission180 import animation_timeline_ui, animation_ui

    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(b, {"op": "anim_explode", "storyboard": "sb1", "at": 3, "levels": "one"})
        at(3)
        v = tp.view()
        v.viewIsometric()
        v.fitAll()
        tp.settle()
        at(4)
        v.viewFront()
        v.fitAll()
        tp.settle()
        tp.wait(600)  # input pace: the view must come to rest before it is recorded
        tp.settle()
        animation_ui.refresh()
        tp.settle()
        widget = animation_timeline_ui.widget()
        image = tp.grab(widget)
        # the rows and the first seconds: the View row and the bars, readable
        return tp.dialog_picture(image, area=(0, 0, min(image.width, 560), image.height))
    finally:
        leave()


# -- PUBLISH -----------------------------------------------------------------------------------
@tp.picture("anim_publish_video.png")
def publish_video():
    b = assembly()
    enter()
    try:
        storyboard(b)
        ws.build(b, {"op": "anim_explode", "storyboard": "sb1", "at": 2, "levels": "one"})
        at(2)
        ws.look((-1, 1, -0.8))
        shot = tp.render()
        return picture_of_panel(lambda: tp.run_command("Fission180_AnimPublishVideo"), shot, 170)
    finally:
        leave()
