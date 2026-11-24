import { useId, useState } from 'react'
import { Link } from 'react-router-dom'

const LIMITE_REPARTO = 18
const TIPOS = { pelicula: 'Película', serie: 'Serie', anime: 'Anime' }
const ESTADOS = { en_cartelera: 'En cartelera', proximo_estreno: 'Próximo estreno', fuera_cartelera: 'Fuera de cartelera' }
const fechaLarga = new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

function slug(text) {
  return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

/** Busca a la persona en Google en una pestaña nueva. */
function PersonaChip({ persona }) {
  return (
    <a className="info-chip" href={`https://www.google.com/search?q=${encodeURIComponent(persona.nombre)}`} target="_blank" rel="noreferrer" title={`Buscar a ${persona.nombre} en Google`}>
      {persona.nombre}
    </a>
  )
}

/** Pestañas de la ficha (al estilo de Letterboxd): reparto, equipo, detalles y géneros. */
export default function MediaInfoTabs({ media }) {
  const [verTodo, setVerTodo] = useState(false)
  const base = useId()
  const reparto = media.reparto || []
  const directores = media.directores || []
  const generos = media.generos || []
  const tabs = [
    reparto.length > 0 && { id: 'reparto', label: 'Reparto' },
    directores.length > 0 && { id: 'equipo', label: 'Equipo' },
    { id: 'detalles', label: 'Detalles' },
    generos.length > 0 && { id: 'generos', label: 'Géneros' },
  ].filter(Boolean)
  const [elegida, setElegida] = useState(tabs[0].id)
  const tab = tabs.some(({ id }) => id === elegida) ? elegida : tabs[0].id

  function onKeyDown(event) {
    const index = tabs.findIndex(({ id }) => id === tab)
    const paso = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!paso) return
    event.preventDefault()
    const siguiente = tabs[(index + paso + tabs.length) % tabs.length].id
    setElegida(siguiente)
    document.getElementById(`${base}-tab-${siguiente}`)?.focus()
  }

  const detalles = [
    media.titulo_original && media.titulo_original !== media.titulo && ['Título original', media.titulo_original],
    ['Tipo', TIPOS[media.tipo] || media.tipo],
    media.fecha_estreno && ['Estreno', fechaLarga.format(new Date(media.fecha_estreno))],
    media.duracion && ['Duración', `${media.duracion} min${media.tipo === 'pelicula' ? '' : ' por episodio'}`],
    ['Estado', ESTADOS[media.estado] || media.estado],
  ].filter(Boolean)

  return (
    <section className="media-info">
      <div className="info-tabs" role="tablist" aria-label="Información del título" onKeyDown={onKeyDown}>
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            id={`${base}-tab-${id}`}
            type="button"
            role="tab"
            aria-selected={tab === id}
            aria-controls={`${base}-panel`}
            tabIndex={tab === id ? 0 : -1}
            onClick={() => setElegida(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div id={`${base}-panel`} role="tabpanel" aria-labelledby={`${base}-tab-${tab}`} className="info-panel">
        {tab === 'reparto' && (
          <div className="info-chips">
            {(verTodo ? reparto : reparto.slice(0, LIMITE_REPARTO)).map((persona) => <PersonaChip key={persona.id} persona={persona} />)}
            {reparto.length > LIMITE_REPARTO && (
              <button type="button" className="info-chip info-chip-more" onClick={() => setVerTodo(!verTodo)}>
                {verTodo ? 'Mostrar menos' : `Mostrar todos (${reparto.length})`}
              </button>
            )}
          </div>
        )}
        {tab === 'equipo' && (
          <dl className="info-rows">
            <div>
              <dt>{directores.length === 1 ? 'Dirección' : 'Directores'}</dt>
              <dd className="info-chips">{directores.map((persona) => <PersonaChip key={persona.id} persona={persona} />)}</dd>
            </div>
          </dl>
        )}
        {tab === 'detalles' && (
          <dl className="info-rows">
            {detalles.map(([dt, dd]) => <div key={dt}><dt>{dt}</dt><dd>{dd}</dd></div>)}
          </dl>
        )}
        {tab === 'generos' && (
          <div className="info-chips">
            {generos.map(({ id, nombre }) => <Link key={id} className="info-chip" to={`/catalogo?genero=${slug(nombre)}`}>{nombre}</Link>)}
          </div>
        )}
      </div>
    </section>
  )
}
