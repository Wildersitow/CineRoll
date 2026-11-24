import { useEffect, useId, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Link, useLocation } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'

/**
 * Avatar del usuario en la barra superior. Al hacer clic abre un menú con los
 * accesos de la cuenta (perfil, mensajes, configuración, cerrar sesión).
 * Se cierra con Escape, al hacer clic fuera o al navegar a otra página.
 */
export default function UserMenu({ user, onLogout, isLoading }) {
  const [open, setOpen] = useState(false)
  const [failedAvatar, setFailedAvatar] = useState(null)
  const root = useRef(null)
  const trigger = useRef(null)
  const menuId = useId()
  const { pathname, search } = useLocation()
  const reduceMotion = useReducedMotion()

  // Cerrar al cambiar de página.
  const [lastPath, setLastPath] = useState(pathname + search)
  if (lastPath !== pathname + search) {
    setLastPath(pathname + search)
    setOpen(false)
  }

  useEffect(() => {
    if (!open) return
    function onPointerDown(event) {
      if (!root.current?.contains(event.target)) setOpen(false)
    }
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        trigger.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const name = user.nombre || user.username
  const initial = (name || 'U').charAt(0).toUpperCase()
  const avatar = user.avatar && user.avatar !== failedAvatar ? (
    <img src={user.avatar} alt="" onError={() => setFailedAvatar(user.avatar)} />
  ) : <span aria-hidden="true">{initial}</span>

  const perfil = `/usuarios/${encodeURIComponent(user.username)}`
  const links = [
    { to: perfil, label: 'Mi perfil', icon: 'user' },
    { to: `${perfil}?tab=listas`, label: 'Mis listas', icon: 'list' },
    { to: `${perfil}?tab=red`, label: 'Amigos', icon: 'users' },
    { to: '/mensajes', label: 'Mensajes', icon: 'chat' },
    { to: '/perfil', label: 'Configuración', icon: 'settings' },
  ]

  return (
    <div className="cinema-user-menu" ref={root}>
      <button
        ref={trigger}
        type="button"
        className="cinema-user-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Menú de ${name}`}
        onClick={() => setOpen(!open)}
      >
        <span className="cinema-user-avatar">{avatar}</span>
        <CinemaIcon name="caretDown" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={menuId}
            role="menu"
            aria-label="Cuenta"
            className="cinema-user-dropdown"
            initial={reduceMotion ? false : { opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.14, ease: 'easeOut' }}
          >
            <div className="cinema-user-summary">
              <span className="cinema-user-avatar">{avatar}</span>
              <div>
                <strong>{name}</strong>
                <small>@{user.username}</small>
              </div>
            </div>
            {links.map(({ to, label, icon }) => (
              <Link key={to} to={to} role="menuitem" aria-current={pathname + search === to ? 'page' : undefined}>
                <CinemaIcon name={icon} /> {label}
              </Link>
            ))}
            <button type="button" role="menuitem" className="cinema-user-logout" onClick={onLogout} disabled={isLoading}>
              <CinemaIcon name="signOut" /> {isLoading ? 'Cerrando…' : 'Cerrar sesión'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
