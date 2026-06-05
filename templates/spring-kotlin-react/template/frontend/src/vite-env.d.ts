/// <reference types="vite/client" />

type ImportMetaEnv = {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  // add every VITE_ var used in the codebase here
}

type ImportMeta = {
  readonly env: ImportMetaEnv
}
