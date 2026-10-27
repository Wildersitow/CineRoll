const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Retorna los datos de autenticación almacenados en localStorage.
 */
export function getStoredAuth() {
  try {
    const saved = localStorage.getItem('cineroll_auth');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

/**
 * Guarda los datos de autenticación en localStorage.
 */
export function setStoredAuth(authData) {
  if (authData) {
    localStorage.setItem('cineroll_auth', JSON.stringify(authData));
  } else {
    localStorage.removeItem('cineroll_auth');
  }
}

/**
 * Limpia la sesión de localStorage.
 */
export function clearStoredAuth() {
  localStorage.removeItem('cineroll_auth');
}

/**
 * Función genérica para realizar peticiones HTTP a la API Django.
 * Inyecta automáticamente el header `Authorization: Bearer <token>` si existe sesión.
 */
export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const auth = getStoredAuth();

  const headers = {
    'Content-Type': 'application/json',
    ...(auth?.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    ...options.headers,
  };

  const config = {
    ...options,
    headers,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch (networkError) {
    throw new Error('No se pudo conectar con el servidor Django (puerto 8000). Asegúrate de tener levantado el backend con: python manage.py runserver');
  }

  // Si el token expiró o no es válido (401), se limpia la sesión
  if (response.status === 401 && auth?.token) {
    clearStoredAuth();
  }

  return response;
}

/**
 * Realiza el inicio de sesión contra /api/usuario/login/
 */
export async function loginUser(usuario, clave) {
  const response = await fetch(`${API_BASE_URL}/usuario/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario, clave }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.error || 'Credenciales incorrectas');
  }

  const data = await response.json();
  setStoredAuth(data);
  return data;
}

/**
 * Valida el token actual y obtiene los datos del usuario autenticado contra /api/usuario/me/
 */
export async function getCurrentUser() {
  const response = await apiFetch('/usuario/me/');
  if (!response.ok) {
    throw new Error('Sesión no válida o expirada');
  }
  return await response.json();
}

/**
 * Refresca el token JWT usando /api/token/refresh/
 */
export async function refreshAccessToken() {
  const auth = getStoredAuth();
  if (!auth?.refresh) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: auth.refresh }),
    });

    if (response.ok) {
      const data = await response.json();
      const updatedAuth = {
        ...auth,
        token: data.access,
        access: data.access,
      };
      setStoredAuth(updatedAuth);
      return updatedAuth;
    }
  } catch {
    clearStoredAuth();
  }
  return null;
}
