import { useState } from 'react';
import { FileCheck2, ShieldAlert } from 'lucide-react';
import {
  CONTRACT_STRUCTURE,
  errorCode,
  inspectSyntheticFixtureStructure,
  type FixtureMeta,
  type FixtureStructuralEvidence,
} from '../lib/ipc';

const EXPECTED_SHAPES: Record<string, { kind: string; references: number; entries: number }> = {
  'fixture-patient-alpha': { kind: 'Patient', references: 0, entries: 0 },
  'fixture-allergy-beta': { kind: 'AllergyIntolerance', references: 1, entries: 0 },
  'fixture-observation-gamma': { kind: 'Observation', references: 1, entries: 0 },
  'fixture-bundle-delta': { kind: 'Bundle', references: 0, entries: 2 },
};

type StructureState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; evidence: FixtureStructuralEvidence }
  | { kind: 'error'; code: string };

/**
 * Render only bounded, versioned evidence from native Rust.
 * This is not a full FHIR R4 validator, not model inference, and never clinical.
 */
export function FixtureStructuralSubset({ fixture }: { fixture: FixtureMeta }) {
  const [state, setState] = useState<StructureState>({ kind: 'idle' });

  async function inspect() {
    setState({ kind: 'loading' });
    try {
      const result = await inspectSyntheticFixtureStructure({ fixture_id: fixture.id });
      const expected = EXPECTED_SHAPES[fixture.id];
      if (
        !expected ||
        result.contract !== CONTRACT_STRUCTURE ||
        result.fixture_id !== fixture.id ||
        result.resource_id !== fixture.id ||
        result.resource_type !== expected.kind ||
        result.sha256_hex !== fixture.sha256_hex ||
        result.byte_len !== fixture.byte_len ||
        result.reference_count !== expected.references ||
        result.bundle_entry_count !== expected.entries ||
        !Number.isSafeInteger(result.reference_count) ||
        !Number.isSafeInteger(result.bundle_entry_count) ||
        result.duplicate_keys_rejected !== true ||
        result.structural_subset_checked !== true ||
        result.fhir_semantics_validated !== false ||
        result.synthetic_only !== true ||
        result.release_authorized !== false
      ) {
        setState({ kind: 'error', code: 'structure_contract_mismatch' });
        return;
      }
      setState({ kind: 'ready', evidence: result });
    } catch (err) {
      setState({ kind: 'error', code: errorCode(err) });
    }
  }

  return (
    <section aria-label="Fictional structural subset" className="fixture-structure-section">
      <div className="search-row">
        <h2>Inspect fictional JSON structure</h2>
        <button
          type="button"
          className="btn"
          onClick={inspect}
          disabled={state.kind === 'loading'}
          aria-label="Check fictional JSON structural subset"
        >
          {state.kind === 'loading' ? 'Checking structure...' : 'Check structural subset'}
        </button>
      </div>
      <p className="sub">
        Strict duplicate-key detection and allowlisted references, checked by native Rust on bundled
        fictional bytes only. <b>Not a complete FHIR validator</b> and not a clinical safety check.
      </p>

      {state.kind === 'ready' && (
        <div className="panel" role="status" aria-label="Fictional structural subset result">
          <div className="structure-summary">
            <FileCheck2 size={18} aria-hidden="true" className="brand-icon" />
            <strong>FICTIONAL STRUCTURAL SUBSET CHECKED</strong>
          </div>
          <dl className="structure-facts">
            <div><dt>Resource</dt><dd>{state.evidence.resource_type}</dd></div>
            <div><dt>ID</dt><dd className="mono">{state.evidence.resource_id}</dd></div>
            <div><dt>References matched</dt><dd>{state.evidence.reference_count}</dd></div>
            <div><dt>Bundle entries checked</dt><dd>{state.evidence.bundle_entry_count}</dd></div>
            <div><dt>Duplicate JSON keys</dt><dd>Rejected at any depth</dd></div>
            <div><dt>FHIR semantics validated</dt><dd>No</dd></div>
          </dl>
          <p className="sub">
            Byte identity remains pinned to <code>{state.evidence.sha256_hex}</code>.
          </p>
        </div>
      )}

      {state.kind === 'error' && (
        <div className="error-box" role="alert" aria-label="Structural subset refused">
          <ShieldAlert size={17} aria-hidden="true" />
          <strong>Structural subset refused</strong>
          <p>Malformed, inconsistent or unavailable evidence (code: <span className="mono">{state.code}</span>). No valid-structure claim is shown.</p>
        </div>
      )}
    </section>
  );
}
