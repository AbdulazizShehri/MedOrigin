# MedOrigin desktop - read-only, exact-binary Windows process-tree TCP witness.
# This script NEVER grants zero-egress qualification, even if it sees zero sockets.
# No firewall, WFP, network policy, service, registry, user profile, or app mutation.
# See Microsoft Win32_Process CreationDate/PID-reuse warnings and NetTCPIP docs.
[CmdletBinding()]
param(
  [string]$ExecutablePath,
  [string]$ExpectedSha256,
  [string]$ReportPath,
  [ValidateRange(8,120)][int]$SamplingSeconds = 45,
  [ValidateRange(250,5000)][int]$IntervalMs = 1000,
  [switch]$SelfTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-ProcessIdentityTime {
  param([object]$Process)
  $time = [datetime]$Process.CreationDate
  if ($time.Kind -eq [DateTimeKind]::Unspecified) {
    return $time
  }
  return $time.ToUniversalTime()
}

function Get-TrackedProcessTree {
  param([object[]]$Processes, [int]$RootPid, [datetime]$RootCreationDate)
  $indexed = @{}
  foreach ($process in $Processes) {
    $indexed[[int]$process.ProcessId] = $process
  }
  $root = $indexed[$RootPid]
  if ($null -eq $root -or (Get-ProcessIdentityTime $root) -ne $RootCreationDate) {
    throw 'root_identity_mismatch_or_gone'
  }

  $ids = [System.Collections.Generic.HashSet[int]]::new()
  [void]$ids.Add($RootPid)
  $pending = [System.Collections.Generic.Queue[int]]::new()
  $pending.Enqueue($RootPid)
  $unsafeParents = 0
  while ($pending.Count -gt 0) {
    $parentId = $pending.Dequeue()
    $parent = $indexed[$parentId]
    if ($null -eq $parent) { continue }
    $parentTime = Get-ProcessIdentityTime $parent
    foreach ($child in $Processes) {
      $childId = [int]$child.ProcessId
      if ([int]$child.ParentProcessId -ne $parentId -or $ids.Contains($childId)) {
        continue
      }
      # A newly recycled parent PID can otherwise graft unrelated processes
      # into this observed tree. Err toward undercount/incomplete, never PASS.
      if ((Get-ProcessIdentityTime $child) -lt $parentTime) {
        $unsafeParents++
        continue
      }
      [void]$ids.Add($childId)
      $pending.Enqueue($childId)
    }
  }
  return [pscustomobject]@{
    Ids = $ids
    Processes = @($Processes | Where-Object { $ids.Contains([int]$_.ProcessId) } |
        ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId; parent=[int]$_.ParentProcessId; name=[string]$_.Name} })
    ParentReuseSuspicions = $unsafeParents
  }
}

function Test-NonLoopbackRemote {
  param([string]$RemoteAddress, [int]$RemotePort)
  if ($RemotePort -lt 1 -or [string]::IsNullOrWhiteSpace($RemoteAddress)) { return $false }
  $addr = [net.ipaddress]::None
  if (-not [net.ipaddress]::TryParse($RemoteAddress, [ref]$addr)) {
    # Unknown nonempty hostname/address is conservatively treated as external.
    return $true
  }
  if ($addr.IsIPv4MappedToIPv6) {
    return -not [net.ipaddress]::IsLoopback($addr.MapToIPv4())
  }
  return -not [net.ipaddress]::IsLoopback($addr)
}

function Get-RemoteFamily {
  param([string]$RemoteAddress)
  $addr = [net.ipaddress]::None
  if ([net.ipaddress]::TryParse($RemoteAddress, [ref]$addr)) {
    if ($addr.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetworkV6) { return 'IPv6' }
    return 'IPv4'
  }
  return 'unknown'
}

function Get-WitnessDisposition {
  param([int]$ExternalTcpCount, [string]$ProbeFailure, [int]$ParentReuseSuspicions, [bool]$RootIdentityLost)
  if ($ExternalTcpCount -gt 0) { return 'OBSERVED_EXTERNAL_TCP_NO_GO' }
  if (-not [string]::IsNullOrWhiteSpace($ProbeFailure) -or
      $ParentReuseSuspicions -gt 0 -or $RootIdentityLost) {
    return 'INCOMPLETE_NO_GO'
  }
  return 'UNQUALIFIED_SNAPSHOT_ONLY_NO_GO'
}

function Assert-SyntheticProbeTests {
  function Assert([bool]$check,[string]$message) {
    if (-not $check) { throw ('selftest_failed:' + $message) }
  }
  $date = [datetime]::SpecifyKind([datetime]'2026-11-04T00:00:00', [DateTimeKind]::Utc)
  $list = @(
    [pscustomobject]@{ ProcessId=100; ParentProcessId=1; CreationDate=$date; Name='synthetic-host.exe' },
    [pscustomobject]@{ ProcessId=101; ParentProcessId=100; CreationDate=$date.AddSeconds(2); Name='msedgewebview2.exe' },
    [pscustomobject]@{ ProcessId=102; ParentProcessId=101; CreationDate=$date.AddSeconds(3); Name='msedgewebview2.exe' },
    [pscustomobject]@{ ProcessId=103; ParentProcessId=100; CreationDate=$date.AddSeconds(-1); Name='recycled-process.exe' },
    [pscustomobject]@{ ProcessId=104; ParentProcessId=9; CreationDate=$date; Name='unrelated.exe' }
  )
  $tree = Get-TrackedProcessTree $list 100 $date
  Assert ($tree.Ids.Count -eq 3) 'expected three descendants including root'
  Assert ($tree.Ids.Contains(102)) 'missed nested descendant'
  Assert (-not $tree.Ids.Contains(103)) 'PID reuse not excluded'
  Assert (-not $tree.Ids.Contains(104)) 'included unrelated process'
  Assert ($tree.ParentReuseSuspicions -eq 1) 'missing reuse flag'
  $identityRefused = $false
  try { $null = Get-TrackedProcessTree $list 100 $date.AddSeconds(1) } catch { $identityRefused = $true }
  Assert $identityRefused 'reused root accepted'
  foreach ($local in @('127.0.0.1','127.99.22.11','::1','::ffff:127.0.0.1')) {
    Assert (-not (Test-NonLoopbackRemote $local 443)) ('misclassified loopback '+$local)
  }
  foreach ($remote in @('1.1.1.1','192.168.1.9','2603:1046:c0c:c0c::2','fe80::3')) {
    Assert (Test-NonLoopbackRemote $remote 443) ('missed remote '+$remote)
  }
  Assert (-not (Test-NonLoopbackRemote '8.8.8.8' 0)) 'listening socket counted'
  Assert ((Get-RemoteFamily '2001:db8::1') -eq 'IPv6') 'IPv6 classification'
  Assert ((Get-RemoteFamily '192.0.2.1') -eq 'IPv4') 'IPv4 classification'
  Assert ((Get-WitnessDisposition 2 $null 0 $false) -eq 'OBSERVED_EXTERNAL_TCP_NO_GO') 'positive TCP must be NO-GO'
  Assert ((Get-WitnessDisposition 0 'probe_failure' 0 $false) -eq 'INCOMPLETE_NO_GO') 'measurement error must be NO-GO'
  Assert ((Get-WitnessDisposition 0 $null 1 $false) -eq 'INCOMPLETE_NO_GO') 'PID reuse must be NO-GO'
  Assert ((Get-WitnessDisposition 0 $null 0 $true) -eq 'INCOMPLETE_NO_GO') 'lost root must be NO-GO'
  Assert ((Get-WitnessDisposition 0 $null 0 $false) -eq 'UNQUALIFIED_SNAPSHOT_ONLY_NO_GO') 'zero sampled TCP is NOT a security PASS'
  Write-Output 'WITNESS_SELFTEST_PASS process ancestry, root identity, PID reuse, IPv4/IPv6/loopback'
}

if ($SelfTest) {
  Assert-SyntheticProbeTests
  exit 0
}

if ([string]::IsNullOrWhiteSpace($ExecutablePath) -or
    [string]::IsNullOrWhiteSpace($ExpectedSha256) -or
    [string]::IsNullOrWhiteSpace($ReportPath)) {
  throw 'ExecutablePath, ExpectedSha256 and ReportPath are required for native observation'
}
if ($ExpectedSha256 -notmatch '^[0-9a-fA-F]{64}$') {
  throw 'invalid_expected_sha256'
}
if (Test-Path -LiteralPath $ReportPath) {
  throw 'Refusing to overwrite prior egress evidence'
}
$resolved = (Resolve-Path -LiteralPath $ExecutablePath -ErrorAction Stop).Path
if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne '.exe') {
  throw 'expected_exact_windows_executable'
}
$actualHash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256 -ErrorAction Stop).Hash
if ($actualHash -ne $ExpectedSha256.ToUpperInvariant()) {
  throw 'executable_sha256_mismatch_refuse_launch'
}

$rootProcess = $null
$samples = [System.Collections.Generic.List[object]]::new()
$observed = [System.Collections.Generic.List[object]]::new()
$observedUdp = 0
$failure = $null
$rootGone = $false
$parentReuses = 0
$rootIdentityDate = $null
try {
  $rootProcess = Start-Process -FilePath $resolved -PassThru -ErrorAction Stop
  $root = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $rootProcess.Id) -ErrorAction Stop
  if ($null -eq $root) { throw 'native_process_identity_missing_at_start' }
  $rootIdentityDate = Get-ProcessIdentityTime $root
  $stopAt = [datetime]::UtcNow.AddSeconds($SamplingSeconds)
  $index = 0
  do {
    $index++
    # One live process snapshot per iteration, not a stale ever-growing PID set.
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $tree = Get-TrackedProcessTree $processes $rootProcess.Id $rootIdentityDate
    $parentReuses += $tree.ParentReuseSuspicions

    $tcpRaw = @(Get-NetTCPConnection -ErrorAction Stop)
    $udpRaw = @(Get-NetUDPEndpoint -ErrorAction Stop)
    $tcp = @($tcpRaw | Where-Object {
      $tree.Ids.Contains([int]$_.OwningProcess) -and
      (Test-NonLoopbackRemote ([string]$_.RemoteAddress) ([int]$_.RemotePort))
    })
    $udp = @($udpRaw | Where-Object { $tree.Ids.Contains([int]$_.OwningProcess) })
    $observedUdp += $udp.Count
    $edgeCount = @($tree.Processes | Where-Object { $_.name -eq 'msedgewebview2.exe' }).Count
    foreach ($c in $tcp) {
      # No remote IP, command line, home path or other sensitive endpoint data
      # in version-controlled evidence. IP family, port and state suffice here.
      $owner = @($tree.Processes | Where-Object { $_.pid -eq [int]$c.OwningProcess } | Select-Object -First 1)
      $record = [pscustomobject]@{
        sample = $index; processName = if($owner.Count){$owner[0].name}else{'unknown'}
        family = Get-RemoteFamily ([string]$c.RemoteAddress)
        remotePort = [int]$c.RemotePort; state = [string]$c.State
      }
      $observed.Add($record)
    }
    $samples.Add([pscustomobject]@{
      sample=$index; treeCount=$tree.Ids.Count; webviewChildren=$edgeCount
      nonLoopbackTcpCount=$tcp.Count; localUdpEndpointCount=$udp.Count
      parentReuseSuspicions=$tree.ParentReuseSuspicions
    })
    Write-Output ('SAMPLE {0} tree={1} webview={2} nonloopbackTcp={3} udpLocal={4}' -f $index,$tree.Ids.Count,$edgeCount,$tcp.Count,$udp.Count)
    if ([datetime]::UtcNow -lt $stopAt) {
      Start-Sleep -Milliseconds $IntervalMs
    }
  } while ([datetime]::UtcNow -lt $stopAt)
} catch {
  $failure = $_.Exception.Message
  if ($failure -like '*root_identity_mismatch_or_gone*') { $rootGone = $true }
} finally {
  # Kill only the exact executable launched by this script, never WebView2
  # globally or another user's app. This is an observational harness.
  if ($null -ne $rootProcess) {
    try {
      if (-not $rootProcess.HasExited) {
        $rootProcess.Refresh()
        if (-not $rootProcess.HasExited) { Stop-Process -Id $rootProcess.Id -Force -ErrorAction Stop }
      }
    } catch {
      if ($null -eq $failure) { $failure = 'launched_process_cleanup_failed' }
    }
  }
}

$status = Get-WitnessDisposition -ExternalTcpCount $observed.Count -ProbeFailure $failure -ParentReuseSuspicions $parentReuses -RootIdentityLost $rootGone
$report = [ordered]@{
  schema = 'medorigin-windows-process-tree-egress-witness-v1'
  state = $status
  executableSha256 = $actualHash
  sampleCount = $samples.Count
  samplingSecondsRequested = $SamplingSeconds
  sampleIntervalMillisecondsRequested = $IntervalMs
  nonLoopbackTcpObservations = $observed.Count
  localUdpEndpointObservations = $observedUdp
  parentReuseSuspicions = $parentReuses
  rootIdentityLost = $rootGone
  probeError = $failure
  warnings = @(
    'Read-only live snapshots are NOT network confinement or packet capture.',
    'Transient TCP, UDP destinations, DNS, QUIC, proxies, injected threads and inherited handles can be missed.',
    'Local UDP endpoint counts do not reveal outbound remote UDP traffic.',
    'No snapshot result grants PHI, clinical use, offline claims, or release authorization.',
    'WebView2 runtime external TCP from earlier tests is an unresolved independent NO-GO.'
  )
  tcpObservations = @($observed.ToArray())
  samples = @($samples.ToArray())
}
$parentDir = Split-Path -Parent $ReportPath
if ($parentDir -and -not (Test-Path -LiteralPath $parentDir)) {
  [void](New-Item -ItemType Directory -Force -Path $parentDir)
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($ReportPath),
  ($report | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
Write-Output ('WITNESS_STATE='+$status)
Write-Output ('REPORT='+[IO.Path]::GetFullPath($ReportPath))
if ($status -eq 'OBSERVED_EXTERNAL_TCP_NO_GO') { exit 2 }
if ($status -eq 'INCOMPLETE_NO_GO') { exit 4 }
exit 3
