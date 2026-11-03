import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { webcrypto } from 'node:crypto';

vi.mock('../lib/ipc', async (load) => {
  const original = await load<typeof import('../lib/ipc')>();
  return { ...original, readSyntheticFixtureSource: vi.fn() };
});

import {
  CONTRACT_SOURCE,
  MOCK_FIXTURES,
  readSyntheticFixtureSource,
  type FixtureSource,
} from '../lib/ipc';
import patientRaw from '../../src-tauri/fixtures/fixture-patient-alpha.json?raw';
import { VerifiedFixtureSource } from './VerifiedFixtureSource';

const patient = MOCK_FIXTURES[0];
const mockRead = vi.mocked(readSyntheticFixtureSource);

const validSource: FixtureSource = {
  contract: CONTRACT_SOURCE,
  fixture_id: patient.id,
  media_type: patient.media_type,
  byte_len: patient.byte_len,
  sha256_hex: patient.sha256_hex,
  text: patientRaw,
  synthetic_only: true,
  release_authorized: false,
};

describe('VerifiedFixtureSource', () => {
  beforeEach(() => {
    mockRead.mockReset();
    mockRead.mockResolvedValue({ ...validSource });
    Object.defineProperty(globalThis.crypto, 'subtle', { value: webcrypto.subtle, configurable: true });
  });

  it('reveals only hash-checked fictional committed bytes after explicit request', async () => {
    const user = userEvent.setup();
    render(<VerifiedFixtureSource fixture={patient} />);
    expect(screen.queryByRole('region', { name: 'Verified fictional JSON text' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Inspect verified fictional JSON source' }));
    const region = await screen.findByRole('region', { name: 'Verified fictional JSON text' });
    expect(region).toHaveTextContent('FICTIONAL');
    expect(region).toHaveTextContent('"resourceType": "Patient"');
    expect(mockRead).toHaveBeenCalledWith({ fixture_id: patient.id });
  });

  it('refuses spoofed metadata and never renders source', async () => {
    mockRead.mockResolvedValue({ ...validSource, synthetic_only: false });
    const user = userEvent.setup();
    render(<VerifiedFixtureSource fixture={patient} />);
    await user.click(screen.getByRole('button', { name: 'Inspect verified fictional JSON source' }));
    expect(await screen.findByRole('alert', { name: 'Source inspection failed' })).toHaveTextContent('source_contract_mismatch');
    expect(screen.queryByRole('region', { name: 'Verified fictional JSON text' })).not.toBeInTheDocument();
  });

  it('refuses changed bytes even if the host reports the original hash and size', async () => {
    mockRead.mockResolvedValue({ ...validSource, text: patientRaw.replace('EXAMPLEPERSON', 'OTHEREXAMPLEX') });
    const user = userEvent.setup();
    render(<VerifiedFixtureSource fixture={patient} />);
    await user.click(screen.getByRole('button', { name: 'Inspect verified fictional JSON source' }));
    expect(await screen.findByRole('alert', { name: 'Source inspection failed' })).toHaveTextContent('source_hash_mismatch');
    expect(screen.queryByRole('region', { name: 'Verified fictional JSON text' })).not.toBeInTheDocument();
  });

  it('refuses non-allowlisted source failures without echoing user input', async () => {
    mockRead.mockRejectedValue({ code: 'unknown_fixture' });
    const user = userEvent.setup();
    render(<VerifiedFixtureSource fixture={patient} />);
    await user.click(screen.getByRole('button', { name: 'Inspect verified fictional JSON source' }));
    expect(await screen.findByRole('alert', { name: 'Source inspection failed' })).toHaveTextContent('unknown_fixture');
  });
});
