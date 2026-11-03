import { Link, useLocation } from 'react-router-dom';
import { ROUTE_GROUPS, ROUTES } from '../lib/routes';

export function Sidebar() {
  const location = useLocation();
  const clean = location.pathname.replace(/\/+$/, '') || '/';

  return (
    <aside className="sidebar" aria-label="MedOrigin navigation">
      <div className="brand">
        <span className="brand-dot" aria-hidden="true" />
        <span className="brand-name">MedOrigin</span>
      </div>
      <div className="ribbon" role="note">
        <b>SYNTHETIC / DEVELOPER PREVIEW</b>
        <br />
        Not a clinical product. No patient data.
      </div>
      {ROUTE_GROUPS.map((group) => (
        <nav key={group} aria-label={`${group} section`}>
          <div className="nav-label">{group}</div>
          {ROUTES.filter((r) => r.group === group).map((r) => {
            const active = r.path === clean;
            const Icon = r.icon;
            return (
              <Link
                key={r.path}
                to={r.path}
                className="nav-link"
                aria-current={active ? 'page' : undefined}
                aria-label={`${r.label} — ${r.status}`}
              >
                <span className="nav-icon" aria-hidden="true">
                  <Icon size={16} strokeWidth={1.75} />
                </span>
                <span>{r.label}</span>
              </Link>
            );
          })}
        </nav>
      ))}
      <div className="sidebar-bottom">
        MedOrigin Desktop v1 · Slice 1
        <br />
        Local-first · Synthetic only
        <br />
        Not egress-qualified
      </div>
    </aside>
  );
}
