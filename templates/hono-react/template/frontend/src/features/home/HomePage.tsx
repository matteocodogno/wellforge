import { config } from '@/config'

export const HomePage = () => {
  return (
    <main>
      <h1>{config.appName}</h1>
      <p>
        Frontend is running. The API is expected at <code>{config.apiBaseUrl}</code>.
      </p>
    </main>
  )
}
