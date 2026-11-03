import { Home, Users, FileText, Mic, NotebookPen, ListTodo, CircleDollarSign, BookOpenText, Library, FileJson2, FlaskConical, Network, Clock, FileEdit, Table2, Search, ChartLine, Database, ShieldCheck, Microscope, Gauge, Boxes, Cable, ScrollText, HardDrive, Settings, Info, LifeBuoy, type LucideIcon } from 'lucide-react';

export type RouteStatus =
  | 'fixture-only'
  | 'foundation'
  | 'gated'
  | 'deferred'
  | 'experiment'
  | 'designed';

export type RouteGroup = 'Workspace' | 'Research' | 'Trust';

export interface RouteEntry {
  path: string;
  label: string;
  group: RouteGroup;
  status: RouteStatus;
  reason: string;
  anchor: string;
  icon: LucideIcon;
}

// Source of truth: docs/design/desktop-v1/SLICE1_SPEC.md Appendix R.
// Anchors are repository module paths, not URLs.
export const ROUTES: RouteEntry[] = [
  { path: '/', label: 'Home', group: 'Workspace', status: 'designed', reason: 'Shell route; honesty banner + full capability inventory.', anchor: 'apps/workspace/README.md', icon: Home },
  { path: '/patients', label: 'Synthetic patients', group: 'Workspace', status: 'foundation', reason: 'Identity/binding/graph modules exist in the Workspace foundation; no desktop adapter yet.', anchor: 'apps/workspace/src/medscale_workspace/identity.py', icon: Users },
  { path: '/encounters', label: 'Encounter detail', group: 'Workspace', status: 'foundation', reason: 'encounter/review modules; fixtures only, no live capture.', anchor: 'apps/workspace/src/medscale_workspace/encounter.py', icon: FileText },
  { path: '/audio', label: 'Audio & transcript', group: 'Workspace', status: 'gated', reason: 'Live microphone and ASR capture are not qualified; review-only contract.', anchor: 'apps/workspace/src/medscale_workspace/asr.py', icon: Mic },
  { path: '/notes', label: 'Clinical note drafts', group: 'Workspace', status: 'foundation', reason: 'draft/review contracts; synthetic-only editing.', anchor: 'apps/workspace/src/medscale_workspace/draft.py', icon: NotebookPen },
  { path: '/orders', label: 'Orders / tasks', group: 'Workspace', status: 'gated', reason: 'No auto-submit. Manual review gate; external write blocked.', anchor: 'specs/medscale-clinical-workspace-v1/capability_map.md (4.2)', icon: ListTodo },
  { path: '/coding', label: 'Coding suggestions', group: 'Workspace', status: 'deferred', reason: 'Out of authorized scope; billing submission never allowed.', anchor: 'specs/medscale-clinical-workspace-v1/capability_map.md', icon: CircleDollarSign },
  { path: '/evidence', label: 'Clinical evidence', group: 'Research', status: 'foundation', reason: 'retrieval/corpus/strength modules exist; not connected to the desktop UI yet.', anchor: 'apps/workspace/src/medscale_workspace/retrieval.py', icon: BookOpenText },
  { path: '/literature', label: 'Literature screening', group: 'Research', status: 'foundation', reason: 'litdb and screen modules; read-only first.', anchor: 'src/medscale/litdb/', icon: Library },
  { path: '/fhir', label: 'FHIR workspace', group: 'Research', status: 'foundation', reason: 'fhir_r4 + fhirkit; synthetic-only.', anchor: 'apps/workspace/src/medscale_workspace/fhir_r4.py', icon: FileJson2 },
  { path: '/fhir-inspector', label: 'FHIR fixture inspector', group: 'Workspace', status: 'fixture-only', reason: 'Connected Slices 1-4: allowlisted FICTIONAL fixture hash, source viewer, strict JSON subset and pinned provenance links. Not general FHIR validation.', anchor: 'experiments/desktop-v1-tauri (this track)', icon: FlaskConical },
  { path: '/graph', label: 'Patient graph', group: 'Workspace', status: 'foundation', reason: 'patient_graph/linked_workspace; synthetic only.', anchor: 'apps/workspace/src/medscale_workspace/patient_graph.py', icon: Network },
  { path: '/timeline', label: 'Patient timeline', group: 'Workspace', status: 'foundation', reason: 'Chronological view over the same graph modules.', anchor: 'apps/workspace/src/medscale_workspace/patient_graph.py', icon: Clock },
  { path: '/documents', label: 'Documents & canvas', group: 'Workspace', status: 'designed', reason: 'Structured notes and object blocks; not connected.', anchor: 'apps/workspace/src/medscale_workspace/draft.py', icon: FileEdit },
  { path: '/tables', label: 'Tables & structured data', group: 'Research', status: 'foundation', reason: 'dataset/analytics modules; local only.', anchor: 'apps/workspace/src/medscale_workspace/dataset.py', icon: Table2 },
  { path: '/search', label: 'Local search', group: 'Workspace', status: 'foundation', reason: 'Exact scope with readable provenance; offline errors.', anchor: 'apps/workspace/src/medscale_workspace/retrieval.py', icon: Search },
  { path: '/analytics', label: 'Analytics', group: 'Research', status: 'foundation', reason: 'Workspace-only indicators; no Research telemetry.', anchor: 'apps/workspace/src/medscale_workspace/analytics.py', icon: ChartLine },
  { path: '/datasets', label: 'Dataset manager', group: 'Research', status: 'foundation', reason: 'Research vs Workspace staging; no implicit cross-domain copy.', anchor: 'apps/workspace/src/medscale_workspace/dataset.py', icon: Database },
  { path: '/export', label: 'Export quarantine', group: 'Research', status: 'gated', reason: 'Quarantine manifest exists; Research admission is GATED — stop.', anchor: 'apps/workspace/src/medscale_workspace/nobackflow.py', icon: ShieldCheck },
  { path: '/research', label: 'Research explorer', group: 'Research', status: 'foundation', reason: 'Read-only hypotheses and experiment artifacts.', anchor: 'apps/workspace/src/medscale_workspace/research_view.py', icon: Microscope },
  { path: '/benchmarks', label: 'Benchmark & evaluation', group: 'Research', status: 'foundation', reason: 'Trusted results and frozen evaluator versions; training/promotion GATED.', anchor: 'src/medscale/bench/', icon: Gauge },
  { path: '/models', label: 'Model catalog & runtime', group: 'Research', status: 'gated', reason: 'Execution/download GATED; identity display only — never claims installed models.', anchor: 'src/medscale/modelkit/', icon: Boxes },
  { path: '/integrations', label: 'Integrations', group: 'Workspace', status: 'gated', reason: 'EHR write GATED; read-only dry-run contract later.', anchor: 'apps/workspace/src/medscale_workspace/connector.py', icon: Cable },
  { path: '/audit', label: 'Audit history', group: 'Trust', status: 'foundation', reason: 'Append-only events and provenance view; not connected in Slice 1.', anchor: 'apps/workspace/src/medscale_workspace/audit.py', icon: ScrollText },
  { path: '/storage', label: 'Storage & recovery', group: 'Trust', status: 'foundation', reason: 'Encrypted store / backup quarantine / key status; platform secret provider must qualify.', anchor: 'apps/workspace/src/medscale_workspace/storage.py', icon: HardDrive },
  { path: '/settings', label: 'Settings', group: 'Trust', status: 'designed', reason: 'Theme, density, shortcuts and the two storage keys — all implemented.', anchor: 'docs/design/desktop-v1/tokens.json; spec §C', icon: Settings },
  { path: '/about', label: 'About & diagnostics', group: 'Trust', status: 'designed', reason: 'Build identity from get_desktop_status; no PHI in logs.', anchor: 'CITATION.cff; spec §B', icon: Info },
  { path: '/help', label: 'Help & safety boundaries', group: 'Trust', status: 'designed', reason: 'Research-only / synthetic-only boundaries and incident workflow.', anchor: 'SECURITY.md; GOVERNANCE.md', icon: LifeBuoy },
];

export const ROUTE_GROUPS: RouteGroup[] = ['Workspace', 'Research', 'Trust'];

export function routeByPath(pathname: string): RouteEntry | undefined {
  const clean = pathname.replace(/\/+$/, '') || '/';
  return ROUTES.find((r) => r.path === clean);
}

export const STATUS_LABEL: Record<RouteStatus, string> = {
  'fixture-only': 'Fixture-only',
  foundation: 'Foundation',
  gated: 'Gated',
  deferred: 'Deferred',
  experiment: 'Experiment',
  designed: 'Designed',
};
