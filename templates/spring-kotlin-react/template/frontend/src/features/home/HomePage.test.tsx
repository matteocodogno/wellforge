import { MantineProvider } from '@mantine/core'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HomePage } from './HomePage'

// The preset ships one real test on purpose. `vitest run` exits 1 on an empty suite, so a
// scaffold with no tests fails its own gate on day one — and the alternative,
// `passWithNoTests`, turns the test gate green for a project that has never tested
// anything, which is exactly what the coverage floor exists to prevent.
//
// Mantine components read theme context, so the provider is part of rendering one.
describe('HomePage', () => {
  it('renders the app name heading', () => {
    render(
      <MantineProvider>
        <HomePage />
      </MantineProvider>
    )
    expect(screen.getByRole('heading')).toBeTruthy()
  })
})
