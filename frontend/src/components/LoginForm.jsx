import SmoothInput from './SmoothInput'
import { useState } from 'react'

export default function LoginForm({
  loginEmail,
  setLoginEmail,
  loginPassword,
  setLoginPassword,
  rememberMe,
  setRememberMe,
  isLoading,
  onSubmit,
  onSwitchToRegister,
}) {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <div className="input-group">
        <label htmlFor="login-email">Correo electrónico o usuario</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="login-email"
            name="username"
            autoCapitalize="none"
            type="text"
            autoComplete="username"
            required
            placeholder="valeria@ejemplo.com o valeria_cine"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
          />
        </div>
      </div>

      <div className="input-group">
        <label htmlFor="login-password">Contraseña</label>
        <div className="input-field-wrapper">
          <SmoothInput
            id="login-password"
            name="password"
            autoComplete="current-password"
            type={showPassword ? 'text' : 'password'}
            required
            placeholder="Escribe tu clave"
            value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
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
      </div>

      <div className="form-meta-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
          />
          <span className="custom-checkbox"></span>
          <span>Recordarme</span>
        </label>
      </div>

      <button type="submit" className="submit-btn" disabled={isLoading}>
        {isLoading ? 'Iniciando sesión...' : 'Iniciar sesión'}
      </button>

      <p className="switch-text">
        ¿No tienes una cuenta?{' '}
        <button
          type="button"
          className="link-btn"
          onClick={onSwitchToRegister}
        >
          Crea una cuenta
        </button>
      </p>
    </form>
  )
}

