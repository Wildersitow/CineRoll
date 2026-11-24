import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HeroBanner from './HeroBanner'
import { getMedia } from '../services/api'

vi.mock('../services/api', () => ({ getMedia: vi.fn() }))

const pelicula = (id, titulo) => ({ id, titulo, tipo: 'pelicula', poster_url: `https://img/${id}.jpg`, generos: [], sinopsis: `Sinopsis de ${titulo}` })

function renderizar() {
  return render(<MemoryRouter><HeroBanner ciudad="valledupar" etiqueta="En cartelera hoy" detailSearch="" /></MemoryRouter>)
}

describe('HeroBanner', () => {
  beforeEach(() => getMedia.mockReset())

  it('muestra las películas con funciones hoy y permite pasar a la siguiente', async () => {
    getMedia.mockResolvedValueOnce({ results: [pelicula(1, 'Dune'), pelicula(2, 'Coco')] })
    renderizar()
    expect(await screen.findByRole('heading', { name: 'Dune' })).toBeInTheDocument()
    expect(getMedia).toHaveBeenCalledWith(expect.objectContaining({ ciudad: 'valledupar', fecha: 'hoy' }), expect.anything())
    fireEvent.click(screen.getByRole('button', { name: 'Película siguiente' }))
    expect(await screen.findByRole('heading', { name: 'Coco' })).toBeInTheDocument()
  })

  it('usa los títulos en cartelera si hoy no hay funciones', async () => {
    getMedia
      .mockResolvedValueOnce({ results: [] })
      .mockResolvedValueOnce({ results: [pelicula(3, 'Verity')] })
    renderizar()
    expect(await screen.findByRole('heading', { name: 'Verity' })).toBeInTheDocument()
    expect(getMedia).toHaveBeenLastCalledWith(expect.objectContaining({ estado: 'en_cartelera' }), expect.anything())
    expect(screen.queryByRole('button', { name: 'Película siguiente' })).not.toBeInTheDocument()
  })

  it('no muestra nada si no hay películas', async () => {
    getMedia.mockResolvedValue({ results: [] })
    const { container } = renderizar()
    await vi.waitFor(() => expect(container.querySelector('.cinema-banner')).toBeNull())
  })
})
