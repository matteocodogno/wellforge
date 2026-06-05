import type { ErrorHandler } from 'hono'
import { ZodError } from 'zod'
import { logger } from '@/config/logger'

/**
 * Global error handler. Wire with `app.onError(errorHandler)`.
 *
 * Error shape:
 *   - Zod validation: 400 { error: 'Validation failed', issues }
 *   - everything else: 500 { error: 'Internal server error', message? }
 *     (message included only in development)
 */
export const errorHandler: ErrorHandler = (err, c) => {
  logger.error({
    error: err.message,
    stack: err.stack,
    path: c.req.path,
    method: c.req.method,
  })

  if (err instanceof ZodError) {
    return c.json({ error: 'Validation failed', issues: err.issues }, 400)
  }

  return c.json(
    {
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? err.message : undefined,
    },
    500
  )
}
