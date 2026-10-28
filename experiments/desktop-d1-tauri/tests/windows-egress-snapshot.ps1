param([Parameter(Mandatory=$true)][int]$RootPid)
$ErrorActionPreference='Stop'
$all=Get-CimInstance Win32_Process
if(-not ($all | Where-Object {$_.ProcessId -eq $RootPid})){throw 'D1 root process absent'}
$ids=[System.Collections.Generic.HashSet[int]]::new()
[void]$ids.Add($RootPid)
do {
 $changed=$false
 foreach($p in $all){
  if($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)){
   [void]$ids.Add([int]$p.ProcessId)
   $changed=$true
  }
 }
}while($changed)
$external=@(Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | Where-Object {
 $ids.Contains([int]$_.OwningProcess) -and
 $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::')
})
$udp=@(Get-NetUDPEndpoint -ErrorAction SilentlyContinue | Where-Object {$ids.Contains([int]$_.OwningProcess)})
Write-Output ('D1_PROCESS_TREE_COUNT='+$ids.Count)
Write-Output ('EXTERNAL_ESTABLISHED_TCP='+$external.Count)
foreach($c in $external){
 Write-Output ('EXTERNAL_TCP pid='+$c.OwningProcess+' remote='+$c.RemoteAddress+':'+$c.RemotePort)
}
Write-Output ('UDP_ENDPOINT_COUNT='+$udp.Count)
Write-Output 'Snapshot only: zero observed sockets is NOT a zero-egress proof; packet capture and OS-level isolation remain required.'
if($external.Count -gt 0){Write-Output 'D1_NETWORK_ISOLATION_NO_GO';exit 2}
Write-Output 'D1_SNAPSHOT_NO_EXTERNAL_ESTABLISHED_TCP'
