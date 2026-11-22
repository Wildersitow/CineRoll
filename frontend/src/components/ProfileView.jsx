import { useState } from 'react'
import { Link } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'
import ProfileEditForm from './ProfileEditForm'
import ChangePasswordModal from './ChangePasswordModal'

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
  const [editing, setEditing] = useState(false)
  const [failedAvatar, setFailedAvatar] = useState(null)

  return (
    <main className="cinema-page cinema-profile cinema-profile-settings">
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

      <header className="cinema-profile-header">
        <div className="cinema-profile-identity">
          <div className="cinema-profile-avatar">
            {currentUser.avatar && currentUser.avatar !== failedAvatar ? (
              <img src={currentUser.avatar} alt="" onError={() => setFailedAvatar(currentUser.avatar)} />
            ) : <span aria-hidden="true">{(currentUser.nombre || currentUser.username || 'U').charAt(0).toUpperCase()}</span>}
          </div>
          <div><h1>{currentUser.nombre || currentUser.username}</h1><p>@{currentUser.username}</p></div>
        </div>
        <div className="cinema-profile-actions">
          <button type="button" aria-expanded={editing} aria-controls="editar-perfil" onClick={() => setEditing(!editing)}>
            <CinemaIcon name="edit" /> {editing ? 'Cancelar edición' : 'Editar perfil'}
          </button>
          <Link to={`/usuarios/${encodeURIComponent(currentUser.username)}`}>
            <CinemaIcon name="external" /> Ver perfil público
          </Link>
        </div>
        {currentUser.biografia && <p className="cinema-profile-bio">{currentUser.biografia}</p>}
      </header>
      <section className="cinema-profile-panel">
        <h2>Datos de la cuenta</h2>
        <dl className="cinema-settings-details">
          <div><dt>Correo</dt><dd>{currentUser.email || 'Sin correo registrado'}</dd></div>
          <div><dt>Escala de puntuación</dt><dd>{currentUser.escala_calificacion === 5 ? '5 estrellas (con medias)' : '1 a 10 puntos'}</dd></div>
        </dl>
        <div className="cinema-profile-actions">
          <button type="button" onClick={() => setShowChangePasswordModal(true)}>Cambiar contraseña</button>
        </div>
      </section>
      <div id="editar-perfil">
        {editing && (
          <ProfileEditForm currentUser={currentUser} onSaved={(data) => {
            setEditing(false)
            onProfileSaved(data)
          }} />
        )}
      </div>
    </main>
  )
}

