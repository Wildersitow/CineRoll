import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getFuncionesDeMedia, getMediaDetalle, getResenasDeMedia } from '../services/api'
import CinemaState from './CinemaState'
import Poster from './Poster'

const fechaFuncion = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})

export default function MediaDetailView() {
  const { id } = useParams()
  const [query] = useSearchParams()
  const date = query.get('fecha')
  const city = query.get('ciudad')
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const key = JSON.stringify([id, date, attempt])

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
      funciones: getFuncionesDeMedia(id, { fecha: date || undefined }, options),
      resenas: getResenasDeMedia(id, {}, options),
    }
    for (const [name, request] of Object.entries(requests)) {
      request.then(
        (data) => store(name, 'fulfilled', data),
        (error) => store(name, 'rejected', error),
      )
    }
    return () => controller.abort()
  }, [id, date, key])

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
        <section className="cinema-section">
          <h2>Funciones</h2>
          {!current.funciones && <p role="status">Cargando horarios…</p>}
          {current.funciones?.status === 'rejected' && <CinemaState error={current.funciones.value} title="No pudimos consultar los horarios." retry={retry} />}
          {current.funciones?.status === 'fulfilled' && !funciones.length && <p>{fromCinemas ? 'No hay funciones para esta selección.' : 'No hay funciones próximas para este título.'}</p>}
          {fromCinemas && <p><Link to={`/media/${id}`}>Ver todas las funciones próximas</Link></p>}
          <ul>{funciones.map(({ id, cine, fecha_hora, formato }) => (
            <li key={id}><strong>{cine.nombre}</strong><small>{cine.ciudad} · {fechaFuncion.format(new Date(fecha_hora))}{formato && ` · ${formato}`}</small></li>
          ))}</ul>
        </section>
        <section className="cinema-section">
          <h2>Reseñas de la comunidad</h2>
          {!current.resenas && <p role="status">Cargando reseñas…</p>}
          {current.resenas?.status === 'rejected' && <CinemaState error={current.resenas.value} title="No pudimos consultar las reseñas." retry={retry} />}
          {current.resenas?.status === 'fulfilled' && !resenas.length && <p>Aún no hay reseñas publicadas.</p>}
          <ul>{resenas.map(({ id, usuario, puntuacion, texto }) => (
            <li key={id}><strong>{usuario} · {puntuacion}/10</strong>{texto && <p>{texto}</p>}</li>
          ))}</ul>
        </section>
        <p><Link to={fromCinemas ? { pathname: '/cines', search: query.toString() } : '/#en-cartelera'}>Volver a la cartelera</Link></p>
      </div>
    </main>
  )
}
