import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { ROUTES } from './lib/routes';

afterEach(() => {
  window.location.hash = '';
});

function renderAt(path: string) {
  window.location.hash = '#' + path;
  return render(<App />);
}

describe('App routing and shell', () => {
  it('renders every route without crashing', () => {
    for (const route of ROUTES) {
      const { unmount } = renderAt(route.path);
      expect(document.body.textContent).toBeTruthy();
      unmount();
    }
  }, 30_000); // 28 synchronous mounts can exceed Vitest's 5s default on a busy Windows host.

  it('every gated/deferred route shows a blocked explanation, never a working CTA', async () => {
    for (const route of ROUTES.filter((r) => r.status === 'gated' || r.status === 'deferred')) {
      const { unmount } = renderAt(route.path);
      const panel = await screen.findByTestId('honest-state');
      expect(within(panel).queryByRole('button')).toBeNull();
      expect(panel.textContent).toMatch(/block|authoriz|gat|scope|deferred/i);
      unmount();
    }
  });

  it('unknown paths redirect home', async () => {
    renderAt('/no/such/route');
    expect((await screen.findByRole('heading', { level: 1 })).textContent).toBe('Home');
  });

  it('Ctrl+K opens the palette and Escape closes it', async () => {
    const user = userEvent.setup();
    renderAt('/');
    expect(screen.queryByRole('dialog', { name: /Command palette/i })).toBeNull();
    await user.keyboard('{Control>}k{/Control}');
    expect(await screen.findByRole('dialog', { name: /Command palette/i })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: /Command palette/i })).toBeNull();
  });
});
