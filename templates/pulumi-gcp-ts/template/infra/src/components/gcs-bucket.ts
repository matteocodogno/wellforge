import * as gcp from '@pulumi/gcp'
import * as pulumi from '@pulumi/pulumi'

export interface SecureBucketArgs {
  /** Bucket location — a region or multi-region (e.g. "EU", "europe-west6"). */
  location: pulumi.Input<string>
  /** Labels applied to the bucket (use `buildLabels` from src/config). */
  labels?: pulumi.Input<Record<string, string>>
  /** Object versioning — enabled by default. */
  versioning?: boolean
  /** Allow `pulumi destroy` to delete a non-empty bucket — disabled by default. */
  forceDestroy?: boolean
}

/**
 * A GCS bucket with WellForge secure defaults baked in: public access is prevented,
 * uniform bucket-level access is enforced, object versioning is on, and a 7-day soft-delete
 * window guards against accidental deletion. Prefer this over a bare `gcp.storage.Bucket`
 * so a caller can never forget a control the policy pack requires.
 */
export class SecureBucket extends pulumi.ComponentResource {
  readonly bucket: gcp.storage.Bucket
  readonly url: pulumi.Output<string>

  constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
    super('wellforge:gcp:SecureBucket', name, {}, opts)

    this.bucket = new gcp.storage.Bucket(
      name,
      {
        location: args.location,
        labels: args.labels,
        uniformBucketLevelAccess: true,
        publicAccessPrevention: 'enforced',
        forceDestroy: args.forceDestroy ?? false,
        versioning: { enabled: args.versioning ?? true },
        softDeletePolicy: { retentionDurationSeconds: 604800 },
      },
      { parent: this }
    )

    this.url = pulumi.interpolate`gs://${this.bucket.name}`

    this.registerOutputs({ bucket: this.bucket, url: this.url })
  }
}
