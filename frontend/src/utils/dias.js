// Utilidades de fechas compartidas por el Inicio y la página de Cines.
// Todas usan la hora de Bogotá, igual que el backend.

export const isoDate = new Intl.DateTimeFormat('sv-SE', { dateStyle: 'short', timeZone: 'America/Bogota' })
const diaCorto = new Intl.DateTimeFormat('es-CO', { weekday: 'short', timeZone: 'America/Bogota' })
const diaMes = new Intl.DateTimeFormat('es-CO', { day: 'numeric', timeZone: 'America/Bogota' })

/** Los próximos 7 días (hoy incluido) para elegir la fecha con botones. */
export function proximosDias() {
  const ahora = Date.now()
  return Array.from({ length: 7 }, (_, offset) => {
    const dia = new Date(ahora + offset * 86400000)
    return {
      value: offset === 0 ? 'hoy' : isoDate.format(dia),
      iso: isoDate.format(dia),
      label: offset === 0 ? 'Hoy' : offset === 1 ? 'Mañana' : diaCorto.format(dia).replace('.', ''),
      day: diaMes.format(dia),
    }
  })
}

export function cityLabel(value) {
  if (!value) return ''
  return value === 'bogota' ? 'Bogotá' : value.charAt(0).toLocaleUpperCase('es-CO') + value.slice(1)
}
