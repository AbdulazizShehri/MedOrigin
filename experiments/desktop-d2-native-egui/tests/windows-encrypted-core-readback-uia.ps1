# Genuine native Windows UIAutomation on exact synthetic Core encrypted
# readback projection. No PHI/clinical authorization, no embedded worker.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256,
  [string]$LiveReceiptPath = ''
)
$ErrorActionPreference='Stop'
function Refuse([string]$reason) {
  [Console]::Error.WriteLine('D2_ENCRYPTED_READBACK_WINDOWS_UIA_NO_GO: '+$reason)
  exit 1
}
$reportHash='c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49'
try {
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    Refuse 'unapproved_native_executable_name'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    Refuse 'native_executable_binary_changed'
  }
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\encrypted-readback-projection.json')).Path
  if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $reportHash) {
    Refuse 'compiled_encrypted_readback_fixture_changed'
  }
  $source=$fixture
  if($LiveReceiptPath) {
    $source=(Resolve-Path -LiteralPath $LiveReceiptPath -ErrorAction Stop).Path
    $entry=Get-Item -LiteralPath $source -ErrorAction Stop
    if($entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $entry.Length -ne 1164 -or
       (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $reportHash) {
      Refuse 'real_core_encrypted_readback_report_not_canonical'
    }
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
} catch {
  Refuse 'native_executable_or_report_qualified_source_missing'
}
$process=$null
try {
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments='--synthetic-encrypted-readback-stdin'
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()) {throw 'native_executable_start_refused'}
  $bytes=[IO.File]::ReadAllBytes($source)
  $process.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
  $process.StandardInput.Close()
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 65;$i++) {
    $wins=@($root.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    ) | Where-Object {
      try {
        $_.Current.ProcessId -eq $process.Id -and
        $_.Current.Name -like 'MedOrigin Native Rust*' -and
        -not $_.Current.IsOffscreen
      } catch { $false }
    })
    if($wins.Count -eq 1) {$window=$wins[0];break}
    if($wins.Count -gt 1) {throw 'ambiguous_native_source_process_windows'}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window) {throw 'native_window_not_present'}
  function Nodes {
    return @($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition
    ))
  }
  function Names {
    return @(Nodes | ForEach-Object { try{$_.Current.Name}catch{''} })
  }
  function Has([string]$wanted) {
    return @(Names | Where-Object {$_ -like ('*'+$wanted+'*')}).Count -gt 0
  }
  function Expect([string]$wanted) {
    for($i=0;$i -lt 55;$i++) {
      if(Has $wanted) {return}
      Start-Sleep -Milliseconds 120
    }
    throw ('missing_actual_native_UIA_text: '+$wanted)
  }
  function Press([string]$wanted) {
    for($i=0;$i -lt 55;$i++) {
      $matches=@(Nodes|Where-Object{
        try {
          $_.Current.Name -eq $wanted -and
          $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and
          $_.Current.IsEnabled
        }catch{$false}
      })
      if($matches.Count -eq 1) {
        $button=$matches[0]
        try {
          $invoke=[System.Windows.Automation.InvokePattern]$button.GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
          )
          $invoke.Invoke()
        }catch {
          throw ('native_UIA_button_cannot_invoke: '+$wanted)
        }
        Start-Sleep -Milliseconds 250
        return
      }
      if($matches.Count -gt 1) {throw ('ambiguous_UIA_button: '+$wanted)}
      Start-Sleep -Milliseconds 130
    }
    throw ('native_UIA_button_missing: '+$wanted)
  }
  Expect 'Recovered fictional resource count: 3'
  Expect ('Encrypted readback SHA-256: '+$reportHash)
  Expect 'Audit chain verified: true'
  Expect 'Encrypted store reopened: true'
  Expect 'Ephemeral encrypted store removed: true'
  Expect 'Sender/freshness NOT authenticated'
  Expect 'Recovered fictional worklist: 3 of 3 source-derived resources visible'
  Press 'Filter recovered resource type: Patient'
  Expect 'Active recovered type: Patient'
  Expect 'Recovered fictional worklist: 1 of 3 source-derived resources visible'
  if(Has 'Open recovered fictional resource: Observation/fictional-observation-001') {
    throw 'filtered_core_observation_still_visible'
  }
  Press 'Filter recovered resource type: All'
  Expect 'Recovered fictional worklist: 3 of 3 source-derived resources visible'
  Press 'Open recovered fictional resource: Observation/fictional-observation-001'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Follow recovered fictional subject -> urn:uuid:00000000-0000-4000-8000-000000000002'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Follow recovered fictional encounter -> urn:uuid:00000000-0000-4000-8000-000000000003'
  Expect 'Recovered fictional record: Encounter/fictional-encounter-001'
  Press 'Follow recovered fictional subject -> urn:uuid:00000000-0000-4000-8000-000000000002'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Press 'Open recovered incoming Observation/fictional-observation-001 via subject'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Encounter/fictional-encounter-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Clear encrypted Core readback display'
  if(Has 'Recovered fictional record: Observation/fictional-observation-001'){
    throw 'fictional_encrypted_memory_readback_leaked_after_clear'
  }
  if($process.HasExited){throw 'native_GUI_exited_before_full_UIA_acceptance'}
  Write-Output 'WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL'
} catch {
  Refuse $_.Exception.Message
} finally {
  if($process -and -not $process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
  if($process){$process.Dispose()}
}
if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
  Refuse 'native_executable_changed_after_run'
}
exit 0
