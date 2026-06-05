// Central, typed access to env vars. Never read import.meta.env elsewhere.
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  appName: import.meta.env.VITE_APP_NAME,
} as const
