# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book replay, project 13: the Tesla Turbine (Mastering Autodesk Fusion, 2nd ed.,
pp 156-176; the book parity report, lines 2147-2281). In one design, in the report's order,
by real input only, with a person's defaults. The report built the housing to the book's
dimensions and tried every other tool on simplified parts; so does this replay, with the
stand-ins named in each part's steps file (replay_13_*_steps.py).
"""

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_13_assembly_steps as assembly
from Fission180Tests.gui import replay_13_housing_steps as housing
from Fission180Tests.gui import replay_13_walls_steps as walls
from Fission180Tests.gui import replay_e_steps as r


def split(steps, at):
    cut = [x.__name__ for x in steps].index(at)
    return steps[:cut], steps[cut:]


housing_a, housing_b = split(housing.steps(), "extrude_key")
housing_b, housing_c = split(housing_b, "show_sketch1")
housing_c, housing_d = split(housing_c, "fillet_key")
SECTIONS = [("housing", housing_a), ("housing2", housing_b), ("housing3", housing_c)]
SECTIONS += [("housing4", housing_d)]
walls_all = walls.steps()
second = [x.__name__ for x in walls_all].index("activate_stator_subassembly", 1)
walls_b, walls_c = walls_all[:second], walls_all[second:]
walls_c, walls_d = split(walls_c, "wall_extrude_key")
walls_d, walls_e = split(walls_d, "steam_mirror_open")
SECTIONS += [("gaskets", walls_b), ("wall", walls_c), ("wall2", walls_d), ("steam", walls_e)]
assembly_all = assembly.steps()
assembly_a, assembly_b = split(assembly_all, "power_back")
assembly_b, assembly_c = split(assembly_b, "circular_open")
SECTIONS += [("sliders", assembly_a), ("screw", assembly_b), ("patterns", assembly_c)]

h.run("replay_13_tesla_turbine", r.assemble(SECTIONS), paced_by="state")
