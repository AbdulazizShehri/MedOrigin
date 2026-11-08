# Native D2 synthetic-only Windows observer runner.
# This script cannot qualify OS-enforced isolation, DNS, packet capture or release.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Executable,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
  [ValidateRange(1,30)][int]$Samples=3
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$owned=$null
$outcome=4
try {
  $resolved=(Resolve-Path -LiteralPath $Executable -ErrorAction Stop).Path
  if ([IO.Path]::GetFileName($resolved) -cne 'medorigin-desktop-d2-native-egui.exe') {
    Write-Output 'D2_SMOKE_NO_GO_EXECUTABLE_NAME'
  } elseif ((Get-FileHash -LiteralPath $resolved -Algorithm SHA256 -ErrorAction Stop).Hash -ine $ExpectedSha256) {
    Write-Output 'D2_SMOKE_NO_GO_PINNED_SHA_MISMATCH'
  } else {
    $observer=Join-Path $PSScriptRoot 'windows-network-socket-observation.ps1'
    if (-not (Test-Path -LiteralPath $observer -PathType Leaf)) {
      Write-Output 'D2_SMOKE_NO_GO_OBSERVER_MISSING'
    } else {
      # The input is a source-built test-only executable, not a patient-data app.
      # One process is launched with no elevated privileges or firewall mutation.
      $owned=Start-Process -FilePath $resolved -WorkingDirectory (Split-Path $resolved) -PassThru -ErrorAction Stop
      Start-Sleep -Milliseconds 1000
      if ($owned.HasExited) {
        Write-Output 'D2_SMOKE_NO_GO_PREMATURE_EXIT'
      } else {
        Write-Output 'D2_SMOKE_PROCESS_STARTED_SYNTHETIC_ONLY'
        & $observer -RootPid $owned.Id -ExpectedSha256 $ExpectedSha256 -ExpectedExecutableName 'medorigin-desktop-d2-native-egui.exe' -Samples $Samples -IntervalMs 250
        $outcome=$LASTEXITCODE
        if ($outcome -eq 0) {
          Write-Output 'D2_SMOKE_NO_GO_UNSAFE_OBSERVER_SUCCESS'
          $outcome=4
        }
      }
    }
  }
} catch {
  # Intentionally redact exception detail, including any paths.
  Write-Output 'D2_SMOKE_NO_GO_OBSERVATION_ERROR'
  $outcome=4
} finally {
  if ($null -ne $owned) {
    try {
      $owned.Refresh()
      if (-not $owned.HasExited) { Stop-Process -Id $owned.Id -Force -ErrorAction Stop }
      Write-Output 'D2_SMOKE_OWNED_PROCESS_CLEANUP_DONE'
    } catch {
      Write-Output 'D2_SMOKE_NO_GO_PROCESS_CLEANUP_FAILED'
      $outcome=4
    }
  }
}
# All outcomes remain nonzero. This is a negative-gate tool, not approval.
if ($outcome -eq 0) { $outcome=4 }
exit $outcome
