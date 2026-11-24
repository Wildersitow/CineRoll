import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { HeartIcon } from '@phosphor-icons/react'
import { puntuacionParaMostrar } from '../utils/puntuacion'

// Texto que acompaña cada nota (1 a 10) en la burbuja de las estrellas.
const ETIQUETAS = ['Horrible', 'Muy mala', 'Mala', 'Floja', 'Regular', 'Aceptable', 'Buena', 'Muy buena', 'Excelente', 'Obra maestra']

const PARTICULAS = Array.from({ length: 6 }, (_, index) => {
  const angle = (index / 6) * Math.PI * 2
  return { x: Math.cos(angle) * 18, y: Math.sin(angle) * 18 }
})

/**
 * Corazón con pulso, onda y partículas. `burst` cambia cada vez que se marca
 * "me gusta", y eso dispara la animación.
 */
export function HeartGlyph({ liked, burst }) {
  const reduceMotion = useReducedMotion()
  return (
    <span className="heart-icon">
      <motion.span
        key={`corazon-${burst}`}
        initial={reduceMotion || !burst ? false : { scale: 0.4 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 520, damping: 14 }}
        style={{ display: 'grid' }}
      >
        <HeartIcon weight={liked ? 'fill' : 'regular'} aria-hidden="true" />
      </motion.span>
      <AnimatePresence>
        {burst > 0 && liked && !reduceMotion && (
          <motion.span key={`onda-${burst}`} aria-hidden="true" style={{ position: 'absolute', inset: 0 }} initial={{ opacity: 1 }} animate={{ opacity: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.6 }}>
            <motion.span className="heart-ring" initial={{ scale: 0.3, opacity: 0.9 }} animate={{ scale: 1.5, opacity: 0 }} transition={{ duration: 0.45, ease: 'easeOut' }} />
            {PARTICULAS.map(({ x, y }, index) => (
              <motion.span key={index} className="heart-particle" style={{ left: 'calc(50% - .15rem)', top: 'calc(50% - .15rem)' }} initial={{ x: 0, y: 0, scale: 1 }} animate={{ x, y, scale: 0 }} transition={{ duration: 0.5, ease: 'easeOut' }} />
            ))}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  )
}

/**
 * Selector de estrellas (medias estrellas en escala de 5, diez en escala de 10)
 * con la burbuja que asoma encima mostrando la nota y su etiqueta.
 * `value` y `onChange` usan siempre la nota guardada, de 1 a 10.
 */
export function StarPicker({ value, onChange, scale, name, disabled = false, label = 'Tu puntuación' }) {
  const [preview, setPreview] = useState(0)
  const shown = disabled ? value : preview || value
  return (
    <div className="rating" role="radiogroup" aria-label={label} onPointerLeave={() => setPreview(0)}>
      {shown > 0 && (
        <span className="rating-peek" aria-hidden="true" style={{ '--peek': (shown - 0.5) / 10 }}>
          <strong>{puntuacionParaMostrar(shown, scale)}{scale === 5 ? ' ★' : '/10'}</strong> {ETIQUETAS[shown - 1]}
        </span>
      )}
      {Array.from({ length: 10 }, (_, index) => {
        const nota = index + 1
        const texto = puntuacionParaMostrar(nota, scale)
        return (
          <label key={nota} className={scale === 5 ? `half-star ${nota % 2 ? 'half-left' : 'half-right'}` : ''} onPointerEnter={() => setPreview(nota)}>
            <input type="radio" name={name} disabled={disabled} aria-label={`${texto} de ${scale}`} checked={value === nota} onChange={() => onChange(nota)} />
            <span className={nota <= shown ? 'lit' : ''} aria-hidden="true">★</span>
          </label>
        )
      })}
    </div>
  )
}

/** Nota de solo lectura: "★★★★½" en escala de 5 o "8/10" en escala de 10. */
export function NotaCompacta({ puntuacion, scale }) {
  const valor = puntuacionParaMostrar(puntuacion, scale)
  if (scale === 10) return <span className="nota-compacta" aria-label={`${valor} de 10`}>{valor}/10</span>
  return (
    <span className="nota-compacta" role="img" aria-label={`${valor} de 5`}>
      {'★'.repeat(Math.floor(valor))}{valor % 1 ? '½' : ''}
    </span>
  )
}
