import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../lib/ipc', async (load) => {
  const original = await load<typeof import('../lib/ipc')>();
  return { ...original, inspectSyntheticFixtureStructure: vi.fn() };
});

import {
  CONTRACT_STRUCTURE,
  MOCK_FIXTURES,
  inspectSyntheticFixtureStructure,
  type FixtureStructuralEvidence,
} from '../lib/ipc';
import { FixtureStructuralSubset } from './FixtureStructuralSubset';

const patient = MOCK_FIXTURES[0];
const inspectMock = vi.mocked(inspectSyntheticFixtureStructure);

const valid: FixtureStructuralEvidence = {
  contract: CONTRACT_STRUCTURE,
  fixture_id: patient.id,
  resource_type: 'Patient',
  resource_id: patient.id,
  byte_len: patient.byte_len,
  sha256_hex: patient.sha256_hex,
  reference_count: 0,
  bundle_entry_count: 0,
  duplicate_keys_rejected: true,
  structural_subset_checked: true,
  fhir_semantics_validated: false,
  synthetic_only: true,
  release_authorized: false,
};

async function clickCheck() {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Check fictional JSON structural subset' }));
}

describe('FixtureStructuralSubset', () => {
  beforeEach(() => {
    inspectMock.mockReset();
    inspectMock.mockResolvedValue({ ...valid });
  });

  it('does not claim structure pass before explicit button click', async () => {
    render(<FixtureStructuralSubset fixture={patient} />);
    expect(screen.queryByRole('status', { name: 'Fictional structural subset result' })).not.toBeInTheDocument();
    await clickCheck();
    const status = await screen.findByRole('status', { name: 'Fictional structural subset result' });
    expect(status).toHaveTextContent('FICTIONAL STRUCTURAL SUBSET CHECKED');
    expect(status).toHaveTextContent('Rejected at any depth');
    expect(status).toHaveTextContent('FHIR semantics validated');
    expect(status).toHaveTextContent('No');
    expect(inspectMock).toHaveBeenCalledWith({ fixture_id: patient.id });
  });

  it('refuses forged semantic-validation claims', async () => {
    inspectMock.mockResolvedValue({ ...valid, fhir_semantics_validated: true });
    render(<FixtureStructuralSubset fixture={patient} />);
    await clickCheck();
    expect(await screen.findByRole('alert', { name: 'Structural subset refused' })).toHaveTextContent('structure_contract_mismatch');
    expect(screen.queryByRole('status', { name: 'Fictional structural subset result' })).not.toBeInTheDocument();
  });

  it('refuses mismatched fixture identity or hash', async () => {
    inspectMock.mockResolvedValue({ ...valid, sha256_hex: 'f'.repeat(64) });
    render(<FixtureStructuralSubset fixture={patient} />);
    await clickCheck();
    expect(await screen.findByRole('alert', { name: 'Structural subset refused' })).toHaveTextContent('structure_contract_mismatch');
  });

  it('refuses inconsistent reference counts', async () => {
    inspectMock.mockResolvedValue({ ...valid, reference_count: 900 });
    render(<FixtureStructuralSubset fixture={patient} />);
    await clickCheck();
    expect(await screen.findByRole('alert', { name: 'Structural subset refused' })).toHaveTextContent('structure_contract_mismatch');
  });

  it('keeps native error codes and does not expose raw input', async () => {
    inspectMock.mockRejectedValue({ code: 'structural_subset_rejected' });
    render(<FixtureStructuralSubset fixture={patient} />);
    await clickCheck();
    expect(await screen.findByRole('alert', { name: 'Structural subset refused' })).toHaveTextContent('structural_subset_rejected');
  });
});
