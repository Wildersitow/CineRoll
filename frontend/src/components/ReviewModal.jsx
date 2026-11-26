import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { motion, useReducedMotion } from 'motion/react'
import { TrashIcon, XIcon } from '@phosphor-icons/react'
import { borrarResena, crearResena, editarResena } from '../services/api'
import { puntuacionParaMostrar } from '../utils/puntuacion'
import Poster from './Poster'
import { HeartGlyph, StarPicker } from './Valoracion'

const MAX_TEXTO = 5000

/**
 * Ventana para registrar y reseñar un título, inspirada en el "I watched…"
 * de Letterboxd: póster, texto, estrellas y me gusta en un solo lugar.
 *
 * Se monta con un portal en <body>: si se quedara dentro del panel lateral de
 * la ficha, el backdrop-filter de ese panel convierte el position:fixed del
 * fondo en "relativo al panel" y la ventana sale aplastada en esa columna.
 */
export default function ReviewModal({ media, own, scale, initialScore, viendo, liked, likeBusy, burst, onLike, onClose, onSaved, onDeleted }) {
  const [score, setScore] = useState(initialScore || own?.puntuacion || 0)
  const [text, setText] = useState(own?.texto || '')
  const [status, setStatus] = useState({ busy: false, error: '' })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const reduceMotion = useReducedMotion()
  const titleId = useId()
  const textId = useId()
  const textarea = useRef(null)
  const cerrar = useRef(onClose)
  useEffect(() => { cerrar.current = onClose })

  useEffect(() => {
    textarea.current?.focus({ preventScroll: true })
    function onKeyDown(event) { if (event.key === 'Escape') cerrar.current() }
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = overflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  async function save(event) {
    event.preventDefault()
    if (!score || status.busy) return
    setStatus({ busy: true, error: '' })
    try {
      const datos = { puntuacion: score, texto: text }
      const result = await (own ? editarResena(own.id, datos) : crearResena(media.id, datos))
      onSaved(result, own ? 'Reseña actualizada.' : 'Reseña publicada.')
    } catch (error) {
      setStatus({ busy: false, error: error.message })
    }
  }

  async function remove() {
    setStatus({ busy: true, error: '' })
    try {
      await borrarResena(own.id)
      onDeleted()
    } catch (error) {
      setStatus({ busy: false, error: error.message })
    }
  }

  const year = media.fecha_estreno?.slice(0, 4)

  return createPortal(
    <motion.div
      className="review-modal-backdrop"
      onPointerDown={(event) => event.target === event.currentTarget && onClose()}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
    >
      <motion.form
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="review-modal"
        onSubmit={save}
        initial={reduceMotion ? false : { opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      >
        <header className="review-modal-head">
          <h2 id={titleId}>{own ? 'Editar mi reseña' : viendo ? 'Lo estoy viendo…' : 'Lo vi…'}</h2>
          <button type="button" className="review-modal-close" aria-label="Cerrar" onClick={onClose}>
            <XIcon aria-hidden="true" />
          </button>
        </header>

        <div className="review-modal-body">
          <Poster url={media.poster_url} />
          <div className="review-modal-main">
            <p className="review-modal-title"><strong>{media.titulo}</strong>{year && <span> {year}</span>}</p>
            <label className="cinema-visually-hidden" htmlFor={textId}>Tu reseña</label>
            <textarea
              id={textId}
              ref={textarea}
              className="review-modal-text"
              placeholder="Añade una reseña…"
              maxLength={MAX_TEXTO}
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <div className="review-modal-row">
              <div className="review-modal-rating">
                <div className="review-modal-label">
                  <span>Puntuación</span>
                  <output>{score ? `${puntuacionParaMostrar(score, scale)} de ${scale}` : `Sin nota`}</output>
                </div>
                <StarPicker name="puntuacion-modal" value={score} onChange={setScore} scale={scale} />
              </div>
              <div className="review-modal-like">
                <span className="review-modal-label">Me gusta</span>
                <button type="button" className="log-like-big" aria-pressed={liked} aria-label="Me gusta" disabled={likeBusy} onClick={onLike}>
                  <HeartGlyph liked={liked} burst={burst} />
                </button>
              </div>
            </div>
          </div>
        </div>

        <footer className="review-modal-foot">
          {status.error && <p role="alert">{status.error}</p>}
          {own && !confirmDelete && (
            <button type="button" className="review-modal-delete" disabled={status.busy} onClick={() => setConfirmDelete(true)}>
              <TrashIcon aria-hidden="true" /> Eliminar reseña
            </button>
          )}
          {own && confirmDelete && (
            <span className="review-modal-confirm">
              ¿Eliminar tu reseña?
              <button type="button" className="review-modal-delete" disabled={status.busy} onClick={remove}>Sí, eliminar</button>
              <button type="button" className="review-modal-cancel" onClick={() => setConfirmDelete(false)}>No</button>
            </span>
          )}
          {!score && <small className="review-modal-hint">Elige una puntuación para guardar.</small>}
          <button type="submit" className="review-modal-save" disabled={!score || status.busy}>
            {status.busy ? 'Guardando…' : 'Guardar'}
          </button>
        </footer>
      </motion.form>
    </motion.div>,
    document.body,
  )
}
