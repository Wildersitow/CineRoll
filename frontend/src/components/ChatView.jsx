import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getMediaDetalle, getPerfilPublico, leerJson } from '../services/api'
import CinemaIcon from './CinemaIcon'
import Poster from './Poster'
import { agruparMensajes, etiquetaDia, haceCuanto, hora } from '../utils/chat'

const LONGITUD_MAXIMA = 2000
const AVISO_LONGITUD = 1800
const INTERVALO_SONDEO_MS = 5000
// Si el usuario está a menos de esto del final, los mensajes nuevos bajan la vista solos.
const CERCA_DEL_FINAL_PX = 120

function Avatar({ nombre, url, className = 'chat-avatar' }) {
  const [fallo, setFallo] = useState(false)
  return (
    <span className={className} aria-hidden="true">
      {url && !fallo ? <img src={url} alt="" onError={() => setFallo(true)} /> : (nombre || '?').charAt(0).toUpperCase()}
    </span>
  )
}

function Bandeja() {
  const [filas, setFilas] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    async function cargar() {
      if (document.hidden) return
      try {
        const data = await leerJson('/chats/', { signal: controller.signal })
        if (!controller.signal.aborted) { setFilas(data); setError('') }
      } catch (e) { if (!controller.signal.aborted) setError(e.message) }
    }
    cargar()
    const timer = setInterval(cargar, INTERVALO_SONDEO_MS * 3)
    return () => { controller.abort(); clearInterval(timer) }
  }, [])

  return (
    <main className="cinema-page chat-inbox">
      <header className="chat-inbox-header">
        <h1>Mensajes</h1>
        <p>Tus conversaciones privadas. Para empezar una, abre el perfil de alguien y pulsa “Mensaje”.</p>
      </header>
      {error && <p className="chat-error" role="alert">{error}</p>}
      {!filas && !error && (
        <ul className="chat-inbox-list" aria-hidden="true">
          {[0, 1, 2].map(i => <li key={i} className="chat-inbox-skeleton"><span /><span /></li>)}
        </ul>
      )}
      {filas && !filas.length && (
        <div className="chat-empty">
          <CinemaIcon name="chat" />
          <p>Aún no tienes conversaciones.</p>
        </div>
      )}
      {filas?.length > 0 && (
        <ul className="chat-inbox-list">
          {filas.map(({ usuario, nombre, avatar, ultimo_mensaje: ultimo }) => (
            <li key={usuario}>
              <Link to={`/mensajes/${encodeURIComponent(usuario)}`} className="chat-inbox-item">
                <Avatar nombre={nombre || usuario} url={avatar} />
                <span className="chat-inbox-text">
                  <strong>{nombre || usuario}</strong>
                  <span className="chat-inbox-user">@{usuario}</span>
                  {ultimo && <span className="chat-inbox-preview">{ultimo.mio && 'Tú: '}{ultimo.texto}</span>}
                </span>
                {ultimo && <time dateTime={ultimo.fecha}>{haceCuanto(ultimo.fecha)}</time>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}

function Conversacion({ endpoint, user, username, mediaId }) {
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [older, setOlder] = useState(false)
  const [text, setText] = useState('')
  const [pendiente, setPendiente] = useState(null)
  const [error, setError] = useState('')
  const [nuevosAbajo, setNuevosAbajo] = useState(false)
  const [cabecera, setCabecera] = useState(null)
  const requestId = useRef(null)
  const lista = useRef(null)
  const campo = useRef(null)
  const [corte, setCorte] = useState(null)
  const abierta = useRef(false)
  const alto = useRef(null)
  const location = useLocation()
  const sala = mediaId !== undefined

  const merge = useCallback(messages => setItems(prev => [...new Map([...prev, ...messages].map(m => [m.id, m])).values()].sort((a, b) => a.id - b.id)), [])

  function cercaDelFinal() {
    const el = lista.current
    return !el || el.scrollHeight - el.scrollTop - el.clientHeight < CERCA_DEL_FINAL_PX
  }

  function bajar(suave = true) {
    const el = lista.current
    if (!el) return
    const reducir = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    el.scrollTo?.({ top: el.scrollHeight, behavior: suave && !reducir ? 'smooth' : 'auto' })
    setNuevosAbajo(false)
  }

  useEffect(() => {
    const controller = new AbortController()
    const pedir = sala ? getMediaDetalle(mediaId, { signal: controller.signal }) : getPerfilPublico(encodeURIComponent(username), { signal: controller.signal })
    pedir.then(data => { if (!controller.signal.aborted) setCabecera(data) }).catch(() => {})
    return () => controller.abort()
  }, [sala, mediaId, username])

  useEffect(() => {
    const controller = new AbortController()
    let first = true
    let pending = false
    let latest = 0
    async function load() {
      if (document.hidden || pending) return
      pending = true
      try {
        let more
        do {
          const url = first ? endpoint : endpoint + '?despues=' + latest
          const data = await leerJson(url, { signal: controller.signal })
          if (controller.signal.aborted) return
          if (data.results.length) {
            const abajo = cercaDelFinal()
            merge(data.results)
            latest = data.results.at(-1).id
            if (!first && !abajo) setNuevosAbajo(true)
          }
          if (first) setOlder(data.hay_anteriores)
          more = data.hay_mas
        } while (more && !document.hidden)
        if (first) setCorte(latest)
        first = false
        setLoaded(true)
        setError('')
      } catch (e) { if (!controller.signal.aborted) setError(e.message) }
      finally { pending = false }
    }
    load()
    const timer = setInterval(load, INTERVALO_SONDEO_MS)
    document.addEventListener('visibilitychange', load)
    return () => { controller.abort(); clearInterval(timer); document.removeEventListener('visibilitychange', load) }
  }, [endpoint, merge])

  // Al abrir la conversación se baja al último mensaje; los que lleguen después
  // se marcan como nuevos para animarlos.
  useLayoutEffect(() => {
    if (!loaded) return
    if (!abierta.current) {
      abierta.current = true
      bajar(false)
      return
    }
    if (alto.current !== null) {
      // Se cargaron mensajes anteriores: mantener la vista donde estaba.
      lista.current.scrollTop += lista.current.scrollHeight - alto.current
      alto.current = null
    } else if (cercaDelFinal() || items.at(-1)?.autor === user?.username) {
      bajar()
    }
  }, [loaded, items]) // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    const el = campo.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [text])

  async function history() {
    try {
      alto.current = lista.current?.scrollHeight ?? null
      const data = await leerJson(endpoint + '?antes=' + items[0].id)
      merge(data.results); setOlder(data.hay_anteriores)
    } catch (e) { alto.current = null; setError(e.message) }
  }

  async function send(e) {
    e?.preventDefault()
    const texto = text.trim()
    if (!texto || pendiente) return
    setError('')
    requestId.current ??= crypto.randomUUID()
    setPendiente({ texto, fecha: new Date().toISOString() })
    setText('')
    try {
      const message = await leerJson(endpoint, { method: 'POST', body: JSON.stringify({ texto, envio: requestId.current }) })
      merge([message]); requestId.current = null
    } catch (err) {
      setError(err.message)
      setText(texto)
    } finally {
      setPendiente(null)
      campo.current?.focus()
    }
  }

  function teclas(e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  const nombre = sala ? cabecera?.titulo : (cabecera?.nombre || cabecera?.username || username)
  const filas = agruparMensajes(items)
  const restante = LONGITUD_MAXIMA - text.length

  return (
    <main className="cinema-page chat-room">
      <header className="chat-room-header">
        <Link to={sala ? `/media/${mediaId}` : '/mensajes'} className="chat-back" aria-label={sala ? 'Volver a la ficha' : 'Volver a mensajes'}>
          <CinemaIcon name="back" />
        </Link>
        {sala
          ? <span className="chat-room-poster" aria-hidden="true"><Poster url={cabecera?.poster_url} /></span>
          : <Avatar nombre={nombre} url={cabecera?.avatar} />}
        <div className="chat-room-title">
          <h1>{sala ? (nombre ? `Sala de ${nombre}` : 'Sala de la película') : `Conversación con @${username}`}</h1>
          <p>{sala ? 'Conversación abierta: cualquiera puede leerla.' : <Link to={`/usuarios/${encodeURIComponent(username)}`}>Ver perfil</Link>}</p>
        </div>
      </header>

      <div className="chat-thread-wrap">
        <div className="chat-thread" ref={lista} role="log" aria-label="Mensajes" aria-busy={!loaded}>
          {older && <button type="button" className="chat-older" onClick={history}>Cargar mensajes anteriores</button>}
          {!loaded && !error && <p className="chat-status" role="status">Cargando mensajes…</p>}
          {loaded && !items.length && !pendiente && (
            <div className="chat-empty">
              <CinemaIcon name="chat" />
              <p>{sala ? 'Nadie ha escrito todavía. ¡Abre la conversación!' : 'Aún no hay mensajes. Saluda 👋'}</p>
            </div>
          )}
          <ol className="chat-messages">
            {filas.map(fila => {
              if (fila.tipo === 'dia') {
                return <li key={fila.key} className="chat-day"><span>{etiquetaDia(fila.fecha)}</span></li>
              }
              const { mensaje: m, inicio, fin } = fila
              const mio = m.autor === user?.username
              const nuevo = corte !== null && m.id > corte
              const clases = ['chat-msg', mio ? 'mine' : 'theirs', inicio && 'group-start', fin && 'group-end', nuevo && 'is-new'].filter(Boolean).join(' ')
              return (
                <li key={fila.key} className={clases}>
                  {!mio && (fin ? <Avatar nombre={m.autor} url={m.autor_avatar} /> : <span className="chat-avatar-gap" aria-hidden="true" />)}
                  <div className="chat-bubble">
                    {!mio && inicio && sala && <Link className="chat-author" to={`/usuarios/${encodeURIComponent(m.autor)}`}>@{m.autor}</Link>}
                    {!mio && !sala && <span className="cinema-visually-hidden">@{m.autor}: </span>}
                    {mio && <span className="cinema-visually-hidden">Tú: </span>}
                    <p>{m.texto}</p>
                    <time dateTime={m.fecha} title={new Date(m.fecha).toLocaleString('es-CO')}>{hora(m.fecha)}</time>
                  </div>
                </li>
              )
            })}
            {pendiente && (
              <li className="chat-msg mine group-start group-end is-new is-pending">
                <div className="chat-bubble">
                  <p>{pendiente.texto}</p>
                  <time dateTime={pendiente.fecha}>Enviando…</time>
                </div>
              </li>
            )}
          </ol>
        </div>
        {nuevosAbajo && (
          <button type="button" className="chat-new-pill" onClick={() => bajar()}>
            Mensajes nuevos <CinemaIcon name="down" />
          </button>
        )}
      </div>

      {error && <p className="chat-error" role="alert">{error}</p>}

      {user ? (
        <form className="chat-composer" onSubmit={send}>
          <label htmlFor="chat-texto" className="cinema-visually-hidden">Mensaje</label>
          <textarea
            id="chat-texto"
            ref={campo}
            rows={1}
            value={text}
            maxLength={LONGITUD_MAXIMA}
            placeholder={sala ? 'Escribe en la sala…' : `Escribe a @${username}…`}
            aria-describedby="chat-ayuda"
            onKeyDown={teclas}
            onChange={e => { setText(e.target.value); requestId.current = null }}
          />
          <span id="chat-ayuda" className="cinema-visually-hidden">Enter envía, Mayús + Enter añade una línea.</span>
          {restante <= LONGITUD_MAXIMA - AVISO_LONGITUD && <span className="chat-counter" aria-live="polite">{restante}</span>}
          <button type="submit" className="chat-send" disabled={Boolean(pendiente) || !text.trim()} aria-label="Enviar">
            <CinemaIcon name="send" weight="fill" />
          </button>
        </form>
      ) : (
        <p className="chat-login"><Link to="/acceso" state={{ volver: location.pathname }}>Ingresa para conversar</Link></p>
      )}
    </main>
  )
}

export default function ChatView({ user }) {
  const { username, id } = useParams()
  if (!username && !id) return <Bandeja key={user?.username || ''} />
  const endpoint = username ? `/chats/usuarios/${encodeURIComponent(username)}/` : `/chats/media/${id}/`
  return <Conversacion key={endpoint + (user?.username || '')} endpoint={endpoint} user={user} username={username} mediaId={id} />
}
