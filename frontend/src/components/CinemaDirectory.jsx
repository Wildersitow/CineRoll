import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCines, getEstadoCartelera, getFunciones } from '../services/api'
import CinemaIcon from './CinemaIcon'
import { MediaSection } from './CatalogView'
import CurtainOpening from './CurtainOpening'
import CinemaState from './CinemaState'
import HeroBanner from './HeroBanner'
import { cityLabel, isoDate, proximosDias } from '../utils/dias'

const horaFuncion = new Intl.DateTimeFormat('es-CO', {
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})
const fechaActualizacion = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})
const proveedores = { cinepolis: 'Cinépolis', royal_films: 'Royal Films', cineland: 'Cineland', cinemark: 'Cinemark' }

async function loadCinemas(options) {
  const cines = []
  let page = 1
  let data
  do {
    data = await getCines({page}, options)
    cines.push(...data.results)
    page++
  } while (data.next)
  return cines
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

export default function CinemaDirectory({ home = false }) {
  const reduceMotion = useReducedMotion()
  const [query, setQuery] = useSearchParams()
  const [result, setResult] = useState(null)
  const [directory, setDirectory] = useState({})
  const [attempt, setAttempt] = useState(0)
  const city = query.get('ciudad')?.trim() || (home ? 'valledupar' : '')
  const cinema = query.get('cine') || ''
  const date = query.get('fecha') || 'hoy'
  const key = `${city}/${date}`

  useEffect(() => {
    if (home) return
    const controller = new AbortController()
    getFunciones({ fecha: date, ciudad: city || undefined }, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, attempt, data })
      })
      .catch((error) => {
        if (!controller.signal.aborted) setResult({ key, attempt, error })
      })
    return () => controller.abort()
  }, [date, city, key, attempt, home])

  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    Promise.allSettled([loadCinemas(options), getEstadoCartelera(options)])
      .then(([cines, estado]) => {
        if (controller.signal.aborted) return
        setDirectory({
          cines: cines.value || [],
          estado: estado.value?.resultados || [],
          cinemaError: cines.status === 'rejected' ? cines.reason : null,
          failed: estado.status === 'rejected',
        })
      })
    return () => controller.abort()
  }, [attempt])

  function select(name, value) {
    const next = new URLSearchParams(query)
    if (value) next.set(name, value)
    else next.delete(name)
    next.delete('page')
    if (name === 'ciudad') next.delete('cine')
    setQuery(next)
  }

  const loading = !home && (result?.key !== key || result.attempt !== attempt)
  const funciones = loading ? [] : result?.data?.resultados || []
  const cities = [...new Set([
    ...(directory.cines || []).map((cine) => cine.ciudad),
    ...(directory.estado || []).map((item) => item.ciudad),
    ...funciones.map(({ cine }) => cine.ciudad),
    city,
  ].filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'))
  const providers = (directory.estado || []).filter((item) => !city || city === item.ciudad)
  const byCinema = Map.groupBy(funciones, ({ cine }) => cine.id)

  if (home) {
    const dias = proximosDias()
    const today = dias[0].iso
    const selected = date === 'hoy' || date === today ? 'hoy' : date
    if (!dias.some((dia) => dia.value === selected)) {
      dias.push({ value: selected, iso: selected, label: 'Fecha', day: selected.slice(8, 10) })
    }
    const diaElegido = dias.find((dia) => dia.value === selected)
    const cinesCiudad = (directory.cines || []).filter((c) => c.ciudad.toLowerCase().startsWith(city.toLowerCase()))
    const cineElegido = cinesCiudad.find((c) => String(c.id) === cinema)
    const cuando = selected === 'hoy' ? 'hoy' : selected === dias[1].value ? 'mañana' : `el ${diaElegido.label} ${diaElegido.day}`
    const detailSearch = new URLSearchParams({ ciudad: city, fecha: date, ...(cinema && { cine: cinema }) }).toString()

    return (
      <main className="cinema-page cinema-home">
        <CurtainOpening />
        <HeroBanner ciudad={city} etiqueta={`En cartelera hoy · ${cityLabel(city)}`} detailSearch={new URLSearchParams({ ciudad: city, fecha: 'hoy' }).toString()} />

        <section className="cinema-home-picker" aria-labelledby="que-ver">
          <div className="cinema-home-picker-heading">
            <div>
              <h1 id="que-ver">¿Qué vemos {cuando}?</h1>
              <p>Elige ciudad, día y cine para ver qué películas tienen funciones.</p>
            </div>
            <label className="cinema-city-select">
              <CinemaIcon name="pin" />
              <span className="cinema-visually-hidden">Ciudad</span>
              <select value={city} onChange={(event) => select('ciudad', event.target.value)}>
                {cities.map((name) => <option key={name} value={name}>{cityLabel(name)}</option>)}
              </select>
            </label>
          </div>
          <div className="cinema-day-pills" role="group" aria-label="Día">
            {dias.map((dia) => (
              <button
                key={dia.value}
                type="button"
                aria-pressed={dia.value === selected}
                onClick={() => select('fecha', dia.value === 'hoy' ? '' : dia.value)}
              >
                <small>{dia.label}</small>
                <strong>{dia.day}</strong>
              </button>
            ))}
          </div>
          {cinesCiudad.length > 0 && (
            <div className="cinema-chips" role="group" aria-label="Cine">
              <button type="button" aria-pressed={!cinema} onClick={() => select('cine', '')}>Todos los cines</button>
              {cinesCiudad.map((c) => (
                <button key={c.id} type="button" aria-pressed={String(c.id) === cinema} onClick={() => select('cine', String(c.id))}>
                  {c.nombre}
                </button>
              ))}
            </div>
          )}
          <Actualizacion providers={providers} failed={directory.failed} />
        </section>
        {directory.cinemaError && <CinemaState error={directory.cinemaError} title="No pudimos cargar el directorio de cines." retry={() => setAttempt(attempt + 1)} />}

        <MediaSection
          id="en-cartelera"
          title={cineElegido ? `En ${cineElegido.nombre}` : `Películas en cartelera ${cuando}`}
          empty="No hay funciones publicadas para esta selección. Prueba otro día u otro cine."
          params={{ ciudad: city, fecha: date, cine: cinema, ordering: 'titulo' }}
          detailSearch={detailSearch}
        />
        <MediaSection
          id="proximos"
          title="Próximos estrenos"
          params={{ estado: 'proximo_estreno', ordering: 'fecha_estreno' }}
          carousel
          hideEmpty
          moreTo="/catalogo?estado=proximo_estreno"
        />
      </main>
    )
  }

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
      {directory.cinemaError && <CinemaState error={directory.cinemaError} title="No pudimos cargar el directorio de cines." retry={() => setAttempt(attempt + 1)} />}
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
