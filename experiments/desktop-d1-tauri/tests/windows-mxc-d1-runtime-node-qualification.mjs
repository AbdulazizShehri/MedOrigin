// Pure fail-closed Windows MXC SDK runtime admission; no network or GUI.
export function requireSupportedWindowsMxcNode(version,platform){
  const valid=typeof version==='string' &&
    /^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/.test(version);
  if(platform!=='win32'||!valid){
    throw new Error('D1_MXC_NODE_RUNTIME_NO_GO: Windows and stable strict Node release required');
  }
  const [major,minor,patch]=version.split('.').map(Number);
  if(![major,minor,patch].every(Number.isSafeInteger)){
    throw new Error('D1_MXC_NODE_RUNTIME_NO_GO: unrepresentable Node version');
  }
  const allowed=(major===24&&minor>=21)||(major===26&&minor>=8);
  if(!allowed){
    throw new Error('D1_MXC_NODE_RUNTIME_NO_GO: requires Node 24.21+ or Node 26.8+ on Windows');
  }
  return Object.freeze({platform,version,qualified:true});
}
