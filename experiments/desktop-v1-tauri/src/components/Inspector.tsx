import { X } from 'lucide-react';
import type { RouteEntry } from '../lib/routes';

interface InspectorProps {
  route: RouteEntry;
  onHide: () => void;
}

export function Inspector({ route, onHide }: InspectorProps) {
  return (
    <aside className="inspector" aria-label="Context inspector">
      <h2>
        <span>Inspector</span>
        <button type="button" className="inspector-toggle" onClick={onHide} aria-label="Hide inspector" title="Hide inspector (Ctrl+Shift+I)">
          <X size={15} aria-hidden="true" />
        </button>
      </h2>

      <div className="detail">
        <strong>About this screen</strong>
        <p>{route.reason}</p>
      </div>

      <div className="detail">
        <strong>Source anchor</strong>
        <p><code>{route.anchor}</code></p>
      </div>

      <div className="detail">
        <strong>State · status</strong>
        <p>
          {route.status === 'fixture-only' && 'Connected to the Slice-1 native fixture command only. Everything else is unmounted by design.'}
          {route.status === 'foundation' && 'Python foundation exists and is contract-tested; the desktop route is intentionally not wired yet.'}
          {route.status === 'gated' && 'Blocked behind a separate authorization. The desktop must not fake an enabled control.'}
          {route.status === 'deferred' && 'Outside the currently authorized scope.'}
          {route.status === 'designed' && 'Interface implemented honestly; backend integration pending its own qualification.'}
          {route.status === 'experiment' && 'Experimental track; not production, not releasable.'}
        </p>
      </div>

      <div className="detail">
        <strong>Security boundary</strong>
        <p>Synthetic data only. No PHI, no EHR access, no model execution, no Research Core admission. Frontend controls are not security controls; the Rust host fails closed.</p>
      </div>

      <div className="note">
        <b>Product rule</b>
        A disabled action with a visible reason is safer than a simulated success. Nothing on this page manufactures a result.
      </div>
    </aside>
  );
}
