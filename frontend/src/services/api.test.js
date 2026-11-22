import { afterEach, expect, test, vi } from 'vitest'
import { apiFetch, getElementosDeLista, getStoredAuth, setStoredAuth } from './api'

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


test.each([
  [[{ media_id: 8 }]],
  [{ results: [{ media_id: 8 }], count: 1 }],
])('devuelve los elementos de una lista en ambos formatos de la API', async (payload) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(payload)))
  const result = await getElementosDeLista(1)
  expect(result.results).toEqual([{ media_id: 8 }])
})
