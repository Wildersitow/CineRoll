import { describe, expect, it } from 'vitest'
import { puntuacionParaMostrar, puntuacionParaGuardar } from './puntuacion'

describe('conversión de puntuaciones', () => {
  it('muestra la puntuación guardada en escala de 5 estrellas con medias', () => {
    expect(puntuacionParaMostrar(7, 5)).toBe(3.5)
    expect(puntuacionParaMostrar(1, 5)).toBe(0.5)
    expect(puntuacionParaMostrar(10, 5)).toBe(5)
  })

  it('conserva la puntuación en escala de 10', () => {
    expect(puntuacionParaMostrar(7, 10)).toBe(7)
  })

  it('convierte estrellas a una puntuación entera al guardar', () => {
    expect(puntuacionParaGuardar(3.5, 5)).toBe(7)
    expect(puntuacionParaGuardar(0.5, 5)).toBe(1)
    expect(puntuacionParaGuardar(5, 5)).toBe(10)
  })

  it('conserva la puntuación en escala de 10 al guardar', () => {
    expect(puntuacionParaGuardar(7, 10)).toBe(7)
  })

  it('rechaza escalas y puntuaciones fuera de los rangos admitidos', () => {
    expect(() => puntuacionParaMostrar(0, 5)).toThrow(RangeError)
    expect(() => puntuacionParaMostrar(11, 10)).toThrow(RangeError)
    expect(() => puntuacionParaMostrar(7, 7)).toThrow(RangeError)
    expect(() => puntuacionParaGuardar(3.2, 5)).toThrow(RangeError)
    expect(() => puntuacionParaGuardar(0, 5)).toThrow(RangeError)
    expect(() => puntuacionParaGuardar(10.5, 10)).toThrow(RangeError)
  })
})
