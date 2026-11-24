import { useEffect, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { getFuncionesDeMedia, getMediaDetalle, getResenasDeMedia } from '../services/api'
import CinemaState from './CinemaState'
import FilmActions, { Heart } from './FilmActions'
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

  return (
    <main className="cinema-page cinema-detail">
      <Poster url={media.poster_url} eager />
      <div>
        <h1>{media.titulo}</h1>
        <p>{[media.fecha_estreno?.slice(0, 4), media.duracion && `${media.duracion} min`, ...(media.generos || []).map(({ nombre }) => nombre)].filter(Boolean).join(' · ')}</p>
        {media.promedio_puntuacion != null && <p>{media.promedio_puntuacion}/10 · {media.total_votos} votos</p>}
        <p>{media.sinopsis || 'Sinopsis aún no disponible.'}</p>
        {media.directores?.length > 0 && <p>Dirección: {media.directores.map(({ nombre }) => nombre).join(', ')}</p>}
        {media.reparto?.length > 0 && <p>Reparto: {media.reparto.map(({ nombre }) => nombre).join(', ')}</p>}
        {media.trailer_url && <p><a href={media.trailer_url}>Ver tráiler</a></p>}
        <FilmActions key={media.id + (user?.username || '')} media={media} user={user} refresh={() => setRecarga((value) => value + 1)} />
        {/* Las series y el anime no se proyectan en cines, así que no tienen funciones. */}
        {media.tipo === 'pelicula' && <section className="cinema-section">
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
        <section className="cinema-section">
          <h2>Reseñas de la comunidad</h2>
          {!current.resenas && <p role="status">Cargando reseñas…</p>}
          {current.resenas?.status === 'rejected' && <CinemaState error={current.resenas.value} title="No pudimos consultar las reseñas." retry={retry} />}
          {current.resenas?.status === 'fulfilled' && !resenas.length && <p>Aún no hay reseñas publicadas.</p>}
          <ul>{resenas.map(review => (
            <li key={review.id}><Link to={`/usuarios/${encodeURIComponent(review.usuario)}`}>{review.usuario}</Link> · {review.puntuacion}/10{review.texto && <p>{review.texto}</p>}<Heart review={review} user={user} /></li>
          ))}</ul>
          <Pagination count={current.resenas?.value?.count || 0} page={page} change={n => { const next = new URLSearchParams(query); next.set('resenas', n); setQuery(next, {state:location.state}) }} />
        </section>
        <p><Link to={location.state?.origen || (fromCinemas ? { pathname: '/cines', search: query.toString() } : '/')} state={{ poster: location.state?.poster }}>Volver a la cartelera</Link></p>
      </div>
    </main>
  )
}
