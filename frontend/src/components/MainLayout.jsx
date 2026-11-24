import { useLayoutEffect } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { Link, useLocation, useNavigate, useOutlet } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'
import SiteFooter from './SiteFooter'
import UserMenu from './UserMenu'
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

function NavGroup({ label, links, pathname, search }) {
  return (
    <div className="cinema-nav-group" role="group" aria-label={label}>
      <span className="cinema-nav-label" aria-hidden="true">{label}</span>
      {links.map(({ path, label, icon }) => {
        const active = path === pathname + search || (pathname !== '/' && path === pathname)
        return (
          <Link key={path} to={path} aria-current={active ? 'page' : undefined}>
            <CinemaIcon name={icon} weight={active ? 'fill' : 'regular'} />
            {label}
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
          <input type="search" name="q" defaultValue={query} placeholder="Buscar en el catálogo" aria-label="Buscar en el catálogo" />
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
          <NavGroup label="Explorar" links={cinemaLinks} pathname={pathname} search={search} />
          <NavGroup label="Cartelera" links={billboardLinks} pathname={pathname} search={search} />
        </nav>
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
