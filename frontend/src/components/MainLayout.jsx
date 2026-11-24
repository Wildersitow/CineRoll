import { useLayoutEffect } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { Link, useLocation, useNavigate, useOutlet } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'
import SiteFooter from './SiteFooter'
import UserMenu from './UserMenu'
import { activePath } from '../utils/navegacion'
import './Cinema.css'

// Películas, Series y Anime se filtran desde el propio Catálogo, así que la
// barra lateral solo lleva las secciones principales.
const cinemaLinks = [
  { path: '/', label: 'Inicio', icon: 'home' },
  { path: '/catalogo', label: 'Catálogo', icon: 'film' },
  { path: '/cines', label: 'Cines', icon: 'pin' },
]

const billboardLinks = [
  { path: '/catalogo?estado=proximo_estreno', label: 'Estrenos', icon: 'clock' },
]

function accountLinks(user) {
  return [
    { path: `/usuarios/${encodeURIComponent(user.username)}`, label: 'Mi perfil', icon: 'user' },
    { path: '/mensajes', label: 'Mensajes', icon: 'chat' },
    { path: '/perfil', label: 'Ajustes', icon: 'settings' },
  ]
}

function NavGroup({ label, links, active, reduceMotion }) {
  return (
    <div className="cinema-nav-group" role="group" aria-label={label}>
      <span className="cinema-nav-label" aria-hidden="true">{label}</span>
      {links.map(({ path, label, icon }) => {
        const isActive = path === active
        return (
          <Link key={path} to={path} aria-current={isActive ? 'page' : undefined}>
            {isActive && (
              <motion.span
                layoutId="cinema-nav-activo"
                className="cinema-nav-indicator"
                aria-hidden="true"
                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 520, damping: 40 }}
              />
            )}
            <span className="cinema-nav-icon"><CinemaIcon name={icon} weight={isActive ? 'fill' : 'regular'} /></span>
            <span className="cinema-nav-text">{label}</span>
          </Link>
        )
      })}
    </div>
  )
}

export default function MainLayout({ currentUser, onLogout, isLoading }) {
  const { pathname, search } = useLocation()
  const navigate = useNavigate()
  const outlet = useOutlet()
  const reduceMotion = useReducedMotion()
  const query = new URLSearchParams(search).get('q') || ''
  const searchFieldKey = pathname + search
  const allLinks = [...cinemaLinks, ...billboardLinks, ...(currentUser ? accountLinks(currentUser) : [])]
  const active = activePath(allLinks.map(({ path }) => path), pathname, search)
  useLayoutEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  function submitSearch(event) {
    event.preventDefault()
    const term = new FormData(event.currentTarget).get('q').trim()
    navigate(term ? `/catalogo?${new URLSearchParams({ q: term })}` : '/')
  }

  return (
    <div className="cinema-shell">
      <a className="cinema-skip" href="#contenido">Saltar al contenido</a>
      <header className="cinema-header">
        <Link to="/" className="cinema-brand" aria-label="CineRoll">
          <span className="cinema-brand-symbol" aria-hidden="true" />
          <span className="cinema-brand-wordmark" aria-hidden="true" />
        </Link>
        <form key={searchFieldKey} onSubmit={submitSearch} role="search" className="cinema-search">
          <input type="search" name="q" defaultValue={query} placeholder="Buscar títulos o personas" aria-label="Buscar títulos o personas" />
          <button type="submit" aria-label="Buscar"><CinemaIcon name="search" /></button>
        </form>
        <div className="cinema-account">
          {currentUser ? (
            <UserMenu user={currentUser} onLogout={onLogout} isLoading={isLoading} />
          ) : (
            <Link to="/acceso" aria-current={pathname === '/acceso' ? 'page' : undefined}>
              <CinemaIcon name="user" weight={pathname === '/acceso' ? 'fill' : 'regular'} /><span>Ingresar</span>
            </Link>
          )}
        </div>
      </header>
      <aside className="cinema-sidebar">
        <nav aria-label="Navegación principal">
          <NavGroup label="Explorar" links={cinemaLinks} active={active} reduceMotion={reduceMotion} />
          <NavGroup label="Cartelera" links={billboardLinks} active={active} reduceMotion={reduceMotion} />
          {currentUser && <NavGroup label="Tu espacio" links={accountLinks(currentUser)} active={active} reduceMotion={reduceMotion} />}
        </nav>
        {!currentUser && pathname !== '/acceso' && (
          <div className="cinema-sidebar-cta">
            <p>Reseña lo que ves, arma listas y sigue a otros cinéfilos.</p>
            <Link to="/acceso">Crear cuenta</Link>
          </div>
        )}
      </aside>
      <div className="cinema-content" id="contenido" tabIndex={-1}>
        <motion.div
          key={pathname}
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.18, ease: 'easeOut' }}
        >
          {outlet}
        </motion.div>
        <SiteFooter user={currentUser} />
      </div>
    </div>
  )
}
