import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getMedia } from '../services/api'
import CinemaState from './CinemaState'
import CinemaIcon from './CinemaIcon'
import FilmCard from './FilmCard'
import Pagination from './Pagination'
import CurtainOpening from './CurtainOpening'

const filters = { pelicula: 'Películas', serie: 'Series', anime: 'Anime' }

function useMedia(params, page) {
  const key = JSON.stringify({ ...params, page })
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getMedia(JSON.parse(key), { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, attempt, data })
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ key, attempt, error })
      })
    return () => controller.abort()
  }, [key, attempt])

  const current = result?.key === key && result.attempt === attempt ? result : null
  return { ...current, retry: () => setAttempt((value) => value + 1), loading: !current }
}

const hora = new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota', timeStyle: 'short' })

function Showtimes({ shows }) {
  const byCinema = Map.groupBy(shows, show => show.cine.id)
  return [...byCinema].map(([id, items]) => (
    <div className="film-times" key={id}>
      <strong>{items[0].cine.nombre}</strong>
      <p>{[...new Set(items.map(show => hora.format(new Date(show.fecha_hora))))].join(' · ')}</p>
    </div>
  ))
}

export function MediaSection({ id, title, params, carousel = false, empty, detailSearch }) {
  const [query, setQuery] = useSearchParams()
  const page = carousel ? 1 : Math.max(1, Number(query.get('page')) || 1)
  function setPage(value) {
    const next = new URLSearchParams(query)
    next.set('page', value)
    setQuery(next)
  }
  const { data, error, retry, loading } = useMedia(params, page)
  const rail = useRef(null)
  const [edges, setEdges] = useState({ start: true, end: true })
  const titles = data?.results || []

  useEffect(() => {
    const element = rail.current
    if (!element || !carousel) return
    function updateEdges() {
      setEdges({
        start: element.scrollLeft < 2,
        end: element.scrollLeft + element.clientWidth >= element.scrollWidth - 2,
      })
    }
    const frame = requestAnimationFrame(updateEdges)
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateEdges)
    observer?.observe(element)
    element.addEventListener('scroll', updateEdges, { passive: true })
    return () => {
      cancelAnimationFrame(frame)
      observer?.disconnect()
      element.removeEventListener('scroll', updateEdges)
    }
  }, [carousel, data, loading])

  useEffect(() => {
    const element = rail.current
    if (!element || loading || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver((entries) => {
      for (const { target, isIntersecting } of entries) {
        if (!isIntersecting) continue
        target.classList.add('cinema-revealed')
        observer.unobserve(target)
      }
    })
    for (const item of element.children) observer.observe(item)
    return () => observer.disconnect()
  }, [data, loading])

  function move(direction) {
    const element = rail.current
    const last = element.scrollWidth - element.clientWidth
    const target = element.scrollLeft + direction * element.clientWidth
    element.scrollTo({ left: Math.min(last, Math.max(0, target)) })
  }

  return (
    <section className="cinema-section" id={id} aria-labelledby={`${id}-title`}>
      <div className="cinema-section-heading">
        <h2 id={`${id}-title`}>{title}</h2>
        {carousel && !loading && titles.length > 1 && (
          <div className="cinema-arrows">
            <button type="button" aria-label={`Anterior en ${title}`} aria-controls={`${id}-row`} disabled={edges.start} onClick={() => move(-1)}><CinemaIcon name="left" /></button>
            <button type="button" aria-label={`Siguiente en ${title}`} aria-controls={`${id}-row`} disabled={edges.end} onClick={() => move(1)}><CinemaIcon name="right" /></button>
          </div>
        )}
      </div>
      {loading && <span className="cinema-visually-hidden" role="status">Cargando {title.toLowerCase()}…</span>}
      {error && <CinemaState error={error} title="No pudimos cargar los títulos." retry={retry} />}
      {!loading && !error && !titles.length && <p className="cinema-state">{empty}</p>}
      {(loading || titles.length > 0) && (
        <ul className={carousel ? 'cinema-rail' : 'cinema-grid'} ref={rail} id={`${id}-row`} aria-hidden={loading || undefined}>
          {loading
            ? Array.from({ length: 6 }, (_, index) => <li className="cinema-skeleton" key={index} style={{ '--skeleton-delay': `${index * 90}ms` }}><div className="cinema-poster" /><span /><span /></li>)
            : titles.map(media => (
              <li key={media.id}>
                <FilmCard media={media} search={detailSearch} />
                {media.funciones && <Showtimes shows={media.funciones} />}
              </li>
            ))}
        </ul>
      )}
      {!carousel && <Pagination page={page} count={data?.count || 0} change={setPage} />}
    </section>
  )
}

export default function CatalogView() {
  const [query] = useSearchParams()
  const search = query.get('q')?.trim()
  const type = Object.hasOwn(filters, query.get('tipo')) ? query.get('tipo') : undefined
  const state = query.get('estado') === 'proximo_estreno' ? 'proximo_estreno' : undefined
  const filtered = search || type || state
  const title = search ? `Resultados para “${search}”` : filters[type] || 'Próximos estrenos'

  if (filtered) {
    return (
      <main className="cinema-page cinema-catalog">
        <h1>{title}</h1>
        <MediaSection key={query.toString()} id="resultados" title="Títulos" params={{ search, tipo: type, estado: state, ordering: state ? 'fecha_estreno' : 'titulo' }} empty="No encontramos títulos para esta selección." />
      </main>
    )
  }

  return (
    <main className="cinema-page">
      <CurtainOpening />
      <section className="cinema-hero" aria-labelledby="cinema-title">
        <div className="cinema-hero-copy">
          <span className="cinema-hero-label">Cartelera local</span>
          <h1 id="cinema-title">Se abre<br />el telón<span>.</span></h1>
          <p>Encuentra qué ver en los cines de tu ciudad y descubre los próximos estrenos.</p>
          <div className="cinema-hero-actions">
            <a className="cinema-primary" href="#en-cartelera">Ver cartelera <CinemaIcon name="down" /></a>
            <Link className="cinema-secondary" to="/cines"><CinemaIcon name="ticket" /> Buscar funciones</Link>
          </div>
        </div>
      </section>
      <MediaSection id="en-cartelera" title="En cartelera" params={{ estado: 'en_cartelera', ordering: '-fecha_estreno' }} carousel empty="Aún no hay títulos en cartelera." />
      <MediaSection id="proximos" title="Próximos estrenos" params={{ estado: 'proximo_estreno', ordering: 'fecha_estreno' }} carousel empty="Aún no hay próximos estrenos publicados." />
    </main>
  )
}
