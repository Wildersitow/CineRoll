# Reconocimiento inicial de cartelera

Este reconocimiento cubre los pasos 1 y 2 asignados a la Persona 3. Se
consultaron los sitios públicos el 8 de noviembre de 2026. Para Cinépolis y Royal
Films se observó en Network la solicitud que entrega funciones y su respuesta.
En Cineland también se capturó en Network una respuesta de cartelera no vacía
para Valledupar, con títulos, fechas, formatos, salas y funciones.

El segundo scraper de la Fase 3 queda elegido: **Cinépolis**. La llamada de
Valledupar entrega películas, formatos y horarios agrupados por fecha en una
sola respuesta JSON, mientras que Royal Films requiere una llamada de funciones
por cada película.

Para los próximos estrenos de Cinemark, el modelo `Media` ya dispone de
`fecha_estreno` y del estado `PROXIMO_ESTRENO`. El scraper toma `OpeningDate`
de `UpcomingReleases` y actualiza esos campos solo si el título coincide de
forma única con una película existente; no crea películas nuevas cuando no hay
coincidencia.

Al final de cada ejecución, el comando elimina globalmente las funciones cuya
fecha y hora ya pasaron. Una película `EN_CARTELERA` pasa a `FUERA_CARTELERA`
solo si no le quedan funciones futuras en ningún cine; las películas
`PROXIMO_ESTRENO` no cambian por esta limpieza. La regla está en
`cines.services.cleanup_expired_showtimes`, reutilizable por una tarea programada.
La orquestación completa de scraping y persistencia está en
`cines.services.scrape_and_save_cartelera`; el comando de gestión solo la invoca
y presenta el resultado, y una futura tarea de Celery puede llamar al mismo
servicio.

| Cine | URL consultada y evidencia | Datos de funciones / endpoint JSON | ¿Playwright? | Dificultad inicial |
|---|---|---|---|---|
| Cinemark | [Cartelera por ciudad](https://www.cinemark.com.co/cartelera/bogota) respondió HTTP 200. El HTML de Next.js contiene `__NEXT_DATA__` con `PremieresBillboard` y `Presales`. | La respuesta incrustada incluye título (`TitleAlt`/`Title`), cine (`CinemaName`, `CinemaId`), identificador de función, hora ISO (`Showtime`), sala (`ScreenName`) y formato/idioma (`Attributes`). No se confirmó un endpoint JSON separado: la fuente del scraper es el HTML de cartelera. | No hace falta para la cartelera observada: una petición HTTP entrega los datos renderizados por el servidor. | Baja-media; la página por ciudad ya incluye sesiones. |
| Cinépolis | [Cartelera de Valledupar](https://cinepolis.com.co/cartelera/valledupar-colombia). | `POST /Cartelera.aspx/GetNowPlayingByCity` devuelve JSON con películas, formatos y funciones: 18 fechas, 41 películas y 176 horarios en la captura. Elegido para el segundo scraper de Fase 3. Detalle abajo. | Sí para seleccionar la ciudad; la respuesta de cartelera observada es JSON y puede consultarse directamente. | Media; se requiere la clave de ciudad. |
| Royal Films | [Cartelera de Valledupar](https://cinemasroyalfilms.com/cartelera/valledupar). | `GET /api/billboard/city/1006` devuelve 13 películas. La aplicación consulta `/api/movies/functions/{peliculaId}/city/1006` por película; las respuestas contienen funciones en JSON. | Sí para seleccionar Colombia y Valledupar; luego las solicitudes observadas son GET. | Media; requiere varias solicitudes, una por película. |
| Cineland | [Aplicación web](https://home.cineland.co/), ruta observada `#/cartelera/valledupar`. | `POST https://cineland.website/api_point_back.php` recibe rango de fechas y código de teatro; la respuesta contiene 9 películas con fechas, formatos, salas y horarios. Detalle abajo. | Sí para seleccionar la ciudad; la respuesta de cartelera es JSON y puede consultarse directamente. | Media; endpoint genérico compartido con otras operaciones, y respuesta servida como JSON con content type `text/html`. |

## Evidencia de Network

### Cinépolis

1. La carga de complejos fue `POST
   https://cinepolis.com.co/manejadores/CiudadesComplejos.ashx?EsVIP=false`,
   con cuerpo `{}`. Respondió `200 application/json; charset=utf-8`; Valledupar
   aparece con clave `valledupar-colombia` y el complejo Cinépolis Mega Mall
   (clave `cinepolis-mega-mall`).
2. Al abrir la cartelera de Valledupar se observó
   `POST https://cinepolis.com.co/Cartelera.aspx/GetNowPlayingByCity`, con cuerpo
   `{"claveCiudad":"valledupar-colombia","esVIP":false}`. Respondió
   `200 application/json; charset=utf-8`.
3. La respuesta usa el objeto `d`, con `Cinemas[]`; cada complejo contiene
   `Dates[]`, que contiene `Movies[]`, `Formats[]` y `Showtimes[]`. Se observaron
   identificadores y nombres de cine, título (`Title`, `OriginalTitle`), formato
   (`Name`), idioma (`Language`) y, por horario, `CinemaId`, `VistaCinemaId`,
   `ShowtimeId`, `TimeFilter`, `Time` y `ShowtimeAMPM`. Ejemplo: *Clayface*,
   formato `DOB`, idioma `DOBLADA`, horarios 16:00, 18:30 y 21:00.
4. La captura resumida correspondió a un complejo (ID `577`), 18 fechas, 41
   películas y 176 horarios. Los horarios y cantidades cambian con la cartelera.
5. Se repitió la petición el 13 de noviembre de 2026 con el mismo cuerpo. La
   respuesta `200 application/json` incluyó un complejo, 20 fechas, 52 películas,
   67 formatos y 210 horarios. Se guardó un recorte de una función real en
   `cines/fixtures/cinepolis_valledupar_sample.json`: *Cómo robar un banco*,
   formato `DOB` + `DOBLADA`, `ShowtimeId` `64989` y `CinemaId` `577`.

### Cinemark: próximos estrenos

La respuesta HTML de [la cartelera de Bogotá](https://www.cinemark.com.co/cartelera/bogota)
incluye `UpcomingReleases` dentro de `props.pageProps` en `__NEXT_DATA__`.
La captura del 8 de noviembre de 2026 incluyó 29 títulos; cada uno tenía
`OpeningDate` (por ejemplo, `2026-11-12T00:00:00`) y cero funciones en `Sessions`.
El scraper procesa esta sección junto con los horarios en la misma descarga y
usa `OpeningDate` como fecha local de estreno.

### Royal Films

1. El sitio oficial observado fue `https://cinemasroyalfilms.com/`. Tras elegir
   Colombia y Valledupar, la aplicación abrió
   `https://cinemasroyalfilms.com/cartelera/valledupar`; el ID de ciudad usado
   en la API es `1006`.
2. `GET https://cinemasroyalfilms.com/api/cinemas/city/1006` respondió 200.
   También se observaron `GET /api/billboard/city/1006` y respuestas
   `200 application/json; charset=utf-8`. La cartelera devolvió 13 películas.
3. Para cada película se observó
   `GET /api/movies/functions/{peliculaId}/city/1006`, también con respuesta
   `200 application/json; charset=utf-8`. La respuesta tiene `status` y `data`;
   `data` es una lista de funciones. Sus campos incluyen `funcion_id`,
   `funcion_fecha`, `funcion_pelicula_id`, `funcion_multicine_id`,
   `funcion_sala_id`, `funcion_hora_inicio` y `funcion_enumerada`, además de
   `formato.formato_nombre`, `multicine.multicine_nombre` y `sala.sala_nombre`.
4. Ejemplo observado para la película `4206`: `data` contenía 9 funciones; una
   de ellas tenía fecha `2026-11-12`, hora `16:30`, formato `2D`, cine
   Multicine Unicentro Valledupar y sala `SALA 2 STD`. La hora se entrega como
   fecha ISO (`1970-01-01T16:30:00.000Z`) separada de `funcion_fecha`.
5. El scraper consulta el listado y, secuencialmente, el endpoint de funciones
   de cada película, esperando un segundo antes de cada consulta secundaria.
   Conserva la hora y los minutos de `funcion_hora_inicio` tal cual (sin
   conversión de zona) y los combina con `funcion_fecha`.

### Títulos y calificadores de exhibición

En las muestras revisadas, Cinépolis separa `Title` y `OriginalTitle`, Royal
Films entrega `pelicula_titulo` y `pelicula_nombre_original`, y Cineland entrega
`nombre_pelicula_original` y `nombre_pelicula`. No se observaron nuevos sufijos
en los títulos: `3D`, `DOB` y `SUB` ya están contemplados por
`TITLE_QUALIFIERS`; además, aparecen como formato o idioma de función. Cinépolis
y Royal conservan el título alternativo cuando difiere del principal. Cineland
aún no tiene scraper implementado.

### Cineland

1. El dominio que cargó la aplicación fue `https://home.cineland.co/`. Al
   seleccionar Valledupar se abrió `#/cartelera/valledupar`. La página mostró
   títulos, fechas, cine (C.C. Mayales), formatos, salas y horarios.
2. Al seleccionar Valledupar el navegador envió
   `POST https://cineland.website/api_point_back.php`, con JSON
   `{"fechacon1":"2026-11-08","fechacon2":"2026-11-08","codteatro":"0051"}`.
   La respuesta observada en esa primera carga fue
   `200 text/html; charset=UTF-8`, con claves `data`, `count` y
   `transaction_status`; `data` fue `[]` en esa consulta inicial.
3. Al abrir una película se observó
   `POST https://cineland.website/api_point_back.php` con parámetro JSON
   `codpel` (ejemplo `260920`). Respondió `200 text/html; charset=UTF-8` con un
   objeto JSON de metadatos de película (`data`, `count`,
   `transaction_status`); esta llamada no era la respuesta de horarios.
4. Al volver a seleccionar Valledupar desde otra ciudad, el mismo endpoint
   respondió `200 text/html; charset=UTF-8` con 9 películas. La forma de cada
   película es `nombre_pelicula_original`, `url_imagen_pelicula`, `genero`,
   `clasificacion`, `movie_status` y `fechas[]`. Cada fecha tiene `date`,
   `preventa` y `atributos[]`; cada atributo contiene `codigo_pelicula`,
   `nombre_pelicula`, `atributos_pelicula` y `salas[]`. Cada sala contiene
   `codigo_sala`, `nombre_sala` y `funciones_y_tarifas[]`, con `funcion` y
   `tarifa`.
5. Ejemplo observado: *AVENGERS DOOMSDAY*, fecha `2026-11-08`, con formatos
   `3D DOBLADA` y `DIGITAL DOBLADA`, salas 2, 3 y HS, y horarios entre 13:30 y
   20:50. No se anotan valores de sesión.
6. Las solicitudes `GET https://cms.cineland.co/api/slider` y
   `GET https://cms.cineland.co/api/banners` respondieron 504 en esa sesión; son
   recursos de la página y no se identificaron como fuentes de funciones.

## Resultado y siguiente verificación

Para Cinemark, una ciudad consultada con cartelera poblada permitió implementar
una petición HTTP directa y leer el JSON incrustado, sin Playwright. La ruta
`/cartelera/valledupar` respondió, pero al momento de la consulta sus secciones
de cartelera estaban vacías; por eso ese resultado no acredita funciones de
Cinemark en Valledupar. Cinépolis queda elegido como segundo scraper de la
Fase 3: su respuesta confirmada entrega en una llamada los horarios completos
de la ciudad. Royal Films también es viable, aunque requiere consultar las
funciones película por película. En Cineland se reconocieron el dominio, el
endpoint de cartelera, sus parámetros y el esquema de la respuesta con
funciones. No se implementó ningún scraper adicional para esos cines en este
paso.
El scraper de Cinemark también lee
`UpcomingReleases`; el comando actualiza las fechas y el estado de las películas
que ya existen en `Media` y muestra los títulos sin coincidencia para revisión,
sin crear fichas automáticamente.

## Decisión sobre Playwright

Por ahora no se agrega Playwright ni otra dependencia de navegador. En los cuatro
sitios reconocidos, la información de funciones se puede obtener con peticiones
HTTP directas: HTML con datos incrustados en Cinemark y respuestas JSON en
Cinépolis, Royal Films y Cineland. El navegador sirvió para descubrir las
solicitudes y seleccionar ciudades durante el reconocimiento, pero no es
necesario para ejecutar esas peticiones. Se reconsiderará Playwright solo si un
proveedor deja de exponer los datos por HTTP directo y exige renderizado,
interacción o estado de navegador para obtenerlos.

## Ciudades canónicas

El servicio recibe el slug canónico y lo traduce a la clave que requiere cada
proveedor. Las funciones y los títulos pendientes se guardan usando ese slug en
`Cine.ciudad` y `TituloPendiente.ciudad`, de modo que
`/api/funciones/?ciudad=valledupar` reúne funciones de los cines configurados
para Valledupar.

| Ciudad canónica | Cinemark | Cinépolis | Royal Films | Cineland |
|---|---|---|---|---|
| `valledupar` | No habilitado: no se observaron funciones | `valledupar-colombia` | `1006` | `0051` |
| `bogota` | `bogota` (solo manual; no programado) | — | — | — |

Cinemark se conserva configurado, pero no está asociado a Valledupar. La clave
`bogota` se mantiene para ejecuciones manuales del scraper; no se programa una
ciudad de Cinemark hasta verificar que devuelve funciones. En esta fase todavía
no hay una programación periódica de scraping configurada.

## Importar cartelera de Cinemark manualmente

Desde `backend`, ejecutar:

```powershell
python manage.py migrate
python manage.py scrape_cartelera --cine cinemark --ciudad bogota
```

Cada ejecución también elimina funciones vencidas y recalcula el estado de
cartelera según las funciones futuras que queden en todos los cines. Esta
limpieza es inmediata; no depende de Celery.

Tras un scrape con funciones válidas, se eliminan las funciones futuras de ese
proveedor y ciudad que ya no aparecen en la fuente; el cine, película, fecha,
hora, sala y formato identifican cada función. Si la respuesta viene vacía o
contiene menos del 50% de las funciones futuras previamente guardadas y
asociadas al catálogo, no se borran funciones y se registra una advertencia.
Una respuesta exactamente igual al 50% sí permite sincronizar.

El comando guarda únicamente las funciones cuyo título coincide de forma
inequívoca con una película del catálogo. Los títulos sin coincidencia (o con
coincidencias ambiguas) quedan en `TituloPendiente` para revisión; no se crean
fichas ficticias. Las ejecuciones posteriores actualizan las funciones
existentes en vez de duplicarlas. Se puede consultar otra ciudad pasando su slug
canónico configurado en `--ciudad`.

## Endpoints de lectura

- `GET /api/cines/` devuelve el catálogo paginado de cines. `POST` en esa ruta y
  `PUT`, `PATCH` o `DELETE /api/cines/<id>/` requieren un usuario administrador
  (`is_staff`); las lecturas siguen siendo públicas.
- `GET /api/cines/<id>/funciones/` devuelve las funciones de hoy de ese cine;
  acepta `?fecha=AAAA-MM-DD` para otra fecha.
- `GET /api/funciones/` devuelve las funciones de hoy y acepta los filtros
  `?fecha=AAAA-MM-DD&ciudad=<ciudad>`. `fecha=hoy` y omitir `fecha` significan
  hoy en `America/Bogota`; la ciudad se compara sin distinguir mayúsculas y
  minúsculas con `Cine.ciudad`.
- Ambos endpoints devuelven todos los resultados en una sola respuesta bajo la
  clave `resultados` (sin paginación), para que el home cargue la cartelera
  diaria o la de un cine con una llamada.
- `GET /api/media/<id>/funciones/` devuelve funciones con la hora, la sala, el
  formato y la información del cine, junto con `ultima_actualizacion`.
- Se puede filtrar con `?cine=<id>&fecha=AAAA-MM-DD`. La fecha filtra las
  funciones; `ultima_actualizacion` representa la última actualización del
  conjunto de funciones de esa película y, si se especifica, ese cine. Cuando no
  existen funciones para la película (o cine) es `null`.
- El listado de catálogo `GET /api/media/?cine=<id>` filtra películas a través
  de la relación `Media.funciones` → `Funcion.cine`; el identificador debe ser
  un entero positivo y el resultado no repite películas aunque tengan varias
  funciones en ese cine.
