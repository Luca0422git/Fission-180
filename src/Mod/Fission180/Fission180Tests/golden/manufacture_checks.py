# SPDX-License-Identifier: LGPL-2.1-or-later
"""The golden models' check for the MANUFACTURE steps (needs FreeCAD).

cam_expect {"target": a cam_operation step, "state": "valid", "bounds": [xmin, ymin, zmin,
xmax, ymax, zmax] of the tool's tip along the toolpath (setup coordinates), "cut_length":
mm of cutting moves, "rapid_length": mm, "min_z": the lowest cutting height, "time_s":
machining time, "tol": mm (default 0.01), "rel_tol": for the lengths and the time (default
0.001; FreeCAD's adaptive clearing does not give the same path twice: say 0.1 there)}
checks the toolpath FreeCAD's CAM engine made for that operation.

cam_expect {"target": a cam_setup step, "stock": [box], "model": [box], "origin": [x, y, z]
(where the setup's origin is in the design), "gcode": {"units": "mm", "min_z": z, "problems":
0, "lines_min": n} (the program of the last cam_post step for it, read by Fission 180's G-code
checker), "stale_after": true (every toolpath of the setup needs regenerating: an edit of
the design came before)} checks the setup.
"""

from .builder import BuildError, Builder


def _close(got, want, tol):
    return got is not None and abs(float(got) - float(want)) <= tol


def op_cam_expect(self, step):
    from fission180 import manufacture as cam

    target = self.objects.get(step["target"])
    tol = float(step.get("tol", 0.01))
    rel = float(step.get("rel_tol", 0.001))
    problems = []
    if cam.is_op(target):
        state = cam.state(target)
        if "state" in step and state != step["state"]:
            problems.append(
                "state is %s, expected %s (%s)"
                % (state, step["state"], cam.result(target).get("error"))
            )
        stats = cam.result(target).get("stats") or {}
        if "bounds" in step:
            got = stats.get("bounds") or []
            if len(got) != 6 or any(not _close(g, w, tol) for g, w in zip(got, step["bounds"])):
                problems.append("bounds are %s, expected %s" % (got, step["bounds"]))
        for key in ("cut_length", "rapid_length", "time_s"):
            if key in step:
                want = float(step[key])
                if not _close(stats.get(key), want, max(tol, rel * abs(want))):
                    problems.append("%s is %s, expected %s" % (key, stats.get(key), want))
        if "min_z" in step and not _close(stats.get("min_cut_z"), step["min_z"], tol):
            problems.append(
                "lowest cut is at Z %s, expected %s" % (stats.get("min_cut_z"), step["min_z"])
            )
    elif cam.is_setup(target):
        summary = cam.summary(target)
        for key, name in (("stock", "stock_box"), ("model", "model_box")):
            if key in step:
                got = summary[name]
                if any(not _close(g, w, tol) for g, w in zip(got, step[key])):
                    problems.append("%s box is %s, expected %s" % (key, got, step[key]))
        if "origin" in step:
            got = summary["origin"]
            if any(not _close(g, w, tol) for g, w in zip(got, step["origin"])):
                problems.append("the origin is at %s, expected %s" % (got, step["origin"]))
        if step.get("stale_after"):
            states = {o["label"]: o["state"] for o in summary["operations"]}
            if any(s != "stale" for s in states.values()):
                problems.append("every toolpath should need regenerating: %s" % states)
        if "gcode" in step:
            posted = getattr(self, "cam_posted", {}).get(step["target"])
            if posted is None:
                raise BuildError("cam_expect: no cam_post step ran for %r" % step["target"])
            check = posted["check"]
            want = step["gcode"]
            if "units" in want and check["units"] != want["units"]:
                problems.append(
                    "the program is in %s, expected %s" % (check["units"], want["units"])
                )
            if "min_z" in want and not _close(check["min_z"], want["min_z"], tol):
                problems.append(
                    "the program's lowest Z is %s, expected %s" % (check["min_z"], want["min_z"])
                )
            if "problems" in want and len(check["problems"]) != int(want["problems"]):
                problems.append("the G-code checker found: %s" % check["problems"])
            if "lines_min" in want and check["lines"] < int(want["lines_min"]):
                problems.append("the program has only %d lines" % check["lines"])
    else:
        raise BuildError("cam_expect: %r is no cam_setup or cam_operation step" % step["target"])
    if problems:
        raise BuildError("cam_expect %r: %s" % (step["target"], "; ".join(problems)))
    return target


Builder.op_cam_expect = op_cam_expect
