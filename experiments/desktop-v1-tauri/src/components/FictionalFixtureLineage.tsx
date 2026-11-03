import { useState } from 'react';
import { GitBranch, ShieldAlert } from 'lucide-react';
import {
  CONTRACT_LINEAGE,
  LINEAGE_SCOPE,
  PINNED_FICTIONAL_LINKS,
  errorCode,
  inspectFictionalFixtureLineage,
  type FictionalLineage,
  type FixtureMeta,
} from '../lib/ipc';

const EXPECTED_KINDS: Record<string, string> = {
  'fixture-patient-alpha': 'Patient',
  'fixture-allergy-beta': 'AllergyIntolerance',
  'fixture-observation-gamma': 'Observation',
  'fixture-bundle-delta': 'Bundle',
};

type LineageState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; graph: FictionalLineage }
  | { kind: 'error'; code: string };

function graphMatchesPinnedFixtures(graph: FictionalLineage, focus: FixtureMeta, fixtures: FixtureMeta[]) {
  if (
    graph.contract !== CONTRACT_LINEAGE ||
    graph.scope !== LINEAGE_SCOPE ||
    graph.focus_id !== focus.id ||
    graph.synthetic_only !== true ||
    graph.fhir_semantics_validated !== false ||
    graph.release_authorized !== false ||
    !Array.isArray(graph.nodes) || !Array.isArray(graph.edges) ||
    graph.nodes.length < 2 || graph.nodes.length > 4 || graph.edges.length > 4
  ) return false;

  const expectedEdges = PINNED_FICTIONAL_LINKS.filter((edge) =>
    edge.source_id === focus.id || edge.target_id === focus.id,
  );
  if (graph.edges.length !== expectedEdges.length) return false;
  if (!graph.edges.every((edge, index) =>
    edge.source_id === expectedEdges[index].source_id &&
    edge.target_id === expectedEdges[index].target_id &&
    edge.relationship === expectedEdges[index].relationship &&
    edge.source_pointer === expectedEdges[index].source_pointer
  )) return false;

  const involved = new Set<string>([focus.id]);
  for (const edge of expectedEdges) {
    involved.add(edge.source_id);
    involved.add(edge.target_id);
  }
  if (graph.nodes.length !== involved.size) return false;
  const found = new Set<string>();
  for (const node of graph.nodes) {
    const expected = fixtures.find((item) => item.id === node.fixture_id);
    if (
      !involved.has(node.fixture_id) || found.has(node.fixture_id) ||
      !expected || EXPECTED_KINDS[node.fixture_id] !== node.resource_type ||
      node.sha256_hex !== expected.sha256_hex ||
      node.byte_len !== expected.byte_len
    ) return false;
    found.add(node.fixture_id);
  }
  return found.size === involved.size;
}

/** Only four pinned fictional resources can be navigated: no generic graph, file or URI. */
export function FictionalFixtureLineage({
  fixture,
  fixtures,
  onSelectFixture,
}: {
  fixture: FixtureMeta;
  fixtures: FixtureMeta[];
  onSelectFixture: (id: string) => void;
}) {
  const [state, setState] = useState<LineageState>({ kind: 'idle' });

  async function inspect() {
    setState({ kind: 'loading' });
    try {
      const graph = await inspectFictionalFixtureLineage({ fixture_id: fixture.id });
      if (!graphMatchesPinnedFixtures(graph, fixture, fixtures)) {
        setState({ kind: 'error', code: 'lineage_contract_mismatch' });
        return;
      }
      setState({ kind: 'ready', graph });
    } catch (err) {
      setState({ kind: 'error', code: errorCode(err) });
    }
  }

  return (
    <section aria-label="Pinned fictional fixture lineage" className="fixture-lineage-section">
      <div className="search-row">
        <h2>Inspect fictional provenance links</h2>
        <button type="button" className="btn" aria-label="Inspect pinned fictional provenance links"
          onClick={inspect} disabled={state.kind === 'loading'}>
          {state.kind === 'loading' ? 'Checking links...' : 'Inspect provenance links'}
        </button>
      </div>
      <p className="sub">
        Native Rust resolves exactly four committed fictional JSON pointers against hash-pinned bytes.
        This is a <b>small synthetic lineage example</b>, not patient graph coverage or FHIR validation.
      </p>
      {state.kind === 'ready' && (
        <div className="panel" role="status" aria-label="Verified fictional fixture lineage">
          <div className="structure-summary">
            <GitBranch size={18} aria-hidden="true" className="brand-icon" />
            <strong>FICTIONAL PROVENANCE LINKS VERIFIED</strong>
          </div>
          <div className="lineage-links" aria-label="Pinned reference relationships">
            {state.graph.edges.map((edge) => (
              <div className="lineage-link" key={edge.source_id + edge.source_pointer}>
                <b className="mono">{edge.source_id}</b>
                <span aria-hidden="true">→</span>
                <b className="mono">{edge.target_id}</b>
                <small>{edge.relationship === 'fictional_bundle_member' ? 'Bundle example membership' : 'Fictional resource reference'}</small>
                <code>JSON pointer {edge.source_pointer}</code>
              </div>
            ))}
          </div>
          <div className="lineage-fixtures">
            <h3>Source-bound fictional files</h3>
            {state.graph.nodes.map((node) => (
              <div className="lineage-node" key={node.fixture_id}>
                <div>
                  <strong>{node.fixture_id}</strong>
                  <small className="mono">{node.resource_type} · {node.byte_len} bytes · SHA-256 {node.sha256_hex}</small>
                </div>
                {node.fixture_id !== fixture.id && (
                  <button type="button" className="btn"
                    aria-label={'Select related fictional fixture ' + node.fixture_id}
                    onClick={() => onSelectFixture(node.fixture_id)}>
                    Review source
                  </button>
                )}
              </div>
            ))}
          </div>
          <p className="sub">Only four pinned synthetic fixtures are in scope. FHIR semantics validated: <b>No</b>. No EHR or patient data access.</p>
        </div>
      )}
      {state.kind === 'error' && (
        <div className="error-box" role="alert" aria-label="Fictional provenance links refused">
          <ShieldAlert size={17} aria-hidden="true" />
          <strong>Provenance inspection refused</strong>
          <p>Untrusted or unavailable response (code: <span className="mono">{state.code}</span>). No trusted links shown.</p>
        </div>
      )}
    </section>
  );
}
