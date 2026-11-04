# SPDX-License-Identifier: LGPL-2.1-or-later
"""Remembers the last command run through Fission 180 (ribbon, keys, marking menu),
for Fusion's "Repeat <command>"."""

_last = {"name": None, "index": None, "label": None}
_history = []  # the names of the last few commands run, newest last (also unrepeatable ones)
HISTORY = 4
# Commands that end the running tool themselves and keep what it drew (Finish Sketch is
# OK for a spline being drawn): the tool running is still the one before them.
PASSING = {"Fission180_FinishSketch"}

# Commands that make no sense to repeat.
NOT_REPEATABLE = {
    "Std_Undo",
    "Std_Redo",
    "Std_Delete",
    "Fission180_CommandSearch",
    "__menu__",
    "Std_ViewFitAll",
    "Std_Save",
    "Std_Open",
    "Std_New",
    "Fission180_Save",
    "Fission180_SaveAs",
    "Fission180_RecoverySaveNow",
    "Fission180_VersionHistory",
    "Fission180_RecoverDocuments",
    "Fission180_DataPanel",
    "Fission180_FilesSettings",
    "Fission180_Home",
    "Fission180_ConnectPlace",
    "Fission180_AddAI",
    "Fission180_AIActivity",
    "Fission180_AIChat",
}


def record(name, label, index=None):
    if name:
        _history.append(name)
        del _history[:-HISTORY]
    if name and name not in NOT_REPEATABLE:
        _last.update(name=name, index=index, label=label)


def running_tool():
    """The name of the command whose tool may still be running: the last one run (as
    last()), past the PASSING ones (Finish Sketch, clicked while a spline is drawn, is
    recorded before it runs), or None."""
    for name in reversed(_history):
        if name not in PASSING and name not in NOT_REPEATABLE:
            return name
    return None


def last():
    """(name, index, label) of the last repeatable command, or None."""
    return (_last["name"], _last["index"], _last["label"]) if _last["name"] else None
