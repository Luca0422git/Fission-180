# SPDX-License-Identifier: LGPL-2.1-or-later
"""Commands pinned to the ribbon (Fusion's "Pin to Toolbar"): a pinned command gets a big
icon in its group's always-visible row, after the group's own icons.

Fusion (Autodesk forum, "Can't Pin to Toolbar"; "losing tools on tool bar", Autodesk staff):
hover a command in a panel's drop-down, its three-dot menu has Pin to Toolbar (and Unpin);
right-click the toolbar: Reset All Toolbar Customization (Fusion asks nothing; its users
asked for a confirmation, Fission 180 asks).

Any command can be taken off the toolbar, the group's own default icons too, and as many
pinned as wanted (Luca, 2026-11-06: "there is no way of unpinning already pinned tools. its a
set amount. I should be able to have as many or as little as i please").

Stored per tab and group as JSON in the parameter Mod/Fission180/Ribbon/Pinned: the commands
pinned on top of the group's own icons ("solid/modify": ["Coil", ...]) and the group's own
icons taken off ("solid/modify#off": ["Shell", ...]). The pure functions below take and
return that dict (unit tested); load() / save() talk to FreeCAD.
"""

import json

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Ribbon"
KEY = "Pinned"


OFF = "#off"  # the group's own icons taken off the toolbar


def slot(tab_id, group_id):
    return "%s/%s" % (tab_id, group_id)


def pinned(store, tab_id, group_id):
    """The commands pinned on top of the group's own icons, in the order they were pinned."""
    return list((store or {}).get(slot(tab_id, group_id), []))


def taken_off(store, tab_id, group_id):
    """The group's own icons taken off the toolbar."""
    return list((store or {}).get(slot(tab_id, group_id) + OFF, []))


def shown(store, tab_id, group_id, built_in=()):
    """The commands with a big icon in the group's row, in order: its own icons (but the
    ones taken off), then the pinned ones."""
    off = set(taken_off(store, tab_id, group_id))
    out = [label for label in built_in if label not in off]
    out += [label for label in pinned(store, tab_id, group_id) if label not in out]
    return out


def is_pinned(store, tab_id, group_id, label, built_in=()):
    """Whether the command has a big icon in the group's row (its own or pinned)."""
    return label in shown(store, tab_id, group_id, built_in)


def _copy(store):
    return {k: list(v) for k, v in (store or {}).items()}


def _set(result, key, row):
    if row:
        result[key] = row
    else:
        result.pop(key, None)


def pin(store, tab_id, group_id, label, built_in=()):
    """New store with `label` on the toolbar: one of the group's own icons taken off before
    comes back in its place; any other command is pinned at the end of the row (once)."""
    result = _copy(store)
    key = slot(tab_id, group_id)
    if label in built_in:
        _set(result, key + OFF, [x for x in result.get(key + OFF, []) if x != label])
        return result
    row = result.setdefault(key, [])
    if label not in row:
        row.append(label)
    return result


def unpin(store, tab_id, group_id, label, built_in=()):
    """New store with `label` off the toolbar (still in the group's drop-down): a pinned
    command is unpinned, one of the group's own icons is taken off."""
    result = _copy(store)
    key = slot(tab_id, group_id)
    _set(result, key, [x for x in result.get(key, []) if x != label])
    if label in built_in:
        off = result.get(key + OFF, [])
        if label not in off:
            off = off + [label]
        _set(result, key + OFF, off)
    return result


def load():
    try:
        import FreeCAD as App

        text = App.ParamGet(PARAMS).GetString(KEY, "")
        data = json.loads(text) if text else {}
        return {str(k): [str(x) for x in v] for k, v in data.items() if isinstance(v, list)}
    except Exception:
        return {}


def save(store):
    import FreeCAD as App

    App.ParamGet(PARAMS).SetString(KEY, json.dumps(store or {}, sort_keys=True))
