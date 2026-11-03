import { PanelRight, Search } from 'lucide-react';
import { useTheme, type ThemePreference, type Density } from '../theme/ThemeProvider';

interface TopBarProps {
  trail: string[];
  onOpenPalette: () => void;
  inspectorVisible: boolean;
  onToggleInspector: () => void;
  triggerRef?: React.Ref<HTMLButtonElement>;
  paletteOpen: boolean;
}

const THEMES: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

const DENSITIES: { value: Density; label: string }[] = [
  { value: 'compact', label: 'Compact' },
  { value: 'comfortable', label: 'Comfortable' },
];

export function TopBar({ trail, onOpenPalette, inspectorVisible, onToggleInspector, triggerRef, paletteOpen }: TopBarProps) {
  const { theme, density, setTheme, setDensity } = useTheme();

  return (
    <header className="topbar">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        MedOrigin / <b>{trail.join(' / ')}</b>
      </nav>

      <button type="button" ref={triggerRef} className="palette-trigger" onClick={onOpenPalette} aria-label="Open command palette" aria-keyshortcuts="Control+K" aria-expanded={paletteOpen}>
        <Search size={14} aria-hidden="true" />
        <span>Palette</span>
        <kbd className="kbd">Ctrl K</kbd>
      </button>

      <div className="segment" role="group" aria-label="Density">
        {DENSITIES.map((d) => (
          <button key={d.value} type="button" aria-pressed={density === d.value} onClick={() => setDensity(d.value)}>
            {d.label}
          </button>
        ))}
      </div>

      <div className="segment" role="group" aria-label="Appearance">
        {THEMES.map((t) => (
          <button key={t.value} type="button" aria-pressed={theme === t.value} onClick={() => setTheme(t.value)}>
            {t.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        className="inspector-toggle"
        onClick={onToggleInspector}
        aria-label={inspectorVisible ? 'Hide inspector' : 'Show inspector'}
        aria-pressed={inspectorVisible}
        aria-keyshortcuts="Control+Shift+I"
        title="Toggle inspector (Ctrl+Shift+I)"
      >
        <PanelRight size={16} aria-hidden="true" />
      </button>
    </header>
  );
}
