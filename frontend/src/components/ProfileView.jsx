import ChangePasswordModal from './ChangePasswordModal'

export default function ProfileView({
  currentUser,
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
  onLogout,
  isLoading,
}) {
  return (
    <div className="authenticated-scene">
      <header className="scene-navbar">
        <div className="scene-brand">
          <div className="logo-badge-small">
            <svg
              className="film-icon-small"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
              <line x1="7" y1="2" x2="7" y2="22"></line>
              <line x1="17" y1="2" x2="17" y2="22"></line>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <line x1="2" y1="7" x2="7" y2="7"></line>
              <line x1="2" y1="17" x2="7" y2="17"></line>
              <line x1="17" y1="17" x2="22" y2="17"></line>
              <line x1="17" y1="7" x2="22" y2="7"></line>
            </svg>
          </div>
          <span className="scene-title">
            Cine<span>Roll</span>
          </span>
        </div>

        <div className="scene-user-actions">
          <span className="scene-user-greeting">
            Hola, <strong>{currentUser.nombre || currentUser.username}</strong>
          </span>
          <button
            type="button"
            className="action-btn-secondary"
            onClick={() => {
              onResetPasswordInputs()
              setShowChangePasswordModal(!showChangePasswordModal)
            }}
            style={{
              padding: '0.5rem 1rem',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: '0.85rem',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            {showChangePasswordModal ? 'Cerrar Clave' : 'Cambiar Contraseña'}
          </button>
          <button
            id="btn-logout"
            type="button"
            className="action-btn-logout"
            onClick={onLogout}
            disabled={isLoading}
          >
            {isLoading ? 'Cerrando...' : 'Cerrar Sesión'}
          </button>
        </div>
      </header>

      <main
        className="blank-scene-content"
        style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}
      >
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

        {/* Perfil del Usuario */}
        <div
          className="profile-info-card"
          style={{
            background: 'rgba(18, 23, 34, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '20px',
            padding: '2rem',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1.5rem' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #e50914 0%, #7f1d1d 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                fontWeight: '700',
                color: '#ffffff',
                boxShadow: '0 4px 14px rgba(229, 9, 20, 0.3)',
              }}
            >
              {(currentUser.nombre || currentUser.username || 'U').charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style={{ color: '#ffffff', margin: 0, fontSize: '1.4rem' }}>
                {currentUser.nombre || currentUser.username}
              </h2>
              <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                @{currentUser.username} · {currentUser.email || 'Sin correo registrado'}
              </span>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
              marginTop: '1rem',
            }}
          >
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                padding: '1rem',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <span
                style={{
                  color: '#94a3b8',
                  fontSize: '0.8rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Escala de Puntuación
              </span>
              <p style={{ color: '#f1f5f9', margin: '0.25rem 0 0 0', fontWeight: '600' }}>
                {currentUser.escala_calificacion === 5 ? '⭐ 5 estrellas (con medias)' : '🔢 1 a 10 puntos'}
              </p>
            </div>

            <div
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                padding: '1rem',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.05)',
              }}
            >
              <span
                style={{
                  color: '#94a3b8',
                  fontSize: '0.8rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Sesión Segura
              </span>
              <p
                style={{
                  color: '#10b981',
                  margin: '0.25rem 0 0 0',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
                JWT + Lista Negra Activa
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

