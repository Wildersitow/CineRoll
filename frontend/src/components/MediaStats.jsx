import { ClockIcon, EyeIcon, HeartIcon, ListBulletsIcon, NotePencilIcon, PlayIcon, StarIcon, TimerIcon } from '@phosphor-icons/react'

const compacto = new Intl.NumberFormat('es-CO', { notation: 'compact', maximumFractionDigits: 1 })

function duracionTexto(minutos) {
  const horas = Math.floor(minutos / 60)
  return horas ? `${horas} h ${minutos % 60 ? `${minutos % 60} min` : ''}`.trim() : `${minutos} min`
}

/**
 * Estadísticas de la ficha, inspiradas en Backloggd: nota media con su
 * distribución, actividad de la comunidad y fichas con totales.
 */
export default function MediaStats({ stats, media, scale }) {
  if (!stats) return <div className="media-stats media-stats-skeleton cinema-skeleton" aria-hidden="true" />

  const distribucion = Array.from({ length: 10 }, (_, index) => stats.distribucion?.[String(index + 1)] || 0)
  const max = Math.max(1, ...distribucion)
  const promedio = stats.promedio == null ? null : (scale === 5 ? stats.promedio / 2 : stats.promedio).toFixed(1)
  const esSerie = media.tipo === 'serie' || media.tipo === 'anime'
  const etiqueta = (nota) => (scale === 5 ? `${nota / 2} estrellas` : `${nota} de 10`)

  const actividad = [
    { label: 'Vistos', value: stats.vistos, Icon: EyeIcon },
    ...(esSerie ? [{ label: 'Viendo', value: stats.viendo, Icon: PlayIcon }] : []),
    { label: 'Pendientes', value: stats.pendientes, Icon: ClockIcon },
    { label: 'Calificaciones', value: stats.total_votos, Icon: StarIcon },
  ]
  const fichas = [
    { label: 'Reseñas', value: stats.resenas, Icon: NotePencilIcon },
    { label: 'Listas', value: stats.listas, Icon: ListBulletsIcon },
    { label: 'Me gusta', value: stats.me_gusta, Icon: HeartIcon },
  ]

  return (
    <section className="media-stats" aria-label="Estadísticas">
      <div className="stats-rating">
        <span className="stats-caption">Nota media</span>
        <strong className="stats-average">{promedio ?? '—'}</strong>
        <small>{promedio ? `de ${scale} · ${compacto.format(stats.total_votos)} ${stats.total_votos === 1 ? 'calificación' : 'calificaciones'}` : 'Aún sin calificaciones'}</small>
        <div className="stats-histogram" role="img" aria-label={distribucion.map((total, index) => `${etiqueta(index + 1)}: ${total}`).join(', ')}>
          {distribucion.map((total, index) => (
            <span key={index} style={{ '--h': total / max }} data-vacio={total === 0 || undefined} title={`${etiqueta(index + 1)}: ${total}`} />
          ))}
        </div>
        <div className="stats-axis" aria-hidden="true"><span>{scale === 5 ? '½★' : '1'}</span><span>{scale === 5 ? '5★' : '10'}</span></div>
      </div>

      <ul className="stats-activity">
        {actividad.map(({ label, value, Icon }) => (
          <li key={label}>
            <span className="stats-activity-icon"><Icon weight="fill" aria-hidden="true" /></span>
            <span>{label}</span>
            <strong>{compacto.format(value || 0)}</strong>
          </li>
        ))}
      </ul>

      <div className="stats-tiles">
        {fichas.map(({ label, value, Icon }) => (
          <div key={label} className="stats-tile">
            <strong>{compacto.format(value || 0)}</strong>
            <span><Icon weight="fill" aria-hidden="true" /> {label}</span>
          </div>
        ))}
        {media.duracion > 0 && (
          <div className="stats-tile stats-tile-accent">
            <TimerIcon aria-hidden="true" />
            <strong>{duracionTexto(media.duracion)}</strong>
            <span>{esSerie ? 'por episodio' : 'de duración'}</span>
          </div>
        )}
      </div>
    </section>
  )
}
