# SPDX-License-Identifier: LGPL-2.1-or-later
# Application bar icons (wave 7, shell): the "+" beside the design tabs, the profile button
# at the top right (its menu holds Preferences) and the Data Panel's projects. Run inside
# make_icons.py's namespace (path, circle, line, ... are its helpers). Original artwork in the
# style of the other quick-access icons.
# flake8: noqa


@icon("qa_plus")
def _():
    # a plus: a new design tab
    return line(24, 10, 24, 38, STROKE, 3.2) + line(10, 24, 38, 24, STROKE, 3.2)


@icon("qa_profile")
def _():
    # a person in a ring: the profile menu (Preferences)
    return (
        circle(24, 24, 18, "none", STROKE, 2.4)
        + circle(24, 19, 6, "none", STROKE, 2.4)
        + path("M12 37 A12 10 0 0 1 36 37", STROKE, 2.4)
    )


@icon("project")
def _():
    # a folder with a mark on its front: a project of the Data Panel
    return (
        path("M6 14 H18 L22 18 H42 V38 H6 Z", STROKE, 2.4)
        + path("M17 28 H31 M24 22 V34", STROKE, 2.2)
    )
