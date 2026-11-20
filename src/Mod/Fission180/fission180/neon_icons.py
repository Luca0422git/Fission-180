# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights icons (design 6.5, plan task A6). Scaffold: the normal icon until A6."""

import os


def enable():
    pass


def disable():
    pass


def refresh():
    pass


def path(name):
    """The neon icon file for `name`."""
    from . import ROOT

    return os.path.join(ROOT, "icons", "ui", name + ".svg")
