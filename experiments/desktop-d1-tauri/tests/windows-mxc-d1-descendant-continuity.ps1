# NONPUBLISHING D1 MXC temporal process-tree attribution.
# No elevated permissions, packet capture, network change or GUI launch.
function Assert-MxcD1ProcessTreeContinuity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][object[]]$Processes,
        [Parameter(Mandatory=$true)][int]$RootPid,
        [Parameter(Mandatory=$true)][string]$ExpectedExePath,
        [Parameter(Mandatory=$true)][string]$ExpectedStartTicks,
        [Parameter(Mandatory=$true)][hashtable]$Seen
    )
    if ($RootPid -lt 1 -or $Processes.Count -eq 0) {
        throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: empty process snapshot'
    }
    # A snapshot with duplicate PID entries cannot identify which instance
    # owns socket endpoints. Refuse rather than choose first.
    $byPid=@{}
    foreach ($proc in $Processes) {
        if ($null -eq $proc -or $null -eq $proc.ProcessId) { continue }
        $id=[int]$proc.ProcessId
        if ($id -lt 1) { continue }
        if ($byPid.ContainsKey($id)) { throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: ambiguous duplicate PID' }
        $byPid[$id]=$proc
    }
    if (-not $byPid.ContainsKey($RootPid)) {
        throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: missing root process'
    }
    Assert-MxcD1RootIdentity -Process $byPid[$RootPid] -ExpectedPid $RootPid -ExpectedExePath $ExpectedExePath -ExpectedStartTicks $ExpectedStartTicks | Out-Null

    $ids=New-Object 'System.Collections.Generic.HashSet[int]'
    [void]$ids.Add($RootPid)
    for ($depth=0; $depth -lt 16; $depth++) {
        $added=$false
        foreach ($proc in $byPid.Values) {
            $id=[int]$proc.ProcessId
            $parent=[int]$proc.ParentProcessId
            if ($id -ne $RootPid -and $parent -gt 0 -and $id -ne $parent -and
                $ids.Contains($parent) -and $ids.Add($id)) {
                $added=$true
            }
        }
        if (-not $added) { break }
    }
    # PID reuse can also create parent chains longer than the cap; never
    # silently omit a connected child and claim clean network observation.
    foreach ($proc in $byPid.Values) {
        $id=[int]$proc.ProcessId
        $parent=[int]$proc.ParentProcessId
        if ($id -ne $RootPid -and $ids.Contains($parent) -and -not $ids.Contains($id)) {
            throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: descendant depth limit'
        }
    }

    $next=@{}
    foreach ($id in $ids) {
        $proc=$byPid[$id]
        if ($proc.CreationDate -isnot [datetime] -or
            [string]::IsNullOrWhiteSpace([string]$proc.Name)) {
            throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: unidentifiable process timestamp/name'
        }
        $parent=[int]$proc.ParentProcessId
        $ticks=[string]$proc.CreationDate.ToUniversalTime().Ticks
        if ($ticks -notmatch '^\d{15,20}$') {
            throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: invalid process creation time'
        }
        if ($id -ne $RootPid) {
            if (-not $ids.Contains($parent)) {
                throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: missing parent process'
            }
            $parentTicks=$byPid[$parent].CreationDate
            if ($parentTicks -isnot [datetime] -or
                $parentTicks.ToUniversalTime().Ticks -gt $proc.CreationDate.ToUniversalTime().Ticks) {
                throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: child predates recorded parent'
            }
        }
        $path=[string]$proc.ExecutablePath
        $identity=[pscustomobject]@{
            pid=[int]$id; parentPid=$parent
            startTicks=$ticks; name=[string]$proc.Name; path=$path
        }
        if ($Seen.ContainsKey([int]$id)) {
            $prior=$Seen[[int]$id]
            if ([string]$prior.startTicks -cne $ticks -or
                [int]$prior.parentPid -ne $parent -or
                -not [string]::Equals([string]$prior.name,[string]$proc.Name,
                    [System.StringComparison]::OrdinalIgnoreCase) -or
                (-not [string]::IsNullOrEmpty([string]$prior.path) -and
                 -not [string]::IsNullOrEmpty($path) -and
                 -not [string]::Equals([string]$prior.path,$path,
                    [System.StringComparison]::OrdinalIgnoreCase))) {
                throw 'D1_MXC_DESCENDANT_IDENTITY_NO_GO: PID reused or process identity changed'
            }
            # Preserve a previously known path when Windows CIM temporarily
            # withholds the path from a low-integrity WebView2 subprocess.
            if ([string]::IsNullOrEmpty($path)) { $identity.path=[string]$prior.path }
        }
        $next[[int]$id]=$identity
    }
    # Commit history only after the whole snapshot is qualified. Deliberately
    # keep departed PIDs in history so a later reappearance cannot reuse them.
    foreach ($key in $next.Keys) { $Seen[$key]=$next[$key] }
    $inventory=@($next.Values | Sort-Object pid)
    return [pscustomobject]@{Ids=$ids;Inventory=$inventory}
}
