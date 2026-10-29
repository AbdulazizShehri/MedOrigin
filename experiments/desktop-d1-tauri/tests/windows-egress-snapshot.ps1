param([Parameter(Mandatory=$true)][int]$RootPid)
$ErrorActionPreference='Stop'
$all=Get-CimInstance Win32_Process -ErrorAction Stop
$root=@($all | Where-Object {$_.ProcessId -eq $RootPid})
if($root.Count -ne 1){throw 'D1 root process absent'}
if(-not $root[0].CreationDate){throw 'D1 root creation timestamp unavailable'}
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
$tcp=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {
 $ids.Contains([int]$_.OwningProcess) -and
 $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::')
})
$established=@($tcp | Where-Object {$_.State -eq 'Established'})
$udp=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
# A clean socket query is inconclusive if the root or any descendant exited,
# changed parent, or had its PID reused while sockets were enumerated.
$afterAll=@(Get-CimInstance Win32_Process -ErrorAction Stop)
$after=@($afterAll | Where-Object {$_.ProcessId -eq $RootPid})
if($after.Count -ne 1 -or $after[0].CreationDate -ne $root[0].CreationDate){throw 'D1 root process changed during snapshot'}
foreach($childId in $ids){
 if($childId -eq $RootPid){continue}
 $beforeChild=@($all | Where-Object {$_.ProcessId -eq $childId})
 $afterChild=@($afterAll | Where-Object {$_.ProcessId -eq $childId})
 if($beforeChild.Count -ne 1 -or $afterChild.Count -ne 1 -or
    -not $beforeChild[0].CreationDate -or
    $beforeChild[0].CreationDate -ne $afterChild[0].CreationDate -or
    $beforeChild[0].ParentProcessId -ne $afterChild[0].ParentProcessId){
  throw 'D1 child process changed during snapshot'
 }
}
Write-Output ('D1_PROCESS_TREE_COUNT='+$ids.Count)
Write-Output ('EXTERNAL_ESTABLISHED_TCP='+$established.Count)
Write-Output ('EXTERNAL_TCP_ALL_STATES='+$tcp.Count)
foreach($c in $tcp){
 Write-Output ('EXTERNAL_TCP pid='+$c.OwningProcess+' state='+$c.State+' remote='+$c.RemoteAddress+':'+$c.RemotePort)
}
Write-Output ('UDP_ENDPOINT_COUNT='+$udp.Count)
Write-Output 'Snapshot only: zero observed sockets is NOT a zero-egress proof; packet capture and OS-level isolation remain required.'
if($tcp.Count -gt 0){Write-Output 'D1_NETWORK_ISOLATION_NO_GO';exit 2}
Write-Output 'D1_SNAPSHOT_NO_EXTERNAL_TCP'
