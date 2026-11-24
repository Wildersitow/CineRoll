import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { addTituloToLista, getElementosDeLista, getListas, getMedia, removeTituloFromLista } from '../services/api'
import FavoritasEditor from './FavoritasEditor'

vi.mock('../services/api', () => ({
  getListas: vi.fn(), getElementosDeLista: vi.fn(), getMedia: vi.fn(),
  addTituloToLista: vi.fn(), removeTituloFromLista: vi.fn(),
}))

beforeEach(() => {
  vi.resetAllMocks()
  getListas.mockResolvedValue({ results: [{ id: 5, tipo: 'favoritas' }] })
  getElementosDeLista.mockResolvedValue({ results: [{ id: 1, media_id: 3, media_titulo: 'Coco', media_poster_url: '' }] })
})

test('muestra las favoritas y permite quitar una', async () => {
  removeTituloFromLista.mockResolvedValue(null)
  render(<FavoritasEditor username="ana" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Quitar Coco de favoritas' }))
  expect(removeTituloFromLista).toHaveBeenCalledWith(5, 3)
  expect(await screen.findAllByRole('button', { name: 'Añadir una favorita' })).toHaveLength(1)
  expect(screen.queryByText('Coco')).not.toBeInTheDocument()
})

test('busca un título y lo añade en el siguiente hueco', async () => {
  getMedia.mockResolvedValue({ results: [{ id: 3, titulo: 'Coco' }, { id: 8, titulo: 'Dune', poster_url: '', fecha_estreno: '2021-10-21' }] })
  addTituloToLista.mockResolvedValue({})
  render(<FavoritasEditor username="ana" />)
  fireEvent.click(await screen.findByRole('button', { name: 'Añadir una favorita' }))
  fireEvent.change(screen.getByLabelText('Buscar título'), { target: { value: 'du' } })
  // Coco ya está en favoritas, así que no se ofrece de nuevo.
  fireEvent.click(await screen.findByRole('button', { name: /Dune/ }))
  expect(addTituloToLista).toHaveBeenCalledWith(5, 8, 1)
  expect(await screen.findByRole('button', { name: 'Quitar Dune de favoritas' })).toBeInTheDocument()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})
