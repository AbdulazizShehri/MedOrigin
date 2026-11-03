# Synthetic in-process command mocks, with exact on-disk name/hash fixture.
# No Windows/Edge executable launch, packets or firewall changes.
$ErrorActionPreference='Stop'
$probe=Join-Path $PSScriptRoot 'windows-attributed-egress-preflight.ps1'
if(-not (Test-Path -LiteralPath $probe -PathType Leaf)){throw 'PROBE_NOT_FOUND'}
$work=Join-Path $env:TEMP ('medorigin-d1-pin-qa-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
  # SHA is genuine, but the fixture bytes are inert and NEVER executed.
  $exe=Join-Path $work 'medorigin-desktop-d1-preview.exe'
  [IO.File]::WriteAllText($exe,'inert synthetic fixture; not a Windows executable')
  $sha=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  $tests=@(
    @{name='no-sockets';code=3;reason='NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN'},
    @{name='unrelated-tcp';code=3;reason='NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN'},
    @{name='child-synsent';code=2;reason='D1_OBSERVED_EXTERNAL_TCP_NO_GO'},
    @{name='grandchild-established';code=2;reason='D1_OBSERVED_EXTERNAL_TCP_NO_GO'},
    @{name='wrong-root-image';code=4;reason='D1_ROOT_IMAGE_PATH_MISMATCH'},
    @{name='pid-reused';code=4;reason='D1_ROOT_IDENTITY_CHANGED_DURING_OBSERVATION'},
    @{name='descendant-pid-reused';code=4;reason='D1_DESCENDANT_IDENTITY_UNSTABLE_DURING_OBSERVATION'},
    @{name='root-missing';code=4;reason='D1_ROOT_ABSENT_OR_AMBIGUOUS'},
    @{name='birth-missing';code=4;reason='D1_ROOT_IMAGE_OR_BIRTH_UNREADABLE'},
    @{name='cim-error';code=4;reason='D1_OBSERVATION_ERROR'},
    @{name='tcp-error';code=4;reason='D1_OBSERVATION_ERROR'},
    @{name='udp-error';code=4;reason='D1_OBSERVATION_ERROR'},
    @{name='wrong-sha';code=4;reason='D1_EXECUTABLE_SHA256_MISMATCH'},
    @{name='binary-replaced';code=4;reason='D1_EXECUTABLE_HASH_CHANGED_DURING_OBSERVATION'}
  )
  foreach($case in $tests){
    $harness=Join-Path $work ($case.name+'.ps1')
    $source=@'
$ErrorActionPreference='Stop'
$script:cimReads=0
function Get-CimInstance {
 [CmdletBinding()]param([string]$ClassName)
 if('__CASE__' -eq 'cim-error'){throw 'MOCK_CIM_UNREADABLE'}
 $script:cimReads++
 if('__CASE__' -ne 'root-missing'){
  $birth='2026-11-03T00:00:00Z'
  if('__CASE__' -eq 'pid-reused' -and $script:cimReads -gt 1){$birth='2026-11-03T00:01:00Z'}
  if('__CASE__' -eq 'birth-missing'){$birth=$null}
  $img='__EXE__'
  if('__CASE__' -eq 'wrong-root-image'){$img='C:\Windows\System32\not-medorigin.exe'}
  [pscustomobject]@{ProcessId=12345;ParentProcessId=0;CreationDate=$birth;ExecutablePath=$img}
 }
 $childBirth='2026-11-03T00:00:00Z'
 if('__CASE__' -eq 'descendant-pid-reused' -and $script:cimReads -gt 1){$childBirth='2026-11-03T00:02:00Z'}
 [pscustomobject]@{ProcessId=23456;ParentProcessId=12345;CreationDate=$childBirth;ExecutablePath='C:\Program Files\WebView2\msedgewebview2.exe'}
 [pscustomobject]@{ProcessId=34567;ParentProcessId=23456;CreationDate='2026-11-03T00:00:00Z';ExecutablePath='C:\Program Files\WebView2\msedgewebview2.exe'}
 [pscustomobject]@{ProcessId=99999;ParentProcessId=0;CreationDate='2026-11-03T00:00:00Z';ExecutablePath='C:\Other\app.exe'}
}
function Get-NetTCPConnection {
 [CmdletBinding()]param()
 if('__CASE__' -eq 'tcp-error'){throw 'MOCK_TCP_UNREADABLE'}
 if('__CASE__' -eq 'binary-replaced'){
   [IO.File]::AppendAllText('__EXE__', 'synthetic tamper during socket query')
 }
 if('__CASE__' -eq 'unrelated-tcp'){
   [pscustomobject]@{OwningProcess=99999;RemoteAddress='2001:db8::b';RemotePort=443;State='Established'}
 }
 if('__CASE__' -eq 'child-synsent'){
   [pscustomobject]@{OwningProcess=23456;RemoteAddress='2001:db8::a';RemotePort=443;State='SynSent'}
 }
 if('__CASE__' -eq 'grandchild-established'){
   [pscustomobject]@{OwningProcess=34567;RemoteAddress='192.0.2.7';RemotePort=443;State='Established'}
 }
}
function Get-NetUDPEndpoint {
 [CmdletBinding()]param()
 if('__CASE__' -eq 'udp-error'){throw 'MOCK_UDP_UNREADABLE'}
}
& '__PROBE__' -RootPid 12345 -ExpectedRootExecutable '__EXE__' -ExpectedSha256 '__SHA__'
exit $LASTEXITCODE
'@
    $pinned=$sha
    if($case.name -eq 'wrong-sha'){$pinned='0'*64}
    $source=$source.Replace('__CASE__',$case.name).Replace('__EXE__',$exe.Replace("'","''")).Replace('__SHA__',$pinned).Replace('__PROBE__',$probe.Replace("'","''"))
    [IO.File]::WriteAllText($harness,$source,[Text.UTF8Encoding]::new($false))
    $out=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $harness 2>&1
    $code=$LASTEXITCODE
    if($code -ne $case.code) {throw ('CASE_EXIT_MISMATCH '+$case.name+' actual='+$code+' output='+($out|Out-String))}
    $json=($out | Out-String | ConvertFrom-Json -ErrorAction Stop)
    if($json.decision -ne 'NO_GO' -or $json.reason -ne $case.reason -or
       $json.release_authorized -ne $false -or
       $json.os_packet_egress_denial_proven -ne $false -or
       $json.dns_udp_egress_denial_proven -ne $false -or
       $json.host_policy_modified -ne $false){
      throw ('CASE_FALSE_ATTESTATION '+$case.name+' '+($out|Out-String))
    }
    Write-Output ('D1_PINNED_ATTRIBUTION_MOCK_PASS '+$case.name+' code='+$code)
  }
}
finally { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
Write-Output 'D1_PINNED_ATTRIBUTION_14_OF_14_MOCK_PASS_NO_RELEASE'
