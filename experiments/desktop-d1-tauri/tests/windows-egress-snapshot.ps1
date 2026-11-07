param([Parameter(Mandatory=$true)][int]$RootPid)
$ErrorActionPreference='Stop'
$all=Get-CimInstance Win32_Process -ErrorAction Stop
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
$tcp=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {
 $ids.Contains([int]$_.OwningProcess) -and
 $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::')
})
$established=@($tcp | Where-Object {$_.State -eq 'Established'})
$udp=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
Write-Output ('D1_PROCESS_TREE_COUNT='+$ids.Count)
Write-Output ('EXTERNAL_ESTABLISHED_TCP='+$established.Count)
Write-Output ('EXTERNAL_TCP_ALL_STATES='+$tcp.Count)
foreach($c in $tcp){
 Write-Output ('EXTERNAL_TCP pid='+$c.OwningProcess+' state='+$c.State+' remote='+$c.RemoteAddress+':'+$c.RemotePort)
}
Write-Output ('UDP_ENDPOINT_COUNT='+$udp.Count)
foreach($endpoint in $udp){
 Write-Output ('UDP_ENDPOINT pid='+$endpoint.OwningProcess+' local='+$endpoint.LocalAddress+':'+$endpoint.LocalPort)
}
Write-Output 'Snapshot only: zero observed sockets is NOT a zero-egress proof; packet capture and OS-level isolation remain required.'
if($tcp.Count -gt 0 -or $udp.Count -gt 0){Write-Output 'D1_NETWORK_ISOLATION_NO_GO';exit 2}
Write-Output 'D1_SNAPSHOT_NO_EXTERNAL_TCP'
Write-Output 'D1_SNAPSHOT_NO_UDP_ENDPOINTS'
