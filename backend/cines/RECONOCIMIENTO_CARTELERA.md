# Reconocimiento inicial de cartelera

Este reconocimiento cubre los pasos 1 y 2 asignados a la Persona 3. Se
consultaron los sitios públicos el 15 de octubre de 2026. La inspección disponible
desde este entorno no permite abrir la pestaña Network de un navegador contra
todos los sitios; por eso, un endpoint no se considera confirmado hasta observar
la solicitud y su respuesta en esa pestaña.

| Cine | URL consultada y evidencia | Datos de funciones / endpoint JSON | ¿Playwright? | Dificultad inicial |
|---|---|---|---|---|
| Cinemark | [Cartelera](https://www.cinemark.com.co/cartelera) respondió HTTP 200. La página está construida con Next.js y carga el bundle `pages/cartelera`; este recibe datos de cartelera y próximos estrenos renderizados por el servidor. | No se confirmó una URL de API de funciones ni campos de sala, hora y formato. El bundle de la página de cartelera no expone por sí mismo esos datos de funciones. | Por determinar con Network en una ficha y el flujo de compra. | Media; la página es accesible, pero falta localizar el origen de los horarios. |
| Cinépolis | [Sitio Colombia](https://cinepolis.com.co/) redirige desde `www` y muestra primero la selección de ciudad; la lista incluye Valledupar. | La página de inicio consultada no mostró funciones ni una URL JSON verificable antes de seleccionar ciudad. | Probablemente necesario para investigar el cambio de ciudad y la sesión; no está confirmado que sea necesario para consumir los horarios una vez localizada su solicitud. | Media; la cartelera depende de seleccionar una ciudad. |
| Royal Films | Se intentó consultar `https://www.royal-films.com/`. La solicitud desde este entorno no pudo completar la conexión TLS; no se verificó un dominio alternativo. | Sin respuesta verificable; endpoint y campos pendientes. | No evaluable todavía. | Pendiente hasta validar el sitio oficial y su disponibilidad. |
| Cineland | Se intentó consultar `https://www.cineland.com.co/`, pero el nombre de host no resolvió desde este entorno. No se verificó un dominio alternativo. | Sin respuesta verificable; endpoint y campos pendientes. | No evaluable todavía. | Pendiente hasta confirmar el dominio oficial y su disponibilidad. |

## Resultado y siguiente verificación

Con la evidencia disponible todavía no es responsable recomendar uno o dos
cines para el MVP: no se ha confirmado una respuesta JSON con película, sala,
hora y formato en ninguno de los sitios. Para completar el reconocimiento,
abrir cada cartelera en un navegador con acceso, seleccionar ciudad cuando
corresponda y registrar en Network la URL, método, parámetros, respuesta y
requisitos de sesión de las solicitudes que contienen las funciones. Mantener
las consultas manuales y espaciadas.
