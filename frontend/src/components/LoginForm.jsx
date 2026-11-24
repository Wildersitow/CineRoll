import AuthField from './AuthField'

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
  return (
    <form className="auth-form" onSubmit={onSubmit} aria-busy={isLoading}>
      <AuthField
        id="login-email"
        label="Correo electrónico o usuario"
        icon="at"
        name="username"
        autoCapitalize="none"
        type="text"
        autoComplete="username"
        required
        placeholder="valeria@ejemplo.com o valeria_cine"
        value={loginEmail}
        onChange={(e) => setLoginEmail(e.target.value)}
      />

      <AuthField
        id="login-password"
        label="Contraseña"
        icon="lock"
        password
        name="password"
        autoComplete="current-password"
        required
        placeholder="Escribe tu clave"
        value={loginPassword}
        onChange={(e) => setLoginPassword(e.target.value)}
      />

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
        {isLoading && <span className="submit-spinner" aria-hidden="true" />}
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
