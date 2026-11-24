import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AuthField from './AuthField'

describe('AuthField', () => {
  it('muestra y oculta la contraseña', () => {
    render(<AuthField id="clave" label="Contraseña" icon="lock" password value="" onChange={() => {}} />)
    const campo = screen.getByLabelText('Contraseña')
    expect(campo).toHaveAttribute('type', 'password')
    fireEvent.click(screen.getByRole('button', { name: 'Ver contraseña' }))
    expect(campo).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Ocultar contraseña' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('avisa cuando Bloq Mayús está activado', () => {
    render(<AuthField id="clave" label="Contraseña" password value="" onChange={() => {}} />)
    const campo = screen.getByLabelText('Contraseña')
    fireEvent.keyUp(campo, { key: 'A', modifierCapsLock: true })
    expect(screen.getByRole('status')).toHaveTextContent('Bloq Mayús está activado')
    expect(campo).toHaveAttribute('aria-describedby', 'clave-mayus')
    fireEvent.blur(campo)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('los campos normales conservan su tipo y no llevan botón de contraseña', () => {
    render(<AuthField id="correo" label="Correo" icon="mail" type="email" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('Correo')).toHaveAttribute('type', 'email')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
