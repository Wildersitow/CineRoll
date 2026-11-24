import { useEffect, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { PlayIcon } from '@phosphor-icons/react'
import { getEstadisticasMedia, getFuncionesDeMedia, getMediaDetalle, getResenasDeMedia } from '../services/api'
import CinemaState from './CinemaState'
import CommunityReviews from './CommunityReviews'
import FilmActions from './FilmActions'
import MediaInfoTabs from './MediaInfoTabs'
import MediaStats from './MediaStats'
import Pagination from './Pagination'
import Poster from './Poster'

const fechaFuncion = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})

/** Tarifas de una función, solo si el cine las publicó. */
function Prices({ show }) {
  if (!show.tarifas?.length) return null
  return <p className="show-prices">{show.tarifas.map(tarifa => {
    const price = new Intl.NumberFormat('es-CO', { style: 'currency', currency: tarifa.moneda, maximumFractionDigits: 0 }).format(tarifa.importe)
    return [tarifa.nombre, price].filter(Boolean).join(' ')
  }).join(' · ')}</p>
}

export default function MediaDetailView({ user }) {
  const { id } = useParams()
  const location = useLocation()
  const [query, setQuery] = useSearchParams()
  const date = query.get('fecha')
  const city = query.get('ciudad')
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  // Recarga en segundo plano (tras reseñar) sin volver a mostrar el esqueleto.
  const [recarga, setRecarga] = useState(0)
  const cine = query.get('cine')
  const page = Math.max(1, Number(query.get('resenas')) || 1)
  const key = JSON.stringify([id, date, cine, page, attempt, user?.username])

  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    const consultadoEn = Date.now()
    function store(name, status, value) {
      if (!controller.signal.aborted) {
        setResult((previous) => ({
          ...(previous?.key === key ? previous : { key, consultadoEn }),
          [name]: { status, value },
        }))
      }
    }
    const requests = {
      media: getMediaDetalle(id, options),
      funciones: getFuncionesDeMedia(id, { fecha: date || undefined, cine }, options),
      resenas: getResenasDeMedia(id, {page}, options),
      estadisticas: getEstadisticasMedia(id, options),
    }
    for (const [name, request] of Object.entries(requests)) {
      request.then(
        (data) => store(name, 'fulfilled', data),
        (error) => store(name, 'rejected', error),
      )
    }
    return () => controller.abort()
  }, [id, date, cine, page, key, recarga])

  const current = result?.key === key ? result : null
  const retry = () => setAttempt((value) => value + 1)

  if (!current?.media) {
    return (
      <main className="cinema-page cinema-detail">
        <span className="cinema-visually-hidden" role="status">Cargando ficha…</span>
        <div className="cinema-poster cinema-skeleton" aria-hidden="true" />
        <div className="cinema-detail-skeleton cinema-skeleton" aria-hidden="true"><span /><span /><span /></div>
      </main>
    )
  }
  if (current.media.status === 'rejected') {
    return <CinemaState error={current.media.value} title="No pudimos cargar la ficha." retry={retry} page />
  }

  const media = current.media.value
  const normalize = (value) => value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
  const funciones = (current.funciones?.value?.resultados || [])
    .filter(({ cine, fecha_hora }) => (!city || normalize(cine.ciudad) === normalize(city)) &&
      (date || Date.parse(fecha_hora) >= current.consultadoEn))
  const resenas = current.resenas?.value?.results || []
  const fromCinemas = date || city

  const scale = Number(user?.escala_calificacion) === 10 ? 10 : 5
  const year = media.fecha_estreno?.slice(0, 4)
  const directores = media.directores || []
  const fondo = media.backdrop_url || media.poster_url

  return (
    <main className="cinema-page media-page">
      {/* Fondo horizontal; si el título no tiene uno, se usa el póster difuminado. */}
      {fondo && (
        <div className="media-backdrop" data-desde-poster={!media.backdrop_url || undefined} aria-hidden="true">
          <img src={fondo} alt="" />
        </div>
      )}
      <div className="media-layout">
        <aside className="media-aside">
          <Poster url={media.poster_url} eager />
          <FilmActions key={media.id + (user?.username || '')} media={media} user={user} refresh={() => setRecarga((value) => value + 1)} />
          {media.trailer_url && (
            <a className="media-trailer" href={media.trailer_url} target="_blank" rel="noreferrer">
              <PlayIcon weight="fill" aria-hidden="true" /> Ver tráiler
            </a>
          )}
        </aside>

        <div className="media-main">
          <header className="media-header">
            <div>
              <h1>{media.titulo}{year && <span className="media-year"> {year}</span>}</h1>
              {directores.length > 0 && (
                <p className="media-byline">
                  {media.tipo === 'pelicula' ? 'Dirigida por ' : 'Creada por '}
                  {directores.map(({ id: personaId, nombre }, index) => (
                    <span key={personaId}>{index > 0 && ', '}<a href={`https://www.google.com/search?q=${encodeURIComponent(nombre)}`} target="_blank" rel="noreferrer">{nombre}</a></span>
                  ))}
                </p>
              )}
            </div>
            {media.fecha_estreno && (
              <p className="media-release">
                <span>{media.estado === 'proximo_estreno' ? 'Se estrena' : 'Estreno'}</span>
                <strong>{new Date(media.fecha_estreno).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })}</strong>
              </p>
            )}
          </header>
          <p className="media-synopsis">{media.sinopsis || 'Sinopsis aún no disponible.'}</p>

          <MediaInfoTabs media={media} />
          <MediaStats stats={current.estadisticas?.status === 'fulfilled' ? current.estadisticas.value : null} media={media} scale={scale} />

          {/* Las series y el anime no se proyectan en cines, así que no tienen funciones. */}
          {media.tipo === 'pelicula' && <section className="cinema-section media-section">
            <h2>Funciones</h2>
            {!current.funciones && <p role="status">Cargando horarios…</p>}
            {current.funciones?.status === 'rejected' && <CinemaState error={current.funciones.value} title="No pudimos consultar los horarios." retry={retry} />}
            {current.funciones?.status === 'fulfilled' && !funciones.length && <p>{fromCinemas ? 'No hay funciones para esta selección.' : 'No hay funciones próximas para este título.'}</p>}
            {fromCinemas && <p><Link to={`/media/${id}`}>Ver todas las funciones próximas</Link></p>}
            {[...Map.groupBy(funciones, show => show.cine.id)].map(([cinemaId, shows]) => (
              <div key={cinemaId}>
                <h3>{shows[0].cine.nombre}</h3>
                <ul>{shows.map(show => (
                  <li key={show.id}>
                    <time dateTime={show.fecha_hora}>{fechaFuncion.format(new Date(show.fecha_hora))}</time>
                    <small>{[show.formato, show.sala].filter(Boolean).join(' · ')}</small>
                    <Prices show={show} />
                  </li>
                ))}</ul>
              </div>
            ))}
          </section>}

          <section className="cinema-section media-section">
            <h2>Reseñas de la comunidad{current.resenas?.value?.count > 0 && <span className="media-count"> {current.resenas.value.count}</span>}</h2>
            {!current.resenas && <p role="status">Cargando reseñas…</p>}
            {current.resenas?.status === 'rejected' && <CinemaState error={current.resenas.value} title="No pudimos consultar las reseñas." retry={retry} />}
            {current.resenas?.status === 'fulfilled' && !resenas.length && <p>Aún no hay reseñas publicadas. ¡Sé el primero!</p>}
            <CommunityReviews reviews={resenas} user={user} scale={scale} />
            <Pagination count={current.resenas?.value?.count || 0} page={page} change={n => { const next = new URLSearchParams(query); next.set('resenas', n); setQuery(next, {state:location.state}) }} />
          </section>
          <p><Link to={location.state?.origen || (fromCinemas ? { pathname: '/cines', search: query.toString() } : '/')} state={{ poster: location.state?.poster }}>Volver a la cartelera</Link></p>
        </div>
      </div>
    </main>
  )
}
