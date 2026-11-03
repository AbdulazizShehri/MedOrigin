import { useCallback, useEffect, useRef, useState } from 'react';
import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import './styles/tokens.css';
import './app.css';
import { ThemeProvider } from './theme/ThemeProvider';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { Inspector } from './components/Inspector';
import { CommandPalette } from './components/CommandPalette';
import { ErrorBoundary } from './components/ErrorBoundary';
import { HonestState } from './components/HonestState';
import { HomeScreen } from './screens/HomeScreen';
import { FixtureInspectorScreen } from './screens/FixtureInspectorScreen';
import { SettingsScreen } from './screens/SettingsScreen';
import { AboutScreen } from './screens/AboutScreen';
import { HelpScreen } from './screens/HelpScreen';
import { ROUTES, routeByPath } from './lib/routes';

function RoutedView() {
  const location = useLocation();
  const route = routeByPath(location.pathname);

  if (location.pathname === '/' || location.pathname === '') return <HomeScreen />;
  if (location.pathname === '/fhir-inspector') return <FixtureInspectorScreen />;
  if (location.pathname === '/settings') return <SettingsScreen />;
  if (location.pathname === '/about') return <AboutScreen />;
  if (location.pathname === '/help') return <HelpScreen />;
  if (route) return <HonestState route={route} />;
  return <Navigate to="/" replace />;
}

function Shell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [inspectorVisible, setInspectorVisible] = useState(true);
  const paletteTriggerRef = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  const route = routeByPath(location.pathname) ?? ROUTES[0];

  const closePalette = useCallback(() => {
    setPaletteOpen(false);
    paletteTriggerRef.current?.focus();
  }, []);

  const toggleInspector = useCallback(() => setInspectorVisible((v) => !v), []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      } else if (mod && e.shiftKey && e.key.toLowerCase() === 'i') {
        e.preventDefault();
        setInspectorVisible((v) => !v);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const trail = [route.group, route.label];

  return (
    <div className="shell">
      <Sidebar />
      <div className="content">
        <TopBar
          trail={trail}
          onOpenPalette={() => setPaletteOpen(true)}
          inspectorVisible={inspectorVisible}
          onToggleInspector={toggleInspector}
          triggerRef={paletteTriggerRef}
          paletteOpen={paletteOpen}
        />
        <div className={inspectorVisible ? 'main' : 'main inspector-hidden'}>
          <main className="work" aria-label="Workspace">
            <div className="work-inner">
              <ErrorBoundary>
                <RoutedView />
              </ErrorBoundary>
            </div>
          </main>
          {inspectorVisible && <Inspector route={route} onHide={() => setInspectorVisible(false)} />}
        </div>
      </div>
      <CommandPalette open={paletteOpen} onClose={closePalette} onToggleInspector={toggleInspector} />
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <ThemeProvider>
        <Routes>
          <Route path="*" element={<Shell />} />
        </Routes>
      </ThemeProvider>
    </HashRouter>
  );
}
