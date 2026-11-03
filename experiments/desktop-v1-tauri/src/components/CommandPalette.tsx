import { useEffect, useMemo, useRef, useState, useId } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../lib/routes';
import { useTheme } from '../theme/ThemeProvider';

export interface PaletteItem {
  id: string;
  label: string;
  hint: string;
  run: () => void;
}

export function buildPaletteItems(navigate: (to: string) => void, setTheme: (t: 'system' | 'light' | 'dark') => void, setDensity: (d: 'compact' | 'comfortable') => void, toggleInspector: () => void): PaletteItem[] {
  const nav = ROUTES.map((r) => ({
    id: `nav:${r.path}`,
    label: `Go to ${r.label}`,
    hint: r.path,
    run: () => navigate(r.path),
  }));
  const theme: PaletteItem[] = [
    { id: 'theme:light', label: 'Appearance: Light', hint: 'theme', run: () => setTheme('light') },
    { id: 'theme:dark', label: 'Appearance: Dark', hint: 'theme', run: () => setTheme('dark') },
    { id: 'theme:system', label: 'Appearance: System', hint: 'theme', run: () => setTheme('system') },
  ];
  const density: PaletteItem[] = [
    { id: 'density:compact', label: 'Density: Compact', hint: 'density', run: () => setDensity('compact') },
    { id: 'density:comfortable', label: 'Density: Comfortable', hint: 'density', run: () => setDensity('comfortable') },
  ];
  return [
    ...nav,
    ...theme,
    ...density,
    { id: 'inspector:toggle', label: 'Toggle inspector', hint: 'Ctrl+Shift+I', run: toggleInspector },
  ];
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onToggleInspector: () => void;
}

export function CommandPalette({ open, onClose, onToggleInspector }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { setTheme, setDensity } = useTheme();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo(
    () => buildPaletteItems(navigate, setTheme, setDensity, onToggleInspector),
    [navigate, setTheme, setDensity, onToggleInspector],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => `${item.label} ${item.hint}`.toLowerCase().includes(q));
  }, [items, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      // Focus after the palette mounts.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => { setActiveIndex(0); }, [query]);

  if (!open) return null;

  const active = filtered[Math.min(activeIndex, Math.max(filtered.length - 1, 0))];

  function runItem(item: PaletteItem | undefined) {
    if (!item) return;
    item.run();
    onClose();
  }

  return (
    <div className="scrim" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="palette" role="dialog" aria-modal="true" aria-label="Command palette">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls={listId}
          aria-activedescendant={active ? `palette-option-${active.id}` : undefined}
          aria-autocomplete="list"
          aria-label="Type a command or route"
          placeholder="Type a command or route…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setActiveIndex((i) => (filtered.length ? (i + 1) % filtered.length : 0));
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setActiveIndex((i) => (filtered.length ? (i - 1 + filtered.length) % filtered.length : 0));
            } else if (e.key === 'Enter') {
              e.preventDefault();
              runItem(active);
            } else if (e.key === 'Escape') {
              e.preventDefault();
              onClose();
            }
          }}
        />
        <div className="palette-list" role="listbox" id={listId} aria-label="Commands">
          {filtered.length === 0 && <div className="palette-empty">No matching command or route.</div>}
          {filtered.map((item, index) => (
            <button
              key={item.id}
              id={`palette-option-${item.id}`}
              type="button"
              role="option"
              aria-selected={active?.id === item.id}
              className="palette-item"
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => runItem(item)}
            >
              <span>{item.label}</span>
              <small>{item.hint}</small>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
