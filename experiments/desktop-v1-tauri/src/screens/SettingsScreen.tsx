import { useTheme, type ThemePreference, type Density } from '../theme/ThemeProvider';

const THEME_OPTIONS: { value: ThemePreference; label: string; description: string }[] = [
  { value: 'light', label: 'Light', description: 'Stone canvas, ink text, qualified accent.' },
  { value: 'dark', label: 'Dark', description: 'Charcoal foundation with the dark accent role.' },
  { value: 'system', label: 'System', description: 'Follows prefers-color-scheme; no flicker at launch.' },
];

const DENSITY_OPTIONS: { value: Density; label: string; description: string }[] = [
  { value: 'compact', label: 'Compact', description: '13 px body, 38 px controls, 40 px rows. Default.' },
  { value: 'comfortable', label: 'Comfortable', description: '14 px body, 44 px controls and rows.' },
];

const SHORTCUTS: { keys: string; action: string }[] = [
  { keys: 'Ctrl K', action: 'Open command palette' },
  { keys: 'Ctrl Shift I', action: 'Toggle inspector' },
  { keys: 'Esc', action: 'Close palette' },
];

const STORAGE_KEYS: { key: string; scope: string }[] = [
  { key: 'mo.theme', scope: 'system | light | dark' },
  { key: 'mo.density', scope: 'compact | comfortable' },
];

export function SettingsScreen() {
  const { theme, density, setTheme, setDensity } = useTheme();

  return (
    <>
      <span className="eyebrow">MEDORIGIN / TRUST / SETTINGS</span>
      <h1 className="page-title">Settings</h1>
      <p className="sub">Every control on this page works. Nothing else is pretending to.</p>

      <section className="panel" aria-label="Appearance">
        <h3>Appearance</h3>
        <fieldset className="option-group">
          <legend>Theme</legend>
          {THEME_OPTIONS.map((o) => (
            <label key={o.value} className="option-row">
              <input type="radio" name="mo-theme" checked={theme === o.value} onChange={() => setTheme(o.value)} />
              <span>
                <b>{o.label}</b>
                <small>{o.description}</small>
              </span>
            </label>
          ))}
        </fieldset>
        <fieldset className="option-group">
          <legend>Density</legend>
          {DENSITY_OPTIONS.map((o) => (
            <label key={o.value} className="option-row">
              <input type="radio" name="mo-density" checked={density === o.value} onChange={() => setDensity(o.value)} />
              <span>
                <b>{o.label}</b>
                <small>{o.description}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </section>

      <section className="panel" aria-label="Keyboard shortcuts">
        <h3>Keyboard shortcuts</h3>
        <ul className="inline-list">
          {SHORTCUTS.map((s) => (
            <li key={s.keys} className="status-line">
              <kbd className="kbd">{s.keys}</kbd> <span>{s.action}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel" aria-label="Local storage">
        <h3>Local storage — complete inventory</h3>
        <p>Exactly two keys are ever written, both non-sensitive UI preferences. No fixture content, no logs, no telemetry.</p>
        <ul className="inline-list">
          {STORAGE_KEYS.map((k) => (
            <li key={k.key} className="status-line">
              <span className="mono">{k.key}</span> <span>{k.scope}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
