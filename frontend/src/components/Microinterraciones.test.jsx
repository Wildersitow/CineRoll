import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { Heart } from './FilmActions'
import Pagination from './Pagination'
import { leerJson } from '../services/api'

vi.mock('../services/api', () => ({ leerJson: vi.fn() }))

describe('Heart', () => {
  it('marca el like al instante y suma uno al contador', async () => {
    leerJson.mockResolvedValue({ me_gusta: true, total_likes: 4 })
    render(<MemoryRouter><Heart review={{ id: 9, total_likes: 3, me_gusta: false }} user={{ username: 'ana' }} /></MemoryRouter>)
    const boton = screen.getByRole('button', { name: 'Me gusta' })
    expect(boton).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(boton)
    expect(boton).toHaveAttribute('aria-pressed', 'true')
    expect(await screen.findByText('4')).toBeInTheDocument()
    expect(leerJson).toHaveBeenCalledWith('/resenas/9/like/', { method: 'PUT' })
  })

  it('vuelve al estado anterior si falla la petición', async () => {
    leerJson.mockRejectedValue(new Error('Sin conexión'))
    render(<MemoryRouter><Heart review={{ id: 9, total_likes: 3, me_gusta: false }} user={{ username: 'ana' }} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Me gusta' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión')
    expect(screen.getByRole('button', { name: 'Me gusta' })).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('Pagination', () => {
  it('muestra primera, vecinas y última página con puntos suspensivos', () => {
    const change = vi.fn()
    render(<Pagination page={5} count={20 * 12} change={change} />)
    for (const n of [1, 4, 5, 6, 12]) expect(screen.getByRole('button', { name: `Página ${n}` })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Página 2' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Página 5' })).toHaveAttribute('aria-current', 'page')
    fireEvent.click(screen.getByRole('button', { name: /Siguiente/ }))
    expect(change).toHaveBeenCalledWith(6)
  })
})
