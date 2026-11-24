import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CommunityReviews from './CommunityReviews'
import MediaInfoTabs from './MediaInfoTabs'
import MediaStats from './MediaStats'
import { borrarComentarioResena, crearComentarioResena, getComentariosResena } from '../services/api'

vi.mock('../services/api', () => ({
  borrarComentarioResena: vi.fn(),
  crearComentarioResena: vi.fn(),
  getComentariosResena: vi.fn(),
  leerJson: vi.fn(),
}))

const media = {
  id: 7, titulo: 'Dune', titulo_original: 'Dune: Part Two', tipo: 'pelicula', estado: 'en_cartelera',
  fecha_estreno: '2024-02-29', duracion: 166,
  reparto: [{ id: 1, nombre: 'Zendaya' }, { id: 2, nombre: 'Javier Bardem' }],
  directores: [{ id: 3, nombre: 'Denis Villeneuve' }],
  generos: [{ id: 4, nombre: 'Ciencia ficción' }],
}

const resena = {
  id: 5, usuario: 'joramenoc', usuario_avatar: '', puntuacion: 9, texto: 'Enorme',
  fecha_creacion: '2026-11-23T15:00:00Z', total_likes: 2, me_gusta: false,
  total_comentarios: 1, estado_autor: 'visto', autor_le_gusta: true,
}

beforeEach(() => vi.clearAllMocks())

describe('MediaInfoTabs', () => {
  it('el reparto enlaza a una búsqueda en Google en otra pestaña', () => {
    render(<MemoryRouter><MediaInfoTabs media={media} /></MemoryRouter>)
    const zendaya = screen.getByRole('link', { name: 'Zendaya' })
    expect(zendaya).toHaveAttribute('href', 'https://www.google.com/search?q=Zendaya')
    expect(zendaya).toHaveAttribute('target', '_blank')
  })

  it('cambia de pestaña y muestra detalles y géneros', () => {
    render(<MemoryRouter><MediaInfoTabs media={media} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('tab', { name: 'Detalles' }))
    expect(screen.getByText('Dune: Part Two')).toBeInTheDocument()
    expect(screen.getByText('166 min')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Géneros' }))
    expect(screen.getByRole('link', { name: 'Ciencia ficción' })).toHaveAttribute('href', '/catalogo?genero=ciencia-ficcion')
  })
})

describe('MediaStats', () => {
  it('muestra la nota media en la escala del usuario y la actividad', () => {
    const stats = { promedio: 8.6, total_votos: 3, distribucion: { 9: 2, 8: 1 }, vistos: 4, viendo: 0, pendientes: 2, me_gusta: 1, resenas: 3, listas: 0 }
    render(<MediaStats stats={stats} media={media} scale={5} />)
    expect(screen.getByText('4.3')).toBeInTheDocument()
    expect(screen.getByText(/de 5 · 3 calificaciones/)).toBeInTheDocument()
    expect(screen.getByText('Vistos').nextSibling).toHaveTextContent('4')
    expect(screen.queryByText('Viendo')).not.toBeInTheDocument()
    expect(screen.getByText('2 h 46 min')).toBeInTheDocument()
  })
})

describe('CommunityReviews', () => {
  it('muestra nota, estado del autor y abre los comentarios', async () => {
    getComentariosResena.mockResolvedValue({ count: 1, results: [{ id: 1, usuario: 'vienca', texto: 'De acuerdo', fecha_creacion: '2026-11-23T18:00:00Z' }] })
    render(<MemoryRouter><CommunityReviews reviews={[resena]} user={{ username: 'chicas' }} scale={5} /></MemoryRouter>)
    expect(screen.getByRole('img', { name: '4.5 de 5' })).toBeInTheDocument()
    expect(screen.getByText('Visto')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /1 comentario/ }))
    expect(await screen.findByText('De acuerdo')).toBeInTheDocument()
    expect(getComentariosResena).toHaveBeenCalledWith(5)
  })

  it('publica un comentario y suma uno al contador', async () => {
    getComentariosResena.mockResolvedValue({ count: 0, results: [] })
    crearComentarioResena.mockResolvedValue({ id: 9, usuario: 'chicas', texto: 'Qué buena reseña', fecha_creacion: '2026-11-24T01:00:00Z' })
    render(<MemoryRouter><CommunityReviews reviews={[{ ...resena, total_comentarios: 0 }]} user={{ username: 'chicas' }} scale={5} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /0 comentarios/ }))
    await screen.findByText('Nadie ha comentado todavía.')
    fireEvent.change(screen.getByLabelText('Escribe un comentario'), { target: { value: 'Qué buena reseña' } })
    fireEvent.click(screen.getByRole('button', { name: 'Comentar' }))
    expect(await screen.findByText('Qué buena reseña')).toBeInTheDocument()
    expect(crearComentarioResena).toHaveBeenCalledWith(5, 'Qué buena reseña')
    expect(screen.getByRole('button', { name: /1 comentario/ })).toBeInTheDocument()
  })

  it('el autor del comentario puede borrarlo', async () => {
    getComentariosResena.mockResolvedValue({ count: 1, results: [{ id: 1, usuario: 'chicas', texto: 'Mío', fecha_creacion: '2026-11-23T18:00:00Z' }] })
    borrarComentarioResena.mockResolvedValue(true)
    render(<MemoryRouter><CommunityReviews reviews={[resena]} user={{ username: 'chicas' }} scale={5} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /1 comentario/ }))
    const lista = await screen.findByRole('list')
    fireEvent.click(within(lista).getByRole('button', { name: 'Borrar comentario de chicas' }))
    await waitFor(() => expect(screen.queryByText('Mío')).not.toBeInTheDocument())
  })

  it('sin sesión invita a iniciar sesión para comentar', async () => {
    getComentariosResena.mockResolvedValue({ count: 0, results: [] })
    render(<MemoryRouter><CommunityReviews reviews={[resena]} user={null} scale={5} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /comentario/ }))
    expect(await screen.findByRole('link', { name: 'Inicia sesión' })).toBeInTheDocument()
  })
})
