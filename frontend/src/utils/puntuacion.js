const ESCALAS_PERMITIDAS = [5, 10]

function validarEscala(escalaCalificacion) {
  if (!ESCALAS_PERMITIDAS.includes(escalaCalificacion)) {
    throw new RangeError('La escala de calificación debe ser 5 o 10.')
  }
}

function validarPuntuacionGuardada(puntuacion) {
  if (!Number.isInteger(puntuacion) || puntuacion < 1 || puntuacion > 10) {
    throw new RangeError('La puntuación guardada debe ser un entero entre 1 y 10.')
  }
}

export function puntuacionParaMostrar(puntuacionGuardada, escalaCalificacion) {
  validarEscala(escalaCalificacion)
  validarPuntuacionGuardada(puntuacionGuardada)

  return escalaCalificacion === 5 ? puntuacionGuardada / 2 : puntuacionGuardada
}

export function puntuacionParaGuardar(puntuacionMostrada, escalaCalificacion) {
  validarEscala(escalaCalificacion)

  if (escalaCalificacion === 5) {
    if (
      !Number.isFinite(puntuacionMostrada) ||
      puntuacionMostrada < 0.5 ||
      puntuacionMostrada > 5 ||
      !Number.isInteger(puntuacionMostrada * 2)
    ) {
      throw new RangeError('La puntuación en estrellas debe ir de 0.5 a 5 en pasos de 0.5.')
    }

    return puntuacionMostrada * 2
  }

  validarPuntuacionGuardada(puntuacionMostrada)
  return puntuacionMostrada
}
