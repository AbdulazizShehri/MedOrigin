# Real Windows keyboard-only (Tab, Shift+Tab, Space) fictional comparison QA.
# UIA reads focus/result only; no Invoke/TogglePattern/mouse, no file/PHI/network.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$ExePath,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {throw 'EXE_MISSING'}
if ((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {throw 'EXE_NAME_MISMATCH'}
if ((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256) {throw 'EXE_SHA_MISMATCH'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
$p=$null
try {
 $p=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
 $root=[System.Windows.Automation.AutomationElement]::RootElement
 $window=$null
 for($attempt=0;$attempt -lt 80;$attempt++){
  foreach($n in $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
    try{if($n.Current.ProcessId -eq $p.Id -and $n.Current.Name -like 'MedOrigin Native Rust*' -and -not $n.Current.IsOffscreen){$window=$n;break}}catch{}
  }
  if($window){break};Start-Sleep -Milliseconds 160
 }
 if(!$window){throw 'WINDOW_NOT_FOUND'}
 $window.SetFocus()
 Start-Sleep -Milliseconds 250
 function Focused {
  $f=[System.Windows.Automation.AutomationElement]::FocusedElement
  if(-not $f){throw 'FOCUS_MISSING'}
  $info=$f.Current
  if($info.ProcessId -ne $p.Id){throw ('FOCUS_ESCAPED_APP PID='+$info.ProcessId)}
  return $info.Name
 }
 function SendKey([string]$key) {
  $null=Focused
  [System.Windows.Forms.SendKeys]::SendWait($key)
  Start-Sleep -Milliseconds 120
 }
 function TabUntil([string]$wanted,[int]$limit=55) {
  for($i=0;$i -lt $limit;$i++){
   SendKey '{TAB}'
   $name=Focused
   Write-Output ('FOCUS_TAB='+$i+' NAME='+$name)
   if($name -ceq $wanted){return}
  }
  throw ('KEYBOARD_TARGET_NOT_REACHABLE='+$wanted)
 }
 function SpaceAt([string]$wanted) {
  if((Focused) -cne $wanted){throw ('WRONG_FOCUSED_ELEMENT='+$wanted)}
  SendKey ' '
  Write-Output ('KEYBOARD_ACTIVATED='+$wanted)
 }
 function See([string]$expected,[bool]$present=$true) {
  for($i=0;$i -lt 40;$i++) {
   $nodes=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
   $match=@($nodes | Where-Object{try{$_.Current.Name -ceq $expected -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text'}catch{$false}}).Count
   if($present -and $match -ge 1){return}
   if((-not $present) -and $match -eq 0){return}
   Start-Sleep -Milliseconds 160
  }
  throw ('TEXT_FAIL='+$expected+',present='+$present)
 }
 TabUntil 'Choose second fictional fixture (9)'
 SpaceAt 'Choose second fictional fixture (9)'
 TabUntil 'Compare: observation-minimal'
 SpaceAt 'Compare: observation-minimal'
 TabUntil 'Compare verified fictional JSON (read-only)'
 SpaceAt 'Compare verified fictional JSON (read-only)'
 See 'SHA-256: 747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0'
 See 'SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19'
 Write-Output 'KEYBOARD_REAL_COMPARE_TWO_SHA_PASS'
 SendKey '+{TAB}'
 $reverse=(Focused)
 Write-Output ('SHIFT_TAB_FOCUSED='+$reverse)
 if($reverse -cne 'Compare: bundle-dangling'){
  SendKey '+{TAB}'
  $reverse=(Focused)
  Write-Output ('SHIFT_TAB_REPEAT_FOCUSED='+$reverse)
 }
 if($reverse -cne 'Compare: bundle-dangling'){throw 'REVERSE_SHIFT_TAB_FOCUS_WRONG'}
 Write-Output 'KEYBOARD_REAL_REVERSE_SHIFT_TAB_PASS'
 TabUntil 'Compare: patient-minimal'
 SpaceAt 'Compare: patient-minimal'
 TabUntil 'Compare verified fictional JSON (read-only)'
 SpaceAt 'Compare verified fictional JSON (read-only)'
 See 'FAIL CLOSED: choose two distinct fictional fixtures'
 See 'SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19' $false
 Write-Output 'KEYBOARD_REAL_SAME_FIXTURE_REFUSAL_PASS'
 TabUntil 'Compare: observation-minimal'
 SpaceAt 'Compare: observation-minimal'
 TabUntil 'Compare verified fictional JSON (read-only)'
 SpaceAt 'Compare verified fictional JSON (read-only)'
 See 'SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19'
 TabUntil 'Verify synthetic SHA-256'
 SpaceAt 'Verify synthetic SHA-256'
 See 'SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19' $false
 Write-Output 'KEYBOARD_REAL_STALE_CLEAR_PASS'
 Write-Output 'D2_COMPARE_WINDOWS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING'
}catch{
 [Console]::Error.WriteLine('D2_COMPARE_WINDOWS_KEYBOARD_NO_GO: '+$_.Exception.Message)
 exit 1
}finally{
 if($p -and -not $p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}
}
