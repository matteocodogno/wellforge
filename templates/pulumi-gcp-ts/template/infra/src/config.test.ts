import { describe, expect, it } from 'vitest'
import { DEFAULT_REGION, buildLabels, resolveRegion } from './config'

describe('resolveRegion', () => {
  it('returns the configured region when provided', () => {
    expect(resolveRegion('us-central1')).toBe('us-central1')
  })

  it('falls back to the default when undefined', () => {
    expect(resolveRegion(undefined)).toBe(DEFAULT_REGION)
  })

  it('falls back to the default when blank', () => {
    expect(resolveRegion('   ')).toBe(DEFAULT_REGION)
  })
})

describe('buildLabels', () => {
  it('always includes managed-by and environment', () => {
    expect(buildLabels('dev')).toEqual({ 'managed-by': 'pulumi', environment: 'dev' })
  })

  it('merges extra labels', () => {
    expect(buildLabels('prod', { team: 'platform' })).toEqual({
      'managed-by': 'pulumi',
      environment: 'prod',
      team: 'platform',
    })
  })

  it('lets extra labels override the defaults', () => {
    expect(buildLabels('dev', { environment: 'override' }).environment).toBe('override')
  })
})
