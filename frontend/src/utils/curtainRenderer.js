import { curtainTriangles } from './curtainCloth'

const VERTEX = `
attribute vec3 positionAndLight;
attribute vec2 texturePosition;
uniform float aspect;
varying vec2 uv;
varying float brightness;

void main() {
  uv = texturePosition;
  brightness = positionAndLight.z;
  gl_Position = vec4(positionAndLight.x * 2.0 - 1.0,
    1.0 - positionAndLight.y / aspect * 2.0, 0.0, 1.0);
}
`

const FRAGMENT = `
precision mediump float;
uniform sampler2D fabric;
uniform float side;
varying vec2 uv;
varying float brightness;

void main() {
  float fiber = fract(sin(floor(uv.y * 520.0) * 17.83 + side) * 876.6);
  float tornEdge = 0.009 + sin(uv.y * 73.0 + side) * 0.004
    + sin(uv.y * 181.0) * 0.002;
  float distanceToEdge = 1.0 - uv.x - tornEdge;
  if (distanceToEdge < -0.004 * step(0.91, fiber)) discard;

  float x = mix(uv.x * 0.5, 1.0 - uv.x * 0.5, side);
  vec3 velvet = texture2D(fabric, vec2(x, uv.y)).rgb;
  gl_FragColor = vec4(velvet * brightness, 1.0);
}
`

function compile(gl, type, source) {
  const shader = gl.createShader(type)
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader
  gl.deleteShader(shader)
  return null
}

export function createCurtainRenderer(canvas) {
  const gl = canvas.getContext('webgl', { alpha: true, antialias: true })
  if (!gl) return null

  const vertexShader = compile(gl, gl.VERTEX_SHADER, VERTEX)
  const fragmentShader = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT)
  if (!vertexShader || !fragmentShader) {
    if (vertexShader) gl.deleteShader(vertexShader)
    if (fragmentShader) gl.deleteShader(fragmentShader)
    return null
  }

  const program = gl.createProgram()
  gl.attachShader(program, vertexShader)
  gl.attachShader(program, fragmentShader)
  gl.linkProgram(program)
  gl.deleteShader(vertexShader)
  gl.deleteShader(fragmentShader)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program)
    return null
  }

  gl.useProgram(program)
  const vertexBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer)
  const positions = gl.getAttribLocation(program, 'positionAndLight')
  const texturePositions = gl.getAttribLocation(program, 'texturePosition')
  gl.enableVertexAttribArray(positions)
  gl.enableVertexAttribArray(texturePositions)
  gl.vertexAttribPointer(positions, 3, gl.FLOAT, false, 20, 0)
  gl.vertexAttribPointer(texturePositions, 2, gl.FLOAT, false, 20, 12)

  const indexBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer)
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, curtainTriangles, gl.STATIC_DRAW)
  const texture = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, texture)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
  gl.uniform1i(gl.getUniformLocation(program, 'fabric'), 0)
  const aspectUniform = gl.getUniformLocation(program, 'aspect')
  const sideUniform = gl.getUniformLocation(program, 'side')

  return {
    setTexture(image) {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
    },
    draw(aspect, panels, closed) {
      gl.viewport(0, 0, canvas.width, canvas.height)
      gl.clearColor(.075, .02, .03, closed ? 1 : 0)
      gl.clear(gl.COLOR_BUFFER_BIT)
      gl.uniform1f(aspectUniform, aspect)
      panels.forEach((panel, side) => {
        gl.uniform1f(sideUniform, side)
        gl.bufferData(gl.ARRAY_BUFFER, panel.geometry(), gl.DYNAMIC_DRAW)
        gl.drawElements(gl.TRIANGLES, curtainTriangles.length, gl.UNSIGNED_SHORT, 0)
      })
    },
    dispose() {
      gl.deleteTexture(texture)
      gl.deleteBuffer(vertexBuffer)
      gl.deleteBuffer(indexBuffer)
      gl.deleteProgram(program)
    },
  }
}
