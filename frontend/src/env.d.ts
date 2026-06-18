/// <reference path="../.astro/types.d.ts" />

interface ImportMetaEnv {
  /** Base URL of the FastAPI backend (e.g. http://127.0.0.1:8001). */
  readonly PUBLIC_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
