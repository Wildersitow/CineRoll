import { useState } from 'react'

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
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Cálculo de fuerza de contraseña
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { level: 0, label: '', color: '' }
    if (pwd.length < MIN_PASSWORD_LENGTH) return { level: 1, label: 'Débil', color: '#ef4444' }
    if (pwd.length < 12 || /^\d+$/.test(pwd)) return { level: 2, label: 'Media', color: '#f59e0b' }
    return { level: 3, label: 'Segura', color: '#10b981' }
  }

  const strength = getPasswordStrength(registerPassword)

  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <div className="input-group">
        <label htmlFor="register-username">Nombre de usuario</label>
        <div className="input-field-wrapper">
          <span className="input-icon">
            <span style={{ fontWeight: 'bold', fontSize: '1rem', color: '#94a3b8' }}>@</span>
          </span>
          <input
            id="register-username"
            type="text"
            placeholder="ej. valeria_cine"
            value={registerUsername}
            onChange={(e) => setRegisterUsername(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-name">Nombre completo</label>
        <div className="input-field-wrapper">
          <span className="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </span>
          <input
            id="register-name"
            type="text"
            placeholder="Tu nombre y apellido"
            value={registerName}
            onChange={(e) => setRegisterName(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-email">Correo electrónico</label>
        <div className="input-field-wrapper">
          <span className="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
              <polyline points="22,6 12,13 2,6"></polyline>
            </svg>
          </span>
          <input
            id="register-email"
            type="email"
            required
            placeholder="ejemplo@cineroll.com"
            value={registerEmail}
            onChange={(e) => setRegisterEmail(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-password">Contraseña (mínimo 8 caracteres)</label>
        <div className="input-field-wrapper">
          <span className="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </span>
          <input
            id="register-password"
            type={showPassword ? 'text' : 'password'}
            required
            placeholder="Mínimo 8 caracteres"
            value={registerPassword}
            onChange={(e) => setRegisterPassword(e.target.value)}
          />
          <button
            type="button"
            className="toggle-password-btn"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
          >
            {showPassword ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            )}
          </button>
        </div>

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
      </div>

      <div className="input-group">
        <label htmlFor="register-confirm">Confirmar contraseña</label>
        <div className="input-field-wrapper">
          <span className="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
          </span>
          <input
            id="register-confirm"
            type={showConfirmPassword ? 'text' : 'password'}
            required
            placeholder="Repite tu contraseña"
            value={registerConfirmPassword}
            onChange={(e) => setRegisterConfirmPassword(e.target.value)}
          />
          <button
            type="button"
            className="toggle-password-btn"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            aria-label={showConfirmPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
          >
            {showConfirmPassword ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            )}
          </button>
        </div>
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
        {isLoading ? 'Creando cuenta...' : 'Crear Cuenta'}
      </button>

      <p className="switch-text">
        ¿Ya tienes una cuenta?{' '}
        <button
          type="button"
          className="link-btn"
          onClick={onSwitchToLogin}
        >
          Inicia sesión aquí
        </button>
      </p>
    </form>
  )
}

