import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CinesView from './CinesView'
import { getCines, getFuncionesDeCine, getMedia } from '../services/api'

vi.mock('../services/api', () => ({ getCines: vi.fn(), getFuncionesDeCine: vi.fn(), getMedia: vi.fn() }))

const CINE = { id: 7, nombre: 'Cinépolis Guatapurí', ciudad: 'Valledupar', direccion: 'Diagonal 10 #6N-15', sitio_web: '' }

function renderizar(ruta = '/cines') {
  return render(<MemoryRouter initialEntries={[ruta]}><CinesView /></MemoryRouter>)
}

describe('CinesView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    getCines.mockResolvedValue({ results: [CINE], next: null })
  })

  it('muestra un panel por cine con el botón para abrir Google Maps', async () => {
    renderizar()
    expect(await screen.findByRole('heading', { name: 'Cinépolis Guatapurí' })).toBeInTheDocument()
    expect(getCines).toHaveBeenCalledWith({ ciudad: 'valledupar', page: 1 }, expect.anything())
    const mapa = screen.getByRole('link', { name: 'Abrir Cinépolis Guatapurí en Google Maps' })
    expect(mapa.getAttribute('href')).toContain('https://www.google.com/maps/search/?api=1&query=')
    expect(mapa.getAttribute('href')).toContain(encodeURIComponent('Diagonal 10 #6N-15'))
    expect(screen.getByRole('button', { name: /Ver cartelera y detalles/ })).toHaveAttribute('aria-expanded', 'false')
    expect(getMedia).not.toHaveBeenCalled()
  })

  it('al desplegar el cine carga sus películas y horarios del día', async () => {
    getMedia.mockResolvedValue({ results: [{ id: 3, titulo: 'Coco', poster_url: '', generos: [] }] })
    getFuncionesDeCine.mockResolvedValue({ resultados: [
      { id: 1, media_id: 3, fecha_hora: '2026-11-23T20:30:00-05:00', formato: '2D', sala: 'Sala 1' },
    ] })
    renderizar()
    fireEvent.click(await screen.findByRole('button', { name: /Ver cartelera y detalles/ }))
    expect(await screen.findByRole('link', { name: 'Coco' })).toBeInTheDocument()
    expect(getMedia).toHaveBeenCalledWith(expect.objectContaining({ cine: 7, fecha: 'hoy' }), expect.anything())
    expect(getFuncionesDeCine).toHaveBeenCalledWith(7, { fecha: 'hoy' }, expect.anything())
    expect(screen.getByText('2D · Sala 1')).toBeInTheDocument()
    expect(screen.getByText('Aún no disponibles')).toBeInTheDocument()
  })

  it('abre directamente el cine indicado en la URL', async () => {
    getMedia.mockResolvedValue({ results: [] })
    getFuncionesDeCine.mockResolvedValue({ resultados: [] })
    renderizar('/cines?cine=7')
    expect(await screen.findByRole('button', { name: /Ocultar cartelera y detalles/ })).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByText('No hay funciones publicadas para este día.')).toBeInTheDocument()
  })
})
