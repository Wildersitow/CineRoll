const API_BASE_URL = 'http://localhost:8000/api';

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
    const errObj = errorData?.error;
    let mensaje = errObj?.mensaje || 'Error al crear la cuenta.';
    if (errObj?.campos) {
      const detalles = Object.entries(errObj.campos)
        .map(([campo, errores]) => `${campo}: ${Array.isArray(errores) ? errores.join(' ') : errores}`)
        .join(' | ');
      mensaje = `${mensaje} (${detalles})`;
    }
    throw new Error(mensaje);
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
    const errObj = errorData?.error;
    let mensaje = errObj?.mensaje || 'Error al cambiar la contraseña.';
    if (errObj?.campos) {
      const detalles = Object.entries(errObj.campos)
        .map(([campo, errores]) => `${campo}: ${Array.isArray(errores) ? errores.join(' ') : errores}`)
        .join(' | ');
      mensaje = `${mensaje} (${detalles})`;
    }
    throw new Error(mensaje);
  }

  return await response.json();
}
