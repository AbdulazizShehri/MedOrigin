# Real native Windows UIAutomation: two independently verified fictional JSON texts.
# Exact executable SHA required; source fixture files are test-only, never app input.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){throw 'missing executable'}
if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){throw 'wrong executable'}
if((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256){throw 'wrong SHA256'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process=$null
try {
  $process=Start-Process -FilePath (Resolve-Path $ExePath).Path -PassThru
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 60;$i++){
    foreach($node in $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
      try {if($node.Current.ProcessId -eq $process.Id -and $node.Current.Name -like 'MedOrigin Native Rust*' -and -not $node.Current.IsOffscreen){$window=$node;break}}catch{}
    }
    if($window){break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'native window not visible'}
  function Nodes { @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)) }
  function One([string]$label){
    # Native eframe redraws button trees asynchronously when changing a
    # fictional comparison selection. Wait for a unique accessible button
    # rather than interpreting a transient missing node as a product failure.
    for($retry=0;$retry -lt 40;$retry++){
      $found=@(Nodes | Where-Object {
        try {$_.Current.Name -ceq $label -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.IsEnabled} catch {$false}
      })
      if($found.Count -eq 1){return $found[0]}
      Start-Sleep -Milliseconds 150
    }
    throw ('missing/ambiguous button '+$label+' count='+$found.Count)
  }
  function Press([System.Windows.Automation.AutomationElement]$element){
    try {$element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
    catch {$element.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()}
  }
  function ExpectText([string]$text,[bool]$present=$true){
    for($i=0;$i -lt 35;$i++){
      $count=@(Nodes | Where-Object {
        try {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text' -and $_.Current.Name -ceq $text} catch {$false}
      }).Count
      if($present -and $count -ge 1){return}
      if((-not $present) -and $count -eq 0){return}
      Start-Sleep -Milliseconds 180
    }
    throw ('expected text mismatch present='+$present+' text='+$text)
  }
  $d0source=Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'desktop-d0-rust\src\lib.rs'
  $rust=Get-Content -LiteralPath $d0source -Raw
  $patient=([regex]::Match($rust,'const PATIENT: &\[u8\] = br#"(.*?)"#;',[System.Text.RegularExpressions.RegexOptions]::Singleline)).Groups[1].Value
  $observation=([regex]::Match($rust,'const OBSERVATION: &\[u8\] = br#"(.*?)"#;',[System.Text.RegularExpressions.RegexOptions]::Singleline)).Groups[1].Value
  if($patient.Length -ne 57 -or $observation.Length -ne 251){throw 'D0 source fixture extraction mismatch'}
  # Independently derive exact HEX context from the pinned fictional D0 bytes.
  $a=[Text.Encoding]::UTF8.GetBytes($patient)
  $b=[Text.Encoding]::UTF8.GetBytes($observation)
  $offset=0
  while($offset -lt [Math]::Min($a.Length,$b.Length) -and $a[$offset] -eq $b[$offset]){$offset++}
  $start=[Math]::Max(0,$offset-8)
  $endA=[Math]::Min($a.Length,$offset+8)
  $endB=[Math]::Min($b.Length,$offset+8)
  $hexA=($a[$start..($endA-1)] | ForEach-Object {$_.ToString('X2')}) -join ' '
  $hexB=($b[$start..($endB-1)] | ForEach-Object {$_.ToString('X2')}) -join ' '
  $hexContext='Fictional HEX context at zero-based byte {0}: left bytes {1}..{2} [HEX {3}]; right bytes {1}..{4} [HEX {5}]. Raw bytes only, not JSON semantics.' -f $offset,$start,$endA,$hexA,$endB,$hexB
  Press (One 'Choose second fictional fixture (9)')
  $option=$null
  for($i=0;$i -lt 35;$i++){
    try {$option=One 'Compare: observation-minimal';break}catch{Start-Sleep -Milliseconds 180}
  }
  if(-not $option){throw 'accessible second fixture missing'}
  Press $option
  Press (One 'Compare verified fictional JSON (read-only)')
  ExpectText $patient
  ExpectText $observation
  ExpectText 'SHA-256: 747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0'
  ExpectText 'SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19'
  $byteDiff='Fictional byte difference: first differing byte offset 17 (zero-based); common suffix 1 bytes; left 57 bytes, right 251 bytes. Original source bytes unchanged.'
  ExpectText $byteDiff
  ExpectText $hexContext
  Write-Output 'D2_COMPARE_TWO_REAL_UIA_PASS'

  Press (One 'Compare: patient-minimal')
  Press (One 'Compare verified fictional JSON (read-only)')
  ExpectText 'FAIL CLOSED: choose two distinct fictional fixtures'
  ExpectText $observation $false
  ExpectText $byteDiff $false
  ExpectText $hexContext $false
  Write-Output 'D2_COMPARE_SAME_FIXTURE_REFUSAL_PASS'

  Press (One 'Compare: observation-minimal')
  Press (One 'Compare verified fictional JSON (read-only)')
  ExpectText $observation
  Press (One 'Verify synthetic SHA-256')
  ExpectText $observation $false
  ExpectText $byteDiff $false
  ExpectText $hexContext $false
  Write-Output 'D2_COMPARE_STALE_CLEAR_PASS'
  Write-Output 'D2_COMPARE_WINDOWS_UIA_3_OF_3_PASS_NONPUBLISHING'
}catch{
  [Console]::Error.WriteLine('D2_COMPARE_WINDOWS_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
}finally{
  if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}
}
