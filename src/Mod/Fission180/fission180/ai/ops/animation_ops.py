# SPDX-License-Identifier: LGPL-2.1-or-later
"""Design steps for the ANIMATION workspace (storyboards, exploded views), built with the same
Fission 180 code its dialogs use (fission180/animation.py), registered on core.Builder when the
package is imported. The step format is checked by Fission180Tests/golden/animation_schema.py;
what a storyboard does is checked by the golden models' anim_expect step
(golden/animation_checks.py).

A component is named by a step that made it or a body in it (a sf_primitive with operation
new_component, a components_from_bodies step). Times are seconds on the storyboard's
timeline; "at" is where the playhead stands when the command runs (0: the scratch zone, the
storyboard then starts that way and no action is recorded).

  {"op": "anim_storyboard", "id": "sb1", "name": "Explode", "clean": true}
      STORYBOARD > New Storyboard. clean false: Start from end of previous.

  {"op": "anim_explode", "storyboard": "sb1", "at": 2, "levels": "one", "of": ["k1"],
   "scale": 1, "sequential": false, "trails": false}
      TRANSFORM > Auto Explode: One Level / All Levels ("all") of the components named in
      "of" (none: the whole design), with the Explosion Scale, One-Step or Sequential.

  {"op": "anim_manual_explode", "storyboard": "sb1", "at": 2,
   "picks": [{"of": "k1", "axis": "Z+"}], "distance": 10, "scale": 1, "sequential": false}
      TRANSFORM > Manual Explode: each picked component along its axis (X+ X- Y+ Y- Z+ Z-).

  {"op": "anim_transform", "storyboard": "sb1", "at": 2, "of": ["k1"], "move": [0, 0, 10],
   "axis": [0, 0, 1], "angle": 90, "pivot": [0, 0, 0]}
      TRANSFORM > Transform Components by numbers, in design coordinates: a turn about the
      axis through the pivot (default: the middle of the components), then the move.

  {"op": "anim_restore_home", "storyboard": "sb1", "at": 4, "of": ["k1"]}
  {"op": "anim_show_hide", "storyboard": "sb1", "at": 2, "of": ["k1"], "show": false}
  {"op": "anim_reverse", "storyboard": "sb1"}
      the storyboard tab's Reverse: it plays backwards from now on
"""

from .core import Builder, BuildError


def _animation():
    from fission180 import animation

    return animation


def component_of_step(self, name, what):
    """The component a step stands for: the component it made, or the one its body is in."""
    from fission180 import bodies, components

    obj = self.objects.get(name)
    if obj is None:
        raise BuildError("%s: no step named %r" % (what, name))
    if components.is_component(obj):
        return obj
    body = obj if components.is_body(obj) else bodies.body_of(obj)
    comp = components.container_of(body) if body is not None else None
    if comp is None:
        raise BuildError(
            "%s: step %r is not in a component (an animation moves components)" % (what, name)
        )
    return comp


def storyboard_name(self, key, what):
    names = getattr(self, "storyboards", {})
    if key not in names:
        raise BuildError("%s: no anim_storyboard step named %r" % (what, key))
    return names[key]


def _remember_design(self):
    """The components' placements before the first animation step: no step may change them."""
    if getattr(self, "anim_home", None) is None:
        import FreeCAD as App

        animation = _animation()
        self.anim_home = {c.Name: App.Placement(c.Placement) for c in animation.movables(self.doc)}


def _targets(self, step, what):
    return [component_of_step(self, name, what) for name in step.get("of", [])]


def _run(this, fn, *args, **kwargs):
    animation = _animation()
    try:
        return fn(*args, **kwargs)
    except animation.AnimationError as exc:
        raise BuildError("%s: %s" % (this["op"], exc))


def op_anim_storyboard(self, step):
    animation = _animation()
    _remember_design(self)
    name = _run(
        step,
        animation.new_storyboard,
        self.doc,
        step.get("name"),
        bool(step.get("clean", True)),
    )
    if not hasattr(self, "storyboards"):
        self.storyboards = {}
    self.storyboards[step["id"]] = name
    self.ops[step["id"]] = "anim_storyboard"
    return animation.store(self.doc)


def op_anim_explode(self, step):
    animation = _animation()
    _remember_design(self)
    name = storyboard_name(self, step["storyboard"], "anim_explode")
    _run(
        step,
        animation.auto_explode,
        self.doc,
        name,
        float(step.get("at", 0.0)),
        _targets(self, step, "anim_explode"),
        step.get("levels", "one"),
        float(step.get("scale", 1.0)),
        bool(step.get("sequential", False)),
        step.get("trails"),
    )
    return animation.store(self.doc)


def op_anim_manual_explode(self, step):
    animation = _animation()
    _remember_design(self)
    name = storyboard_name(self, step["storyboard"], "anim_manual_explode")
    picks = [
        (component_of_step(self, pick["of"], "anim_manual_explode"), pick["axis"])
        for pick in step["picks"]
    ]
    _run(
        step,
        animation.manual_explode,
        self.doc,
        name,
        float(step.get("at", 0.0)),
        picks,
        float(step["distance"]),
        float(step.get("scale", 1.0)),
        bool(step.get("sequential", False)),
        step.get("trails"),
    )
    return animation.store(self.doc)


def op_anim_transform(self, step):
    animation = _animation()
    _remember_design(self)
    name = storyboard_name(self, step["storyboard"], "anim_transform")
    _run(
        step,
        animation.transform,
        self.doc,
        name,
        float(step.get("at", 0.0)),
        _targets(self, step, "anim_transform"),
        tuple(step.get("move", (0, 0, 0))),
        tuple(step.get("axis", (0, 0, 1))),
        float(step.get("angle", 0.0)),
        tuple(step["pivot"]) if "pivot" in step else None,
        step="Transform Components",
    )
    return animation.store(self.doc)


def op_anim_restore_home(self, step):
    animation = _animation()
    name = storyboard_name(self, step["storyboard"], "anim_restore_home")
    _run(
        step,
        animation.restore_home,
        self.doc,
        name,
        float(step.get("at", 0.0)),
        _targets(self, step, "anim_restore_home"),
    )
    return animation.store(self.doc)


def op_anim_show_hide(self, step):
    animation = _animation()
    _remember_design(self)
    name = storyboard_name(self, step["storyboard"], "anim_show_hide")
    _run(
        step,
        animation.show_hide,
        self.doc,
        name,
        float(step.get("at", 0.0)),
        _targets(self, step, "anim_show_hide"),
        step.get("show"),
    )
    return animation.store(self.doc)


def op_anim_reverse(self, step):
    animation = _animation()
    name = storyboard_name(self, step["storyboard"], "anim_reverse")
    _run(step, animation.reverse_storyboard, self.doc, name)
    return animation.store(self.doc)


Builder.op_anim_storyboard = op_anim_storyboard
Builder.op_anim_explode = op_anim_explode
Builder.op_anim_manual_explode = op_anim_manual_explode
Builder.op_anim_transform = op_anim_transform
Builder.op_anim_restore_home = op_anim_restore_home
Builder.op_anim_show_hide = op_anim_show_hide
Builder.op_anim_reverse = op_anim_reverse
