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
    } else {
      clearStoredAuth();
    }
  } else if (response.status === 401) {
    clearStoredAuth();
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
  const response = await apiFetch('/usuarios/me/clave/', {
    method: 'POST',
    body: JSON.stringify({
      clave_actual: claveActual,
      clave_nueva: claveNueva,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al cambiar la contraseña.'));
  }

  return await response.json();
}


/**
 * Convierte un objeto de parámetros en una query string URL válida.
 */
function buildQueryString(params = {}) {
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

/**
 * Obtiene el listado de películas, series y anime desde /api/media/.
 * Admite filtros: { buscar, tipo, genero, anio, estado, cine, ordenar, page }
 */
export async function getMedia(params = {}) {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/media/${qs}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener el catálogo de media.'));
  }
  return await response.json();
}

/**
 * Obtiene la ficha completa de un título desde /api/media/<id>/.
 */
export async function getMediaDetalle(id) {
  const response = await apiFetch(`/media/${id}/`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener el detalle del título.'));
  }
  return await response.json();
}

/**
 * Obtiene las funciones de cartelera desde /api/funciones/.
 * Admite filtros: { ciudad, cine, fecha, formato, page }
 */
export async function getFunciones(params = {}) {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/funciones/${qs}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener las funciones en cartelera.'));
  }
  return await response.json();
}

/**
 * Obtiene el listado de cines registrados desde /api/cines/.
 * Admite filtro: { ciudad }
 */
export async function getCines(params = {}) {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/cines/${qs}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener los cines.'));
  }
  return await response.json();
}

/**
 * Obtiene la ficha de una persona (actor, director) con su filmografía desde /api/personas/<id>/.
 */
export async function getPersona(id) {
  const response = await apiFetch(`/personas/${id}/`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener los datos de la persona.'));
  }
  return await response.json();
}

/**
 * Obtiene las listas de usuarios desde /api/listas/.
 * Admite filtros: { usuario, usuario_id, tipo }
 */
export async function getListas(params = {}) {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/listas/${qs}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener las listas.'));
  }
  return await response.json();
}

/**
 * Obtiene el detalle de una lista con sus elementos desde /api/listas/<id>/.
 */
export async function getListaDetalle(id) {
  const response = await apiFetch(`/listas/${id}/`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al obtener la lista.'));
  }
  return await response.json();
}

/**
 * Crea una nueva lista para el usuario autenticado en /api/listas/.
 */
export async function createLista(listaData) {
  const response = await apiFetch('/listas/', {
    method: 'POST',
    body: JSON.stringify(listaData),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al crear la lista.'));
  }
  return await response.json();
}

/**
 * Modifica una lista propia en /api/listas/<id>/.
 */
export async function updateLista(id, listaData) {
  const response = await apiFetch(`/listas/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(listaData),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al actualizar la lista.'));
  }
  return await response.json();
}

/**
 * Elimina una lista propia en /api/listas/<id>/.
 */
export async function deleteLista(id) {
  const response = await apiFetch(`/listas/${id}/`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al eliminar la lista.'));
  }
  return true;
}

/**
 * Agrega un título de Media a una lista en /api/listas/<listaId>/elementos/.
 */
export async function addTituloToLista(listaId, mediaId, orden = 0) {
  const response = await apiFetch(`/listas/${listaId}/elementos/`, {
    method: 'POST',
    body: JSON.stringify({ media_id: mediaId, orden }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al agregar el título a la lista.'));
  }
  return await response.json();
}

/**
 * Quita un título de Media de una lista en /api/listas/<listaId>/elementos/<mediaId>/.
 */
export async function removeTituloFromLista(listaId, mediaId) {
  const response = await apiFetch(`/listas/${listaId}/elementos/${mediaId}/`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, 'Error al quitar el título de la lista.'));
  }
  return true;
}

/**
 * Obtiene las listas públicas de un usuario específico desde /api/usuarios/<username>/listas/.
 */
export async function getUsuarioListas(username) {
  const response = await apiFetch(`/usuarios/${username}/listas/`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(formatApiError(errorData?.error, `Error al obtener las listas de @${username}.`));
  }
  return await response.json();
}


