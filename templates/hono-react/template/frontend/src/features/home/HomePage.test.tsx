import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HomePage } from './HomePage'

describe('HomePage', () => {
  it('renders the app name heading', () => {
    render(<HomePage />)
    expect(screen.getByRole('heading')).toBeTruthy()
  })
})
