# Developer-only network isolation evidence, not a MedOrigin runtime guarantee.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExePath,
    [ValidateSet('Host', 'Hold', 'Outbound', 'UIA')][string]$Mode = 'Host',
    [int]$HoldSeconds = 25
)
$ErrorActionPreference = 'Stop'
$exe = (Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
$ui = Join-Path $PSScriptRoot 'windows-uia-smoke.ps1'
$observer = Join-Path $PSScriptRoot 'windows-egress-window.ps1'

function Test-TcpConnection {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $pending = $client.ConnectAsync('1.1.1.1', 443)
        return [bool]$pending.Wait(2500)
    }
    catch { return $false }
    finally { $client.Dispose() }
}

if ($Mode -eq 'Outbound') {
    if (Test-TcpConnection) { Write-Output 'MXC_NETWORK_ESCAPE'; exit 2 }
    Write-Output 'MXC_NETWORK_DENIED_PROBE'
    exit 0
}
if ($Mode -eq 'Hold') {
    $process = Start-Process -FilePath $exe -PassThru
    Write-Output ('MXC_D1_HELD_PID=' + $process.Id)
    try { Start-Sleep -Seconds $HoldSeconds }
    finally {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Output 'MXC_D1_HOLD_COMPLETED'
    exit 0
}
if ($Mode -eq 'UIA') {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ui -ExePath $exe
    if ($LASTEXITCODE -ne 0) { throw 'MXC D1 UIA smoke failed' }
    Write-Output 'MXC_D1_UIA_COMPLETED'
    exit 0
}

# Host mode never edits the firewall and refuses ambiguous process attribution.
if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI with native MXC support unavailable'
}
$versionOutput = [string](& codex --version)
if ($versionOutput -notmatch 'codex-cli\s+(\d+)\.(\d+)') { throw 'Unrecognised Codex CLI version' }
if ([int]$Matches[1] -eq 0 -and [int]$Matches[2] -lt 162) {
    throw 'Codex CLI 0.162 or later is required for Windows MXC'
}
if (-not (Test-TcpConnection)) {
    throw 'HOST_CONTROL_INCONCLUSIVE: TCP endpoint unreachable outside MXC'
}
Write-Output 'HOST_EXTERNAL_TCP_CONTROL_CONNECTED'

$existing = @(Get-CimInstance Win32_Process -ErrorAction Stop |
    Where-Object { $_.Name -eq [IO.Path]::GetFileName($exe) })
if ($existing.Count -ne 0) { throw 'D1 preview already running; process identity ambiguous' }

$base = @('-c', 'windows.sandbox=mxc', 'sandbox',
          '--include-managed-config', '--permission-profile', ':workspace',
          '--', 'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
          '-File', $PSCommandPath, '-ExePath', $exe)
$out = @(& codex @base -Mode Outbound 2>&1)
if ($LASTEXITCODE -ne 0 -or -not ($out -contains 'MXC_NETWORK_DENIED_PROBE')) {
    throw ('MXC network negative test failed: ' + ($out -join '; '))
}
Write-Output 'MXC_EXTERNAL_TCP_NEGATIVE_PASS'

$out = @(& codex @base -Mode UIA 2>&1)
if ($LASTEXITCODE -ne 0 -or -not ($out -contains 'D1_UIA_4_OF_4_PASS (synthetic SHA only; NOT FHIR validation)') -or
    -not ($out -contains 'MXC_D1_UIA_COMPLETED')) {
    throw ('MXC IPC/UIA test failed: ' + ($out -join '; '))
}
Write-Output 'MXC_D1_UIA_FOUR_OF_FOUR_PASS'

# CIM is denied inside MXC. Host-side polling binds the actual app PID and
# sees the full WebView2 descendant tree using the existing independent probe.
$job = Start-Job -ArgumentList (,$base) -ScriptBlock {
    param([string[]]$arguments)
    & codex @arguments -Mode Hold -HoldSeconds 25
    if ($LASTEXITCODE -ne 0) { throw ('MXC hold subprocess failed: ' + $LASTEXITCODE) }
}
$rootPid = $null
try {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $candidate = @(Get-CimInstance Win32_Process -ErrorAction Stop |
            Where-Object { $_.Name -eq [IO.Path]::GetFileName($exe) -and $_.ExecutablePath -eq $exe })
        if ($candidate.Count -gt 1) { throw 'Ambiguous D1 roots; cannot qualify network PID' }
        if ($candidate.Count -eq 1) { $rootPid = [int]$candidate[0].ProcessId; break }
        if ($job.State -ne 'Running') { throw 'MXC process exited before host observation' }
        Start-Sleep -Milliseconds 400
    }
    if (-not $rootPid) { throw 'D1 process did not start under MXC' }
    Write-Output ('HOST_BOUND_MXC_D1_PID=' + $rootPid)
    $observation = @(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $observer -RootPid $rootPid -DurationSeconds 6 -SampleIntervalMilliseconds 300 -ProbeTimeoutSeconds 10 2>&1)
    $clear = @($observation | Where-Object { $_ -match '^D1_WINDOW_SNAPSHOT_CLEAR samples=([0-9]+)$' })
    if ($LASTEXITCODE -ne 0 -or $clear.Count -ne 1) {
        throw ('HOST_MXC_EGRESS_NOT_QUALIFIED: ' + ($observation -join '; '))
    }
    Write-Output $clear[0]
    Write-Output 'HOST_MXC_D1_EGRESS_OBSERVATION_PASS'
    $done = Wait-Job -Job $job -Timeout 30
    if (-not $done) { throw 'MXC job timed out' }
    $jobOutput = @($job | Receive-Job)
    if ($job.State -ne 'Completed' -or -not ($jobOutput -contains 'MXC_D1_HOLD_COMPLETED')) {
        throw ('MXC hold failed: ' + ($jobOutput -join '; '))
    }
}
finally {
    if ($job.State -eq 'Running') { Stop-Job -Job $job -ErrorAction SilentlyContinue }
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
}
Write-Output 'MXC_D1_EXPERIMENT_PASS_NOT_APPLICATION_ZERO_EGRESS_OR_RELEASE_APPROVAL'
