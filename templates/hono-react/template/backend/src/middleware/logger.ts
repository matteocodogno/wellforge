import type { MiddlewareHandler } from 'hono'
import { logger } from '@/config/logger'

/**
 * Request logger — logs method, url, status and duration for every request.
 */
export const requestLogger: MiddlewareHandler = async (c, next) => {
  const start = Date.now()
  const { method, url } = c.req

  await next()

  logger.info({
    method,
    url,
    status: c.res.status,
    duration: `${Date.now() - start}ms`,
  })
}
