param(
  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 2147483647)]
  [int]$RootPid,
  [ValidateRange(1.0, 600.0)]
  [double]$DurationSeconds = 10.0,
  [ValidateRange(50, 5000)]
  [int]$SampleIntervalMilliseconds = 250,
  [ValidateRange(1, 60)]
  [int]$ProbeTimeoutSeconds = 10
)

# A repeated, deliberately narrow socket *observation* gate, not an OS firewall
# or a zero-egress proof. Keep invoking the separately self-tested fail-closed
# process-tree snapshot. No system-wide network configuration is modified.
$ErrorActionPreference = 'Stop'
$probe = Join-Path $PSScriptRoot 'windows-egress-snapshot.ps1'
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) {
  Write-Output 'D1_EGRESS_MONITOR_ERROR: missing snapshot probe'
  exit 1
}
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$samples = 0
do {
  # A separate process plus asynchronous pipe reads bounds *each* invocation.
  # A hung CIM query must not make the diagnostic monitor wait indefinitely.
  $settings = [System.Diagnostics.ProcessStartInfo]::new()
  $settings.FileName = 'powershell.exe'
  $settings.Arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $probe + '" -RootPid ' + $RootPid
  $settings.UseShellExecute = $false
  $settings.CreateNoWindow = $true
  $settings.RedirectStandardOutput = $true
  $settings.RedirectStandardError = $true
  $child = [System.Diagnostics.Process]::new()
  $child.StartInfo = $settings
  $started = $false
  try {
    $started = $child.Start()
    if (-not $started) { throw 'Snapshot could not be started' }
    $stdout = $child.StandardOutput.ReadToEndAsync()
    $stderr = $child.StandardError.ReadToEndAsync()
    if (-not $child.WaitForExit($ProbeTimeoutSeconds * 1000)) {
      throw 'Snapshot exceeded per-probe deadline'
    }
    if (-not $stdout.Wait(1000) -or -not $stderr.Wait(1000)) {
      throw 'Snapshot pipe capture incomplete'
    }
    $result = $stdout.Result
    $code = $child.ExitCode
  }
  catch {
    # Never reproduce untrusted output, arguments, OS paths or exception data.
    Write-Output 'D1_EGRESS_MONITOR_ERROR: snapshot failed or timed out'
    exit 1
  }
  finally {
    if ($started -and -not $child.HasExited) {
      try { $child.Kill() } catch { }
    }
    $child.Dispose()
  }
  $samples++
  if ($code -eq 2) {
    Write-Output ('D1_NETWORK_ISOLATION_NO_GO sample=' + $samples)
    Write-Output $result.TrimEnd()
    exit 2
  }
  if ($code -ne 0 -or -not $result.Contains('D1_SNAPSHOT_NO_EXTERNAL_TCP')) {
    Write-Output ('D1_EGRESS_MONITOR_ERROR: inconclusive snapshot sample=' + $samples)
    exit 1
  }
  $remaining = $DurationSeconds * 1000 - $watch.Elapsed.TotalMilliseconds
  if ($remaining -le 0) { break }
  Start-Sleep -Milliseconds ([int][Math]::Min($remaining, $SampleIntervalMilliseconds))
} while ($true)

if ($samples -lt 2) {
  Write-Output 'D1_EGRESS_MONITOR_ERROR: insufficient successful samples'
  exit 1
}
Write-Output ('D1_WINDOW_SNAPSHOT_CLEAR samples=' + $samples)
Write-Output 'Observed snapshots only: zero TCP sockets does NOT demonstrate zero egress. OS enforcement, UDP/DNS, short-lived attempts and packet evidence remain NO-GO.'
