import { useEffect, useRef, useState } from 'react'
import { addTituloToLista, getElementosDeLista, getListas, getMedia, removeTituloFromLista } from '../services/api'
import CinemaIcon from './CinemaIcon'
import Poster from './Poster'

const MAX_FAVORITAS = 4

/** Buscador para elegir un título y añadirlo a favoritas. */
function Buscador({ onPick, onClose, excluded }) {
  const [term, setTerm] = useState('')
  const [result, setResult] = useState({ term: '', items: [] })
  const input = useRef(null)

  useEffect(() => { input.current?.focus() }, [])

  useEffect(() => {
    const query = term.trim()
    if (query.length < 2) return
    const controller = new AbortController()
    const timer = setTimeout(() => {
      getMedia({ search: query }, { signal: controller.signal })
        .then((data) => { if (!controller.signal.aborted) setResult({ term: query, items: data.results || [] }) })
        .catch(() => { if (!controller.signal.aborted) setResult({ term: query, items: [] }) })
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [term])

  const query = term.trim()
  const items = query.length >= 2 && result.term === query ? result.items.filter((item) => !excluded.has(item.id)) : []

  return (
    <div className="favorites-search" role="dialog" aria-label="Añadir a favoritas" onKeyDown={(event) => event.key === 'Escape' && onClose()}>
      <div className="favorites-search-bar">
        <CinemaIcon name="search" />
        <input ref={input} type="search" value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Busca una película, serie o anime…" aria-label="Buscar título" />
        <button type="button" className="settings-button settings-button-ghost" onClick={onClose}>Cancelar</button>
      </div>
      {query.length >= 2 && result.term !== query && <p className="settings-hint" role="status">Buscando…</p>}
      {query.length >= 2 && result.term === query && !items.length && <p className="settings-hint">No encontramos títulos con ese nombre.</p>}
      {items.length > 0 && (
        <ul className="favorites-results">
          {items.slice(0, 8).map((item) => (
            <li key={item.id}>
              <button type="button" onClick={() => onPick(item)}>
                <Poster url={item.poster_url} />
                <span><strong>{item.titulo}</strong><small>{item.fecha_estreno?.slice(0, 4)}</small></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Sección "Películas favoritas": 4 huecos que se llenan desde el catálogo. */
export default function FavoritasEditor({ username }) {
  const [list, setList] = useState(null)
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [searching, setSearching] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    getListas({ tipo: 'favoritas', usuario: username })
      .then(async (data) => {
        const favoritas = data.results?.[0] || null
        const elementos = favoritas ? await getElementosDeLista(favoritas.id) : { results: [] }
        if (active) { setList(favoritas); setItems(elementos.results || []) }
      })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [username])

  async function add(media) {
    setBusy(true)
    setError('')
    try {
      await addTituloToLista(list.id, media.id, items.length)
      setItems([...items, { id: `nuevo-${media.id}`, media_id: media.id, media_titulo: media.titulo, media_poster_url: media.poster_url }])
      setSearching(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove(item) {
    setBusy(true)
    setError('')
    try {
      await removeTituloFromLista(list.id, item.media_id)
      setItems(items.filter((other) => other.media_id !== item.media_id))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const visibles = (items || []).slice(0, MAX_FAVORITAS)

  return (
    <section className="settings-section" aria-labelledby="favoritas-titulo">
      <div className="settings-section-heading">
        <h2 id="favoritas-titulo">Películas favoritas</h2>
        <small className="settings-hint">Aparecen en tu perfil público. Pasa el ratón sobre un póster para quitarlo.</small>
      </div>
      {error && <p role="alert">{error}</p>}
      {items === null && !error && <p className="settings-hint" role="status">Cargando favoritas…</p>}
      {items !== null && !list && <p className="settings-hint">No encontramos tu lista de favoritas.</p>}
      {items !== null && list && (
        <ul className="favorites-slots" aria-busy={busy || undefined}>
          {Array.from({ length: MAX_FAVORITAS }, (_, index) => {
            const item = visibles[index]
            if (item) {
              return (
                <li key={item.media_id} className="favorites-slot">
                  <Poster url={item.media_poster_url} />
                  <span className="favorites-slot-title">{item.media_titulo}</span>
                  <button type="button" className="favorites-remove" onClick={() => remove(item)} disabled={busy} aria-label={`Quitar ${item.media_titulo} de favoritas`}>×</button>
                </li>
              )
            }
            const first = index === visibles.length
            return (
              <li key={`vacio-${index}`} className="favorites-slot favorites-slot-empty">
                {first && (
                  <button type="button" onClick={() => setSearching(true)} disabled={busy} aria-label="Añadir una favorita">
                    <span aria-hidden="true">+</span>
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {searching && (
        <Buscador
          onPick={add}
          onClose={() => setSearching(false)}
          excluded={new Set((items || []).map((item) => item.media_id))}
        />
      )}
    </section>
  )
}
