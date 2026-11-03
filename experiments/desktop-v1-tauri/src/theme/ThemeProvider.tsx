import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from 'react';

export type ThemePreference = 'system' | 'light' | 'dark';
export type Density = 'compact' | 'comfortable';

interface ThemeContextValue {
  theme: ThemePreference;
  density: Density;
  setTheme: (t: ThemePreference) => void;
  setDensity: (d: Density) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const THEME_KEY = 'mo.theme';
const DENSITY_KEY = 'mo.density';

function readStoredTheme(): ThemePreference {
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system';
  } catch {
    return 'system';
  }
}

function readStoredDensity(): Density {
  try {
    return window.localStorage.getItem(DENSITY_KEY) === 'comfortable' ? 'comfortable' : 'compact';
  } catch {
    return 'compact';
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemePreference>(() => readStoredTheme());
  const [density, setDensityState] = useState<Density>(() => readStoredDensity());

  useEffect(() => {
    if (theme === 'system') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-density', density);
  }, [density]);

  const setTheme = useCallback((t: ThemePreference) => {
    setThemeState(t);
    try {
      window.localStorage.setItem(THEME_KEY, t);
    } catch {
      /* storage unavailable — preference stays in memory */
    }
  }, []);

  const setDensity = useCallback((d: Density) => {
    setDensityState(d);
    try {
      window.localStorage.setItem(DENSITY_KEY, d);
    } catch {
      /* storage unavailable — preference stays in memory */
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, density, setTheme, setDensity }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}
