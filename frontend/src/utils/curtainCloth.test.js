import { expect, test } from 'vitest'
import { createCurtainCloth } from './curtainCloth'

test.each([.65, 2.15])('el telón tarda en arrastrar el bajo y sale de pantalla (%s)', (aspect) => {
  const left = createCurtainCloth(aspect, -1)
  const right = createCurtainCloth(aspect, 1)

  for (let step = 0; step <= 70; step += 1) {
    left.step(step / 140)
    right.step(step / 140)
  }

  const cloth = left.geometry()
  const top = 24 * 5
  const bottom = cloth.length - 5
  expect(cloth[bottom] - cloth[top]).toBeGreaterThan(.04)
  expect(left.isOffscreen()).toBe(false)
  expect(right.isOffscreen()).toBe(false)

  for (let step = 71; step <= 270; step += 1) {
    left.step(Math.min(step / 140, 1))
    right.step(Math.min(step / 140, 1))
  }

  expect(left.geometry().every(Number.isFinite)).toBe(true)
  expect(right.geometry().every(Number.isFinite)).toBe(true)
  expect(left.isOffscreen()).toBe(true)
  expect(right.isOffscreen()).toBe(true)
})
