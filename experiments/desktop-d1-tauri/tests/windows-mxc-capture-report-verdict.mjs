// Pure fail-closed verifier for an experimental MXC block-mode capture report.
// Does not claim OS process-tree or UDP packet-level proof.
export function assessCaptureResult(result, files, readReport) {
  if (!result || result.timedOut || result.exitCode !== 0) {
    throw Error('CAPTURE_NO_GO: native contained probe did not exit successfully');
  }
  if (!Array.isArray(result.warnings) || result.warnings.length !== 0) {
    throw Error('CAPTURE_NO_GO: SDK enforcement or capture emitted warning');
  }
  const stdout = result.stdout || '';
  for (const exact of [
    'D1_MXC_SYNTHETIC_LOCALHOST=WSA10013',
    'D1_MXC_SYNTHETIC_TEST_NET_2=WSA10013',
    'D1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS',
  ]) {
    if (!stdout.split(/\r?\n/).includes(exact)) {
      throw Error('CAPTURE_NO_GO: native WSAEACCES proof incomplete');
    }
  }
  if (!Array.isArray(files) || files.length !== 1 ||
    !/^denials(?:\.[a-zA-Z0-9_-]+)?\.json$/.test(files[0])) {
    throw Error('CAPTURE_NO_GO: exactly one identifiable denial JSON required');
  }
  const contents = readReport(files[0]);
  const parsed = JSON.parse(contents);
  if (!parsed || !Array.isArray(parsed.denials) || parsed.denials.length === 0 ||
    !parsed.summary || typeof parsed.summary !== 'object' || Array.isArray(parsed.summary)) {
    throw Error('CAPTURE_NO_GO: denial report missing valid nonempty denials or summary');
  }
  return {denialRows: parsed.denials.length, reportExists: true, classification: 'NOT_WFP_OR_PACKET_ATTESTED'};
}
