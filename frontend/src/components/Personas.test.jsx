import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PersonasEncontradas, UsuariosRecomendados } from './Personas'
import { buscarUsuarios, dejarDeSeguir, getStoredAuth, getUsuariosRecomendados, seguirUsuario } from '../services/api'

vi.mock('../services/api', () => ({
  buscarUsuarios: vi.fn(),
  dejarDeSeguir: vi.fn(),
  getStoredAuth: vi.fn(),
  getUsuariosRecomendados: vi.fn(),
  seguirUsuario: vi.fn(),
}))

const ana = { id: 2, username: 'ana_cine', nombre: 'Ana Mejía', avatar: '', total_resenas: 3, total_seguidores: 1, en_comun: 0, lo_sigo: false }

function renderizar(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  getStoredAuth.mockReturnValue({ username: 'valeria', token: 't' })
})

describe('UsuariosRecomendados', () => {
  it('muestra las tarjetas y permite seguir', async () => {
    getUsuariosRecomendados.mockResolvedValue([{ ...ana, en_comun: 2 }])
    seguirUsuario.mockResolvedValue({})
    renderizar(<UsuariosRecomendados />)
    expect(await screen.findByRole('heading', { name: 'Usuarios recomendados' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ana Mejía/ })).toHaveAttribute('href', '/usuarios/ana_cine')
    expect(screen.getByText('Lo siguen 2 personas que sigues')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Seguir a @ana_cine' }))
    await waitFor(() => expect(seguirUsuario).toHaveBeenCalledWith('ana_cine'))
    expect(await screen.findByRole('button', { name: 'Dejar de seguir a @ana_cine' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('no pinta nada si no hay recomendaciones', async () => {
    getUsuariosRecomendados.mockResolvedValue([])
    const { container } = renderizar(<UsuariosRecomendados />)
    await waitFor(() => expect(getUsuariosRecomendados).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })

  it('sin sesión el botón lleva a ingresar', async () => {
    getStoredAuth.mockReturnValue(null)
    getUsuariosRecomendados.mockResolvedValue([ana])
    renderizar(<UsuariosRecomendados />)
    expect(await screen.findByRole('link', { name: 'Seguir' })).toHaveAttribute('href', '/acceso')
  })
})

describe('PersonasEncontradas', () => {
  it('lista las personas que coinciden con la búsqueda', async () => {
    buscarUsuarios.mockResolvedValue({ count: 1, results: [{ ...ana, lo_sigo: true }] })
    dejarDeSeguir.mockResolvedValue(true)
    renderizar(<PersonasEncontradas texto="ana" />)
    expect(await screen.findByRole('heading', { name: 'Personas' })).toBeInTheDocument()
    expect(buscarUsuarios).toHaveBeenCalledWith('ana', {}, expect.anything())
    expect(screen.getByText('3 reseñas · 1 seguidor')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dejar de seguir a @ana_cine' }))
    await waitFor(() => expect(dejarDeSeguir).toHaveBeenCalledWith('ana_cine'))
  })

  it('se oculta si nadie coincide', async () => {
    buscarUsuarios.mockResolvedValue({ count: 0, results: [] })
    const { container } = renderizar(<PersonasEncontradas texto="zzz" />)
    await waitFor(() => expect(buscarUsuarios).toHaveBeenCalled())
    expect(container).toBeEmptyDOMElement()
  })
})
