/* Utilidades de fechas y agrupación para el chat (ChatView). */

// Mensajes seguidos del mismo autor con menos de esto de diferencia van agrupados.
const VENTANA_GRUPO_MS = 5 * 60 * 1000

export function diaDe(fecha) {
  const d = new Date(fecha)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

export function etiquetaDia(fecha, hoy = new Date()) {
  const d = new Date(fecha)
  const ayer = new Date(hoy)
  ayer.setDate(hoy.getDate() - 1)
  if (diaDe(d) === diaDe(hoy)) return 'Hoy'
  if (diaDe(d) === diaDe(ayer)) return 'Ayer'
  return d.toLocaleDateString('es-CO', {
    weekday: 'long', day: 'numeric', month: 'long',
    ...(d.getFullYear() !== hoy.getFullYear() && { year: 'numeric' }),
  })
}

export function hora(fecha) {
  return new Date(fecha).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })
}

export function haceCuanto(fecha, ahora = Date.now()) {
  const minutos = Math.round((ahora - new Date(fecha)) / 60000)
  if (minutos < 1) return 'ahora'
  if (minutos < 60) return `${minutos} min`
  if (minutos < 24 * 60) return `${Math.round(minutos / 60)} h`
  return new Date(fecha).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
}

/*
 * Convierte la lista plana de mensajes en filas para pintar: separadores de día
 * y, en cada mensaje, si abre o cierra un grupo del mismo autor.
 */
export function agruparMensajes(mensajes) {
  const filas = []
  mensajes.forEach((mensaje, i) => {
    const previo = mensajes[i - 1]
    const siguiente = mensajes[i + 1]
    if (!previo || diaDe(previo.fecha) !== diaDe(mensaje.fecha)) {
      filas.push({ tipo: 'dia', key: `dia-${diaDe(mensaje.fecha)}`, fecha: mensaje.fecha })
    }
    const juntoA = otro => otro && otro.autor === mensaje.autor && diaDe(otro.fecha) === diaDe(mensaje.fecha) &&
      Math.abs(new Date(otro.fecha) - new Date(mensaje.fecha)) < VENTANA_GRUPO_MS
    filas.push({ tipo: 'mensaje', key: mensaje.id, mensaje, inicio: !juntoA(previo), fin: !juntoA(siguiente) })
  })
  return filas
}
