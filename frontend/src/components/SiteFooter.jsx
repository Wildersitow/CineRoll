import { Link } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'

const explorar = [
  { to: '/', label: 'Inicio' },
  { to: '/catalogo', label: 'Catálogo' },
  { to: '/cines', label: 'Cines de Valledupar' },
  { to: '/catalogo?estado=proximo_estreno', label: 'Próximos estrenos' },
]

const catalogo = [
  { to: '/catalogo?tipo=pelicula', label: 'Películas' },
  { to: '/catalogo?tipo=serie', label: 'Series' },
  { to: '/catalogo?tipo=anime', label: 'Anime' },
]

function enlacesCuenta(user) {
  if (!user) return [{ to: '/acceso', label: 'Ingresar o crear cuenta' }]
  const perfil = `/usuarios/${encodeURIComponent(user.username)}`
  return [
    { to: perfil, label: 'Mi perfil' },
    { to: `${perfil}?tab=listas`, label: 'Mis listas' },
    { to: '/mensajes', label: 'Mensajes' },
    { to: '/perfil', label: 'Configuración' },
  ]
}

function Columna({ titulo, enlaces }) {
  return (
    <div className="site-footer-col">
      <h2>{titulo}</h2>
      <ul>
        {enlaces.map(({ to, label }) => <li key={to}><Link to={to}>{label}</Link></li>)}
      </ul>
    </div>
  )
}

/*
 * Pie de página con efecto "reveal": queda fijo detrás del contenido y se
 * descubre al llegar al final de la página (ver .site-footer en Cinema.css).
 */
export default function SiteFooter({ user }) {
  function subir() {
    const suave = !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: suave ? 'smooth' : 'auto' })
    document.getElementById('contenido')?.focus({ preventScroll: true })
  }

  return (
    <footer className="site-footer">
      <div className="site-footer-top">
        <div className="site-footer-brand">
          <Link to="/" className="cinema-brand" aria-label="CineRoll, ir al inicio">
            <span className="cinema-brand-symbol" aria-hidden="true" />
            <span className="cinema-brand-wordmark" aria-hidden="true" />
          </Link>
          <p>La cartelera de Valledupar y tu diario de cine, series y anime en un solo lugar.</p>
        </div>
        <nav className="site-footer-links" aria-label="Pie de página">
          <Columna titulo="Explorar" enlaces={explorar} />
          <Columna titulo="Catálogo" enlaces={catalogo} />
          <Columna titulo="Tu cuenta" enlaces={enlacesCuenta(user)} />
        </nav>
      </div>
      <p className="site-footer-wordmark" aria-hidden="true">CineRoll</p>
      <div className="site-footer-bottom">
        <small>© {new Date().getFullYear()} CineRoll. Los horarios pueden cambiar; confírmalos con cada cine.</small>
        <button type="button" className="site-footer-top-btn" onClick={subir}>
          Volver arriba <CinemaIcon name="up" />
        </button>
      </div>
    </footer>
  )
}
