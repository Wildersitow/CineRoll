/*
 * Ruta activa: si algún enlace coincide exacto (con su ?query), solo ese; si no,
 * el que coincide por ruta. Así "Estrenos" no marca también "Catálogo".
 */
export function activePath(paths, pathname, search) {
  const exact = paths.find(path => path === pathname + search)
  if (exact) return exact
  return paths.find(path => !path.includes('?') && path !== '/' && pathname.startsWith(path) &&
    (pathname.length === path.length || pathname[path.length] === '/')) ?? (pathname === '/' ? '/' : null)
}
