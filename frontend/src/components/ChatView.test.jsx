import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ChatView from './ChatView'
import { agruparMensajes, etiquetaDia } from '../utils/chat'
import { getMediaDetalle, getPerfilPublico, leerJson } from '../services/api'

vi.mock('../services/api', () => ({
  getMediaDetalle: vi.fn(),
  getPerfilPublico: vi.fn(),
  leerJson: vi.fn(),
}))

const yo = { username: 'valeria' }

function mensaje(id, autor, fecha, texto = `m${id}`) {
  return { id, autor, autor_avatar: '', texto, fecha }
}

function abrir(ruta, user = yo) {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        {['/mensajes', '/mensajes/:username', '/salas/:id'].map(path => (
          <Route key={path} path={path} element={<ChatView user={user} />} />
        ))}
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  getPerfilPublico.mockResolvedValue({ username: 'sergio', nombre: 'Sergio Díaz', avatar: '' })
  getMediaDetalle.mockResolvedValue({ id: 7, titulo: 'Dune', poster_url: '' })
})

describe('utilidades del chat', () => {
  it('agrupa mensajes seguidos del mismo autor y separa por día', () => {
    const filas = agruparMensajes([
      mensaje(1, 'sergio', '2026-11-23T15:00:00'),
      mensaje(2, 'sergio', '2026-11-24T10:00:00'),
      mensaje(3, 'sergio', '2026-11-24T10:01:00'),
      mensaje(4, 'valeria', '2026-11-24T10:02:00'),
    ])
    expect(filas.map(f => f.tipo)).toEqual(['dia', 'mensaje', 'dia', 'mensaje', 'mensaje', 'mensaje'])
    const [m2, m3, m4] = filas.slice(3)
    expect([m2.inicio, m2.fin]).toEqual([true, false])
    expect([m3.inicio, m3.fin]).toEqual([false, true])
    expect([m4.inicio, m4.fin]).toEqual([true, true])
  })

  it('nombra los días como Hoy y Ayer', () => {
    const hoy = new Date('2026-11-24T12:00:00')
    expect(etiquetaDia('2026-11-24T08:00:00', hoy)).toBe('Hoy')
    expect(etiquetaDia('2026-11-23T08:00:00', hoy)).toBe('Ayer')
    expect(etiquetaDia('2026-11-20T08:00:00', hoy)).not.toMatch(/Hoy|Ayer/)
  })
})

describe('ChatView', () => {
  it('la bandeja muestra cada conversación con su último mensaje', async () => {
    leerJson.mockResolvedValue([
      { usuario: 'sergio', nombre: 'Sergio Díaz', avatar: '', ultimo_mensaje: { texto: '¿Vamos?', fecha: new Date().toISOString(), mio: true } },
    ])
    abrir('/mensajes')
    const enlace = await screen.findByRole('link', { name: /Sergio Díaz/ })
    expect(enlace).toHaveAttribute('href', '/mensajes/sergio')
    expect(enlace).toHaveTextContent('Tú: ¿Vamos?')
    expect(leerJson).toHaveBeenCalledWith('/chats/', expect.anything())
  })

  it('pinta mis mensajes a la derecha y los ajenos a la izquierda', async () => {
    const ahora = Date.now()
    leerJson.mockResolvedValue({
      results: [
        mensaje(1, 'sergio', new Date(ahora - 60000).toISOString(), 'Hola'),
        mensaje(2, 'valeria', new Date(ahora).toISOString(), '¡Hola!'),
      ],
      hay_anteriores: false, hay_mas: false,
    })
    abrir('/mensajes/sergio')
    const log = await screen.findByRole('log', { name: 'Mensajes' })
    await waitFor(() => expect(within(log).getByText('¡Hola!')).toBeInTheDocument())
    expect(within(log).getByText('¡Hola!').closest('li')).toHaveClass('chat-msg', 'mine')
    expect(within(log).getByText('Hola').closest('li')).toHaveClass('chat-msg', 'theirs')
    expect(within(log).getByText('Hoy')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Conversación con @sergio' })).toBeInTheDocument()
  })

  it('Enter envía el mensaje y Mayús + Enter no', async () => {
    leerJson.mockImplementation((url, opciones) => opciones?.method === 'POST'
      ? Promise.resolve(mensaje(9, 'valeria', new Date().toISOString(), JSON.parse(opciones.body).texto))
      : Promise.resolve({ results: [], hay_anteriores: false, hay_mas: false }))
    abrir('/mensajes/sergio')
    const campo = await screen.findByRole('textbox', { name: 'Mensaje' })
    fireEvent.change(campo, { target: { value: 'Nos vemos en el cine' } })
    fireEvent.keyDown(campo, { key: 'Enter', shiftKey: true })
    expect(leerJson).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ method: 'POST' }))

    fireEvent.keyDown(campo, { key: 'Enter' })
    await waitFor(() => expect(leerJson).toHaveBeenCalledWith(
      '/chats/usuarios/sergio/', expect.objectContaining({ method: 'POST' })
    ))
    const cuerpo = JSON.parse(leerJson.mock.calls.find(([, o]) => o?.method === 'POST')[1].body)
    expect(cuerpo.texto).toBe('Nos vemos en el cine')
    expect(cuerpo.envio).toEqual(expect.any(String))
    expect(await screen.findByText('Nos vemos en el cine')).toBeInTheDocument()
    expect(campo).toHaveValue('')
  })

  it('si el envío falla, devuelve el texto al campo y avisa', async () => {
    leerJson.mockImplementation((url, opciones) => opciones?.method === 'POST'
      ? Promise.reject(new Error('Sin conexión'))
      : Promise.resolve({ results: [], hay_anteriores: false, hay_mas: false }))
    abrir('/mensajes/sergio')
    const campo = await screen.findByRole('textbox', { name: 'Mensaje' })
    fireEvent.change(campo, { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión')
    expect(campo).toHaveValue('Hola')
  })

  it('la sala de un título muestra su nombre e invita a ingresar sin sesión', async () => {
    leerJson.mockResolvedValue({ results: [], hay_anteriores: false, hay_mas: false })
    abrir('/salas/7', null)
    expect(await screen.findByRole('heading', { name: 'Sala de Dune' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ingresa para conversar' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Volver a la ficha' })).toHaveAttribute('href', '/media/7')
  })
})
