import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('../lib/ipc', async (load) => {
  const original = await load<typeof import('../lib/ipc')>();
  return { ...original, inspectFictionalPatientTimeline: vi.fn() };
});

import {
  CONTRACT_TIMELINE, LINEAGE_SCOPE, MOCK_FIXTURES,
  inspectFictionalPatientTimeline, type FictionalPatientTimeline,
} from '../lib/ipc';
import { FictionalTimelineScreen } from './FictionalTimelineScreen';
import { FixtureInspectorScreen } from './FixtureInspectorScreen';

const mockRead = vi.mocked(inspectFictionalPatientTimeline);
const meta = (id: string) => MOCK_FIXTURES.find((fixture) => fixture.id === id)!;

function valid(): FictionalPatientTimeline {
  const entry = (
    source: string, event_id: string, event_kind: string,
    kind: string, label: string, date: string | null,
    pointer: string | null, status: string,
  ) => ({
    source_fixture_id: source, source_resource_type: kind,
    source_sha256_hex: meta(source).sha256_hex, source_byte_len: meta(source).byte_len,
    event_id, event_kind, label, date, date_json_pointer: pointer, date_status: status,
  });
  return {
    contract: CONTRACT_TIMELINE,
    patient_fixture_id: 'fixture-patient-alpha',
    scope: LINEAGE_SCOPE,
    order: 'dated_descending_then_undated',
    synthetic_only: true,
    fhir_semantics_validated: false,
    release_authorized: false,
    events: [
      entry('fixture-allergy-beta', 'fictional-allergy-recorded', 'fictional_recorded_date',
        'AllergyIntolerance', 'Fictional allergy record date', '2026-01-01', '/recordedDate', 'source_date_only'),
      entry('fixture-patient-alpha', 'fictional-patient-dob', 'fictional_demographic_date',
        'Patient', 'Fictional example birth date', '1970-01-01', '/birthDate', 'source_date_only'),
      entry('fixture-observation-gamma', 'fictional-observation-undated', 'fictional_undated_observation',
        'Observation', 'Fictional observation (no recorded event date)', null, null, 'not_present_in_source'),
    ],
  };
}
function mount(withInspector = false) {
  return render(
    <MemoryRouter initialEntries={['/timeline']}>
      <Routes>
        <Route path="/timeline" element={<FictionalTimelineScreen />} />
        <Route path="/fhir-inspector" element={withInspector
          ? <FixtureInspectorScreen />
          : <div role="status" aria-label="Reached fictional inspector">FICTIONAL INSPECTOR</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('FictionalTimelineScreen — strictly bounded native proof', () => {
  beforeEach(() => { mockRead.mockReset(); mockRead.mockResolvedValue(valid()); });

  it('renders exactly two source-derived dates and explicitly undated observation', async () => {
    mount();
    const timeline = await screen.findByRole('region', { name: 'Verified fictional timeline' });
    expect(within(timeline).getByText('2026-01-01')).toHaveAttribute('datetime', '2026-01-01');
    expect(within(timeline).getByText('1970-01-01')).toHaveAttribute('datetime', '1970-01-01');
    expect(within(timeline).getByText('Undated — no event date in source')).toBeInTheDocument();
    expect(within(timeline).getByText('Fictional example birth date')).toBeInTheDocument();
    expect(within(timeline).getByText('Fictional allergy record date')).toBeInTheDocument();
    expect(within(timeline).getByText('Fictional observation (no recorded event date)')).toBeInTheDocument();
    expect(within(timeline).getAllByRole('button', { name: /^Review bundled fictional source/ })).toHaveLength(3);
    expect(mockRead).toHaveBeenCalledExactlyOnceWith({ fixture_id: 'fixture-patient-alpha' });
  });

  it('filters dated versus undated without changing source data', async () => {
    const user = userEvent.setup();
    mount();
    const events = await screen.findByRole('list', { name: 'Fictional date-only events' });
    expect(within(events).getAllByRole('listitem')).toHaveLength(3);
    await user.click(screen.getByRole('button', { name: 'Undated only (1)' }));
    expect(within(events).getAllByRole('listitem')).toHaveLength(1);
    expect(within(events).getByText('Undated — no event date in source')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Dated only (2)' }));
    expect(within(events).getAllByRole('listitem')).toHaveLength(2);
    expect(within(events).queryByText('Undated — no event date in source')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dated only (2)' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'All examples (3)' }));
    expect(within(events).getAllByRole('listitem')).toHaveLength(3);
  });

  it('refuses forged timestamp, SHA, extra event, order or clinical authorization', async () => {
    const scenarios = [
      { ...valid(), events: valid().events.map((event, i) =>
        i === 2 ? { ...event, date: '2026-01-02', date_status: 'source_date_only' } : event) },
      { ...valid(), events: valid().events.map((event, i) =>
        i === 0 ? { ...event, source_sha256_hex: '0'.repeat(64) } : event) },
      { ...valid(), events: [...valid().events, valid().events[0]] },
      { ...valid(), order: 'fake_descending' },
      { ...valid(), release_authorized: true },
      { ...valid(), fhir_semantics_validated: true },
    ];
    for (const scenario of scenarios) {
      mockRead.mockResolvedValue(scenario);
      const rendered = mount();
      expect(await screen.findByRole('alert', { name: 'Fictional timeline unavailable' })).toHaveTextContent('timeline_contract_mismatch');
      expect(screen.queryByRole('region', { name: 'Verified fictional timeline' })).not.toBeInTheDocument();
      rendered.unmount();
    }
  });

  it('fails closed if native Rust timeline command is unavailable', async () => {
    mockRead.mockRejectedValue({ code: 'unknown_patient_fixture' });
    mount();
    expect(await screen.findByRole('alert', { name: 'Fictional timeline unavailable' })).toHaveTextContent('unknown_patient_fixture');
    expect(screen.queryByText('2026-01-01')).not.toBeInTheDocument();
  });

  it('opens the allowlisted inspector in an UNVERIFIED state; never auto-verifies', async () => {
    const user = userEvent.setup();
    mount(true);
    await screen.findByRole('region', { name: 'Verified fictional timeline' });
    await user.click(screen.getByRole('button', { name: 'Review bundled fictional source fixture-allergy-beta' }));
    const selected = await screen.findByRole('button', { name: 'Fixture fixture-allergy-beta' });
    await waitFor(() => expect(selected).toHaveAttribute('aria-pressed', 'true'));
    expect(screen.queryByRole('status', { name: 'Verification result' })).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Verified fictional JSON text' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Verify fixture with native Rust' })).toBeEnabled();
  });
});
