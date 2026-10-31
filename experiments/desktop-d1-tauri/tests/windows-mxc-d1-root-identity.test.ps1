# Synthetic-only, nonpublishing regression for D1 MXC root PID reuse.
# Tests actual Windows CIM CreationDate conversion and strict source integration.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$helper = Join-Path $here 'windows-mxc-d1-root-identity.ps1'
$uia = Join-Path $here 'windows-mxc-d1-real-uia-qualification.ps1'
if (-not (Test-Path -LiteralPath $helper)) { throw 'RED: root identity helper absent' }
. $helper
$checks = 0
function MustPass([scriptblock]$body) {
    & $body
    $script:checks++
}
function MustThrow([scriptblock]$body) {
    $threw = $false
    try { & $body | Out-Null } catch { $threw = $true }
    if (-not $threw) { throw 'Expected root-identity fail-closed exception' }
    $script:checks++
}
$me = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $PID) -ErrorAction Stop
if (-not $me -or -not $me.CreationDate) { throw 'Real Windows CIM CreationDate unavailable' }
$root = [pscustomobject]@{
    ProcessId = 43521
    ExecutablePath = 'D:\synthetic\medorigin-desktop-d1-preview.exe'
    CreationDate = $me.CreationDate
    Name = 'medorigin-desktop-d1-preview.exe'
}
$ticks = [string]$me.CreationDate.ToUniversalTime().Ticks
MustPass { if (-not (Assert-MxcD1RootIdentity -Process $root -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks $ticks)) { throw 'valid root rejected' } }
MustThrow { Assert-MxcD1RootIdentity -Process $root -ExpectedPid 43522 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks $ticks }
MustThrow { Assert-MxcD1RootIdentity -Process $root -ExpectedPid 43521 -ExpectedExePath 'D:\other\medorigin-desktop-d1-preview.exe' -ExpectedStartTicks $ticks }
MustThrow { Assert-MxcD1RootIdentity -Process $root -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks ([string]([long]$ticks+1)) }
MustThrow { Assert-MxcD1RootIdentity -Process ([pscustomobject]@{ProcessId=43521;ExecutablePath=$root.ExecutablePath;CreationDate=$null;Name=$root.Name}) -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks $ticks }
MustThrow { Assert-MxcD1RootIdentity -Process ([pscustomobject]@{ProcessId=43521;ExecutablePath=$root.ExecutablePath;CreationDate=$me.CreationDate;Name='not-d1.exe'}) -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks $ticks }
MustThrow { Assert-MxcD1RootIdentity -Process $null -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks $ticks }
MustThrow { Assert-MxcD1RootIdentity -Process $root -ExpectedPid 43521 -ExpectedExePath $root.ExecutablePath -ExpectedStartTicks 'bad' }
$source = Get-Content -LiteralPath $uia -Raw
$uses = [regex]::Matches($source, '(?m)^\s*Assert-MxcD1RootIdentity\b').Count
$treeUses = [regex]::Matches($source, '(?m)^\s*\$\w+=Assert-MxcD1ProcessTreeContinuity\b').Count
$treeHelper=Join-Path $here 'windows-mxc-d1-descendant-continuity.ps1'
$treeSource=if(Test-Path -LiteralPath $treeHelper){Get-Content -LiteralPath $treeHelper -Raw}else{''}
$delegated = ($treeUses -ge 2 -and
    $source -match [regex]::Escape('windows-mxc-d1-descendant-continuity.ps1') -and
    $treeSource -match '(?m)^\s*Assert-MxcD1RootIdentity\b')
if (($uses -lt 2 -and -not $delegated) -or
    $source -notmatch [regex]::Escape('windows-mxc-d1-root-identity.ps1')) {
    throw 'RED: root creation identity not checked by both UIA sampling call sites'
}
$checks++
Write-Output "D1_MXC_ROOT_PID_REUSE_FAIL_CLOSED_SYNTHETIC_PASS checks=$checks"
