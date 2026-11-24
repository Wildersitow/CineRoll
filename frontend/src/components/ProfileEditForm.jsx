import { useState } from 'react'
import { updateProfile } from '../services/api'
import CinemaIcon from './CinemaIcon'

const BIO_LIMIT = 500

/** Vista previa de una imagen por URL; si falla o está vacía, muestra el respaldo. */
function Preview({ url, className, fallback }) {
  const [failed, setFailed] = useState(null)
  return (
    <div className={className}>
      {url && url !== failed ? <img src={url} alt="" onError={() => setFailed(url)} /> : fallback}
    </div>
  )
}

/** Campo de imagen con vista previa y botón "Cambiar" que despliega la URL. */
function ImageField({ label, name, value, onChange, preview, hint }) {
  const [open, setOpen] = useState(false)
  const inputId = `campo-${name}`
  return (
    <div className="settings-field">
      <span className="settings-label">{label}</span>
      <div className="settings-image-row">
        {preview}
        <div className="settings-image-actions">
          <button type="button" className="settings-button" aria-expanded={open} aria-controls={inputId} onClick={() => setOpen(!open)}>
            <CinemaIcon name="edit" /> {open ? 'Listo' : 'Cambiar'}
          </button>
          {value && (
            <button type="button" className="settings-button settings-button-ghost" onClick={() => onChange('')}>Quitar</button>
          )}
        </div>
      </div>
      <input
        id={inputId}
        className="settings-input"
        name={name}
        type="url"
        maxLength={200}
        placeholder="https://…"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        hidden={!open}
        aria-label={`URL del ${label.toLowerCase()}`}
      />
      {hint && <small className="settings-hint">{hint}</small>}
    </div>
  )
}

/** Sección "Perfil" de los ajustes: identidad pública del usuario. */
export default function ProfileEditForm({ currentUser, onSaved }) {
  const [biografia, setBiografia] = useState(currentUser.biografia || '')
  const [avatar, setAvatar] = useState(currentUser.avatar || '')
  const [banner, setBanner] = useState(currentUser.banner || '')
  const [status, setStatus] = useState({ loading: false, error: '', saved: false })
  const initial = (currentUser.nombre || currentUser.first_name || currentUser.username || 'U').charAt(0).toUpperCase()

  async function save(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const datos = {
      first_name: form.get('first_name').trim(),
      last_name: form.get('last_name').trim(),
      avatar: avatar.trim(),
      banner: banner.trim(),
      biografia,
    }
    setStatus({ loading: true, error: '', saved: false })
    try {
      onSaved(await updateProfile(datos))
      setStatus({ loading: false, error: '', saved: true })
    } catch (error) {
      setStatus({ loading: false, error: error.message, saved: false })
    }
  }

  return (
    <form className="settings-section" onSubmit={save} onChange={() => status.saved && setStatus({ ...status, saved: false })}>
      <h2>Perfil</h2>

      <div className="settings-field">
        <label className="settings-label" htmlFor="campo-usuario">Usuario</label>
        <input id="campo-usuario" className="settings-input" value={`@${currentUser.username || ''}`} readOnly aria-describedby="usuario-ayuda" />
        <small id="usuario-ayuda" className="settings-hint">El nombre de usuario no se puede cambiar.</small>
      </div>

      <div className="settings-grid">
        <ImageField
          label="Avatar"
          name="avatar"
          value={avatar}
          onChange={setAvatar}
          preview={<Preview url={avatar} className="settings-avatar-preview" fallback={<span aria-hidden="true">{initial}</span>} />}
        />
        <ImageField
          label="Banner"
          name="banner"
          value={banner}
          onChange={setBanner}
          hint="Imagen ancha, ideal 1500 × 500. Se ve en tu perfil público."
          preview={<Preview url={banner} className="settings-banner-preview" fallback={<span>Sin banner</span>} />}
        />
      </div>

      <div className="settings-grid">
        <label className="settings-field">
          <span className="settings-label">Nombre</span>
          <input className="settings-input" name="first_name" maxLength={150} defaultValue={currentUser.first_name || ''} />
        </label>
        <label className="settings-field">
          <span className="settings-label">Apellido</span>
          <input className="settings-input" name="last_name" maxLength={150} defaultValue={currentUser.last_name || ''} />
        </label>
      </div>

      <div className="settings-field">
        <label className="settings-label" htmlFor="campo-biografia">Biografía</label>
        <textarea
          id="campo-biografia"
          className="settings-input settings-textarea"
          name="biografia"
          rows={5}
          maxLength={BIO_LIMIT}
          value={biografia}
          onChange={(event) => setBiografia(event.target.value)}
          placeholder="Cuéntale a los demás qué tipo de cine te gusta…"
          aria-describedby="bio-length"
        />
        <small id="bio-length" className="settings-hint settings-counter">{biografia.length}/{BIO_LIMIT} caracteres</small>
      </div>

      <div className="settings-savebar">
        {status.error && <p role="alert">{status.error}</p>}
        {status.saved && <p role="status">Cambios guardados.</p>}
        <button className="settings-button settings-button-primary" type="submit" disabled={status.loading}>
          {status.loading ? 'Guardando…' : 'Guardar perfil'}
        </button>
      </div>
    </form>
  )
}
