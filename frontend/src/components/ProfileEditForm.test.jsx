import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { updateProfile } from '../services/api'
import ProfileEditForm from './ProfileEditForm'

vi.mock('../services/api', () => ({ updateProfile: vi.fn() }))

test('edita el perfil con avatar, banner y biografía', async () => {
  const currentUser = { username: 'ana', first_name: 'Ana', escala_calificacion: 10 }
  const saved = { ...currentUser, biografia: 'Me gusta el cine.', banner: 'https://example.com/b.jpg' }
  const onSaved = vi.fn()
  updateProfile.mockResolvedValue(saved)
  render(<ProfileEditForm currentUser={currentUser} onSaved={onSaved} />)

  expect(screen.getByDisplayValue('@ana')).toHaveAttribute('readonly')
  const bio = screen.getByLabelText('Biografía')
  expect(bio).toHaveAttribute('maxlength', '500')
  fireEvent.change(bio, { target: { value: saved.biografia } })
  expect(screen.getByText('17/500 caracteres')).toBeInTheDocument()

  const [, cambiarBanner] = screen.getAllByRole('button', { name: /Cambiar/ })
  fireEvent.click(cambiarBanner)
  fireEvent.change(screen.getByLabelText('URL del banner'), { target: { value: saved.banner } })
  fireEvent.click(screen.getByRole('button', { name: 'Guardar perfil' }))

  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved))
  expect(updateProfile).toHaveBeenCalledWith({
    first_name: 'Ana',
    last_name: '',
    avatar: '',
    banner: saved.banner,
    biografia: saved.biografia,
  })
  expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument()
})
