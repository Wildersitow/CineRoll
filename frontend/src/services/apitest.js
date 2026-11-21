import { afterEach, expect, test, vi } from 'vitest'
import { apiFetch, getStoredAuth, setStoredAuth } from './api'

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

test('un refresh rechazado emite una sola notificación de sesión vencida', async () => {
  setStoredAuth({ token: 'anterior', refresh: 'vencido' })
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 401 }))
  const expired = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  window.addEventListener('cineroll:session-expired', expired)
  try {
    await apiFetch('/usuarios/me/')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(expired).toHaveBeenCalledTimes(1)
    expect(getStoredAuth()).toBeNull()
  } finally {
    window.removeEventListener('cineroll:session-expired', expired)
  }
})
