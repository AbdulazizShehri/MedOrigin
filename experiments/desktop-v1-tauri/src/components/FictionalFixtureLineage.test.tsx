import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../lib/ipc', async (load) => {
  const original = await load<typeof import('../lib/ipc')>();
  return { ...original, inspectFictionalFixtureLineage: vi.fn() };
});
import {
  CONTRACT_LINEAGE, LINEAGE_SCOPE, MOCK_FIXTURES, PINNED_FICTIONAL_LINKS,
  inspectFictionalFixtureLineage, type FictionalLineage,
} from '../lib/ipc';
import { FictionalFixtureLineage } from './FictionalFixtureLineage';

const kinds: Record<string, string> = {
  'fixture-patient-alpha': 'Patient',
  'fixture-allergy-beta': 'AllergyIntolerance',
  'fixture-observation-gamma': 'Observation',
  'fixture-bundle-delta': 'Bundle',
};
const focus = MOCK_FIXTURES[0];
const readMock = vi.mocked(inspectFictionalFixtureLineage);
function validGraph(): FictionalLineage {
  const edges = PINNED_FICTIONAL_LINKS
    .filter((edge) => edge.source_id === focus.id || edge.target_id === focus.id)
    .map((edge) => ({ ...edge }));
  const involved = new Set([focus.id]);
  for (const edge of edges) { involved.add(edge.source_id); involved.add(edge.target_id); }
  return {
    contract: CONTRACT_LINEAGE,
    scope: LINEAGE_SCOPE,
    focus_id: focus.id,
    nodes: MOCK_FIXTURES.filter((f) => involved.has(f.id)).map((f) => ({
      fixture_id: f.id, resource_type: kinds[f.id], sha256_hex: f.sha256_hex, byte_len: f.byte_len,
    })),
    edges,
    synthetic_only: true, fhir_semantics_validated: false, release_authorized: false,
  };
}
const go = async () => {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Inspect pinned fictional provenance links' }));
};
describe('FictionalFixtureLineage', () => {
  beforeEach(() => { readMock.mockReset(); readMock.mockResolvedValue(validGraph()); });
  it('reveals no relationships before user action and reports precisely bounded provenance', async () => {
    render(<FictionalFixtureLineage fixture={focus} fixtures={MOCK_FIXTURES} onSelectFixture={vi.fn()} />);
    expect(screen.queryByRole('status', { name: 'Verified fictional fixture lineage' })).not.toBeInTheDocument();
    await go();
    const panel = await screen.findByRole('status', { name: 'Verified fictional fixture lineage' });
    expect(panel).toHaveTextContent('FICTIONAL PROVENANCE LINKS VERIFIED');
    expect(panel).toHaveTextContent('/patient/reference');
    expect(panel).toHaveTextContent('/subject/reference');
    expect(panel).toHaveTextContent('/entry/0/resource');
    expect(panel).toHaveTextContent('FHIR semantics validated:');
    expect(panel).toHaveTextContent('No');
    expect(readMock).toHaveBeenCalledWith({ fixture_id: focus.id });
  });
  it('lets user navigate only to another pinned fixture', async () => {
    const choose = vi.fn();
    const user = userEvent.setup();
    render(<FictionalFixtureLineage fixture={focus} fixtures={MOCK_FIXTURES} onSelectFixture={choose} />);
    await go();
    const linked = await screen.findByRole('button', { name: 'Select related fictional fixture fixture-observation-gamma' });
    await user.click(linked);
    expect(choose).toHaveBeenCalledExactlyOnceWith('fixture-observation-gamma');
    expect(screen.queryByRole('button', { name: 'Select related fictional fixture fixture-patient-alpha' })).not.toBeInTheDocument();
  });
  it('refuses injected external pointer edge with no positive status', async () => {
    readMock.mockResolvedValue({ ...validGraph(), edges: [
      ...validGraph().edges,
      { source_id: 'https://attacker.invalid', target_id: focus.id, relationship: 'fictional_reference', source_pointer: '/etc/secret' },
    ] });
    render(<FictionalFixtureLineage fixture={focus} fixtures={MOCK_FIXTURES} onSelectFixture={vi.fn()} />);
    await go();
    expect(await screen.findByRole('alert', { name: 'Fictional provenance links refused' })).toHaveTextContent('lineage_contract_mismatch');
    expect(screen.queryByRole('status', { name: 'Verified fictional fixture lineage' })).not.toBeInTheDocument();
  });
  it('refuses forged metadata, duplicate nodes and prohibited clinical authorization', async () => {
    for (const variant of [
      { ...validGraph(), release_authorized: true },
      { ...validGraph(), nodes: [...validGraph().nodes, validGraph().nodes[0]] },
      { ...validGraph(), nodes: validGraph().nodes.map((n, i) => i === 0 ? { ...n, sha256_hex: '0'.repeat(64) } : n) },
    ]) {
      readMock.mockResolvedValue(variant);
      const { unmount } = render(<FictionalFixtureLineage fixture={focus} fixtures={MOCK_FIXTURES} onSelectFixture={vi.fn()} />);
      await go();
      expect(await screen.findByRole('alert', { name: 'Fictional provenance links refused' })).toHaveTextContent('lineage_contract_mismatch');
      unmount();
    }
  });
  it('fails closed on native typed errors', async () => {
    readMock.mockRejectedValue({ code: 'unknown_fixture' });
    render(<FictionalFixtureLineage fixture={focus} fixtures={MOCK_FIXTURES} onSelectFixture={vi.fn()} />);
    await go();
    expect(await screen.findByRole('alert', { name: 'Fictional provenance links refused' })).toHaveTextContent('unknown_fixture');
  });
});
