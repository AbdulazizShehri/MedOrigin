# Time-windowed D1 TCP observation; NOT an OS-deny or no-egress attestation.
# Requires a pre-launched task-owned D1 process and its exact binary SHA.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$RootPid,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedExeSha256,
    [ValidateRange(1,120)][int]$DurationSeconds = 10,
    [ValidateRange(100,1000)][int]$IntervalMilliseconds = 250
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'windows-egress-window-functions.ps1')
function Stop-NoGo([string]$Reason, [int]$Code=1) {
    [Console]::Error.WriteLine("D1_EGRESS_WINDOW_NO_GO: $Reason")
    exit $Code
}
$rootExe = $null; $started = $null
try {
    $root=Get-Process -Id $RootPid -ErrorAction Stop
    $rootExe=$root.Path
    if ($root.ProcessName -ne 'medorigin-desktop-d1-preview' -or
        [string]::IsNullOrWhiteSpace($rootExe) -or
        -not (Test-Path -LiteralPath $rootExe -PathType Leaf)) {
        Stop-NoGo 'D1 source-bound process path unavailable or wrong native identity'
    }
    if ((Get-FileHash -LiteralPath $rootExe -Algorithm SHA256).Hash -ine $ExpectedExeSha256) {
        Stop-NoGo 'executable bytes do not match supplied source-bound SHA'
    }
    $started=$root.StartTime.ToUniversalTime().Ticks
} catch { Stop-NoGo "initial process identity could not be verified: $($_.Exception.Message)" }
$clock=[System.Diagnostics.Stopwatch]::StartNew()
$samples=0; $maxTree=0; $udpMax=0; $externalCount=0
while ($clock.Elapsed.TotalSeconds -lt $DurationSeconds -or $samples -eq 0) {
    try {
        # Check root lifetime and process identity BEFORE every sample. A PID
        # reused after process exit must never be mistaken for the authorized app.
        $current=Get-Process -Id $RootPid -ErrorAction Stop
        if ($current.StartTime.ToUniversalTime().Ticks -ne $started -or
            $current.Path -ne $rootExe) { Stop-NoGo 'root PID reused or executable changed' }
        $rows=@(Get-CimInstance Win32_Process -ErrorAction Stop)
        $tree=Get-D1ProcessTree -Processes $rows -RootPid $RootPid
        $tcp=@(Get-NetTCPConnection -ErrorAction Stop)
        $udp=@(Get-NetUDPEndpoint -ErrorAction Stop)
        $disallowed=@(Get-D1ExternalTcp -TreePids $tree -Connections $tcp)
        $samples++
        $maxTree=[math]::Max($maxTree,$tree.Count)
        $udpMax=[math]::Max($udpMax,@($udp|Where-Object { $tree.Contains([int]$_.OwningProcess) }).Count)
        if ($disallowed.Count -gt 0) {
            $externalCount += $disallowed.Count
            foreach ($entry in $disallowed | Select-Object -First 12) {
                Write-Output "D1_OBSERVED_DISALLOWED_TCP sample=$samples pid=$($entry.OwningProcess) state=$($entry.State) remote=$($entry.RemoteAddress):$($entry.RemotePort)"
            }
            Stop-NoGo "observed external/ambiguous TCP during bounded window; sample=$samples count=$($disallowed.Count)" 2
        }
    } catch {
        Stop-NoGo "process/TCP/UDP sample failed closed: $($_.Exception.Message)"
    }
    if ($clock.Elapsed.TotalSeconds -lt $DurationSeconds) {
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
}
Write-Output "D1_EGRESS_WINDOW_SAMPLED_NO_OBSERVED_TCP samples=$samples max_tree=$maxTree max_udp_endpoints=$udpMax elapsed_sec=$([math]::Round($clock.Elapsed.TotalSeconds,2))"
Write-Output "D1_NETWORK_ISOLATION_STILL_NO_GO: polling cannot rule out DNS/UDP payloads, ephemeral TCP between samples, brokers or services; OS-enforced denial + packet/equivalent evidence required."
exit 0
