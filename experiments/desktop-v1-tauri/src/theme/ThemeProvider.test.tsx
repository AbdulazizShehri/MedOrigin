import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme } from './ThemeProvider';

function Probe() {
  const { theme, density, setTheme, setDensity } = useTheme();
  return (
    <div>
      <output data-testid="theme">{theme}</output>
      <output data-testid="density">{density}</output>
      <output data-testid="dt">{document.documentElement.dataset.theme ?? 'none'}</output>
      <button onClick={() => setTheme('dark')}>dark</button>
      <button onClick={() => setTheme('light')}>light</button>
      <button onClick={() => setTheme('system')}>system</button>
      <button onClick={() => setDensity('comfortable')}>comfortable</button>
      <button onClick={() => setDensity('compact')}>compact</button>
    </div>
  );
}

describe('ThemeProvider', () => {
  it('defaults to system theme and compact density', async () => {
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('system');
    expect(screen.getByTestId('density')).toHaveTextContent('compact');
    expect(document.documentElement.dataset.density).toBe('compact');
  });

  it('persists only mo.theme and mo.density', async () => {
    const user = userEvent.setup();
    render(<ThemeProvider><Probe /></ThemeProvider>);
    await user.click(screen.getByText('dark'));
    await user.click(screen.getByText('comfortable'));
    const keys: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) keys.push(window.localStorage.key(i)!);
    expect(keys.sort()).toEqual(['mo.density', 'mo.theme']);
    expect(window.localStorage.getItem('mo.theme')).toBe('dark');
    expect(window.localStorage.getItem('mo.density')).toBe('comfortable');
  });

  it('restores persisted values on mount and sets data-theme', async () => {
    window.localStorage.setItem('mo.theme', 'light');
    window.localStorage.setItem('mo.density', 'comfortable');
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.dataset.density).toBe('comfortable');
  });

  it('ignores hostile stored values without crashing', async () => {
    window.localStorage.setItem('mo.theme', '"; DROP TABLE'); 
    window.localStorage.setItem('mo.density', 'spacious');
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('system');
    expect(screen.getByTestId('density')).toHaveTextContent('compact');
  });

  it('system removes the data-theme attribute', async () => {
    const user = userEvent.setup();
    render(<ThemeProvider><Probe /></ThemeProvider>);
    await user.click(screen.getByText('dark'));
    expect(document.documentElement.dataset.theme).toBe('dark');
    await user.click(screen.getByText('system'));
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });
});
