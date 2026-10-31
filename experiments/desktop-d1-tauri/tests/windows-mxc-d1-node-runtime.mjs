// Fail-closed host runtime gate for unpublished Windows D1 MXC testing.
// Microsoft MXC SDK 1.0.1 Windows native stdio requires Node 24.21+ or 26.8+.
// Future unverified major versions are intentionally rejected until qualified.
export function assertSupportedWindowsMxcNode({
  platform=process.platform, version=process.versions.node
}={}) {
  const match=typeof version==='string'
    ? /^(24|26)\.(\d+)\.(\d+)$/.exec(version) : null;
  const major=match ? Number(match[1]) : -1;
  const minor=match ? Number(match[2]) : -1;
  const patch=match ? Number(match[3]) : -1;
  const supported=Number.isSafeInteger(minor) && Number.isSafeInteger(patch)
    && ((major===24 && minor>=21) || (major===26 && minor>=8));
  if (platform!=='win32' || !supported) {
    throw new Error('D1_MXC_NODE_RUNTIME_UNSUPPORTED: require Windows Node 24.21+ or 26.8+ (verified major only)');
  }
  return true;
}
