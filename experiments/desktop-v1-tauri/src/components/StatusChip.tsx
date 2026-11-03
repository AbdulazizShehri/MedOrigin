import { STATUS_LABEL, type RouteStatus } from '../lib/routes';

export function StatusChip({ status }: { status: RouteStatus }) {
  return (
    <span className={`chip ${status}`} data-testid="status-chip">
      {STATUS_LABEL[status]}
    </span>
  );
}
