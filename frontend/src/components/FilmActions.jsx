import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { addTituloToLista, crearResena, editarResena, getListas, getMiResena, getMisListasDeMedia, leerJson } from '../services/api'
import { puntuacionParaMostrar } from '../utils/puntuacion'

export function Heart({ review, user }) {
  const [state, setState] = useState(review)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const location = useLocation()
  const navigate = useNavigate()
  async function toggle() {
    if (!user) return navigate('/acceso', { state: { volver: location.pathname + location.search } })
    const previous = state
    setBusy(true)
    setError('')
    setState({ me_gusta: !state.me_gusta, total_likes: (state.total_likes || 0) + (state.me_gusta ? -1 : 1) })
    try {
      setState(await leerJson(`/resenas/${review.id}/like/`, { method: previous.me_gusta ? 'DELETE' : 'PUT' }))
    } catch (e) { setState(previous); setError(e.message) }
    finally { setBusy(false) }
  }
  return <><button className="review-heart" aria-label="Me gusta" aria-pressed={!!state.me_gusta} disabled={busy} onClick={toggle}><span aria-hidden="true">{state.me_gusta ? '♥' : '♡'}</span> {state.total_likes || 0}</button>{error && <small role="alert">{error}</small>}</>
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
          {Array.from({ length: 10 }, (_, i) => {
            const value = i + 1
            const label = puntuacionParaMostrar(value, scale)
            return <label key={value} className={scale === 5 ? 'half-star' : ''} onPointerEnter={() => setPreview(value)}>
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
