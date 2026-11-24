import { useEffect, useId, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCines, getFuncionesDeCine, getMedia } from '../services/api'
import { cityLabel, proximosDias } from '../utils/dias'
import CinemaIcon from './CinemaIcon'
import CinemaState from './CinemaState'
import Poster from './Poster'

const hora = new Intl.DateTimeFormat('es-CO', { timeStyle: 'short', timeZone: 'America/Bogota' })

async function cargarCines(ciudad, options) {
  const cines = []
  let page = 1
  let data
  do {
    data = await getCines({ ciudad, page }, options)
    cines.push(...data.results)
    page++
  } while (data.next)
  return cines
}

/** Texto que se busca en Google Maps para ubicar el cine. */
function consultaMapa(cine) {
  return [cine.nombre, cine.direccion, cityLabel(cine.ciudad), 'Colombia'].filter(Boolean).join(', ')
}

function urlGoogleMaps(cine) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(consultaMapa(cine))}`
}

function urlMapaEmbebido(cine) {
  return `https://maps.google.com/maps?q=${encodeURIComponent(consultaMapa(cine))}&z=15&output=embed`
}

/** Cartelera del cine para un día: películas (con póster) y sus horarios. */
function CineCartelera({ cine }) {
  const [fecha, setFecha] = useState('hoy')
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const key = `${fecha}/${attempt}`
  const dias = proximosDias()

  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    Promise.all([
      getMedia({ cine: cine.id, fecha, ordering: 'titulo' }, options),
      getFuncionesDeCine(cine.id, { fecha }, options),
    ])
      .then(([media, funciones]) => {
        if (controller.signal.aborted) return
        const porTitulo = Map.groupBy(funciones.resultados || [], (funcion) => funcion.media_id)
        const peliculas = (media.results || [])
          .filter((item) => porTitulo.has(item.id))
          .map((item) => ({ media: item, funciones: porTitulo.get(item.id) }))
        setResult({ key, peliculas })
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ key, error })
      })
    return () => controller.abort()
  }, [cine.id, fecha, key])

  const loading = result?.key !== key
  const search = new URLSearchParams({ cine: String(cine.id), fecha }).toString()

  return (
    <div className="cine-cartelera">
      <div className="cinema-day-pills" role="group" aria-label={`Día en ${cine.nombre}`}>
        {dias.map((dia) => (
          <button key={dia.value} type="button" aria-pressed={dia.value === fecha} onClick={() => setFecha(dia.value)}>
            <small>{dia.label}</small>
            <strong>{dia.day}</strong>
          </button>
        ))}
      </div>
      {loading && <p className="cine-cartelera-estado" role="status">Cargando cartelera…</p>}
      {!loading && result.error && (
        <CinemaState error={result.error} title="No pudimos cargar la cartelera de este cine." retry={() => setAttempt(attempt + 1)} />
      )}
      {!loading && !result.error && !result.peliculas.length && (
        <p className="cine-cartelera-estado">No hay funciones publicadas para este día.</p>
      )}
      {!loading && !result.error && result.peliculas.length > 0 && (
        <ul className="cine-peliculas">
          {result.peliculas.map(({ media, funciones }) => (
            <li key={media.id}>
              <Link to={{ pathname: `/media/${media.id}`, search }} className="cine-pelicula-poster" tabIndex={-1} aria-hidden="true">
                <Poster url={media.poster_url} />
              </Link>
              <div>
                <Link to={{ pathname: `/media/${media.id}`, search }} className="cine-pelicula-titulo">{media.titulo}</Link>
                <small>{[media.generos?.slice(0, 2).map((g) => g.nombre).join(', '), media.duracion && `${media.duracion} min`].filter(Boolean).join(' · ')}</small>
                <ul className="cine-horarios" aria-label={`Horarios de ${media.titulo}`}>
                  {funciones.map((funcion) => (
                    <li key={funcion.id}>
                      <time dateTime={funcion.fecha_hora}>{hora.format(new Date(funcion.fecha_hora))}</time>
                      {[funcion.formato, funcion.sala].filter(Boolean).length > 0 && <span>{[funcion.formato, funcion.sala].filter(Boolean).join(' · ')}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Panel grande de un cine: mapa de fondo, nombre, botón de mapa y detalle desplegable. */
function CinePanel({ cine, expanded, onToggle }) {
  const reduceMotion = useReducedMotion()
  const detalleId = useId()

  return (
    <article className="cine-panel" data-expanded={expanded || undefined} id={`cine-${cine.id}`}>
      <div className="cine-panel-hero">
        <iframe className="cine-panel-map" src={urlMapaEmbebido(cine)} title={`Mapa de ${cine.nombre}`} loading="lazy" tabIndex={-1} aria-hidden="true" referrerPolicy="no-referrer-when-downgrade" />
        <div className="cine-panel-copy">
          <span className="cinema-hero-label">{cityLabel(cine.ciudad)}</span>
          <h2>{cine.nombre}</h2>
          {cine.direccion && <p><CinemaIcon name="pin" /> {cine.direccion}</p>}
        </div>
        <a className="cine-panel-mapbtn" href={urlGoogleMaps(cine)} target="_blank" rel="noreferrer" aria-label={`Abrir ${cine.nombre} en Google Maps`}>
          <CinemaIcon name="map" /> <span>Cómo llegar</span>
        </a>
      </div>
      <button type="button" className="cine-panel-toggle" aria-expanded={expanded} aria-controls={detalleId} onClick={onToggle}>
        <span>{expanded ? 'Ocultar cartelera y detalles' : 'Ver cartelera y detalles'}</span>
        <CinemaIcon name="caretDown" />
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={detalleId}
            className="cine-panel-detalle"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: reduceMotion ? 0 : 0.28, ease: 'easeOut' }}
          >
            <div className="cine-panel-detalle-inner">
              <CineCartelera cine={cine} />
              <aside className="cine-info" aria-label={`Información de ${cine.nombre}`}>
                <h3>Información</h3>
                <dl>
                  <div><dt><CinemaIcon name="pin" /> Dirección</dt><dd>{cine.direccion || 'Sin dirección registrada'}</dd></div>
                  <div><dt><CinemaIcon name="price" /> Precios</dt><dd>Aún no disponibles</dd></div>
                  {cine.sitio_web && (
                    <div><dt><CinemaIcon name="globe" /> Sitio web</dt><dd><a href={cine.sitio_web} target="_blank" rel="noreferrer">Abrir sitio oficial</a></dd></div>
                  )}
                </dl>
                <a className="cinema-secondary" href={urlGoogleMaps(cine)} target="_blank" rel="noreferrer">
                  <CinemaIcon name="directions" /> Cómo llegar
                </a>
              </aside>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  )
}

export default function CinesView() {
  const [query, setQuery] = useSearchParams()
  const ciudad = query.get('ciudad')?.trim() || 'valledupar'
  const abierto = query.get('cine') || ''
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [expanded, setExpanded] = useState(() => new Set(abierto ? [abierto] : []))
  const key = `${ciudad}/${attempt}`

  useEffect(() => {
    const controller = new AbortController()
    cargarCines(ciudad, { signal: controller.signal })
      .then((cines) => { if (!controller.signal.aborted) setResult({ key, cines }) })
      .catch((error) => { if (!controller.signal.aborted) setResult({ key, error }) })
    return () => controller.abort()
  }, [ciudad, key])

  const loading = result?.key !== key
  const cines = loading ? [] : result.cines || []

  // Si se llega con ?cine=ID, se baja hasta ese cine cuando ya cargó.
  useEffect(() => {
    if (!loading && abierto) document.getElementById(`cine-${abierto}`)?.scrollIntoView({ block: 'start' })
  }, [loading, abierto])

  function toggle(id) {
    setExpanded((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <main className="cinema-page cinema-cines">
      <header className="cinema-cines-heading">
        <div>
          <h1>Cines en {cityLabel(ciudad)}</h1>
          <p>{loading ? 'Buscando cines…' : `${cines.length} ${cines.length === 1 ? 'cine' : 'cines'} · Abre uno para ver su cartelera, horarios y cómo llegar.`}</p>
        </div>
      </header>
      {loading && (
        <div className="cinema-cines-list" aria-hidden="true">
          {[0, 1, 2].map((index) => <div key={index} className="cine-panel cine-panel-skeleton cinema-skeleton" style={{ '--skeleton-delay': `${index * 90}ms` }} />)}
        </div>
      )}
      {!loading && result.error && <CinemaState error={result.error} title="No pudimos cargar los cines." retry={() => setAttempt(attempt + 1)} />}
      {!loading && !result.error && !cines.length && (
        <p className="cinema-state">
          Aún no hay cines registrados en {cityLabel(ciudad)}.{' '}
          {ciudad !== 'valledupar' && <button type="button" onClick={() => setQuery({})}>Ver Valledupar</button>}
        </p>
      )}
      {!loading && cines.length > 0 && (
        <div className="cinema-cines-list">
          {cines.map((cine) => (
            <CinePanel key={cine.id} cine={cine} expanded={expanded.has(String(cine.id))} onToggle={() => toggle(String(cine.id))} />
          ))}
        </div>
      )}
    </main>
  )
}
