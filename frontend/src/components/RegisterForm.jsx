import SmoothInput from './SmoothInput'
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
        <label htmlFor="register-username">Nombre de usuario (opcional)</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="register-username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            type="text"
            placeholder="valeria_cine"
            value={registerUsername}
            onChange={(e) => setRegisterUsername(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-name">Nombre completo</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="register-name"
            name="name"
            autoComplete="name"
            type="text"
            placeholder="Valeria Torres"
            value={registerName}
            onChange={(e) => setRegisterName(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-email">Correo electrónico</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="register-email"
            name="email"
            autoComplete="email"
            autoCapitalize="none"
            type="email"
            required
            placeholder="valeria@ejemplo.com"
            value={registerEmail}
            onChange={(e) => setRegisterEmail(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="register-password">Contraseña</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="register-password"
            name="password"
            autoComplete="new-password"
            aria-describedby="register-password-hint"
            type={showPassword ? 'text' : 'password'}
            required
            placeholder="Crea una clave"
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
      </div>

      <div className="input-group">
        <label htmlFor="register-confirm">Confirmar contraseña</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="register-confirm"
            name="password_confirmation"
            autoComplete="new-password"
            type={showConfirmPassword ? 'text' : 'password'}
            required
            placeholder="Escribe la misma clave"
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

