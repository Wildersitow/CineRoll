import { NavLink, Outlet } from 'react-router-dom'

export default function MainLayout({ currentUser, onLogout, isLoading }) {
  return (
    <div className="authenticated-scene">
      <header className="scene-navbar">
        <NavLink to="/" className="scene-brand" aria-label="Ir al inicio">
          <div className="logo-badge-small" aria-hidden="true">
            <svg className="film-icon-small" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
              <line x1="7" y1="2" x2="7" y2="22" />
              <line x1="17" y1="2" x2="17" y2="22" />
              <line x1="2" y1="12" x2="22" y2="12" />
            </svg>
          </div>
          <span className="scene-title">Cine<span>Roll</span></span>
        </NavLink>

        <nav className="scene-main-nav" aria-label="Navegación principal">
          <NavLink to="/">Inicio</NavLink>
          <NavLink to="/cines">Cines</NavLink>
          {currentUser && <NavLink to="/perfil">Perfil</NavLink>}
          {!currentUser && <NavLink to="/acceso">Acceso</NavLink>}
        </nav>

        {currentUser && (
          <div className="scene-user-actions">
            <span className="scene-user-greeting">
              Hola, <strong>{currentUser.nombre || currentUser.username}</strong>
            </span>
            <button
              id="btn-logout"
              type="button"
              className="action-btn-logout"
              onClick={onLogout}
              disabled={isLoading}
            >
              {isLoading ? 'Cerrando...' : 'Cerrar Sesión'}
            </button>
          </div>
        )}
      </header>

      <div className="blank-scene-content">
        <Outlet />
      </div>
    </div>
  )
}
