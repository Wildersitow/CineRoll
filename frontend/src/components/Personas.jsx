import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { buscarUsuarios, dejarDeSeguir, getStoredAuth, getUsuariosRecomendados, seguirUsuario } from '../services/api'
import CinemaIcon from './CinemaIcon'

function plural(n, uno, varios) {
  return `${n} ${n === 1 ? uno : varios}`
}

function BotonSeguir({ persona }) {
  const location = useLocation()
  const yo = getStoredAuth()
  const [sigo, setSigo] = useState(Boolean(persona.lo_sigo))
  const [pendiente, setPendiente] = useState(false)
  const [error, setError] = useState(false)

  if (yo?.username === persona.username) return <span className="person-card-me">Eres tú</span>
  if (!yo) {
    return <Link className="person-follow" to="/acceso" state={{ volver: location.pathname + location.search }}>Seguir</Link>
  }

  async function alternar() {
    setPendiente(true)
    setError(false)
    try {
      await (sigo ? dejarDeSeguir(encodeURIComponent(persona.username)) : seguirUsuario(encodeURIComponent(persona.username)))
      setSigo(!sigo)
    } catch {
      setError(true)
    } finally {
      setPendiente(false)
    }
  }

  return (
    <button
      type="button"
      className="person-follow"
      aria-pressed={sigo}
      aria-label={`${sigo ? 'Dejar de seguir' : 'Seguir'} a @${persona.username}`}
      title={error ? 'No se pudo actualizar. Intenta de nuevo.' : undefined}
      disabled={pendiente}
      onClick={alternar}
    >
      {error ? 'Reintentar' : sigo ? 'Siguiendo' : 'Seguir'}
    </button>
  )
}

export function PersonaCard({ persona }) {
  const [fallo, setFallo] = useState(false)
  const perfil = `/usuarios/${encodeURIComponent(persona.username)}`
  const detalle = persona.en_comun > 0
    ? `${persona.en_comun === 1 ? 'Lo sigue' : 'Lo siguen'} ${plural(persona.en_comun, 'persona', 'personas')} que sigues`
    : `${plural(persona.total_resenas ?? 0, 'reseña', 'reseñas')} · ${plural(persona.total_seguidores ?? 0, 'seguidor', 'seguidores')}`

  return (
    <li className="person-card">
      <Link to={perfil} className="person-card-link">
        <span className="person-card-avatar" aria-hidden="true">
          {persona.avatar && !fallo
            ? <img src={persona.avatar} alt="" loading="lazy" onError={() => setFallo(true)} />
            : (persona.nombre || persona.username).charAt(0).toUpperCase()}
        </span>
        <strong>{persona.nombre || persona.username}</strong>
        <span className="person-card-user">@{persona.username}</span>
        <span className="person-card-detail">{detalle}</span>
      </Link>
      <BotonSeguir persona={persona} />
    </li>
  )
}

function FilaPersonas({ id, titulo, subtitulo, personas }) {
  return (
    <section className="cinema-section people-section" aria-labelledby={`${id}-titulo`}>
      <div className="cinema-section-heading">
        <h2 id={`${id}-titulo`}>{titulo}</h2>
      </div>
      {subtitulo && <p className="people-subtitle">{subtitulo}</p>}
      <ul className="people-row">
        {personas.map(persona => <PersonaCard key={persona.id} persona={persona} />)}
      </ul>
    </section>
  )
}

/* Al final del inicio: personas para seguir (no se muestra si no hay ninguna). */
export function UsuariosRecomendados() {
  const [personas, setPersonas] = useState([])

  useEffect(() => {
    const controller = new AbortController()
    getUsuariosRecomendados({ signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setPersonas(data) })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  if (!personas.length) return null
  return (
    <FilaPersonas
      id="recomendados"
      titulo="Usuarios recomendados"
      subtitulo={getStoredAuth() ? 'Cinéfilos que quizá conozcas, según a quién sigues.' : 'Los cinéfilos más activos de CineRoll.'}
      personas={personas}
    />
  )
}

/* En los resultados de búsqueda: personas cuyo usuario o nombre coincide. */
export function PersonasEncontradas({ texto }) {
  const [resultado, setResultado] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    buscarUsuarios(texto, {}, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setResultado({ texto, ...data }) })
      .catch(() => {})
    return () => controller.abort()
  }, [texto])

  if (!resultado?.results?.length || resultado.texto !== texto) return null
  const { results, count } = resultado
  return (
    <FilaPersonas
      id="personas"
      titulo={<><CinemaIcon name="users" /> Personas</>}
      subtitulo={count > results.length ? `Mostrando ${results.length} de ${count}. Prueba con el usuario exacto para afinar.` : undefined}
      personas={results}
    />
  )
}
