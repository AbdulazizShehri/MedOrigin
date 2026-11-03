import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../lib/ipc', async (importOriginal) => {
  const original = await importOriginal<typeof import('../lib/ipc')>();
  return {
    ...original,
    listSyntheticFixtures: vi.fn(),
    verifySyntheticFixture: vi.fn(),
  };
});

import {
  listSyntheticFixtures,
  verifySyntheticFixture,
  MOCK_FIXTURES,
  CONTRACT_LIST,
  CONTRACT_VERIFY,
} from '../lib/ipc';
import { FixtureInspectorScreen } from './FixtureInspectorScreen';

const mockList = vi.mocked(listSyntheticFixtures);
const mockVerify = vi.mocked(verifySyntheticFixture);

const listResponse = { contract: CONTRACT_LIST, fixtures: MOCK_FIXTURES.map((f) => ({ ...f })) };
const patient = MOCK_FIXTURES[0];

function renderInspector() {
  return render(
    <MemoryRouter initialEntries={['/fhir-inspector']}>
      <FixtureInspectorScreen />
    </MemoryRouter>,
  );
}

describe('FixtureInspectorScreen — connected slice', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockVerify.mockReset();
    mockList.mockResolvedValue(listResponse);
  });

  it('lists exactly the four allowlisted fixtures', async () => {
    renderInspector();
    for (const f of MOCK_FIXTURES) {
      expect(await screen.findByRole('button', { name: `Fixture ${f.id}` })).toBeInTheDocument();
    }
    expect(screen.getByText(/FICTIONAL — NOT CLINICAL DATA/i)).toBeInTheDocument();
  });

  it('verifies a selected fixture against the browser-mocked native contract', async () => {
    const user = userEvent.setup();
    mockVerify.mockResolvedValue({
      contract: CONTRACT_VERIFY,
      fixture_id: patient.id,
      byte_len: patient.byte_len,
      sha256_hex: patient.sha256_hex,
      synthetic_only: true,
      release_authorized: false,
    });
    renderInspector();
    await user.click(await screen.findByRole('button', { name: `Fixture ${patient.id}` }));
    await user.click(screen.getByRole('button', { name: /Verify fixture with native Rust/i }));
    const resultRegion = await screen.findByRole('status', { name: /Verification result/i });
    expect(resultRegion).toBeInTheDocument();
    expect(within(resultRegion).getByText(patient.sha256_hex)).toBeInTheDocument();
  });

  it('treats a sha256 mismatch as a failure and never marks the fixture verified', async () => {
    const user = userEvent.setup();
    mockVerify.mockResolvedValue({
      contract: CONTRACT_VERIFY,
      fixture_id: patient.id,
      byte_len: patient.byte_len,
      sha256_hex: '0'.repeat(64),
      synthetic_only: true,
      release_authorized: false,
    });
    renderInspector();
    await user.click(await screen.findByRole('button', { name: `Fixture ${patient.id}` }));
    await user.click(screen.getByRole('button', { name: /Verify fixture with native Rust/i }));
    expect(await screen.findByRole('alert', { name: /Verification failed/i })).toBeInTheDocument();
    expect(screen.queryByText(/byte-identical/i)).not.toBeInTheDocument();
  });

  it('rejects a response whose contract tag does not match', async () => {
    const user = userEvent.setup();
    mockVerify.mockResolvedValue({
      contract: 'medorigin-fixture-verify-v999',
      fixture_id: patient.id,
      byte_len: patient.byte_len,
      sha256_hex: patient.sha256_hex,
      synthetic_only: true,
      release_authorized: false,
    });
    renderInspector();
    await user.click(await screen.findByRole('button', { name: `Fixture ${patient.id}` }));
    await user.click(screen.getByRole('button', { name: /Verify fixture with native Rust/i }));
    expect(await screen.findByRole('alert', { name: /Verification failed/i })).toBeInTheDocument();
    expect(screen.getByText(/contract_mismatch/i)).toBeInTheDocument();
  });

  it('fails closed when the list contract is mismatched', async () => {
    mockList.mockResolvedValue({ contract: 'medorigin-fixtures-list-v999', fixtures: [] } as never);
    renderInspector();
    expect(await screen.findByRole('alert', { name: /Fixture list failed/i })).toBeInTheDocument();
  });

  it('fails closed when verification throws (e.g. native IPC stall)', async () => {
    const user = userEvent.setup();
    mockVerify.mockRejectedValue({ message: 'stalled' });
    renderInspector();
    await user.click(await screen.findByRole('button', { name: `Fixture ${patient.id}` }));
    await user.click(screen.getByRole('button', { name: /Verify fixture with native Rust/i }));
    await waitFor(() => expect(screen.getByRole('alert', { name: /Verification failed/i })).toBeInTheDocument());
  });

  it('shows the fixture-bundle note for the bundle fixture only', async () => {
    const user = userEvent.setup();
    const bundle = MOCK_FIXTURES.find((f) => f.id === 'fixture-bundle-delta')!;
    mockVerify.mockResolvedValue({
      contract: CONTRACT_VERIFY,
      fixture_id: bundle.id,
      byte_len: bundle.byte_len,
      sha256_hex: bundle.sha256_hex,
      synthetic_only: true,
      release_authorized: false,
    });
    renderInspector();
    await user.click(await screen.findByRole('button', { name: `Fixture ${bundle.id}` }));
    await user.click(screen.getByRole('button', { name: /Verify fixture with native Rust/i }));
    expect(await screen.findByText(/no FHIR structural or clinical validation/i)).toBeInTheDocument();
  });
});
