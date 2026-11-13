# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI actions for drawings, with Fission 180's drawing code: the code behind File > New
Drawing and every command of the DRAWING tab (drawing.py on FreeCAD's TechDraw,
drawing_annot.py, drawing_tools.py, drawing_sheets.py, drawing_breakout.py,
drawing_exploded.py, drawing_export.py, flatpattern_drawing.py). A dialog's clicks become
arguments: a view's elements are found the way the commands infer them from clicks (a pick
{kind, near} in the view's own mm), places on the sheet are [x, y] mm, and where the AI
gives no place a free one is worked out (fission180/ai/drawing_core_ai.py). Each changing call
is one undo step; get_drawing reads everything back (and draws the sheet,
fission180/ai/drawing_picture.py).

With the Fission 180 window, TechDraw draws a view's lines in a thread: every call waits
until it is done (_idle), before it reads a view and before it answers, so the next call
finds the view's elements and the answer's numbers are the drawing's."""

import base64
import math
import os
import tempfile
import time

import FreeCAD as App

from ... import log, warn
from .. import bridge_core
from .. import drawing_core_ai as aicore
from ..executor import UserError, json_result
from . import action

KIND_NAMES = {"projected": "ProjectedView", "base": "BaseView"}
SYMBOL_REACH = 12.0  # mm on the sheet from its edge a symbol placed by default stands
IDLE_TIMEOUT_S = 180.0  # TechDraw drawing a big assembly's views


# -- finding things -------------------------------------------------------------------------------
def _pages(doc):
    return [o for o in doc.Objects if o.TypeId == "TechDraw::DrawPage"]


def _page(ctx, ident=None):
    """The drawing (or sheet) an id names, or that a view / item of it is on; the newest
    drawing by default."""
    from ... import drawing

    doc = ctx.need_doc()
    if ident:
        obj = ctx.resolve(ident, "drawing")
        page = obj if drawing.is_page(obj) else _sheet_of_item(obj)
        if page is None:
            raise UserError("%r is not a drawing or a view of one." % ident)
        return page
    found = drawing.drawings(doc) or _pages(doc)
    if not found:
        raise UserError("The design has no drawing yet: call create_drawing first.")
    return found[-1]


def _sheet_of_item(obj):
    """The sheet a view, dimension, balloon, note, symbol or table stands on, or None (a
    body that a drawing shows is no item of it: drawing.page_of finds the drawing through
    its list of sources)."""
    from ... import drawing

    if drawing.is_page(obj):
        return obj
    page = drawing.page_of(obj)
    if page is None:
        return None
    if drawing.is_view(obj) or obj.Name in [v.Name for v in getattr(page, "Views", [])]:
        return page
    return None


def _view(ctx, ident):
    from ... import drawing

    obj = ctx.resolve(ident, "drawing view")
    if not drawing.is_view(obj):
        raise UserError(
            "%r is not a drawing view (get_drawing lists the views: BaseView, "
            "ProjectedView...)." % ident
        )
    return obj


def _sheet(page):
    from ... import drawing, drawing_core

    try:
        return drawing_core.sheet_size(drawing.standard_of(page), drawing.sheet_of(page))
    except Exception:
        return (420.0, 297.0)


def _area(page):
    from ... import drawing, drawing_core

    return drawing_core.drawing_area(drawing.standard_of(page), drawing.sheet_of(page))


def _offset(page, kind):
    """Where a projected view goes, from its parent (a fraction of the sheet)."""
    w, h = _sheet(page)
    dx = {"Right": 0.32, "Left": -0.28, "Top": 0.0, "Bottom": 0.0}.get(kind)
    dy = {"Top": 0.32, "Bottom": -0.32, "Right": 0.0, "Left": 0.0}.get(kind)
    if dx is None:  # an isometric corner view
        dx = 0.32 if "Right" in kind else -0.28
        dy = 0.3 if "Top" in kind else -0.3
    if page.ProjectionType == "First angle":  # ISO: the top view goes below the front
        dx, dy = -dx, -dy
    return dx * w, dy * h


def _scale_text(scale):
    return aicore.scale_text(scale)


# -- TechDraw drawing in its thread (the window) ---------------------------------------------------
def _hlr_busy():
    try:
        from PySide import QtCore

        return QtCore.QThreadPool.globalInstance().activeThreadCount() > 0
    except Exception:
        return False


def _idle(doc=None, timeout=IDLE_TIMEOUT_S):
    """With the window, wait until TechDraw has drawn every view (its lines are worked out
    in Qt's thread pool and handed over through the event loop): a view read before is
    empty, and one recomputed meanwhile keeps its old lines. Without the window TechDraw
    draws at once: nothing to wait for."""
    if not App.GuiUp:
        return True
    try:
        from PySide import QtCore, QtWidgets
    except Exception:
        return True
    start = time.time()
    quiet = 0
    while time.time() - start < timeout:
        busy = _hlr_busy() or (doc is not None and getattr(doc, "Recomputing", False))
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 20)
        quiet = 0 if busy else quiet + 1
        if quiet >= 2:  # (the thread's result reaches its view through one more event)
            return True
        time.sleep(0.005)
    warn("AI drawing: TechDraw was still drawing after %d s" % timeout)
    return False


def _settle(doc):
    """Inside a change: TechDraw draws the views, then what follows the views (the title
    block's scale, parts lists, centre marks, annotations on their edges) is brought up to
    date as the dialogs' OK does (drawing_ui.refresh_drawings), and projected views stay on
    their parents' lines."""
    from ... import drawing

    doc.recompute()
    _idle(doc)
    for page in drawing.all_pages(doc):
        try:
            drawing.refresh(page)
            drawing.keep_aligned(page)
        except Exception as exc:
            warn("AI drawing refresh %s: %s" % (page.Label, exc))
    doc.recompute()
    _idle(doc)


def _looks(doc):
    """With the window: what a view's style means for its look (drawing_ui.apply_view_looks)."""
    if not App.GuiUp:
        return
    try:
        from ... import drawing, drawing_ui

        for page in drawing.all_pages(doc):
            drawing_ui.apply_view_looks(page)
    except Exception as exc:
        log("AI drawing looks: %s" % exc)


def _change(ctx, fn, doc=None):
    """fn() as one undo step (ctx.change), TechDraw idle before and after, everything that
    follows the views refreshed inside the step. DrawingError -> a plain refusal."""
    from ... import drawing, drawing_sheets

    doc = doc or ctx.need_doc()
    _idle(doc)

    def work():
        try:
            value = fn()
        except (drawing.DrawingError, drawing_sheets.SheetError) as exc:
            raise UserError(str(exc))
        _settle(doc)
        return value

    value = ctx.change(work)
    _idle(doc)
    _looks(doc)
    return value


def _recompute(page):
    try:
        page.Document.recompute()
    except Exception:
        pass


def _view_info(view):
    """A view as the answers and get_drawing describe it."""
    from ... import drawing

    x, y = drawing.view_position(view)
    hw, hh = drawing.view_extent(view)
    return "%s %r (id %r) at [%g, %g], %g x %g mm on the sheet, scale %s" % (
        (drawing.kind(view) or view.TypeId.split("::")[-1]),
        view.Label,
        view.Name,
        aicore.r(x, 2),
        aicore.r(y, 2),
        aicore.r(2 * hw, 1),
        aicore.r(2 * hh, 1),
        _scale_text(drawing.scale_of(view)),
    )


def _blocked(page, skip=()):
    """Rectangles on the sheet something already covers (views, tables, the title block)."""
    from ... import drawing, drawing_core, drawing_tools

    rects = []
    for view in drawing.all_views(page):
        if view.Name in skip or not getattr(view, "Visibility", True):
            continue
        try:
            rects.append(drawing.view_rect(view))
        except Exception:
            pass
    for obj in drawing.annotations(page):
        try:
            if drawing_tools._is_table(obj):
                rects.append(drawing_tools.table_rect(obj))
        except Exception:
            pass
    if getattr(page, "Fission180TitleBlock", False):
        rects.append(
            drawing_core.title_block_rect(drawing.standard_of(page), drawing.sheet_of(page))
        )
    return rects


def _place_free(view, page, prefer=None):
    """A view placed by the AI without a place goes where it covers nothing (Fusion's
    person drops it on empty paper)."""
    from ... import drawing

    rect = drawing.view_rect(view)
    blocked = _blocked(page, skip=(view.Name,))
    if not any(aicore.overlaps(rect, b, 2.0) for b in blocked):
        return False
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    spot = aicore.free_spot(_area(page), blocked, (w, h), prefer)
    if spot is None:
        return False
    view.X, view.Y = spot
    return True


def _overlap_note(view):
    """What a view lies on (other views, tables, the title block) or reaches past (the
    sheet's frame), said so the AI moves it: a person sees it."""
    from ... import drawing

    page = drawing.page_of(view)
    if page is None or not getattr(view, "Visibility", True):
        return ""
    rect = drawing.view_rect(view)
    hits = []
    for other in drawing.all_views(page):
        if drawing.same(other, view) or not getattr(other, "Visibility", True):
            continue
        if drawing.same(drawing._get(view, "Fission180BrokenOf", None), other):
            continue
        if aicore.overlaps(rect, drawing.view_rect(other)):
            hits.append("%s (%s)" % (other.Name, other.Label))
    notes = []
    if hits:
        notes.append("it overlaps %s" % ", ".join(hits))
    w, h = _sheet(page)
    if rect[0] < 0 or rect[1] < 0 or rect[2] > w or rect[3] > h:
        notes.append("it reaches off the sheet")
    if not notes:
        return ""
    return (
        " Note: %s: move it (modify_drawing kind move), give it a smaller scale "
        "(edit_drawing_view) or a bigger sheet." % "; ".join(notes)
    )


def _bodies(ctx, idents):
    return [ctx.body_of(i) for i in idents]


def _flat_pattern(ctx, ident):
    """A flat pattern from its id or a sheet metal body's (its flat pattern)."""
    from ... import bodies, drawing, flatpattern

    obj = ctx.resolve(ident, "flat pattern or sheet metal body")
    if flatpattern.is_flat_pattern(obj):
        return obj
    body = obj if bodies.is_body(obj) else bodies.body_of(obj)
    for fp in flatpattern.all_of(obj.Document):
        if body is not None and drawing.same(fp.Body, body):
            if fp.Shape.Solids:
                return fp
    raise UserError(
        "%r has no flat pattern: make one first (flat_pattern, SHEET METAL > CREATE > Create "
        "Flat Pattern)." % ident
    )


def _page_sources(page):
    from ... import drawing

    found = [s for s in (getattr(page, "Fission180Sources", []) or []) if drawing.alive(s)]
    return found or drawing.design_bodies(page.Document, visible_only=True)


# -- CREATE: the drawing --------------------------------------------------------------------------
@action("create_drawing")
def create_drawing(ctx, args):
    from ... import drawing, drawing_exploded

    doc = ctx.need_doc()
    contents = ""
    if args.get("flat_pattern"):
        sources = [_flat_pattern(ctx, args["flat_pattern"])]
    elif args.get("bodies"):
        sources = _bodies(ctx, args["bodies"])
    elif args.get("contents") == "full_assembly":
        contents = "Full Assembly"
        try:
            sources = drawing.sources_for(doc, contents)
        except drawing.DrawingError as exc:
            raise UserError(str(exc))
    else:
        sources = drawing.design_bodies(doc, visible_only=True) or drawing.design_bodies(doc)
        if args.get("contents") == "visible_only":
            contents = "Visible Only"
    board = args.get("storyboard")
    if board:
        why = drawing_exploded.why_none(doc)
        if why:
            raise UserError(why)
        if board not in drawing_exploded.storyboards(doc):
            raise UserError(
                "The design has no storyboard %r: it has %s (anim_storyboards lists them)."
                % (board, ", ".join(drawing_exploded.storyboards(doc)))
            )

    def work():
        page = drawing.create_drawing(
            doc,
            sources,
            standard=args.get("standard", "ISO"),
            units=args.get("units", "mm"),
            sheet=args.get("sheet"),
            title_block=args.get("title_block", True),
            label=args.get("label"),
            contents=contents,
        )
        if board:  # (From Animation: every view of the drawing shows the storyboard's end)
            drawing._add(page, "App::PropertyString", "Fission180Storyboard", board)
        if args.get("automatic"):
            views = drawing.add_automatic_views(page, sources, board)
            return page, views
        area = _area(page)
        x, y = args.get("at", ((area[0] + area[2]) / 2.0, (area[1] + area[3]) / 2.0))
        base = drawing.add_base_view(
            page,
            sources,
            x,
            y,
            args.get("base_view", "Front"),
            args.get("style"),
            args.get("scale"),
        )
        if board:
            drawing_exploded.add_exploded(base, board)
            if "scale" not in args:
                drawing.set_scale(
                    base,
                    drawing.automatic_scale(page, list(base.Source), drawing.orientation_of(base)),
                )
        doc.recompute()
        _idle(doc)
        views = [base]
        for kind in args.get("projected") or []:
            views.append(drawing.add_projected(base, kind, x, y))  # (laid out below)
        if len(views) > 1:
            doc.recompute()
            _idle(doc)
        fits = _lay_out(page, base, views[1:], "scale" not in args, args.get("at"))
        drawing._add(page, "App::PropertyBool", "Fission180AutoFits", bool(fits))
        return page, views

    page, views = _change(ctx, work, doc)
    note = ""
    if getattr(page, "Fission180AutoFits", True) is False:
        note = (
            " The design is too big for this sheet even at 1:200: the views overlap; choose a "
            "bigger sheet or a smaller scale (edit_drawing_view)."
        )
    return bridge_core.result(
        "Done: drawing %r (id %r) on a %s %s sheet, scale %s; views %s.%s"
        % (
            page.Label,
            page.Name,
            drawing.standard_of(page),
            drawing.sheet_of(page),
            _scale_text(drawing.scale_of(views[0])),
            ", ".join("%s (%s)" % (v.Name, v.Label) for v in views),
            note,
        )
    )


def _size1(view):
    """(w, h) of what a view draws, at 1:1 (mm)."""
    from ... import drawing

    s = drawing.scale_of(view) or 1.0
    hw, hh = drawing.view_extent(view)
    return 2.0 * hw / s, 2.0 * hh / s


def _set_place(view, x, y):
    """A view's place; a projected view also keeps it as its offset from its parent (so
    drawing.keep_aligned does not put it back)."""
    from ... import drawing

    view.X, view.Y = x, y
    parent = drawing.parent_of(view)
    if parent is not None and "Fission180Offset" in view.PropertiesList:  # (and sections)
        px, py = drawing.view_position(parent)
        view.Fission180Offset = [x - px, y - py]


def _lay_out(page, base, children, rescale, at=None):
    """A base view and the views projected from it side by side by their real sizes, the
    block centred on the sheet's free area (or the base view kept at `at`), at the largest
    standard scale up to the base view's own at which it fits (rescale), as a person lays
    them out. True when it fits."""
    from ... import drawing, drawing_core

    if not children and at is not None:
        return True
    s = drawing.scale_of(base) or 1.0
    kids = [(drawing._get(v, "Fission180Kind", "") or "Right", _size1(v)) for v in children]
    scales = [s]
    if rescale:
        scales = [a / float(b) for a, b in drawing_core.SCALES if a / float(b) <= s + 1e-9] or [s]
    plan = aicore.layout_views(_size1(base), kids, page.ProjectionType, _area(page), scales, at=at)
    if abs(plan["scale"] - s) > 1e-12:
        drawing.set_scale(base, plan["scale"])
    base.X, base.Y = plan["base"]
    for view, (cx, cy) in zip(children, plan["children"]):
        _set_place(view, cx, cy)
    return plan["fits"]


def _beside(parent, view, kind):
    """A projected view placed beside its parent by both views' sizes."""
    from ... import drawing

    page = drawing.page_of(parent)
    dx, dy = aicore.projected_offset(
        _size1(parent), _size1(view), kind, page.ProjectionType, drawing.scale_of(parent) or 1.0
    )
    px, py = drawing.view_position(parent)
    _slide_free(view, (px, py), (dx, dy))


def _slide_free(view, origin, offset, step=5.0, tries=60):
    """Put a view at origin + offset, or further out along the offset's direction when
    something already covers that place (a person keeps a projected or section view on its
    line and moves it past the views in the way); the first place when there is no free one
    on the sheet."""
    from ... import drawing

    page = drawing.page_of(view)
    blocked = _blocked(page, skip=(view.Name,))
    area = _area(page)
    hw, hh = drawing.view_extent(view)
    length = math.hypot(*offset) or 1.0
    ux, uy = offset[0] / length, offset[1] / length
    for i in range(tries):
        x = origin[0] + offset[0] + ux * step * i
        y = origin[1] + offset[1] + uy * step * i
        rect = (x - hw, y - hh, x + hw, y + hh)
        inside = rect[0] >= area[0] - 1e-6 and rect[2] <= area[2] + 1e-6
        inside = inside and rect[1] >= area[1] - 1e-6 and rect[3] <= area[3] + 1e-6
        if not inside:
            break
        if not any(aicore.overlaps(rect, b, 2.0) for b in blocked):
            _set_place(view, x, y)
            return True
    _set_place(view, origin[0] + offset[0], origin[1] + offset[1])
    return False


def _cut_normal(line, side_sign):
    (x1, y1), (x2, y2) = line[0], line[1]
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    return -(y2 - y1) / length * side_sign, (x2 - x1) / length * side_sign


def _along_cut(parent, section, normal):
    """A section view placed beside its parent along its cut line's normal (where it
    slides: drawing.keep_aligned), by both views' sizes."""
    from ... import drawing

    phw, phh = drawing.view_extent(parent)
    shw, shh = drawing.view_extent(section)
    nx, ny = normal
    reach = abs(nx) * (phw + shw) + abs(ny) * (phh + shh) + aicore.VIEW_GAP
    _slide_free(section, drawing.view_position(parent), (nx * reach, ny * reach))


# -- CREATE: views --------------------------------------------------------------------------------
def _section_side(args, line, side):
    if "side" not in args:
        return side
    (x1, y1), (x2, y2) = line[0], line[1]
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    s = 1.0 if int(args["side"]) >= 0 else -1.0
    return (mx + s * nx * 10.0, my + s * ny * 10.0)


@action("add_drawing_view")
def add_drawing_view(ctx, args):
    from ... import drawing, drawing_breakout, drawing_exploded

    page = _page(ctx, args.get("drawing") or args.get("parent"))
    kind = args["kind"]
    w, h = _sheet(page)
    doc = page.Document
    parent = _view(ctx, args["parent"]) if args.get("parent") else None
    if kind == "exploded":
        why = drawing_exploded.why_none(doc)
        if why:
            raise UserError(why)
        board = args.get("storyboard") or drawing_exploded.front_storyboard(doc)
        if board not in drawing_exploded.storyboards(doc):
            raise UserError(
                "The design has no storyboard %r: it has %s."
                % (board, ", ".join(drawing_exploded.storyboards(doc)))
            )
    if kind in ("base", "exploded"):
        if args.get("flat_pattern"):
            sources = [_flat_pattern(ctx, args["flat_pattern"])]
        elif args.get("bodies"):
            sources = _bodies(ctx, args["bodies"])
        else:
            sources = _page_sources(page)
        if not sources:
            raise UserError("The design has no solid bodies to draw.")
    placed = "at" in args

    def work():
        if kind in ("base", "exploded"):
            x, y = args.get("at", (0.7 * w, 0.3 * h))
            view = drawing.add_base_view(
                page,
                sources,
                x,
                y,
                args.get("orientation", "Front"),
                args.get("style"),
                args.get("scale"),
            )
            if kind == "exploded":
                drawing_exploded.add_exploded(view, board)
                if "scale" not in args:
                    drawing.set_scale(
                        view,
                        drawing.automatic_scale(
                            page, list(view.Source), drawing.orientation_of(view)
                        ),
                    )
        elif kind == "projected":
            px, py = drawing.view_position(parent)
            dx, dy = _offset(page, args["direction"])
            x, y = args.get("at", (px + dx, py + dy))
            view = drawing.add_projected(parent, args["direction"], x, y)
        elif kind == "section":
            px, py = drawing.view_position(parent)
            line = [tuple(p) for p in args["line"]]
            sign = 1.0 if int(args.get("side", 1)) >= 0 else -1.0
            normal = _cut_normal(line, sign)
            hw, hh = drawing.view_extent(parent)
            reach = 2.0 * (abs(normal[0]) * hw + abs(normal[1]) * hh) + aicore.VIEW_GAP
            pos = args.get("at", (px + normal[0] * reach, py + normal[1] * reach))
            side = _section_side(args, line, drawing.page_to_local(parent, pos))
            depth = None
            if args.get("depth_mode", "Full") != "Full":
                depth = (args["depth_mode"], float(args.get("depth", 0.0)))
            view = drawing.add_section(
                parent,
                line[0],
                line[1],
                side,
                pos,
                args.get("label"),
                args.get("scale"),
                points=line if len(line) > 2 else None,
                depth=depth,
            )
        elif kind == "detail":
            px, py = drawing.view_position(parent)
            pos = args.get("at", (px + 0.3 * w, py - 0.3 * h))
            view = drawing.add_detail(
                parent,
                tuple(args["center"]),
                args["radius"],
                pos,
                args.get("label"),
                args.get("scale"),
            )
        elif kind == "break":
            if parent.TypeId in (drawing.DETAIL, drawing.BROKEN):
                raise UserError("Break a base, projected or section view (not %s)." % parent.Label)
            view = drawing.add_break(
                parent, tuple(args["start"]), tuple(args["end"]), args.get("gap", 10.0)
            )
        else:  # breakout
            depth = None
            if not args.get("through_all"):
                depth = args.get("depth") or drawing_breakout.default_depth(parent)
            drawing_breakout.add_breakout(parent, [tuple(p) for p in args["boundary"]], depth)
            view = parent
        if args.get("style") and kind not in ("base", "exploded"):
            drawing.set_view_style(view, args["style"])
        doc.recompute()
        _idle(doc)
        if not placed:
            moved = False
            if kind == "projected":
                _beside(parent, view, args["direction"])
                moved = True
            elif kind == "section":
                _along_cut(parent, view, normal)
                moved = True
            if kind in ("base", "exploded", "detail"):
                moved = _place_free(view, page)
            if moved:
                doc.recompute()
                _idle(doc)
        return view

    view = _change(ctx, work, doc)
    extra = ""
    if kind == "breakout":
        data = drawing_breakout.breakout_of(view) or {}
        depth = data.get("depth")
        extra = " Breakout %s." % ("through all" if depth is None else "%g mm deep" % depth)
    elif kind == "break":
        extra = " It stands in for %s (hidden); deleting it brings that back." % parent.Label
    elif kind == "exploded":
        extra = " It shows storyboard %r at its end." % drawing_exploded.storyboard_of(view)
    return bridge_core.result(
        "Done: %s view: %s on %s.%s%s"
        % (kind, _view_info(view), page.Label, extra, _overlap_note(view))
    )


# -- MODIFY > Edit View ----------------------------------------------------------------------------
@action("edit_drawing_view")
def edit_drawing_view(ctx, args):
    from ... import drawing, drawing_breakout, drawing_exploded

    view = _view(ctx, args["view"])
    doc = view.Document
    if "orientation" in args and drawing.kind(view) != "BaseView":
        raise UserError(
            "Only a base view takes an orientation (its projected views turn with it): "
            "%s is a %s." % (view.Label, drawing.kind(view) or "view")
        )
    if "storyboard" in args and drawing.kind(view) != "BaseView":
        raise UserError("Only a base view shows a storyboard (its projected views follow it).")
    if "gap" in args and view.TypeId != drawing.BROKEN:
        raise UserError("%s is not a broken view (gap is a break's)." % view.Label)
    if ("depth_mode" in args or "hatch" in args) and not drawing.is_section(view):
        raise UserError("%s is not a section view." % view.Label)
    breakout_change = "remove_breakout" in args or (
        not drawing.is_section(view) and ("depth" in args or "through_all" in args)
    )
    if breakout_change and not drawing_breakout.has_breakout(view):
        raise UserError("%s has no breakout (add_drawing_view kind breakout)." % view.Label)

    def work():
        if "storyboard" in args:
            name = args["storyboard"]
            if name != drawing_exploded.MODEL and name not in drawing_exploded.storyboards(doc):
                raise UserError(
                    "The design has no storyboard %r (Model: the design as it is)." % name
                )
            drawing_exploded.set_representation(view, name)
        if "orientation" in args:
            drawing.set_base_orientation(view, args["orientation"])
        if "style" in args or "tangent_edges" in args:
            drawing.set_view_style(
                view, args.get("style", drawing.style_of(view)), args.get("tangent_edges")
            )
        if "scale" in args:
            drawing.set_scale(view, float(args["scale"]))
        if "label" in args or "show_label" in args:
            drawing.set_view_label(view, text=args.get("label"), shown=args.get("show_label"))
        if "center_marks" in args:
            settings = dict(drawing.auto_mark_settings(view))
            settings.update({k: bool(v) for k, v in args["center_marks"].items()})
            drawing.set_auto_marks(view, settings)
        if "depth_mode" in args:
            drawing.set_section_depth(view, args["depth_mode"], float(args.get("depth", 0.0)))
        elif "depth" in args and drawing.is_section(view):
            drawing.set_section_depth(view, "Distance", float(args["depth"]))
        if "hatch" in args:
            if args["hatch"]:
                drawing._hatch(view)
            else:
                view.CutSurfaceDisplay = "Hide"
        if "gap" in args:
            view.Gap = float(args["gap"])
        if args.get("remove_breakout"):
            drawing_breakout.remove_breakout(view)
        elif breakout_change:
            drawing_breakout.set_depth(view, None if args.get("through_all") else args["depth"])
        return view

    _change(ctx, work, doc)
    return bridge_core.result("Done: %s." % _view_info(view))


# -- MODIFY > Move, Rotate, Delete -----------------------------------------------------------------
def _items(ctx, idents):
    found = []
    for ident in idents:
        obj = ctx.resolve(ident, "drawing item")
        if obj.Name not in [o.Name for o in found]:
            found.append(obj)
    return found


def _movable(obj):
    from ... import drawing, drawing_annot, drawing_tools

    return (
        drawing.is_view(obj)
        or obj.TypeId in (drawing.BALLOON, drawing.ANNOTATION, drawing.DIMENSION)
        or drawing_tools._is_table(obj)
        or drawing_annot.is_annotation(obj)
    )


def _item_place(obj):
    """Where an item stands on the sheet (page mm)."""
    from ... import drawing

    if drawing.is_view(obj):
        return drawing.view_position(obj)
    if obj.TypeId == drawing.BALLOON:
        return drawing.balloon_page_points(obj)[1]
    if obj.TypeId == drawing.DIMENSION and obj.References2D:
        x, y = drawing.view_position(obj.References2D[0][0])
        return x + drawing._value(obj.X), y + drawing._value(obj.Y)
    return drawing._value(obj.X), drawing._value(obj.Y)


@action("modify_drawing")
def modify_drawing(ctx, args):
    from ... import drawing, drawing_sheets, drawing_tools

    doc = ctx.need_doc()
    items = _items(ctx, args["items"])
    kind = args["kind"]
    if kind == "delete":
        pages = [o for o in items if drawing.is_page(o)]
        rest = [o for o in items if not drawing.is_page(o)]
        for obj in rest:
            if _sheet_of_item(obj) is None:
                raise UserError(
                    "%r is not on a drawing: delete_step deletes design steps, "
                    "modify_drawing only what is on a drawing's sheet." % obj.Name
                )
        sheets = []
        for page in pages:
            for sheet in drawing_sheets.sheets(page):
                if sheet.Name not in [s.Name for s in sheets]:
                    sheets.append(sheet)
        if App.GuiUp:  # (a drawing's tab goes before its page: drawing_close)
            try:
                from ... import drawing_ui

                for sheet in sheets:
                    drawing_ui.close_tab(sheet)
            except Exception as exc:
                warn("AI drawing: closing a tab: %s" % exc)

        def work():
            removed = drawing.delete_objects(doc, [o for o in rest if drawing.alive(o)])
            for sheet in sheets:
                if drawing.alive(sheet):
                    removed += drawing.delete_drawing(sheet)
            return removed

        removed = _change(ctx, work, doc)
        return bridge_core.result(
            "Done: deleted %d objects (%s)." % (len(removed), ", ".join(removed[:30]))
        )
    for obj in items:
        if kind == "rotate" and not drawing_tools.can_rotate(obj):
            raise UserError(
                "Only views turn (%r is a %s)." % (obj.Name, obj.TypeId.split("::")[-1])
            )
        if kind == "move" and not _movable(obj):
            raise UserError(
                "%r cannot be moved: give views, tables, text, balloons, symbols or "
                "dimensions." % obj.Name
            )

    def work():
        if kind == "rotate":
            drawing_tools.rotate_to(doc, drawing_tools.rotations_of(items), float(args["angle"]))
            return
        if "to" in args:
            x, y = _item_place(items[0])
            dx, dy = args["to"][0] - x, args["to"][1] - y
        else:
            dx, dy = args["by"]
        plain = [o for o in items if o.TypeId != drawing.DIMENSION and not _symbol(o)]
        drawing_tools.move_to(doc, drawing_tools.places_of(plain), dx, dy)
        for obj in items:
            if obj.TypeId == drawing.DIMENSION:
                obj.X = drawing._value(obj.X) + dx
                obj.Y = drawing._value(obj.Y) + dy
            elif _symbol(obj):
                _move_symbol(obj, dx, dy)

    _change(ctx, work, doc)
    parts = []
    for obj in items:
        x, y = _item_place(obj)
        rot = ""
        if drawing.is_view(obj):
            rot = ", turned %g°" % aicore.r(drawing._value(getattr(obj, "Rotation", 0.0)), 2)
        parts.append("%s at [%g, %g]%s" % (obj.Name, aicore.r(x, 2), aicore.r(y, 2), rot))
    return bridge_core.result("Done: %s." % "; ".join(parts))


def _symbol(obj):
    from ... import drawing_annot

    return drawing_annot.is_annotation(obj)


def _move_symbol(obj, dx, dy):
    """A leader's text, a symbol, an ordinate's value moves; its arrow stays on its edge
    (the same as dragging it on the sheet)."""
    from ... import drawing_annot

    data = drawing_annot.annotation_data(obj)
    off = data.get("off") or [0.0, 0.0]
    data["off"] = [off[0] + dx, off[1] + dy]
    drawing_annot.update_annotation(obj, data)


# -- MODIFY > Title Block --------------------------------------------------------------------------
@action("edit_title_block")
def edit_title_block(ctx, args):
    from ... import drawing, drawing_sheets

    page = _page(ctx, args.get("drawing"))
    if drawing.title_template(page) is None or not getattr(page, "Fission180TitleBlock", True):
        raise UserError("This sheet has no title block (it was made with title_block false).")
    values = {k: str(v) for k, v in args["values"].items()}
    _change(ctx, lambda: drawing_sheets.set_title_everywhere(page, values), page.Document)
    now = drawing.title(page)
    return bridge_core.result(
        "Done: title block of %s: %s."
        % (page.Label, ", ".join("%s %r" % (k, now.get(k, "")) for k in values))
    )


# -- the sheet bar ---------------------------------------------------------------------------------
def _sheet_rows(page):
    from ... import drawing_sheets

    return [
        "%d. %s (id %r)" % (i + 1, drawing_sheets.sheet_name(s), s.Name)
        for i, s in enumerate(drawing_sheets.sheets(page))
    ]


def _gui_sheet_bars(page):
    if not App.GuiUp:
        return
    try:
        from ... import drawing_sheets_ui

        drawing_sheets_ui._refresh_bars(page)
    except Exception as exc:
        log("AI drawing: sheet bar: %s" % exc)


@action("drawing_sheet")
def drawing_sheet(ctx, args):
    from ... import drawing, drawing_sheets

    page = _page(ctx, args.get("drawing"))
    doc = page.Document
    action_name = args["action"]
    if action_name == "add":
        made = _change(ctx, lambda: drawing_sheets.add_sheet(page, args.get("index")), doc)
        _gui_sheet_bars(made)
        return bridge_core.result(
            "Done: sheet %r (id %r) added. Sheets: %s."
            % (drawing_sheets.sheet_name(made), made.Name, "; ".join(_sheet_rows(made)))
        )
    if action_name == "rename":
        _change(ctx, lambda: drawing_sheets.rename_sheet(page, args["name"]), doc)
    elif action_name == "move":
        _change(ctx, lambda: drawing_sheets.move_sheet(page, int(args["index"])), doc)
    else:
        order = drawing_sheets.sheets(page)
        if len(order) <= 1:
            raise UserError(
                "A drawing keeps at least one sheet: delete the whole drawing with "
                "modify_drawing kind delete instead."
            )
        rest = [s for s in order if not drawing.same(s, page)]
        if App.GuiUp:
            try:
                from ... import drawing_sheets_ui, drawing_ui

                index = [i for i, s in enumerate(order) if drawing.same(s, page)][0]
                if drawing.same(drawing_ui.active_page(), page):
                    drawing_sheets_ui.switch_to(rest[min(index, len(rest) - 1)])
                else:
                    drawing_ui.close_tab(page)
            except Exception as exc:
                warn("AI drawing: the sheet's tab: %s" % exc)
        shown = _change(ctx, lambda: drawing_sheets.delete_sheet(page), doc)
        _gui_sheet_bars(shown)
        return bridge_core.result(
            "Done: sheet deleted. Sheets: %s." % "; ".join(_sheet_rows(shown))
        )
    _gui_sheet_bars(page)
    return bridge_core.result("Done. Sheets: %s." % "; ".join(_sheet_rows(page)))


# -- dimensions ------------------------------------------------------------------------------------
def _edge_counts(view):
    """(visible, hidden) model edges of a view: TechDraw numbers the visible ones first,
    then the hidden ones, then its cosmetic lines (centre marks, centre lines...)."""
    try:
        return len(view.getVisibleEdges()), len(view.getHiddenEdges())
    except Exception:
        return None, None


def view_elements(view, limit=3000, cosmetic=False):
    """[info] of every element of a view (drawing.edge_info: lines, circles, arcs), each
    marked "hidden" when it is a hidden edge; the cosmetic lines Fission 180 draws on a view
    (centre marks and lines, edge extensions) only with cosmetic (marked so)."""
    from ... import drawing

    visible, hidden = _edge_counts(view)
    found = []
    misses = 0
    for i in range(limit):
        info = drawing.edge_info(view, "Edge%d" % i)
        if info is None:
            misses += 1
            if misses > 3:
                break
            continue
        misses = 0
        if visible is not None and i >= visible:
            if i >= visible + hidden:
                if not cosmetic:
                    continue
                info["cosmetic"] = True
            else:
                info["hidden"] = True
        found.append(info)
    return found


def view_vertexes(view, limit=3000):
    from ... import drawing

    found = []
    for i in range(limit):
        info = drawing.edge_info(view, "Vertex%d" % i)
        if info is None:
            break
        found.append(info)
    return found


def _distance(info, point):
    px, py = point
    if info["kind"] == "line":
        (x1, y1), (x2, y2) = info["p1"], info["p2"]
        dx, dy = x2 - x1, y2 - y1
        length = dx * dx + dy * dy
        t = (
            0.0
            if length < 1e-12
            else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length))
        )
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
    if info["kind"] in ("circle", "arc"):
        cx, cy = info["center"]
        return abs(math.hypot(px - cx, py - cy) - info["radius"])
    if info["kind"] == "vertex":
        return math.hypot(px - info["point"][0], py - info["point"][1])
    return float("inf")


def _find(view, elements, pick, index, what="picks[%d]"):
    label = what % index if "%d" in what else what
    kind = pick.get("kind")
    if kind == "vertex":
        candidates = view_vertexes(view)
    else:
        candidates = [e for e in elements if kind in (None, e["kind"])]
    if "radius" in pick:
        candidates = [
            e
            for e in candidates
            if e["kind"] in ("circle", "arc") and abs(e["radius"] - pick["radius"]) < 1e-3
        ]
    if not candidates:
        raise UserError(
            "%s: the view has no such element (get_drawing with edges true " "lists them)." % label
        )
    if "near" in pick:  # (a visible edge before the hidden one drawn on it)
        return min(
            candidates, key=lambda e: (round(_distance(e, pick["near"]), 6), bool(e.get("hidden")))
        )
    shown = [e for e in candidates if not e.get("hidden")]
    if len(shown) == 1:
        return shown[0]
    if len(candidates) > 1:
        raise UserError(
            "%s: %d elements match: give near [x, y] (get_drawing with "
            "edges true lists them)." % (label, len(candidates))
        )
    return candidates[0]


def _need_flat(view):
    from ... import drawing

    if drawing.is_isometric(view):
        raise UserError(
            "An isometric view cannot be dimensioned: its lengths are drawn shorter. "
            "Dimension a front, top or side view."
        )


FORCED = {
    "linear": ("DistanceX", "DistanceY"),
    "aligned": ("Distance",),
    "radius": ("Radius",),
    "diameter": ("Diameter",),
    "angular": ("Angle", "Angle3Pt"),
}


def _texts_taken(view):
    """Local points of the texts of the dimensions a view already has."""
    from ... import drawing

    out = []
    page = drawing.page_of(view)
    x, y = drawing.view_position(view)
    s = drawing.scale_of(view) or 1.0
    for dim in drawing.annotations(page) if page is not None else []:
        if dim.TypeId == drawing.DIMENSION and dim.References2D:
            if drawing.same(dim.References2D[0][0], view):
                out.append((drawing._value(dim.X) / s, drawing._value(dim.Y) / s))
    return out


def _refs_for(view, infos, result):
    from ... import drawing

    refs = []
    for i, info in enumerate(infos):
        if i in result.get("use_centers", []):
            centre = drawing.center_vertex(view, info["center"])
            if centre is None:
                raise UserError("The centre of that circle is not a point of the view.")
            refs.append(centre)
        else:
            refs.append(info["name"])
    return refs


def _dimension_answer(dims):
    from ... import drawing

    parts = []
    for dim in dims:
        value = drawing.dimension_value(dim)
        parts.append(
            "%s %r: %s (written %r)"
            % (
                dim.Type,
                dim.Name,
                ("%.6g" % value) if value is not None else "?",
                drawing.dimension_text(dim),
            )
        )
    return "; ".join(parts)


@action("add_drawing_dimension")
def add_drawing_dimension(ctx, args):
    forced = args.get("type")
    if forced == "ordinate":
        return _ordinate(ctx, args)
    if forced in ("baseline", "chain"):
        return _stacked(ctx, args, forced == "chain")
    from ... import drawing, drawing_core

    view = _view(ctx, args["view"])
    _idle(view.Document)
    _need_flat(view)
    elements = view_elements(view)
    infos = [_find(view, elements, pick, i) for i, pick in enumerate(args["picks"])]
    if forced == "arc_length":
        return _arc_length(ctx, view, infos[0], args)
    place = drawing.page_to_local(view, args["at"]) if "at" in args else None
    result = drawing_core.infer_dimension(infos, place)
    if "error" in result:
        raise UserError(result["error"])
    if "need" in result:
        raise UserError("One more element is needed for that dimension.")
    if forced:
        allowed = FORCED[forced]
        if result["type"] not in allowed:
            swap = {
                ("linear", "Distance"): aicore.linear_axis(infos),
                ("aligned", "DistanceX"): "Distance",
                ("aligned", "DistanceY"): "Distance",
                ("radius", "Diameter"): "Radius",
                ("diameter", "Radius"): "Diameter",
            }.get((forced, result["type"]))
            if swap is None:
                raise UserError("That is not something a %s dimension measures." % forced)
            result["type"] = swap
    refs = _refs_for(view, infos, result)
    if "at" in args:
        position = tuple(args["at"])
    else:
        local = aicore.dimension_place(
            result["type"],
            infos,
            _local_extent(view),
            drawing.scale_of(view),
            _texts_taken(view),
        )
        position = drawing.local_to_page(view, local)
    page = drawing.page_of(view)
    dim = _change(
        ctx, lambda: drawing.add_dimension(view, refs, result["type"], position), page.Document
    )
    return bridge_core.result(
        "Done: dimension on %s: %s; it measures %s."
        % (view.Label, _dimension_answer([dim]), ", ".join(aicore.element_text(i) for i in infos))
    )


def _local_extent(view):
    from ... import drawing

    hw, hh = drawing.view_extent(view)
    s = drawing.scale_of(view) or 1.0
    return hw / s, hh / s


def _arc_length(ctx, view, info, args):
    from ... import drawing, drawing_annot

    if info["kind"] != "arc":
        raise UserError(
            "An arc length needs an arc (part of a circle): a whole circle takes a diameter."
        )
    page = drawing.page_of(view)
    anchor = drawing_annot.make_anchor(view, info["name"], aicore.element_point(info))
    if "at" in args:
        at = tuple(args["at"])
    else:  # (out from the arc's centre, 8 mm past the arc on the sheet)
        centre = drawing.local_to_page(view, info["center"])
        mid = drawing_annot.page_point(view, anchor) or centre
        at = aicore.outward((centre[0], centre[1], centre[0], centre[1]), mid, 8.0)
    base = drawing.view_position(view)
    data = {"kind": "arc", "anchor": anchor, "off": [at[0] - base[0], at[1] - base[1]]}
    obj = _change(ctx, lambda: drawing_annot.add_annotation(page, data, view), page.Document)
    return bridge_core.result(
        "Done: arc length %r on %s: %s (%s)."
        % (obj.Name, view.Label, drawing_annot.describe(obj), aicore.element_text(info))
    )


def _anchor_of(view, info):
    from ... import drawing_annot

    return drawing_annot.make_anchor(view, info["name"], aicore.element_point(info))


def _ordinate(ctx, args):
    """Fusion's Ordinate Dimension: the origin's 0 and a value per point, along x, y or
    both, their texts on one line each (OrdinatePanel's code)."""
    from ... import drawing, drawing_annot

    view = _view(ctx, args["view"])
    _idle(view.Document)
    _need_flat(view)
    page = drawing.page_of(view)
    elements = view_elements(view)
    origin_info = _find(view, elements, args["origin"], 0, "origin")
    infos = [_find(view, elements, pick, i) for i, pick in enumerate(args["picks"])]
    axes = ["x", "y"] if args.get("axis", "both") == "both" else [args["axis"]]
    rect = drawing.view_rect(view)
    at = args.get("at")

    def work():
        origin = _anchor_of(view, origin_info)
        made = []
        for axis in axes:
            line = aicore.ordinate_lines(rect, axis, at)
            o_page = drawing.local_to_page(view, drawing_annot.centre_point(origin))
            if not drawing_annot.has_zero(page, view, origin, axis):
                zero = (o_page[0], line) if axis == "x" else (line, o_page[1])
                made.append(drawing_annot.add_ordinate(view, origin, origin, axis, zero))
            for info in infos:
                anchor = _anchor_of(view, info)
                f = drawing.local_to_page(view, drawing_annot.centre_point(anchor))
                place = (f[0], line) if axis == "x" else (line, f[1])
                made.append(drawing_annot.add_ordinate(view, origin, anchor, axis, place))
        return made

    made = _change(ctx, work, page.Document)
    rows = [
        "%s %r = %s"
        % (
            drawing_annot.annotation_data(o).get("axis"),
            o.Name,
            _num(drawing_annot.ordinate_value(o)),
        )
        for o in made
    ]
    return bridge_core.result(
        "Done: %d ordinate values on %s from %s: %s."
        % (len(made), view.Label, aicore.element_text(origin_info), "; ".join(rows))
    )


def _num(value):
    return "?" if value is None else "%g" % aicore.r(value, 4)


def _stacked(ctx, args, chain):
    """Fusion's Baseline / Chain Dimension from an existing horizontal or vertical
    dimension (StackPanel's code)."""
    from ... import drawing, drawing_annot

    base = ctx.resolve(args["from"], "dimension")
    if base.TypeId != drawing.DIMENSION or base.Type not in ("DistanceX", "DistanceY"):
        raise UserError(
            "%r is not a horizontal or vertical dimension: Baseline and Chain go on from one "
            "(make it with type linear first)." % args["from"]
        )
    view = base.References2D[0][0]
    if "view" in args and not drawing.same(_view(ctx, args["view"]), view):
        raise UserError("The picks must be on %s, the view of %s." % (view.Label, base.Name))
    _idle(view.Document)
    page = drawing.page_of(view)
    elements = view_elements(view)
    targets = []
    for i, pick in enumerate(args["picks"]):
        info = _find(view, elements, pick, i)
        local = aicore.element_point(info)
        if info["kind"] in ("circle", "arc"):
            name = drawing.center_vertex(view, info["center"])
        elif info["kind"] == "vertex":
            name = info["name"]
        else:  # a line: its end nearer the pick
            near = pick.get("near", local)
            local = min(
                (info["p1"], info["p2"]), key=lambda p: math.hypot(p[0] - near[0], p[1] - near[1])
            )
            name = drawing_annot.vertex_at(view, local)
        if name is None:
            raise UserError("picks[%d]: that is not a point the view can measure to." % i)
        targets.append((name, tuple(local)))
    points = drawing_annot.dimension_points(base)
    if points is None:
        raise UserError("%s has no ends to go on from." % base.Name)
    target_pages = [drawing.local_to_page(view, t[1]) for t in targets]
    end = aicore.baseline_start(points, target_pages)
    if chain:
        end = 1 - end  # (a chain goes on from the end nearer the new points)
    name, end_page = drawing_annot.base_reference(base, points[end])
    if name is None:
        raise UserError("%s's end is not a point Fission 180 can measure from." % base.Name)
    spacing = 8.0

    def work():
        made = []
        start_name, start_page = name, end_page
        base_text = drawing_annot.dimension_line_offset(base)
        for count, (vertex, local) in enumerate(targets, start=1):
            target = drawing.local_to_page(view, local)
            if vertex == start_name:
                raise UserError("A point is the one the dimension starts from: pick another.")
            if chain:
                at = _chain_text(base.Type, base_text, start_page, target)
            else:
                at = drawing_annot.stacked_position(
                    base.Type, base_text, start_page, target, spacing, count
                )
            made.append(drawing.add_dimension(view, [start_name, vertex], base.Type, at))
            if chain:
                start_name, start_page = vertex, target
        return made

    made = _change(ctx, work, page.Document)
    return bridge_core.result(
        "Done: %d %s dimensions from %s: %s."
        % (len(made), "chain" if chain else "baseline", base.Name, _dimension_answer(made))
    )


def _chain_text(dim_type, base_text, start, target):
    if dim_type == "DistanceX":
        return (start[0] + target[0]) / 2.0, base_text[1]
    return base_text[0], (start[1] + target[1]) / 2.0


# -- DIMENSIONS > Edit Dimension -------------------------------------------------------------------
@action("edit_drawing_dimension")
def edit_drawing_dimension(ctx, args):
    from ... import drawing, drawing_annot
    from ... import drawing_dims_core as dc

    dims = []
    for ident in args["dimensions"]:
        dim = ctx.resolve(ident, "dimension")
        if dim.TypeId != drawing.DIMENSION:
            raise UserError(
                "%r is not a dimension (ordinates and arc lengths are written by Fission 180: "
                "delete and make them again to change them)." % ident
            )
        dims.append(dim)
    plans = []
    for dim in dims:
        data = aicore.dimension_settings(args, drawing_annot.dimension_settings(dim))
        problem = dc.validate(data, drawing.dimension_value(dim), drawing_annot.dimension_kind(dim))
        if problem:
            raise UserError("%s: %s" % (dim.Name, problem))
        plans.append((dim, data))
    page = drawing.page_of(dims[0])

    def work():
        for dim, data in plans:
            drawing_annot.set_dimension_settings(dim, data)
        if "at" in args:
            drawing.place_dimension(dims[0], tuple(args["at"]))

    _change(ctx, work, page.Document)
    return bridge_core.result("Done: %s." % _dimension_answer(dims))


# -- TEXT and TABLES -------------------------------------------------------------------------------
def _find_row(ctx, page, table, ident):
    """The parts-list row a component name, part number or body id names."""
    from ... import bodies, components, drawing

    rows = drawing.table_rows(table)
    wanted = str(ident).strip()
    for row in rows:
        if str(row.get("PartNumber", "")).strip().lower() == wanted.lower():
            return row
    try:
        obj = ctx.resolve(wanted, "component or body")
    except UserError:
        obj = None
    names = set()
    if obj is not None:
        if bodies.is_body(obj):
            names.add(obj.Name)
        elif components.is_component(obj):
            names |= {b.Name for b in components.bodies_in(obj.Document, obj, recursive=True)}
        else:
            body = bodies.body_of(obj)
            if body is not None:
                names.add(body.Name)
    for row in rows:
        if names & set(row.get("bodies") or []):
            return row
    raise UserError(
        "The parts list has no row %r: its rows are %s."
        % (ident, ", ".join("%s %s" % (r.get("Item"), r.get("PartNumber")) for r in rows))
    )


@action("add_drawing_annotation")
def add_drawing_annotation(ctx, args):
    from ... import drawing, drawing_annot, drawing_core, flatpattern_drawing

    kind = args["kind"]
    view = _view(ctx, args["view"]) if args.get("view") else None
    page = (
        _page(ctx, args.get("drawing"))
        if args.get("drawing") or view is None
        else drawing.page_of(view)
    )
    w, h = _sheet(page)
    doc = page.Document
    _idle(doc)
    if view is not None and not drawing.same(drawing.page_of(view), page):
        raise UserError("%s is on another sheet than %s." % (view.Label, page.Label))

    if kind == "text":
        at = args.get("at", (0.1 * w, 0.12 * h))
        note = _change(
            ctx,
            lambda: drawing.add_text(
                page, str(args["text"]).split("\n"), at, args.get("size", 3.5)
            ),
            doc,
        )
        return bridge_core.result(
            "Done: text %r on %s at [%g, %g]." % (note.Name, page.Label, at[0], at[1])
        )

    if kind == "leader":
        info = _find(view, view_elements(view), args["pick"], 0, "pick")
        anchor = _anchor_of(view, info)
        start = drawing_annot.page_point(view, anchor)
        at = (
            tuple(args["at"])
            if "at" in args
            else aicore.outward(drawing.view_rect(view), start, 15.0)
        )
        base = drawing.view_position(view)
        data = {
            "kind": "leader",
            "anchor": anchor,
            "off": [at[0] - base[0], at[1] - base[1]],
            "lines": str(args["text"]).split("\n"),
        }
        obj = _change(ctx, lambda: drawing_annot.add_annotation(page, data, view), doc)
        return bridge_core.result(
            "Done: leader %r on %s, its arrow on %s, its text at [%g, %g]."
            % (
                obj.Name,
                view.Label,
                aicore.element_text(info),
                aicore.r(at[0], 2),
                aicore.r(at[1], 2),
            )
        )

    if kind == "parts_list":
        at = args.get("at", (0.62 * w, 0.95 * h))
        table, balloons = _change(
            ctx, lambda: drawing.add_parts_list(page, view, at, args.get("balloons", True)), doc
        )
        rows = drawing.table_rows(table)
        missing = len(rows) - len(balloons) if args.get("balloons", True) else 0
        return bridge_core.result(
            "Done: parts list %r with %d rows (%s) and %d balloons on %s.%s"
            % (
                table.Name,
                len(rows),
                ", ".join(
                    "%s %s x%s" % (r.get("Item"), r.get("PartNumber"), r.get("Qty")) for r in rows
                ),
                len(balloons),
                view.Label,
                (
                    (" %d rows' parts are hidden in this view: no balloon." % missing)
                    if missing > 0
                    else ""
                ),
            )
        )

    if kind == "bend_table":
        if flatpattern_drawing.flat_of(view) is None:
            raise UserError(
                "%s does not show a flat pattern: a bend table needs a flat pattern view "
                "(create_drawing or add_drawing_view with flat_pattern)." % view.Label
            )
        x0, _y0, _x1, y1 = drawing_core.drawing_area(
            drawing.standard_of(page), drawing.sheet_of(page)
        )
        at = args.get("at", (x0 + 4.0, y1 - 4.0))
        table, balloons = _change(
            ctx, lambda: flatpattern_drawing.add_bend_table(page, view, at), doc
        )
        rows = drawing.table_rows(table)
        return bridge_core.result(
            "Done: bend table %r with %d bends (%s) and their identifiers on %s."
            % (
                table.Name,
                len(rows),
                "; ".join(
                    "%s %s %s R%s" % (r["Item"], r["Direction"], r["Angle"], r["Radius"])
                    for r in rows
                ),
                view.Label,
            )
        )

    if kind == "bend_note":
        fp = flatpattern_drawing.flat_of(view)
        if fp is None:
            raise UserError(
                "%s does not show a flat pattern (bend notes go on its bend lines)." % view.Label
            )
        count = len(flatpattern_drawing.bend_rows(fp))
        if not count:
            raise UserError("That flat pattern has no bends.")
        wanted = args.get("bends") or list(range(1, count + 1))
        bad = [b for b in wanted if not 1 <= b <= count]
        if bad:
            raise UserError(
                "The flat pattern has bends 1 to %d (B1..B%d), not %s." % (count, count, bad)
            )
        have = {
            int(getattr(n, "Fission180Bend", -1))
            for n in flatpattern_drawing.bend_notes_of(page, view)
        }
        todo = [b for b in wanted if b - 1 not in have]
        if not todo:
            raise UserError("Those bends have their notes already.")
        notes = _change(
            ctx, lambda: [flatpattern_drawing.add_bend_note(page, view, b - 1) for b in todo], doc
        )
        return bridge_core.result(
            "Done: %d bend notes on %s: %s."
            % (
                len(notes),
                view.Label,
                "; ".join("B%d %s" % (b, " ".join(n.Text)) for b, n in zip(todo, notes)),
            )
        )

    if kind == "balloon":
        table = drawing.parts_list_of(page)
        if table is None:
            raise UserError(
                "Balloons number the parts list's rows: make the parts list first "
                "(add_drawing_annotation kind parts_list)."
            )
        row = _find_row(ctx, page, table, args["component"])
        anchor = drawing.component_anchor(view, row.get("bodies", []))
        if anchor is None:
            raise UserError(
                "%s does not show %s (hidden or off the view)."
                % (view.Label, row.get("PartNumber"))
            )
        if "at" in args:
            spot = tuple(args["at"])
        else:
            spot = drawing_core.balloon_layout(
                drawing.view_rect(view),
                [anchor],
                _blocked(page, skip=(view.Name,)),
                drawing_core.frame_rect(drawing.standard_of(page), drawing.sheet_of(page)),
            )[0]
        balloon = _change(ctx, lambda: drawing.add_balloon_at(view, anchor, spot, row["Item"]), doc)
        return bridge_core.result(
            "Done: balloon %r (%s, %s) on %s at [%g, %g]."
            % (
                balloon.Name,
                row["Item"],
                row.get("PartNumber"),
                view.Label,
                aicore.r(spot[0], 2),
                aicore.r(spot[1], 2),
            )
        )

    # center_marks: every circle that has no mark yet
    def work():
        have = [m["c"] for m in drawing.center_marks(view)]
        made = []
        for info in view_elements(view):
            if info["kind"] == "circle":
                c = info["center"]
                if all(math.hypot(c[0] - h[0], c[1] - h[1]) > 1e-6 for h in have):
                    made.append(drawing.add_center_mark(view, info["name"]))
                    have.append(c)
        if not made:
            if have:
                raise UserError("Every circle of %s has its centre mark already." % view.Label)
            raise UserError("%s shows no circle." % view.Label)
        return made

    made = _change(ctx, work, doc)
    return bridge_core.result("Done: %d centre marks on %s." % (len(made), view.Label))


# -- GEOMETRY --------------------------------------------------------------------------------------
@action("add_drawing_geometry")
def add_drawing_geometry(ctx, args):
    from ... import drawing, drawing_tools

    view = _view(ctx, args["view"])
    doc = view.Document
    _idle(doc)
    kind = args["kind"]
    elements = view_elements(view)
    picks = args.get("picks") or []
    infos = [_find(view, elements, pick, i) for i, pick in enumerate(picks)]
    if kind == "center_mark":
        if not infos:
            return add_drawing_annotation(ctx, {"kind": "center_marks", "view": view.Name})
        for i, info in enumerate(infos):
            if info["kind"] not in ("circle", "arc"):
                raise UserError(
                    "picks[%d] is a %s: a centre mark goes on a circle or an arc."
                    % (i, info["kind"])
                )
        have = [m["c"] for m in drawing.center_marks(view)]
        for i, info in enumerate(infos):
            c = info["center"]
            if any(math.hypot(c[0] - h[0], c[1] - h[1]) < 1e-6 for h in have):
                raise UserError(
                    "picks[%d] (%s) has a centre mark already." % (i, aicore.element_text(info))
                )

        def work():
            return [drawing.add_center_mark(view, info["name"]) for info in infos]

        made = _change(ctx, work, doc)
        return bridge_core.result(
            "Done: %d centre marks on %s: %s."
            % (len(made), view.Label, "; ".join(aicore.element_text(i) for i in infos))
        )
    if kind == "centerline":
        _change(ctx, lambda: drawing.add_centerline(view, infos[0]["name"], infos[1]["name"]), doc)
        return bridge_core.result(
            "Done: centre line on %s between %s and %s."
            % (view.Label, aicore.element_text(infos[0]), aicore.element_text(infos[1]))
        )
    if kind == "edge_extension":
        for i, info in enumerate(infos):
            if info["kind"] != "line":
                raise UserError(
                    "picks[%d] is a %s: edge extensions take straight edges." % (i, info["kind"])
                )
        _change(
            ctx, lambda: drawing.add_edge_extension(view, infos[0]["name"], infos[1]["name"]), doc
        )
        ext = drawing.extensions_of(view)
        corner = ext[-1].get("point") if ext else None
        return bridge_core.result(
            "Done: edge extension on %s%s: dimension to that corner with a vertex pick there."
            % (
                view.Label,
                (
                    (" meeting at (%g, %g)" % (aicore.r(corner[0]), aicore.r(corner[1])))
                    if corner
                    else ""
                ),
            )
        )
    # center_mark_pattern
    shape = _change(
        ctx, lambda: drawing_tools.add_mark_pattern(view, [i["name"] for i in infos]), doc
    )
    what = "a line" if shape[0] == "line" else "a bolt circle of R%g" % aicore.r(shape[2])
    return bridge_core.result(
        "Done: centre mark pattern on %s: %d holes on %s." % (view.Label, len(infos), what)
    )


# -- SYMBOLS ---------------------------------------------------------------------------------------
def _row(spec):
    return {
        "char": spec.get("characteristic", "position"),
        "dia": bool(spec.get("diameter_zone", False)),
        "tol": "%g" % float(spec.get("tolerance", 0.1)),
        "mod": spec.get("material", ""),
        "datums": [
            [str(d).strip().upper(), ""] for d in spec.get("datums") or [] if str(d).strip()
        ],
    }


@action("add_drawing_symbol")
def add_drawing_symbol(ctx, args):
    from ... import drawing, drawing_annot

    kind = args["kind"]
    view = _view(ctx, args["view"]) if args.get("view") else None
    page = drawing.page_of(view) if view is not None else _page(ctx, args.get("drawing"))
    doc = page.Document
    _idle(doc)
    anchor = None
    info = None
    if view is not None:
        info = _find(view, view_elements(view), args["pick"], 0, "pick")
        anchor = _anchor_of(view, info)
    if "at" in args:
        at = tuple(args["at"])
    else:  # (beside the edge, away from the view's middle, like a person puts it)
        at = aicore.outward(
            drawing.view_rect(view), drawing_annot.page_point(view, anchor), SYMBOL_REACH
        )
    base = drawing.view_position(view) if view is not None else (0.0, 0.0)
    data = {
        "kind": {
            "surface_texture": "texture",
            "feature_control_frame": "fcf",
            "datum_identifier": "datum",
        }[kind],
        "anchor": anchor,
        "off": [at[0] - base[0], at[1] - base[1]],
    }
    if kind == "surface_texture":
        start = drawing_annot.page_point(view, anchor)
        if start is not None and math.hypot(at[0] - start[0], at[1] - start[1]) < 2.0:
            data["off"] = [start[0] - base[0], start[1] - base[1]]  # (on the edge)
        data["texture"] = {
            "kind": args.get("texture", "removal"),
            "value": args.get("value", "Ra 3.2"),
            "lay": args.get("lay", ""),
            "all_around": bool(args.get("all_around", False)),
        }
    elif kind == "feature_control_frame":
        row1 = _row(dict(args, characteristic=args.get("characteristic", "position")))
        if "diameter_zone" not in args:
            row1["dia"] = row1["char"] == "position"  # (a position zone is round)
        fcf = {"row1": row1}
        if args.get("second_row"):
            fcf["row2"] = _row(dict(args["second_row"], characteristic=row1["char"]))
            fcf["composite"] = True
        data["fcf"] = fcf
    else:
        letter = str(args.get("letter") or drawing_annot.next_datum_letter(page)).strip().upper()
        if letter in drawing_annot.used_datum_letters(page):
            raise UserError(
                "Datum %s is used already on this drawing: take another letter." % letter
            )
        data["letter"] = letter
    obj = _change(ctx, lambda: drawing_annot.add_annotation(page, data, view), doc)
    return bridge_core.result(
        "Done: %s %r on %s%s: %s."
        % (
            kind.replace("_", " "),
            obj.Name,
            view.Label if view is not None else page.Label,
            (" (%s)" % aicore.element_text(info)) if info else "",
            drawing_annot.describe(obj),
        )
    )


# -- TABLES > Renumber, Align Balloons -------------------------------------------------------------
def _balloon(ctx, page, ident):
    from ... import drawing, drawing_sheets, drawing_tools

    doc = page.Document
    obj = doc.getObject(str(ident))
    if obj is not None and obj.TypeId == drawing.BALLOON:
        return obj
    for sheet in drawing_sheets.sheets(page):
        for balloon in drawing_tools.balloons_of(sheet):
            if str(balloon.Text).strip() == str(ident).strip() or balloon.Label == ident:
                return balloon
    raise UserError(
        "There is no balloon %r on %s (get_drawing lists the balloons and their numbers)."
        % (ident, page.Label)
    )


@action("edit_balloons")
def edit_balloons(ctx, args):
    from ... import drawing, drawing_tools

    page = _page(ctx, args.get("drawing"))
    doc = page.Document
    if args["kind"] == "renumber":
        balloon = _balloon(ctx, page, args["balloon"])
        home = drawing.page_of(balloon)
        old, new = _change(ctx, lambda: drawing_tools.renumber(home, balloon, int(args["to"])), doc)
        table = drawing.parts_list_of(home)
        rows = drawing.table_rows(table) if table is not None else []
        return bridge_core.result(
            "Done: item %d is now %d. Parts list: %s."
            % (old, new, ", ".join("%s %s" % (r.get("Item"), r.get("PartNumber")) for r in rows))
        )
    balloons = [_balloon(ctx, page, b) for b in args["balloons"]]
    way = _change(ctx, lambda: drawing_tools.align_balloons(balloons, tuple(args["at"])), doc)
    spots = [drawing.balloon_page_points(b)[1] for b in balloons]
    return bridge_core.result(
        "Done: %d balloons on one %s line: %s."
        % (
            len(balloons),
            "level" if way == "horizontal" else "upright",
            ", ".join(
                "%s at [%g, %g]" % (b.Text, aicore.r(p[0], 2), aicore.r(p[1], 2))
                for b, p in zip(balloons, spots)
            ),
        )
    )


# -- reading --------------------------------------------------------------------------------------
def _rounded_info(info):
    info = dict(info)
    for key in ("p1", "p2", "center", "point"):
        if key in info:
            info[key] = [aicore.r(v, 4) for v in info[key]]
    if "radius" in info:
        info["radius"] = aicore.r(info["radius"], 4)
    return info


def _view_row(view, edges=False):
    from ... import drawing, drawing_breakout, drawing_exploded, flatpattern_drawing

    x, y = drawing.view_position(view)
    hw, hh = drawing.view_extent(view)
    item = {
        "id": view.Name,
        "label": view.Label,
        "kind": drawing.kind(view) or view.TypeId.split("::")[-1],
        "orientation": drawing.orientation_of(view),
        "scale": drawing.scale_of(view),
        "scale_text": _scale_text(drawing.scale_of(view)),
        "at": [aicore.r(x, 3), aicore.r(y, 3)],
        "half_size_mm": [aicore.r(hw, 3), aicore.r(hh, 3)],
        "style": drawing.style_of(view),
    }
    if not getattr(view, "Visibility", True):
        item["hidden"] = True
    rotation = drawing._value(getattr(view, "Rotation", 0.0))
    if abs(rotation) > 1e-9:
        item["rotation"] = aicore.r(rotation, 3)
    if drawing.label_shown(view):
        item["view_label"] = drawing.view_label(view)
    parent = drawing.parent_of(view)
    if parent is not None:
        item["parent"] = parent.Name
    if drawing._get(view, "Fission180Kind", ""):
        item["direction"] = view.Fission180Kind
    shows = []
    fp = flatpattern_drawing.flat_of(view)
    if fp is not None:
        item["flat_pattern"] = fp.Name
        shows = [fp.Name]
    else:
        shows = [s.Name for s in drawing._view_sources(view)]
    item["shows"] = shows
    board = drawing_exploded.storyboard_of(view)
    if board:
        item["storyboard"] = board
    if drawing.is_section(view):
        mode, value = drawing.section_depth(view)
        item["section"] = {
            "letter": view.SectionSymbol,
            "line": [[aicore.r(a, 3) for a in p] for p in drawing.section_points(view)],
            "type": drawing.section_kind_of(view),
            "depth": mode if mode != "Distance" else "%s %g mm" % (mode, value),
            "hatch": getattr(view, "CutSurfaceDisplay", "") != "Hide",
        }
    if view.TypeId == drawing.DETAIL:
        a = view.AnchorPoint
        item["detail"] = {
            "letter": view.Reference,
            "center": [aicore.r(a.x, 3), aicore.r(a.y, 3)],
            "radius": aicore.r(drawing._value(view.Radius), 3),
        }
    if view.TypeId == drawing.BROKEN:
        original = drawing._get(view, "Fission180BrokenOf", None)
        item["break"] = {
            "of": original.Name if drawing.alive(original) else None,
            "gap": aicore.r(drawing._value(view.Gap), 3),
            "axis": drawing._get(view, "Fission180BreakAxis", ""),
        }
    data = drawing_breakout.breakout_of(view)
    if data:
        item["breakout"] = {
            "boundary": [[aicore.r(a, 3) for a in p] for p in data.get("points", [])],
            "depth": data.get("depth"),
        }
    marks = drawing.center_marks(view)
    if marks:
        item["center_marks"] = [
            {"center": [aicore.r(m["c"][0]), aicore.r(m["c"][1])], "radius": aicore.r(m["r"])}
            for m in marks
        ]
    try:
        lines = list(getattr(view, "CenterLines", []) or [])
        if lines:
            item["centerlines"] = len(lines)
    except Exception:
        pass
    auto = drawing.auto_mark_settings(view)
    if any(auto.values()):
        item["automatic_center_marks"] = sorted(k for k, v in auto.items() if v)
    ext = drawing.extensions_of(view)
    if ext:
        item["edge_extensions"] = len(ext)
    try:
        from ... import drawing_tools

        patterns = drawing_tools.mark_patterns(view)
        if patterns:
            item["center_mark_patterns"] = [
                {"kind": p.get("kind"), "holes": len(p.get("pts", []))} for p in patterns
            ]
    except Exception:
        pass
    if edges:
        item["elements"] = [_rounded_info(i) for i in view_elements(view)]
        item["points"] = [_rounded_info(i)["point"] for i in view_vertexes(view)][:400]
    return item


def _dimension_row(dim):
    from ... import drawing

    value = drawing.dimension_value(dim)
    entry = {
        "id": dim.Name,
        "dimension_type": dim.Type,
        "value": aicore.r(value, 6) if value is not None else None,
        "text": drawing.dimension_text(dim),
    }
    try:
        view = dim.References2D[0][0]
        entry["view"] = view.Name
        measures = []
        for _v, subs in dim.References2D:
            # (one name, or a list of them: FreeCAD gives either, the window a list)
            for sub in [subs] if isinstance(subs, str) else list(subs):
                info = drawing.edge_info(view, sub)
                measures.append(aicore.element_text(info) if info else sub)
        entry["measures"] = measures
        entry["at"] = [aicore.r(v, 2) for v in _item_place(dim)]
    except Exception:
        pass
    return entry


def _annotation_row(obj):
    from ... import drawing, drawing_annot, drawing_tools, flatpattern_drawing

    entry = {"id": obj.Name, "label": obj.Label, "type": obj.TypeId.split("::")[-1]}
    if obj.TypeId == drawing.DIMENSION:
        entry.update(_dimension_row(obj))
        entry["kind"] = "dimension"
        return entry
    if obj.TypeId == drawing.BALLOON:
        origin, spot = drawing.balloon_page_points(obj)
        entry.update(
            {
                "kind": "balloon",
                "number": str(obj.Text),
                "view": obj.SourceView.Name if obj.SourceView is not None else None,
                "at": [aicore.r(spot[0], 2), aicore.r(spot[1], 2)],
                "points_at": [aicore.r(origin[0], 2), aicore.r(origin[1], 2)],
            }
        )
        return entry
    if drawing_annot.is_annotation(obj):
        data = drawing_annot.annotation_data(obj)
        entry["kind"] = data.get("kind")
        entry["text"] = drawing_annot.describe(obj)
        entry["view"] = data.get("view") or None
        if data.get("kind") == "ordinate":
            entry["axis"] = data.get("axis")
            entry["value"] = aicore.r(drawing_annot.ordinate_value(obj) or 0.0, 4)
        return entry
    if drawing_tools._is_table(obj):
        entry["kind"] = (
            "bend_table" if drawing.kind(obj) == flatpattern_drawing.TYPE else "parts_list"
        )
        rows = [
            {k: v for k, v in row.items() if k not in ("members",)}
            for row in drawing.table_rows(obj)
        ]
        entry["rows"] = rows
        return entry
    if obj.TypeId == drawing.ANNOTATION:
        entry["kind"] = (
            "bend_note" if drawing.kind(obj) == flatpattern_drawing.NOTE_TYPE else "text"
        )
        entry["text"] = "\n".join(obj.Text)
        entry["at"] = [aicore.r(drawing._value(obj.X), 2), aicore.r(drawing._value(obj.Y), 2)]
        return entry
    entry["kind"] = drawing.kind(obj) or "other"
    return entry


def _sheet_row(page, edges):
    from ... import drawing, drawing_sheets

    row = {
        "id": page.Name,
        "label": page.Label,
        "sheet_name": drawing_sheets.sheet_name(page),
        "standard": drawing.standard_of(page),
        "sheet": drawing.sheet_of(page),
        "units": drawing.units_of(page),
        "sheet_size_mm": list(_sheet(page)),
        "title_block": drawing.title(page),
        "views": [_view_row(v, edges) for v in drawing.all_views(page)],
        "annotations": [_annotation_row(o) for o in drawing.annotations(page)],
    }
    return row


def sheet_picture(page, width=1200):
    """A PNG (bytes) of one sheet, drawn from its DXF (drawing_picture.py)."""
    from ... import drawing, drawing_core
    from .. import drawing_picture

    folder = tempfile.mkdtemp(prefix="fission180-picture-")
    path = os.path.join(folder, "sheet.dxf")
    try:
        drawing.export_dxf(page, path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    finally:
        try:
            os.remove(path)
            os.rmdir(folder)
        except OSError:
            pass
    entities = drawing_core.read_dxf_entities(text)
    return drawing_picture.render(entities, _sheet(page), width)


@action("get_drawing")
def get_drawing(ctx, args):
    from ... import drawing, drawing_sheets

    doc = ctx.need_doc()
    _idle(doc)
    if args.get("drawing"):
        chosen = _page(ctx, args["drawing"])
        mains = [drawing_sheets.main_page(chosen)]
    else:
        chosen = None
        mains = drawing.drawings(doc) or _pages(doc)
    out = []
    for main in mains:
        sheets = drawing_sheets.sheets(main)
        if chosen is not None and drawing_sheets.is_sheet_page(chosen):
            sheets = [chosen]
        first = _sheet_row(sheets[0], args.get("edges"))
        row = dict(first)
        row["id"] = main.Name
        row["label"] = main.Label
        row["sheets"] = [
            {"id": s.Name, "name": drawing_sheets.sheet_name(s)}
            for s in drawing_sheets.sheets(main)
        ]
        contents = drawing._get(main, "Fission180Contents", "")
        if contents:
            row["contents"] = contents
        board = drawing._get(main, "Fission180Storyboard", "")
        if board:
            row["storyboard"] = board
        if len(sheets) > 1:
            row["more_sheets"] = [_sheet_row(s, args.get("edges")) for s in sheets[1:]]
        out.append(row)
    if not args.get("picture"):
        return json_result({"drawings": out}, compact=True)
    page = chosen or mains[-1]
    try:
        png = sheet_picture(page, int(args.get("width", 1200)))
    except Exception as exc:
        warn("AI drawing picture: %s" % exc)
        raise UserError("The sheet could not be drawn: %s" % exc)
    text = "A picture of %s (%s %s, %d px wide), drawn from its DXF.\n" % (
        page.Label,
        drawing.standard_of(page),
        drawing.sheet_of(page),
        int(args.get("width", 1200)),
    )
    body = json_result({"drawings": out}, compact=True)["text"]
    return bridge_core.result(text + body, base64.b64encode(png).decode("ascii"))


# -- EXPORT ----------------------------------------------------------------------------------------
@action("export_drawing")
def export_drawing(ctx, args):
    from ... import drawing, drawing_export, drawing_sheets

    page = _page(ctx, args.get("drawing"))
    path = ctx.full_path(args["path"])
    fmt = args["format"]
    sheets = args.get("sheets") or ("all" if fmt == "pdf" else "current")
    which = page if sheets == "current" else "all"
    targets = [path]
    if fmt in ("dxf", "dwg"):
        targets = [t for _s, t in drawing_sheets.dxf_paths(page, path, which)]
    for target in targets:
        if os.path.exists(target) and not ctx.host.confirm_overwrite(target):
            raise UserError(ctx.host.refuse_overwrite_text(target))
    _idle(page.Document)
    _recompute(page)
    _idle(page.Document)
    try:
        if fmt == "pdf":
            if not ctx.host.gui:
                raise UserError(
                    "PDF export needs the Fission 180 window (TechDraw prints the "
                    "sheet itself); export DXF instead, or run Fission 180."
                )
            written = drawing_sheets.export_pdf(page, path, which)
            written = [written] if isinstance(written, str) else written
        elif fmt == "dxf":
            written = drawing_sheets.export_dxf(page, path, which)
        elif fmt == "dwg":
            if drawing_export.dwg_converter() is None:
                raise UserError(
                    "Not written: a DWG file can only be made by a DWG converter program and "
                    "none is installed on this computer (LibreDWG's dxf2dwg, the ODA File "
                    "Converter or QCAD; FreeCAD's Preferences > Import-Export > DWG names its "
                    "place). Export format dxf instead: AutoCAD and every other DWG program "
                    "open it; or ask the person to install one of the three."
                )
            written = drawing_export.export_dwg(page, path, which)
        else:
            table = _csv_table(ctx, page, args.get("table"))
            written = [drawing_export.export_csv(table, path)]
            rows = len(drawing_export.table_cells(table)) - 1
            return bridge_core.result(
                "Exported %s (%s, %d rows) to %s." % (table.Label, page.Label, rows, written[0])
            )
    except drawing.DrawingError as exc:
        raise UserError(str(exc))
    written = [w for w in (written or []) if w] or [path]
    from .document_actions import export_losses

    names = os.path.basename(str(written[0])) if len(written) == 1 else "%d files" % len(written)
    lost = export_losses(
        page.Document,
        page,
        "drawing_" + ("dxf" if fmt == "dwg" else fmt),
        names,
        which="current" if (fmt != "pdf" and sheets == "current") else "all",
    )
    return bridge_core.result(
        "Exported %s to %s.%s" % (page.Label, ", ".join(map(str, written)), lost)
    )


def _csv_table(ctx, page, ident):
    from ... import drawing, drawing_export

    tables = drawing_export.tables(page)
    if ident:
        obj = ctx.resolve(ident, "table")
        if not drawing_export.is_table(obj):
            raise UserError("%r is not a table (a parts list or a bend table)." % ident)
        return obj
    if not tables:
        raise UserError(
            "%s has no table: make the parts list first (add_drawing_annotation kind "
            "parts_list) or a bend table." % page.Label
        )
    for table, _caption in tables:
        if drawing.kind(table) == "PartsList":
            return table
    return tables[0][0]
