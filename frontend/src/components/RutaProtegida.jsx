import { Navigate, Outlet, useLocation } from 'react-router-dom'

/**
 * Protege rutas que exigen sesión.
 * - Sin usuario: redirige a /acceso y recuerda a qué ruta quería entrar.
 * - Con usuario: muestra `children` o, si se usa como ruta padre, el <Outlet />.
 */
export default function RutaProtegida({ usuario, children, redirigirA = '/acceso' }) {
  const location = useLocation()

  if (!usuario) {
    return <Navigate to={redirigirA} replace state={{ desde: location }} />
  }

  return children ?? <Outlet />
}