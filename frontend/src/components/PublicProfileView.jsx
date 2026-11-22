import { useEffect, useState } from 'react'
import { Heart } from './FilmActions'
import { Link, useParams } from 'react-router-dom'
import { dejarDeSeguir, getElementosDeLista, getPerfilPublico, getResenasDeUsuario, getUsuarioListas, seguirUsuario } from '../services/api'
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

function ProfileContent({ username, currentUser }) {
  const [data, setData] = useState({})
  const [attempt, setAttempt] = useState(0)
  const [failedAvatar, setFailedAvatar] = useState(null)
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
    return <main className="cinema-page cinema-profile"><span role="status">Cargando perfil…</span><div className="cinema-detail-skeleton cinema-skeleton" aria-hidden="true"><span /><span /></div></main>
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

  return (
    <main className="cinema-page cinema-profile">
      <header className="cinema-profile-header">
        <div className="cinema-profile-identity">
          <div className="cinema-profile-avatar">
            {profile.avatar && profile.avatar !== failedAvatar
              ? <img src={profile.avatar} alt="" onError={() => setFailedAvatar(profile.avatar)} />
              : <span aria-hidden="true">{profile.nombre.charAt(0).toUpperCase()}</span>}
          </div>
          <div><h1>{profile.nombre}</h1><p>@{profile.username}</p></div>
        </div>
        <div className="cinema-profile-actions">
          <button type="button" onClick={share}><CinemaIcon name="share" /> Compartir</button>
          {!mine && <Link to={`/mensajes/${encodeURIComponent(username)}`}>Enviar mensaje</Link>}
          {mine && <Link to="/perfil"><CinemaIcon name="edit" /> Editar perfil</Link>}
          {currentUser && !mine && <button type="button" onClick={toggleFollow} disabled={pending}>
            <CinemaIcon name="user" weight={isFollowing ? 'fill' : 'regular'} /> {pending ? 'Actualizando…' : isFollowing ? 'Dejar de seguir' : 'Seguir'}
          </button>}
          <span role="status">{action}</span>
        </div>
        {profile.biografia && <p className="cinema-profile-bio">{profile.biografia}</p>}
        <dl className="cinema-profile-stats">
          <div><dt>Reseñas</dt><dd>{profile.total_resenas}</dd></div>
          <div><dt>Seguidores</dt><dd>{followers}</dd></div>
          <div><dt>Siguiendo</dt><dd>{profile.total_siguiendo}</dd></div>
        </dl>
      </header>
      <div className="cinema-profile-layout">
        <div>
          {!lists && <p role="status">Cargando listas…</p>}
          {lists?.error && <CinemaState error={lists.error} title="No pudimos cargar las listas." retry={retry} />}
          {lists?.value && <>
            <ProfileCollection key={favorites?.id || 'favoritas'} list={favorites} title="Favoritas" featured />
            <ProfileCollection key={watchlist?.id || 'por_ver'} list={watchlist} title="Por ver" />
            {items.filter(({ tipo }) => !['favoritas', 'por_ver'].includes(tipo)).map((list) => <ProfileCollection key={list.id} list={list} title={list.nombre} />)}
          </>}
        </div>
        <section className="cinema-profile-panel cinema-profile-reviews">
          <h2>Reseñas recientes</h2>
          {!reviews && <p role="status">Cargando reseñas…</p>}
          {reviews?.error && <CinemaState error={reviews.error} title="No pudimos cargar las reseñas." retry={retry} />}
          {reviews?.value?.results?.length === 0 && <p>Aún no hay reseñas publicadas.</p>}
          <ul>{reviews?.value?.results?.slice(0, 6).map(({ id, media_id, media_titulo, puntuacion, texto, total_likes, me_gusta }) => (
            <li key={id}><Link to={`/media/${media_id}`}>{media_titulo}</Link><strong>{puntuacion}/10</strong>{texto && <p>{texto}</p>}<Heart review={{id, total_likes, me_gusta}} user={currentUser} /></li>
          ))}</ul>
        </section>
      </div>
    </main>
  )
}

export default function PublicProfileView({ currentUser }) {
  const { username } = useParams()
  return <ProfileContent key={username} username={username} currentUser={currentUser} />
}
