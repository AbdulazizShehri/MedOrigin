// MedOrigin D1 EGM source↔design drift checker.
// This checks concrete source contracts; it is NOT a fresh Goldfish review,
// OS packet/WFP attestation, signed launch, or release approval.
// No network calls, PHI, shell/process spawning, or external dependencies.
export function findD1SecurityDrift(s) {
  const issues = [];
  const requireSource = (name) => {
    if (typeof s?.[name] !== 'string' || s[name].length < 100)
      issues.push('missing_source:' + name);
    return typeof s?.[name] === 'string' ? s[name] : '';
  };
  const app = requireSource('app');
  const gate = requireSource('gate');
  const runner = requireSource('runner');
  const observer = requireSource('observer');
  const matrix = requireSource('matrix');
  const design = requireSource('design');
  const addUnless = (ok, id) => {if (!ok) issues.push(id)};
  // Assert the gate is called in run() before any GUI/IPC construction.
  const runAt = app.indexOf('pub fn run()');
  const gateAt = app.indexOf('medorigin_d1_windows_token_gate::require_windows_appcontainer_primary_token()',runAt);
  const builderAt = app.indexOf('tauri::Builder::default()',runAt);
  addUnless(runAt>=0 && gateAt>runAt && builderAt>gateAt &&
    app.slice(runAt,builderAt).includes('#[cfg(windows)]') &&
    app.slice(runAt,builderAt).includes('std::process::exit(76)'),
    'uncontained_app_startup');
  addUnless(app.includes('webview_runtime_egress_qualified: false') &&
    app.includes('release_authorized: false') &&
    app.includes('app_network_plugins_enabled: false'),
    'unapproved_product_readiness');

  // Scan read-only Windows primary token, with deny on missing classes,
  // well-known internet/private-network and the separately discovered
  // hostLoopback hashed SID. Lexical checks do not prove FFI semantics.
  addUnless(gate.includes('OpenProcessToken(process, 0x0008, &mut handle)') &&
    gate.split('GetTokenInformation(handle, 30,').length-1===2 &&
    /GetTokenInformation\(\s*handle,\s*29,/m.test(gate) &&
    gate.includes('primary_token_not_appcontainer') &&
    gate.includes('primary_token_capability_query_failed'),
    'missing_primary_token_admission');
  addUnless(['INTERNET_CLIENT','INTERNET_CLIENT_SERVER',
    'PRIVATE_NETWORK_CLIENT_SERVER','HOST_LOOPBACK'].every(x=>gate.includes(x)) &&
    gate.includes('2503302554') &&
    /EqualSid\(\s*sid,\s*\(&HOST_LOOPBACK as \*const SidWithTenSubAuthorities\)\.cast\(\)/m.test(gate) &&
    gate.includes('network_bits |= 1u8 << 3') &&
    gate.includes('reject_network_capability_bits(network_bits)'),
    'network_or_loopback_capability_not_denied');
  addUnless(gate.includes('if bits == 0') &&
    gate.includes('Err("primary_token_has_network_capability")') &&
    gate.includes('for bits in 1u8..16'),
    'network_bitmask_fails_open');

  // The real GUI harness must match the design's no-network policy.
  addUnless(runner.includes("network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}}") &&
    runner.includes("ui:{disable:false,isolation:'container'}") &&
    runner.includes("containment:{type:'process'}"),
    'native_gui_mxc_policy_drift');
  addUnless(runner.includes("actual.toLowerCase()===expected.toLowerCase()") &&
    runner.includes("requireSupportedWindowsMxcNode(process.versions.node,process.platform)") &&
    runner.includes("requireCondition((result.warnings||[]).length===0") &&
    runner.includes("uiaStatus===0") &&
    runner.includes('MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO') &&
    runner.includes("timeoutMs:90000") &&
    runner.includes('rmSync(tmp'),
    'native_gui_evidence_contract_drift');

  // The intentional permissive containers must be rejected by the
  // same imported token gate, not silently accepted as a fallback.
  for(const label of ['deny','allow-egress','allow-ingress','allow-both','allow-host-loopback'])
    addUnless(matrix.includes("label:'"+label+"'"), 'missing_policy_case:'+label);
  addUnless(matrix.includes("hostLoopback:config.hostLoopback||'deny'") &&
    matrix.includes("result.exitCode===76&&result.stderr?.includes('primary_token_has_network_capability')") &&
    matrix.includes("host.status===76") &&
    matrix.includes('D1_EXACT_RUNTIME_TOKEN_GATE_FIVE_POLICY_MATRIX_PASS_NO_WFP_ATTESTATION'),
    'permissive_network_policy_failopen');

  // TCP-only and root-PID-only observation are incomplete even as
  // *sampled* evidence. Keep UDP and descendant identity checks.
  addUnless(observer.includes('Get-NetTCPConnection') &&
    observer.split('Get-NetUDPEndpoint').length-1===2 &&
    observer.includes('Assert-MxcD1ProcessTreeContinuity') &&
    observer.split('Assert-MxcD1StableSocketWindow').length-1===2 &&
    observer.includes('Assert-MxcD1ObservedEndpoints') &&
    observer.includes('$sample -lt 12') &&
    observer.includes('NO_PACKET_LEVEL_ATTESTATION'),
    'socket_observation_scope_drift');

  // A source checker is not allowed to turn the document into GO.
  addUnless(design.includes('DRAFT / NOT APPROVED') &&
    design.includes('Goldfish review: NOT RUN') &&
    design.includes('Release: NO-GO') &&
    design.includes('independent OS') &&
    design.includes('positive control') &&
    design.includes('#662'),
    'design_review_status_or_packet_boundary_drift');
  return issues;
}
