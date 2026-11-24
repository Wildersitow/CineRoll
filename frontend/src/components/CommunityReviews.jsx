import { useEffect, useId, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { CaretDownIcon, ChatsCircleIcon, HeartIcon, TrashIcon } from '@phosphor-icons/react'
import { Link, useLocation } from 'react-router-dom'
import { borrarComentarioResena, crearComentarioResena, getComentariosResena } from '../services/api'
import { Heart } from './FilmActions'
import { NotaCompacta } from './Valoracion'

const LIMITE_TEXTO = 480
const MAX_COMENTARIO = 1000
const fecha = new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })
const ESTADOS = { visto: 'Visto', viendo: 'Viendo' }

function Avatar({ username, url }) {
  const [failed, setFailed] = useState(null)
  return (
    <span className="review-avatar" aria-hidden="true">
      {url && url !== failed ? <img src={url} alt="" onError={() => setFailed(url)} /> : (username || '?').charAt(0).toUpperCase()}
    </span>
  )
}

/** Hilo de comentarios de una reseña: se carga al abrirlo. */
function Comentarios({ review, user, onCount }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [texto, setTexto] = useState('')
  const [busy, setBusy] = useState(false)
  const location = useLocation()
  const inputId = useId()

  useEffect(() => {
    let active = true
    getComentariosResena(review.id)
      .then((data) => { if (active) setItems(data.results || []) })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [review.id])

  async function enviar(event) {
    event.preventDefault()
    if (!texto.trim() || busy) return
    setBusy(true)
    setError('')
    try {
      const nuevo = await crearComentarioResena(review.id, texto.trim())
      setItems((previos) => [...(previos || []), nuevo])
      onCount(1)
      setTexto('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function borrar(comentario) {
    setError('')
    try {
      await borrarComentarioResena(comentario.id)
      setItems((previos) => previos.filter(({ id }) => id !== comentario.id))
      onCount(-1)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="review-comments">
      {items === null && !error && <p className="review-comments-state" role="status">Cargando comentarios…</p>}
      {items?.length === 0 && <p className="review-comments-state">Nadie ha comentado todavía.</p>}
      {items?.length > 0 && (
        <ul>
          {items.map((comentario) => (
            <li key={comentario.id} className="review-comment">
              <Avatar username={comentario.usuario} url={comentario.usuario_avatar} />
              <div>
                <p className="review-comment-meta">
                  <Link to={`/usuarios/${encodeURIComponent(comentario.usuario)}`}>{comentario.usuario}</Link>
                  <time dateTime={comentario.fecha_creacion}>{fecha.format(new Date(comentario.fecha_creacion))}</time>
                  {user && [comentario.usuario, review.usuario].includes(user.username) && (
                    <button type="button" className="review-comment-delete" onClick={() => borrar(comentario)} aria-label={`Borrar comentario de ${comentario.usuario}`}>
                      <TrashIcon aria-hidden="true" />
                    </button>
                  )}
                </p>
                <p className="review-comment-text">{comentario.texto}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className="review-comments-error">{error}</p>}
      {user ? (
        <form className="review-comment-form" onSubmit={enviar}>
          <label className="cinema-visually-hidden" htmlFor={inputId}>Escribe un comentario</label>
          <textarea id={inputId} rows={2} maxLength={MAX_COMENTARIO} value={texto} onChange={(event) => setTexto(event.target.value)} placeholder="Escribe un comentario…" />
          <button type="submit" disabled={busy || !texto.trim()}>{busy ? 'Enviando…' : 'Comentar'}</button>
        </form>
      ) : (
        <p className="review-comments-state">
          <Link to="/acceso" state={{ volver: location.pathname + location.search }}>Inicia sesión</Link> para comentar.
        </p>
      )}
    </div>
  )
}

/** Una reseña de la comunidad, al estilo de Backloggd. */
function ReviewCard({ review, user, scale }) {
  const [expandida, setExpandida] = useState(false)
  const [abierto, setAbierto] = useState(false)
  const [comentarios, setComentarios] = useState(review.total_comentarios || 0)
  const reduceMotion = useReducedMotion()
  const larga = (review.texto || '').length > LIMITE_TEXTO
  const estado = ESTADOS[review.estado_autor]

  return (
    <article className="review-card">
      <Link to={`/usuarios/${encodeURIComponent(review.usuario)}`} tabIndex={-1} aria-hidden="true">
        <Avatar username={review.usuario} url={review.usuario_avatar} />
      </Link>
      <div className="review-body">
        <header className="review-head">
          <Link className="review-user" to={`/usuarios/${encodeURIComponent(review.usuario)}`}>{review.usuario}</Link>
          <time dateTime={review.fecha_creacion}>{fecha.format(new Date(review.fecha_creacion))}</time>
        </header>
        <p className="review-meta">
          <NotaCompacta puntuacion={review.puntuacion} scale={scale} />
          {review.autor_le_gusta && <HeartIcon className="review-liked" weight="fill" aria-label="Le gustó" />}
          {estado && <span className="review-status" data-estado={review.estado_autor}>{estado}</span>}
        </p>
        {review.texto && (
          <p className="review-text" data-recortada={larga && !expandida ? true : undefined}>{review.texto}</p>
        )}
        <footer className="review-actions">
          <Heart review={review} user={user} />
          <button type="button" className="review-comments-toggle" aria-expanded={abierto} aria-label={`${comentarios} ${comentarios === 1 ? 'comentario' : 'comentarios'}`} onClick={() => setAbierto(!abierto)}>
            <ChatsCircleIcon weight={abierto ? 'fill' : 'regular'} aria-hidden="true" />
            <span aria-hidden="true">{comentarios}</span>
          </button>
          {larga && (
            <button type="button" className="review-expand" aria-expanded={expandida} onClick={() => setExpandida(!expandida)}>
              <CaretDownIcon aria-hidden="true" /> {expandida ? 'Ver menos' : 'Ver más'}
            </button>
          )}
        </footer>
        <AnimatePresence initial={false}>
          {abierto && (
            <motion.div
              initial={reduceMotion ? false : { height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              style={{ overflow: 'hidden' }}
            >
              <Comentarios review={review} user={user} onCount={(paso) => setComentarios((total) => total + paso)} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </article>
  )
}

export default function CommunityReviews({ reviews, user, scale }) {
  return (
    <div className="review-list">
      {reviews.map((review) => <ReviewCard key={review.id} review={review} user={user} scale={scale} />)}
    </div>
  )
}
