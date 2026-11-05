# Pure bounded TCP ownership classification functions, synthetic-testable.
# These functions DO NOT claim full packet capture or OS-enforced isolation.
function Get-D1ProcessTree {
    param([Parameter(Mandatory=$true)][object[]]$Processes, [int]$RootPid)
    if ($RootPid -le 0 -or @($Processes | Where-Object { [int]$_.ProcessId -eq $RootPid }).Count -ne 1) {
        throw 'D1_WINDOW_ROOT_ABSENT_OR_AMBIGUOUS'
    }
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    [void]$ids.Add($RootPid)
    # Bounded expansion across a single consistent Win32_Process snapshot.
    for ($round=0; $round -lt $Processes.Count; $round++) {
        $added = 0
        foreach ($proc in $Processes) {
            $pidValue = [int]$proc.ProcessId
            $parentValue = [int]$proc.ParentProcessId
            if ($pidValue -le 0 -or $pidValue -eq $parentValue) { continue }
            if ($ids.Contains($parentValue) -and $ids.Add($pidValue)) { $added++ }
        }
        if ($added -eq 0) { break }
    }
    return ,$ids
}

function Test-D1LoopbackAddress {
    param([string]$Address)
    if ([string]::IsNullOrWhiteSpace($Address)) { return $false }
    $ip = [System.Net.IPAddress]$null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$ip)) { return $false }
    if ([System.Net.IPAddress]::IsLoopback($ip)) { return $true }
    if ($ip.IsIPv4MappedToIPv6) { return [System.Net.IPAddress]::IsLoopback($ip.MapToIPv4()) }
    return $false
}

function Get-D1ExternalTcp {
    param(
        [Parameter(Mandatory=$true)]$TreePids,
        [Parameter(Mandatory=$true)][object[]]$Connections
    )
    $external = [System.Collections.Generic.List[object]]::new()
    foreach ($tcp in $Connections) {
        if (-not $TreePids.Contains([int]$tcp.OwningProcess)) { continue }
        $state = [string]$tcp.State
        if ($state -in @('Listen', 'Bound')) { continue }
        $address = [string]$tcp.RemoteAddress
        if (Test-D1LoopbackAddress $address) { continue }
        # Ambiguous/wildcard/failed parsing also fail closed on non-listener
        # connections; this is NOT a packet capture and misses short-lived flows.
        $external.Add($tcp)
    }
    return $external.ToArray()
}
