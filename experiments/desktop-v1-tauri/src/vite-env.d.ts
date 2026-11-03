/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEV_PROBE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv & Record<string, string | boolean | undefined>;
}
