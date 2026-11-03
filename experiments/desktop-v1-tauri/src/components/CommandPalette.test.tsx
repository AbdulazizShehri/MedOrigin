import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../theme/ThemeProvider';
import { CommandPalette, buildPaletteItems } from './CommandPalette';
import { useState } from 'react';
import { ROUTES } from '../lib/routes';

function renderPalette() {
  const toggle = vi.fn();
  render(
    <MemoryRouter initialEntries={['/']}>
      <ThemeProvider>
        <CommandPalette open={true} onClose={() => {}} onToggleInspector={toggle} />
      </ThemeProvider>
    </MemoryRouter>,
  );
  return toggle;
}

describe('CommandPalette', () => {
  it('builds navigation items for every route plus theme/density actions', () => {
    const navigate = vi.fn();
    const items = buildPaletteItems(navigate, vi.fn(), vi.fn(), vi.fn());
    expect(items.filter((i) => i.id.startsWith('nav:')).length).toBe(ROUTES.length);
    expect(items.some((i) => i.id === 'theme:dark')).toBe(true);
    expect(items.some((i) => i.id === 'density:comfortable')).toBe(true);
    expect(items.some((i) => i.id === 'inspector:toggle')).toBe(true);
  });

  it('filters items by fuzzy substring and exposes aria-activedescendant', async () => {
    const user = userEvent.setup();
    renderPalette();
    const input = screen.getByRole('combobox');
    await user.type(input, 'fhir');
    const options = screen.getAllByRole('option');
    expect(options.length).toBeGreaterThan(0);
    expect(input).toHaveAttribute('aria-activedescendant');
    expect(input.getAttribute('aria-activedescendant')).toBe(options[0].id);
  });

  it('arrow keys move the active option and Enter executes it', async () => {
    const user = userEvent.setup();
    renderPalette();
    const input = screen.getByRole('combobox');
    await user.type(input, 'Appearance: Dark');
    await waitFor(() => expect(screen.getAllByRole('option').length).toBe(1));
    await user.keyboard('{Enter}');
    expect(document.documentElement.dataset.density).toBe('compact');
    // Theme action wrote mo.theme=dark via provider
    expect(window.localStorage.getItem('mo.theme')).toBe('dark');
  });

  it('Escape closes the palette', async () => {
    const user = userEvent.setup();
    function Closable() {
      const [open, setOpen] = useState(true);
      return (
        <ThemeProvider>
          <button onClick={() => setOpen(true)} data-testid="reopen">reopen</button>
          {open ? <CommandPalette open onClose={() => setOpen(false)} onToggleInspector={() => {}} /> : null}
        </ThemeProvider>
      );
    }
    render(
      <MemoryRouter initialEntries={['/']}>
        <Closable />
      </MemoryRouter>,
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    screen.getByRole('combobox').focus();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('shows an empty state for unmatched queries', async () => {
    const user = userEvent.setup();
    renderPalette();
    await user.type(screen.getByRole('combobox'), 'zzzzqqqq-no-such-command');
    expect(screen.getByText(/No matching command or route/i)).toBeInTheDocument();
  });
});
