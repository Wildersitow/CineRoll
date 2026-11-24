import { useEffect, useState } from 'react'
import { Heart } from './FilmActions'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { dejarDeSeguir, getElementosDeLista, getPerfilPublico, getResenasDeUsuario, getSeguidores, getSiguiendo, getUsuarioListas, seguirUsuario } from '../services/api'
import CinemaIcon from './CinemaIcon'
import CinemaState from './CinemaState'
import Poster from './Poster'

export function ProfileCollection({ list, title, featured }) {
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!list) return
    const controller = new AbortController()
    getElementosDeLista(list.id, {}, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult({ attempt, items: data.results }) })
      .catch((error) => { if (!controller.signal.aborted) setResult({ attempt, error }) })
    return () => controller.abort()
  }, [list, attempt])

  const loading = list && result?.attempt !== attempt
  if (!loading && result?.error?.status === 404) return null
  const items = (result?.items || []).slice(0, featured ? 5 : 4)
  return (
    <section className="cinema-profile-panel">
      <h2>{title} {list && <small>{list.total_elementos}</small>}</h2>
      {loading && <p role="status">Cargando títulos…</p>}
      {!loading && result?.error && <CinemaState error={result.error} title="No pudimos cargar los títulos." retry={() => setAttempt(attempt + 1)} />}
      {!loading && !result?.error && !items.length && <p>Aún no hay títulos para mostrar.</p>}
      {!loading && items.length > 0 && <ul className={featured ? 'cinema-profile-posters cinema-profile-featured' : 'cinema-profile-posters'}>
        {items.map(({ id, media_id, media_titulo, media_poster_url }) => (
          <li key={id}><Link to={`/media/${media_id}`} className="cinema-card">
            <Poster url={media_poster_url} /><strong>{media_titulo}</strong>
          </Link></li>
        ))}
      </ul>}
    </section>
  )
}

const fechaUnion = new Intl.DateTimeFormat('es-CO', { month: 'long', year: 'numeric', timeZone: 'America/Bogota' })

const TABS = [
  ['perfil', 'Perfil'],
  ['resenas', 'Reseñas'],
  ['listas', 'Listas'],
  ['red', 'Red'],
]

/** Puntuación de 1 a 10 mostrada como estrellas (de 0,5 a 5). */
export function Estrellas({ puntuacion }) {
  const valor = Math.max(0, Math.min(10, Number(puntuacion) || 0)) / 2
  const llenas = Math.floor(valor)
  const media = valor - llenas >= 0.5
  return (
    <span className="profile-stars" role="img" aria-label={`${puntuacion} de 10`}>
      {'★'.repeat(llenas)}{media && '½'}
    </span>
  )
}

function Avatar({ profile, className }) {
  const [failed, setFailed] = useState(null)
  return (
    <div className={className}>
      {profile.avatar && profile.avatar !== failed
        ? <img src={profile.avatar} alt="" onError={() => setFailed(profile.avatar)} />
        : <span aria-hidden="true">{(profile.nombre || profile.username || 'U').charAt(0).toUpperCase()}</span>}
    </div>
  )
}

/** Fila de 4 pósters favoritos, como en Letterboxd. */
function Favoritas({ list }) {
  const [result, setResult] = useState(null)
  useEffect(() => {
    if (!list) return
    const controller = new AbortController()
    getElementosDeLista(list.id, {}, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult({ items: data.results || [] }) })
      .catch(() => { if (!controller.signal.aborted) setResult({ items: [] }) })
    return () => controller.abort()
  }, [list])
  const items = (list ? result?.items || [] : []).slice(0, 4)
  return (
    <section className="profile-block">
      <h2 className="profile-block-title">Películas favoritas</h2>
      <ul className="profile-favorites">
        {Array.from({ length: 4 }, (_, index) => {
          const item = items[index]
          return item ? (
            <li key={item.id}>
              <Link to={`/media/${item.media_id}`} className="profile-poster" title={item.media_titulo}>
                <Poster url={item.media_poster_url} />
                <span className="cinema-visually-hidden">{item.media_titulo}</span>
              </Link>
            </li>
          ) : <li key={`vacio-${index}`} className="profile-poster-empty" aria-hidden="true" />
        })}
      </ul>
    </section>
  )
}

/** Columna lateral "Por ver": pósters apilados y total. */
function PorVer({ list, username }) {
  const [items, setItems] = useState([])
  useEffect(() => {
    if (!list) return
    const controller = new AbortController()
    getElementosDeLista(list.id, {}, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setItems(data.results || []) })
      .catch(() => {})
    return () => controller.abort()
  }, [list])
  if (!list) return null
  return (
    <section className="profile-block">
      <h2 className="profile-block-title">
        <Link to={`/usuarios/${encodeURIComponent(username)}?tab=listas`}>Por ver</Link>
        <small>{list.total_elementos}</small>
      </h2>
      {items.length > 0
        ? <ul className="profile-stack">{items.slice(0, 5).map((item) => <li key={item.id}><Poster url={item.media_poster_url} /></li>)}</ul>
        : <p className="profile-empty">Aún no hay títulos.</p>}
    </section>
  )
}

function ReviewList({ reviews, currentUser, limit }) {
  if (!reviews) return <p role="status">Cargando reseñas…</p>
  if (reviews.error) return <p className="profile-empty">No pudimos cargar las reseñas.</p>
  const items = reviews.value?.results || []
  if (!items.length) return <p className="profile-empty">Aún no hay reseñas publicadas.</p>
  return (
    <ul className="profile-reviews">
      {items.slice(0, limit).map(({ id, media_id, media_titulo, media_poster_url, puntuacion, texto, fecha_creacion, total_likes, me_gusta }) => (
        <li key={id}>
          <Link to={`/media/${media_id}`} className="profile-poster" tabIndex={-1} aria-hidden="true"><Poster url={media_poster_url} /></Link>
          <div>
            <h3><Link to={`/media/${media_id}`}>{media_titulo}</Link></h3>
            <p className="profile-review-meta">
              <Estrellas puntuacion={puntuacion} />
              {fecha_creacion && <time dateTime={fecha_creacion}>{new Date(fecha_creacion).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })}</time>}
            </p>
            {texto && <p className="profile-review-text">{texto}</p>}
            <Heart review={{ id, total_likes, me_gusta }} user={currentUser} />
          </div>
        </li>
      ))}
    </ul>
  )
}

/** Pestaña "Red": seguidores y seguidos. */
function Red({ username }) {
  const [data, setData] = useState(null)
  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    Promise.allSettled([getSeguidores(username, {}, options), getSiguiendo(username, {}, options)]).then(([seguidores, siguiendo]) => {
      if (!controller.signal.aborted) setData({ seguidores, siguiendo })
    })
    return () => controller.abort()
  }, [username])
  if (!data) return <p role="status">Cargando red…</p>
  const columnas = [['Seguidores', data.seguidores], ['Siguiendo', data.siguiendo]]
  return (
    <div className="profile-network">
      {columnas.map(([titulo, resultado]) => {
        const personas = resultado.status === 'fulfilled' ? resultado.value.results || [] : []
        return (
          <section key={titulo} className="profile-block">
            <h2 className="profile-block-title">{titulo} <small>{resultado.status === 'fulfilled' ? resultado.value.count ?? personas.length : ''}</small></h2>
            {resultado.status === 'rejected' && <p className="profile-empty">No pudimos cargar esta lista.</p>}
            {resultado.status === 'fulfilled' && !personas.length && <p className="profile-empty">Nadie por aquí todavía.</p>}
            <ul className="profile-people">
              {personas.map((persona) => (
                <li key={persona.id}>
                  <Link to={`/usuarios/${encodeURIComponent(persona.username)}`}>
                    <Avatar profile={persona} className="profile-person-avatar" />
                    <span><strong>{persona.nombre}</strong><small>@{persona.username}</small></span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function ProfileContent({ username, currentUser }) {
  const [query, setQuery] = useSearchParams()
  const tab = TABS.some(([value]) => value === query.get('tab')) ? query.get('tab') : 'perfil'
  const [data, setData] = useState({})
  const [attempt, setAttempt] = useState(0)
  const [failedBanner, setFailedBanner] = useState(null)
  const [action, setAction] = useState('')
  const [following, setFollowing] = useState(null)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const options = { signal: controller.signal }
    const requests = {
      profile: getPerfilPublico(username, options),
      lists: getUsuarioListas(username, {}, options),
      reviews: getResenasDeUsuario(username, {}, options),
    }
    for (const [name, request] of Object.entries(requests)) {
      request.then(
        (value) => { if (!controller.signal.aborted) setData((old) => ({ ...old, [name]: { attempt, value } })) },
        (error) => { if (!controller.signal.aborted) setData((old) => ({ ...old, [name]: { attempt, error } })) },
      )
    }
    return () => controller.abort()
  }, [username, attempt, currentUser?.username])

  const retry = () => setAttempt((value) => value + 1)
  if (data.profile?.attempt !== attempt) {
    return <main className="cinema-page cinema-profile"><span role="status">Cargando perfil…</span><div className="profile-banner cinema-skeleton" aria-hidden="true" /></main>
  }
  if (data.profile.error) {
    return <CinemaState error={data.profile.error} title="No pudimos cargar el perfil." retry={retry} page />
  }

  const profile = data.profile.value
  const mine = currentUser?.username === profile.username
  const isFollowing = following ?? profile.lo_sigo
  const followers = profile.total_seguidores + Number(Boolean(isFollowing)) - Number(Boolean(profile.lo_sigo))
  const lists = data.lists?.attempt === attempt ? data.lists : null
  const reviews = data.reviews?.attempt === attempt ? data.reviews : null
  const items = lists?.value?.results?.filter((list) => list.publica) || []
  const favorites = items.find(({ tipo }) => tipo === 'favoritas')
  const watchlist = items.find(({ tipo }) => tipo === 'por_ver')
  const otherLists = items.filter(({ tipo }) => !['favoritas', 'por_ver'].includes(tipo))
  const banner = profile.banner && profile.banner !== failedBanner ? profile.banner : null

  function selectTab(value) {
    const next = new URLSearchParams(query)
    if (value === 'perfil') next.delete('tab')
    else next.set('tab', value)
    setQuery(next, { replace: true })
  }

  async function share() {
    try {
      const url = new URL(`/usuarios/${encodeURIComponent(profile.username)}`, window.location.origin)
      await navigator.clipboard.writeText(url.href)
      setAction('Enlace copiado.')
    } catch {
      setAction('No se pudo copiar el enlace. Puedes copiarlo desde la barra de direcciones.')
    }
  }

  async function toggleFollow() {
    setPending(true)
    setAction('')
    try {
      await (isFollowing ? dejarDeSeguir(username) : seguirUsuario(username))
      setFollowing(!isFollowing)
      setAction(isFollowing ? 'Dejaste de seguir este perfil.' : 'Ahora sigues este perfil.')
    } catch {
      setAction('No pudimos actualizar el seguimiento. Intenta de nuevo.')
    } finally {
      setPending(false)
    }
  }

  const stats = [
    ['Reseñas', profile.total_resenas, 'resenas'],
    ['Listas', items.length, 'listas'],
    ['Seguidores', followers, 'red'],
    ['Siguiendo', profile.total_siguiendo, 'red'],
  ]

  return (
    <main className="cinema-page cinema-profile profile-page">
      <div className={banner ? 'profile-banner' : 'profile-banner profile-banner-default'} aria-hidden="true">
        {banner && <img src={banner} alt="" onError={() => setFailedBanner(banner)} />}
      </div>
      <header className="profile-header">
        <Avatar profile={profile} className="profile-avatar" />
        <div className="profile-identity">
          <h1>{profile.nombre}</h1>
          <p>@{profile.username}{profile.date_joined && <> · Se unió en {fechaUnion.format(new Date(profile.date_joined))}</>}</p>
          {profile.biografia && <p className="profile-bio">{profile.biografia}</p>}
          <div className="cinema-profile-actions">
            {mine && <Link to="/perfil"><CinemaIcon name="edit" /> Editar perfil</Link>}
            {currentUser && !mine && <button type="button" className={isFollowing ? undefined : 'profile-follow'} onClick={toggleFollow} disabled={pending}>
              <CinemaIcon name="user" weight={isFollowing ? 'fill' : 'regular'} /> {pending ? 'Actualizando…' : isFollowing ? 'Siguiendo' : 'Seguir'}
            </button>}
            {!mine && <Link to={`/mensajes/${encodeURIComponent(username)}`}><CinemaIcon name="chat" /> Mensaje</Link>}
            <button type="button" onClick={share}><CinemaIcon name="share" /> Compartir</button>
            <span role="status">{action}</span>
          </div>
        </div>
        <dl className="profile-stats">
          {stats.map(([label, value, target]) => (
            <div key={label}>
              <dt><button type="button" onClick={() => selectTab(target)}>{label}</button></dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </header>

      <nav className="profile-tabs" aria-label="Secciones del perfil">
        {TABS.map(([value, label]) => (
          <button key={value} type="button" aria-current={tab === value ? 'page' : undefined} onClick={() => selectTab(value)}>{label}</button>
        ))}
      </nav>

      {tab === 'perfil' && (
        <div className="profile-layout">
          <div>
            {lists?.error ? <CinemaState error={lists.error} title="No pudimos cargar las listas." retry={retry} /> : <Favoritas key={favorites?.id || 'sin-favoritas'} list={favorites} />}
            <section className="profile-block">
              <h2 className="profile-block-title">Reseñas recientes {(reviews?.value?.results?.length || 0) > 4 && <button type="button" onClick={() => selectTab('resenas')}>Ver todas</button>}</h2>
              <ReviewList reviews={reviews} currentUser={currentUser} limit={4} />
            </section>
          </div>
          <aside>
            <PorVer key={watchlist?.id || 'sin-por-ver'} list={watchlist} username={profile.username} />
            {otherLists.length > 0 && (
              <section className="profile-block">
                <h2 className="profile-block-title">Listas <small>{otherLists.length}</small></h2>
                <ul className="profile-list-links">
                  {otherLists.slice(0, 5).map((list) => (
                    <li key={list.id}><button type="button" onClick={() => selectTab('listas')}>{list.nombre}</button><small>{list.total_elementos}</small></li>
                  ))}
                </ul>
              </section>
            )}
            {profile.promedio_puntuacion_dada != null && (
              <section className="profile-block">
                <h2 className="profile-block-title">Puntuación media</h2>
                <p className="profile-average"><Estrellas puntuacion={Math.round(profile.promedio_puntuacion_dada)} /> <span>{profile.promedio_puntuacion_dada}/10</span></p>
              </section>
            )}
          </aside>
        </div>
      )}

      {tab === 'resenas' && (
        <section className="profile-block">
          <h2 className="profile-block-title">Reseñas <small>{profile.total_resenas}</small></h2>
          <ReviewList reviews={reviews} currentUser={currentUser} />
        </section>
      )}

      {tab === 'listas' && (
        <div>
          {!lists && <p role="status">Cargando listas…</p>}
          {lists?.error && <CinemaState error={lists.error} title="No pudimos cargar las listas." retry={retry} />}
          {lists?.value && !items.length && <p className="profile-empty">Este perfil aún no tiene listas públicas.</p>}
          {lists?.value && <>
            {favorites && <ProfileCollection key={favorites.id} list={favorites} title="Favoritas" />}
            {watchlist && <ProfileCollection key={watchlist.id} list={watchlist} title="Por ver" />}
            {otherLists.map((list) => <ProfileCollection key={list.id} list={list} title={list.nombre} />)}
          </>}
        </div>
      )}

      {tab === 'red' && <Red username={profile.username} />}
    </main>
  )
}

export default function PublicProfileView({ currentUser }) {
  const { username } = useParams()
  return <ProfileContent key={username} username={username} currentUser={currentUser} />
}
