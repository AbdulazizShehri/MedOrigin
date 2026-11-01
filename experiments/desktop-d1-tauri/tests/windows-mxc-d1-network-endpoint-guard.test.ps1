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
function Tcp([string]$State,[string]$Remote,[string]$Local='127.0.0.1') {
  [pscustomobject]@{State=$State;RemoteAddress=$Remote;LocalAddress=$Local;OwningProcess=42}
}
Assert-MxcD1ObservedEndpoints -Tcp @() -Udp @() -Phase 'empty'
Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Established' '127.0.0.1'),(Tcp 'Established' '::1')) -Udp @() -Phase 'loopback'
Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Listen' '0.0.0.0' '127.0.0.1'),(Tcp 'Bound' '::' '::1')) -Udp @() -Phase 'listeners'
Write-Output 'PASS allow empty, loopback and explicitly local passive TCP'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Listen' '0.0.0.0' '0.0.0.0')) -Udp @() -Phase 'wildcard-listener' } 'IPv4 wildcard listener'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Bound' '::' '::')) -Udp @() -Phase 'wildcard-bound' } 'IPv6 wildcard bound'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Listen' '0.0.0.0' '192.0.2.15')) -Udp @() -Phase 'external-listener' } 'external IPv4 listener'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'Listen' '0.0.0.0' '')) -Udp @() -Phase 'missing-local' } 'missing local listener address'
Assert-Denied { Assert-MxcD1ObservedEndpoints -Tcp @((Tcp 'MysteryState' '127.0.0.1')) -Udp @() -Phase 'unknown-state' } 'unclassified TCP state'
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
# The process tree must remain the same while its owned sockets are read.
# Otherwise a short-lived descendant or PID substitution is invisible to
# the socket snapshot and a PASS cannot be attributed to a stable process.
function Proc([int]$Id,[string]$Ticks,[int]$Parent=1,[string]$Name='msedgewebview2.exe') {
  [pscustomobject]@{pid=$Id;parentPid=$Parent;startTicks=$Ticks;name=$Name;path='C:\\Synthetic\\child.exe'}
}
$before=@((Proc 42 '638000000000000000'),(Proc 43 '638000000000000001' 42))
$after=@((Proc 42 '638000000000000000'),(Proc 43 '638000000000000001' 42))
Assert-MxcD1StableSocketWindow -Before $before -After $after -Tcp @() -Udp @() -Phase 'stable'
Write-Output 'PASS stable process inventory around socket observation'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before $before -After @((Proc 42 '638000000000000000')) -Tcp @() -Udp @() -Phase 'departed' } 'departed child during snapshot'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before @((Proc 42 '638000000000000000')) -After $before -Tcp @() -Udp @() -Phase 'spawned' } 'new child during snapshot'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before $before -After @((Proc 42 '638000000000000000'),(Proc 43 '638000000000000002' 42)) -Tcp @() -Udp @() -Phase 'reuse' } 'PID reuse during snapshot'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before $before -After @((Proc 42 '638000000000000000'),(Proc 43 '638000000000000001' 555)) -Tcp @() -Udp @() -Phase 'parent' } 'changed parent during snapshot'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before @() -After $after -Tcp @() -Udp @() -Phase 'empty' } 'empty pre-snapshot'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before $before -After $after -Tcp @([pscustomobject]@{OwningProcess=900;RemoteAddress='127.0.0.1';State='Established'}) -Udp @() -Phase 'owner' } 'unattributed TCP owner'
Assert-Denied { Assert-MxcD1StableSocketWindow -Before $before -After $after -Tcp @() -Udp @([pscustomobject]@{OwningProcess=900}) -Phase 'ownerudp' } 'unattributed UDP owner'
if($uia -notmatch [regex]::Escape('Assert-MxcD1StableSocketWindow -Before $initial.Inventory -After $postInitial.Inventory')) { throw 'initial socket window lacks post-observation identity check' }
if($uia -notmatch [regex]::Escape('Assert-MxcD1StableSocketWindow -Before $sampled.Inventory -After $postSample.Inventory')) { throw 'sampled socket window lacks post-observation identity check' }
Write-Output 'PASS real UIA source requires post-socket identity census'

Write-Output 'MXC_D1_ENDPOINT_NEGATIVE_SOURCE_TESTS_PASS_NO_PACKET_PROOF'
