import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import SiteFooter from './SiteFooter'

function renderizar(user) {
  render(<MemoryRouter><SiteFooter user={user} /></MemoryRouter>)
}

describe('SiteFooter', () => {
  it('sin sesión ofrece ingresar', () => {
    renderizar(null)
    expect(screen.getByRole('link', { name: 'Ingresar o crear cuenta' })).toHaveAttribute('href', '/acceso')
    expect(screen.getByRole('link', { name: 'Series' })).toHaveAttribute('href', '/catalogo?tipo=serie')
    expect(screen.getByRole('button', { name: /Volver arriba/ })).toBeInTheDocument()
  })

  it('con sesión enlaza al perfil y a los mensajes', () => {
    renderizar({ username: 'valeria' })
    expect(screen.getByRole('link', { name: 'Mi perfil' })).toHaveAttribute('href', '/usuarios/valeria')
    expect(screen.getByRole('link', { name: 'Mensajes' })).toHaveAttribute('href', '/mensajes')
    expect(screen.queryByRole('link', { name: 'Ingresar o crear cuenta' })).not.toBeInTheDocument()
  })
})
