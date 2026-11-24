import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getGeneros, getMedia } from '../services/api'
import CinemaState from './CinemaState'
import CinemaIcon from './CinemaIcon'
import FilmCard from './FilmCard'
import Pagination from './Pagination'
import { PersonasEncontradas } from './Personas'

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

export function MediaSection({ id, title, params, carousel = false, empty, detailSearch, hideEmpty = false, moreTo }) {
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

  // Las filas del catálogo se ocultan si no tienen títulos (como en Netflix).
  if (hideEmpty && !loading && !error && !titles.length) return null

  return (
    <section className="cinema-section" id={id} aria-labelledby={`${id}-title`}>
      <div className="cinema-section-heading">
        <h2 id={`${id}-title`}>{title}</h2>
        {moreTo && !loading && titles.length > 0 && <Link className="cinema-more" to={moreTo}>Ver todo <CinemaIcon name="right" /></Link>}
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

/** Carga la lista de géneros una sola vez para los chips y las filas. */
function useGeneros() {
  const [generos, setGeneros] = useState([])
  useEffect(() => {
    const controller = new AbortController()
    getGeneros({ signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setGeneros(data) })
      .catch(() => {})
    return () => controller.abort()
  }, [])
  return generos
}

/** Monta la fila solo cuando está cerca de verse, para no pedir todo de golpe. */
function LazyRow({ children }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(() => typeof IntersectionObserver === 'undefined')
  useEffect(() => {
    if (visible || !ref.current) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setVisible(true)
    }, { rootMargin: '600px 0px' })
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [visible])
  return visible ? children : <div ref={ref} className="cinema-row-placeholder" aria-hidden="true" />
}

function catalogLink(query, changes) {
  const next = new URLSearchParams(query)
  for (const [key, value] of Object.entries(changes)) {
    if (value) next.set(key, value)
    else next.delete(key)
  }
  next.delete('page')
  const text = next.toString()
  return text ? `/catalogo?${text}` : '/catalogo'
}

function slug(text) {
  return text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

export default function CatalogView() {
  const [query] = useSearchParams()
  const generos = useGeneros()
  const search = query.get('q')?.trim()
  const type = Object.hasOwn(filters, query.get('tipo')) ? query.get('tipo') : undefined
  const state = query.get('estado') === 'proximo_estreno' ? 'proximo_estreno' : undefined
  const genre = query.get('genero')?.trim() || undefined

  if (search || state) {
    const title = search ? `Resultados para “${search}”` : 'Próximos estrenos'
    return (
      <main className="cinema-page cinema-catalog">
        <h1>{title}</h1>
        {search && <PersonasEncontradas texto={search} />}
        <MediaSection key={query.toString()} id="resultados" title="Títulos" params={{ search, tipo: type, estado: state, ordering: state ? 'fecha_estreno' : 'titulo' }} empty="No encontramos títulos para esta selección." />
      </main>
    )
  }

  const typeLabel = type ? filters[type] : 'Todo el catálogo'
  const genreName = genre && (generos.find((item) => slug(item.nombre) === slug(genre))?.nombre || genre)

  return (
    <main className="cinema-page cinema-catalog">
      <header className="cinema-catalog-heading">
        <h1>{genreName ? `${type ? filters[type] : 'Títulos'} de ${genreName.toLowerCase()}` : typeLabel}</h1>
        <nav className="cinema-type-tabs" aria-label="Tipo de título">
          {[[undefined, 'Todo'], ...Object.entries(filters)].map(([value, label]) => (
            <Link key={label} to={catalogLink(query, { tipo: value })} aria-current={type === value ? 'page' : undefined}>{label}</Link>
          ))}
        </nav>
        {generos.length > 0 && (
          <nav className="cinema-chips cinema-genre-chips" aria-label="Géneros">
            <Link to={catalogLink(query, { genero: undefined })} aria-current={!genre ? 'page' : undefined}>Todos los géneros</Link>
            {generos.map((item) => (
              <Link key={item.id} to={catalogLink(query, { genero: item.nombre })} aria-current={genreName === item.nombre ? 'page' : undefined}>{item.nombre}</Link>
            ))}
          </nav>
        )}
      </header>

      {genre ? (
        <MediaSection key={query.toString()} id="resultados" title="Todos los títulos" params={{ tipo: type, genero: genre, ordering: 'titulo' }} empty="No hay títulos de este género todavía." />
      ) : (
        <>
          {type ? (
            <MediaSection key={`recientes-${type}`} id="recientes" title="Lo más reciente" params={{ tipo: type, ordering: '-fecha_estreno' }} carousel hideEmpty empty="" />
          ) : (
            <>
              <MediaSection id="en-cartelera" title="En cartelera" params={{ estado: 'en_cartelera', ordering: '-fecha_estreno' }} carousel hideEmpty empty="" moreTo="/" />
              {Object.entries(filters).map(([value, label]) => (
                <MediaSection key={value} id={`tipo-${value}`} title={label} params={{ tipo: value, ordering: '-fecha_estreno' }} carousel hideEmpty empty="" moreTo={catalogLink(query, { tipo: value })} />
              ))}
            </>
          )}
          {generos
            // En "Todo" ya hay una fila de Anime por tipo; no se repite como género.
            .filter((item) => type || !Object.hasOwn(filters, slug(item.nombre)))
            .map((item) => (
            <LazyRow key={`${type}-${item.id}`}>
              <MediaSection
                id={`genero-${slug(item.nombre)}`}
                title={item.nombre}
                params={{ tipo: type, genero: item.nombre, ordering: '-fecha_estreno' }}
                carousel
                hideEmpty
                empty=""
                moreTo={catalogLink(query, { genero: item.nombre })}
              />
            </LazyRow>
          ))}
        </>
      )}
    </main>
  )
}
