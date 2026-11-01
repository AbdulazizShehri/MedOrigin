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
    # Listener/bound TCP sockets are not evidence of an outbound connection.
    if($state -in @('Listen','Bound')) { continue }
    # Fail closed on missing, wildcard, IPv4/IPv6 external, or ambiguous address.
    if($remote -notin @('127.0.0.1','::1')) {
      throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' nonloopback or unclassified TCP endpoint')
    }
  }
  if($Udp.Count -gt 0) {
    throw ('D1_MXC_ENDPOINT_NO_GO '+$Phase+' owned UDP endpoint count='+$Udp.Count)
  }
}
