# Nonpublishing synthetic-only endpoint oracle regression. No network access.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'windows-mxc-d1-network-endpoint-guard.ps1')
function Assert-Denied([scriptblock]$Block,[string]$Case) {
  $denied=$false
  try { & $Block } catch {
    if($_.Exception.Message -notmatch 'D1_MXC_ENDPOINT_NO_GO') { throw }
    $denied=$true
  }
  if(-not $denied) { throw ('D1 endpoint guard erroneously accepted '+$Case) }
  Write-Output ('PASS deny '+$Case)
}
function Tcp([string]$State,[string]$Remote) {
  [pscustomobject]@{State=$State;RemoteAddress=$Remote;OwningProcess=42}
}
Assert-MxcD1ObservedEndpoints -Tcp @() -Udp @() -Phase 'empty'
Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Established' '127.0.0.1'),(Tcp 'Established' '::1')) -Udp @() -Phase 'loopback'
Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Listen' '0.0.0.0'),(Tcp 'Bound' '::')) -Udp @() -Phase 'listeners'
Write-Output 'PASS allow empty, loopback and passive TCP'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Established' '203.0.113.5')) -Udp @() -Phase 'ipv4' } 'external IPv4'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'SynSent' '2001:db8::1')) -Udp @() -Phase 'ipv6' } 'external IPv6'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Established' '0.0.0.0')) -Udp @() -Phase 'wildcard' } 'wildcard active TCP'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Established' '')) -Udp @() -Phase 'blank' } 'unknown TCP remote'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @() -Udp @([pscustomobject]@{LocalAddress='0.0.0.0';OwningProcess=42}) -Phase 'udp' } 'bound UDP'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @($null) -Udp @() -Phase 'null' } 'null TCP record'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @() -Udp @($null) -Phase 'nulludp' } 'null UDP record'
$uia=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'windows-mxc-d1-real-uia-qualification.ps1') -Raw
if($uia -notmatch [regex]::Escape(". (Join-Path `$PSScriptRoot 'windows-mxc-d1-network-endpoint-guard.ps1')")) { throw 'MXC D1 live UIA observer does not dot-source guard' }
if($uia -notmatch [regex]::Escape("Assert-MxcD1ObservedEndpoints -Tcp `$tcp -Udp `$udp -Phase 'initial'")) { throw 'Initial snapshot is not guarded' }
if($uia -notmatch [regex]::Escape("Assert-MxcD1ObservedEndpoints -Tcp `$tcpNow -Udp `$udpNow -Phase ('sample-'+`$sample)")) { throw 'Windowed snapshot is not guarded' }
Write-Output 'PASS source integration both initial and 12 sampling windows'
Write-Output 'MXC_D1_ENDPOINT_NEGATIVE_SOURCE_TESTS_PASS_NO_PACKET_PROOF'
