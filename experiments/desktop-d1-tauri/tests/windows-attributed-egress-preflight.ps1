# Read-only Windows D1 native WebView2 process-tree TCP attribution.
# All outcomes are release NO-GO: absence of observed sockets is not isolation.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateRange(1,2147483647)][int]$RootPid,
  [Parameter(Mandatory=$true)][string]$ExpectedRootExecutable,
  [Parameter(Mandatory=$true)][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
$record=[ordered]@{
  schema='medorigin-d1-windows-attributed-egress-v1'
  decision='NO_GO'
  reason='UNVERIFIED'
  root_pid=$RootPid
  root_executable_sha256=$null
  observed_processes=0
  external_tcp_all_states=0
  external_established_tcp=0
  udp_endpoints=0
  os_packet_egress_denial_proven=$false
  dns_udp_egress_denial_proven=$false
  release_authorized=$false
  host_policy_modified=$false
}
function Refuse([string]$why,[int]$status){
  $record.reason=$why
  $record | ConvertTo-Json -Depth 5 -Compress
  exit $status
}
try {
  if($ExpectedSha256 -notmatch '^[0-9A-Fa-f]{64}$'){ Refuse 'INVALID_PINNED_SHA256' 4 }
  if(-not [IO.Path]::IsPathRooted($ExpectedRootExecutable)){ Refuse 'REQUIRES_ABSOLUTE_EXE_PATH' 4 }
  if([IO.Path]::GetFileName($ExpectedRootExecutable) -cne 'medorigin-desktop-d1-preview.exe'){
    Refuse 'WRONG_D1_EXECUTABLE_NAME' 4
  }
  if(-not (Test-Path -LiteralPath $ExpectedRootExecutable -PathType Leaf)){
    Refuse 'D1_EXECUTABLE_MISSING' 4
  }
  $absolute=(Resolve-Path -LiteralPath $ExpectedRootExecutable -ErrorAction Stop).ProviderPath
  if([IO.Path]::GetFileName($absolute) -cne 'medorigin-desktop-d1-preview.exe'){
    Refuse 'RESOLVED_EXE_NAME_MISMATCH' 4
  }
  $digest=(Get-FileHash -Algorithm SHA256 -LiteralPath $absolute -ErrorAction Stop).Hash
  if($digest -ine $ExpectedSha256){ Refuse 'D1_EXECUTABLE_SHA256_MISMATCH' 4 }
  $record.root_executable_sha256=$digest

  # A single CIM snapshot establishes root identity and process ancestry.
  # Repeat root identity after sockets to reject reused root PID/changed image.
  $before=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  $root=@($before | Where-Object { [int]$_.ProcessId -eq $RootPid })
  if($root.Count -ne 1){ Refuse 'D1_ROOT_ABSENT_OR_AMBIGUOUS' 4 }
  if([string]::IsNullOrWhiteSpace([string]$root[0].ExecutablePath) -or
     [string]::IsNullOrWhiteSpace([string]$root[0].CreationDate)){
    Refuse 'D1_ROOT_IMAGE_OR_BIRTH_UNREADABLE' 4
  }
  $image=([string]$root[0].ExecutablePath)
  if(-not [string]::Equals($absolute,$image,[StringComparison]::OrdinalIgnoreCase)){
    Refuse 'D1_ROOT_IMAGE_PATH_MISMATCH' 4
  }
  $born=[string]$root[0].CreationDate
  $ids=[System.Collections.Generic.HashSet[int]]::new()
  [void]$ids.Add($RootPid)
  do {
    $changed=$false
    foreach($entry in $before){
      $pidInt=[int]$entry.ProcessId
      if($ids.Contains([int]$entry.ParentProcessId) -and -not $ids.Contains($pidInt)){
        [void]$ids.Add($pidInt)
        $changed=$true
      }
    }
  }while($changed)
  $record.observed_processes=$ids.Count
  # We intentionally include SYN_SENT, CLOSE_WAIT, etc. and fail on ANY
  # external socket owned by native root or a snapshot descendant.
  $external=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {
    $ids.Contains([int]$_.OwningProcess) -and
    $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::')
  })
  $record.external_tcp_all_states=$external.Count
  $record.external_established_tcp=@($external | Where-Object {$_.State -eq 'Established'}).Count
  $record.udp_endpoints=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {
    $ids.Contains([int]$_.OwningProcess)
  }).Count
  $after=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  $rootAfter=@($after | Where-Object {[int]$_.ProcessId -eq $RootPid})
  if($rootAfter.Count -ne 1 -or
     [string]$rootAfter[0].CreationDate -cne $born -or
     -not [string]::Equals([string]$rootAfter[0].ExecutablePath,$absolute,[StringComparison]::OrdinalIgnoreCase)){
    Refuse 'D1_ROOT_IDENTITY_CHANGED_DURING_OBSERVATION' 4
  }
  if($external.Count -gt 0){ Refuse 'D1_OBSERVED_EXTERNAL_TCP_NO_GO' 2 }
  Refuse 'NO_EXTERNAL_TCP_OBSERVED_PACKET_DNS_UNPROVEN' 3
}
catch {
  # Never turn CIM/permissions/endpoint errors into no-egress success.
  $record.reason='D1_OBSERVATION_ERROR'
  $record.error_type=$_.Exception.GetType().Name
  $record | ConvertTo-Json -Depth 5 -Compress
  exit 4
}
