# SPDX-License-Identifier: LGPL-2.1-or-later
"""The rim light of Hologram bodies (docs/fission180/neon-lights-design.md 6.6 and 6.13; plan
task B6): a small GLSL program, through Coin's SoShaderProgram, that brightens the faces of a
body where they are seen edge-on, in the look's outline colour.

Graphics drivers differ, so the shader is only used after self_test() has compiled it, drawn
one frame off screen with it and read the frame back: the rim must be brighter with it than
without it. On any failure Hologram uses the flat see-through material (neon_view) and the
reason is logged. The result is kept for the session.

The shader keeps FreeCAD's own colours working: the face colour (and its see-through) arrives
in gl_Color, and so do the hover and selection colours FreeCAD's face set uses while it draws
the highlighted faces (measured: they never reach gl_FrontMaterial's diffuse or emission).
"""

from . import log, warn

NODE = "Fission180NeonRim"
COLOUR = "rimColor"
STRENGTH = "rimStrength"

VERTEX = """
varying vec3 fNormal;
varying vec3 fView;
void main()
{
    vec4 eye = gl_ModelViewMatrix * gl_Vertex;
    fNormal = gl_NormalMatrix * gl_Normal;
    // An orthographic camera (FreeCAD's default) looks along -z everywhere.
    fView = gl_ProjectionMatrix[3][3] > 0.5 ? vec3(0.0, 0.0, 1.0) : -eye.xyz;
    gl_FrontColor = gl_Color;
    gl_BackColor = gl_Color;
    gl_ClipVertex = eye;
    gl_Position = ftransform();
}
"""

FRAGMENT = """
uniform vec3 rimColor;
uniform float rimStrength;
varying vec3 fNormal;
varying vec3 fView;
void main()
{
    vec3 n = normalize(fNormal);
    vec3 v = normalize(fView);
    float facing = abs(dot(n, v));
    float rim = pow(1.0 - facing, 3.0) * rimStrength;
    vec4 diffuse = gl_Color;
    vec3 base = diffuse.rgb * (0.45 + 0.55 * facing) + gl_FrontMaterial.emission.rgb;
    gl_FragColor = vec4(base + rimColor * rim, clamp(diffuse.a + 0.5 * rim, 0.0, 1.0));
}
"""

_state = {"result": None}


def _coin():
    from pivy import coin

    return coin


def program(colour, strength=1.0):
    """A new SoShaderProgram named NODE: rim light in `colour` (r, g, b in 0..1)."""
    coin = _coin()
    node = coin.SoShaderProgram()
    node.setName(coin.SbName(NODE))
    vertex = coin.SoVertexShader()
    vertex.sourceType = coin.SoShaderObject.GLSL_PROGRAM
    vertex.sourceProgram = VERTEX
    fragment = coin.SoFragmentShader()
    fragment.sourceType = coin.SoShaderObject.GLSL_PROGRAM
    fragment.sourceProgram = FRAGMENT
    rim = coin.SoShaderParameter3f()
    rim.name = COLOUR
    rim.value.setValue(*colour)
    power = coin.SoShaderParameter1f()
    power.name = STRENGTH
    power.value = float(strength)
    fragment.parameter.set1Value(0, rim)
    fragment.parameter.set1Value(1, power)
    node.shaderObject.set1Value(0, vertex)
    node.shaderObject.set1Value(1, fragment)
    return node


def set_colour(node, colour, strength=None):
    """A program made by program() in a new colour (and strength)."""
    fragment = node.shaderObject[1]
    for i in range(fragment.parameter.getNum()):
        parameter = fragment.parameter[i]
        name = parameter.name.getValue().getString()
        if name == COLOUR:
            parameter.value.setValue(*colour)
        elif name == STRENGTH and strength is not None:
            parameter.value = float(strength)


# -- the self-test --------------------------------------------------------------------------
_SIZE = 64


def _scene(with_shader):
    """A dark sphere seen from the front, with or without the rim light (pure red)."""
    coin = _coin()
    root = coin.SoSeparator()
    camera = coin.SoOrthographicCamera()
    camera.position.setValue(0, 0, 5)
    camera.height = 2.4
    camera.nearDistance = 1
    camera.farDistance = 10
    root.addChild(camera)
    root.addChild(coin.SoDirectionalLight())
    material = coin.SoMaterial()
    material.diffuseColor.setValue(0.1, 0.1, 0.1)
    root.addChild(material)
    if with_shader:
        root.addChild(program((1.0, 0.0, 0.0), 1.0))
    root.addChild(coin.SoSphere())
    return root


def _render(root):
    """[(r, g, b)] of row _SIZE / 2, or None when nothing could be drawn. Drawn in a Qt
    off-screen OpenGL context and frame buffer, like FreeCAD's own saveImage (Coin's own
    off-screen renderer finds no context under X servers without GLX pixmaps)."""
    coin = _coin()
    from PySide6 import QtGui, QtOpenGL

    surface = QtGui.QOffscreenSurface()
    surface.create()
    context = QtGui.QOpenGLContext()
    if not context.create():
        return None
    previous = QtGui.QOpenGLContext.currentContext()
    previous_surface = previous.surface() if previous is not None else None
    if not context.makeCurrent(surface):
        return None
    try:
        fmt = QtOpenGL.QOpenGLFramebufferObjectFormat()
        fmt.setAttachment(QtOpenGL.QOpenGLFramebufferObject.Depth)
        fbo = QtOpenGL.QOpenGLFramebufferObject(_SIZE, _SIZE, fmt)
        if not fbo.isValid() or not fbo.bind():
            return None
        functions = context.functions()
        functions.glClearColor(0.0, 0.0, 0.0, 1.0)
        functions.glClear(0x4000 | 0x100)  # colour and depth
        action = coin.SoGLRenderAction(coin.SbViewportRegion(_SIZE, _SIZE))
        action.setCacheContext(coin.SoGLCacheContextElement.getUniqueCacheContext())
        action.apply(root)
        functions.glFinish()
        image = fbo.toImage()
        fbo.release()
    finally:
        context.doneCurrent()
        if previous is not None and previous_surface is not None:
            previous.makeCurrent(previous_surface)
    if image.isNull() or image.width() < _SIZE:
        return None
    y = _SIZE // 2
    row = []
    for x in range(_SIZE):
        c = QtGui.QColor(image.pixel(x, y))
        row.append((c.red(), c.green(), c.blue()))
    return row


def _rim_red(row):
    """The reddest pixel near the sphere's left and right edges, and the centre's red."""
    xs = [x for x, c in enumerate(row) if max(c) > 0]
    if len(xs) < 8:
        return None
    left, right = xs[0], xs[-1]
    edge = max(row[x][0] for x in list(range(left, left + 4)) + list(range(right - 3, right + 1)))
    return edge, row[_SIZE // 2][0]


def check():
    """(ok, reason) from drawing the test scene with and without the shader; not cached."""
    try:
        plain = _render(_scene(False))
        lit = _render(_scene(True))
    except Exception as exc:
        return False, "the test picture could not be drawn: %s" % exc
    if plain is None or lit is None:
        return False, "the test picture could not be drawn off screen"
    plain_rim, lit_rim = _rim_red(plain), _rim_red(lit)
    if plain_rim is None or lit_rim is None:
        return False, "the test sphere was not drawn"
    edge, centre = lit_rim
    if edge < plain_rim[0] + 40:
        return False, "the shader had no effect (did it compile?): rim %d vs %d" % (edge, plain_rim[0])
    if centre > edge:
        return False, "the shader drew the wrong picture: centre %d, rim %d" % (centre, edge)
    return True, "rim light drawn (rim red %d, without it %d)" % (edge, plain_rim[0])


def self_test():
    """(ok, reason): whether the rim light works on this computer. Run once per session; the
    environment variable FISSION180_NEON_NO_SHADER=1 makes it fail (the flat fallback)."""
    if _state["result"] is None:
        import os

        if os.environ.get("FISSION180_NEON_NO_SHADER") == "1":
            result = (False, "switched off by FISSION180_NEON_NO_SHADER")
        else:
            try:
                result = check()
            except Exception as exc:
                result = (False, "self-test failed: %s" % exc)
        _state["result"] = result
        if result[0]:
            log("Neon Lights: rim light shader OK (%s)" % result[1])
        else:
            log("Neon Lights: rim light shader not used, Hologram is flat: %s" % result[1])
    return _state["result"]


def reset():
    """Forget the self-test's result (tests)."""
    _state["result"] = None
