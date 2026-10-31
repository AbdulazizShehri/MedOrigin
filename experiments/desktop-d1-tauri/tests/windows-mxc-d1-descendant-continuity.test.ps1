# NONPUBLISHING Windows source-only child-process identity regression.
# Uses actual CIM date types, synthetic process snapshots, no network capture.
$ErrorActionPreference='Stop'
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
$helper=Join-Path $here 'windows-mxc-d1-descendant-continuity.ps1'
$observer=Join-Path $here 'windows-mxc-d1-real-uia-qualification.ps1'
if (-not (Test-Path -LiteralPath $helper)) { throw 'RED: descendant continuity helper absent' }
. (Join-Path $here 'windows-mxc-d1-root-identity.ps1')
. $helper
$me=Get-CimInstance Win32_Process -Filter ("ProcessId="+$PID) -ErrorAction Stop
if (-not $me -or $me.CreationDate -isnot [datetime]) { throw 'Real native Windows CIM date unavailable' }
$start=$me.CreationDate.AddMinutes(-2)
$rootPid=43001
$rootPath='D:\synthetic\medorigin-desktop-d1-preview.exe'
$ticks=[string]$start.ToUniversalTime().Ticks
function P([int]$id,[int]$parent,[string]$name,[datetime]$date,[string]$path='') {
  return [pscustomobject]@{ProcessId=$id;ParentProcessId=$parent;Name=$name;CreationDate=$date;ExecutablePath=$path}
}
$root=P $rootPid 900 'medorigin-desktop-d1-preview.exe' $start $rootPath
$child=P 43002 $rootPid 'msedgewebview2.exe' ($start.AddSeconds(5)) 'C:\WebView\msedgewebview2.exe'
$grandchild=P 43003 43002 'msedgewebview2.exe' ($start.AddSeconds(6)) ''
$unrelated=P 56001 2 'unrelated-process.exe' ($start.AddSeconds(7)) ''
$seen=@{}
$checks=0
function MustThrow([scriptblock]$code) {
  $failed=$false
  try { & $code | Out-Null } catch { $failed=$true }
  if (-not $failed) { throw 'Expected descendant-identity fail-closed refusal' }
  $script:checks++
}
function Valid([object[]]$processes) {
  return Assert-MxcD1ProcessTreeContinuity -Processes $processes -RootPid $rootPid -ExpectedExePath $rootPath -ExpectedStartTicks $ticks -Seen $seen
}
$one=Valid @($root,$child,$grandchild,$unrelated)
if ($one.Ids.Count -ne 3 -or -not $one.Ids.Contains(43003) -or $one.Ids.Contains(56001)) { throw 'Wrong attributed descendant inventory' }
$checks++
$two=Valid @($root,$child,$grandchild)
if ($two.Ids.Count -ne 3 -or $seen.Count -ne 3) { throw 'Stable identities not retained' }
$checks++
MustThrow { Valid @($root,(P 43002 $rootPid 'msedgewebview2.exe' ($start.AddSeconds(8)))) }
MustThrow { Valid @($root,(P 43002 $rootPid 'different.exe' ($start.AddSeconds(5)))) }
MustThrow { Valid @($root,(P 43002 $rootPid 'msedgewebview2.exe' ($start.AddSeconds(5)) 'D:\other\webview.exe')) }
MustThrow { Valid @($root,(P 43002 $rootPid 'msedgewebview2.exe' ($start.AddSeconds(-1)))) }
MustThrow { Valid @($root,(P 43002 $rootPid 'msedgewebview2.exe' ([datetime]::MinValue))) }
MustThrow { Valid @($root,$child,$child) }
MustThrow { Valid @((P $rootPid 900 $root.Name ($start.AddSeconds(1)) $rootPath),$child) }
# Temporarily disappeared PID that reappears with a new creation time is still reused.
$three=Valid @($root)
if ($three.Ids.Count -ne 1) { throw 'Expected disappearing child to be allowed' }
$checks++
MustThrow { Valid @($root,(P 43002 $rootPid $child.Name ($start.AddSeconds(60)) $child.ExecutablePath)) }
# If child metadata is absent, its PID cannot safely be attributed to root.
MustThrow { Valid @($root,[pscustomobject]@{ProcessId=43002;ParentProcessId=$rootPid;Name='msedgewebview2.exe';CreationDate=$null;ExecutablePath=$child.ExecutablePath}) }
$source=Get-Content -LiteralPath $observer -Raw
if ($source -notmatch [regex]::Escape('windows-mxc-d1-descendant-continuity.ps1') -or
    ([regex]::Matches($source,'(?m)^\s*\$\w+=Assert-MxcD1ProcessTreeContinuity\b')).Count -lt 2) {
  throw 'RED: real D1 observer does not preserve descendant identity across snapshot and temporal samples'
}
$checks++
Write-Output "D1_MXC_DESCENDANT_PID_REUSE_FAIL_CLOSED_PASS checks=$checks"
