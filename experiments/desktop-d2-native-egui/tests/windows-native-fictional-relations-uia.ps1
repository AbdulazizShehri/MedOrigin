# Exact-binary, read-only Windows UIA qualification for browserless D2 fictional links.
# Never reads patient files, changes OS security settings, publishes or signs.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){ throw 'native_D2_binary_missing' }
if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){throw 'wrong_executable_name'}
$actual=(Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
if($actual -ine $ExpectedSha256){throw 'exact_executable_sha256_mismatch_refuse_launch'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process=$null
try {
  $process=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 65;$i++){
    $top=$root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
    foreach($node in $top){
      try{
        if($node.Current.ProcessId -eq $process.Id -and $node.Current.Name -like 'MedOrigin Native Rust*' -and -not $node.Current.IsOffscreen){
          $window=$node;break
        }
      }catch{}
    }
    if($window){break}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window){throw 'native_browserless_D2_window_unavailable'}
  function Nodes {
    return @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition))
  }
  function One([string]$name){
    $items=@(Nodes | Where-Object {
      try{$_.Current.Name -ceq $name -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.IsEnabled}catch{$false}
    })
    if($items.Count -ne 1){throw ('missing_or_ambiguous_native_button='+$name+' count='+$items.Count)}
    return $items[0]
  }
  function WaitOne([string]$name){
    for($j=0;$j -lt 45;$j++){
      try{return One $name}catch{Start-Sleep -Milliseconds 150}
    }
    $known=@(Nodes | Where-Object {try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button'}catch{$false}} |
      ForEach-Object {try{$_.Current.Name}catch{''}} | Select-Object -First 45)
    Write-Output ('AVAILABLE_NATIVE_BUTTONS='+($known -join ' | '))
    throw ('native_button_never_appeared='+$name)
  }
  function Press([System.Windows.Automation.AutomationElement]$node){
    try{$node.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()}
    catch{$node.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()}
  }
  function ExactText([string]$expected,[bool]$present=$true){
    for($i=0;$i -lt 40;$i++){
      $count=@(Nodes | Where-Object {
        try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text' -and $_.Current.Name -ceq $expected}catch{$false}
      }).Count
      if($present -and $count -ge 1){return}
      if(-not $present -and $count -eq 0){return}
      Start-Sleep -Milliseconds 150
    }
    throw ('native_text_expectation_failed='+$expected+' present='+$present)
  }
  Write-Output 'D2_NATIVE_EXACT_SHA256_VERIFIED'
  Press (One 'Additional fictional FHIR/Bundle cases (8)')
  Press (WaitOne 'observation-minimal (251 bytes)')
  Press (WaitOne 'Inspect verified fictional relationships (read-only)')
  ExactText 'FICTIONAL RELATIONSHIPS VERIFIED - NOT FHIR OR CLINICAL VALIDATION'
  ExactText 'Source fixture: observation-minimal (251 bytes)'
  ExactText 'Source SHA-256: 527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19'
  ExactText 'JSON pointer /subject/reference -> Patient/synthetic (fictional_subject_reference)'
  ExactText 'No recorded event dates in these source files; chronology unavailable.'
  Write-Output 'D2_OBSERVATION_NATIVE_RELATIONSHIP_PASS'
  Press (WaitOne 'bundle-valid (531 bytes)')
  ExactText 'Source fixture: observation-minimal (251 bytes)' $false
  Press (WaitOne 'Inspect verified fictional relationships (read-only)')
  ExactText 'Source fixture: bundle-valid (531 bytes)'
  ExactText 'JSON pointer /entry/0/resource -> urn:uuid:00000000-0000-4000-8000-000000000001 (fictional_bundle_patient_member)'
  ExactText 'JSON pointer /entry/1/resource -> urn:uuid:00000000-0000-4000-8000-000000000002 (fictional_bundle_observation_member)'
  ExactText 'JSON pointer /entry/1/resource/subject/reference -> Patient/synthetic (fictional_subject_reference)'
  ExactText 'JSON pointer /subject/reference -> Patient/synthetic (fictional_subject_reference)' $false
  Write-Output 'D2_BUNDLE_NATIVE_RELATIONSHIP_PASS'
  Press (One 'Verify synthetic SHA-256')
  ExactText 'Source fixture: bundle-valid (531 bytes)' $false
  Write-Output 'D2_NATIVE_REVERIFY_CLEARS_RELATIONSHIP_PASS'
  Press (WaitOne 'bundle-bad-reference (528 bytes)')
  Press (WaitOne 'Inspect verified fictional relationships (read-only)')
  ExactText 'Relationship inspection unavailable: this fictional source is not in the reviewed three-source graph'
  ExactText 'FICTIONAL RELATIONSHIPS VERIFIED - NOT FHIR OR CLINICAL VALIDATION' $false
  Write-Output 'D2_NEGATIVE_FIXTURE_RELATIONSHIP_REFUSAL_PASS'
  Write-Output 'D2_NATIVE_FICTIONAL_RELATIONSHIPS_UIA_4_OF_4_PASS_NONPUBLISHING'
} catch {
  [Console]::Error.WriteLine('D2_NATIVE_RELATIONSHIPS_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
} finally {
  if($process){
    try{
      $process.Refresh()
      if(-not $process.HasExited){Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}
    }catch{}
  }
}
