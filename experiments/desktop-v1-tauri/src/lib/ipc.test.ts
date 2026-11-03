import { describe, it, expect, vi, afterEach } from 'vitest';
import { withStallGuard, MO_IPC_STALL_MS } from './ipc';

afterEach(() => {
  vi.useRealTimers();
});

describe('withStallGuard', () => {
  it('resolves when the promise settles before the stall budget', async () => {
    await expect(withStallGuard(Promise.resolve('ok'))).resolves.toBe('ok');
  });

  it('rejects with a stalled error after MO_IPC_STALL_MS on a never-settling promise', async () => {
    vi.useFakeTimers();
    const never = new Promise(() => {});
    const guarded = withStallGuard(never);
    const assertion = expect(guarded).rejects.toThrow('stalled');
    await vi.advanceTimersByTimeAsync(MO_IPC_STALL_MS + 10);
    await assertion;
  });

  it('a late resolution cannot rescue a stalled promise', async () => {
    vi.useFakeTimers();
    let resolveInner: (v: string) => void = () => {};
    const inner = new Promise<string>((res) => {
      resolveInner = res;
    });
    const guarded = withStallGuard(inner);
    const assertion = expect(guarded).rejects.toThrow('stalled');
    await vi.advanceTimersByTimeAsync(MO_IPC_STALL_MS + 10);
    resolveInner('late');
    await vi.advanceTimersByTimeAsync(1000);
    await assertion;
  });
});
