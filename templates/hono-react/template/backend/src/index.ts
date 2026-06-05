import { serve } from '@hono/node-server'
import { createApp } from './app'
import { env } from './config/env'
import { logger } from './config/logger'

const app = createApp()

serve({ fetch: app.fetch, port: env.PORT }, info => {
  logger.info(`Server running at http://localhost:${info.port}`)
})
