import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCines, getEstadoCartelera, getFunciones } from '../services/api'
import CinemaIcon from './CinemaIcon'
import CinemaState from './CinemaState'

const horaFuncion = new Intl.DateTimeFormat('es-CO', {
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})
const fechaActualizacion = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})
const isoDate = new Intl.DateTimeFormat('sv-SE', { dateStyle: 'short', timeZone: 'America/Bogota' })
const proveedores = { cinepolis: 'Cinépolis', royal_films: 'Royal Films', cineland: 'Cineland', cinemark: 'Cinemark' }

function cityLabel(value) {
  return value === 'bogota' ? 'Bogotá' : value.charAt(0).toLocaleUpperCase('es-CO') + value.slice(1)
}

function Actualizacion({ providers, failed }) {
  if (!providers.length && !failed) return null
  const warning = failed || providers.some((item) => item.desactualizada || item.ultima_fallo || item.ultima_tuvo_advertencia)
  return (
    <details className="cinema-freshness">
      <summary>
        <CinemaIcon name={warning ? 'warning' : 'clock'} weight="duotone" />
        {failed ? 'No se pudo verificar la actualización' : warning ? 'Actualización de horarios pendiente de confirmar' : 'Horarios actualizados'}
      </summary>
      {providers.length > 0 && (
        <ul>
          {providers.map((item) => (
            <li key={`${item.cine}-${item.ciudad}`}>
              <strong>{proveedores[item.cine] || item.cine} · {cityLabel(item.ciudad)}</strong>
              <span>{item.ultima_ejecucion_exitosa
                ? `${item.desactualizada ? 'Última actualización sin datos recientes' : 'Última actualización'}: ${fechaActualizacion.format(new Date(item.ultima_ejecucion_exitosa))}`
                : 'Sin actualización exitosa registrada'}{item.ultima_fallo && ' · Último intento fallido'}{item.ultima_tuvo_advertencia && ' · Última actualización parcial'}</span>
            </li>
          ))}
        </ul>
      )}
    </details>
  )
}

export default function CinemaDirectory() {
  const reduceMotion = useReducedMotion()
  const [query, setQuery] = useSearchParams()
  const [result, setResult] = useState(null)
  const [directory, setDirectory] = useState({})
  const [attempt, setAttempt] = useState(0)
  const city = query.get('ciudad')?.trim() || ''
  const date = query.get('fecha') || 'hoy'
  const key = `${city}/${date}`

  useEffect(() => {
    const controller = new AbortController()
    getFunciones({ fecha: date, ciudad: city || undefined }, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, attempt, data })
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ key, attempt, error })
      })
    return () => controller.abort()
  }, [date, city, key, attempt])

  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    Promise.allSettled([getCines({}, options), getEstadoCartelera(options)])
      .then(([cines, estado]) => {
        if (controller.signal.aborted) return
        setDirectory({
          cines: cines.value?.results || [],
          estado: estado.value?.resultados || [],
          failed: estado.status === 'rejected',
        })
      })
    return () => controller.abort()
  }, [attempt])

  function select(name, value) {
    const next = new URLSearchParams(query)
    if (value) next.set(name, value)
    else next.delete(name)
    setQuery(next)
  }

  const loading = result?.key !== key || result.attempt !== attempt
  const funciones = loading ? [] : result?.data?.resultados || []
  const cities = [...new Set([
    ...(directory.cines || []).map((cine) => cine.ciudad),
    ...(directory.estado || []).map((item) => item.ciudad),
    ...funciones.map(({ cine }) => cine.ciudad),
    city,
  ].filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'))
  const providers = (directory.estado || []).filter((item) => !city || city === item.ciudad)
  const byCinema = Map.groupBy(funciones, ({ cine }) => cine.id)

  return (
    <main className="cinema-page cinema-directory">
      <header className="cinema-directory-heading">
        <CinemaIcon name="ticket" weight="duotone" />
        <div>
          <h1>{date === 'hoy' ? 'Funciones de hoy' : 'Funciones por fecha'}</h1>
          <p>Consulta los horarios publicados por ciudad y cine.</p>
        </div>
      </header>
      <div className="cinema-filters">
        <label><span>Ciudad</span>
          <select value={city} onChange={(event) => select('ciudad', event.target.value)}>
            <option value="">Todas las ciudades</option>
            {cities.map((name) => <option key={name} value={name}>{cityLabel(name)}</option>)}
          </select>
        </label>
        <label><span>Fecha</span>
          <input type="date" value={date === 'hoy' ? isoDate.format() : date} onChange={(event) => select('fecha', event.target.value)} />
        </label>
        {date !== 'hoy' && <button type="button" onClick={() => select('fecha', '')}>Volver a hoy</button>}
      </div>
      <Actualizacion providers={providers} failed={directory.failed} />
      {loading && <>
        <span role="status" className="cinema-visually-hidden">Cargando funciones…</span>
        <div className="cinema-show-list" aria-hidden="true">
          {[0, 1, 2].map((index) => <div key={index} className="cinema-show-skeleton cinema-skeleton" style={{ '--skeleton-delay': `${index * 75}ms` }}><span /><span /></div>)}
        </div>
      </>}
      {!loading && result.error && <CinemaState error={result.error} title="No pudimos cargar las funciones." message={result.error.status === 400 ? 'Selecciona una fecha válida.' : 'Comprueba la conexión y vuelve a intentarlo.'} retry={() => setAttempt(attempt + 1)} />}
      {!loading && !result.error && !funciones.length && <p className="cinema-state" role="status">No hay funciones publicadas para esta selección.</p>}
      {!loading && [...byCinema].map(([id, shows]) => (
        <motion.section className="cinema-section cinema-show-list" key={id}
          initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.16 }}>
          <header>
            <h2>{shows[0].cine.nombre}</h2>
            <p><CinemaIcon name="pin" /> {cityLabel(shows[0].cine.ciudad)}</p>
          </header>
          <ul>{shows.map(({ id, media_id, media_titulo, fecha_hora, formato, sala }) => (
            <li key={id}>
              <Link to={{ pathname: `/media/${media_id}`, search: new URLSearchParams({ ...Object.fromEntries(query), fecha: date }).toString() }}>{media_titulo}</Link>
              <small>{[sala, formato].filter(Boolean).join(' · ')}</small>
              <time dateTime={fecha_hora}>{horaFuncion.format(new Date(fecha_hora))}</time>
            </li>
          ))}</ul>
        </motion.section>
      ))}
    </main>
  )
}
