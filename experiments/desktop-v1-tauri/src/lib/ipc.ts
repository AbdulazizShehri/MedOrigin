import patientFixtureRaw from '../../src-tauri/fixtures/fixture-patient-alpha.json?raw';
import allergyFixtureRaw from '../../src-tauri/fixtures/fixture-allergy-beta.json?raw';
import observationFixtureRaw from '../../src-tauri/fixtures/fixture-observation-gamma.json?raw';
import bundleFixtureRaw from '../../src-tauri/fixtures/fixture-bundle-delta.json?raw';

// Typed wrappers over the Tauri 2 IPC bridge. Outside a Tauri webview
// (browser dev, Playwright, jsdom) a deterministic synthetic mock is served
// instead — never the real bridge, never the network. The mock mirrors the
// exact contract shapes and the golden hashes of the committed fixtures.
// Browser tests are NOT native validation; the Windows UIA gate is separate.

export const MO_IPC_STALL_MS = 3000;

export interface DesktopStatus {
  contract: string;
  mode: string;
  app_network_plugins_enabled: boolean;
  webview_egress_qualified: boolean;
  release_authorized: boolean;
  production_parity_qualified: boolean;
  app_version: string;
  token_contract: string;
}

export interface FixtureMeta {
  id: string;
  label: string;
  media_type: string;
  byte_len: number;
  sha256_hex: string;
}

export interface FixturesList {
  contract: string;
  fixtures: FixtureMeta[];
}

export interface VerifyFixtureRequest {
  fixture_id: string;
}

export interface FixtureVerification {
  contract: string;
  fixture_id: string;
  byte_len: number;
  sha256_hex: string;
  synthetic_only: boolean;
  release_authorized: boolean;
}

export interface FixtureSource {
  contract: string;
  fixture_id: string;
  media_type: string;
  byte_len: number;
  sha256_hex: string;
  text: string;
  synthetic_only: boolean;
  release_authorized: boolean;
}

export interface CommandError {
  code: string;
}

export const CONTRACT_STATUS = 'medorigin-desktop-status-v1';
export const CONTRACT_LIST = 'medorigin-fixtures-list-v1';
export const CONTRACT_VERIFY = 'medorigin-fixture-verify-v1';
export const CONTRACT_SOURCE = 'medorigin-fixture-source-v1';

// Golden values mirror src-tauri fixtures and are cross-checked by
// tests/verify_goldens.py. Browser mock only — the native Rust host is the
// source of truth in the real app.
export const MOCK_FIXTURES: FixtureMeta[] = [
  { id: 'fixture-patient-alpha', label: 'FICTIONAL patient (example person)', media_type: 'application/fhir+json', byte_len: 425, sha256_hex: '1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f' },
  { id: 'fixture-allergy-beta', label: 'FICTIONAL allergy intolerance (example substance)', media_type: 'application/fhir+json', byte_len: 431, sha256_hex: 'e5719012514e6a858f238da9fcdd46cc61c04828af60c00c31a3887c8f8dddca' },
  { id: 'fixture-observation-gamma', label: 'FICTIONAL observation (example finding)', media_type: 'application/fhir+json', byte_len: 474, sha256_hex: 'b086dee0c87c59ea853a927eba928f9c06703ca14b4dda75e75f46a91511cfb5' },
  { id: 'fixture-bundle-delta', label: 'FICTIONAL bundle, hash-verified only', media_type: 'application/fhir+json', byte_len: 533, sha256_hex: '7971da4c949507fcfb6d3679f7a63ad2840c93206ea4749545b274f6ee49f399' },
];

// Browser preview source bytes are bundled only from the four committed,
 // fictional, LF-pinned fixtures. Never fetch from a URL or user path.
const MOCK_SOURCE_TEXTS: Record<string, string> = {
  'fixture-patient-alpha': patientFixtureRaw,
  'fixture-allergy-beta': allergyFixtureRaw,
  'fixture-observation-gamma': observationFixtureRaw,
  'fixture-bundle-delta': bundleFixtureRaw,
};

export const MOCK_STATUS: DesktopStatus = {
  contract: CONTRACT_STATUS,
  mode: 'SYNTHETIC_DEVELOPER_PREVIEW',
  app_network_plugins_enabled: false,
  webview_egress_qualified: false,
  release_authorized: false,
  production_parity_qualified: false,
  app_version: '0.0.0',
  token_contract: '0.1.0-design-review',
};

function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

async function invokeRaw<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke<T>(command, args);
}

class StallError extends Error {
  constructor() {
    super('stalled');
    this.name = 'StallError';
  }
}

export async function withStallGuard<T>(promise: Promise<T>): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new StallError()), MO_IPC_STALL_MS);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function getDesktopStatus(): Promise<DesktopStatus> {
  if (!isTauri()) return { ...MOCK_STATUS };
  return withStallGuard(invokeRaw<DesktopStatus>('get_desktop_status'));
}

export async function listSyntheticFixtures(): Promise<FixturesList> {
  if (!isTauri()) {
    return { contract: CONTRACT_LIST, fixtures: MOCK_FIXTURES.map((f) => ({ ...f })) };
  }
  return withStallGuard(invokeRaw<FixturesList>('list_synthetic_fixtures'));
}

export async function verifySyntheticFixture(req: VerifyFixtureRequest): Promise<FixtureVerification> {
  if (!isTauri()) {
    const match = MOCK_FIXTURES.find((f) => f.id === req.fixture_id);
    if (!match) {
      const err: CommandError = { code: 'unknown_fixture' };
      throw err;
    }
    return {
      contract: CONTRACT_VERIFY,
      fixture_id: match.id,
      byte_len: match.byte_len,
      sha256_hex: match.sha256_hex,
      synthetic_only: true,
      release_authorized: false,
    };
  }
  return withStallGuard(invokeRaw<FixtureVerification>('verify_synthetic_fixture', { req }));
}

export async function readSyntheticFixtureSource(req: VerifyFixtureRequest): Promise<FixtureSource> {
  if (!isTauri()) {
    const match = MOCK_FIXTURES.find((f) => f.id === req.fixture_id);
    const text = MOCK_SOURCE_TEXTS[req.fixture_id];
    if (!match || text === undefined) {
      const err: CommandError = { code: 'unknown_fixture' };
      throw err;
    }
    return {
      contract: CONTRACT_SOURCE,
      fixture_id: match.id,
      media_type: match.media_type,
      byte_len: match.byte_len,
      sha256_hex: match.sha256_hex,
      text,
      synthetic_only: true,
      release_authorized: false,
    };
  }
  return withStallGuard(invokeRaw<FixtureSource>('read_synthetic_fixture_source', { req }));
}

export function isCommandError(err: unknown): err is CommandError {
  return typeof err === 'object' && err !== null && typeof (err as CommandError).code === 'string';
}

export function errorCode(err: unknown): string {
  if (err instanceof StallError || (err instanceof Error && err.message === 'stalled')) return 'stalled';
  if (isCommandError(err)) return err.code;
  return 'internal';
}
