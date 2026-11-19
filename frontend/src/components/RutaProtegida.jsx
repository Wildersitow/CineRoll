import { Navigate, Outlet, useLocation } from 'react-router-dom'

// Protege rutas que exigen sesión.
// Sin usuario: redirige a /acceso y recuerda a qué ruta se quería entrar.
// Con usuario: muestra children o, si es ruta padre, el Outlet.
export default function RutaProtegida({ usuario, children, redirigirA = '/acceso' }) {
  const location = useLocation()

  if (!usuario) {
    return <Navigate to={redirigirA} replace state={{ desde: location }} />
  }

  return children ?? <Outlet />
}
