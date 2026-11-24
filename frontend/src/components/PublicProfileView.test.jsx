import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PublicProfileView from './PublicProfileView'
import { getElementosDeLista, getPerfilPublico, getResenasDeUsuario, getSeguidores, getSiguiendo, getUsuarioListas } from '../services/api'

vi.mock('../services/api', () => ({
  getPerfilPublico: vi.fn(),
  getUsuarioListas: vi.fn(),
  getResenasDeUsuario: vi.fn(),
  getElementosDeLista: vi.fn(),
  getSeguidores: vi.fn(),
  getSiguiendo: vi.fn(),
  seguirUsuario: vi.fn(),
  dejarDeSeguir: vi.fn(),
  leerJson: vi.fn(),
}))

const PERFIL = {
  id: 1, username: 'pepe', nombre: 'Pepito Perez', avatar: '', banner: 'https://example.com/banner.jpg',
  biografia: 'Cinéfilo.', date_joined: '2026-11-01T10:00:00Z', total_resenas: 1, promedio_puntuacion_dada: 9,
  total_seguidores: 2, total_siguiendo: 3, lo_sigo: null,
}

function renderizar(ruta = '/usuarios/pepe') {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes><Route path="/usuarios/:username" element={<PublicProfileView currentUser={null} />} /></Routes>
    </MemoryRouter>
  )
}

describe('PublicProfileView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    getPerfilPublico.mockResolvedValue(PERFIL)
    getUsuarioListas.mockResolvedValue({ results: [{ id: 5, tipo: 'favoritas', nombre: 'Favoritas', publica: true, total_elementos: 1 }] })
    getResenasDeUsuario.mockResolvedValue({ results: [{ id: 9, media_id: 4, media_titulo: 'Coco', media_poster_url: '', puntuacion: 9, texto: 'Preciosa.', total_likes: 0, me_gusta: false }] })
    getElementosDeLista.mockResolvedValue({ results: [{ id: 1, media_id: 4, media_titulo: 'Coco', media_poster_url: '' }] })
    getSeguidores.mockResolvedValue({ count: 1, results: [{ id: 2, username: 'ana', nombre: 'Ana', avatar: '' }] })
    getSiguiendo.mockResolvedValue({ count: 0, results: [] })
  })

  it('muestra banner, estadísticas, favoritas y reseñas con estrellas', async () => {
    const { container } = renderizar()
    expect(await screen.findByRole('heading', { name: 'Pepito Perez', level: 1 })).toBeInTheDocument()
    expect(container.querySelector('.profile-banner img')).toHaveAttribute('src', PERFIL.banner)
    expect(screen.getByRole('button', { name: 'Seguidores' }).closest('div')).toHaveTextContent('2')
    // Un enlace en Favoritas y otro en la reseña (cargan por separado).
    await waitFor(() => expect(screen.getAllByRole('link', { name: 'Coco' })).toHaveLength(2))
    expect(screen.getAllByRole('img', { name: '9 de 10' }).length).toBeGreaterThan(0)
  })

  it('abre la pestaña de red desde la URL y lista los seguidores', async () => {
    renderizar('/usuarios/pepe?tab=red')
    expect(await screen.findByRole('link', { name: /Ana/ })).toHaveAttribute('href', '/usuarios/ana')
    expect(screen.getByText('Nadie por aquí todavía.')).toBeInTheDocument()
  })

  it('cambia de pestaña al pulsar Reseñas', async () => {
    renderizar()
    const tabs = within(await screen.findByRole('navigation', { name: 'Secciones del perfil' }))
    fireEvent.click(tabs.getByRole('button', { name: 'Reseñas' }))
    expect(tabs.getByRole('button', { name: 'Reseñas' })).toHaveAttribute('aria-current', 'page')
    expect(await screen.findByText('Preciosa.')).toBeInTheDocument()
  })
})
