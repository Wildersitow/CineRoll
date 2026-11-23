import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import UserMenu from './UserMenu'

const USUARIO = { id: 1, username: 'pepe', nombre: 'Pepito Perez', avatar: '' }

function renderizar(props = {}) {
  const onLogout = vi.fn()
  render(
    <MemoryRouter>
      <UserMenu user={USUARIO} onLogout={onLogout} isLoading={false} {...props} />
    </MemoryRouter>
  )
  return { onLogout }
}

describe('UserMenu', () => {
  it('muestra la inicial del usuario y el menú está cerrado al inicio', () => {
    renderizar()
    const boton = screen.getByRole('button', { name: 'Menú de Pepito Perez' })
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    expect(boton).toHaveTextContent('P')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('abre el menú con los accesos de la cuenta', () => {
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: 'Menú de Pepito Perez' }))
    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /Mi perfil/ })).toHaveAttribute('href', '/usuarios/pepe')
    expect(screen.getByRole('menuitem', { name: /Mensajes/ })).toHaveAttribute('href', '/mensajes')
    expect(screen.getByRole('menuitem', { name: /Configuración/ })).toHaveAttribute('href', '/perfil')
  })

  it('cierra el menú con Escape', async () => {
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: 'Menú de Pepito Perez' }))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.getByRole('button', { name: 'Menú de Pepito Perez' })).toHaveAttribute('aria-expanded', 'false')
  })

  it('llama a onLogout al pulsar Cerrar sesión', () => {
    const { onLogout } = renderizar()
    fireEvent.click(screen.getByRole('button', { name: 'Menú de Pepito Perez' }))
    fireEvent.click(screen.getByRole('menuitem', { name: /Cerrar sesión/ }))
    expect(onLogout).toHaveBeenCalledOnce()
  })
})
