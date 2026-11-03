param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){throw 'Missing locally built D1 executable'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
try {
 $root=[System.Windows.Automation.AutomationElement]::RootElement
 $window=$null
 for($i=0;$i -lt 60;$i++){
  Start-Sleep -Milliseconds 250
  $windows=$root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
  foreach($w in $windows){if($w.Current.ProcessId -eq $process.Id -and $w.Current.Name -eq 'MedOrigin - Synthetic Developer Preview'){$window=$w;break}}
  if($window){break}
 }
 if(-not $window){throw 'Native Tauri window was not accessible'}
 $buttonCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
 $textCondition=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Text)
 function ClickButton([string]$prefix) {
  for($attempt=0;$attempt -lt 80;$attempt++){
   $buttons=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttonCondition)
   foreach($b in $buttons){
    if($b.Current.Name.StartsWith($prefix,[System.StringComparison]::Ordinal)){
     if($prefix -eq 'Verify with Rust'){$b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
     else{$b.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()}
     return
    }
   }
   Start-Sleep -Milliseconds 250
  }
  throw ('Missing accessible button: '+$prefix)
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
  for($i=0;$i -lt 30;$i++){
   Start-Sleep -Milliseconds 200
   $names=ReadNames
   $hasHash=$names -contains $case.sha
   $hasMatch=[bool]($names | Where-Object {$_ -match 'MATCHES REFERENCE'})
   $hasContract=[bool]($names | Where-Object {$_ -match 'medorigin-desktop-d0-raw-sha256-v1'})
   if($hasHash -and $hasMatch -and $hasContract){$ok=$true;break}
  }
  if(-not $ok){throw ('D1 UI mismatch: '+$case.id+' hash='+$hasHash+' match='+$hasMatch+' contract='+$hasContract)}
  Write-Output ('PASS '+$case.id+' '+$case.sha)
 }
 Write-Output 'D1_UIA_4_OF_4_PASS (synthetic SHA only; NOT FHIR validation)'
}
finally {if(-not $process.HasExited){Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}}
