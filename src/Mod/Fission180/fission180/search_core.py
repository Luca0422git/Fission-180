"""Fuzzy ranking for the command search box. Pure Python, no FreeCAD/Qt."""


def haystack(entry):
    return ("%s %s" % (entry.get("text", ""), entry.get("name", ""))).lower()


def _score_token(token, text):
    """Score one query token against text; None means no match."""
    index = text.find(token)
    if index >= 0:
        score = 100 - min(index, 50)
        if index == 0 or not text[index - 1].isalnum():
            score += 40  # starts a word
        return score
    # fall back to an in-order subsequence match ("flt" -> "fillet")
    pos = -1
    gaps = 0
    for ch in token:
        nxt = text.find(ch, pos + 1)
        if nxt < 0:
            return None
        if pos >= 0:
            gaps += nxt - pos - 1
        pos = nxt
    return max(1, 40 - gaps)


def score(query, entry):
    text = haystack(entry)
    tokens = query.lower().split()
    if not tokens:
        return 0
    total = 0
    for token in tokens:
        part = _score_token(token, text)
        if part is None:
            return None
        total += part
    # the whole phrase as the user typed it, in the name they see: first (Luca, 2026-11-04:
    # "Control Point Spline" ran FreeCAD's "Toggle B-Spline Control Point Weight")
    label = entry.get("text", "").lower()
    phrase = " ".join(tokens)
    if label == phrase:
        total += 400
    elif phrase in label:
        total += 200
    if entry.get("ribbon"):
        total += 30  # a Fission 180 menu entry before a FreeCAD command of the same words
    return total


def once(entries):
    """The entries without the ones a person reads as a repeat: a command listed under its
    own name although one of Fission 180's menus lists it already (book parity report:
    "Change Parameters" twice), and a second row with the same words and the same key (the
    first one stays: Fission 180's menu entries come first)."""
    in_menus = {e.get("name") for e in entries if e.get("ribbon")}
    seen, kept = set(), []
    for entry in entries:
        if not entry.get("ribbon") and entry.get("name") in in_menus:
            continue
        key = (" ".join(entry.get("text", "").lower().split()), entry.get("shortcut") or "")
        if key in seen:
            continue
        seen.add(key)
        kept.append(entry)
    return kept


def rank(query, entries, limit=30):
    """Best matches first, each row once. An empty query returns entries alphabetically."""
    if not query.strip():
        return once(sorted(entries, key=lambda e: e.get("text", "").lower()))[:limit]
    scored = []
    for entry in entries:
        value = score(query, entry)
        if value is not None:
            scored.append((-value, len(haystack(entry)), entry))
    scored.sort(key=lambda t: (t[0], t[1]))
    return once([entry for _, _, entry in scored])[:limit]
