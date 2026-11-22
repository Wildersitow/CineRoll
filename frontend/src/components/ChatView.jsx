import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { leerJson } from '../services/api'

function Chat({ endpoint, title, user, inbox }) {
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [older, setOlder] = useState(false)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const requestId = useRef(null)
  const location = useLocation()
  const merge = useCallback(messages => setItems(prev => [...new Map([...prev, ...messages].map(m => [m.id,m])).values()].sort((a,b) => a.id-b.id)), [])
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
          const url = inbox || first ? endpoint : endpoint + '?despues=' + latest
          const data = await leerJson(url, { signal: controller.signal })
          if (controller.signal.aborted) return
          if (inbox) setItems(data)
          else {
            merge(data.results)
            if (data.results.length) latest = data.results.at(-1).id
            if (first) setOlder(data.hay_anteriores)
          }
          more = data.hay_mas
        } while (more && !document.hidden)
        first = false
        setLoaded(true)
      } catch (e) { if (!controller.signal.aborted) setError(e.message) }
      finally { pending = false }
    }
    load()
    const timer = setInterval(load, 5000)
    document.addEventListener('visibilitychange', load)
    return () => { controller.abort(); clearInterval(timer); document.removeEventListener('visibilitychange', load) }
  }, [endpoint, inbox, merge])
  async function history() {
    try {
      const data = await leerJson(endpoint + '?antes=' + items[0].id)
      merge(data.results); setOlder(data.hay_anteriores)
    } catch (e) { setError(e.message) }
  }
  async function send(e) {
    e.preventDefault()
    setSending(true); setError('')
    requestId.current ??= crypto.randomUUID()
    try {
      const message = await leerJson(endpoint, { method:'POST', body:JSON.stringify({ texto:text.trim(), envio:requestId.current }) })
      merge([message]); setText(''); requestId.current = null
    } catch (e) { setError(e.message) }
    finally { setSending(false) }
  }
  return <main className="cinema-page conversation"><h1>{title}</h1>
    {error && <p role="alert">{error}</p>}
    {!loaded && !error && <p role="status">Cargando mensajes…</p>}
    {loaded && !items.length && <p>{inbox ? 'Aún no tienes conversaciones. Abre un perfil para enviar un mensaje.' : 'Aún no hay mensajes.'}</p>}
    {older && <button onClick={history}>Cargar mensajes anteriores</button>}
    <ol>{items.map(item => inbox ? <li key={item.usuario}><Link to={`/mensajes/${encodeURIComponent(item.usuario)}`}>@{item.usuario}</Link></li> :
      <li className={item.autor === user?.username ? 'mine' : ''} key={item.id}>
        <Link to={`/usuarios/${encodeURIComponent(item.autor)}`}>@{item.autor}</Link><p>{item.texto}</p><time dateTime={item.fecha}>{new Date(item.fecha).toLocaleString('es-CO')}</time>
      </li>)}</ol>
    {!inbox && (user ? <form onSubmit={send}><label>Mensaje<textarea value={text} disabled={sending} maxLength={2000} onChange={e => { setText(e.target.value); requestId.current = null }} /></label><button disabled={sending || !text.trim()}>{sending ? 'Enviando…' : 'Enviar'}</button></form> : <Link to="/acceso" state={{ volver:location.pathname }}>Ingresa para conversar</Link>)}
  </main>
}

export default function ChatView({ user }) {
  const { username, id } = useParams()
  const endpoint = username ? `/chats/usuarios/${encodeURIComponent(username)}/` : id ? `/chats/media/${id}/` : '/chats/'
  return <Chat key={endpoint + (user?.username || '')} endpoint={endpoint} user={user} inbox={!id && !username} title={username ? `Conversación con @${username}` : id ? 'Conversación de la película' : 'Mis conversaciones'} />
}
