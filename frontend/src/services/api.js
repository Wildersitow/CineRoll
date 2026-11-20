const API_BASE_URL = (import.meta.env && import.meta.env.VITE_API_URL)
  ? import.meta.env.VITE_API_URL
  : 'http://localhost:8000/api';

const FIELD_LABELS = {
  username: 'Usuario',
  email: 'Correo',
  password: 'Contraseña',
  clave_actual: 'Contraseña actual',
  clave_nueva: 'Nueva contraseña',
  first_name: 'Nombre',
  last_name: 'Apellido',
};

function formatApiError(errObj, fallback) {
  if (errObj?.campos) {
    const detalles = Object.entries(errObj.campos)
      .map(([campo, errores]) => `${FIELD_LABELS[campo] || campo}: ${Array.isArray(errores) ? errores.join(' ') : errores}`)
      .join(' | ');
    if (detalles) return detalles;
  }
  return errObj?.mensaje || fallback;
}

/**
 * Retorna los datos de autenticación almacenados en localStorage o sessionStorage.
 */
export function getStoredAuth() {
  try {
    const saved = localStorage.getItem('cineroll_auth') || sessionStorage.getItem('cineroll_auth');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

/**
 * Guarda los datos de autenticación.
 * Si rememberMe es true, se guarda en localStorage (persiste tras cerrar el navegador).
 * Si rememberMe es false, se guarda en sessionStorage (solo dura la sesión actual).
 */
export function setStoredAuth(authData, rememberMe = false) {
  if (authData) {
    const dataStr = JSON.stringify(authData);
    if (rememberMe) {
      localStorage.setItem('cineroll_auth', dataStr);
      sessionStorage.removeItem('cineroll_auth');
    } else {
      sessionStorage.setItem('cineroll_auth', dataStr);
      localStorage.removeItem('cineroll_auth');
    }
  } else {
    clearStoredAuth();
  }
}

/**
 * Limpia la sesión de ambos almacenamientos.
 */
export function clearStoredAuth() {
  localStorage.removeItem('cineroll_auth');
  sessionStorage.removeItem('cineroll_auth');
}

/**
 * Refresca el token JWT usando /api/auth/refresh/.
 */
export async function refreshAccessToken() {
  const auth = getStoredAuth();
  if (!auth?.refresh) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: auth.refresh }),
    });

    if (response.ok) {
      const data = await response.json();
      const isPersistent = Boolean(localStorage.getItem('cineroll_auth'));
      const updatedAuth = {
        ...auth,
        token: data.access,
        access: data.access,
        // Si rotó el refresh token, guardamos el nuevo
        ...(data.refresh ? { refresh: data.refresh } : {}),
      };
      setStoredAuth(updatedAuth, isPersistent);
      return updatedAuth;
    }
  } catch {
    // Si falla la petición de refresco, se invalidará la sesión
  }

  clearStoredAuth();
  notifySessionExpired();
  return null;
}

/**
 * Función genérica para realizar peticiones HTTP a la API Django.
 * Inyecta automáticamente el header `Authorization: Bearer <token>` si existe sesión.
 * Si recibe 401 y hay un refresh token, intenta refrescar automáticamente y reintentar la petición.
 */
export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  let auth = getStoredAuth();

  const headers = {
    'Content-Type': 'application/json',
    ...(auth?.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch {
    throw new Error('No se pudo conectar con el servidor Django (puerto 8000). Asegúrate de tener levantado el backend con: python manage.py runserver');
  }

  // Si el token expiró (401), intentamos refrescarlo y reintentar una vez
  if (response.status === 401 && auth?.refresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed?.token) {
      const retryHeaders = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${refreshed.token}`,
        ...options.headers,
      };
      try {
        response = await fetch(url, { ...options, headers: retryHeaders });
      } catch {
        throw new Error('No se pudo conectar con el servidor Django.');
      }
      if (response.status === 401) {
        clearStoredAuth();
        notifySessionExpired();
      }
    } else {
      clearStoredAuth();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('cineroll:sesion-vencida'));
      }
    }
  } else if (response.status === 401) {
    clearStoredAuth();
    notifySessionExpired();
  }

  return response;
}


/**
 * Inicia sesión contra /api/auth/login/
 */
export async function loginUser(usuario, clave, rememberMe = false) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ usuario, clave }),
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor Django (puerto 8000). Asegúrate de tener levantado el backend con: python manage.py runserver');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const mensaje = errorData?.error?.mensaje || 'Credenciales incorrectas.';
    throw new Error(mensaje);
  }

  const data = await response.json();
  setStoredAuth(data, rememberMe);
  return data;
}

/**
 * Registra un nuevo usuario contra /api/auth/registro/
 */
export async function registerUser({ username, email, password, first_name = '', last_name = '' }, rememberMe = false) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/registro/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        email,
        password,
        first_name,
        last_name,
      }),
    });
  } catch {
    throw new Error('No se pudo conectar con el servidor Django (puerto 8000). Asegúrate de tener levantado el backend con: python manage.py runserver');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al crear la cuenta.'));
  }

  const data = await response.json();
  setStoredAuth(data, rememberMe);
  return data;
}

/**
 * Cierra la sesión de forma segura invalidando el refresh token en /api/auth/logout/
 */
export async function logoutUser() {
  const auth = getStoredAuth();
  if (auth?.refresh) {
    try {
      await fetch(`${API_BASE_URL}/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
        },
        body: JSON.stringify({ refresh: auth.refresh }),
      });
    } catch {
      // Si falla la red, la sesión se limpia localmente de todos modos
    }
  }
  clearStoredAuth();
}

/**
 * Valida el token actual y obtiene los datos del perfil propio desde /api/usuarios/me/
 */
export async function getCurrentUser() {
  const response = await apiFetch('/usuarios/me/');
  if (!response.ok) {
    throw new Error('Sesión no válida o expirada');
  }
  return await response.json();
}

/**
 * Cambia la contraseña del usuario autenticado en /api/usuarios/me/clave/
 */
export async function changePassword(claveActual, claveNueva) {
  return leerJson('/usuarios/me/clave/', {
    method: 'POST',
    body: JSON.stringify({
      clave_actual: claveActual,
      clave_nueva: claveNueva,
    }),
  }, 'Error al cambiar la contraseña.');
}

/**
 * Actualiza los datos del perfil propio (nombre, apellido, biografía, avatar, escala)
 * mediante PATCH a /api/usuarios/me/.
 */
export async function updateProfile(datos) {
  const data = await leerJson('/usuarios/me/', {
    method: 'PATCH',
    body: JSON.stringify(datos),
  }, 'Error al actualizar el perfil.');

  const auth = getStoredAuth();
  if (auth) {
    const isPersistent = Boolean(localStorage.getItem('cineroll_auth'));
    setStoredAuth({ ...auth, ...data }, isPersistent);
  }
  return data;
}

/**
 * Helper centralizado para consultar endpoints con manejo uniforme de errores y JSON.
 */
export async function leerJson(endpoint, options = {}, mensajeFallback = 'Error en la solicitud.') {
  let opts = options;
  let fallback = mensajeFallback;
  if (typeof options === 'string') {
    fallback = options;
    opts = {};
  }
  const response = await apiFetch(endpoint, opts);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, fallback));
  }
  if (response.status === 204) {
    return true;
  }
  return await response.json();
}

/**
 * Convierte un objeto de parámetros en una query string URL válida.
 */
export function buildQueryString(params = {}) {
  const entries = Object.entries(params).filter(
    ([, val]) => val !== undefined && val !== null && val !== ''
  );
  if (!entries.length) return '';
  const searchParams = new URLSearchParams();
  for (const [key, val] of entries) {
    searchParams.append(key, val);
  }
  return `?${searchParams.toString()}`;
}

/* ==========================================================================
   Catálogo y Personas
   ========================================================================== */

/**
 * Obtiene el listado de títulos desde /api/media/.
 * Filtros: { buscar, tipo, genero, anio, estado, cine, ordenar, page }
 */
export async function getMedia(params = {}) {
  return leerJson(`/media/${buildQueryString(params)}`, 'Error al obtener el catálogo de media.');
}

/**
 * Obtiene la ficha completa de un título desde /api/media/<id>/.
 */
export async function getMediaDetalle(id) {
  return leerJson(`/media/${id}/`, 'Error al obtener el detalle del título.');
}

/**
 * Obtiene la ficha de una persona con su filmografía desde /api/personas/<id>/.
 */
export async function getPersona(id) {
  return leerJson(`/personas/${id}/`, 'Error al obtener los datos de la persona.');
}

/* ==========================================================================
   Cartelera y Cines
   ========================================================================== */

/**
 * Obtiene las funciones en cartelera desde /api/funciones/.
 * Filtros: { ciudad, fecha, cine }
 */
export async function getFunciones(params = {}) {
  return leerJson(`/funciones/${buildQueryString(params)}`, 'Error al obtener las funciones en cartelera.');
}

export async function getFuncionesDeCine(cineId, params = {}) {
  return leerJson(`/cines/${cineId}/funciones/${buildQueryString(params)}`, 'Error al obtener las funciones del cine.');
}

export async function getFuncionesDeMedia(mediaId, params = {}) {
  return leerJson(`/media/${mediaId}/funciones/${buildQueryString(params)}`, 'Error al obtener las funciones del título.');
}

/**
 * Obtiene el listado de cines registrados desde /api/cines/.
 * Filtros: { ciudad }
 */
export async function getCines(params = {}) {
  return leerJson(`/cines/${buildQueryString(params)}`, 'Error al obtener los cines.');
}

/**
 * Consulta el estado de frescura de la cartelera por cine desde /api/cartelera/estado/.
 */
export async function getEstadoCartelera() {
  return leerJson('/cartelera/estado/', 'Error al consultar el estado de la cartelera.');
}

/* ==========================================================================
   Reseñas y Puntuaciones
   ========================================================================== */

export async function getResenasDeMedia(mediaId, params = {}) {
  return leerJson(`/media/${mediaId}/resenas/${buildQueryString(params)}`, 'Error al obtener las reseñas del título.');
}

export async function getMiResena(mediaId) {
  return leerJson(`/media/${mediaId}/resenas/propia/`, 'Error al obtener tu reseña.');
}

export async function crearResena(mediaId, { puntuacion, texto = '' }) {
  return leerJson(`/media/${mediaId}/resenas/`, {
    method: 'POST',
    body: JSON.stringify({ puntuacion, texto }),
  }, 'Error al publicar la reseña.');
}

export async function editarResena(resenaId, { puntuacion, texto }) {
  return leerJson(`/resenas/${resenaId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ puntuacion, texto }),
  }, 'Error al actualizar la reseña.');
}

export async function borrarResena(resenaId) {
  return leerJson(`/resenas/${resenaId}/`, {
    method: 'DELETE',
  }, 'Error al eliminar la reseña.');
}

export async function getResumenResenas(mediaId) {
  return leerJson(`/media/${mediaId}/resenas/resumen/`, 'Error al obtener el resumen de puntuación.');
}

export async function getResenasDeUsuario(username, params = {}) {
  return leerJson(`/usuarios/${username}/resenas/${buildQueryString(params)}`, `Error al obtener las reseñas de @${username}.`);
}

/* ==========================================================================
   Perfil Público y Seguimiento
   ========================================================================== */

export async function getPerfilPublico(username) {
  return leerJson(`/usuarios/${username}/`, `Error al obtener el perfil de @${username}.`);
}

export async function seguirUsuario(username) {
  return leerJson(`/usuarios/${username}/seguir/`, {
    method: 'POST',
  }, `Error al seguir a @${username}.`);
}

export async function dejarDeSeguir(username) {
  return leerJson(`/usuarios/${username}/seguir/`, {
    method: 'DELETE',
  }, `Error al dejar de seguir a @${username}.`);
}

export async function getSeguidores(username, params = {}) {
  return leerJson(`/usuarios/${username}/seguidores/${buildQueryString(params)}`, `Error al obtener seguidores de @${username}.`);
}

export async function getSiguiendo(username, params = {}) {
  return leerJson(`/usuarios/${username}/siguiendo/${buildQueryString(params)}`, `Error al obtener seguidos de @${username}.`);
}

export async function getFeed(params = {}) {
  return leerJson(`/usuarios/me/feed/${buildQueryString(params)}`, 'Error al obtener el feed de actividad.');
}

/* ==========================================================================
   Sugerencias de Edición
   ========================================================================== */

export async function crearSugerencia(mediaId, { campo, valor_propuesto, motivo = '' }) {
  return leerJson(`/media/${mediaId}/sugerencias/`, {
    method: 'POST',
    body: JSON.stringify({ campo, valor_propuesto, motivo }),
  }, 'Error al enviar la sugerencia de edición.');
}

export async function getMisSugerencias(params = {}) {
  return leerJson(`/usuarios/me/sugerencias/${buildQueryString(params)}`, 'Error al obtener tus sugerencias.');
}

/* ==========================================================================
   Listas de Usuario
   ========================================================================== */

export async function getListas(params = {}) {
  return leerJson(`/listas/${buildQueryString(params)}`, 'Error al obtener las listas.');
}

export async function getListaDetalle(id) {
  return leerJson(`/listas/${id}/`, 'Error al obtener la lista.');
}

export async function createLista(listaData) {
  return leerJson('/listas/', {
    method: 'POST',
    body: JSON.stringify(listaData),
  }, 'Error al crear la lista.');
}

export async function updateLista(id, listaData) {
  return leerJson(`/listas/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(listaData),
  }, 'Error al actualizar la lista.');
}

export async function deleteLista(id) {
  return leerJson(`/listas/${id}/`, {
    method: 'DELETE',
  }, 'Error al eliminar la lista.');
}

export async function addTituloToLista(listaId, mediaId, orden = 0) {
  return leerJson(`/listas/${listaId}/elementos/`, {
    method: 'POST',
    body: JSON.stringify({ media_id: mediaId, orden }),
  }, 'Error al agregar el título a la lista.');
}

export async function removeTituloFromLista(listaId, mediaId) {
  return leerJson(`/listas/${listaId}/elementos/${mediaId}/`, {
    method: 'DELETE',
  }, 'Error al quitar el título de la lista.');
}

export async function getUsuarioListas(username, params = {}) {
  return leerJson(`/usuarios/${username}/listas/${buildQueryString(params)}`, `Error al obtener las listas de @${username}.`);
}

/**
 * Obtiene las sugerencias de edición para un título desde /api/media/<id>/sugerencias/.
 */
export async function getSugerenciasMedia(mediaId, params = {}) {
  return leerJson(
    `/media/${mediaId}/sugerencias/${buildQueryString(params)}`,
    'Error al obtener las sugerencias de edición.'
  );
}

/**
 * Crea una nueva sugerencia de edición para un título en /api/media/<id>/sugerencias/.
 */
export async function crearSugerenciaEdicion(mediaId, sugerencia) {
  const response = await apiFetch(`/media/${mediaId}/sugerencias/`, {
    method: 'POST',
    body: JSON.stringify(sugerencia),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al enviar la sugerencia de edición.'));
  }
  return await response.json();
}

/**
 * Obtiene todas las sugerencias para moderación desde /api/sugerencias/.
 * Filtros: { estado, media, page }.
 */
export async function getSugerenciasModeracion(params = {}) {
  return leerJson(
    `/sugerencias/${buildQueryString(params)}`,
    'Error al obtener las sugerencias.'
  );
}

export async function getSugerenciasPendientes(params = {}) {
  return getSugerenciasModeracion({ ...params, estado: 'pendiente' });
}

/**
 * Aprueba una sugerencia en /api/sugerencias/<id>/aprobar/.
 */
export async function aprobarSugerencia(sugerenciaId) {
  const response = await apiFetch(`/sugerencias/${sugerenciaId}/aprobar/`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al aprobar la sugerencia.'));
  }
  return await response.json();
}

/**
 * Rechaza una sugerencia en /api/sugerencias/<id>/rechazar/.
 */
export async function rechazarSugerencia(sugerenciaId, motivoRechazo = '') {
  const response = await apiFetch(`/sugerencias/${sugerenciaId}/rechazar/`, {
    method: 'POST',
    body: JSON.stringify({ motivo_rechazo: motivoRechazo }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al rechazar la sugerencia.'));
  }
  return await response.json();
}

/**
 * Notifica que la sesión ha expirado, disparando un evento global.
 */
export function notifySessionExpired() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('cineroll:session-expired'))
  }
}

export async function getMisListasDeMedia(mediaId) {
  return leerJson(`/media/${mediaId}/mis-listas/`, 'Error al consultar las listas para este título.');
}
