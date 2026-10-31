param([Parameter(Mandatory=$true)][string]$ExePath,[Parameter(Mandatory=$true)][string]$ExpectedExeSha256)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$full=(Resolve-Path -LiteralPath $ExePath).Path
$sha=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
if($ExpectedExeSha256 -notmatch '^[0-9a-fA-F]{64}$' -or $sha -ne $ExpectedExeSha256){throw 'Exact executable SHA-256 mismatch'}
$matches=@(Get-CimInstance Win32_Process -Filter "Name='medorigin-desktop-d1-preview.exe'" | Where-Object { $_.ExecutablePath -eq $full })
if($matches.Count -ne 1){throw ('Expected exactly one exact-path D1 root; got '+$matches.Count)}
$rootPid=[int]$matches[0].ProcessId
$root=[System.Windows.Automation.AutomationElement]::RootElement
$window=$null
for($i=0;$i -lt 40;$i++){
  $windows=$root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
  foreach($w in $windows){if($w.Current.ProcessId -eq $rootPid -and $w.Current.Name -eq 'MedOrigin - Synthetic Developer Preview'){$window=$w;break}}
  if($window){break}
  Start-Sleep -Milliseconds 200
}
if(-not $window){throw 'MXC D1 host UIA window not found'}
$buttonCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
$textCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
function ClickButton([string]$prefix){
  for($attempt=0;$attempt -lt 50;$attempt++){
    $buttons=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttonCondition)
    foreach($b in $buttons){
      if($b.Current.Name.StartsWith($prefix,[System.StringComparison]::Ordinal)){
        if($prefix -eq 'Verify with Rust'){$b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
        else{$b.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()}
        return
      }
    }
    Start-Sleep -Milliseconds 150
  }
  throw ('Missing UIA button '+$prefix)
}
function ReadNames {
  $items=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$textCondition)
  $names=@()
  foreach($item in $items){$names+=$item.Current.Name}
  return ,$names
}
$cases=@(
  @{button='Minimal Patient';id='patient-minimal';sha='747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0'},
  @{button='Invalid encoding';id='patient-invalid-utf8';sha='a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89'},
  @{button='Oversize payload';id='patient-over-limit';sha='b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538'},
  @{button='Exact limit';id='patient-exact-limit';sha='ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e'}
)
foreach($case in $cases){
  ClickButton $case.button
  ClickButton 'Verify with Rust'
  $ok=$false
  for($i=0;$i -lt 25;$i++){
    $names=ReadNames
    if(($names -contains $case.sha) -and [bool]($names | Where-Object {$_ -match 'MATCHES REFERENCE'}) -and [bool]($names | Where-Object {$_ -match 'medorigin-desktop-d0-raw-sha256-v1'})){$ok=$true;break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $ok){throw ('MXC D1 UIA mismatch '+$case.id)}
  Write-Output ('MXC_D1_UIA_PASS '+$case.id)
}
$all=@(Get-CimInstance Win32_Process)
$ids=New-Object 'System.Collections.Generic.HashSet[int]'
[void]$ids.Add($rootPid)
for($i=0;$i -lt 15;$i++){
  $added=$false
  foreach($p in $all){if($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)){[void]$ids.Add([int]$p.ProcessId);$added=$true}}
  if(-not $added){break}
}
$webview=@($all | Where-Object {$ids.Contains([int]$_.ProcessId) -and $_.Name -eq 'msedgewebview2.exe'})
if($webview.Count -lt 1){throw 'No actual WebView2 descendants under D1 root'}
$inventory=@($all | Where-Object {$ids.Contains([int]$_.ProcessId)} | ForEach-Object {
  if(-not $_.CreationDate){throw 'Process creation identity unavailable'}
  [pscustomobject]@{pid=[int]$_.ProcessId;startTicks=[string]$_.CreationDate.ToUniversalTime().Ticks;name=[string]$_.Name}
})
Write-Output ('MXC_D1_PROCESS_SNAPSHOT_JSON='+(ConvertTo-Json -InputObject $inventory -Compress -Depth 3))
$tcp=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
$udp=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
$nonloop=@($tcp | Where-Object {$_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::') -and $_.State -notin @('Listen','Bound')})
Write-Output ('MXC_D1_PROCESS_TREE='+$ids.Count+' WEBVIEW2='+$webview.Count+' OWNED_TCP='+$tcp.Count+' NONLOOP_TCP='+$nonloop.Count+' UDP_ENDPOINTS='+$udp.Count+' ROOT_SHA256='+$sha)
if($nonloop.Count -gt 0){throw 'Observed nonloopback TCP in MXC D1 descendant tree'}
$maxSampledTcp=0
$maxSampledUdp=0
for($sample=0;$sample -lt 12;$sample++){
  $live=@(Get-CimInstance Win32_Process -ErrorAction Stop)
  $roots=@($live | Where-Object { $_.ProcessId -eq $rootPid -and $_.ExecutablePath -eq $full })
  if($roots.Count -ne 1){throw 'Exact source binary D1 root identity changed in windowed sampling'}
  $tree=New-Object 'System.Collections.Generic.HashSet[int]'
  [void]$tree.Add($rootPid)
  for($depth=0;$depth -lt 15;$depth++){
    $new=$false
    foreach($child in $live){
      if($tree.Contains([int]$child.ParentProcessId) -and -not $tree.Contains([int]$child.ProcessId)){
        [void]$tree.Add([int]$child.ProcessId)
        $new=$true
      }
    }
    if(-not $new){break}
  }
  $web=@($live | Where-Object {$tree.Contains([int]$_.ProcessId) -and $_.Name -eq 'msedgewebview2.exe'})
  if($web.Count -lt 1){throw 'Real WebView2 descendants missing during windowed sampling'}
  $tcpNow=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$tree.Contains([int]$_.OwningProcess)})
  $udpNow=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {$tree.Contains([int]$_.OwningProcess)})
  $bad=@($tcpNow | Where-Object {
    $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::') -and $_.State -notin @('Listen','Bound')
  })
  if($bad.Count -gt 0){throw ('Nonloopback TCP in WebView2/D1 process tree sample '+$sample)}
  $maxSampledTcp=[math]::Max($maxSampledTcp,$tcpNow.Count)
  $maxSampledUdp=[math]::Max($maxSampledUdp,$udpNow.Count)
  Start-Sleep -Milliseconds 250
}
Write-Output ('MXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12 max_owned_tcp='+$maxSampledTcp+' max_udp_endpoints='+$maxSampledUdp+' NO_PACKET_LEVEL_ATTESTATION')
Write-Output 'MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO'
