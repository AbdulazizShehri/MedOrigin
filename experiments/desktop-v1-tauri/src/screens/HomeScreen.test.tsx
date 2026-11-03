import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../lib/ipc', async (importOriginal) => {
  const original = await importOriginal<typeof import('../lib/ipc')>();
  return {
    ...original,
    getDesktopStatus: vi.fn(),
  };
});

import { getDesktopStatus, MOCK_STATUS } from '../lib/ipc';
import { HomeScreen } from './HomeScreen';

const mockedGet = vi.mocked(getDesktopStatus);

function renderHome() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <HomeScreen />
    </MemoryRouter>,
  );
}

describe('HomeScreen', () => {
  beforeEach(() => {
    mockedGet.mockReset();
  });

  it('renders the environment flags when the native host answers', async () => {
    mockedGet.mockResolvedValue({ ...MOCK_STATUS });
    renderHome();
    expect(await screen.findByText(/SYNTHETIC_DEVELOPER_PREVIEW/)).toBeInTheDocument();
    expect(screen.getByText(/release authorized:/i)).toHaveTextContent(/no/i);
    expect(screen.getByText(/SYNTHETIC — NOT EGRESS-QUALIFIED/)).toBeInTheDocument();
  });

  it('hard-blocks on native status failure instead of inventing defaults', async () => {
    mockedGet.mockRejectedValue(new Error('ipc down'));
    renderHome();
    expect(await screen.findByRole('alert')).toHaveTextContent(/Native status unavailable/i);
    expect(screen.queryByText(/SYNTHETIC_DEVELOPER_PREVIEW/)).not.toBeInTheDocument();
  });

  it('renders all 28 inventory rows and filters them', async () => {
    mockedGet.mockResolvedValue({ ...MOCK_STATUS });
    const { container } = renderHome();
    await screen.findByText(/SYNTHETIC_DEVELOPER_PREVIEW/);
    const table = screen.getByRole('table', { name: /Capability inventory/i });
    const rows = within(table).getAllByRole('row').slice(1); // minus header
    expect(rows.length).toBe(28);
    const filter = screen.getByLabelText(/Filter capabilities/i);
    filter.focus();
    filter.setAttribute('value', 'fhir');
    expect(container.querySelectorAll('.cap-row').length).toBeGreaterThan(0);
  });

  it('shows fixture-only status only for inspector and synthetic timeline', async () => {
    mockedGet.mockResolvedValue({ ...MOCK_STATUS });
    renderHome();
    await screen.findByText(/SYNTHETIC_DEVELOPER_PREVIEW/);
    const fixtureChips = screen.getAllByTestId('status-chip').filter((c) => c.textContent === 'Fixture-only');
    expect(fixtureChips).toHaveLength(2);
    expect(screen.getByText('FHIR fixture inspector')).toBeInTheDocument();
    expect(screen.getByText('Synthetic timeline')).toBeInTheDocument();
  });
});
