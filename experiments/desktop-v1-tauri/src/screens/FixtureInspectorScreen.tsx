import { useEffect, useRef, useState } from 'react';
import { VerifiedFixtureSource } from '../components/VerifiedFixtureSource';
import { FixtureStructuralSubset } from '../components/FixtureStructuralSubset';
import { CircleCheck, CircleX, FileSearch, ShieldAlert } from 'lucide-react';
import {
  CONTRACT_LIST,
  CONTRACT_VERIFY,
  errorCode,
  listSyntheticFixtures,
  verifySyntheticFixture,
  type FixtureMeta,
  type FixtureVerification,
} from '../lib/ipc';

type ListState =
  | { kind: 'loading' }
  | { kind: 'ready'; fixtures: FixtureMeta[] }
  | { kind: 'error'; code: string };

type VerifyState =
  | { kind: 'idle' }
  | { kind: 'verifying' }
  | { kind: 'ready'; result: FixtureVerification; expectedSha256: string }
  | { kind: 'error'; code: string };

export function FixtureInspectorScreen() {
  const [list, setList] = useState<ListState>({ kind: 'loading' });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [verify, setVerify] = useState<VerifyState>({ kind: 'idle' });
  const verificationGeneration = useRef(0);
  // DEV-only affordance (visible, never styled as active): probe an unknown id to prove the host fails closed.
  const [probeId, setProbeId] = useState('');

  useEffect(() => {
    let cancelled = false;
    listSyntheticFixtures()
      .then((res) => {
        if (cancelled) return;
        if (res.contract !== CONTRACT_LIST || !Array.isArray(res.fixtures)) {
          setList({ kind: 'error', code: 'contract_mismatch' });
          return;
        }
        setList({ kind: 'ready', fixtures: res.fixtures });
      })
      .catch((err) => {
        if (!cancelled) setList({ kind: 'error', code: errorCode(err) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const [probeState, setProbeState] = useState<VerifyState>({ kind: 'idle' });

  function selectFixture(f: FixtureMeta) {
    verificationGeneration.current += 1;
    setSelectedId(f.id);
    setVerify({ kind: 'idle' });
  }

  async function runVerify(id: string, expectedSha256: string) {
    const requestId = ++verificationGeneration.current;
    setVerify({ kind: 'verifying' });
    try {
      const result = await verifySyntheticFixture({ fixture_id: id });
      if (requestId !== verificationGeneration.current) return;
      if (result.contract !== CONTRACT_VERIFY || result.fixture_id !== id) {
        setVerify({ kind: 'error', code: 'contract_mismatch' });
        return;
      }
      const listed = list.kind === 'ready' ? list.fixtures.find((item) => item.id === id) : undefined;
      if (!listed || result.byte_len !== listed.byte_len || result.synthetic_only !== true || result.release_authorized !== false) {
        setVerify({ kind: 'error', code: 'verification_contract_mismatch' });
        return;
      }
      if (result.sha256_hex !== expectedSha256) {
        setVerify({ kind: 'error', code: 'hash_mismatch' });
        return;
      }
      setVerify({ kind: 'ready', result, expectedSha256 });
    } catch (err) {
      if (requestId === verificationGeneration.current) {
        setVerify({ kind: 'error', code: errorCode(err) });
      }
    }
  }

  async function runProbe() {
    const id = probeId.trim();
    if (!id) return;
    setProbeState({ kind: 'verifying' });
    try {
      await verifySyntheticFixture({ fixture_id: id });
      setProbeState({ kind: 'error', code: 'unexpectedly_accepted' });
    } catch (err) {
      setProbeState({ kind: 'error', code: errorCode(err) });
    }
  }

  const selected = list.kind === 'ready' ? list.fixtures.find((f) => f.id === selectedId) : undefined;

  return (
    <>
      <span className="eyebrow">MEDORIGIN / SYNTHETIC FHIR FIXTURE INSPECTOR / SLICES 1-3</span>
      <h1 className="page-title">FHIR fixture inspector</h1>
      <p className="sub">
        FICTIONAL fixtures, hash-verified by the native Rust host over committed bytes. This is <b>not</b> FHIR validation,
        not a patient record, and not a clinical surface. Every payload says FICTIONAL; nothing here is real.
      </p>

      <div className="honesty-banner" role="note" aria-label="Fixture scope notice">
        <ShieldAlert size={18} aria-hidden="true" className="brand-icon" />
        <span>
          <b>FICTIONAL — NOT CLINICAL DATA</b>
          <br />
          Hash verification proves byte identity only. It does not validate FHIR semantics, references, or clinical content.
        </span>
      </div>

      <section aria-label="Synthetic fixtures">
        <div className="search-row">
          <h2>Fixtures ({list.kind === 'ready' ? list.fixtures.length : '—'}, allowlisted in the native host)</h2>
        </div>

        {list.kind === 'loading' && <div className="loading-skeleton" aria-label="Loading fixtures" />}
        {list.kind === 'error' && (
          <div className="error-box" role="alert" aria-label="Fixture list failed">
            <strong>Fixture list unavailable</strong>
            <p>The native host did not answer with a valid fixtures contract (error code: <span className="mono">{list.code}</span>). Failing closed; nothing is shown as verified.</p>
          </div>
        )}

        {list.kind === 'ready' && (
          <ul className="inline-list" aria-label="Synthetic fixtures">
            {list.fixtures.map((f) => (
              <li key={f.id}>
                <button
                  type="button"
                  className="fixture-item"
                  aria-pressed={selectedId === f.id}
                  aria-label={`Fixture ${f.id}`}
                  onClick={() => selectFixture(f)}
                >
                  <FileSearch size={18} aria-hidden="true" />
                  <span>
                    <b>{f.id}</b>
                    <small>{f.label}</small>
                    <small className="mono">{f.byte_len} bytes · {f.media_type}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Verification" className="verify-section">
        {selected && (
          <>
            <div className="search-row">
              <h2>Verify with native Rust</h2>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => runVerify(selected.id, selected.sha256_hex)}
                disabled={verify.kind === 'verifying'}
                aria-label="Verify fixture with native Rust"
              >
                {verify.kind === 'verifying' ? 'Verifying…' : 'Verify with native Rust'}
              </button>
            </div>

            <div className="panel">
              <div className="detail">
                <strong>Listed SHA-256 (allowlist metadata)</strong>
                <code className="hash">{selected.sha256_hex}</code>
              </div>

              {verify.kind === 'ready' && verify.result.fixture_id === selected.id && (
                <div className="detail" role="status" aria-label="Verification result" aria-live="polite">
                  <strong>
                    <CircleCheck size={14} aria-hidden="true" /> Native verification — byte-identical
                  </strong>
                  <code className="hash">{verify.result.sha256_hex}</code>
                  <p>
                    contract <span className="mono">{verify.result.contract}</span> · {verify.result.byte_len} bytes · synthetic_only{' '}
                    <b>{String(verify.result.synthetic_only)}</b> · release_authorized <b>{String(verify.result.release_authorized)}</b>
                  </p>
                  {selected.id === 'fixture-bundle-delta' && (
                    <p className="sub-spaced">Hash-verified only — no FHIR structural or clinical validation.</p>
                  )}
                </div>
              )}

              {verify.kind === 'error' && (
                <div className="error-box" role="alert" aria-label="Verification failed">
                  <strong>Verification failed</strong>
                  <p>
                    The native host rejected the request or returned an untrusted payload (code: <span className="mono">{verify.code}</span>).
                    Failing closed: this fixture is <b>not</b> marked verified.
                  </p>
                </div>
              )}
            </div>
            {verify.kind === 'ready' && verify.result.fixture_id === selected.id && (
              <>
                <VerifiedFixtureSource key={selected.id} fixture={selected} />
                <FixtureStructuralSubset key={`${selected.id}-structure`} fixture={selected} />
              </>
            )}
          </>
        )}

        {!selected && list.kind === 'ready' && (
          <p className="sub">Select a fixture to verify it with the native host.</p>
        )}

        {(import.meta.env.DEV || import.meta.env.VITE_DEV_PROBE === 'true') && (
          <div className="panel dev-probe" aria-label="Developer probe">
            <strong className="dev-probe-label">DEV — probe unknown fixture id</strong>
            <p>Debug builds only. Proves the native host fails closed on non-allowlisted input. Never shipped as an active control.</p>
            <div className="dev-probe-row">
              <input
                type="text"
                className="search-box"
                value={probeId}
                onChange={(e) => setProbeId(e.target.value)}
                placeholder="e.g. ../secret or patient-minimal"
                aria-label="Unknown fixture id to probe"
              />
              <button type="button" className="btn" onClick={runProbe} aria-label="Probe unknown fixture id">
                <CircleX size={15} aria-hidden="true" /> Probe
              </button>
            </div>
            {probeState.kind === 'error' && (
              <p className="status-line" role="status">
                Result: <span className="mono">{probeState.code}</span>
                {probeState.code === 'unexpectedly_accepted'
                  ? ' — the host ACCEPTED an out-of-band id. Treat the allowlist as broken and fail closed.'
                  : ' (expected fail-closed rejection)'}
              </p>
            )}
          </div>
        )}
      </section>
    </>
  );
}
