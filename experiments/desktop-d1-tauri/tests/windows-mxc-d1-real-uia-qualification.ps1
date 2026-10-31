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
$tcp=@(Get-NetTCPConnection -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
$udp=@(Get-NetUDPEndpoint -ErrorAction Stop | Where-Object {$ids.Contains([int]$_.OwningProcess)})
$nonloop=@($tcp | Where-Object {$_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::') -and $_.State -notin @('Listen','Bound')})
Write-Output ('MXC_D1_PROCESS_TREE='+$ids.Count+' WEBVIEW2='+$webview.Count+' OWNED_TCP='+$tcp.Count+' NONLOOP_TCP='+$nonloop.Count+' UDP_ENDPOINTS='+$udp.Count+' ROOT_SHA256='+$sha)
if($nonloop.Count -gt 0){throw 'Observed nonloopback TCP in MXC D1 descendant tree'}
Write-Output 'MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO'

[executed on device: Abdulaziz (62835bd9-9ffe-4bd5-9010-6ac23b2d7223)]

Note: you've used 85% of this month's Desktop Commander usage. Visit https://mcp.desktopcommander.app/ to learn more about usage and resets.
