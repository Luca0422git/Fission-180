# SPDX-License-Identifier: LGPL-2.1-or-later
"""The tooltip pictures of the SIMULATION workspace's SETUP and RESULTS tabs (wave 8, builder
tips-workspaces): tools/fission180/make_tip_pictures.sh simulation [picture ...].

The demo is a steel L bracket (a plate with a hole on an upright): the upright's back face is
Fixed (a wall), 200 N push down on the plate's end. The study, its items and its solve are
Fission 180's own (fission180/simulation.py: the code the dialogs run; CalculiX solves it in
about a second). SETUP pictures show the glyphs on the model or the command's window; RESULTS
pictures show the coloured result (the legend beside it) as the RESULTS tab draws it, or the
window the command opens."""

import tip_pictures as tp
import tip_pictures_workspaces as ws

CAMERA = (-1, 1, -0.75)


# -- the demo ----------------------------------------------------------------------------------
def bracket_shape():
    import FreeCAD as App
    import Part

    plate = Part.makeBox(80, 20, 6)
    upright = Part.makeBox(6, 20, 40)
    shape = plate.fuse(upright).removeSplitter()
    return shape.cut(Part.makeCylinder(4, 6, App.Vector(55, 10, 0)))


def body_of_shape(shape, label):
    """A body whose base feature is `shape` (as sim_benchmarks.make_body)."""
    from fission180 import bodies

    doc = tp.doc()
    base = doc.addObject("Part::Feature", label + "Shape")
    base.Shape = bodies.baked(shape)
    body = doc.addObject("PartDesign::Body", label)
    body.BaseFeature = base
    tp.recompute()
    base.ViewObject.Visibility = False
    return body


def faces(body, test):
    return ["Face%d" % (i + 1) for i, f in enumerate(body.Shape.Faces) if test(f)]


def wall_face(body):
    return faces(body, lambda f: abs(f.CenterOfMass.x) < 1e-6 and f.Area > 700)


def end_face(body):
    return faces(body, lambda f: abs(f.CenterOfMass.x - 80) < 1e-6)


def hole_face(body):
    return faces(body, lambda f: f.Surface.__class__.__name__ == "Cylinder")


def bracket(constraint=True, load=True, extra=None):
    """A new design with the bracket and a study (the design's own first body is empty)."""
    from fission180 import simulation as sim

    tp.new_design("Bracket")
    body = body_of_shape(bracket_shape(), "Bracket")
    study = sim.create_study(tp.doc())
    if constraint:
        sim.add_item(study, "constraint", "fixed", [(body, n) for n in wall_face(body)])
    if load:
        sim.add_item(
            study,
            "load",
            "force",
            [(body, n) for n in end_face(body)],
            {"direction": "vector", "vector": [0, 0, -1], "magnitude": 200.0},
        )
    if extra:
        extra(study, body)
    tp.recompute()
    return body, study


def enter(tab=None):
    from fission180 import simulation_ui

    if not simulation_ui.enter_workspace(tab):
        raise RuntimeError("the SIMULATION workspace did not open")
    tp.settle()
    simulation_ui.refresh()
    tp.settle()


def leave():
    try:
        from fission180 import simulation_results_ui, simulation_ui

        for widget in _sim_windows():
            try:
                widget.close()
            except Exception:
                pass
        import FreeCADGui as Gui

        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()
        if simulation_results_ui.current() is not None:
            simulation_results_ui.finish()
        simulation_ui.leave_workspace()
        tp.settle()
    except Exception as exc:
        tp.log("leaving SIMULATION: %s" % exc)


def _sim_windows():
    from fission180.compat import QtWidgets

    out = []
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            name = widget.metaObject().className()
            if (
                widget.isVisible()
                and isinstance(widget, QtWidgets.QDialog)
                and name != "QFileDialog"
            ):
                out.append(widget)
        except Exception:
            continue
    return out


def solve(study, wait_s=300):
    """Solve as the Solve dialog does (the job, its progress, the results shown at the end)."""
    from fission180 import simulation_solve_dialog

    if not simulation_solve_dialog.start([study]):
        raise RuntimeError("the solve did not start")
    tp.wait_for(lambda: not simulation_solve_dialog.solving(), "the solve to end", wait_s)
    tp.settle()
    for widget in _sim_windows():  # the progress window
        if widget.metaObject().className() != "QMessageBox":
            widget.close()
    tp.settle()


def results(study):
    """The RESULTS tab on the solved study: its session (simulation_results_ui.Session)."""
    from fission180 import simulation_results_ui, simulation_ui

    simulation_ui.show_results(study)
    tp.settle()
    session = simulation_results_ui.current()
    if session is None:
        raise RuntimeError("the results did not show")
    return session


def window(cls_name):
    """The shown top-level window whose class is named cls_name."""
    for widget in _sim_windows():
        if widget.metaObject().className() == cls_name or type(widget).__name__ == cls_name:
            return widget
    return None


def grab_window(cls_name, what):
    tp.wait_for(lambda: window(cls_name) is not None, what)
    tp.settle()
    w = window(cls_name)
    image = tp.grab(w)
    w.close()
    tp.settle()
    return image


def legend_picture(session, shot):
    """The result render framed on the right, the legend (as the RESULTS tab shows it) on the
    left: what a person sees."""
    from PIL import Image

    out = Image.new("RGB", tp.SIZE, tp.BACKGROUND)
    legend = tp.grab(session.legend)
    scale = min(96.0 / legend.width, 188.0 / legend.height)
    small = legend.resize(
        (max(1, int(legend.width * scale)), max(1, int(legend.height * scale))), Image.LANCZOS
    )
    model_w = tp.SIZE[0] - small.width - 8
    model = tp._frame(shot, shot.box, (model_w, tp.SIZE[1]))
    out.paste(model, (tp.SIZE[0] - model_w, 0))
    out.paste(small, (4, 6))
    return out


def view_picture(body, margin=0.1):
    """The 3D view as the window shows it, with what floats over it (the min / max and probe
    tags), cut to the picture's shape around the part."""
    from PIL import Image

    from fission180 import simulation_results_view as srv

    gl = srv.gl_widget_of(tp.doc().Name)
    widget = srv.overlay_parent(gl)
    image = tp.grab(widget)
    ratio = gl.devicePixelRatioF()
    xs, ys = [], []
    for vertex in body.Shape.Vertexes:
        x, y = tp.view().getPointOnViewport(vertex.Point)
        where = srv.in_parent(gl, x / ratio, gl.height() - y / ratio)
        xs.append(where.x())
        ys.append(where.y())
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    cx, cy = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    w, h = w * (1 + 2 * margin), h * (1 + 2 * margin)
    aspect = tp.SIZE[0] / float(tp.SIZE[1])
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    w, h = min(w, image.width), min(h, image.height)
    left = min(max(0, cx - w / 2), image.width - w)
    top = min(max(0, cy - h / 2), image.height - h)
    crop = (int(left), int(top), int(left + w), int(top + h))
    return image.crop(crop).resize(tp.SIZE, Image.LANCZOS)


def solved(extra=None):
    body, study = bracket(extra=extra)
    enter()
    solve(study)
    session = results(study)
    ws.look(CAMERA)
    return body, study, session


# -- SETUP: STUDY, MATERIALS ---------------------------------------------------------------------
@tp.picture("sim_new_study.png")
def new_study():
    from fission180 import simulation_dialogs

    tp.new_design("Bracket")
    body_of_shape(bracket_shape(), "Bracket")
    enter()  # no study yet: the New Study window opens by itself
    try:
        tp.wait_for(
            lambda: simulation_dialogs.new_study_dialog() is not None, "the New Study window"
        )
        tp.settle()
        dialog = simulation_dialogs.new_study_dialog()
        image = tp.grab(dialog)
        dialog.reject()
        return tp.dialog_picture(image)
    finally:
        leave()


@tp.picture("sim_study_materials.png")
def study_materials():
    from fission180 import simulation_dialogs

    body, study = bracket()
    enter()
    try:
        simulation_dialogs.open_materials(study)
        panel = tp.wait_for_panel()
        tp.settle()
        return tp.dialog_picture(ws.trim_panel(tp.grab(panel)))
    finally:
        leave()


# -- SETUP: CONSTRAINTS, LOADS -----------------------------------------------------------------
def glyph_picture(body, highlight_faces, setup=None):
    ws.look(CAMERA)
    if setup:
        setup()
    shot = tp.render(highlight={body: highlight_faces} if highlight_faces else None)
    return tp.finish(shot)


@tp.picture("sim_constraints.png")
def constraints():
    body, study = bracket(load=False)
    enter()
    try:
        ws.look((1, 1, -0.75))
        return tp.finish(tp.render(highlight={body: wall_face(body)}))
    finally:
        leave()


@tp.picture("sim_loads.png")
def loads():
    body, study = bracket(constraint=False)
    enter()
    try:
        return glyph_picture(body, end_face(body))
    finally:
        leave()


@tp.picture("sim_gravity.png")
def gravity():
    body, study = bracket()
    enter()
    try:
        tp.run_command("Fission180_SimGravity")
        tp.settle()
        return glyph_picture(body, [])
    finally:
        leave()


# -- SETUP: CONTACTS ---------------------------------------------------------------------------
def two_bodies(study, body):
    """A pad under the plate's end: a second body touching the bracket (bonded)."""
    import FreeCAD as App
    import Part

    body_of_shape(Part.makeBox(16, 20, 4, App.Vector(64, 0, -4)), "Pad")


@tp.picture("sim_auto_contacts.png")
def auto_contacts():
    from fission180 import simulation_dialogs
    from fission180.compat import QtWidgets

    body, study = bracket(extra=two_bodies)
    enter()
    try:
        simulation_dialogs.open_contacts(study)
        panel = tp.wait_for_panel()
        for button in panel.findChildren(QtWidgets.QPushButton):
            if button.text() == "Generate":
                button.click()
        tp.settle()
        return tp.dialog_picture(ws.trim_panel(tp.grab(panel)))
    finally:
        leave()


@tp.picture("sim_contact_manager.png")
def contact_manager():
    from fission180 import simulation_dialogs

    body, study = bracket(extra=two_bodies)
    enter()
    try:
        simulation_dialogs.open_contact_manager(study)
        return tp.dialog_picture(grab_window("_TableDialog", "the Contact Manager"))
    finally:
        leave()


# -- SETUP: DISPLAY ----------------------------------------------------------------------------
@tp.picture("sim_dof_view.png")
def dof_view():
    body, study = bracket(constraint=False)
    enter()
    try:
        tp.run_command("Fission180_SimDOFView")
        tp.settle()
        return glyph_picture(body, [])
    finally:
        leave()


def generated_mesh(study):
    from fission180 import simulation_solve_dialog

    simulation_solve_dialog.generate_mesh(study)
    tp.wait_for(lambda: not simulation_solve_dialog.solving(), "the mesh", 300)
    tp.settle()
    for widget in _sim_windows():
        widget.close()
    tp.settle()


@tp.picture("sim_show_mesh.png")
def show_mesh():
    body, study = bracket()
    enter()
    try:
        generated_mesh(study)
        return glyph_picture(body, [])
    finally:
        leave()


@tp.picture("sim_generate_mesh.png")
def generate_mesh():
    body, study = bracket()
    enter()
    try:
        ws.look(CAMERA)
        before = tp.render()
        generated_mesh(study)
        after = tp.render()
        return tp.before_after(before, after)
    finally:
        leave()


# -- SETUP: MANAGE -----------------------------------------------------------------------------
@tp.picture("sim_settings.png")
def settings():
    from fission180 import simulation_dialogs

    body, study = bracket()
    enter()
    try:
        simulation_dialogs.open_settings(study)
        panel = tp.wait_for_panel()
        tp.settle()
        return tp.dialog_picture(ws.trim_panel(tp.grab(panel)))
    finally:
        leave()


def local_mesh(study, body):
    from fission180 import simulation as sim

    sim.add_item(study, "mesh", "local", [(body, n) for n in hole_face(body)], {"size": 1.0})


@tp.picture("sim_local_mesh.png")
def local_mesh_control():
    body, study = bracket(extra=local_mesh)
    enter()
    try:
        return glyph_picture(body, hole_face(body))
    finally:
        leave()


@tp.picture("sim_attributes.png")
def attributes():
    from fission180 import simulation_dialogs

    body, study = bracket()
    enter()
    try:
        simulation_dialogs.open_attributes(study)
        return tp.dialog_picture(grab_window("_TableDialog", "Load Case Attributes"))
    finally:
        leave()


# -- SETUP: SOLVE ------------------------------------------------------------------------------
@tp.picture("sim_precheck.png")
def precheck():
    """A study with nothing holding the bracket: Pre-check's red list and its Repair."""
    from fission180 import simulation_dialogs

    body, study = bracket(constraint=False)
    enter()
    try:
        simulation_dialogs.open_precheck(study)
        return tp.dialog_picture(grab_window("PrecheckDialog", "the Pre-check list"))
    finally:
        leave()


@tp.picture("sim_solve.png")
def solve_dialog():
    from fission180 import simulation_solve_dialog

    body, study = bracket()
    enter()
    try:
        simulation_solve_dialog.open_solve()
        return tp.dialog_picture(grab_window("SolveDialog", "the Solve window"))
    finally:
        leave()


@tp.picture("sim_job_status.png")
def job_status():
    from fission180 import simulation_solve_dialog

    body, study = bracket()
    enter()
    try:
        solve(study)
        simulation_solve_dialog.show_status()
        return tp.dialog_picture(grab_window("StatusDialog", "the Job Status window"))
    finally:
        leave()


# -- RESULTS: DEFORMATION and DISPLAY ------------------------------------------------------------
def result_picture(set_up=None, deformation=None):
    body, study, session = solved()
    try:
        if deformation:
            session.set_deformation(deformation)
        if set_up:
            set_up(session)
        tp.settle()
        return legend_picture(session, tp.render())
    finally:
        leave()


@tp.picture("simr_undeformed.png")
def undeformed():
    return result_picture(deformation="undeformed")


@tp.picture("simr_actual.png")
def actual():
    return result_picture(deformation="actual")


@tp.picture("simr_adjusted_half.png")
def adjusted_half():
    return result_picture(deformation="adjusted_half")


@tp.picture("simr_adjusted.png")
def adjusted():
    return result_picture(deformation="adjusted")


@tp.picture("simr_adjusted_2.png")
def adjusted_2():
    return result_picture(deformation="adjusted_2")


@tp.picture("simr_adjusted_5.png")
def adjusted_5():
    return result_picture(deformation="adjusted_5")


@tp.picture("simr_show_mesh.png")
def results_mesh():
    return result_picture(lambda s: s.set_option("mesh", True))


@tp.picture("simr_ghost.png")
def ghost():
    return result_picture(lambda s: s.set_option("ghost", True), deformation="adjusted_2")


@tp.picture("simr_loads.png")
def results_loads():
    return result_picture(lambda s: s.set_option("loads", True))


# -- RESULTS: tags over the view ---------------------------------------------------------------
@tp.picture("simr_minmax.png")
def minmax():
    body, study, session = solved()
    try:
        session.set_option("minmax", True)
        tp.settle()
        return view_picture(body)
    finally:
        leave()


def node_screen(session, x, y, z):
    """Pixel (in the 3D view widget) of the result's surface node nearest (x, y, z)."""
    import FreeCAD as App

    pts = session.data.points
    best = None
    for n in session.display.nodes.tolist():
        d = sum((pts[n][k] - c) ** 2 for k, c in enumerate((x, y, z)))
        if best is None or d < best[0]:
            best = (d, n)
    place = App.Vector(*session.display.node_place(best[1]))
    return tp.view().getPointOnViewport(place)  # Coin's pixel, as add_probe_at takes it


@tp.picture("simr_probes.png")
def probes():
    body, study, session = solved()
    try:
        tp.run_command("Fission180_SimResultsProbes")
        tp.wait_for_panel()
        for point in ((3, 10, 38), (40, 10, 6), (75, 10, 6)):
            x, y = node_screen(session, *point)
            session.add_probe_at(x, y)
        tp.settle()
        return view_picture(body)
    finally:
        leave()


@tp.picture("simr_animate.png")
def animate():
    """The result with the animation bar the command shows under it (a moment of the play)."""
    from PIL import Image

    from fission180 import simulation_results_view as srv
    from fission180.compat import QtWidgets

    body, study, session = solved()
    try:
        tp.run_command("Fission180_SimResultsAnimate")
        tp.wait(900)  # on purpose: a moment of the animation playing
        shot = tp.render()
        bars = [
            b
            for b in QtWidgets.QApplication.instance().allWidgets()
            if isinstance(b, srv.AnimationBar) and b.isVisible()
        ]
        bar = tp.grab(bars[0]) if bars else None
        session.stop_animation()
        out = Image.new("RGB", tp.SIZE, tp.BACKGROUND)
        if bar is None:
            return tp.finish(shot)
        scale = min(1.0, (tp.SIZE[0] - 8) / float(bar.width))
        small = bar.resize((int(bar.width * scale), int(bar.height * scale)), Image.LANCZOS)
        model_h = tp.SIZE[1] - small.height - 6
        out.paste(tp._frame(shot, shot.box, (tp.SIZE[0], model_h)), (0, 0))
        out.paste(small, (4, tp.SIZE[1] - small.height - 3))
        return out
    finally:
        leave()


# -- RESULTS: windows --------------------------------------------------------------------------
def results_window(command, cls_name, what, set_up=None):
    body, study, session = solved()
    try:
        if set_up:
            set_up(session)
        tp.run_command(command)
        return tp.dialog_picture(grab_window(cls_name, what))
    finally:
        leave()


@tp.picture("simr_details.png")
def details():
    return results_window("Fission180_SimResultsDetails", "DetailsDialog", "Results Details")


@tp.picture("simr_range.png")
def legend_range():
    return results_window(
        "Fission180_SimResultsRange",
        "RangeDialog",
        "Legend Min/Max",
        lambda s: s.set_result("von_mises"),
    )


@tp.picture("simr_report.png")
def report():
    return results_window("Fission180_SimResultsReport", "ReportDialog", "the Report window")


@tp.picture("simr_reactions.png")
def reactions():
    return results_window("Fission180_SimResultsReactions", "ReactionsDialog", "Reaction Force")


@tp.picture("simr_solver_data.png")
def solver_data():
    return results_window("Fission180_SimResultsSolverData", "SolverDataDialog", "Solver Data")


@tp.picture("simr_compare.png")
def compare():
    """Two studies of the bracket (200 N and 400 N) solved: the Compare window ticks them."""
    from fission180 import simulation as sim

    body, study = bracket()
    second = sim.clone_study(study)
    enter()
    try:
        solve(study)
        solve(second)
        results(study)
        tp.run_command("Fission180_SimResultsCompare")
        return tp.dialog_picture(grab_window("CompareDialog", "the Compare window"))
    finally:
        leave()


@tp.picture("simr_convergence.png")
def convergence():
    from fission180 import simulation as sim

    def adaptive(study, body):
        sim.set_settings(study, {"adaptive": {"level": "low", "result": "von_mises"}})

    body, study = bracket(extra=adaptive)
    enter()
    try:
        solve(study, wait_s=600)
        results(study)
        tp.run_command("Fission180_SimResultsConvergence")
        return tp.dialog_picture(grab_window("ConvergenceDialog", "the Convergence Plot"))
    finally:
        leave()


# -- RESULTS: INSPECT panels ---------------------------------------------------------------------
def panel_picture(command, set_up=None):
    body, study, session = solved()
    try:
        tp.run_command(command)
        panel = tp.wait_for_panel()
        if set_up:
            set_up(session, panel)
        tp.settle()
        shot = tp.render()
        return tp.with_dialog(shot, ws.trim_panel(tp.grab(panel)), width=165)
    finally:
        leave()


@tp.picture("simr_slice.png")
def slice_plane():
    return panel_picture("Fission180_SimResultsSlice")


@tp.picture("simr_iso.png")
def iso_surface():
    return panel_picture("Fission180_SimResultsIso")


@tp.picture("simr_point_probes.png")
def point_probes():
    import FreeCAD as App

    from fission180 import simulation_results_panels

    body, study, session = solved()
    try:
        panel = simulation_results_panels.point_probes(session)
        widget = tp.wait_for_panel()
        for at in ((3, 10, 30), (30, 10, 3), (70, 10, 3)):
            session.add_point(App.Vector(*at))
        panel.refresh()
        tp.settle()
        shot = tp.render()
        return tp.with_dialog(shot, ws.trim_panel(tp.grab(widget)), width=165)
    finally:
        leave()


# -- FINISH RESULTS ----------------------------------------------------------------------------
@tp.picture("simr_finish.png")
def finish_results():
    body, study, session = solved()
    try:
        before = tp.render()
        tp.run_command("Fission180_SimResultsFinish")
        tp.settle()
        after = tp.render()
        return tp.before_after(before, after, labels=("RESULTS", "SETUP"))
    finally:
        leave()
