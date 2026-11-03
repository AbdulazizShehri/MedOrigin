import { ShieldAlert } from 'lucide-react';
import type { RouteEntry } from '../lib/routes';
import { StatusChip } from './StatusChip';

function required(status: RouteEntry['status']): string {
  switch (status) {
    case 'foundation':
      return 'A qualified, versioned desktop IPC command plus synthetic E2E and native Windows evidence for this capability.';
    case 'gated':
      return 'Separate written authorization from the process owners, a security review, and an independent qualification pass. This screen cannot grant it.';
    case 'deferred':
      return 'Scope expansion approval and its own qualification program.';
    case 'designed':
      return 'Backend qualification for the specific commands shown, then per-route integration.';
    case 'experiment':
      return 'Experimental exit criteria per the track README; not an integration contract.';
    case 'fixture-only':
      return 'Nothing further for this screen — its scope is exactly the fixtures listed.';
  }
}

export function HonestState({ route }: { route: RouteEntry }) {
  const isGated = route.status === 'gated' || route.status === 'deferred';
  return (
    <div className="panel" data-testid="honest-state" role="region" aria-label={`${route.label} — ${route.status}`}>
      <div className="panel-head">
        <h2>{route.label}</h2>
        <StatusChip status={route.status} />
      </div>
      <p>{route.reason}</p>
      <p>
        <b>Source anchor:</b>
        <br />
        <span className="anchor">{route.anchor}</span>
      </p>
      <p>
        <b>What would be required:</b>
        <br />
        {required(route.status)}
      </p>
      {isGated && (
        <div className="blocked-note" role="note">
          <ShieldAlert size={16} aria-hidden="true" className="blocked-icon" />
          <span>
            <b>Blocked.</b> No button here can enable this capability. Any workflow claiming to do so is fiction, not a feature.
          </span>
        </div>
      )}
    </div>
  );
}
