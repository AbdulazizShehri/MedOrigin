# Nonpublishing synthetic-only socket snapshot guard. Not a packet capture or
# a proof of OS-enforced network denial. Deliberately rejects any owned UDP
# endpoint, including bindings that do not demonstrate external transmission.
function Assert-MxcD1ObservedEndpoints {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$Tcp,
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$Udp,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Phase
  )
  if($null -eq $Tcp -or $null -eq $Udp) {
    throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' missing socket observation source')
  }
  foreach($endpoint in $Tcp) {
    if($null -eq $endpoint) { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' null TCP record') }
    $state=[string]$endpoint.State
    $remote=[string]$endpoint.RemoteAddress
    $local=[string]$endpoint.LocalAddress
    # Unrecognized TCP states must not bypass the snapshot policy.
    if($state -notin @('Listen','Bound','Established','SynSent','SynReceived',
        'FinWait1','FinWait2','CloseWait','Closing','LastAck','TimeWait',
        'DeleteTcb','Closed')) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' unclassified TCP state')
    }
    # A public/wildcard listener is an inbound exposure, not proof of egress.
    # Fail conservatively unless it is explicitly bound to loopback.
    if($state -in @('Listen','Bound')) {
      if($local -notin @('127.0.0.1','::1')) {
        throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' nonloopback or unknown TCP listener')
      }
      continue
    }
    # An active nonloopback or unclassified connection is not admitted.
    if($remote -notin @('127.0.0.1','::1')) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' nonloopback or unclassified TCP endpoint')
    }
  }
  if($Udp.Count -gt 0) {
    throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' owned UDP endpoint count='+$Udp.Count)
  }
}

# Conservatively reject endpoint snapshots when the descendant process tree
# changes during enumeration. This closes a source-level PID attribution gap,
# but cannot observe processes that start and exit entirely between censuses.
function Assert-MxcD1StableSocketWindow {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$Before,
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$After,
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$Tcp,
    [Parameter(Mandatory=$true)][AllowNull()][AllowEmptyCollection()][object[]]$Udp,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Phase
  )
  if($null -eq $Before -or $null -eq $After -or $Before.Count -eq 0 -or
     $After.Count -eq 0 -or $null -eq $Tcp -or $null -eq $Udp) {
    throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' incomplete before/after census or endpoint data')
  }
  $byPid=@{}
  foreach($proc in $Before) {
    if($null -eq $proc) { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' null pre-snapshot process') }
    try { $id=[int]$proc.pid } catch { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' invalid pre-snapshot PID') }
    if($id -lt 1 -or $byPid.ContainsKey($id) -or
       [string]::IsNullOrWhiteSpace([string]$proc.startTicks) -or
       [string]::IsNullOrWhiteSpace([string]$proc.name)) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' unidentifiable or duplicate pre-snapshot PID')
    }
    $byPid[$id]=$proc
  }
  $afterIds=New-Object 'System.Collections.Generic.HashSet[int]'
  foreach($proc in $After) {
    if($null -eq $proc) { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' null post-snapshot process') }
    try { $id=[int]$proc.pid } catch { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' invalid post-snapshot PID') }
    if(-not $afterIds.Add($id) -or -not $byPid.ContainsKey($id)) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' new or duplicate post-snapshot PID')
    }
    $prior=$byPid[$id]
    if([string]$prior.startTicks -cne [string]$proc.startTicks -or
       [int]$prior.parentPid -ne [int]$proc.parentPid -or
       -not [string]::Equals([string]$prior.name,[string]$proc.name,[StringComparison]::OrdinalIgnoreCase) -or
       -not [string]::Equals([string]$prior.path,[string]$proc.path,[StringComparison]::OrdinalIgnoreCase)) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' process identity changed during socket census')
    }
  }
  if($afterIds.Count -ne $byPid.Count) {
    throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' child exited during socket census')
  }
  foreach($socket in @($Tcp)+@($Udp)) {
    if($null -eq $socket) { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' null socket owner record') }
    try { $id=[int]$socket.OwningProcess } catch { throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' invalid socket owner PID') }
    if($id -lt 1 -or -not $byPid.ContainsKey($id)) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' unattributed socket owner')
    }
  }
}
