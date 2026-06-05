import { OpenAPIHono } from '@hono/zod-openapi'
import { healthRouter } from './health'

/**
 * Route registry. Mount one OpenAPIHono router per resource here.
 */
export const createRouter = () => {
  const app = new OpenAPIHono()

  app.route('/health', healthRouter)

  return app
}
