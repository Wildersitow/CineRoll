import { useState } from 'react'
import CinemaIcon from './CinemaIcon'
import SmoothInput from './SmoothInput'

/*
 * Campo de los formularios de acceso: etiqueta, icono, brillo que sigue al
 * cursor por el borde, botón para ver la contraseña y aviso de Bloq Mayús.
 * `children` va debajo del campo (pistas, medidor de fuerza…).
 */
export default function AuthField({ id, label, icon, password = false, children, ...inputProps }) {
  const [visible, setVisible] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const capsId = `${id}-mayus`

  function moverBrillo(event) {
    const box = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--mx', `${event.clientX - box.left}px`)
    event.currentTarget.style.setProperty('--my', `${event.clientY - box.top}px`)
  }

  function revisarMayus(event) {
    if (password && event.getModifierState) setCapsLock(event.getModifierState('CapsLock'))
  }

  const describedBy = [inputProps['aria-describedby'], password && capsLock ? capsId : null].filter(Boolean).join(' ') || undefined

  return (
    <div className="input-group">
      <label htmlFor={id}>{label}</label>
      <div className="input-field-wrapper auth-glow" onPointerMove={moverBrillo}>
        {icon && <span className="auth-field-icon"><CinemaIcon name={icon} /></span>}
        <SmoothInput
          {...inputProps}
          id={id}
          type={password ? (visible ? 'text' : 'password') : inputProps.type}
          aria-describedby={describedBy}
          onKeyDown={revisarMayus}
          onKeyUp={revisarMayus}
          onBlur={() => setCapsLock(false)}
        />
        {password && (
          <button
            type="button"
            className="toggle-password-btn"
            onClick={() => setVisible(v => !v)}
            aria-label={visible ? 'Ocultar contraseña' : 'Ver contraseña'}
            aria-pressed={visible}
          >
            <span key={visible ? 'ver' : 'oculto'} className="toggle-password-icon">
              <CinemaIcon name={visible ? 'eyeOff' : 'eye'} />
            </span>
          </button>
        )}
      </div>
      {password && capsLock && (
        <p id={capsId} className="field-hint caps-lock-hint" role="status">
          <CinemaIcon name="warning" /> Bloq Mayús está activado
        </p>
      )}
      {children}
    </div>
  )
}
