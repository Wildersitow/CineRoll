import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import RutaProtegida from './RutaProtegida'

function PantallaAcceso() {
  const location = useLocation()
  const desde = location.state?.desde?.pathname ?? 'ninguna'
  return <p>{`Pantalla de acceso (desde: ${desde})`}</p>
}

const USUARIO = { id: 1, username: 'ana' }

function renderizarComoRutaPadre(usuario, rutaInicial = '/perfil') {
  return render(
    <MemoryRouter initialEntries={[rutaInicial]}>
      <Routes>
        <Route path="/acceso" element={<PantallaAcceso />} />
        <Route element={<RutaProtegida usuario={usuario} />}>
          <Route path="/perfil" element={<p>Contenido privado</p>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('RutaProtegida', () => {
  it('redirige a /acceso cuando no hay sesión', () => {
    renderizarComoRutaPadre(null)

    expect(screen.getByText(/Pantalla de acceso/)).toBeInTheDocument()
    expect(screen.queryByText('Contenido privado')).not.toBeInTheDocument()
  })

  it('recuerda la ruta a la que se intentaba entrar', () => {
    renderizarComoRutaPadre(null, '/perfil')

    expect(screen.getByText('Pantalla de acceso (desde: /perfil)')).toBeInTheDocument()
  })

  it('muestra el contenido cuando hay sesión', () => {
    renderizarComoRutaPadre(USUARIO)

    expect(screen.getByText('Contenido privado')).toBeInTheDocument()
    expect(screen.queryByText(/Pantalla de acceso/)).not.toBeInTheDocument()
  })

  it('también funciona envolviendo a un componente hijo', () => {
    render(
      <MemoryRouter initialEntries={['/perfil']}>
        <Routes>
          <Route path="/acceso" element={<PantallaAcceso />} />
          <Route
            path="/perfil"
            element={
              <RutaProtegida usuario={USUARIO}>
                <p>Hijo directo</p>
              </RutaProtegida>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('Hijo directo')).toBeInTheDocument()
  })
})