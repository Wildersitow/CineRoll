import LoginForm from './LoginForm'
import RegisterForm from './RegisterForm'

export default function AuthCard({
  activeTab,
  onSwitchTab,
  authError,
  isLoading,
  // Login props
  loginEmail,
  setLoginEmail,
  loginPassword,
  setLoginPassword,
  rememberMe,
  setRememberMe,
  onLoginSubmit,
  // Register props
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
  onRegisterSubmit,
}) {
  function handleTabKey(event) {
    const first = event.key === 'Home'
    const last = event.key === 'End'
    const arrow = event.key === 'ArrowLeft' || event.key === 'ArrowRight'
    if (!first && !last && !arrow) return

    event.preventDefault()
    const next = first || (arrow && activeTab === 'register') ? 'login' : 'register'
    if (next === activeTab) return
    event.currentTarget.querySelector(`#auth-${next}-tab`).focus()
    onSwitchTab(next)
  }

  return (
    <main className="auth-wrapper">
      <div className="auth-card">
        <header className="brand-header">
          <span className="cinema-brand-symbol" aria-hidden="true" />
          <h1 className="brand-title">{activeTab === 'login' ? 'Inicia sesión' : 'Crea tu cuenta'}</h1>
        </header>

        <div className="tab-control" role="tablist" aria-label="Acceso a CineRoll" onKeyDown={handleTabKey}>
          <button
            id="auth-login-tab"
            type="button"
            role="tab"
            aria-controls="auth-panel"
            aria-selected={activeTab === 'login'}
            tabIndex={activeTab === 'login' ? 0 : -1}
            className="tab-btn"
            onClick={() => onSwitchTab('login')}
          >
            Iniciar sesión
          </button>
          <button
            id="auth-register-tab"
            type="button"
            role="tab"
            aria-controls="auth-panel"
            aria-selected={activeTab === 'register'}
            tabIndex={activeTab === 'register' ? 0 : -1}
            className="tab-btn"
            onClick={() => onSwitchTab('register')}
          >
            Registrarse
          </button>
        </div>

        <div id="auth-panel" role="tabpanel" aria-labelledby={`auth-${activeTab}-tab`}>
          {authError && (
            <div key={authError} className="auth-alert-error" role="alert">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <span>{authError}</span>
            </div>
          )}

          {activeTab === 'login' ? (
            <LoginForm
              loginEmail={loginEmail}
              setLoginEmail={setLoginEmail}
              loginPassword={loginPassword}
              setLoginPassword={setLoginPassword}
              rememberMe={rememberMe}
              setRememberMe={setRememberMe}
              isLoading={isLoading}
              onSubmit={onLoginSubmit}
              onSwitchToRegister={() => onSwitchTab('register')}
            />
          ) : (
            <RegisterForm
              registerUsername={registerUsername}
              setRegisterUsername={setRegisterUsername}
              registerName={registerName}
              setRegisterName={setRegisterName}
              registerEmail={registerEmail}
              setRegisterEmail={setRegisterEmail}
              registerPassword={registerPassword}
              setRegisterPassword={setRegisterPassword}
              registerConfirmPassword={registerConfirmPassword}
              setRegisterConfirmPassword={setRegisterConfirmPassword}
              agreeTerms={agreeTerms}
              setAgreeTerms={setAgreeTerms}
              isLoading={isLoading}
              onSubmit={onRegisterSubmit}
              onSwitchToLogin={() => onSwitchTab('login')}
            />
          )}
        </div>
      </div>
    </main>
  )
}

