# SPDX-License-Identifier: LGPL-2.1-or-later
"""Names as buttons, menus and tabs show them (no Qt: unit tested). taskui.set_names puts
them on a button."""


def shown_name(text):
    """A name as a button, a check box, a tab or a menu entry must be given it: Qt reads "&"
    there as the mark of a keyboard letter and drops it ("Nut & Bolt" showed as "Nut  Bolt")."""
    return str(text).replace("&", "&&")


def fit_names(text, width, measure, separator=", "):
    """`text` (names joined by ", ") shortened to `width` pixels: the first names that fit and
    how many more ("Arm, Base + 5 more"), one name too long cut with "…". measure(text) gives
    a text's width in pixels."""
    text = str(text)
    if width <= 0 or measure(text) <= width:
        return text
    names = text.split(separator)
    if len(names) > 1:
        for count in range(len(names) - 1, 0, -1):
            short = "%s + %d more" % (separator.join(names[:count]), len(names) - count)
            if measure(short) <= width:
                return short
        tail = " + %d more" % (len(names) - 1)
        head = names[0]
    else:
        tail, head = "", text
    while len(head) > 1 and measure(head + "…" + tail) > width:
        head = head[:-1]
    return head.rstrip() + "…" + tail
