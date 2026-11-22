import { Link } from 'react-router-dom'
import CinemaIcon from './CinemaIcon'

const errors = {
  403: ['Acceso restringido', 'Tu cuenta no tiene permiso para ver este contenido.'],
  404: ['No encontramos esta página', 'Puedes volver al catálogo y continuar explorando.'],
  429: ['Demasiadas solicitudes', 'Espera un momento antes de volver a intentarlo.'],
  503: ['Servicio temporalmente no disponible', 'Intenta cargar el contenido de nuevo en unos momentos.'],
}

export default function CinemaState({ error, title, message, retry, page = false }) {
  const code = error?.status
  const [heading, description] = errors[code] || [title, message]
  const Heading = page ? 'h1' : 'h3'
  const Container = page ? 'main' : 'div'

  return (
    <Container className={page ? 'cinema-page cinema-error-page' : undefined}>
      <div className="cinema-state cinema-feedback" role="alert">
        <CinemaIcon name={code === 404 ? 'film' : 'warning'} weight="duotone" />
        <div>
          {page && errors[code] && <span className="cinema-error-code">{code}</span>}
          <Heading>{heading}</Heading>
          {description && <p>{description}</p>}
          {retry && code !== 404 && <button type="button" onClick={retry}>Reintentar</button>}
          {page && <Link to="/" className="cinema-back"><CinemaIcon name="back" /> Volver al inicio</Link>}
        </div>
      </div>
    </Container>
  )
}
