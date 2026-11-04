# SPDX-License-Identifier: LGPL-2.1-or-later
"""The AI tools that are not design steps (fission180/ai/catalog says which): reading the
design, the timeline, parameters, design files, drawings, the view, sketch editing,
assembly, the checking tools (verify_actions) and the documentation tools (docs_actions).
Each action is a function (ctx, args) -> bridge_core result, registered with
@action("tool name"); fission180/ai/executor.py calls it after the arguments were checked and
the tool is available. Actions call the same Fission 180 code as the commands and dialogs
(timeline_ops, parameters, drawing, joints...), never raw FreeCAD calls that would skip
Fission 180's behaviour. Needs FreeCAD."""

ACTIONS = {}


def action(name):
    def register(fn):
        ACTIONS[name] = fn
        return fn

    return register


from . import document_actions  # noqa: E402,F401
from . import inspect_actions  # noqa: E402,F401
from . import sketch_actions  # noqa: E402,F401
from . import timeline_actions  # noqa: E402,F401
from . import assemble_actions  # noqa: E402,F401
from . import drawing_actions  # noqa: E402,F401
from . import view_actions  # noqa: E402,F401
from . import verify_actions  # noqa: E402,F401
from . import docs_actions  # noqa: E402,F401
from . import simulate_actions  # noqa: E402,F401  (beta 3)
from . import rebuild_actions  # noqa: E402,F401  (beta 3)
