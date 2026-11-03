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

export interface FixtureStructuralEvidence {
  contract: string;
  fixture_id: string;
  resource_type: string;
  resource_id: string;
  byte_len: number;
  sha256_hex: string;
  reference_count: number;
  bundle_entry_count: number;
  duplicate_keys_rejected: boolean;
  structural_subset_checked: boolean;
  fhir_semantics_validated: boolean;
  synthetic_only: boolean;
  release_authorized: boolean;
}

export interface FictionalLineageNode {
  fixture_id: string;
  resource_type: string;
  sha256_hex: string;
  byte_len: number;
}

export interface FictionalLineageEdge {
  source_id: string;
  target_id: string;
  relationship: string;
  source_pointer: string;
}

export interface FictionalLineage {
  contract: string;
  focus_id: string;
  nodes: FictionalLineageNode[];
  edges: FictionalLineageEdge[];
  scope: string;
  synthetic_only: boolean;
  fhir_semantics_validated: boolean;
  release_authorized: boolean;
}

export interface FictionalTimelineEvent {
  event_id: string;
  event_kind: string;
  source_fixture_id: string;
  source_resource_type: string;
  source_sha256_hex: string;
  source_byte_len: number;
  date: string | null;
  date_json_pointer: string | null;
  date_status: string;
  label: string;
}

export interface FictionalPatientTimeline {
  contract: string;
  patient_fixture_id: string;
  scope: string;
  order: string;
  events: FictionalTimelineEvent[];
  synthetic_only: boolean;
  fhir_semantics_validated: boolean;
  release_authorized: boolean;
}

export interface CommandError {
  code: string;
}

export const CONTRACT_STATUS = 'medorigin-desktop-status-v1';
export const CONTRACT_LIST = 'medorigin-fixtures-list-v1';
export const CONTRACT_VERIFY = 'medorigin-fixture-verify-v1';
export const CONTRACT_SOURCE = 'medorigin-fixture-source-v1';
export const CONTRACT_STRUCTURE = 'medorigin-fictional-structure-subset-v1';
export const CONTRACT_LINEAGE = 'medorigin-four-fictional-fixtures-lineage-v1';
export const LINEAGE_SCOPE = 'FOUR_PINNED_SYNTHETIC_FIXTURES';
export const CONTRACT_TIMELINE = 'medorigin-three-fictional-timeline-entries-v1';

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

// Browser-only mock: mirrors the exact fictional, pinned Rust fixture outcome.
 // It is NOT evidence that structural parsing ran in the browser. Native Rust
 // independently checks recursive duplicates, IDs, references and bundle URNs.
const MOCK_STRUCTURE: Record<string, {
  resource_type: string;
  reference_count: number;
  bundle_entry_count: number;
}> = {
  'fixture-patient-alpha': { resource_type: 'Patient', reference_count: 0, bundle_entry_count: 0 },
  'fixture-allergy-beta': { resource_type: 'AllergyIntolerance', reference_count: 1, bundle_entry_count: 0 },
  'fixture-observation-gamma': { resource_type: 'Observation', reference_count: 1, bundle_entry_count: 0 },
  'fixture-bundle-delta': { resource_type: 'Bundle', reference_count: 0, bundle_entry_count: 2 },
};

export async function inspectSyntheticFixtureStructure(
  req: VerifyFixtureRequest,
): Promise<FixtureStructuralEvidence> {
  if (!isTauri()) {
    const match = MOCK_FIXTURES.find((item) => item.id === req.fixture_id);
    const shape = MOCK_STRUCTURE[req.fixture_id];
    if (!match || !shape) {
      const err: CommandError = { code: 'unknown_fixture' };
      throw err;
    }
    return {
      contract: CONTRACT_STRUCTURE,
      fixture_id: match.id,
      resource_type: shape.resource_type,
      resource_id: match.id,
      byte_len: match.byte_len,
      sha256_hex: match.sha256_hex,
      reference_count: shape.reference_count,
      bundle_entry_count: shape.bundle_entry_count,
      duplicate_keys_rejected: true,
      structural_subset_checked: true,
      fhir_semantics_validated: false,
      synthetic_only: true,
      release_authorized: false,
    };
  }
  return withStallGuard(invokeRaw<FixtureStructuralEvidence>('inspect_synthetic_fixture_structure', { req }));
}

// Static browser-preview values only. Rust validates these same pointer paths
// against strictly parsed, hash-pinned fictional JSON, never user-supplied paths.
export const PINNED_FICTIONAL_LINKS: FictionalLineageEdge[] = [
  { source_id: 'fixture-allergy-beta', target_id: 'fixture-patient-alpha', relationship: 'fictional_reference', source_pointer: '/patient/reference' },
  { source_id: 'fixture-observation-gamma', target_id: 'fixture-patient-alpha', relationship: 'fictional_reference', source_pointer: '/subject/reference' },
  { source_id: 'fixture-bundle-delta', target_id: 'fixture-patient-alpha', relationship: 'fictional_bundle_member', source_pointer: '/entry/0/resource' },
  { source_id: 'fixture-bundle-delta', target_id: 'fixture-observation-gamma', relationship: 'fictional_bundle_member', source_pointer: '/entry/1/resource' },
];
const PINNED_FICTIONAL_KINDS: Record<string, string> = {
  'fixture-patient-alpha': 'Patient',
  'fixture-allergy-beta': 'AllergyIntolerance',
  'fixture-observation-gamma': 'Observation',
  'fixture-bundle-delta': 'Bundle',
};

export async function inspectFictionalFixtureLineage(req: VerifyFixtureRequest): Promise<FictionalLineage> {
  if (!isTauri()) {
    const focus = MOCK_FIXTURES.find((item) => item.id === req.fixture_id);
    if (!focus) {
      const err: CommandError = { code: 'unknown_fixture' };
      throw err;
    }
    const edges = PINNED_FICTIONAL_LINKS.filter((link) =>
      link.source_id === focus.id || link.target_id === focus.id,
    ).map((link) => ({ ...link }));
    const involved = new Set<string>([focus.id]);
    for (const link of edges) {
      involved.add(link.source_id);
      involved.add(link.target_id);
    }
    const nodes = MOCK_FIXTURES.filter((item) => involved.has(item.id)).map((item) => ({
      fixture_id: item.id,
      resource_type: PINNED_FICTIONAL_KINDS[item.id],
      sha256_hex: item.sha256_hex,
      byte_len: item.byte_len,
    }));
    return {
      contract: CONTRACT_LINEAGE,
      focus_id: focus.id,
      nodes,
      edges,
      scope: LINEAGE_SCOPE,
      synthetic_only: true,
      fhir_semantics_validated: false,
      release_authorized: false,
    };
  }
  return withStallGuard(invokeRaw<FictionalLineage>('inspect_fictional_fixture_lineage', { req }));
}

// Browser-only deterministic mock of the three pinned fictional dates/records.
 // Actual native evidence is separately checked by Tauri + Windows UIA.
export async function inspectFictionalPatientTimeline(req: VerifyFixtureRequest): Promise<FictionalPatientTimeline> {
  if (!isTauri()) {
    if (req.fixture_id !== 'fixture-patient-alpha') {
      const err: CommandError = { code: 'unknown_patient_fixture' };
      throw err;
    }
    const event = (
      sourceId: string, event_id: string, event_kind: string, label: string,
      resourceType: string, date: string | null, pointer: string | null, status: string,
    ): FictionalTimelineEvent => {
      const source = MOCK_FIXTURES.find((fixture) => fixture.id === sourceId);
      if (!source) throw new Error('synthetic_fixture_metadata_unavailable');
      return {
        event_id, event_kind, label, source_fixture_id: source.id,
        source_resource_type: resourceType, source_sha256_hex: source.sha256_hex,
        source_byte_len: source.byte_len, date, date_json_pointer: pointer, date_status: status,
      };
    };
    return {
      contract: CONTRACT_TIMELINE,
      patient_fixture_id: 'fixture-patient-alpha',
      scope: LINEAGE_SCOPE,
      order: 'dated_descending_then_undated',
      synthetic_only: true,
      fhir_semantics_validated: false,
      release_authorized: false,
      events: [
        event('fixture-allergy-beta', 'fictional-allergy-recorded', 'fictional_recorded_date',
          'Fictional allergy record date', 'AllergyIntolerance', '2026-01-01', '/recordedDate', 'source_date_only'),
        event('fixture-patient-alpha', 'fictional-patient-dob', 'fictional_demographic_date',
          'Fictional example birth date', 'Patient', '1970-01-01', '/birthDate', 'source_date_only'),
        event('fixture-observation-gamma', 'fictional-observation-undated', 'fictional_undated_observation',
          'Fictional observation (no recorded event date)', 'Observation', null, null, 'not_present_in_source'),
      ],
    };
  }
  return withStallGuard(invokeRaw<FictionalPatientTimeline>('inspect_fictional_patient_timeline', { req }));
}

export function isCommandError(err: unknown): err is CommandError {
  return typeof err === 'object' && err !== null && typeof (err as CommandError).code === 'string';
}

export function errorCode(err: unknown): string {
  if (err instanceof StallError || (err instanceof Error && err.message === 'stalled')) return 'stalled';
  if (isCommandError(err)) return err.code;
  return 'internal';
}
