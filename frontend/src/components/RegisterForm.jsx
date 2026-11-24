import AuthField from './AuthField'

const MIN_PASSWORD_LENGTH = 8

export default function RegisterForm({
  registerUsername,
  setRegisterUsername,
  registerName,
  setRegisterName,
  registerEmail,
  setRegisterEmail,
  registerPassword,
  setRegisterPassword,
  registerConfirmPassword,
  setRegisterConfirmPassword,
  agreeTerms,
  setAgreeTerms,
  isLoading,
  onSubmit,
  onSwitchToLogin,
}) {
  // Cálculo de fuerza de contraseña
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { level: 0, label: '', color: '' }
    if (pwd.length < MIN_PASSWORD_LENGTH) return { level: 1, label: 'Débil', color: '#ef4444' }
    if (pwd.length < 12 || /^\d+$/.test(pwd)) return { level: 2, label: 'Media', color: '#f59e0b' }
    return { level: 3, label: 'Segura', color: '#10b981' }
  }

  const strength = getPasswordStrength(registerPassword)

  return (
    <form className="auth-form" onSubmit={onSubmit} aria-busy={isLoading}>
      <AuthField
        id="register-username"
        label="Nombre de usuario (opcional)"
        icon="at"
        name="username"
        autoComplete="username"
        autoCapitalize="none"
        type="text"
        placeholder="valeria_cine"
        value={registerUsername}
        onChange={(e) => setRegisterUsername(e.target.value)}
      />

      <AuthField
        id="register-name"
        label="Nombre completo"
        icon="name"
        name="name"
        autoComplete="name"
        type="text"
        placeholder="Valeria Torres"
        value={registerName}
        onChange={(e) => setRegisterName(e.target.value)}
      />

      <AuthField
        id="register-email"
        label="Correo electrónico"
        icon="mail"
        name="email"
        autoComplete="email"
        autoCapitalize="none"
        type="email"
        required
        placeholder="valeria@ejemplo.com"
        value={registerEmail}
        onChange={(e) => setRegisterEmail(e.target.value)}
      />

      <AuthField
        id="register-password"
        label="Contraseña"
        icon="lock"
        password
        name="password"
        autoComplete="new-password"
        aria-describedby="register-password-hint"
        required
        placeholder="Crea una clave"
        value={registerPassword}
        onChange={(e) => setRegisterPassword(e.target.value)}
      >
        <p id="register-password-hint" className="field-hint">Mínimo 8 caracteres.</p>
        {registerPassword && (
          <div className="strength-meter">
            <div className="strength-bars">
              <span className={`bar ${strength.level >= 1 ? 'active' : ''}`} style={{ backgroundColor: strength.level >= 1 ? strength.color : '' }}></span>
              <span className={`bar ${strength.level >= 2 ? 'active' : ''}`} style={{ backgroundColor: strength.level >= 2 ? strength.color : '' }}></span>
              <span className={`bar ${strength.level >= 3 ? 'active' : ''}`} style={{ backgroundColor: strength.level >= 3 ? strength.color : '' }}></span>
            </div>
            <span className="strength-label" style={{ color: strength.color }}>{strength.label}</span>
          </div>
        )}
      </AuthField>

      <AuthField
        id="register-confirm"
        label="Confirmar contraseña"
        icon="lock"
        password
        name="password_confirmation"
        autoComplete="new-password"
        required
        placeholder="Escribe la misma clave"
        value={registerConfirmPassword}
        onChange={(e) => setRegisterConfirmPassword(e.target.value)}
      />

      <div className="input-group">
        <label htmlFor="register-scale">Escala de calificación (opcional)</label>
        <select id="register-scale" name="escala_calificacion" className="rating-select" defaultValue="">
          <option value="">Predeterminada (1 a 10 puntos)</option>
          <option value="10">1 a 10 puntos</option>
          <option value="5">5 estrellas (con medias)</option>
        </select>
      </div>

      <div className="terms-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            required
            checked={agreeTerms}
            onChange={(e) => setAgreeTerms(e.target.checked)}
          />
          <span className="custom-checkbox"></span>
          <span>
            Acepto los <a href="#terminos" onClick={(e) => e.preventDefault()}>Términos de servicio</a> y la <a href="#privacidad" onClick={(e) => e.preventDefault()}>Política de privacidad</a>
          </span>
        </label>
      </div>

      <button type="submit" className="submit-btn" disabled={isLoading}>
        {isLoading && <span className="submit-spinner" aria-hidden="true" />}
        {isLoading ? 'Creando cuenta...' : 'Crear cuenta'}
      </button>

      <p className="switch-text">
        ¿Ya tienes una cuenta?{' '}
        <button
          type="button"
          className="link-btn"
          onClick={onSwitchToLogin}
        >
          Inicia sesión
        </button>
      </p>
    </form>
  )
}

