# Source-only, non-elevated Windows network observation for a pinned executable.
# NEVER evidence of OS-enforced isolation, packet-level denial, DNS coverage, or release.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$RootPid,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ExpectedExecutableName,
    [ValidateRange(1,30)][int]$Samples=3,
    [ValidateRange(100,5000)][int]$IntervalMs=400
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Emit-NoGo([string]$reason, [array]$observations, [int]$exitCode) {
    [pscustomobject]@{
        schema='medorigin-d2-windows-socket-observation-v1'
        decision='NO_GO'
        reason=$reason
        root_pid=$RootPid
        executable_sha256_expected=$ExpectedSha256.ToLowerInvariant()
        observations=$observations
        os_packet_enforcement_proven=$false
        dns_and_udp_egress_covered=$false
        release_authorized=$false
    } | ConvertTo-Json -Depth 7 -Compress
    exit $exitCode
}

# Check exact process identity and file digest before observing anything.
try {
    $initial=@(Get-CimInstance Win32_Process -ErrorAction Stop)
    $root=@($initial | Where-Object { [int]$_.ProcessId -eq $RootPid })
    if ($root.Count -ne 1) { Emit-NoGo 'ROOT_MISSING_OR_AMBIGUOUS' @() 4 }
    $path=[string]$root[0].ExecutablePath
    if ([string]::IsNullOrWhiteSpace($path)) { Emit-NoGo 'ROOT_EXECUTABLE_PATH_UNAVAILABLE' @() 4 }
    if ([IO.Path]::GetFileName($path) -cne $ExpectedExecutableName) {
        Emit-NoGo 'EXECUTABLE_NAME_MISMATCH' @() 4
    }
    $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash
    if ($actual -ine $ExpectedSha256) { Emit-NoGo 'EXECUTABLE_DIGEST_MISMATCH' @() 4 }
    $rootCreation=[string]$root[0].CreationDate
    $observations=@()
    $anyExternalTcp=$false
    $anyUdpEndpoint=$false

    for ($i=0; $i -lt $Samples; $i++) {
        $processes=@(Get-CimInstance Win32_Process -ErrorAction Stop)
        $current=@($processes | Where-Object { [int]$_.ProcessId -eq $RootPid })
        if ($current.Count -ne 1 -or [string]$current[0].CreationDate -ne $rootCreation) {
            Emit-NoGo 'ROOT_EXITED_OR_PID_REUSED' $observations 4
        }
        $ids=[System.Collections.Generic.HashSet[int]]::new()
        [void]$ids.Add($RootPid)
        # Newly created children that have already exited are not observable.
        do {
            $changed=$false
            foreach ($p in $processes) {
                $pidValue=[int]$p.ProcessId
                if ($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains($pidValue)) {
                    [void]$ids.Add($pidValue)
                    $changed=$true
                }
            }
        } while ($changed)

        $tcp=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {
            $ids.Contains([int]$_.OwningProcess) -and
            $_.State -notin @('Listen','Bound','Closed','DeleteTCB') -and
            $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::')
        })
        $udp=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {
            $ids.Contains([int]$_.OwningProcess)
        })
        $anyExternalTcp = $anyExternalTcp -or ($tcp.Count -gt 0)
        $anyUdpEndpoint = $anyUdpEndpoint -or ($udp.Count -gt 0)
        $observations+= [pscustomobject]@{
            sample=$i
            timestamp_utc=(Get-Date).ToUniversalTime().ToString('o')
            visible_process_count=$ids.Count
            nonloopback_tcp_connections=$tcp.Count
            udp_endpoint_count=$udp.Count
        }
        if ($i -lt ($Samples-1)) { Start-Sleep -Milliseconds $IntervalMs }
    }
    if ($anyExternalTcp -or $anyUdpEndpoint) {
        Emit-NoGo 'SOCKET_ACTIVITY_OBSERVED_NOT_OFFLINE_QUALIFIED' $observations 2
    }
    Emit-NoGo 'NO_SOCKET_OBSERVED_BUT_PACKET_AND_DNS_EGRESS_UNVERIFIED' $observations 3
} catch {
    # Don't print native exception values (which could include sensitive paths).
    Emit-NoGo 'OBSERVATION_ERROR_OR_INSUFFICIENT_PRIVILEGE' @() 4
}
