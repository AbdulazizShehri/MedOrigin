# Nonpublishing D1 MXC observation boundary. TCP/UDP endpoints are forbidden,
# including loopback, listening, bound and IPv6 endpoints: no silent exceptions.
# This is a sampled endpoint guard, NOT packet capture or proof of WFP enforcement.
function Assert-MxcD1NoOwnedNetworkEndpoints {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][AllowEmptyCollection()][object[]]$Tcp,
        [Parameter(Mandatory=$true)][AllowEmptyCollection()][object[]]$Udp,
        [Parameter(Mandatory=$true)][ValidateSet('initial','sample')][string]$Phase
    )
    if ($null -eq $Tcp -or $null -eq $Udp) {
        throw 'D1_MXC_NETWORK_ENDPOINT_NO_GO: missing TCP or UDP inventory'
    }
    if ($Tcp.Count -ne 0 -or $Udp.Count -ne 0) {
        throw ('D1_MXC_NETWORK_ENDPOINT_NO_GO: phase=' + $Phase + ' owned_tcp=' + $Tcp.Count + ' owned_udp=' + $Udp.Count)
    }
    return $true
}
