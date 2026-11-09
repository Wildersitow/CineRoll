import { useState, useEffect } from 'react'
import './App.css'
import {
  loginUser,
  registerUser,
  logoutUser,
  getCurrentUser,
  clearStoredAuth,
  getStoredAuth,
  changePassword,
} from './services/api'

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredAuth())
  const [activeTab, setActiveTab] = useState('login') // 'login' | 'register'
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [toastNotice, setToastNotice] = useState('')
  const [authError, setAuthError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Estados para cambio de contraseña desde perfil
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false)
  const [currentPasswordInput, setCurrentPasswordInput] = useState('')
  const [newPasswordInput, setNewPasswordInput] = useState('')
  const [confirmNewPasswordInput, setConfirmNewPasswordInput] = useState('')
  const [passwordChangeStatus, setPasswordChangeStatus] = useState({ error: '', success: '', loading: false })

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Form states - Login
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  // Form states - Registro
  const [registerUsername, setRegisterUsername] = useState('')
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)

  // Limpieza de inputs
  const resetFormInputs = () => {
    setLoginEmail('')
    setLoginPassword('')
    setRegisterUsername('')
    setRegisterName('')
    setRegisterEmail('')
    setRegisterPassword('')
    setRegisterConfirmPassword('')
    setAgreeTerms(false)
    setAuthError('')
    setShowPassword(false)
    setShowConfirmPassword(false)
  }

  const resetPasswordChangeInputs = () => {
    setCurrentPasswordInput('')
    setNewPasswordInput('')
    setConfirmNewPasswordInput('')
    setPasswordChangeStatus({ error: '', success: '', loading: false })
  }

  const switchTab = (tab) => {
    resetFormInputs()
    setActiveTab(tab)
  }

  // Cálculo de fuerza de contraseña
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { level: 0, label: '', color: '' }
    if (pwd.length < 6) return { level: 1, label: 'Débil', color: '#ef4444' }
    if (pwd.length < 10) return { level: 2, label: 'Media', color: '#f59e0b' }
    return { level: 3, label: 'Segura', color: '#10b981' }
  }

  const strength = getPasswordStrength(registerPassword)

  const showToast = (message, duration = 3500) => {
    setToastNotice(message)
    setTimeout(() => setToastNotice(''), duration)
  }

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')

    try {
      const data = await loginUser(loginEmail.trim(), loginPassword, rememberMe)
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Bienvenido de vuelta, ${data.nombre || data.username}!`)
    } catch (err) {
      setAuthError(err.message || 'Error en las credenciales.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = async () => {
    setIsLoading(true)
    try {
      await logoutUser()
    } finally {
      resetFormInputs()
      resetPasswordChangeInputs()
      setShowChangePasswordModal(false)
      setActiveTab('login')
      setCurrentUser(null)
      setIsLoading(false)
      showToast('Sesión cerrada de forma segura.')
    }
  }

  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')

    if (registerPassword !== registerConfirmPassword) {
      setAuthError('Las contraseñas no coinciden.')
      setIsLoading(false)
      return
    }

    if (registerPassword.length < 6) {
      setAuthError('La contraseña debe tener al menos 6 caracteres.')
      setIsLoading(false)
      return
    }

    // Si el usuario no ingresó un username explícito, derivar del correo
    const derivedUsername = (
      registerUsername.trim() ||
      registerEmail.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '') ||
      'usuario'
    )

    // Separar nombre y apellido si se ingresó
    const partesNombre = registerName.trim().split(/\s+/)
    const firstName = partesNombre[0] || ''
    const lastName = partesNombre.slice(1).join(' ') || ''

    try {
      const data = await registerUser(
        {
          username: derivedUsername,
          email: registerEmail.trim(),
          password: registerPassword,
          first_name: firstName,
          last_name: lastName,
        },
        rememberMe
      )
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Cuenta creada con éxito! Bienvenido a CineRoll, ${data.nombre || data.username}.`)
    } catch (err) {
      setAuthError(err.message || 'Error al crear la cuenta.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePasswordSubmit = async (e) => {
    e.preventDefault()
    setPasswordChangeStatus({ error: '', success: '', loading: true })

    if (newPasswordInput !== confirmNewPasswordInput) {
      setPasswordChangeStatus({
        error: 'La nueva contraseña y su confirmación no coinciden.',
        success: '',
        loading: false,
      })
      return
    }

    try {
      const res = await changePassword(currentPasswordInput, newPasswordInput)
      setPasswordChangeStatus({
        error: '',
        success: res.mensaje || 'Contraseña actualizada exitosamente.',
        loading: false,
      })
      setCurrentPasswordInput('')
      setNewPasswordInput('')
      setConfirmNewPasswordInput('')
      showToast('Contraseña actualizada con éxito.')
      setTimeout(() => setShowChangePasswordModal(false), 2000)
    } catch (err) {
      setPasswordChangeStatus({
        error: err.message || 'Error al actualizar la contraseña.',
        success: '',
        loading: false,
      })
    }
  }

  if (currentUser) {
    return (
      <div className="authenticated-scene">
        {toastNotice && (
          <div className="toast-notification" role="status">
            <svg className="toast-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span>{toastNotice}</span>
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
              Hola, <strong>{currentUser.nombre || currentUser.username}</strong>
            </span>
            <button
              type="button"
              className="action-btn-secondary"
              onClick={() => {
                resetPasswordChangeInputs()
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
            <button id="btn-logout" type="button" className="action-btn-logout" onClick={handleLogout} disabled={isLoading}>
              {isLoading ? 'Cerrando...' : 'Cerrar Sesión'}
            </button>
          </div>
        </header>

        <main className="blank-scene-content" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
          {showChangePasswordModal && (
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
              <h3 style={{ color: '#ffffff', marginBottom: '1rem', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#e50914' }}>
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
                <div style={{ background: 'rgba(22, 101, 52, 0.3)', border: '1px solid #16a34a', color: '#86efac', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.88rem' }}>
                  <span>{passwordChangeStatus.success}</span>
                </div>
              )}

              <form onSubmit={handleChangePasswordSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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
                  <label htmlFor="new-pwd">Nueva contraseña (mínimo 6 caracteres)</label>
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
                    onClick={() => {
                      resetPasswordChangeInputs()
                      setShowChangePasswordModal(false)
                    }}
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
                <h2 style={{ color: '#ffffff', margin: 0, fontSize: '1.4rem' }}>{currentUser.nombre || currentUser.username}</h2>
                <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>@{currentUser.username} · {currentUser.email || 'Sin correo registrado'}</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Escala de Puntuación</span>
                <p style={{ color: '#f1f5f9', margin: '0.25rem 0 0 0', fontWeight: '600' }}>
                  {currentUser.escala_calificacion === 5 ? '⭐ 5 estrellas (con medias)' : '🔢 1 a 10 puntos'}
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                <span style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sesión Segura</span>
                <p style={{ color: '#10b981', margin: '0.25rem 0 0 0', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
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

  return (
    <div className="auth-wrapper">
      {toastNotice && (
        <div className="toast-notification" role="status">
          <svg className="toast-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span>{toastNotice}</span>
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
            onClick={() => switchTab('login')}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'register'}
            className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => switchTab('register')}
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
                  placeholder="ejemplo@cineroll.com o usuario"
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
              {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
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
                onClick={() => switchTab('register')}
              >
                Regístrate gratis
              </button>
            </p>
          </form>
        )}

        {/* Formulario de Registro */}
        {activeTab === 'register' && (
          <form className="auth-form" onSubmit={handleRegisterSubmit}>
            {authError && (
              <div className="auth-alert-error" role="alert">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span>{authError}</span>
              </div>
            )}

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
                onClick={() => switchTab('login')}
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
