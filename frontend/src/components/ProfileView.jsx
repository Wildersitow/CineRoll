import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { updateProfile } from '../services/api'
import CinemaIcon from './CinemaIcon'
import ProfileEditForm from './ProfileEditForm'
import FavoritasEditor from './FavoritasEditor'
import ChangePasswordModal from './ChangePasswordModal'

const SECCIONES = [
  { id: 'perfil', label: 'Perfil', description: 'Avatar, banner, biografía y favoritas', icon: 'user' },
  { id: 'preferencias', label: 'Preferencias', description: 'Cómo ves las puntuaciones', icon: 'settings' },
  { id: 'cuenta', label: 'Cuenta', description: 'Correo y contraseña', icon: 'key' },
]

const ESCALAS = [
  { value: 10, title: '1 a 10 puntos', example: '8/10', description: 'Una nota exacta para cada título.' },
  { value: 5, title: '5 estrellas', example: '★★★★½', description: 'Estrellas con medias, como en Letterboxd.' },
]

/** Sección "Preferencias": escala de puntuación como tarjetas seleccionables. */
function Preferencias({ currentUser, onProfileSaved }) {
  const [status, setStatus] = useState({ loading: false, error: '' })
  const actual = Number(currentUser.escala_calificacion) || 10

  async function choose(value) {
    if (value === actual || status.loading) return
    setStatus({ loading: true, error: '' })
    try {
      onProfileSaved(await updateProfile({ escala_calificacion: value }))
      setStatus({ loading: false, error: '' })
    } catch (error) {
      setStatus({ loading: false, error: error.message })
    }
  }

  return (
    <section className="settings-section" aria-labelledby="preferencias-titulo">
      <h2 id="preferencias-titulo">Preferencias</h2>
      <div className="settings-field">
        <span className="settings-label" id="escala-label">Escala de puntuación</span>
        <small className="settings-hint">Solo cambia cómo ves las notas; las reseñas se guardan siempre de 1 a 10.</small>
        <div className="settings-choices" role="radiogroup" aria-labelledby="escala-label">
          {ESCALAS.map(({ value, title, example, description }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={actual === value}
              className="settings-choice"
              disabled={status.loading}
              onClick={() => choose(value)}
            >
              <span className="settings-choice-example" aria-hidden="true">{example}</span>
              <strong>{title}</strong>
              <small>{description}</small>
            </button>
          ))}
        </div>
        {status.loading && <p className="settings-hint" role="status">Guardando…</p>}
        {status.error && <p role="alert">{status.error}</p>}
      </div>
    </section>
  )
}

export default function ProfileView({
  currentUser,
  onProfileSaved,
  showChangePasswordModal,
  setShowChangePasswordModal,
  currentPasswordInput,
  setCurrentPasswordInput,
  newPasswordInput,
  setNewPasswordInput,
  confirmNewPasswordInput,
  setConfirmNewPasswordInput,
  passwordChangeStatus,
  onChangePasswordSubmit,
  onResetPasswordInputs,
}) {
  const [query, setQuery] = useSearchParams()
  const seccion = SECCIONES.some(({ id }) => id === query.get('seccion')) ? query.get('seccion') : 'perfil'
  const perfilPublico = `/usuarios/${encodeURIComponent(currentUser.username)}`

  function select(id) {
    setQuery(id === 'perfil' ? {} : { seccion: id }, { replace: true })
  }

  return (
    <main className="cinema-page settings-page">
      {showChangePasswordModal && (
        <ChangePasswordModal
          currentPasswordInput={currentPasswordInput}
          setCurrentPasswordInput={setCurrentPasswordInput}
          newPasswordInput={newPasswordInput}
          setNewPasswordInput={setNewPasswordInput}
          confirmNewPasswordInput={confirmNewPasswordInput}
          setConfirmNewPasswordInput={setConfirmNewPasswordInput}
          passwordChangeStatus={passwordChangeStatus}
          onSubmit={onChangePasswordSubmit}
          onClose={() => {
            onResetPasswordInputs()
            setShowChangePasswordModal(false)
          }}
        />
      )}

      <aside className="settings-nav">
        <h1>Ajustes</h1>
        <nav aria-label="Secciones de ajustes">
          {SECCIONES.map(({ id, label, description, icon }) => (
            <button key={id} type="button" aria-current={seccion === id ? 'page' : undefined} onClick={() => select(id)}>
              <CinemaIcon name={icon} weight={seccion === id ? 'fill' : 'regular'} />
              <span><strong>{label}</strong><small>{description}</small></span>
            </button>
          ))}
          <Link to={perfilPublico}>
            <CinemaIcon name="external" />
            <span><strong>Ver perfil público</strong><small>Así te ven los demás</small></span>
          </Link>
        </nav>
      </aside>

      <div className="settings-content">
        {seccion === 'perfil' && (
          <>
            <ProfileEditForm key={currentUser.username} currentUser={currentUser} onSaved={onProfileSaved} />
            <FavoritasEditor username={currentUser.username} />
          </>
        )}
        {seccion === 'preferencias' && <Preferencias currentUser={currentUser} onProfileSaved={onProfileSaved} />}
        {seccion === 'cuenta' && (
          <section className="settings-section" aria-labelledby="cuenta-titulo">
            <h2 id="cuenta-titulo">Cuenta</h2>
            <dl className="settings-details">
              <div><dt>Correo</dt><dd>{currentUser.email || 'Sin correo registrado'}</dd></div>
              <div><dt>Usuario</dt><dd>@{currentUser.username}</dd></div>
              {currentUser.date_joined && (
                <div><dt>Miembro desde</dt><dd>{new Date(currentUser.date_joined).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })}</dd></div>
              )}
            </dl>
            <div className="settings-field">
              <span className="settings-label">Contraseña</span>
              <small className="settings-hint">Usa al menos 8 caracteres y no la repitas en otros sitios.</small>
              <div>
                <button type="button" className="settings-button" onClick={() => setShowChangePasswordModal(true)}>
                  <CinemaIcon name="key" /> Cambiar contraseña
                </button>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  )
}
