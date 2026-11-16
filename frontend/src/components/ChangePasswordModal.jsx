export default function ChangePasswordModal({
  currentPasswordInput,
  setCurrentPasswordInput,
  newPasswordInput,
  setNewPasswordInput,
  confirmNewPasswordInput,
  setConfirmNewPasswordInput,
  passwordChangeStatus,
  onSubmit,
  onClose,
}) {
  return (
    <div
      className="password-change-card"
      style={{
        background: 'rgba(18, 23, 34, 0.95)',
        border: '1px solid rgba(229, 9, 20, 0.3)',
        borderRadius: '16px',
        padding: '1.75rem',
        marginBottom: '2rem',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)',
      }}
    >
      <h3
        style={{
          color: '#ffffff',
          marginBottom: '1rem',
          fontSize: '1.2rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <svg
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: '#e50914' }}
        >
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
        Cambiar Contraseña de tu Perfil
      </h3>

      {passwordChangeStatus.error && (
        <div className="auth-alert-error" role="alert" style={{ marginBottom: '1rem' }}>
          <span>{passwordChangeStatus.error}</span>
        </div>
      )}

      {passwordChangeStatus.success && (
        <div
          style={{
            background: 'rgba(22, 101, 52, 0.3)',
            border: '1px solid #16a34a',
            color: '#86efac',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.88rem',
          }}
        >
          <span>{passwordChangeStatus.success}</span>
        </div>
      )}

      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="input-group">
          <label htmlFor="current-pwd">Contraseña actual</label>
          <div className="input-field-wrapper">
            <input
              id="current-pwd"
              type="password"
              required
              placeholder="••••••••"
              value={currentPasswordInput}
              onChange={(e) => setCurrentPasswordInput(e.target.value)}
            />
          </div>
        </div>

        <div className="input-group">
          <label htmlFor="new-pwd">Nueva contraseña (mínimo 8 caracteres)</label>
          <div className="input-field-wrapper">
            <input
              id="new-pwd"
              type="password"
              required
              placeholder="••••••••"
              value={newPasswordInput}
              onChange={(e) => setNewPasswordInput(e.target.value)}
            />
          </div>
        </div>

        <div className="input-group">
          <label htmlFor="confirm-new-pwd">Confirmar nueva contraseña</label>
          <div className="input-field-wrapper">
            <input
              id="confirm-new-pwd"
              type="password"
              required
              placeholder="••••••••"
              value={confirmNewPasswordInput}
              onChange={(e) => setConfirmNewPasswordInput(e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '0.6rem 1.2rem',
              background: 'transparent',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              color: '#94a3b8',
              cursor: 'pointer',
            }}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="submit-btn"
            style={{ width: 'auto', padding: '0.6rem 1.5rem', margin: 0 }}
            disabled={passwordChangeStatus.loading}
          >
            {passwordChangeStatus.loading ? 'Guardando...' : 'Actualizar Contraseña'}
          </button>
        </div>
      </form>
    </div>
  )
}

