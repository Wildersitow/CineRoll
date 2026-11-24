import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ChatCircleDotsIcon, ClockIcon, EyeIcon, PencilSimpleIcon, PlayIcon } from '@phosphor-icons/react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { actualizarRegistro, getMiRegistro, getMiResena, leerJson } from '../services/api'
import ReviewModal from './ReviewModal'
import { HeartGlyph, NotaCompacta, StarPicker } from './Valoracion'

/** Botón de "me gusta" de una reseña, con pulso, onda y partículas al marcar. */
export function Heart({ review, user }) {
  const [state, setState] = useState(review)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [burst, setBurst] = useState(0)
  const reduceMotion = useReducedMotion()
  const location = useLocation()
  const navigate = useNavigate()
  async function toggle() {
    if (!user) return navigate('/acceso', { state: { volver: location.pathname + location.search } })
    const previous = state
    setBusy(true)
    setError('')
    if (!state.me_gusta) setBurst((value) => value + 1)
    setState({ me_gusta: !state.me_gusta, total_likes: (state.total_likes || 0) + (state.me_gusta ? -1 : 1) })
    try {
      setState(await leerJson(`/resenas/${review.id}/like/`, { method: previous.me_gusta ? 'DELETE' : 'PUT' }))
    } catch (e) { setState(previous); setError(e.message) }
    finally { setBusy(false) }
  }
  const total = state.total_likes || 0
  return <>
    <button className="review-heart" aria-label="Me gusta" aria-pressed={!!state.me_gusta} disabled={busy} onClick={toggle}>
      <HeartGlyph liked={!!state.me_gusta} burst={burst} />
      <span className="heart-count" aria-live="polite">
        <AnimatePresence initial={false} mode="popLayout">
          <motion.span key={total} initial={reduceMotion ? false : { y: state.me_gusta ? '100%' : '-100%', opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={reduceMotion ? { opacity: 0 } : { y: state.me_gusta ? '-100%' : '100%', opacity: 0 }} transition={{ duration: 0.2 }}>
            {total}
          </motion.span>
        </AnimatePresence>
      </span>
    </button>
    {error && <small role="alert">{error}</small>}
  </>
}

const SIN_REGISTRO = { estado: '', me_gusta: false, pendiente: false }

/**
 * Panel para registrar un título, inspirado en Backloggd: botones de Visto,
 * Viendo (solo series y anime), Pendiente y Me gusta, más la puntuación rápida
 * y el botón que abre la ventana de reseña (estilo Letterboxd).
 */
export default function FilmActions({ media, user, refresh }) {
  const [query, setQuery] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [registro, setRegistro] = useState(null)
  const [own, setOwn] = useState(undefined)
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const [burst, setBurst] = useState(0)
  const [initialScore, setInitialScore] = useState(0)
  const [attempt, retry] = useState(0)
  const scale = Number(user?.escala_calificacion) === 10 ? 10 : 5
  const estreno = media.estado === 'proximo_estreno'
  const esSerie = media.tipo === 'serie' || media.tipo === 'anime'
  const modalOpen = query.get('accion') === 'reseña'

  useEffect(() => {
    if (!user) return
    let active = true
    getMiRegistro(media.id)
      .then((data) => { if (active) setRegistro(data) })
      .catch((error) => { if (active) setNotice(error.message) })
    getMiResena(media.id)
      .then((data) => { if (active) setOwn(data) })
      .catch((error) => { if (active) { if (error.status === 404) setOwn(null); else setNotice(error.message) } })
    return () => { active = false }
  }, [user, media.id, attempt])

  function pedirAcceso(search = location.search) {
    navigate('/acceso', { state: { volver: location.pathname + search } })
  }

  function abrirReseña(score = 0) {
    const next = new URLSearchParams(query)
    next.set('accion', 'reseña')
    if (!user) return pedirAcceso(`?${next}`)
    setInitialScore(score)
    setNotice('')
    setQuery(next, { replace: true, state: location.state })
  }

  function cerrarReseña() {
    const next = new URLSearchParams(query)
    next.delete('accion')
    setQuery(next, { replace: true, state: location.state })
  }

  async function cambiar(cambios, campo) {
    if (!user) return pedirAcceso()
    const previo = registro
    setBusy(campo)
    setNotice('')
    // Se pinta el cambio al instante y se revierte si el servidor falla.
    setRegistro({ ...(registro || SIN_REGISTRO), ...cambios, ...(cambios.estado === 'visto' ? { pendiente: false } : {}) })
    try {
      setRegistro(await actualizarRegistro(media.id, cambios))
    } catch (error) {
      setRegistro(previo)
      setNotice(error.message)
    } finally {
      setBusy('')
    }
  }

  function toggleLike() {
    const actual = registro || SIN_REGISTRO
    if (!actual.me_gusta) setBurst((value) => value + 1)
    cambiar({ me_gusta: !actual.me_gusta }, 'me_gusta')
  }

  function despuesDeReseñar(message) {
    cerrarReseña()
    setNotice(message)
    retry((value) => value + 1)
    refresh()
  }

  const r = registro || SIN_REGISTRO
  const cargando = Boolean(user) && (registro === null || own === undefined) && !notice
  const estados = [
    { id: 'visto', label: 'Visto', Icon: EyeIcon },
    ...(esSerie ? [{ id: 'viendo', label: 'Viendo', Icon: PlayIcon }] : []),
  ]

  return (
    <section className="log-panel" aria-label="Tu registro" aria-busy={cargando || undefined}>
      <div className="log-bar" role="group" aria-label="Estado">
        {estados.map(({ id, label, Icon }) => {
          const on = r.estado === id
          return (
            <button
              key={id}
              type="button"
              className="log-button"
              data-estado={id}
              aria-pressed={on}
              disabled={cargando || busy === 'estado' || estreno}
              title={estreno ? 'Aún no se estrena' : undefined}
              onClick={() => cambiar({ estado: on ? '' : id }, 'estado')}
            >
              <Icon weight={on ? 'fill' : 'regular'} aria-hidden="true" /> {label}
            </button>
          )
        })}
        <button
          type="button"
          className="log-button"
          data-estado="pendiente"
          aria-pressed={r.pendiente}
          disabled={cargando || busy === 'pendiente'}
          onClick={() => cambiar({ pendiente: !r.pendiente }, 'pendiente')}
        >
          <ClockIcon weight={r.pendiente ? 'fill' : 'regular'} aria-hidden="true" /> Pendiente
        </button>
        <button
          type="button"
          className="log-button log-like"
          aria-pressed={r.me_gusta}
          disabled={cargando || busy === 'me_gusta'}
          onClick={toggleLike}
        >
          <HeartGlyph liked={r.me_gusta} burst={burst} /> Me gusta
        </button>
      </div>

      <div className="log-review">
        {own ? (
          <div className="log-own">
            <span className="log-label">Tu reseña</span>
            <NotaCompacta puntuacion={own.puntuacion} scale={scale} />
            {own.texto && <p>“{own.texto}”</p>}
          </div>
        ) : (
          <div className="log-quickrate">
            <span className="log-label">{estreno ? 'Disponible al estrenarse' : 'Calificar'}</span>
            <StarPicker name="puntuacion-rapida" value={0} onChange={abrirReseña} scale={scale} disabled={estreno || cargando} label="Calificar" />
          </div>
        )}
        <button type="button" className="log-write" disabled={estreno || cargando} onClick={() => abrirReseña()}>
          <PencilSimpleIcon aria-hidden="true" /> {own ? 'Editar reseña' : 'Reseñar'}
        </button>
      </div>

      {estreno && <p className="log-hint">Aún no se estrena: puedes dejarlo pendiente o darle me gusta.</p>}
      {notice && (
        <p className="log-hint" role="status">
          {notice}{' '}
          {user && (registro === null || own === undefined) && <button type="button" className="log-retry" onClick={() => { setNotice(''); retry(attempt + 1) }}>Reintentar</button>}
        </p>
      )}
      <Link className="log-chat" to={`/salas/${media.id}`}>
        <ChatCircleDotsIcon aria-hidden="true" /> Conversación sobre {media.titulo}
      </Link>

      <AnimatePresence>
        {modalOpen && user && own !== undefined && !estreno && (
          <ReviewModal
            key="resena"
            media={media}
            own={own}
            scale={scale}
            initialScore={initialScore}
            viendo={r.estado === 'viendo'}
            liked={r.me_gusta}
            likeBusy={busy === 'me_gusta'}
            burst={burst}
            onLike={toggleLike}
            onClose={cerrarReseña}
            onSaved={(_, message) => despuesDeReseñar(message)}
            onDeleted={() => despuesDeReseñar('Reseña eliminada.')}
          />
        )}
      </AnimatePresence>
    </section>
  )
}
