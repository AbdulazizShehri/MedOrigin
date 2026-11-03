import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarDays, CircleAlert, ShieldCheck, Clock3, FileJson2 } from 'lucide-react';
import {
  CONTRACT_TIMELINE,
  LINEAGE_SCOPE,
  MOCK_FIXTURES,
  errorCode,
  inspectFictionalPatientTimeline,
  type FictionalPatientTimeline,
  type FictionalTimelineEvent,
} from '../lib/ipc';

type TimelineState =
  | { kind: 'loading' }
  | { kind: 'ready'; value: FictionalPatientTimeline }
  | { kind: 'error'; code: string };

type TimelineFilter = 'all' | 'dated' | 'undated';

type ExpectedEvent = Pick<FictionalTimelineEvent,
  'event_id' | 'event_kind' | 'source_fixture_id' | 'source_resource_type' |
  'date' | 'date_json_pointer' | 'date_status' | 'label'>;

const PINNED_EVENTS: readonly ExpectedEvent[] = [
  {
    event_id: 'fictional-allergy-recorded',
    event_kind: 'fictional_recorded_date',
    source_fixture_id: 'fixture-allergy-beta',
    source_resource_type: 'AllergyIntolerance',
    date: '2026-01-01',
    date_json_pointer: '/recordedDate',
    date_status: 'source_date_only',
    label: 'Fictional allergy record date',
  },
  {
    event_id: 'fictional-patient-dob',
    event_kind: 'fictional_demographic_date',
    source_fixture_id: 'fixture-patient-alpha',
    source_resource_type: 'Patient',
    date: '1970-01-01',
    date_json_pointer: '/birthDate',
    date_status: 'source_date_only',
    label: 'Fictional example birth date',
  },
  {
    event_id: 'fictional-observation-undated',
    event_kind: 'fictional_undated_observation',
    source_fixture_id: 'fixture-observation-gamma',
    source_resource_type: 'Observation',
    date: null,
    date_json_pointer: null,
    date_status: 'not_present_in_source',
    label: 'Fictional observation (no recorded event date)',
  },
];

function isTrustedTimeline(value: FictionalPatientTimeline): boolean {
  if (
    !value || value.contract !== CONTRACT_TIMELINE ||
    value.patient_fixture_id !== 'fixture-patient-alpha' ||
    value.scope !== LINEAGE_SCOPE ||
    value.order !== 'dated_descending_then_undated' ||
    value.synthetic_only !== true ||
    value.fhir_semantics_validated !== false ||
    value.release_authorized !== false ||
    !Array.isArray(value.events) ||
    value.events.length !== PINNED_EVENTS.length
  ) return false;

  return value.events.every((event, index) => {
    const expected = PINNED_EVENTS[index];
    const fixture = MOCK_FIXTURES.find((f) => f.id === expected.source_fixture_id);
    return Boolean(
      fixture &&
      event.event_id === expected.event_id &&
      event.event_kind === expected.event_kind &&
      event.source_fixture_id === expected.source_fixture_id &&
      event.source_resource_type === expected.source_resource_type &&
      event.source_sha256_hex === fixture.sha256_hex &&
      event.source_byte_len === fixture.byte_len &&
      event.date === expected.date &&
      event.date_json_pointer === expected.date_json_pointer &&
      event.date_status === expected.date_status &&
      event.label === expected.label
    );
  });
}

/**
 * One fictional patient, 2 date-only source values and 1 explicitly undated
 * observation. Never extrapolate timestamps or clinical event semantics.
 */
export function FictionalTimelineScreen() {
  const navigate = useNavigate();
  const [state, setState] = useState<TimelineState>({ kind: 'loading' });
  const [filter, setFilter] = useState<TimelineFilter>('all');

  useEffect(() => {
    let cancelled = false;
    inspectFictionalPatientTimeline({ fixture_id: 'fixture-patient-alpha' })
      .then((value) => {
        if (!cancelled) setState(isTrustedTimeline(value)
          ? { kind: 'ready', value }
          : { kind: 'error', code: 'timeline_contract_mismatch' });
      })
      .catch((error) => {
        if (!cancelled) setState({ kind: 'error', code: errorCode(error) });
      });
    return () => { cancelled = true; };
  }, []);

  const displayed = useMemo(() => {
    if (state.kind !== 'ready') return [];
    if (filter === 'dated') return state.value.events.filter((event) => event.date !== null);
    if (filter === 'undated') return state.value.events.filter((event) => event.date === null);
    return state.value.events;
  }, [state, filter]);

  return (
    <>
      <span className="eyebrow">MEDORIGIN / FICTIONAL SOURCE-BOUND TIMELINE / SLICE 5</span>
      <h1 className="page-title">Synthetic patient timeline</h1>
      <p className="sub">
        A second connected desktop route, using the native Rust host to project three
        fictional examples from four committed fixtures. Dates are source values, not inferred event times.
      </p>

      <div className="honesty-banner" role="note" aria-label="Timeline safety notice">
        <ShieldCheck size={18} aria-hidden="true" className="brand-icon" />
        <span>
          <b>FICTIONAL DATA ONLY — NOT A CLINICAL TIMELINE</b>
          <br />
          Only two recorded date values exist in these examples. The observation has no event date
          and must remain undated. Neither FHIR semantics nor WebView2 zero-egress is qualified.
        </span>
      </div>

      {state.kind === 'loading' && (
        <div className="loading-skeleton" aria-label="Loading native fictional timeline" />
      )}
      {state.kind === 'error' && (
        <div className="error-box" role="alert" aria-label="Fictional timeline unavailable">
          <CircleAlert size={17} aria-hidden="true" />
          <strong>Timeline evidence refused</strong>
          <p>Native source contract is missing or inconsistent (<code>{state.code}</code>).
            No chronology is displayed as verified.</p>
        </div>
      )}

      {state.kind === 'ready' && (
        <section aria-label="Verified fictional timeline">
          <div className="timeline-summary panel">
            <div className="timeline-summary-heading">
              <CalendarDays size={20} aria-hidden="true" className="brand-icon" />
              <div>
                <strong>FICTIONAL DATE-ONLY TIMELINE</strong>
                <p className="sub">One synthetic patient · four pinned source files · no actual encounters</p>
              </div>
            </div>
            <div className="timeline-stat-row">
              <div><strong>2</strong><span>Dated source fields</span></div>
              <div><strong>1</strong><span>Undated example</span></div>
              <div><strong>0</strong><span>Clinical validations</span></div>
            </div>
          </div>

          <div className="timeline-controls" role="group" aria-label="Filter fictional timeline">
            {([
              ['all', 'All examples (3)'],
              ['dated', 'Dated only (2)'],
              ['undated', 'Undated only (1)'],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={'btn timeline-filter' + (filter === value ? ' timeline-filter-active' : '')}
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>

          <ol className="timeline-events" aria-label="Fictional date-only events">
            {displayed.map((event) => (
              <li className="timeline-event" key={event.event_id}>
                <div className="timeline-event-track" aria-hidden="true">
                  {event.date === null ? <Clock3 size={16} /> : <CalendarDays size={16} />}
                </div>
                <div className="timeline-event-body">
                  <div className="timeline-event-header">
                    {event.date === null
                      ? <span className="timeline-event-date undated">Undated — no event date in source</span>
                      : <time className="timeline-event-date" dateTime={event.date}>{event.date}</time>}
                    <span className="timeline-event-kind">{event.source_resource_type}</span>
                  </div>
                  <h2>{event.label}</h2>
                  <p className="sub">
                    {event.date === null
                      ? 'Observation contains no effectiveDateTime, issued, or recordedDate field. No timestamp is invented.'
                      : event.event_kind === 'fictional_demographic_date'
                        ? 'Demographic birthDate field only — not an encounter or medical event.'
                        : 'recordedDate field only — not proof that an allergic event occurred on this date.'}
                  </p>
                  <div className="timeline-provenance">
                    <div>
                      <span>Bundled fictional source</span>
                      <code>{event.source_fixture_id}</code>
                    </div>
                    <div>
                      <span>Date provenance</span>
                      <code>{event.date_json_pointer ?? 'Not present in source'}</code>
                    </div>
                    <div>
                      <span>Source SHA-256</span>
                      <code className="timeline-sha">{event.source_sha256_hex}</code>
                    </div>
                  </div>
                  <button
                    className="btn timeline-source-button"
                    type="button"
                    aria-label={'Review bundled fictional source ' + event.source_fixture_id}
                    onClick={() => navigate('/fhir-inspector?fixture=' + encodeURIComponent(event.source_fixture_id))}
                  >
                    <FileJson2 size={15} aria-hidden="true" /> Review fictional source
                  </button>
                </div>
              </li>
            ))}
          </ol>
          <p className="sub">
            Choosing a source opens the separate inspector in an unverified state. Re-run its
            native SHA-256 verification before viewing source text, structural checks or provenance.
          </p>
        </section>
      )}
    </>
  );
}
