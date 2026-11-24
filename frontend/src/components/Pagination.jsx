import CinemaIcon from './CinemaIcon'

/** Paginación estilo shadcn: Anterior · 1 … 4 5 6 … 12 · Siguiente. */
export default function Pagination({ page, count, change }) {
  const total = Math.ceil(count / 20)
  if (total < 2) return null
  const numbers = [...new Set([1, page - 1, page, page + 1, total])].filter(n => n >= 1 && n <= total).sort((a, b) => a - b)
  return <nav className="cinema-pagination" aria-label="Paginación">
    <button disabled={page <= 1} onClick={() => change(page - 1)}><CinemaIcon name="left" /> Anterior</button>
    {numbers.map((n, i) => <span className="page-number" key={n}>
      {i > 0 && n - numbers[i - 1] > 1 && <span className="page-ellipsis" aria-hidden="true">…</span>}
      <button aria-current={page === n ? 'page' : undefined} aria-label={`Página ${n}`} onClick={() => change(n)}>{n}</button>
    </span>)}
    <span className="page-compact">Página {page} de {total}</span>
    <button disabled={page >= total} onClick={() => change(page + 1)}>Siguiente <CinemaIcon name="right" /></button>
  </nav>
}
