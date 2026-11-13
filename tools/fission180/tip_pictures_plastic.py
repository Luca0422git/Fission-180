# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltip pictures of the PLASTIC tab (wave 8, builder tips-workspaces):
tools/fission180/make_tip_pictures.sh plastic [picture ...].

The demo parts are built by Fission 180's own design steps (fission180/ai/ops, the code the
dialogs and the AI tools run; the step lists follow the golden models plastic_* and
plastic2_*), then rendered before and after the tool with what it made in the selection blue
(docs/fission180/dev/tip-pictures.md). The rule dialogs and Design Advice are shown as
Fission 180 shows them."""

import tip_pictures as tp
import tip_pictures_workspaces as ws

builder, build, body_of = ws.builder, ws.build, ws.body_of


def base(b, length=60, width=40, height=20, wall=2):
    """An open box (the bottom half of an enclosure)."""
    return build(
        b,
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, length, width]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": height},
        {
            "op": "shell",
            "id": "sh1",
            "faces": {"normal": [0, 0, 1], "count": 1},
            "thickness": wall,
        },
    )


def lid(b, length=60, width=40, at=20, height=10, wall=2):
    """The top half: an upside-down open box on the bottom half."""
    return build(
        b,
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": at,
            "geometry": [{"rect": [0, 0, length, width]}],
        },
        {
            "op": "extrude",
            "id": "e2",
            "profile": "s2",
            "distance": height,
            "operation": "new_body",
        },
        {
            "op": "shell",
            "id": "sh2",
            "faces": {"normal": [0, 0, -1], "count": 1},
            "thickness": wall,
        },
    )


trim_panel = ws.trim_panel


def tree_item(tree, text):
    """The first row of a QTreeWidget whose text starts with `text` (any depth)."""
    from fission180.compat import QtWidgets

    it = QtWidgets.QTreeWidgetItemIterator(tree)
    while it.value() is not None:
        item = it.value()
        if item.text(0).startswith(text):
            return item
        it += 1
    return None


# -- SETUP -------------------------------------------------------------------------------------
@tp.picture("pl_assign_rule.png")
def assign_rule():
    tp.new_design("Case")
    b = builder()
    base(b)
    tp.camera()
    shot = tp.render()
    tp.run_command("Fission180_AssignPlasticRule")
    panel = tp.wait_for_panel()
    from fission180 import plastic_rules_ui

    dialog = (
        plastic_rules_ui.AssignPanel.last if hasattr(plastic_rules_ui.AssignPanel, "last") else None
    )
    tree = getattr(getattr(dialog, "rules", None), "tree", None)
    if tree is not None:
        item = tree_item(tree, "ABS")
        if item is not None:
            tree.setCurrentItem(item)
            item.setExpanded(True)
    tp.settle()
    return tp.with_dialog(shot, trim_panel(tp.grab(panel)), width=170)


@tp.picture("pl_manage_rules.png")
def manage_rules():
    tp.new_design("Case")
    tp.run_command("Fission180_ManagePlasticRules")
    panel = tp.wait_for_panel()
    from fission180 import plastic_rules_ui

    dialog = plastic_rules_ui.ManagePanel.last
    item = tree_item(dialog.rules.tree, "ABS")
    if item is not None:
        dialog.rules.tree.setCurrentItem(item)
        dialog._button("edit")
    tp.settle()
    image = tp.grab(panel)
    # the rule's fields (the editor under the lists) are what the picture is about
    from fission180.compat import QtCore

    top = dialog.editor.mapTo(panel, QtCore.QPoint(0, 0)).y()
    height = min(dialog.editor.height() + 8, image.height - top)
    return tp.dialog_picture(image, area=(0, max(0, top - 4), image.width, height))


# -- CREATE ------------------------------------------------------------------------------------
@tp.picture("pl_boss.png")
def boss():
    """The bottom half with its screw bosses (the top half's bosses are made too, hidden
    here so the inside shows)."""
    tp.new_design("Case")
    b = builder()
    base(b)
    lid(b)
    bottom = body_of(b.objects["sh1"])
    top = body_of(b.objects["sh2"])
    old = bottom.Shape.copy()
    tp.hide(top)
    tp.camera(zoom=1.0)
    before = tp.render()
    build(
        b,
        {
            "op": "sf_boss",
            "id": "b1",
            "plane": "XY",
            "offset": 20,
            "points": [[10, 10], [50, 30]],
            "side1": {"draft": 0, "step_draft": 0, "root_radius": 0},
            "side2": {"draft": 0, "step_draft": 0, "root_radius": 0},
        },
    )
    tp.hide(top)
    after = tp.render(highlight={bottom: tp.new_faces(old, bottom)})
    return tp.before_after(before, after)


@tp.picture("pl_snap_fit.png")
def snap_fit():
    """A lid that clicks onto a box: the hook under the lid and the window in the box's wall
    it catches in (the lid see-through)."""
    tp.new_design("Case")
    b = builder()
    base(b)
    build(
        b,
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": 20,
            "geometry": [{"rect": [0, 0, 60, 40]}],
        },
        {"op": "extrude", "id": "e2", "profile": "s2", "distance": 2, "operation": "new_body"},
    )
    bottom = body_of(b.objects["sh1"])
    top = body_of(b.objects["e2"])
    old_bottom, old_top = bottom.Shape.copy(), top.Shape.copy()
    see_through(bottom, top)
    ws.look((-1, 0.25, -0.35), zoom=1.8)
    before = tp.render()
    build(
        b,
        {
            "op": "sf_snap_fit",
            "id": "sf1",
            "plane": "XY",
            "offset": 20,
            "points": [[58, 20]],
            "options": {
                "fillet": 0,
                "draft": 0,
                "thickness": 2,
                "tip_thickness": 2,
                "clearance": 0.1,
                "loop_thickness": 2,
                "length": 12,
                "width": 6,
                "catch_depth": 1,
                "catch_length": 3,
            },
        },
    )
    see_through(bottom, top)
    after = tp.render(
        highlight={
            bottom: tp.new_faces(old_bottom, bottom),
            top: tp.new_faces(old_top, top),
        }
    )
    return tp.before_after(before, after)


def see_through(*bodies):
    """Bodies drawn see-through (their shown step), so what is inside shows."""
    for body in bodies:
        for obj in (body, getattr(body, "Tip", None)):
            try:
                obj.ViewObject.Transparency = 65
            except Exception:
                pass


@tp.picture("pl_lip.png")
def lip():
    """A lip on the rim of a box (close up on one corner)."""
    tp.new_design("Case")
    b = builder()
    base(b, 40, 30, 14, 2)
    bottom = body_of(b.objects["sh1"])
    old = bottom.Shape.copy()
    tp.camera(zoom=1.0)
    before = tp.render()
    build(
        b,
        {
            "op": "sf_lip",
            "id": "l1",
            "of": "sh1",
            "edges": {
                "any_of": [
                    {
                        "type": "line",
                        "parallel": [1, 0, 0],
                        "at": [{"axis": "z", "value": 14}, {"axis": "y", "value": 2}],
                        "count": 1,
                    },
                    {
                        "type": "line",
                        "parallel": [1, 0, 0],
                        "at": [{"axis": "z", "value": 14}, {"axis": "y", "value": 28}],
                        "count": 1,
                    },
                    {
                        "type": "line",
                        "parallel": [0, 1, 0],
                        "at": [{"axis": "z", "value": 14}, {"axis": "x", "value": 2}],
                        "count": 1,
                    },
                    {
                        "type": "line",
                        "parallel": [0, 1, 0],
                        "at": [{"axis": "z", "value": 14}, {"axis": "x", "value": 38}],
                        "count": 1,
                    },
                ],
                "count": 4,
            },
            "options": {
                "type": "lip",
                "lip_width": 1,
                "lip_height": 1.5,
                "inner_draft": 0,
                "outer_draft": 0,
            },
        },
    )
    after = tp.render(highlight={bottom: tp.new_faces(old, bottom)})
    return tp.before_after(before, after)


@tp.picture("pl_rest.png")
def rest():
    tp.new_design("Bar")
    b = builder()
    build(
        b,
        {"op": "sketch", "id": "s1", "plane": "YZ", "geometry": [{"circle": [0, 0, 20]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 60},
    )
    bar = b.body
    old = bar.Shape.copy()
    tp.camera()
    before = tp.render()
    build(
        b,
        {
            "op": "sf_rest",
            "id": "r1",
            "plane": "XY",
            "offset": 22,
            "rect": [20, -6, 40, 6],
            "thickness": 2,
            "draft": 0,
        },
    )
    after = tp.render(highlight={bar: tp.new_faces(old, bar)})
    return tp.before_after(before, after)


# -- MODIFY ------------------------------------------------------------------------------------
@tp.picture("pl_rule_fillet.png")
def rule_fillet():
    """A rib on a plate: Rule Fillet on the rib's feature rounds every edge it made."""
    tp.new_design("Part")
    b = builder()
    build(
        b,
        {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]},
        {"op": "extrude", "id": "e1", "profile": "s1", "distance": 4},
        {
            "op": "sketch",
            "id": "s2",
            "plane": "XY",
            "offset": 4,
            "geometry": [{"rect": [8, 12, 42, 18]}],
        },
        {"op": "extrude", "id": "e2", "profile": "s2", "distance": 12},
    )
    part = b.body
    rib = b.objects["e2"]
    old = part.Shape.copy()
    tp.camera()
    made = tp.new_faces(b.objects["e1"], rib)
    before = tp.render(highlight={part: made})
    build(b, {"op": "rule_fillet", "id": "r1", "radius": 1.5, "features": ["e2"]})
    after = tp.render(highlight={part: tp.new_faces(old, part)})
    return tp.before_after(before, after)


# -- INSPECT -----------------------------------------------------------------------------------
@tp.picture("pl_design_advice.png")
def design_advice():
    """A box with a thick boss and walls without draft: the colours Design Advice puts on it,
    beside its list of issues."""
    tp.new_design("Case")
    b = builder()
    base(b)
    build(
        b,
        {
            "op": "sketch",
            "id": "s3",
            "plane": "XY",
            "offset": 2,
            "geometry": [{"circle": [15, 20, 6]}],
        },
        {"op": "extrude", "id": "e3", "profile": "s3", "distance": 10},
    )
    tp.camera()
    tp.run_command("Fission180_DesignAdvice")
    panel = tp.wait_for_panel()
    tp.settle()
    tp.wait(500)
    tp.settle()
    shot = tp.render()
    return tp.with_dialog(shot, trim_panel(tp.grab(panel)), width=170)
