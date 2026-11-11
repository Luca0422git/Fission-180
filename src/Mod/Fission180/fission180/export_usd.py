# SPDX-License-Identifier: LGPL-2.1-or-later
"""USDZ export (Fusion's File > Export > USDZ, for AR: the book's Saturn V "view it on your
desk" step). Pure Python: no FreeCAD, no Qt, no USD library.

A USDZ file is a zip archive that is not compressed, whose first file is a USD layer and
whose files each start at a multiple of 64 bytes (Pixar's "Usdz File Format Specification").
Here the layer is text (USDA): one Xform for the design, one Mesh per body (or per colour of
a body with painted faces) and a UsdPreviewSurface material per colour. AR viewers (Apple's
AR Quick Look, Reality Composer, usdview, Blender) read text layers inside USDZ.

The numbers are written the way AR viewers expect them, whatever the design's unit:
**metres, Y up** (the design's Z becomes up: (x, y, z) mm -> (x, z, -y) / 1000 m), so the
part stands on the table at its real size.

    write_usdz(path, parts, name)   parts: [{"name", "points", "triangles", "color",
                                             "opacity", "metallic", "roughness"}]
    read_usdz(path)                 what a file holds (the tests read back what was written;
                                    it is also what the Export report shows)
"""

import os
import re
import struct
import zlib

ALIGN = 64
MM_TO_M = 0.001
LAYER_NAME = "design.usda"
_PAD_ID = 0x1986  # the extra-field id Pixar's own packer pads with


class UsdError(ValueError):
    pass


def prim_name(text, used=None, fallback="Body"):
    """A USD prim name from a body's name: letters, digits and "_" only, not starting with
    a digit, unique among `used` (a set, added to)."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", str(text or "")).strip("_") or fallback
    if name[0].isdigit():
        name = "_" + name
    if used is not None:
        base, n = name, 1
        while name in used:
            n += 1
            name = "%s_%d" % (base, n)
        used.add(name)
    return name


def to_ar(point):
    """A point of the design (mm, Z up) as AR viewers want it (metres, Y up)."""
    x, y, z = point
    return (x * MM_TO_M, z * MM_TO_M, -y * MM_TO_M)


def _f(value):
    text = "%.6f" % value
    text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _tuple(values):
    return "(%s)" % ", ".join(_f(v) for v in values)


def _color_key(part):
    c = tuple(round(float(v), 4) for v in (part.get("color") or (0.8, 0.8, 0.8))[:3])
    return (
        c,
        round(float(part.get("opacity", 1.0)), 4),
        round(float(part.get("metallic", 0.0)), 4),
        round(float(part.get("roughness", 0.5)), 4),
    )


def usda_text(parts, name="Design"):
    """The USD layer (text) of the parts. Raises UsdError when there is nothing to write."""
    parts = [p for p in parts if p.get("points") and p.get("triangles")]
    if not parts:
        raise UsdError("There is nothing to export: no body has a surface yet.")
    root = prim_name(name, fallback="Design")
    used = {"Looks"}
    looks = {}  # colour key -> material name
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "%s"' % root,
        "    metersPerUnit = 1",
        '    upAxis = "Y"',
        '    doc = "Written by Fission 180"',
        ")",
        "",
        'def Xform "%s" (' % root,
        '    kind = "component"',
        ")",
        "{",
    ]
    for part in parts:
        key = _color_key(part)
        if key not in looks:
            looks[key] = "Look_%d" % (len(looks) + 1)
        points = [to_ar(p) for p in part["points"]]
        count = len(points)
        for tri in part["triangles"]:
            if len(tri) != 3 or min(tri) < 0 or max(tri) >= count:
                raise UsdError("%s: a triangle names a point that is not there." % part["name"])
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        prim = prim_name(part.get("name"), used)
        lines += [
            '    def Mesh "%s" (' % prim,
            '        prepend apiSchemas = ["MaterialBindingAPI"]',
            "    )",
            "    {",
            '        custom string fission180:name = "%s"'
            % str(part.get("name") or prim).replace("\\", "\\\\").replace('"', '\\"'),
            "        uniform bool doubleSided = 1",
            "        float3[] extent = [%s, %s]" % (_tuple(lo), _tuple(hi)),
            "        int[] faceVertexCounts = [%s]" % ", ".join("3" for _ in part["triangles"]),
            "        int[] faceVertexIndices = [%s]"
            % ", ".join("%d, %d, %d" % tuple(t) for t in part["triangles"]),
            "        point3f[] points = [%s]" % ", ".join(_tuple(p) for p in points),
            "        color3f[] primvars:displayColor = [%s] (" % _tuple(key[0]),
            '            interpolation = "constant"',
            "        )",
            '        uniform token subdivisionScheme = "none"',
            "        rel material:binding = </%s/Looks/%s>" % (root, looks[key]),
            "    }",
            "",
        ]
    lines += ['    def Scope "Looks"', "    {"]
    for key, look in looks.items():
        color, opacity, metallic, roughness = key
        path = "/%s/Looks/%s" % (root, look)
        lines += [
            '        def Material "%s"' % look,
            "        {",
            "            token outputs:surface.connect = <%s/Surface.outputs:surface>" % path,
            "",
            '            def Shader "Surface"',
            "            {",
            '                uniform token info:id = "UsdPreviewSurface"',
            "                color3f inputs:diffuseColor = %s" % _tuple(color),
            "                float inputs:metallic = %s" % _f(metallic),
            "                float inputs:opacity = %s" % _f(opacity),
            "                float inputs:roughness = %s" % _f(roughness),
            "                token outputs:surface",
            "            }",
            "        }",
            "",
        ]
    lines += ["    }", "}", ""]
    return "\n".join(lines)


def pack_usdz(files):
    """The bytes of a USDZ archive holding `files` ([(name, bytes)], the USD layer first):
    stored without compression, each file's data starting at a multiple of 64 bytes."""
    if not files:
        raise UsdError("A USDZ file needs its USD layer.")
    out = bytearray()
    central = []
    for name, data in files:
        raw_name = name.encode("utf-8")
        offset = len(out)
        start = offset + 30 + len(raw_name)
        pad = (ALIGN - (start + 4) % ALIGN) % ALIGN  # (+4: the extra field's own header)
        extra = struct.pack("<HH", _PAD_ID, pad) + b"\0" * pad
        crc = zlib.crc32(data) & 0xFFFFFFFF
        header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # local file header
            10,  # version needed
            0x0800,  # names are UTF-8
            0,  # stored
            0,  # time
            0x21,  # date: 1980-01-01
            crc,
            len(data),
            len(data),
            len(raw_name),
            len(extra),
        )
        out += header + raw_name + extra + data
        central.append((raw_name, crc, len(data), offset))
    directory_at = len(out)
    for raw_name, crc, size, offset in central:
        out += struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,  # central directory header
            10,  # made by
            10,  # needed
            0x0800,
            0,
            0,
            0x21,
            crc,
            size,
            size,
            len(raw_name),
            0,  # no extra here
            0,  # no comment
            0,  # disk
            0,  # internal attributes
            0,  # external attributes
            offset,
        )
        out += raw_name
    size = len(out) - directory_at
    out += struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, len(central), len(central), size, directory_at, 0
    )
    return bytes(out)


def write_usdz(path, parts, name="Design"):
    """Write the parts as a USDZ file (whole or not at all). Returns the number of
    triangles written."""
    text = usda_text(parts, name)
    data = pack_usdz([(LAYER_NAME, text.encode("utf-8"))])
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    partial = path + ".part"
    with open(partial, "wb") as handle:
        handle.write(data)
    os.replace(partial, path)
    return sum(len(p["triangles"]) for p in parts if p.get("points") and p.get("triangles"))


# -- reading back ---------------------------------------------------------------------------
def _entries(data):
    """[(name, method, data offset, size)] of a zip archive's local files, in order."""
    found, pos = [], 0
    while pos + 30 <= len(data):
        if struct.unpack_from("<I", data, pos)[0] != 0x04034B50:
            break
        _v, _flags, method, _t, _d, _crc, csize, _usize, nlen, elen = struct.unpack_from(
            "<HHHHHIIIHH", data, pos + 4
        )
        name = data[pos + 30 : pos + 30 + nlen].decode("utf-8", "replace")
        start = pos + 30 + nlen + elen
        found.append((name, method, start, csize))
        pos = start + csize
    return found


_MESH = re.compile(r'def Mesh "([^"]+)"(.*?)\n    \}', re.S)


def _numbers(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", text)]


def read_usdz(path):
    """What a USDZ file written here holds: {"files", "stored", "aligned", "layer",
    "meters_per_unit", "up", "meshes": [{"prim", "name", "points", "triangles", "extent",
    "color", "look"}], "looks": {name: {"color", "opacity"}}}. Raises UsdError on a file that
    is no USDZ."""
    with open(path, "rb") as handle:
        data = handle.read()
    entries = _entries(data)
    if not entries:
        raise UsdError("%s is not a USDZ file (no zip archive)." % os.path.basename(path))
    first = entries[0]
    if not first[0].lower().endswith((".usda", ".usdc", ".usd")):
        raise UsdError("The first file of a USDZ must be its USD layer, not %s." % first[0])
    text = data[first[2] : first[2] + first[3]].decode("utf-8", "replace")
    result = {
        "files": [e[0] for e in entries],
        "stored": all(e[1] == 0 for e in entries),
        "aligned": all(e[2] % ALIGN == 0 for e in entries),
        "layer": text,
        "meters_per_unit": None,
        "up": None,
        "meshes": [],
        "looks": {},
    }
    found = re.search(r"metersPerUnit\s*=\s*([\d.eE+-]+)", text)
    if found:
        result["meters_per_unit"] = float(found.group(1))
    found = re.search(r'upAxis\s*=\s*"(\w)"', text)
    if found:
        result["up"] = found.group(1)
    for look, body in re.findall(r'def Material "([^"]+)"(.*?)\n        \}', text, re.S):
        color = re.search(r"inputs:diffuseColor = \(([^)]*)\)", body)
        opacity = re.search(r"inputs:opacity = ([\d.eE+-]+)", body)
        result["looks"][look] = {
            "color": tuple(_numbers(color.group(1))) if color else None,
            "opacity": float(opacity.group(1)) if opacity else None,
        }
    for prim, body in _MESH.findall(text):
        points = re.search(r"point3f\[\] points = \[(.*?)\]\n", body, re.S)
        indices = re.search(r"faceVertexIndices = \[(.*?)\]", body, re.S)
        extent = re.search(r"extent = \[(.*?)\]\n", body, re.S)
        color = re.search(r"primvars:displayColor = \[\(([^)]*)\)\]", body)
        look = re.search(r"material:binding = <[^>]*/([^/>]+)>", body)
        label = re.search(r'fission180:name = "((?:[^"\\]|\\.)*)"', body)
        values = _numbers(points.group(1)) if points else []
        ext = _numbers(extent.group(1)) if extent else []
        result["meshes"].append(
            {
                "prim": prim,
                "name": (
                    label.group(1).replace('\\"', '"').replace("\\\\", "\\") if label else prim
                ),
                "points": len(values) // 3,
                "triangles": len(_numbers(indices.group(1))) // 3 if indices else 0,
                "extent": (tuple(ext[:3]), tuple(ext[3:6])) if len(ext) >= 6 else None,
                "color": tuple(_numbers(color.group(1))) if color else None,
                "look": look.group(1) if look else None,
            }
        )
    return result
