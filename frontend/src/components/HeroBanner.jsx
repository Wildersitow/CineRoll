import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Link } from 'react-router-dom'
import { getMedia } from '../services/api'
import CinemaIcon from './CinemaIcon'

// Tiempo que se muestra cada película antes de pasar a la siguiente.
export const INTERVALO_BANNER = 4000
const MAX_SLIDES = 6
const tipos = { pelicula: 'Película', serie: 'Serie', anime: 'Anime' }

/**
 * Carga las películas para el banner: primero las que tienen funciones hoy en
 * la ciudad; si no hay ninguna, las marcadas como "en cartelera".
 */
async function cargarSlides(ciudad, options) {
  const hoy = await getMedia({ ciudad: ciudad || undefined, fecha: 'hoy', ordering: '-fecha_estreno' }, options)
  let titulos = hoy.results || []
  if (!titulos.length) {
    const cartelera = await getMedia({ estado: 'en_cartelera', ordering: '-fecha_estreno' }, options)
    titulos = cartelera.results || []
  }
  return titulos.filter((media) => media.poster_url).slice(0, MAX_SLIDES)
}

function meta(media) {
  return [
    media.generos?.slice(0, 2).map((genero) => genero.nombre).join(', '),
    media.fecha_estreno?.slice(0, 4),
    media.duracion && `${media.duracion} min`,
  ].filter(Boolean).join(' · ') || tipos[media.tipo]
}

/**
 * Banner principal del Inicio: rota entre las películas en cartelera.
 * Se pausa al pasar el ratón o al enfocar un control, y no rota si el usuario
 * pidió reducir el movimiento.
 */
export default function HeroBanner({ ciudad, etiqueta, detailSearch }) {
  const reduceMotion = useReducedMotion()
  const [result, setResult] = useState(null)
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    cargarSlides(ciudad, { signal: controller.signal })
      .then((slides) => {
        if (controller.signal.aborted) return
        setResult({ ciudad, slides })
        setIndex(0)
      })
      .catch(() => {
        if (!controller.signal.aborted) setResult({ ciudad, slides: [] })
      })
    return () => controller.abort()
  }, [ciudad])

  const slides = result?.slides || []
  const loading = result?.ciudad !== ciudad
  const autoplay = slides.length > 1 && !paused && !reduceMotion

  useEffect(() => {
    if (!autoplay) return
    const timer = setTimeout(() => setIndex((value) => (value + 1) % slides.length), INTERVALO_BANNER)
    return () => clearTimeout(timer)
  }, [autoplay, index, slides.length])

  if (loading) return <div className="cinema-banner cinema-banner-loading cinema-skeleton" aria-hidden="true" />
  if (!slides.length) return null

  const media = slides[index % slides.length]
  const go = (step) => setIndex((value) => (value + step + slides.length) % slides.length)

  return (
    <section
      className="cinema-banner"
      aria-roledescription="carrusel"
      aria-label="Películas destacadas en cartelera"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false) }}
    >
      <AnimatePresence initial={false} mode="popLayout">
        <motion.div
          key={media.id}
          className="cinema-banner-slide"
          role="group"
          aria-roledescription="diapositiva"
          aria-label={`${index + 1} de ${slides.length}: ${media.titulo}`}
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.03 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.6, ease: 'easeOut' }}
        >
          <div className="cinema-banner-backdrop" style={{ backgroundImage: `url("${media.poster_url}")` }} aria-hidden="true" />
          <div className="cinema-banner-copy">
            <span className="cinema-hero-label">{etiqueta}</span>
            <h2 className={media.titulo.length > 40 ? 'is-very-long' : media.titulo.length > 22 ? 'is-long' : undefined}>{media.titulo}</h2>
            <p className="cinema-banner-meta">{meta(media)}</p>
            {media.sinopsis && <p className="cinema-banner-synopsis">{media.sinopsis}</p>}
            <div className="cinema-hero-actions">
              <Link className="cinema-primary" to={{ pathname: `/media/${media.id}`, search: detailSearch }}>
                <CinemaIcon name="ticket" /> Ver horarios
              </Link>
              {media.trailer_url && (
                <a className="cinema-secondary" href={media.trailer_url} target="_blank" rel="noreferrer">
                  <CinemaIcon name="play" /> Tráiler
                </a>
              )}
            </div>
          </div>
          <img className="cinema-banner-poster" src={media.poster_url} alt="" />
        </motion.div>
      </AnimatePresence>
      {slides.length > 1 && (
        <div className="cinema-banner-controls">
          <button type="button" onClick={() => go(-1)} aria-label="Película anterior"><CinemaIcon name="left" /></button>
          <div className="cinema-banner-dots">
            {slides.map((slide, position) => (
              <button
                key={slide.id}
                type="button"
                aria-label={`Ver ${slide.titulo}`}
                aria-current={position === index ? 'true' : undefined}
                onClick={() => setIndex(position)}
              >
                {position === index && autoplay && (
                  <span key={`${slide.id}-${index}`} style={{ animationDuration: `${INTERVALO_BANNER}ms` }} />
                )}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => go(1)} aria-label="Película siguiente"><CinemaIcon name="right" /></button>
        </div>
      )}
    </section>
  )
}
