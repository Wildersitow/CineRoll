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
  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        {/* Encabezado con Logo CineRoll */}
        <div className="brand-header">
          <div className="logo-badge">
            <svg
              className="film-icon"
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
          <h1 className="brand-title">
            Cine<span>Roll</span>
          </h1>
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
            onClick={() => onSwitchTab('login')}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'register'}
            className={`tab-btn ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => onSwitchTab('register')}
          >
            Registrarse
          </button>
        </div>

        {authError && (
          <div className="auth-alert-error" role="alert">
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
  )
}

