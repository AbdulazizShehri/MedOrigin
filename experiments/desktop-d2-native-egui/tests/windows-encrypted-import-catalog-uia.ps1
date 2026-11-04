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
  [Console]::Error.WriteLine('D2_ENCRYPTED_IMPORT_HISTORY_WINDOWS_UIA_NO_GO: '+$reason)
  exit 1
}
$reportHash='cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623'
try {
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    Refuse 'unapproved_native_executable_name'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    Refuse 'native_executable_binary_changed'
  }
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\encrypted-import-catalog-demo.json')).Path
  if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $reportHash) {
    Refuse 'compiled_encrypted_import_history_fixture_changed'
  }
  $source=$fixture
  if($LiveReceiptPath) {
    $source=(Resolve-Path -LiteralPath $LiveReceiptPath -ErrorAction Stop).Path
    $entry=Get-Item -LiteralPath $source -ErrorAction Stop
    if($entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $entry.Length -ne 799 -or
       (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ine $reportHash) {
      Refuse 'real_core_encrypted_import_history_report_not_canonical'
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
  $info.Arguments='--synthetic-encrypted-import-history-stdin'
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
  Expect 'Verified encrypted fictional import count: 2'
  Expect 'Total fictional resources across imports: 4'
  Expect 'Verified audit events across imports: 3'
  Expect 'Ephemeral encrypted catalog store removed: true'
  Expect ('Source-approved encrypted catalog SHA-256: '+$reportHash)
  Expect 'Sender/freshness NOT authenticated'
  Expect 'FHIR R4 NOT validated'
  Press 'Open encrypted fictional import 1 (3 resources)'
  Expect 'Selected encrypted fictional import: 1'
  Expect 'Fictional resources in selected import: 3'
  Expect 'Verified import audit sequence: 1'
  Expect 'Original fictional Bundle source SHA-256: 7d7cc615ea74886b2f2ad0d14005ed3151b265159daafac1a52a08b3165ba450'
  Press 'Open encrypted fictional import 2 (1 resources)'
  Expect 'Selected encrypted fictional import: 2'
  Expect 'Fictional resources in selected import: 1'
  Expect 'Verified import audit sequence: 3'
  Expect 'Original fictional Bundle source SHA-256: f6359af7f22fe50e63f771c80eef91b1fccbd3ec706c057f76aa9a4551f225b8'
  Press 'Back to encrypted fictional import list'
  if(Has 'Selected encrypted fictional import: 2'){
    throw 'encrypted_history_back_retained_selected_import'
  }
  Press 'Clear encrypted import history'
  if(Has 'Verified encrypted fictional import count: 2'){
    throw 'encrypted_history_clear_retained_source_details'
  }
  if($process.HasExited){throw 'native_GUI_exited_before_historical_catalog_UIA_acceptance'}
  Write-Output 'WINDOWS_REAL_ENCRYPTED_CORE_TWO_HISTORICAL_IMPORTS_NATIVE_UIA_PASS_NOT_CLINICAL'
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
