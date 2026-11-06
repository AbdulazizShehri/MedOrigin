# Owner Windows UIAutomation: keyboard-accessible local fictional-only JSON import.
# This test does not read real patient data, change clipboard or use network.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedExeSha256,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedFixtureSha256
)
$ErrorActionPreference='Stop'
$native=$null
try {
  if([Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA'){
    throw 'native_keyboard_test_requires_sta'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Split-Path -Leaf $exe) -cne 'medorigin-desktop-d2-native-egui.exe' -or
    (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedExeSha256){
    throw 'source_pinned_native_exe_refused'
  }
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\synthetic-multipatient-fhir-bundle.json')).Path
  if($ExpectedFixtureSha256 -ine '92004ddb54302dd70c899dc5ace1a88147e36d81d101f67616b9ee031365cd10' -or
     (Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $ExpectedFixtureSha256){
    throw 'reviewed_synthetic_fixture_sha_refused'
  }
  $item=Get-Item -LiteralPath $fixture
  if($item.Length -le 0 -or $item.Length -gt 32768 -or
    ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
    throw 'fictional_fixture_reparse_or_size_refused'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  Add-Type -AssemblyName System.Windows.Forms
  $native=Start-Process -FilePath $exe -PassThru
  if(-not $native){throw 'native_process_not_launched'}
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($try=0;$try -lt 70;$try++){
    foreach($candidate in $root.FindAll([System.Windows.Automation.TreeScope]::Children,
        [System.Windows.Automation.Condition]::TrueCondition)){
      try {
        if($candidate.Current.ProcessId -eq $native.Id -and
           $candidate.Current.Name -like 'MedOrigin Native Rust*' -and
           -not $candidate.Current.IsOffscreen){
          $window=$candidate;break
        }
      }catch{}
    }
    if($window){break}
    if($native.HasExited){throw 'native_process_exited_before_window'}
    Start-Sleep -Milliseconds 180
  }
  if(-not $window){throw 'source_pinned_native_window_not_found'}
  function Nodes {
    return @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition))
  }
  function Names {
    return @(Nodes|ForEach-Object{try{$_.Current.Name}catch{''}})
  }
  function Expect([string]$text) {
    for($i=0;$i -lt 60;$i++){
      if(@(Names|Where-Object {$_ -ceq $text -or $_ -like ('*'+$text+'*')}).Count -gt 0){return}
      Start-Sleep -Milliseconds 140
    }
    $safe=@(Names|Where-Object {
      $_ -like 'Local file refused:*' -or
      $_ -like 'Open refused:*' -or
      $_ -like 'Drop refused:*' -or
      $_ -like 'Local synthetic-only FHIR Bundle admitted*' -or
      $_ -like 'Native Rust Experiment*' -or
      $_ -like 'Fictional Multi-Patient Workspace*'
    })
    Write-Output ('SAFE_LOCAL_IMPORT_SCREEN_STATE='+($safe -join '; '))
    throw ('native_typed_path_ui_not_visible:'+ $text)
  }
  function Press([string]$buttonName) {
    for($i=0;$i -lt 50;$i++){
      $buttons=@(Nodes|Where-Object{
        try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and
          $_.Current.Name -ceq $buttonName -and $_.Current.IsEnabled}catch{$false}
      })
      if($buttons.Count -eq 1) {
        $pattern=[System.Windows.Automation.InvokePattern]$buttons[0].GetCurrentPattern(
          [System.Windows.Automation.InvokePattern]::Pattern)
        $pattern.Invoke()
        Start-Sleep -Milliseconds 280
        return
      }
      if($buttons.Count -gt 1){throw ('multiple_import_buttons:'+ $buttonName)}
      Start-Sleep -Milliseconds 140
    }
    throw ('import_button_not_found:'+ $buttonName)
  }
  Expect 'Local fictional JSON file path:'
  $edit=$null
  for($i=0;$i -lt 40;$i++){
    $edits=@(Nodes|Where-Object{
      try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit' -and
          $_.Current.IsEnabled}catch{$false}
    })
    if($edits.Count -eq 1){$edit=$edits[0];break}
    if($edits.Count -gt 1){throw 'native_path_entry_not_unique'}
    Start-Sleep -Milliseconds 100
  }
  if(-not $edit){throw 'native_local_path_entry_not_accessible'}
  # Real keyboard input, not a UIAutomation SetValue mutation. Some
  # accessibility adapters expose SetValue but do not route it to egui state.
  # Never use/replace the user's clipboard.
  if($fixture -notmatch '^[A-Za-z]:\\[A-Za-z0-9_.\\-]+$'){
    throw 'reviewed_source_path_not_keyboard_safe'
  }
  $edit.SetFocus()
  Start-Sleep -Milliseconds 200
  [System.Windows.Forms.SendKeys]::SendWait('^a')
  [System.Windows.Forms.SendKeys]::SendWait('"' + $fixture + '"')
  Start-Sleep -Milliseconds 350
  Write-Output 'FICTIONAL_LOCAL_PATH_ENTRY_UIA_METHOD=REAL_KEYBOARD_NOT_CLIPBOARD'
  Press 'Open local fictional JSON (NO PHI)'
  Expect 'Fictional Multi-Patient Workspace'
  Expect 'Bundle: Opened local synthetic-only JSON (no PHI, session-only)'
  Expect '8 imaginary source-only records across 2 fictional patients'
  Press 'Bundle: Clear fictional records'
  Expect 'Local fictional JSON file path:'
  $edits=@(Nodes|Where-Object{
    try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit' -and
      $_.Current.IsEnabled}catch{$false}
  })
  if($edits.Count -ne 1){throw 'typed_path_edit_not_unique_after_clear'}
  try {
    $current=[System.Windows.Automation.ValuePattern]$edits[0].GetCurrentPattern(
      [System.Windows.Automation.ValuePattern]::Pattern)
    if($current.Current.Value -ne ''){throw 'typed_local_path_persisted_after_clear'}
  }catch [System.InvalidCastException]{
    Write-Output 'PATH_CLEAR_MEMORY_COVERED_BY_RUST_TEST_UIA_VALUE_NOT_EXPOSED'
  }
  Write-Output 'OWNER_WINDOWS_NATIVE_TYPED_SYNTHETIC_FILE_PATH_UIA_PASS_NONCLINICAL'
}catch{
  [Console]::Error.WriteLine('MEDORIGIN_TYPED_LOCAL_FILE_UIA_NO_GO:'+ $_.Exception.Message)
  exit 2
}finally{
  if($native){
    if(-not $native.HasExited){
      Stop-Process -Id $native.Id -Force -ErrorAction SilentlyContinue
    }
    # A test process may remain present briefly after Stop-Process.
    # The installer lifecycle requires it to be fully terminated before removal.
    if(-not $native.WaitForExit(15000)){
      throw 'typed_path_native_test_process_cleanup_timed_out'
    }
  }
}