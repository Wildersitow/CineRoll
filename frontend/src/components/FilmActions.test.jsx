import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FilmActions from './FilmActions'
import { actualizarRegistro, crearResena, getMiRegistro, getMiResena } from '../services/api'

vi.mock('../services/api', () => ({
  actualizarRegistro: vi.fn(),
  borrarResena: vi.fn(),
  crearResena: vi.fn(),
  editarResena: vi.fn(),
  getMiRegistro: vi.fn(),
  getMiResena: vi.fn(),
  leerJson: vi.fn(),
}))

const user = { username: 'ana', escala_calificacion: 5 }
const pelicula = { id: 7, titulo: 'Dune', tipo: 'pelicula', estado: 'en_cartelera', fecha_estreno: '2024-03-01' }
const vacio = { media_id: 7, estado: '', me_gusta: false, pendiente: false }

function renderActions(media = pelicula, ruta = '/media/7', refresh = vi.fn()) {
  return render(<MemoryRouter initialEntries={[ruta]}><FilmActions media={media} user={user} refresh={refresh} /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  getMiRegistro.mockResolvedValue(vacio)
  const sinResena = Object.assign(new Error('No has reseñado'), { status: 404 })
  getMiResena.mockRejectedValue(sinResena)
})

describe('FilmActions', () => {
  it('una película muestra Visto, Pendiente y Me gusta, pero no Viendo', async () => {
    renderActions()
    expect(await screen.findByRole('button', { name: /Visto/ })).toBeEnabled()
    expect(screen.getByRole('button', { name: /Pendiente/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Me gusta/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Viendo/ })).not.toBeInTheDocument()
  })

  it('una serie también puede marcarse como Viendo', async () => {
    renderActions({ ...pelicula, tipo: 'serie' })
    expect(await screen.findByRole('button', { name: /Viendo/ })).toBeInTheDocument()
  })

  it('marcar Visto se ve al instante y lo saca de Pendiente', async () => {
    getMiRegistro.mockResolvedValue({ ...vacio, pendiente: true })
    actualizarRegistro.mockResolvedValue({ ...vacio, estado: 'visto' })
    renderActions()
    const visto = await screen.findByRole('button', { name: /Visto/ })
    await waitFor(() => expect(visto).toBeEnabled())
    fireEvent.click(visto)
    expect(visto).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Pendiente/ })).toHaveAttribute('aria-pressed', 'false')
    expect(actualizarRegistro).toHaveBeenCalledWith(7, { estado: 'visto' })
  })

  it('revierte el cambio si el servidor falla', async () => {
    actualizarRegistro.mockRejectedValue(new Error('Sin conexión'))
    renderActions()
    const like = await screen.findByRole('button', { name: /Me gusta/ })
    await waitFor(() => expect(like).toBeEnabled())
    fireEvent.click(like)
    expect(await screen.findByRole('status')).toHaveTextContent('Sin conexión')
    expect(like).toHaveAttribute('aria-pressed', 'false')
  })

  it('un próximo estreno no se puede marcar como visto ni reseñar', async () => {
    renderActions({ ...pelicula, estado: 'proximo_estreno' })
    await waitFor(() => expect(screen.getByRole('button', { name: /Pendiente/ })).toBeEnabled())
    expect(screen.getByRole('button', { name: /Visto/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Reseñar/ })).toBeDisabled()
  })

  it('la ventana de reseña publica con la nota elegida', async () => {
    const refresh = vi.fn()
    crearResena.mockResolvedValue({ id: 3, puntuacion: 8, texto: 'Enorme' })
    renderActions(pelicula, '/media/7?accion=reseña', refresh)
    const dialogo = await screen.findByRole('dialog', { name: 'Lo vi…' })
    const guardar = within(dialogo).getByRole('button', { name: 'Guardar' })
    expect(guardar).toBeDisabled()
    fireEvent.change(within(dialogo).getByLabelText('Tu reseña'), { target: { value: 'Enorme' } })
    fireEvent.click(within(dialogo).getByLabelText('4 de 5'))
    expect(within(dialogo).getByText('4 de 5', { selector: 'output' })).toBeInTheDocument()
    fireEvent.click(guardar)
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(crearResena).toHaveBeenCalledWith(7, { puntuacion: 8, texto: 'Enorme' })
    expect(refresh).toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Reseña publicada.')
  })

  it('al elegir estrellas en el panel se abre la reseña con esa nota', async () => {
    renderActions()
    const calificar = await screen.findByRole('radiogroup', { name: 'Calificar' })
    await waitFor(() => expect(within(calificar).getByLabelText('3.5 de 5')).toBeEnabled())
    fireEvent.click(within(calificar).getByLabelText('3.5 de 5'))
    const dialogo = await screen.findByRole('dialog')
    expect(within(dialogo).getByText('3.5 de 5', { selector: 'output' })).toBeInTheDocument()
  })
})
