# Genuine native Windows UIAutomation on exact synthetic Core encrypted
# readback projection. No PHI/clinical authorization, no embedded worker.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256,
  [string]$LiveReceiptPath = '',
  [string]$SessionFramePath = '',
  [string]$PersistentQaReceiptPath = '',
  [switch]$FocusedStartup
)
$ErrorActionPreference='Stop'
function Refuse([string]$reason) {
  [Console]::Error.WriteLine('D2_ENCRYPTED_READBACK_WINDOWS_UIA_NO_GO: '+$reason)
  exit 1
}
$reportHash='c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49'
$persistentHash='3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243'
if($PersistentQaReceiptPath -and $LiveReceiptPath) {
  Refuse 'two_different_fictional_receipts_refused'
}
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
  if($PersistentQaReceiptPath) {
    $persistentFixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\encrypted-persistent-readback-projection.json')).Path
    if((Get-FileHash -LiteralPath $persistentFixture -Algorithm SHA256).Hash -ine $persistentHash) {
      Refuse 'compiled_persistent_fictional_readback_modified'
    }
    $source=(Resolve-Path -LiteralPath $PersistentQaReceiptPath -ErrorAction Stop).Path
    $entry=Get-Item -LiteralPath $source -ErrorAction Stop
    if($entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $entry.Length -ne 1215 -or
       (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $persistentHash) {
      Refuse 'real_persistent_fictional_core_receipt_not_canonical'
    }
    $reportHash=$persistentHash
  }
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
  $info.Arguments=if($FocusedStartup){'--synthetic-encrypted-readback-focused-stdin'}else{'--synthetic-encrypted-readback-stdin'}
  if($SessionFramePath) {
    if((-not $LiveReceiptPath -and -not $PersistentQaReceiptPath) -or
       $env:MEDORIGIN_D2_FICTIONAL_SESSION_NONCE -cnotmatch '^[0-9a-f]{32}$' -or
       $env:MEDORIGIN_D2_FICTIONAL_SESSION_KEY -cnotmatch '^[0-9a-f]{64}$') {
      Refuse 'session_environment_or_original_source_missing'
    }
    $frame=(Resolve-Path -LiteralPath $SessionFramePath -ErrorAction Stop).Path
    $entry=Get-Item -LiteralPath $frame -ErrorAction Stop
    if($entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $entry.Length -le 1164 -or $entry.Length -gt 2048) {
      Refuse 'session_frame_file_bounds_refused'
    }
    $info.Arguments=if($FocusedStartup){'--synthetic-encrypted-readback-session-focused-stdin'}else{'--synthetic-encrypted-readback-session-stdin'}
  }
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()) {throw 'native_executable_start_refused'}
  $bytes=[IO.File]::ReadAllBytes($source)
  if($SessionFramePath) {
    $frameBytes=[IO.File]::ReadAllBytes($frame)
    $size=if($PersistentQaReceiptPath){1215}else{1164}
    $tail=New-Object byte[] $size
    [Array]::Copy($frameBytes,$frameBytes.Length-$size,$tail,0,$size)
    if([Convert]::ToBase64String($bytes) -cne [Convert]::ToBase64String($tail)) {
      throw 'session_frame_core_projection_suffix_mismatch'
    }
    $bytes=$frameBytes
  }
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
  if($FocusedStartup) {
    Expect 'MedOrigin focused Workspace'
    Expect 'Source-verified resource browser'
    Expect 'Focus: 3 of 3 source-verified fictional resources visible'
    if(Has 'Workspace home: fictional Core source only') {
      throw 'focused_startup_unexpectedly_started_developer_mode'
    }
    Press 'Focus: Return to developer evidence'
  }
  Expect 'Recovered fictional resource count: 3'
  Expect ('Encrypted readback SHA-256: '+$reportHash)
  Expect 'Audit chain verified: true'
  Expect 'Encrypted store reopened: true'
  if($PersistentQaReceiptPath) {
    Expect 'Ephemeral encrypted store removed: false'
    Expect 'Persistent fictional QA vault reopened: true'
  } else {
    Expect 'Ephemeral encrypted store removed: true'
    Expect 'Persistent fictional QA vault reopened: false'
  }
  Expect 'Sender/freshness NOT authenticated'
  Expect 'Workspace home: fictional Core source only'
  Expect 'Verified fictional resources: 3 (read-only)'
  if($PersistentQaReceiptPath) {
    Expect 'Workspace source: Cold-reopened persistent QA encrypted test vault'
  } else {
    Expect 'Workspace source: Reopened ephemeral encrypted test vault (removed after QA)'
  }
  Press 'Open focused fictional Workspace'
  Expect 'MedOrigin focused Workspace'
  Expect '3 fictional identities | encrypted reopen: true | audit: true'
  Expect 'Source-verified resource browser'
  Expect 'Focus: 3 of 3 source-verified fictional resources visible'
  Press 'Focus: Type Patient'
  Expect 'Focus: 1 of 3 source-verified fictional resources visible'
  if(Has 'Focus: Inspect Observation/fictional-observation-001') {
    throw 'focused_type_patient_still_exposes_observation'
  }
  Press 'Focus: Find Encounter'
  Expect 'Focus: 0 of 3 source-verified fictional resources visible'
  Expect 'No fictional resources match the chosen type and identity keyword.'
  Press 'Focus: Type Encounter'
  Expect 'Focus: 1 of 3 source-verified fictional resources visible'
  Press 'Focus: Inspect Encounter/fictional-encounter-001'
  Expect 'Focused fictional record: Encounter/fictional-encounter-001'
  Press 'Focus: Find All'
  Expect 'Focus: 1 of 3 source-verified fictional resources visible'
  Press 'Focus: Type All'
  Expect 'Focus: 3 of 3 source-verified fictional resources visible'
  Press 'Focus: Find Observation'
  Expect 'Focus: 1 of 3 source-verified fictional resources visible'
  Press 'Focus: Inspect Observation/fictional-observation-001'
  Expect 'Focused fictional record: Observation/fictional-observation-001'
  Press 'Focus: Find All'
  Expect 'Focus: 3 of 3 source-verified fictional resources visible'
  if($PersistentQaReceiptPath) {
    Expect 'Source: Cold-reopened persistent DPAPI QA test vault'
  } else {
    Expect 'Source: Ephemeral encrypted QA test vault, removed after readback'
  }
  Expect 'Fictional walkthrough: 0 of 3 visited this session'
  Press 'Focus: Open Patient'
  Expect 'Focused fictional record: Patient/fictional-patient-001'
  Press 'Focus: Open Encounter'
  Expect 'Focused fictional record: Encounter/fictional-encounter-001'
  Press 'Focus: Back to patient'
  Expect 'Focused fictional record: Patient/fictional-patient-001'
  Press 'Focus: Open Observation'
  Expect 'Focused fictional record: Observation/fictional-observation-001'
  Press 'Focus: Mark visited (demo only)'
  Expect 'Fictional walkthrough: 1 of 3 visited this session'
  Press 'Focus: Reset visits'
  Expect 'Fictional walkthrough: 0 of 3 visited this session'
  Press 'Focus: Return to developer evidence'
  Expect 'Workspace home: fictional Core source only'
  Expect 'Fictional session walkthrough: 0 of 3 identities visited'
  Press 'Open next unvisited fictional identity'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Expect 'Fictional walkthrough status: not visited'
  Press 'Mark fictional identity visited (demo only)'
  Expect 'Fictional session walkthrough: 1 of 3 identities visited'
  Expect 'Fictional walkthrough status: visited this session'
  Press 'Open next unvisited fictional identity'
  Expect 'Recovered fictional record: Encounter/fictional-encounter-001'
  Press 'Mark fictional identity visited (demo only)'
  Expect 'Fictional session walkthrough: 2 of 3 identities visited'
  Press 'Open next unvisited fictional identity'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Mark fictional identity visited (demo only)'
  Expect 'Fictional session walkthrough: 3 of 3 identities visited'
  Press 'Open next unvisited fictional identity'
  Expect 'All three fictional walkthrough steps complete (session only)'
  Press 'Reset fictional walkthrough (session only)'
  Expect 'Fictional session walkthrough: 0 of 3 identities visited'
  Press 'Open workspace home: fictional patient chart'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Expect 'Recovered fictional worklist: 3 of 3 source-derived resources visible'
  Press 'Open recovered fictional patient chart'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Expect 'Fictional patient chart: source-verified relationships'
  Expect 'Associated fictional resources: 1 Encounter, 1 Observation'
  Expect 'No clinical chronology, medications, diagnoses or outcomes are available.'
  Press 'Open patient chart member: Encounter/fictional-encounter-001'
  Expect 'Recovered fictional record: Encounter/fictional-encounter-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Press 'Open patient chart member: Observation/fictional-observation-001'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Press 'Back to previous recovered fictional record'
  Expect 'Recovered fictional record: Patient/fictional-patient-001'
  Press 'Search recovered source: Patient'
  Expect 'Active recovered search: patient'
  Expect 'Recovered fictional worklist: 1 of 3 source-derived resources visible'
  if(Has 'Open recovered fictional resource: Observation/fictional-observation-001') {
    throw 'search_filtered_core_observation_still_visible'
  }
  Press 'Clear recovered search'
  Expect 'Active recovered search: All fictional IDs'
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
  Expect 'Recovered fictional relationship inspector'
  Expect 'Verified fictional references: 0 outgoing, 2 incoming'
  Expect 'Recovered fictional navigation trail: 2 previous verified steps'
  Press 'Jump recovered history step 1: Observation/fictional-observation-001'
  Expect 'Recovered fictional record: Observation/fictional-observation-001'
  Expect 'Verified fictional references: 2 outgoing, 0 incoming'
  if(Has 'Jump recovered history step 2: Encounter/fictional-encounter-001') {
    throw 'stale_source_breadcrumb_visible_after_history_jump'
  }
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
