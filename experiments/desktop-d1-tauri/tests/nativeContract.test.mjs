import test from "node:test";
import assert from "node:assert/strict";
import { assertHashResult, assertPreviewStatus } from "../src/nativeContract.ts";

const safeStatus = {
  mode: "SYNTHETIC_DEVELOPER_PREVIEW",
  data_access: "four_allowlisted_in_memory_fixtures_only",
  release_authorized: false,
  production_parity_qualified: false,
  app_network_plugins_enabled: false,
  webview_runtime_egress_qualified: false,
};

const expected = {
  id: "patient-minimal",
  bytes: 57,
  sha: "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
};
const safeHash = {
  contract: "medorigin-desktop-d0-raw-sha256-v1",
  fixture_id: expected.id,
  bytes: expected.bytes,
  sha256_hex: expected.sha,
  synthetic_only: true,
  release_authorized: false,
};

test("exact known-safe native status is accepted", () => {
  assert.deepEqual(assertPreviewStatus(safeStatus), safeStatus);
});
test("unsafe native status is always rejected", () => {
  for (const key of Object.keys(safeStatus)) {
    const invalid = { ...safeStatus, [key]: key === "mode" || key === "data_access" ? "unexpected" : true };
    assert.throws(() => assertPreviewStatus(invalid), /Verification blocked/);
  }
  for (const invalid of [null, [], false, 0, "ok", {}]) {
    assert.throws(() => assertPreviewStatus(invalid), /Verification blocked/);
  }
});
test("exact source-bound synthetic hash result is accepted", () => {
  assert.deepEqual(assertHashResult(safeHash, expected), safeHash);
});
test("all altered response fields fail closed", () => {
  const variants = [
    { contract: "unknown" }, { fixture_id: "../patient" }, { bytes: 58 },
    { bytes: 57.5 }, { bytes: "57" }, { sha256_hex: "0".repeat(64) },
    { sha256_hex: expected.sha.toUpperCase() }, { sha256_hex: null },
    { synthetic_only: false }, { release_authorized: true },
  ];
  for (const variant of variants) {
    assert.throws(() => assertHashResult({ ...safeHash, ...variant }, expected), /Verification blocked/);
  }
  for (const invalid of [null, [], false, 0, "ok", {}]) {
    assert.throws(() => assertHashResult(invalid, expected), /Verification blocked/);
  }
});
test("all four source-bound fixed synthetic vectors are accepted", () => {
  const vectors = [
    ["patient-minimal", 57, "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0"],
    ["patient-invalid-utf8", 1, "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89"],
    ["patient-over-limit", 32769, "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538"],
    ["patient-exact-limit", 32768, "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e"],
  ];
  for (const [id, bytes, sha] of vectors) {
    const expectation = { id, bytes, sha };
    const response = { ...safeHash, fixture_id: id, bytes, sha256_hex: sha };
    assert.deepEqual(assertHashResult(response, expectation), response);
  }
});
test("unexpected selected fixture and corrupted local reference fail closed", () => {
  assert.throws(() => assertHashResult(safeHash, { ...expected, id: "patient-over-limit" }), /Verification blocked/);
  assert.throws(() => assertHashResult(safeHash, { ...expected, bytes: 32769 }), /Verification blocked/);
  assert.throws(() => assertHashResult(safeHash, { ...expected, sha: "f".repeat(64) }), /Verification blocked/);
});
