import { describe, expect, it } from 'vitest'
import { activePath } from './navegacion'

const rutas = ['/', '/catalogo', '/cines', '/catalogo?estado=proximo_estreno', '/usuarios/pepe', '/mensajes', '/perfil']

describe('activePath', () => {
  it('Estrenos no marca también Catálogo', () => {
    expect(activePath(rutas, '/catalogo', '?estado=proximo_estreno')).toBe('/catalogo?estado=proximo_estreno')
    expect(activePath(rutas, '/catalogo', '?tipo=serie')).toBe('/catalogo')
  })

  it('marca la sección también en sus subrutas', () => {
    expect(activePath(rutas, '/mensajes/sergio', '')).toBe('/mensajes')
    expect(activePath(rutas, '/usuarios/pepe', '?tab=listas')).toBe('/usuarios/pepe')
    expect(activePath(rutas, '/', '')).toBe('/')
  })

  it('no confunde rutas con el mismo prefijo ni marca nada fuera del menú', () => {
    expect(activePath(rutas, '/usuarios/pepetheboss', '')).toBeNull()
    expect(activePath(rutas, '/media/4', '')).toBeNull()
  })
})
