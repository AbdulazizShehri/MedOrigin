# Real, read-only D1/WebView2 attributed egress lifecycle smoke.
# Always release NO-GO. No system firewall mutation or packets emitted by harness.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ExpectedSha256,
  [ValidateRange(2,20)][int]$Snapshots=5,
  [ValidateRange(300,10000)][int]$IntervalMs=1000
)
$ErrorActionPreference='Stop'
$summary=[ordered]@{
  schema='medorigin-d1-real-windows-egress-snapshot-series-v1'
  decision='NO_GO'
  reason='INCOMPLETE_OR_UNRUN'
  release_authorized=$false
  os_packet_denial_proven=$false
  dns_udp_denial_proven=$false
  host_policy_modified=$false
  actual_runtime_launched=$false
  snapshots_requested=$Snapshots
  snapshots_completed=0
  snapshots_with_observed_external_tcp=0
  maximum_external_tcp=0
  maximum_descendant_inclusive_processes=0
  root_executable_sha256=$null
  cases=@()
}
$owned=$null
try {
  $probe=Join-Path $PSScriptRoot 'windows-attributed-egress-preflight.ps1'
  if(-not (Test-Path -LiteralPath $probe -PathType Leaf)){throw 'ATTRIBUTION_PROBE_MISSING'}
  if(-not [IO.Path]::IsPathRooted($ExePath)){throw 'ABSOLUTE_PATH_REQUIRED'}
  if([IO.Path]::GetFileName($ExePath) -cne 'medorigin-desktop-d1-preview.exe'){throw 'WRONG_EXE_NAME'}
  $resolved=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).ProviderPath
  $digest=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256 -ErrorAction Stop).Hash
  if($digest -ine $ExpectedSha256){throw 'EXACT_EXE_SHA256_MISMATCH'}
  $summary.root_executable_sha256=$digest
  $owned=Start-Process -FilePath $resolved -PassThru -ErrorAction Stop
  $summary.actual_runtime_launched=$true
  Start-Sleep -Milliseconds 600
  for($i=0;$i -lt $Snapshots;$i++){
    if($owned.HasExited){throw ('ROOT_EXITED_BEFORE_SNAPSHOT_'+$i)}
    # Probe always exits nonzero, even with zero observed external sockets.
    # Capture its JSON without leaking remote addresses or process command lines.
    $out=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $probe -RootPid $owned.Id -ExpectedRootExecutable $resolved -ExpectedSha256 $digest 2>&1
    $code=$LASTEXITCODE
    $data=($out | Out-String | ConvertFrom-Json -ErrorAction Stop)
    if($data.schema -ne 'medorigin-d1-windows-attributed-egress-v1' -or
       $data.decision -ne 'NO_GO' -or
       $data.release_authorized -ne $false -or
       $data.os_packet_egress_denial_proven -ne $false -or
       $data.dns_udp_egress_denial_proven -ne $false -or
       $data.host_policy_modified -ne $false){
      throw ('UNTRUSTED_SNAPSHOT_RESULT_'+$i)
    }
    $summary.snapshots_completed++
    $n=[int]$data.external_tcp_all_states
    $summary.maximum_external_tcp=[Math]::Max($summary.maximum_external_tcp,$n)
    $summary.maximum_descendant_inclusive_processes=[Math]::Max($summary.maximum_descendant_inclusive_processes,[int]$data.observed_processes)
    if($data.reason -eq 'D1_OBSERVED_EXTERNAL_TCP_NO_GO'){
      if($code -ne 2){throw ('WRONG_EXTERNAL_TCP_EXIT_'+$i)}
      $summary.snapshots_with_observed_external_tcp++
    }
    elseif($data.reason -eq 'NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN'){
      if($code -ne 3){throw ('WRONG_UNPROVEN_EXIT_'+$i)}
    }
    else {
      # A renamed root, recycled child PID, partial socket enumeration or
      # transient exited process is NOT a legitimate zero-egress sample.
      if($code -ne 4){throw ('WRONG_INCOMPLETE_EVIDENCE_EXIT_'+$i)}
      $summary.reason='OBSERVATION_INCOMPLETE_NO_GO'
    }
    $summary.cases+=@([ordered]@{
      sample=$i+1
      reason=[string]$data.reason
      decision='NO_GO'
      external_tcp_all_states=$n
      external_established_tcp=[int]$data.external_established_tcp
      observed_processes=[int]$data.observed_processes
      udp_endpoints=[int]$data.udp_endpoints
    })
    Start-Sleep -Milliseconds $IntervalMs
  }
  if($summary.reason -eq 'INCOMPLETE_OR_UNRUN'){
    if($summary.snapshots_with_observed_external_tcp -gt 0){
      $summary.reason='OBSERVED_EXTERNAL_TCP_NO_GO'
    }else{
      $summary.reason='NO_EXTERNAL_TCP_OBSERVED_OS_DENIAL_UNPROVEN'
    }
  }
}
catch {
  $summary.decision='NO_GO'
  $summary.reason='REAL_RUNTIME_OR_OBSERVATION_ERROR'
  $summary.error_type=$_.Exception.GetType().Name
}
finally {
  if($null -ne $owned){
    try {
      if(-not $owned.HasExited){
        Stop-Process -Id $owned.Id -Force -ErrorAction Stop
      }
      $owned.WaitForExit(5000) | Out-Null
      $summary.owned_root_stopped=$owned.HasExited
    } catch {
      $summary.reason='FAILED_TO_STOP_OWNED_ROOT'
      $summary.owned_root_stopped=$false
    }
  }
  $summary | ConvertTo-Json -Compress -Depth 6
}
# NO_GO is deliberate, even for a fully sampled interval with no TCP seen.
exit 2
