/** Boundary checks for the synthetic-only Rust command bridge. No user input or I/O. */
export type NativePreviewStatus = {
  mode: string;
  data_access: string;
  release_authorized: boolean;
  production_parity_qualified: boolean;
  app_network_plugins_enabled: boolean;
  webview_runtime_egress_qualified: boolean;
};

export type NativeHashResult = {
  contract: string;
  fixture_id: "patient-minimal" | "patient-invalid-utf8" | "patient-over-limit" | "patient-exact-limit";
  bytes: number;
  sha256_hex: string;
  synthetic_only: boolean;
  release_authorized: boolean;
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Never enable the verify button if the native safety posture is unexpected. */
export function assertPreviewStatus(value: unknown): NativePreviewStatus {
  if (!record(value) ||
      value.mode !== "SYNTHETIC_DEVELOPER_PREVIEW" ||
      value.data_access !== "four_allowlisted_in_memory_fixtures_only" ||
      value.release_authorized !== false ||
      value.production_parity_qualified !== false ||
      value.app_network_plugins_enabled !== false ||
      value.webview_runtime_egress_qualified !== false) {
    throw new Error("Native preview contract is unsafe or unavailable. Verification blocked.");
  }
  return value as NativePreviewStatus;
}

/** Verify all native response fields against source-bound fixture expectations. */
export function assertHashResult(
  value: unknown,
  expected: { id: string; bytes: number; sha: string },
): NativeHashResult {
  if (!record(value) ||
      value.contract !== "medorigin-desktop-d0-raw-sha256-v1" ||
      value.fixture_id !== expected.id ||
      value.bytes !== expected.bytes ||
      !Number.isSafeInteger(value.bytes) ||
      typeof value.sha256_hex !== "string" ||
      !/^[0-9a-f]{64}$/.test(value.sha256_hex) ||
      value.sha256_hex !== expected.sha ||
      value.synthetic_only !== true ||
      value.release_authorized !== false) {
    throw new Error("Native integrity result does not match the synthetic reference. Verification blocked.");
  }
  return value as NativeHashResult;
}
