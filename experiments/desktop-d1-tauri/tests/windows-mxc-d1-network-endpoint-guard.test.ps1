# Synthetic-only regression for the D1 MXC network endpoint fail-closed boundary.
# No native MXC, GUI, sockets or network traffic are created by this test.
$ErrorActionPreference = 'Stop'
$guard = Join-Path $PSScriptRoot 'windows-mxc-d1-network-endpoint-guard.ps1'
if (-not (Test-Path -LiteralPath $guard -PathType Leaf)) {
    throw 'RED: D1 MXC owned TCP/UDP endpoint guard is missing'
}
. $guard
$passed = 0
function Expect-Reject([string]$label, [object[]]$tcp, [object[]]$udp) {
    $rejected = $false
    try { Assert-MxcD1NoOwnedNetworkEndpoints -Tcp $tcp -Udp $udp -Phase sample | Out-Null }
    catch { $rejected = $_.Exception.Message -like '*D1_MXC_NETWORK_ENDPOINT_NO_GO*' }
    if (-not $rejected) { throw ('RED: unexpected green endpoint fixture ' + $label) }
    $script:passed++
}
Assert-MxcD1NoOwnedNetworkEndpoints -Tcp @() -Udp @() -Phase initial | Out-Null
$passed++
Expect-Reject 'IPv4 loopback TCP' @([pscustomobject]@{OwningProcess=100;RemoteAddress='127.0.0.1';State='Established'}) @()
Expect-Reject 'IPv6 loopback TCP' @([pscustomobject]@{OwningProcess=100;RemoteAddress='::1';State='SynSent'}) @()
Expect-Reject 'external IPv4 TCP' @([pscustomobject]@{OwningProcess=100;RemoteAddress='198.51.100.7';State='SynSent'}) @()
Expect-Reject 'TCP listener' @([pscustomobject]@{OwningProcess=100;RemoteAddress='0.0.0.0';State='Listen'}) @()
Expect-Reject 'IPv4 UDP bind' @() @([pscustomobject]@{OwningProcess=100;LocalAddress='0.0.0.0'})
Expect-Reject 'IPv6 UDP bind' @() @([pscustomobject]@{OwningProcess=100;LocalAddress='::'})
Expect-Reject 'mixed TCP/UDP' @([pscustomobject]@{OwningProcess=100;RemoteAddress='::1'}) @([pscustomobject]@{OwningProcess=100;LocalAddress='::'})
$observer = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'windows-mxc-d1-real-uia-qualification.ps1') -Raw
foreach ($required in @(
    'Assert-MxcD1NoOwnedNetworkEndpoints -Tcp $tcp -Udp $udp -Phase initial',
    'Assert-MxcD1NoOwnedNetworkEndpoints -Tcp $tcpNow -Udp $udpNow -Phase sample'
)) {
    if (-not $observer.Contains($required)) { throw ('RED: actual D1 observer does not enforce ' + $required) }
    $passed++
}
Write-Output ('D1_MXC_OWNED_ENDPOINT_FAIL_CLOSED_MOCK_PASS=' + $passed + '_OF_10_SOURCE_ONLY')
