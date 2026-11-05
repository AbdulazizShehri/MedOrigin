# Real Windows UIAutomation for the native multi-patient fictional-only FHIR-shaped Bundle.
# Strict source fixture path + exact exe SHA; never real patient files/clinical operations.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$FixtureSha256,
  [switch]$EmbeddedDemo
)
$ErrorActionPreference='Stop'
$process=$null
try {
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Split-Path -Leaf $exe) -cne 'medorigin-desktop-d2-native-egui.exe' -or
     (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    throw 'reviewed_native_binary_refused'
  }
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\synthetic-multipatient-fhir-bundle.json')).Path
  $item=Get-Item -LiteralPath $fixture
  if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
     $item.Length -gt 32768 -or
     (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $FixtureSha256) {
    throw 'reviewed_eight_record_fictional_source_refused'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments=if($EmbeddedDemo){''}else{'--synthetic-multipatient-bundle-stdin'}
  $info.UseShellExecute=$false
  $info.RedirectStandardInput= -not [bool]$EmbeddedDemo
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()) {throw 'native_process_start_refused'}
  if(-not $EmbeddedDemo){
    $bytes=[IO.File]::ReadAllBytes($fixture)
    $process.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
    $process.StandardInput.Close()
  }
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 90;$i++) {
    $wins=@($root.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    )|Where-Object {
      try{$_.Current.ProcessId -eq $process.Id -and
          $_.Current.Name -like 'MedOrigin Native Rust*' -and
          -not $_.Current.IsOffscreen}catch{$false}
    })
    if($wins.Count -eq 1){$window=$wins[0];break}
    if($wins.Count -gt 1){throw 'multiple_native_test_windows'}
    if($process.HasExited){throw 'native_exited_before_ui_created'}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window){throw 'native_bundle_window_missing'}
  function Nodes {return @($window.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
  ))}
  function Has([string]$wanted){
    return @((Nodes|ForEach-Object{try{$_.Current.Name}catch{''}})|
      Where-Object {$_ -like ('*'+$wanted+'*')}).Count -gt 0
  }
  function Expect([string]$wanted){
    for($i=0;$i -lt 60;$i++){
      if(Has $wanted){return}
      Start-Sleep -Milliseconds 120
    }
    throw ('missing_real_bundle_ui: '+$wanted)
  }
  function Press([string]$wanted){
    for($i=0;$i -lt 65;$i++){
      $matches=@(Nodes|Where-Object{
        try {$_.Current.Name -ceq $wanted -and
          $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and
          $_.Current.IsEnabled}catch{$false}
      })
      if($matches.Count -eq 1){
        try{
          $invoke=[System.Windows.Automation.InvokePattern]$matches[0].GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
          )
          $invoke.Invoke()
        }catch{throw ('bundle_native_press_refused: '+$wanted)}
        Start-Sleep -Milliseconds 250
        return
      }
      if($matches.Count -gt 1){throw ('duplicate_bundle_button: '+$wanted)}
      Start-Sleep -Milliseconds 130
    }
    throw ('bundle_native_button_missing: '+$wanted)
  }
  if($EmbeddedDemo){
    Expect 'Native Rust Experiment'
    Press 'Open built-in two-patient fictional demo (NO PHI)'
  }
  Expect 'Fictional Multi-Patient Workspace'
  Expect '8 imaginary source-only records across 2 fictional patients'
  Expect 'Bundle: 4 of 8 fictional resources visible'
  Expect 'Bundle record: Patient/fictional-patient-001'
  Expect 'Bundle exploration: 1 of 4 visible fictional records opened'
  Press 'Bundle: Open next unexplored visible record'
  Expect 'Bundle record: Encounter/fictional-encounter-001'
  Expect 'Bundle exploration: 2 of 4 visible fictional records opened'
  Press 'Bundle: Reset session exploration'
  Expect 'Bundle exploration: 0 of 4 visible fictional records opened'
  Press 'Bundle: Open next unexplored visible record'
  Expect 'Bundle record: Patient/fictional-patient-001'
  Press 'Bundle: Next visible record'
  Expect 'Bundle record: Encounter/fictional-encounter-001'
  Press 'Bundle: Previous visible record'
  Expect 'Bundle record: Patient/fictional-patient-001'
  Press 'Bundle: Incoming Encounter/fictional-encounter-001 via subject'
  Expect 'Bundle record: Encounter/fictional-encounter-001'
  Press 'Bundle: Follow subject to Patient/fictional-patient-001'
  Expect 'Bundle record: Patient/fictional-patient-001'
  Expect 'Bundle: 2 of 24 navigation steps'
  Press 'Bundle: Back to previous resource'
  Expect 'Bundle record: Encounter/fictional-encounter-001'
  Press 'Bundle: Back to previous resource'
  Expect 'Bundle record: Patient/fictional-patient-001'
  Press 'Bundle: Patient fictional-patient-002'
  Expect 'Bundle: 4 of 8 fictional resources visible'
  Press 'Bundle: Type Observation'
  Expect 'Bundle: 2 of 8 fictional resources visible'
  Expect 'Bundle exploration: 0 of 2 visible fictional records opened'
  Press 'Bundle: Open next unexplored visible record'
  Expect 'Bundle record: Observation/fictional-observation-003'
  Press 'Bundle: Open next unexplored visible record'
  Expect 'Bundle record: Observation/fictional-observation-004'
  Expect 'Bundle exploration: 2 of 2 visible fictional records opened'
  if(Has 'Bundle: Open Observation/fictional-observation-001') {
    throw 'first_patient_observation_leaked_into_second_patient'
  }
  Press 'Bundle: Open Observation/fictional-observation-003'
  Expect 'Bundle record: Observation/fictional-observation-003'
  Press 'Bundle: Follow encounter to Encounter/fictional-encounter-002'
  Expect 'Bundle record: Encounter/fictional-encounter-002'
  Press 'Bundle: Back to previous resource'
  Expect 'Bundle record: Observation/fictional-observation-003'
  Press 'Bundle: All patients'
  Expect 'Bundle: 8 of 8 fictional resources visible'
  Press 'Bundle: Type Patient'
  Expect 'Bundle: 2 of 8 fictional resources visible'
  Press 'Bundle: Clear fictional records'
  Expect 'Native Rust Experiment'
  if(Has 'Bundle record: Observation/fictional-observation-003') {
    throw 'fictional_bundle_record_leaked_after_clear'
  }
  if($EmbeddedDemo){
    Write-Output 'WINDOWS_NOARG_ONE_CLICK_EMBEDDED_MULTIPATIENT_UIA_PASS_NONCLINICAL'
  }else{
    Write-Output 'WINDOWS_NATIVE_EIGHT_RECORD_TWO_PATIENT_STRUCTURAL_FHIR_BUNDLE_GROUP_GRAPH_UIA_PASS_NONCLINICAL'
  }
} catch {
  [Console]::Error.WriteLine('WINDOWS_NATIVE_MULTIPATIENT_STRUCTURAL_BUNDLE_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
} finally {
  if($process -and -not $process.HasExited){
    if(-not $process.CloseMainWindow() -or -not $process.WaitForExit(4500)){
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
