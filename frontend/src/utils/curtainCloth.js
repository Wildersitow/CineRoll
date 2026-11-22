const COLUMNS = 24
const ROWS = 18
const STRIDE = COLUMNS + 1
const POINT_COUNT = STRIDE * (ROWS + 1)
export const CLOTH_STEP = 1 / 120

export const curtainTriangles = new Uint16Array(COLUMNS * ROWS * 6)
for (let row = 0; row < ROWS; row += 1) {
  for (let col = 0; col < COLUMNS; col += 1) {
    const point = row * STRIDE + col
    curtainTriangles.set(
      [point, point + 1, point + STRIDE, point + 1, point + STRIDE + 1, point + STRIDE],
      (row * COLUMNS + col) * 6,
    )
  }
}

export function createCurtainCloth(aspect, side) {
  const points = new Float32Array(POINT_COUNT * 3)
  const previous = new Float32Array(points.length)
  const vertices = new Float32Array(POINT_COUNT * 5)
  const pleats = new Float32Array(STRIDE)
  const springs = []

  for (let col = 0; col <= COLUMNS; col += 1) {
    pleats[col] = Math.sin(col / COLUMNS * Math.PI * 9)
  }

  function railX(col, progress) {
    const span = .506 - progress * .37
    const edge = .006 + progress * .64
    return .5 + side * (edge + (1 - col / COLUMNS) * span)
  }

  for (let row = 0; row <= ROWS; row += 1) {
    for (let col = 0; col <= COLUMNS; col += 1) {
      const index = row * STRIDE + col
      points.set([
        railX(col, 0),
        aspect * (row / ROWS * 1.035 - .014),
        pleats[col] * .004,
      ], index * 3)
      vertices.set([col / COLUMNS, row / ROWS], index * 5 + 3)
    }
  }
  previous.set(points)

  function connect(first, second, stiffness) {
    const a = first * 3
    const b = second * 3
    springs.push([
      a, b, Math.hypot(points[b] - points[a], points[b + 1] - points[a + 1], points[b + 2] - points[a + 2]),
      stiffness, a >= STRIDE * 3 ? .5 : 0,
    ])
  }

  for (let row = 0; row <= ROWS; row += 1) {
    for (let col = 0; col <= COLUMNS; col += 1) {
      const point = row * STRIDE + col
      if (col < COLUMNS && row > 0) connect(point, point + 1, .86)
      if (row === ROWS) continue
      connect(point, point + STRIDE, .93)
      if (col < COLUMNS) connect(point, point + STRIDE + 1, .48)
      if (col > 0) connect(point, point + STRIDE - 1, .48)
    }
  }

  function step(progress) {
    const dtSquared = CLOTH_STEP ** 2
    const folds = .004 + progress * .025
    for (let col = 0; col <= COLUMNS; col += 1) {
      points[col * 3] = railX(col, progress)
      points[col * 3 + 2] = folds * pleats[col]
    }

    // Verlet integra la inercia. Las restricciones mantienen la tensión entre puntos vecinos.
    for (let index = STRIDE; index < POINT_COUNT; index += 1) {
      const offset = index * 3
      const col = index % STRIDE
      const pullForce = (railX(col, progress) - points[offset]) * 23
      const foldForce = (folds * pleats[col] - points[offset + 2]) * 20
      for (let axis = 0; axis < 3; axis += 1) {
        const coordinate = offset + axis
        const current = points[coordinate]
        const force = axis === 0 ? pullForce : axis === 1 ? .7 : foldForce
        points[coordinate] += (current - previous[coordinate]) * .976 + force * dtSquared
        previous[coordinate] = current
      }
    }

    for (let pass = 0; pass < 5; pass += 1) {
      for (const [a, b, rest, stiffness, weight] of springs) {
        const dx = points[b] - points[a]
        const dy = points[b + 1] - points[a + 1]
        const dz = points[b + 2] - points[a + 2]
        const length = Math.hypot(dx, dy, dz)
        const correction = (length - rest) / Math.max(length, .00001) * stiffness
        const pullA = correction * weight
        const pullB = correction - pullA
        points[a] += dx * pullA
        points[a + 1] += dy * pullA
        points[a + 2] += dz * pullA
        points[b] -= dx * pullB
        points[b + 1] -= dy * pullB
        points[b + 2] -= dz * pullB
      }
    }
  }

  function geometry() {
    for (let index = 0; index < POINT_COUNT; index += 1) {
      const point = index * 3
      const vertex = index * 5
      const col = index % STRIDE
      const left = col === 0 ? point : point - 3
      const right = col === COLUMNS ? point : point + 3
      const dx = points[right] - points[left]
      const dz = points[right + 2] - points[left + 2]
      vertices[vertex] = points[point]
      vertices[vertex + 1] = points[point + 1]
      vertices[vertex + 2] = .91 + side * dz / Math.max(Math.hypot(dx, dz), .00001) * .2
    }
    return vertices
  }

  function isOffscreen() {
    const edge = side === -1 ? 0 : 1
    for (let index = 0; index < points.length; index += 3) {
      if (side * (points[index] - edge) <= 0) return false
    }
    return true
  }

  return { step, geometry, isOffscreen }
}
