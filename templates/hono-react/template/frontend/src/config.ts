// Central, typed access to environment variables.
// Never read import.meta.env outside this module; never use process.env.
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  appName: import.meta.env.VITE_APP_NAME,
} as const
