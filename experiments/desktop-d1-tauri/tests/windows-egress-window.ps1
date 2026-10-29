param(
  [Parameter(Mandatory = $true)]
  [ValidateRange(1, 2147483647)]
  [int]$RootPid,
  [ValidateRange(1.0, 600.0)]
  [double]$DurationSeconds = 10.0,
  [ValidateRange(50, 5000)]
  [int]$SampleIntervalMilliseconds = 250
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
  try {
    $result = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $probe -RootPid $RootPid 2>&1 | Out-String
    $code = $LASTEXITCODE
  }
  catch {
    # Avoid leaking PowerShell exception details or private local file paths.
    Write-Output 'D1_EGRESS_MONITOR_ERROR: snapshot invocation failed'
    exit 1
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
