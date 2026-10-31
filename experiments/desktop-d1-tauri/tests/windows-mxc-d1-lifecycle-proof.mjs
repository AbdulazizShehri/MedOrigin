// Pure fail-closed parser for an actual MXC D1 process-tree lifecycle observation.
// The process IDs and start ticks are source-bound test evidence, NOT WFP or packet proof.
const rootName = 'medorigin-desktop-d1-preview.exe';
const webviewName = 'msedgewebview2.exe';
function validate(items, requireTree) {
  if (!Array.isArray(items) || (requireTree && items.length < 2) || items.length > 128)
    throw Error('D1_LIFECYCLE_NO_GO: invalid process inventory length');
  const ids = new Set();
  for (const item of items) {
    if (!item || !Number.isSafeInteger(item.pid) || item.pid < 1 ||
        typeof item.startTicks !== 'string' || !/^\d{15,20}$/.test(item.startTicks) ||
        typeof item.name !== 'string' || !/^[a-zA-Z0-9._-]{1,128}$/.test(item.name) ||
        ids.has(item.pid))
      throw Error('D1_LIFECYCLE_NO_GO: invalid or duplicate process identity');
    ids.add(item.pid);
  }
  if (requireTree && (items.filter(x=>x.name.toLowerCase()===rootName).length!==1 ||
      !items.some(x=>x.name.toLowerCase()===webviewName)))
    throw Error('D1_LIFECYCLE_NO_GO: actual D1 root and WebView2 required');
  return items;
}
export function parseD1Snapshot(output) {
  if (typeof output !== 'string') throw Error('D1_LIFECYCLE_NO_GO: missing output');
  const matches = [...output.matchAll(/^MXC_D1_PROCESS_SNAPSHOT_JSON=(.+)$/gm)];
  if (matches.length !== 1) throw Error('D1_LIFECYCLE_NO_GO: missing or repeated snapshot');
  let parsed;
  try { parsed = JSON.parse(matches[0][1]); }
  catch { throw Error('D1_LIFECYCLE_NO_GO: malformed snapshot'); }
  return validate(parsed,true);
}
export function requireQualifiedRun({status,stdout}) {
  if (status !== 0 || typeof stdout !== 'string' ||
      !stdout.includes('MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO') ||
      !stdout.includes('D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO') ||
      !stdout.includes('MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12'))
    throw Error('D1_LIFECYCLE_NO_GO: real GUI/IPC/network-window qualification missing');
  return parseD1Snapshot(stdout);
}
export function assertNoResidual(original, live) {
  validate(original,true);
  validate(live,false);
  const expected = new Set(original.map(x=>x.pid+'@'+x.startTicks));
  const lingering = live.filter(x=>expected.has(x.pid+'@'+x.startTicks));
  if (lingering.length) throw Error('D1_LIFECYCLE_NO_GO: exact process descendants survived sandbox termination');
  return true;
}
