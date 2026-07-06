import * as pulumi from '@pulumi/pulumi'
import { describe, expect, it } from 'vitest'

// Mocks intercept resource registration — no cloud calls. Must be set before importing
// any module that constructs resources (hence the dynamic import() in each test).
pulumi.runtime.setMocks({
  newResource: (args: pulumi.runtime.MockResourceArgs) => ({
    id: `${args.name}-id`,
    // Echo inputs back as state, and surface the logical name so `bucket.name` resolves.
    state: { ...args.inputs, name: args.name },
  }),
  call: () => ({}),
})

/** Resolve a Pulumi Output to a plain value in tests. */
function value<T>(output: pulumi.Output<T>): Promise<T> {
  return new Promise(resolve => output.apply(resolve))
}

describe('SecureBucket', () => {
  it('enforces secure defaults', async () => {
    const { SecureBucket } = await import('./gcs-bucket')
    const bucket = new SecureBucket('data', {
      location: 'EU',
      labels: { environment: 'dev' },
    })

    expect(await value(bucket.bucket.uniformBucketLevelAccess)).toBe(true)
    expect(await value(bucket.bucket.publicAccessPrevention)).toBe('enforced')
    expect(await value(bucket.bucket.versioning)).toEqual({ enabled: true })
    expect(await value(bucket.bucket.forceDestroy)).toBe(false)
    expect(await value(bucket.url)).toBe('gs://data')
  })

  it('honours explicit overrides', async () => {
    const { SecureBucket } = await import('./gcs-bucket')
    const bucket = new SecureBucket('scratch', {
      location: 'EU',
      versioning: false,
      forceDestroy: true,
    })

    expect(await value(bucket.bucket.versioning)).toEqual({ enabled: false })
    expect(await value(bucket.bucket.forceDestroy)).toBe(true)
  })
})
