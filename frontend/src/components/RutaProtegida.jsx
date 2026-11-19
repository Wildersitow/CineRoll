import { Navigate, useLocation } from 'react-router-dom'

export default function RutaProtegida({ currentUser, children }) {
  const location = useLocation()

  if (!currentUser) {
    return <Navigate to="/acceso" replace state={{ from: location.pathname }} />
  }

  return children
}
