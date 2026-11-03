# Reconocimiento inicial de cartelera

Este reconocimiento cubre los pasos 1 y 2 asignados a la Persona 3. Se
consultaron los sitios públicos el 15 de octubre de 2026. La inspección disponible
desde este entorno no permite abrir la pestaña Network de un navegador contra
todos los sitios; por eso, un endpoint no se considera confirmado hasta observar
la solicitud y su respuesta en esa pestaña.

| Cine | URL consultada y evidencia | Datos de funciones / endpoint JSON | ¿Playwright? | Dificultad inicial |
|---|---|---|---|---|
| Cinemark | [Cartelera por ciudad](https://www.cinemark.com.co/cartelera/bogota) respondió HTTP 200. El HTML de Next.js contiene `__NEXT_DATA__` con `PremieresBillboard` y `Presales`. | La respuesta incrustada incluye título (`TitleAlt`/`Title`), cine (`CinemaName`, `CinemaId`), identificador de función, hora ISO (`Showtime`), sala (`ScreenName`) y formato/idioma (`Attributes`). No se confirmó un endpoint JSON separado: la fuente del scraper es el HTML de cartelera. | No hace falta para la cartelera observada: una petición HTTP entrega los datos renderizados por el servidor. | Baja-media; la página por ciudad ya incluye sesiones. |
| Cinépolis | [Sitio Colombia](https://cinepolis.com.co/) redirige desde `www` y muestra primero la selección de ciudad; la lista incluye Valledupar. | La página de inicio consultada no mostró funciones ni una URL JSON verificable antes de seleccionar ciudad. | Probablemente necesario para investigar el cambio de ciudad y la sesión; no está confirmado que sea necesario para consumir los horarios una vez localizada su solicitud. | Media; la cartelera depende de seleccionar una ciudad. |
| Royal Films | Se intentó consultar `https://www.royal-films.com/`. La solicitud desde este entorno no pudo completar la conexión TLS; no se verificó un dominio alternativo. | Sin respuesta verificable; endpoint y campos pendientes. | No evaluable todavía. | Pendiente hasta validar el sitio oficial y su disponibilidad. |
| Cineland | Se intentó consultar `https://www.cineland.com.co/`, pero el nombre de host no resolvió desde este entorno. No se verificó un dominio alternativo. | Sin respuesta verificable; endpoint y campos pendientes. | No evaluable todavía. | Pendiente hasta confirmar el dominio oficial y su disponibilidad. |

## Resultado y siguiente verificación

Para Cinemark, una ciudad consultada con cartelera poblada permitió implementar
una petición HTTP directa y leer el JSON incrustado, sin Playwright. La ruta
`/cartelera/valledupar` respondió, pero al momento de la consulta sus secciones
de cartelera estaban vacías; por eso ese resultado no acredita funciones de
Cinemark en Valledupar. Para los otros sitios todavía no se ha confirmado una
respuesta JSON con película, sala, hora y formato. Para completar el reconocimiento,
abrir cada cartelera en un navegador con acceso, seleccionar ciudad cuando
corresponda y registrar en Network la URL, método, parámetros, respuesta y
requisitos de sesión de las solicitudes que contienen las funciones. Mantener
las consultas manuales y espaciadas.

## Importar cartelera de Cinemark manualmente

Desde `backend`, ejecutar:

```powershell
python manage.py migrate
python manage.py scrape_cartelera --cine cinemark --ciudad bogota
```

El comando guarda únicamente las funciones cuyo título coincide de forma
inequívoca con una película del catálogo. Los títulos sin coincidencia (o con
coincidencias ambiguas) quedan en `TituloPendiente` para revisión; no se crean
fichas ficticias. Las ejecuciones posteriores actualizan las funciones
existentes en vez de duplicarlas. Se puede consultar otra ciudad pasando su slug
de Cinemark en `--ciudad`.

## Endpoints de lectura

- `GET /api/cines/` devuelve el catálogo paginado de cines.
- `GET /api/media/<id>/funciones/` devuelve funciones con la hora, la sala, el
  formato y la información del cine, junto con `ultima_actualizacion`.
- Se puede filtrar con `?cine=<id>&fecha=AAAA-MM-DD`. La fecha filtra las
  funciones; `ultima_actualizacion` representa la última actualización del
  conjunto de funciones de esa película y, si se especifica, ese cine. Cuando no
  existen funciones para la película (o cine) es `null`.
