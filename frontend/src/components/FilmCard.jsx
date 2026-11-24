import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigationType } from 'react-router-dom'
import Poster from './Poster'

export default function FilmCard({ media, search }) {
  const [flipped, flip] = useState(false)
  const card = useRef(null)
  const front = useRef(null)
  const detail = useRef(null)
  const wasFlipped = useRef(false)
  useEffect(() => {
    if (flipped) detail.current?.focus({ preventScroll:true })
    else if (wasFlipped.current) front.current?.focus({ preventScroll:true })
    wasFlipped.current = flipped
  }, [flipped])
  const navigationType = useNavigationType()
  const location = useLocation()
  const to = { pathname: `/media/${media.id}`, search }
  const state = { origen: location.pathname + location.search, poster: media.id }
  const storageKey = 'cineroll:poster:' + location.key
  useEffect(() => {
    if (location.state?.poster === media.id || (navigationType === 'POP' && sessionStorage.getItem(storageKey) === String(media.id))) {
      card.current.scrollIntoView({block:'center', behavior:'instant'})
      card.current.querySelector(':scope > a')?.focus({preventScroll:true})
      sessionStorage.removeItem(storageKey)
    }
  }, [location.state, media.id, navigationType, storageKey])
  function remember() { sessionStorage.setItem(storageKey, String(media.id)) }
  // Inclinación 3D y brillo holográfico que siguen al ratón (solo con ratón y sin "reducir movimiento").
  function tilt(event) {
    if (flipped || event.pointerType !== 'mouse' || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    const box = event.currentTarget.getBoundingClientRect()
    const x = (event.clientX - box.left) / box.width
    const y = (event.clientY - box.top) / box.height
    const style = event.currentTarget.style
    style.setProperty('--tilt-x', `${(0.5 - y) * 14}deg`)
    style.setProperty('--tilt-y', `${(x - 0.5) * 16}deg`)
    style.setProperty('--glare-x', `${x * 100}%`)
    style.setProperty('--glare-y', `${y * 100}%`)
    event.currentTarget.dataset.tilting = ''
  }
  function untilt(event) {
    const style = event.currentTarget.style
    for (const name of ['--tilt-x', '--tilt-y', '--glare-x', '--glare-y']) style.removeProperty(name)
    delete event.currentTarget.dataset.tilting
  }
  return <article ref={card} className="cinema-card film-card" id={`poster-${media.id}`}>
    <div className="film-depth" onPointerMove={tilt} onPointerLeave={untilt}><div className={'film-turn' + (flipped ? ' flipped' : '')}>
      <button ref={front} className="film-front" inert={flipped} onClick={() => { flip(true) }} aria-label={`Ver sinopsis de ${media.titulo}`}>
        <Poster url={media.poster_url} /><span className="film-glare" aria-hidden="true" /><span className="film-hint">Ver sinopsis</span>
      </button>
      <div className="film-back" inert={!flipped}>
        <strong>{media.titulo}</strong><p>{media.sinopsis || 'Sinopsis aún no disponible.'}</p>
        <Link ref={detail} to={to} state={state} onClick={remember}>Ver ficha</Link><button onClick={() => flip(false)}>Volver al póster</button>
      </div>
    </div></div>
    <Link to={to} state={state} onClick={remember}><strong>{media.titulo}</strong></Link>
    <small>{[{ pelicula: 'Película', serie: 'Serie', anime: 'Anime' }[media.tipo], media.fecha_estreno?.slice(0, 4)].filter(Boolean).join(' · ')}</small>
  </article>
}
