import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { HeartIcon } from '@phosphor-icons/react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { addTituloToLista, crearResena, editarResena, getListas, getMiResena, getMisListasDeMedia, leerJson } from '../services/api'
import { puntuacionParaMostrar } from '../utils/puntuacion'

// Texto que acompaña cada nota (1 a 10) en la burbuja de las estrellas.
const ETIQUETAS = ['Horrible', 'Muy mala', 'Mala', 'Floja', 'Regular', 'Aceptable', 'Buena', 'Muy buena', 'Excelente', 'Obra maestra']

const PARTICULAS = Array.from({ length: 6 }, (_, index) => {
  const angle = (index / 6) * Math.PI * 2
  return { x: Math.cos(angle) * 18, y: Math.sin(angle) * 18 }
})

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
      <span className="heart-icon">
        <motion.span
          key={`corazon-${burst}`}
          initial={reduceMotion || !burst ? false : { scale: 0.4 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 520, damping: 14 }}
          style={{ display: 'grid' }}
        >
          <HeartIcon weight={state.me_gusta ? 'fill' : 'regular'} aria-hidden="true" />
        </motion.span>
        <AnimatePresence>
          {burst > 0 && state.me_gusta && !reduceMotion && (
            <motion.span key={`onda-${burst}`} aria-hidden="true" style={{ position: 'absolute', inset: 0 }} initial={{ opacity: 1 }} animate={{ opacity: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.6 }}>
              <motion.span className="heart-ring" initial={{ scale: 0.3, opacity: 0.9 }} animate={{ scale: 1.5, opacity: 0 }} transition={{ duration: 0.45, ease: 'easeOut' }} />
              {PARTICULAS.map(({ x, y }, index) => (
                <motion.span key={index} className="heart-particle" style={{ left: 'calc(50% - .15rem)', top: 'calc(50% - .15rem)' }} initial={{ x: 0, y: 0, scale: 1 }} animate={{ x, y, scale: 0 }} transition={{ duration: 0.5, ease: 'easeOut' }} />
              ))}
            </motion.span>
          )}
        </AnimatePresence>
      </span>
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

export default function FilmActions({ media, user, refresh }) {
  const [query, setQuery] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const action = query.get('accion')
  const [open, setOpen] = useState(Boolean(action))
  const [saved, setSaved] = useState(null)
  const [own, setOwn] = useState(undefined)
  const [score, setScore] = useState(0)
  const [preview, setPreview] = useState(0)
  const [text, setText] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, retry] = useState(0)
  const scale = Number(user?.escala_calificacion) === 10 ? 10 : 5
  useEffect(() => {
    if (!user) return
    let active = true
    getMisListasDeMedia(media.id).then(data => { if (active) setSaved(data.en_por_ver) }).catch(e => { if (active) setNotice(e.message) })
    getMiResena(media.id).then(data => {
      if (active) { setOwn(data); setScore(data.puntuacion); setText(data.texto) }
    }).catch(e => { if (active) { if (e.status === 404) setOwn(null); else setNotice(e.message) } })
    return () => { active = false }
  }, [user, media.id, attempt])
  function choose(value) {
    const next = new URLSearchParams(query)
    if (value) next.set('accion', value)
    else next.delete('accion')
    if (value && value !== 'precios' && !user) {
      navigate('/acceso', { state: { volver: location.pathname + '?' + next } })
    } else { setQuery(next, { replace: true, state: location.state }); setNotice('') }
  }
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    try {
      if (action === 'guardar') {
        const lists = await getListas({ tipo: 'por_ver', usuario: user.username })
        const list = lists.results.find(item => item.tipo === 'por_ver')
        if (!list) throw new Error('La lista Por ver no está disponible.')
        await addTituloToLista(list.id, media.id)
        setSaved(true); choose(''); setNotice('Guardada en Por ver.')
      } else {
        const data = { puntuacion: score, texto: text }
        const result = await (own ? editarResena(own.id, data) : crearResena(media.id, data))
        setOwn(result); choose(''); setNotice('Reseña publicada.'); refresh()
      }
    } catch (e) { setNotice(e.message) }
    finally { setBusy(false) }
  }
  return <div className="film-actions">
    <button className="cinema-primary" disabled={busy} aria-expanded={open} onClick={() => { setOpen(!open); if (open) choose('') }}>Acciones</button>
    {open && <div className="action-grid">
      <button disabled={busy} onClick={() => choose('reseña')}>{own ? 'Editar reseña' : 'Escribir reseña'}</button>
      <button disabled={busy || saved === true} onClick={() => choose('guardar')}>{saved ? 'Guardada en Por ver' : 'Guardar película'}</button>
      <button disabled={busy} onClick={() => choose('precios')}>Consultar precios</button>
    </div>}
    {action === 'guardar' && user && <form onSubmit={submit}><button disabled={busy || saved !== false}>{saved ? 'Guardada en Por ver' : 'Guardar en Por ver'}</button></form>}
    {action === 'reseña' && user && <form onSubmit={submit}>
      <fieldset disabled={busy || own === undefined}><legend>Tu puntuación</legend>
        <div className="rating" onPointerLeave={() => setPreview(0)}>
          {(preview || score) > 0 && (
            <span className="rating-peek" aria-hidden="true" style={{ '--peek': ((preview || score) - 0.5) / 10 }}>
              <strong>{puntuacionParaMostrar(preview || score, scale)}{scale === 5 ? ' ★' : '/10'}</strong> {ETIQUETAS[(preview || score) - 1]}
            </span>
          )}
          {Array.from({ length: 10 }, (_, i) => {
            const value = i + 1
            const label = puntuacionParaMostrar(value, scale)
            return <label key={value} className={scale === 5 ? `half-star ${value % 2 ? 'half-left' : 'half-right'}` : ''} onPointerEnter={() => setPreview(value)}>
              <input type="radio" name="puntuacion" aria-label={`${label} de ${scale}`} checked={score === value} onChange={() => setScore(value)} />
              <span className={value <= (preview || score) ? 'lit' : ''} aria-hidden="true">★</span></label>
          })}
        </div>
        <output>{preview || score ? puntuacionParaMostrar(preview || score, scale) : '—'} de {scale}</output>
        <label>Tu reseña<textarea value={text} maxLength={5000} onChange={e => setText(e.target.value)} /></label>
        <button disabled={!score}>Publicar reseña</button>
      </fieldset>
    </form>}
    {notice && <p role="status">{notice} {user && (own === undefined || saved === null) && <button onClick={() => retry(attempt + 1)}>Reintentar</button>}</p>}
    <Link to={`/salas/${media.id}`}>Conversación sobre {media.titulo}</Link>
  </div>
}
