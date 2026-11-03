import { useState } from 'react';
import {
  CONTRACT_SOURCE,
  errorCode,
  readSyntheticFixtureSource,
  type FixtureMeta,
  type FixtureSource,
} from '../lib/ipc';

type ViewState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; source: FixtureSource }
  | { kind: 'error'; code: string };

function sha256Hex(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  if (!globalThis.crypto?.subtle) return Promise.reject(new Error('crypto_unavailable'));
  return crypto.subtle.digest('SHA-256', bytes).then((buffer) =>
    Array.from(new Uint8Array(buffer), (b) => b.toString(16).padStart(2, '0')).join(''),
  );
}

/**
 * Read-only source viewer, never an arbitrary-file reader or FHIR validator.
 * Browser checks protect against accidental/forged IPC response drift, but
 * Rust owns the actual allowlist and byte-identity boundary.
 */
export function VerifiedFixtureSource({ fixture }: { fixture: FixtureMeta }) {
  const [view, setView] = useState<ViewState>({ kind: 'idle' });

  async function inspect() {
    setView({ kind: 'loading' });
    try {
      const result = await readSyntheticFixtureSource({ fixture_id: fixture.id });
      if (
        result.contract !== CONTRACT_SOURCE ||
        result.fixture_id !== fixture.id ||
        result.media_type !== fixture.media_type ||
        result.byte_len !== fixture.byte_len ||
        result.sha256_hex !== fixture.sha256_hex ||
        result.synthetic_only !== true ||
        result.release_authorized !== false ||
        typeof result.text !== 'string'
      ) {
        setView({ kind: 'error', code: 'source_contract_mismatch' });
        return;
      }
      // Byte count and hash are calculated over the *actual* returned text.
      // Comparing two unverified metadata envelopes alone is insufficient.
      const bytes = new TextEncoder().encode(result.text);
      if (bytes.byteLength !== fixture.byte_len || bytes.byteLength > 65_536) {
        setView({ kind: 'error', code: 'source_length_mismatch' });
        return;
      }
      const digest = await sha256Hex(bytes);
      if (digest !== fixture.sha256_hex) {
        setView({ kind: 'error', code: 'source_hash_mismatch' });
        return;
      }
      const parsed: unknown = JSON.parse(result.text);
      if (
        typeof parsed !== 'object' ||
        parsed === null ||
        Array.isArray(parsed) ||
        !('resourceType' in parsed) ||
        typeof parsed.resourceType !== 'string' ||
        !result.text.includes('FICTIONAL')
      ) {
        setView({ kind: 'error', code: 'source_invalid_json' });
        return;
      }
      setView({ kind: 'ready', source: result });
    } catch (err) {
      const code = err instanceof Error && err.message === 'crypto_unavailable'
        ? 'crypto_unavailable'
        : err instanceof SyntaxError ? 'source_invalid_json' : errorCode(err);
      setView({ kind: 'error', code });
    }
  }

  return (
    <section aria-label="Fictional source viewer" className="fixture-source-section">
      <div className="search-row">
        <h2>Inspect bundled fictional JSON</h2>
        <button
          type="button"
          className="btn"
          aria-label="Inspect verified fictional JSON source"
          onClick={inspect}
          disabled={view.kind === 'loading'}
        >
          {view.kind === 'loading' ? 'Checking source...' : 'Inspect source'}
        </button>
      </div>
      <p className="sub">
        Only committed, allowlisted fictional fixture bytes. SHA-256 is checked again before display.
        JSON syntax and byte identity do <b>not</b> establish FHIR validity or clinical correctness.
      </p>
      {view.kind === 'ready' && (
        <div className="panel" role="region" aria-label="Verified fictional JSON text">
          <p className="source-provenance">
            <b>FICTIONAL SOURCE</b> | {view.source.byte_len} bytes | SHA-256 matched native allowlist
          </p>
          <pre className="fixture-source-pre"><code>{view.source.text}</code></pre>
        </div>
      )}
      {view.kind === 'error' && (
        <div className="error-box" role="alert" aria-label="Source inspection failed">
          <strong>Source inspection refused</strong>
          <p>Inconsistent, malformed, or unavailable trusted source (code: <span className="mono">{view.code}</span>). No content displayed.</p>
        </div>
      )}
    </section>
  );
}
