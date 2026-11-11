# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion-style parameter names and formulas. Pure Python, unit tested.

In Fusion you write `width * 2`. FreeCAD needs `Parameters.width * 2` (the user parameters
live in an App::VarSet object named "Parameters"). These helpers translate between the two,
leaving units, functions and other objects' properties alone.

Fusion also reads a number without a unit as the design's units wherever a length is meant
(`Arm_Length + 5`, `min(100; max(45; Arm_Length))`, `9 * 1.02` typed for a length) and shows
the formula with the unit added (`Arm_Length + 5 mm`). FreeCAD refuses such a formula ("Unit
mismatch"). read() works out which numbers of a formula are lengths or angles and gives them
their unit, so the formula FreeCAD stores is the one Fusion would show (wave 7, the book
parity report: the book's drone limits gave 0 mm).
"""

import difflib
import keyword
import re

CONTAINER = "Parameters"
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# millimetres in one of each length unit, degrees in one of each angle unit
LENGTH_UNITS = {
    "nm": 1e-6,
    "um": 1e-3,
    "\u00b5m": 1e-3,
    "mm": 1.0,
    "cm": 10.0,
    "dm": 100.0,
    "m": 1000.0,
    "km": 1e6,
    "in": 25.4,
    '"': 25.4,
    "ft": 304.8,
    "'": 304.8,
    "thou": 0.0254,
    "mil": 0.0254,
    "yd": 914.4,
    "mi": 1609344.0,
}
ANGLE_UNITS = {"deg": 1.0, "\u00b0": 1.0, "rad": 57.29577951308232, "gon": 0.9}
# Every word FreeCAD's formula reader takes for a unit or a constant (App/Expression.l): a
# property with one of these names cannot be named in a formula ("Parameters.W" does not
# parse), so a parameter called W, H, T, t, h, g, s... is kept under another property name
# (prop_name) and the person never sees it.
FREECAD_WORDS = set(
    """nm um mm cm dm m km l ml Hz kHz MHz GHz THz ug mg g kg t s min h A mA kA MA K mK uK mol
    mmol cd in ft thou mil yd mi mph sqft cft lb lbm oz st cwt lbf N mN kN MN Pa kPa MPa GPa
    bar mbar Torr mTorr uTorr psi ksi Mpsi W mW kW VA V kV mV MS kS S mS uS Ohm kOhm MOhm C T
    G Wb F mF uF nF pF H mH uH nH J mJ kJ Nm VAs CV Ws kWh eV keV MeV cal kcal deg rad gon M
    AS pi e None True true False false""".split()
)
MANGLE = "F180_"  # the property of a parameter whose name FreeCAD reads as a unit

FUNCTIONS = {
    "abs",
    "acos",
    "asin",
    "atan",
    "atan2",
    "cath",
    "ceil",
    "cos",
    "cosh",
    "exp",
    "floor",
    "hypot",
    "log",
    "log10",
    "mod",
    "pow",
    "round",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
    "trunc",
    "min",
    "max",
    "sum",
    "average",
    "count",
    "stddev",
    "create",
    "list",
    "tuple",
    "vector",
    "matrix",
    "rotation",
    "placement",
    "str",
    "hiddenref",
    "href",
}
# Names a parameter cannot have: the units and constants a person types in formulas, and
# the functions. (W, H, T, h, t, s, g... are fine: see FREECAD_WORDS.)
UNIT_NAMES = {"nm", "um", "mm", "cm", "dm", "m", "km", "in", "ft", "thou", "mil", "yd", "mi"}
UNIT_NAMES |= {"deg", "rad", "gon", "kg", "min", "Pa", "pi", "PI"}
RESERVED = UNIT_NAMES | FUNCTIONS | {"ln", "None", "True", "true", "False", "false"}


class ParameterError(ValueError):
    pass


class UnknownName(ParameterError):
    """A formula names something that is no parameter (`.name`)."""

    def __init__(self, message, name):
        super().__init__(message)
        self.name = name


def check_name(name, existing=()):
    """Raise ParameterError unless `name` can be a parameter name."""
    if not name or not _IDENT.fullmatch(name):
        raise ParameterError(
            "'%s' is not a valid name: use letters, digits and _, starting with a letter." % name
        )
    if keyword.iskeyword(name) or name in RESERVED or name.startswith(MANGLE):
        raise ParameterError("'%s' is a unit or function name; pick another name." % name)
    if name in existing:
        raise ParameterError("A parameter named '%s' already exists." % name)
    return name


def prop_name(name):
    """The property that holds the parameter `name` (see FREECAD_WORDS)."""
    return MANGLE + name if name in FREECAD_WORDS else name


def display_name(prop):
    """The parameter's name as the person typed it, from its property's name."""
    return prop[len(MANGLE) :] if prop.startswith(MANGLE) else prop


def _replace(expr, fn):
    """Apply fn(identifier) to identifiers that are bare names (not after '.',
    not a function call, not inside quotes)."""
    out = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch in "'\"":
            end = expr.find(ch, i + 1)
            end = len(expr) if end < 0 else end + 1
            out.append(expr[i:end])
            i = end
            continue
        match = _IDENT.match(expr, i)
        if match and (i == 0 or not (expr[i - 1].isalnum() or expr[i - 1] in "_.")):
            word = match.group(0)
            after = expr[match.end() :].lstrip()
            marked = i > 0 and expr[i - 1] == "\x00"  # a unit (to_freecad)
            if after.startswith("(") or after.startswith(".") or marked:
                out.append(word)  # a function call or another object's property
            else:
                out.append(fn(word))
            i = match.end()
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def to_freecad(expr, names):
    """'width * 2' -> 'Parameters.width * 2' for the given parameter names. (Names only: a
    formula a person typed goes through read(), which also gives its numbers their units.)
    `names` from parameters.user_names() also say what kind each parameter is and the
    design's units: then the numbers of a sum or a min() get their unit here too
    (`Arm_Length + 5` -> `Parameters.Arm_Length + 5 mm`), for every dialog that stores a
    formula through this function."""
    kinds = getattr(names, "kinds", None)
    if kinds is not None:
        try:
            got = read(expr, kinds, getattr(names, "unit", "mm"), None, False)
            if got.freecad:
                return got.freecad
        except ParameterError:
            pass  # something only FreeCAD reads: names only, as before
    names = set(names)

    def qualified(word):
        return "%s.%s" % (CONTAINER, prop_name(word)) if word in names else word

    unit_names = [n for n in names if _is_unit(n)]
    if not unit_names:
        return _replace(expr, qualified)
    # a parameter called like a unit (m, h, s): "5 m" is still five metres
    marked = re.sub(
        r"(\d\s*)(%s)(?![A-Za-z0-9_])" % "|".join(re.escape(n) for n in unit_names),
        lambda m: m.group(1) + "\x00" + m.group(2),
        expr,
    )
    return _replace(marked, qualified).replace("\x00", "")


_FROM = re.compile(
    r"(?<![A-Za-z0-9_.])(?:<<%s>>|%s)\.([A-Za-z_][A-Za-z0-9_]*)" % (CONTAINER, CONTAINER)
)
_MANGLED = re.compile(r"(?<![A-Za-z0-9_.])%s([A-Za-z_][A-Za-z0-9_]*)" % MANGLE)


def from_freecad(expr):
    """'Parameters.width * 2' -> 'width * 2' (what the user typed)."""
    return _MANGLED.sub(r"\1", _FROM.sub(lambda m: display_name(m.group(1)), expr))


UNITS = {"mm": "App::PropertyDistance", "deg": "App::PropertyAngle", "": "App::PropertyFloat"}
# The units a user parameter can be given (Fusion's Unit list, the ones a design uses) ->
# what kind of value it is. A length is kept in an App::PropertyDistance (it may be negative:
# FreeCAD holds an App::PropertyLength at 0 or more, bug 4 of the book parity report).
PARAMETER_UNITS = {
    "mm": "length",
    "cm": "length",
    "m": "length",
    "in": "length",
    "ft": "length",
    "deg": "angle",
    "rad": "angle",
    "": "number",
}
KIND_TYPES = {
    "length": "App::PropertyDistance",
    "angle": "App::PropertyAngle",
    "number": "App::PropertyFloat",
}
# what a field's unit ("mm", "deg", "") or a kind name means
KIND_OF = {"mm": "length", "deg": "angle", "": "number", None: None}
KIND_OF.update({k: k for k in ("length", "angle", "number")})
KIND_WORDS = {"length": "a length", "angle": "an angle", "number": "a number without a unit"}
KIND_EXAMPLES = {"length": "25", "angle": "30", "number": "3"}


def property_type(unit):
    """The property type of a new parameter with this unit (see PARAMETER_UNITS)."""
    if unit not in PARAMETER_UNITS:
        raise ParameterError(
            "Unit must be one of: mm, cm, m, in, ft, deg, rad, or empty (no unit)."
        )
    return KIND_TYPES[PARAMETER_UNITS[unit]]


def kind_of_type(type_id):
    """'length' / 'angle' / 'number' for a parameter property's type."""
    if type_id in ("App::PropertyLength", "App::PropertyDistance"):
        return "length"
    if type_id == "App::PropertyAngle":
        return "angle"
    return "number"


def unit_of(type_id):
    """The base unit of a parameter property ("mm", "deg" or "")."""
    return {"length": "mm", "angle": "deg", "number": ""}[kind_of_type(type_id)]


def per_unit(unit):
    """How many mm (or degrees) one of `unit` is; 1 for no unit."""
    if unit in LENGTH_UNITS:
        return LENGTH_UNITS[unit]
    return ANGLE_UNITS.get(unit, 1.0)


# -- reading what a person typed -----------------------------------------------------------------
class _Token:
    __slots__ = ("kind", "text", "start", "end")

    def __init__(self, kind, text, start, end):
        self.kind, self.text, self.start, self.end = kind, text, start, end

    def __repr__(self):
        return "%s(%r)" % (self.kind, self.text)


_NUMBER = re.compile(r"(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?")
_NUMBER_COMMA = re.compile(r"(\d+,\d+|,\d+)([eE][-+]?\d+)?")
_OPS = ("==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/", "^", "%", "(", ")", ";", ",")
_OPS += ("?", ":", ".", "[", "]")
_UNIT_SIGNS = ("µm", "°", '"', "'")
_NOT_UNITS = ("pi", "e", "None", "True", "true", "False", "false")


def _is_unit(word):
    return word in FREECAD_WORDS and word not in _NOT_UNITS


def _tokens(text):
    """The tokens of a formula. A comma between digits is a decimal comma, as FreeCAD reads
    it ("2,5"), unless it separates the arguments of a function written without ';'
    (`max(10,20)` is two numbers; FreeCAD read 10.20)."""
    out = []
    i = 0
    n = len(text)
    calls = []  # for each open bracket: True when it is a function's, and has no ';'
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if text.startswith("<<", i):
            end = text.find(">>", i + 2)
            if end < 0:
                raise ParameterError("The text after << is never closed with >>.")
            out.append(_Token("string", text[i : end + 2], i, end + 2))
            i = end + 2
            continue
        match = _IDENT.match(text, i)
        if match:
            out.append(_Token("name", match.group(0), i, match.end()))
            i = match.end()
            continue
        match = None
        if not (calls and calls[-1]):
            match = _NUMBER_COMMA.match(text, i)
        match = match or _NUMBER.match(text, i)
        if match:
            out.append(_Token("number", match.group(0), i, match.end()))
            i = match.end()
            continue
        for sign in _UNIT_SIGNS:
            if text.startswith(sign, i):
                out.append(_Token("name", sign, i, i + len(sign)))
                i += len(sign)
                break
        else:
            for op in _OPS:
                if text.startswith(op, i):
                    if op == "(":
                        is_call = bool(out) and out[-1].kind == "name"
                        calls.append(is_call and not _has_semicolon(text, i))
                    elif op == ")" and calls:
                        calls.pop()
                    out.append(_Token("op", op, i, i + len(op)))
                    i += len(op)
                    break
            else:
                if ch == "=":
                    raise ParameterError(
                        "'=' can only start a formula or follow a new parameter's name "
                        "(Name = value)."
                    )
                raise ParameterError("'%s' cannot be part of a value." % ch)
    return out


def _has_semicolon(text, open_at):
    """True when the bracket opened at `open_at` holds a ';' at its own level (then a comma
    between digits is a decimal comma)."""
    level = 0
    for j in range(open_at, len(text)):
        c = text[j]
        if c == "(":
            level += 1
        elif c == ")":
            level -= 1
            if level == 0:
                return False
        elif c == ";" and level == 1:
            return True
    return False


class _Node:
    """A piece of a formula: kind, where it is in the text, and its parts."""

    __slots__ = ("kind", "start", "end", "op", "parts", "name", "unit", "dim", "text")

    def __init__(self, kind, start, end, op=None, parts=(), name=None, unit=None, text=None):
        self.kind, self.start, self.end = kind, start, end
        self.op, self.parts, self.name, self.unit, self.text = op, list(parts), name, unit, text
        self.dim = None


class _Parser:
    def __init__(self, text):
        self.text = text
        self.tokens = _tokens(text)
        self.pos = 0

    def peek(self, offset=0):
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else None

    def at(self, *ops):
        tok = self.peek()
        return tok is not None and tok.kind == "op" and tok.text in ops

    def take(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def expect(self, op):
        if not self.at(op):
            tok = self.peek()
            found = "'%s'" % tok.text if tok is not None else "the end"
            raise ParameterError(
                "'%s' is not a value: '%s' is missing before %s." % (self.text.strip(), op, found)
            )
        return self.take()

    def parse(self):
        if not self.tokens:
            raise ParameterError("Type a value.")
        node = self.cond()
        tok = self.peek()
        if tok is not None:
            if tok.kind == "name" and not _is_unit(tok.text):
                raise ParameterError(
                    "'%s' is not a value: something is missing before '%s' (a * or a +?)."
                    % (self.text.strip(), tok.text)
                )
            raise ParameterError(
                "'%s' is not a value: '%s' does not belong there." % (self.text.strip(), tok.text)
            )
        return node

    def cond(self):
        node = self.compare()
        if self.at("?"):
            self.take()
            yes = self.cond()
            self.expect(":")
            no = self.cond()
            node = _Node("cond", node.start, no.end, parts=[node, yes, no])
        return node

    def compare(self):
        node = self.add()
        while self.at("==", "!=", "<=", ">=", "<", ">"):
            op = self.take().text
            right = self.add()
            node = _Node("compare", node.start, right.end, op=op, parts=[node, right])
        return node

    def add(self):
        node = self.mul()
        while self.at("+", "-"):
            op = self.take().text
            right = self.mul()
            node = _Node("bin", node.start, right.end, op=op, parts=[node, right])
        return node

    def mul(self):
        node = self.unary()
        while self.at("*", "/", "%"):
            op = self.take().text
            right = self.unary()
            node = _Node("bin", node.start, right.end, op=op, parts=[node, right])
        return node

    def unary(self):
        if self.at("-", "+"):
            tok = self.take()
            child = self.unary()
            return _Node("unary", tok.start, child.end, op=tok.text, parts=[child])
        return self.power()

    def power(self):
        node = self.primary()
        if self.at("^"):
            self.take()
            right = self.unary()
            node = _Node("bin", node.start, right.end, op="^", parts=[node, right])
        return node

    def primary(self):
        tok = self.peek()
        if tok is None:
            raise ParameterError("'%s' is not a value: it ends too early." % self.text.strip())
        if tok.kind == "number":
            self.take()
            node = _Node("number", tok.start, tok.end, text=tok.text)
            unit = self.peek()
            if unit is not None and unit.kind == "name" and _unit_here(unit, self.peek(1)):
                self.take()
                node.unit = unit.text
                node.end = unit.end
                if self.at("^") and self.peek(1) is not None and self.peek(1).kind == "number":
                    self.take()
                    power = self.take()
                    node.op = power.text  # the unit's power ("mm^2")
                    node.end = power.end
            return node
        if tok.kind == "string":
            self.take()
            return self.reference(tok.start)
        if tok.kind == "name":
            self.take()
            if self.at("("):
                self.take()
                args = []
                if not self.at(")"):
                    args.append(self.cond())
                    while self.at(";", ","):
                        self.take()
                        args.append(self.cond())
                close = self.expect(")")
                return _Node("call", tok.start, close.end, name=tok.text, parts=args)
            if self.at(".") or self.at("["):
                return self.reference(tok.start, tok.text)
            return _Node("name", tok.start, tok.end, name=tok.text)
        if tok.kind == "op" and tok.text == "(":
            self.take()
            inner = self.cond()
            close = self.expect(")")
            return _Node("paren", tok.start, close.end, parts=[inner])
        raise ParameterError(
            "'%s' is not a value: '%s' does not belong there." % (self.text.strip(), tok.text)
        )

    def reference(self, start, first=None):
        """Another object's property (Sketch.Constraints.width, Pad.Length, <<Label>>.x,
        Sketch.Constraints[3]): left as it is. `Parameters.name` is the parameter."""
        end = self.tokens[self.pos - 1].end
        names = [first] if first else []
        while self.at(".", "["):
            tok = self.take()
            if tok.text == ".":
                part = self.peek()
                if part is None or part.kind not in ("name", "number"):
                    raise ParameterError("'%s' is not a value." % self.text.strip())
                self.take()
                names.append(part.text)
                end = part.end
            else:
                level = 1
                while level and self.peek() is not None:
                    part = self.take()
                    if part.text == "[":
                        level += 1
                    elif part.text == "]":
                        level -= 1
                    end = part.end
                names.append("[]")
        if first == CONTAINER and len(names) == 2 and names[1] != "[]":
            node = _Node("name", start, end, name=display_name(names[1]))
            node.op = "qualified"  # already in FreeCAD's spelling
            return node
        return _Node("ref", start, end)


def _unit_here(tok, after):
    """A name right after a number is its unit ("5 mm", '5 "'), unless it is a function."""
    if after is not None and after.kind == "op" and after.text == "(":
        return False
    return _is_unit(tok.text) or tok.text in _UNIT_SIGNS


def _dim_of_unit(unit):
    if unit in LENGTH_UNITS:
        return (1, 0)
    if unit in ANGLE_UNITS:
        return (0, 1)
    return None


NONE = (0, 0)
LENGTH = (1, 0)
ANGLE = (0, 1)
_KIND_DIM = {"length": LENGTH, "angle": ANGLE, "number": NONE}
_DIM_WORDS = {LENGTH: "a length", ANGLE: "an angle", NONE: "a number without a unit"}
_SAME_UNIT = {"min", "max", "hypot", "cath", "atan2", "mod"}  # arguments of one kind
_KEEP = {"abs", "round", "ceil", "floor", "trunc"}  # the result is of the argument's kind
_PLAIN = {"sin", "cos", "tan", "sinh", "cosh", "tanh", "exp", "log", "log10"}
_ANGLE = {"asin", "acos", "atan", "atan2"}
CONSTANTS = {"pi", "e", "PI"}


class _Reader:
    """Works out what kind of value each piece of a formula is and where a unit is missing."""

    def __init__(self, text, params, unit, strict=True, resolve=None, angle_unit="deg"):
        self.text = text
        self.params = params  # {name: "length" / "angle" / "number" / None}
        self.unit = unit  # the design's length unit
        self.angle_unit = angle_unit  # what an angle without a unit is in
        self.strict = strict
        self.resolve = resolve  # what kind another object's property is ("Pad.Length")
        self.edits = []  # (position, order, text to insert)
        self.swaps = []  # (start, end, text): a piece written another way for FreeCAD
        self.used = []  # the parameters the formula names

    # -- kinds --------------------------------------------------------------------------------
    def dim(self, node):
        node.dim = self._dim(node)
        return node.dim

    def _dim(self, node):
        kind = node.kind
        if kind == "number":
            if "," in node.text:
                end = node.start + len(node.text)
                self.swaps.append((node.start, end, node.text.replace(",", ".")))
            if node.unit is None:
                return NONE
            base = _dim_of_unit(node.unit)
            if base is None:
                return None
            power = 1
            if node.op:
                try:
                    power = int(node.op)
                except ValueError:
                    return None
            return (base[0] * power, base[1] * power)
        if kind == "name":
            return self._name(node)
        if kind == "ref":
            if self.resolve is None:
                return None
            try:
                return _KIND_DIM.get(self.resolve(self.text[node.start : node.end]))
            except Exception:
                return None
        if kind in ("paren", "unary"):
            return self.dim(node.parts[0])
        if kind == "bin":
            return self._bin(node)
        if kind == "compare":
            self._same(node.parts, "compares")
            return NONE
        if kind == "cond":
            self.dim(node.parts[0])
            return self._same(node.parts[1:], "chooses between")
        if kind == "call":
            return self._call(node)
        return None

    def _name(self, node):
        name = node.name
        if name in self.params:
            if name not in self.used:
                self.used.append(name)
            self.swaps.append((node.start, node.end, "%s.%s" % (CONTAINER, prop_name(name))))
            return _KIND_DIM.get(self.params[name])
        if node.op == "qualified":
            raise UnknownName(self._unknown(name), name)
        if name in CONSTANTS:
            if name == "PI":
                self.swaps.append((node.start, node.end, "pi"))
            return NONE
        if _is_unit(name) or name in _UNIT_SIGNS:
            return _dim_of_unit(name)  # a unit on its own: one of it
        if name in ("True", "true", "False", "false"):
            return NONE
        if not self.strict:
            return None
        raise UnknownName(self._unknown(name), name)

    def _unknown(self, name):
        close = difflib.get_close_matches(name, list(self.params), n=1, cutoff=0.6)
        if not close:
            lowered = {p.lower(): p for p in self.params}
            if name.lower() in lowered:
                close = [lowered[name.lower()]]
        hint = " Did you mean %s?" % close[0] if close else ""
        return "There is no parameter named '%s'.%s" % (name, hint)

    def _bin(self, node):
        left, right = node.parts
        op = node.op
        if op in ("+", "-"):
            return self._same(node.parts, "adds" if op == "+" else "subtracts")
        a, b = self.dim(left), self.dim(right)
        if op == "*":
            return None if a is None or b is None else (a[0] + b[0], a[1] + b[1])
        if op == "/":
            return None if a is None or b is None else (a[0] - b[0], a[1] - b[1])
        if op == "%":
            return a
        if op == "^":
            if a == NONE:
                return NONE
            power = _whole_number(right)
            if a is None or power is None:
                return None
            return (a[0] * power, a[1] * power)
        return None

    def _same(self, nodes, verb):
        """Pieces that must be of one kind (the sides of a +, the arguments of min): the
        ones without a unit take the kind of the others. Returns that kind."""
        dims = [self.dim(n) for n in nodes]
        known = [d for d in dims if d is not None and d != NONE]
        if not known:
            return None if any(d is None for d in dims) else NONE
        want = known[0]
        for d in known:
            if d != want:
                raise ParameterError(
                    "'%s' %s %s and %s: give both the same kind of unit."
                    % (
                        self.text.strip(),
                        verb,
                        _DIM_WORDS.get(want, "a value with one unit"),
                        _DIM_WORDS.get(d, "a value with another unit"),
                    )
                )
        if want in (LENGTH, ANGLE):
            for node, d in zip(nodes, dims):
                if d == NONE:
                    self.coerce(node, want)
        return want

    def _call(self, node):
        name = node.name
        args = node.parts
        if name == "ln":  # the natural logarithm, as Fusion and Inventor spell it
            self.swaps.append((node.start, node.start + 2, "log"))
            name = "log"
        if name in _SAME_UNIT:
            want = self._same(args, "compares" if name in ("min", "max") else "combines")
            return ANGLE if name == "atan2" else want
        dims = [self.dim(a) for a in args]
        if name in _KEEP:
            return dims[0] if dims else None
        if name in _PLAIN:
            return NONE
        if name in _ANGLE:
            return ANGLE
        if name == "sqrt":
            d = dims[0] if dims else None
            if d is None or d[0] % 2 or d[1] % 2:
                return None
            return (d[0] // 2, d[1] // 2)
        if name == "pow" and len(args) == 2:
            if dims[0] == NONE:
                return NONE
            power = _whole_number(args[1])
            if dims[0] is None or power is None:
                return None
            return (dims[0][0] * power, dims[0][1] * power)
        if name not in FUNCTIONS and self.strict:
            raise ParameterError(
                "'%s' is not a function Fission 180 knows (min, max, abs, round, sqrt, sin...)."
                % name
            )
        return None

    # -- giving a piece without a unit its unit ---------------------------------------------------
    def unit_text(self, dim):
        return self.unit if dim == LENGTH else self.angle_unit

    def _insert(self, pos, text):
        self.edits.append((pos, len(self.edits), text))

    def literal(self, node):
        """True when `node` can take a unit on one of its own numbers."""
        kind = node.kind
        if kind == "number":
            return node.unit is None
        if kind in ("unary", "paren"):
            return self.literal(node.parts[0])
        if kind == "bin":
            left, right = node.parts
            if node.op in ("+", "-"):
                return self.literal(left) and self.literal(right)
            if node.op == "*":
                return self.literal(left) or self.literal(right)
            if node.op == "/":
                return self.literal(left)
            return False
        if kind == "cond":
            return self.literal(node.parts[1]) and self.literal(node.parts[2])
        if kind == "call":
            return (
                node.name in (_SAME_UNIT | _KEEP) - {"atan2", "mod"}
                and bool(node.parts)
                and all(self.literal(a) for a in node.parts)
            )
        return False

    def coerce(self, node, dim):
        """Make the piece `node` (no unit so far) a length or an angle."""
        unit = self.unit_text(dim)
        node.dim = dim
        if not self.literal(node):
            self._wrap(node, unit)
            return
        kind = node.kind
        if kind == "number":
            self._insert(node.end, " " + unit)
        elif kind in ("unary", "paren"):
            self.coerce(node.parts[0], dim)
        elif kind == "bin":
            left, right = node.parts
            if node.op in ("+", "-"):
                self.coerce(left, dim)
                self.coerce(right, dim)
            elif node.op == "*":
                self.coerce(left if self.literal(left) else right, dim)
            else:
                self.coerce(left, dim)
        elif kind == "cond":
            self.coerce(node.parts[1], dim)
            self.coerce(node.parts[2], dim)
        elif kind == "call":
            for arg in node.parts:
                self.coerce(arg, dim)

    def _wrap(self, node, unit):
        """`Count` -> `Count * 1 mm`, as Fusion writes a number used as a length."""
        if node.kind in ("name", "call", "paren", "number", "ref"):
            self._insert(node.end, " * 1 " + unit)
        else:
            self._insert(node.start, "(")
            self._insert(node.end, ") * 1 " + unit)

    # -- the result -----------------------------------------------------------------------------
    def freecad(self):
        """The formula in FreeCAD's spelling, with the units added."""
        text = self.text
        # (position, 0 for an insert / 1 for a swap, order, end, new text): at one position
        # what is added after a piece comes before the swap of the piece that starts there
        marks = [(start, 1, 0, end, new) for start, end, new in self.swaps]
        marks += [(pos, 0, order, pos, new) for pos, order, new in self.edits]
        out = []
        last = 0
        for start, _swap, _order, end, new in sorted(marks, key=lambda m: m[:3]):
            if start < last:
                continue
            out.append(text[last:start])
            out.append(new)
            last = end
        out.append(text[last:])
        return _separators("".join(out))


def _separators(text):
    """Arguments separated the way FreeCAD reads them everywhere: ';'."""
    try:
        tokens = _tokens(text)
    except ParameterError:
        return text
    out = []
    last = 0
    for tok in tokens:
        if tok.kind == "op" and tok.text == ",":
            out.append(text[last : tok.start])
            out.append(";")
            last = tok.end
    out.append(text[last:])
    return "".join(out)


def _whole_number(node):
    while node.kind == "paren":
        node = node.parts[0]
    if node.kind == "number" and node.unit is None:
        try:
            value = float(node.text.replace(",", "."))
        except ValueError:
            return None
        return int(value) if value == int(value) else None
    return None


class Read:
    """What a person typed in a value box, understood (read())."""

    def __init__(self):
        self.plain = False  # one number ("25", "-2.5 mm", "1 in"): a value, no formula
        self.value = None  # the plain number's value (mm, degrees or a number)
        self.freecad = ""  # the formula in FreeCAD's spelling ("Parameters.w + 5 mm")
        self.formula = ""  # the formula as shown to the person ("w + 5 mm")
        self.kind = None  # "length" / "angle" / "number" / None (not known before computing)
        self.names = []  # the parameters it names

    def __repr__(self):
        return "Read(plain=%r, value=%r, formula=%r, kind=%r)" % (
            self.plain,
            self.value,
            self.formula,
            self.kind,
        )


_DIM_KIND = {LENGTH: "length", ANGLE: "angle", NONE: "number"}
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)\s*(.*)$", re.S)


def split_assignment(text):
    """'Thickness = -2.5 mm' -> ('Thickness', '-2.5 mm'): Fusion's way to make a parameter
    while typing a value. (None, text without a leading '=') when it is no assignment."""
    text = (text or "").strip()
    match = _ASSIGN.match(text)
    if match:
        return match.group(1), match.group(2).strip()
    while text.startswith("="):
        text = text[1:].strip()
    return None, text


def read(text, params=None, unit="mm", expect=None, strict=True, resolve=None, angle_unit="deg"):
    """Understand a value or formula typed Fusion's way.

    `params`: {parameter name: "length" / "angle" / "number"}; `unit`: the design's length
    unit; `expect`: what the box takes ("length", "angle", "number" or None for anything; a
    field's unit "mm" / "deg" / "" works too). A number without a unit is in the design's
    units where a length is meant and in degrees (`angle_unit`) where an angle is meant. Raises
    ParameterError with a sentence for the person. `strict`: an unknown name is refused
    (else it is left for FreeCAD to judge). `resolve(text)`: the kind of another object's
    property named in the formula ("Pad.Length" -> "length"), when the caller can tell."""
    expect = KIND_OF.get(expect, expect)
    text = (text or "").strip()
    while text.startswith("="):
        text = text[1:].strip()
    if not text:
        raise ParameterError("Type a value.")
    tree = _Parser(text).parse()
    reader = _Reader(text, dict(params or {}), unit, strict, resolve, angle_unit)
    dim = reader.dim(tree)
    want = _KIND_DIM.get(expect)
    if want is not None and dim is not None and dim != want:
        if dim == NONE and want in (LENGTH, ANGLE):
            reader.coerce(tree, want)
            dim = want
        else:
            raise ParameterError(
                "'%s' is %s, not %s. Type %s, for example %s."
                % (
                    text,
                    _DIM_WORDS.get(dim, "a value with another unit"),
                    KIND_WORDS[expect],
                    KIND_WORDS[expect],
                    KIND_EXAMPLES[expect],
                )
            )
    out = Read()
    out.kind = _DIM_KIND.get(dim)
    out.names = list(reader.used)
    out.freecad = reader.freecad()
    out.formula = from_freecad(out.freecad)
    number = tree
    sign = 1.0
    while number.kind == "unary":
        sign = -sign if number.op == "-" else sign
        number = number.parts[0]
    if number.kind == "number" and not number.op and dim is not None:
        typed_unit = number.unit
        if typed_unit is None and dim in (LENGTH, ANGLE):
            typed_unit = reader.unit_text(dim)
        if typed_unit is None or typed_unit in LENGTH_UNITS or typed_unit in ANGLE_UNITS:
            out.plain = True
            out.value = sign * float(number.text.replace(",", ".")) * per_unit(typed_unit)
    return out


def is_plain(text):
    """True for one number with or without a unit ('25', '-2,5 mm', '1 in', '30 deg')."""
    try:
        return read(text, strict=False).plain
    except ParameterError:
        return False
