import { useState, useEffect } from 'react'
import './App.css'
import { loginUser, getCurrentUser, clearStoredAuth, getStoredAuth } from './services/api'


export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredAuth())
  const [activeTab, setActiveTab] = useState('login') // 'login' | 'register'
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [demoNotice, setDemoNotice] = useState('')
  const [authError, setAuthError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Validar sesión activa al cargar la app
  useEffect(() => {
    if (currentUser?.token) {
      getCurrentUser()
        .then((userData) => {
          setCurrentUser((prev) => ({ ...prev, ...userData }))
        })
        .catch(() => {
          // Token expirado o revocado
          setCurrentUser(null)
          clearStoredAuth()
        })
    }
  }, [])

  // Form states
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)

  // Password strength calculation
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { level: 0, label: '', color: '' }
    if (pwd.length < 6) return { level: 1, label: 'Débil', color: '#ef4444' }
    if (pwd.length < 10) return { level: 2, label: 'Media', color: '#f59e0b' }
    return { level: 3, label: 'Segura', color: '#10b981' }
  }

  const strength = getPasswordStrength(registerPassword)

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')

    try {
      const data = await loginUser(loginEmail, loginPassword)
      setCurrentUser(data)
      setDemoNotice(`¡Bienvenido, ${data.nombre}!`)
      setTimeout(() => setDemoNotice(''), 3500)
    } catch (err) {
      setAuthError(err.message || 'Error en las credenciales.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    setCurrentUser(null)
    clearStoredAuth()
    setDemoNotice('Sesión cerrada')
    setTimeout(() => setDemoNotice(''), 2500)
  }

  const handleRegisterSubmit = (e) => {
    e.preventDefault()
    setDemoNotice('¡Cuenta creada con éxito! (Modo presentación)')
    setTimeout(() => setDemoNotice(''), 3500)
  }

  if (currentUser) {
    return (
      <div className="authenticated-scene">
        {demoNotice && (
          <div className="toast-notification" role="status">
            <svg className="toast-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>{demoNotice}</span>
          </div>
        )}

        <header className="scene-navbar">
          <div className="scene-brand">
            <div className="logo-badge-small">
              <svg className="film-icon-small" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
            <span className="scene-title">Cine<span>Roll</span></span>
          </div>

          <div className="scene-user-actions">
            <span className="scene-user-greeting">
              Hola, <strong>{currentUser.nombre || currentUser.email}</strong>
            </span>
            <button id="btn-logout" type="button" className="action-btn-logout" onClick={handleLogout}>
              Cerrar Sesión
            </button>
          </div>
        </header>

        {/* Escena en blanco tras login */}
        <main className="blank-scene-content">
        </main>
      </div>
    )
  }

  return (
    <div className="auth-wrapper">
      {/* Notificación flotante de demo */}
      {demoNotice && (
        <div className="toast-notification" role="status">
          <svg className="toast-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span>{demoNotice}</span>
        </div>
      )}

      <div className="auth-card">
        {/* Encabezado con Logo CineRoll */}
        <div className="brand-header">
          <div className="logo-badge">
            <svg className="film-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
          <h1 className="brand-title">Cine<span>Roll</span></h1>
          <p className="brand-subtitle">
            {activeTab === 'login'
              ? 'Bienvenido de vuelta a tu cine en casa'
              : 'Únete para disfrutar de tus películas favoritas'}
          </p>
        </div>

        {/* Selector de pestañas: Iniciar sesión / Registro */}
        <div className="tab-control" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'login'}
                className={`tab-btn ${activeTab === 'login' ? 'active' : ''}`}
                onClick={() => setActiveTab('login')}
              >
                Iniciar Sesión
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'register'}
                className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
                onClick={() => setActiveTab('register')}
              >
                Registrarse
              </button>
            </div>

            {/* Formulario de Login */}
            {activeTab === 'login' && (
              <form className="auth-form" onSubmit={handleLoginSubmit}>
                {authError && (
                  <div className="auth-alert-error" role="alert">
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span>{authError}</span>
                  </div>
                )}

                <div className="auth-hint-banner">
                  <span>💡 <strong>Demo backend:</strong> victor / 12345</span>
                  <button
                    type="button"
                    onClick={() => {
                      setLoginEmail('victor')
                      setLoginPassword('12345')
                      setAuthError('')
                    }}
                  >
                    Rellenar
                  </button>
                </div>

                <div className="input-group">
                  <label htmlFor="login-email">Correo electrónico o usuario</label>
                  <div className="input-field-wrapper">
                    <span className="input-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                        <polyline points="22,6 12,13 2,6"></polyline>
                      </svg>
                    </span>
                    <input
                      id="login-email"
                      type="text"
                      autoComplete="username"
                      required
                      placeholder="victor o ejemplo@cineroll.com"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                    />
                  </div>
                </div>

                <div className="input-group">
                  <label htmlFor="login-password">Contraseña</label>
                  <div className="input-field-wrapper">
                    <span className="input-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                      </svg>
                    </span>
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••"
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
                  <a href="#olvide-contrasena" className="forgot-link" onClick={(e) => e.preventDefault()}>
                    ¿Olvidaste tu contraseña?
                  </a>
                </div>

                <button type="submit" className="submit-btn" disabled={isLoading}>
                  {isLoading ? 'Conectando con App.js...' : 'Iniciar Sesión'}
                </button>

                <div className="divider">
                  <span>o continúa con</span>
                </div>

                <div className="social-grid">
                  <button type="button" className="social-btn">
                    <svg className="social-icon" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                    </svg>
                    <span>Google</span>
                  </button>
                  <button type="button" className="social-btn">
                    <svg className="social-icon" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.1c.67-.82 1.13-1.96 1-3.1-.97.04-2.15.65-2.85 1.47-.62.72-1.16 1.88-1.02 3 .01 0 .04 0 .07 0 1.01 0 2.12-.55 2.8-1.37z" />
                    </svg>
                    <span>Apple</span>
                  </button>
                </div>

                <p className="switch-text">
                  ¿No tienes una cuenta?{' '}
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => setActiveTab('register')}
                  >
                    Regístrate gratis
                  </button>
                </p>
              </form>
            )}

        {/* Formulario de Registro */}
        {activeTab === 'register' && (
          <form className="auth-form" onSubmit={handleRegisterSubmit}>
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
                  required
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
              <label htmlFor="register-password">Contraseña</label>
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
                  placeholder="Mínimo 6 caracteres"
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

              {/* Indicador sutil de fuerza de contraseña */}
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

            <button type="submit" className="submit-btn">
              Crear Cuenta
            </button>

            <div className="divider">
              <span>o regístrate con</span>
            </div>

            <div className="social-grid">
              <button type="button" className="social-btn">
                <svg className="social-icon" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>Google</span>
              </button>
              <button type="button" className="social-btn">
                <svg className="social-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.1c.67-.82 1.13-1.96 1-3.1-.97.04-2.15.65-2.85 1.47-.62.72-1.16 1.88-1.02 3 .01 0 .04 0 .07 0 1.01 0 2.12-.55 2.8-1.37z" />
                </svg>
                <span>Apple</span>
              </button>
            </div>

            <p className="switch-text">
              ¿Ya tienes una cuenta?{' '}
              <button
                type="button"
                className="link-btn"
                onClick={() => setActiveTab('login')}
              >
                Inicia sesión aquí
              </button>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
