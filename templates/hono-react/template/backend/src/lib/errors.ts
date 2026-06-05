import { Data } from 'effect'

/**
 * Tagged domain errors. Use `Effect.fail(new NotFoundError({ ... }))` in services /
 * repositories and discriminate with `Effect.catchTag('NotFoundError', ...)` at the
 * route edge.
 */

export class NotFoundError extends Data.TaggedError('NotFoundError')<{
  resource: string
  id: string
}> {
  get message() {
    return `${this.resource} not found: ${this.id}`
  }
}

export class ValidationError extends Data.TaggedError('ValidationError')<{
  message: string
  field?: string
}> {}

export class DuplicateError extends Data.TaggedError('DuplicateError')<{
  message: string
}> {}

export class DatabaseError extends Data.TaggedError('DatabaseError')<{
  message: string
  cause?: unknown
}> {}
