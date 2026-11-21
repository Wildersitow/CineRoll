import { useState } from 'react'
import { updateProfile } from '../services/api'

const BIO_LIMIT = 500

export default function ProfileEditForm({ currentUser, onSaved }) {
  const [biografia, setBiografia] = useState(currentUser.biografia || '')
  const [status, setStatus] = useState({ loading: false, error: '' })

  async function save(event) {
    event.preventDefault()
    const datos = Object.fromEntries(new FormData(event.currentTarget))
    datos.escala_calificacion = Number(datos.escala_calificacion)
    setStatus({ loading: true, error: '' })

    try {
      onSaved(await updateProfile(datos))
    } catch (error) {
      setStatus({ loading: false, error: error.message })
    }
  }

  return (
    <form className="profile-edit auth-form" onSubmit={save}>
      <h2>Editar perfil</h2>
      <label className="input-group">Nombre<input name="first_name" maxLength={150} defaultValue={currentUser.first_name || ''} /></label>
      <label className="input-group">Apellido<input name="last_name" maxLength={150} defaultValue={currentUser.last_name || ''} /></label>
      <label className="input-group">URL del avatar<input name="avatar" type="url" maxLength={200} defaultValue={currentUser.avatar || ''} /></label>
      <label className="input-group">
        Biografía
        <textarea name="biografia" rows={4} maxLength={BIO_LIMIT} value={biografia} onChange={(event) => setBiografia(event.target.value)} aria-describedby="bio-length" />
      </label>
      <small id="bio-length">{biografia.length}/{BIO_LIMIT} caracteres</small>
      <label className="input-group">
        Escala de calificación
        <select name="escala_calificacion" defaultValue={currentUser.escala_calificacion || 10}>
          <option value="10">1 a 10 puntos</option>
          <option value="5">5 estrellas (con medias)</option>
        </select>
      </label>
      {status.error && <p role="alert">{status.error}</p>}
      <button className="submit-btn" type="submit" disabled={status.loading}>
        {status.loading ? 'Guardando…' : 'Guardar perfil'}
      </button>
    </form>
  )
}
