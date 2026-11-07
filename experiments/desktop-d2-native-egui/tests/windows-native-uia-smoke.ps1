# Adapted from MedOrigin D1 synthetic UIA probe. Only fictional D0 vectors.
# Run locally on interactive Windows. No PHI, server, installer or network assertion.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){throw 'Missing native D2 debug executable'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$p=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru -ErrorAction Stop
try {
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($attempt=0;$attempt -lt 60;$attempt++){
    Start-Sleep -Milliseconds 200
    foreach($item in $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
      if($item.Current.ProcessId -eq $p.Id -and $item.Current.Name -like 'MedOrigin Native Rust*'){
        $window=$item
        break
      }
    }
    if($window){break}
  }
  if(-not $window){throw 'D2 native window inaccessible'}
  $buttons=[System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button
  )
  $textCondition=[System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Text
  )
  function Click([string]$name){
    for($attempt=0;$attempt -lt 60;$attempt++){
      $items=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$buttons)
      foreach($button in $items){
        if($button.Current.Name -eq $name){
          try {
            $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
          } catch {
            $button.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()
          }
          return
        }
      }
      Start-Sleep -Milliseconds 200
    }
    throw ('Missing accessible D2 button: '+$name)
  }
  $cases=@(
    @{id='patient-minimal';bytes=57;sha='747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0'},
    @{id='patient-invalid-utf8';bytes=1;sha='a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89'},
    @{id='patient-over-limit';bytes=32769;sha='b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538'},
    @{id='patient-exact-limit';bytes=32768;sha='ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e'}
  )
  foreach($case in $cases){
    Click ($case.id+' ('+$case.bytes+' bytes)')
    Click 'Verify synthetic SHA-256'
    $matched=$false
    for($attempt=0;$attempt -lt 45;$attempt++){
      Start-Sleep -Milliseconds 200
      $texts=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,$textCondition)
      foreach($text in $texts){
        if($text.Current.Name -eq ('Synthetic raw SHA-256 verified: '+$case.sha)){
          $matched=$true
          break
        }
      }
      if($matched){break}
    }
    if(-not $matched){throw ('Native D2 UI result mismatch: '+$case.id)}
    Write-Output ('D2_NATIVE_UIA_PASS='+$case.id+' '+$case.sha)
  }
  Write-Output 'D2_NATIVE_UIA_4_OF_4_PASS (native window, fictional SHA only; no network proof)'
} finally {
  if(-not $p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}
}
