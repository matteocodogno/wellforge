/// <reference types="vite/client" />

// INTERFACE, not `type`: both names are declaration merges. `vite/client` declares
// `interface ImportMetaEnv` and TypeScript's lib.es5 declares `interface ImportMeta`; a
// type alias cannot merge with either, and `type ImportMeta` fails with TS2300 Duplicate
// identifier against the standard lib. This is the documented exception to the
// prefer-type-aliases rule (react-ts-vite skill) — and the comment alone was not enough:
// eslint still failed the build on consistent-type-definitions, so the exception has to be
// stated in a form eslint reads.

/* eslint-disable @typescript-eslint/consistent-type-definitions -- declaration merging
   requires `interface`; see the note above. */

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  // Add every VITE_ var used in the codebase here, AND to the [env] block in the root
  // mise.toml — that is where the values come from. There is no committed dotenv file:
  // Vite reads VITE_-prefixed vars from the process environment, mise puts them there, and
  // the plugin's guards refuse to touch a file named `.env` (so the agent could not have
  // kept one in step with this interface anyway). Local overrides: .mise.local.toml.
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
