import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { updateProfile } from '../services/api'
import ProfileEditForm from './ProfileEditForm'

vi.mock('../services/api', () => ({ updateProfile: vi.fn() }))

test('edita el perfil y envía la escala como número', async () => {
  const currentUser = { first_name: 'Ana', escala_calificacion: 10 }
  const saved = { ...currentUser, biografia: 'Me gusta el cine.', escala_calificacion: 5 }
  const onSaved = vi.fn()
  updateProfile.mockResolvedValue(saved)
  render(<ProfileEditForm currentUser={currentUser} onSaved={onSaved} />)

  const bio = screen.getByLabelText('Biografía')
  expect(bio).toHaveAttribute('maxlength', '500')
  fireEvent.change(bio, { target: { value: saved.biografia } })
  expect(screen.getByText('17/500 caracteres')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Escala de calificación'), { target: { value: '5' } })
  fireEvent.click(screen.getByRole('button', { name: 'Guardar perfil' }))

  await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved))
  expect(updateProfile).toHaveBeenCalledWith({
    first_name: 'Ana',
    last_name: '',
    avatar: '',
    banner: '',
    biografia: saved.biografia,
    escala_calificacion: 5,
  })
})
