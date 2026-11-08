# Actual Windows native UIA for one redacted, source-run Core #963 fictional encrypted receipt.
# Never loads actual patient records: only fixed SHA-qualified synthetic QA report.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedExeSha256,
  [string]$LiveReceiptPath = '',
  [string]$SessionFramePath = ''
)
$ErrorActionPreference='Stop'
$process=$null
try {
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    throw 'not_reviewed_native_executable'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedExeSha256) {
    throw 'changed_native_binary'
  }
  $receipt=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\core963-real-encrypted-fictional-file-batch-redacted.json')).Path
  $item=Get-Item -LiteralPath $receipt
  if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    $item.Length -ne 1341 -or
    (Get-FileHash -LiteralPath $receipt -Algorithm SHA256).Hash -ine
      '34beba4dd887ab5e26fb8ceaf91d06f85a6ebaca349359aa0f9ecccb612d2292') {
    throw 'unreviewed_fictional_core_receipt'
  }
  if($LiveReceiptPath){
    # One-command Core source runs may supply only the exact SAME reviewed,
    # redacted 1,341-byte fictional QA receipt, never arbitrary FHIR data.
    $live=(Resolve-Path -LiteralPath $LiveReceiptPath -ErrorAction Stop).Path
    $liveItem=Get-Item -LiteralPath $live -ErrorAction Stop
    if($liveItem.PSIsContainer -or
       ($liveItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $liveItem.Length -ne 1341 -or
       (Get-FileHash -LiteralPath $live -Algorithm SHA256).Hash -ine
         '34beba4dd887ab5e26fb8ceaf91d06f85a6ebaca349359aa0f9ecccb612d2292'){
      throw 'live_core_source_receipt_not_canonical'
    }
    $receipt=$live
  }
  $bytes=[IO.File]::ReadAllBytes($receipt)
  $launchBytes=$bytes
  $flag='--synthetic-core-file-batch-receipt-stdin'
  if($SessionFramePath){
    if(-not $LiveReceiptPath){throw 'session_frame_requires_live_source_core_receipt'}
    $frameItem=Get-Item -LiteralPath $SessionFramePath -ErrorAction Stop
    if($frameItem.PSIsContainer -or
       ($frameItem.Attributes -band [IO.FileAttributes]::ReparsePoint)){
      throw 'unreviewed_core_session_frame_path'
    }
    $frameBytes=[IO.File]::ReadAllBytes($frameItem.FullName)
    $domain=[Text.Encoding]::ASCII.GetBytes("MedOrigin-D2-FICTIONAL-CORE-BATCH-V1" + [char]0)
    $headerLength=$domain.Length+16+32
    if($frameBytes.Length -ne $bytes.Length+$headerLength -or
       $frameBytes.Length -gt 4096+$headerLength){
      throw 'core963_session_frame_size_refused'
    }
    for($i=0;$i -lt $domain.Length;$i++){
      if($frameBytes[$i] -ne $domain[$i]){throw 'core963_session_domain_refused'}
    }
    $payload=[byte[]]$frameBytes[$headerLength..($frameBytes.Length-1)]
    if([Convert]::ToBase64String($payload) -cne [Convert]::ToBase64String($bytes)){
      throw 'core963_session_payload_not_actual_live_source'
    }
    if($env:MEDORIGIN_D2_FICTIONAL_SESSION_KEY -notmatch '^[0-9a-f]{64}$' -or
       $env:MEDORIGIN_D2_FICTIONAL_SESSION_NONCE -notmatch '^[0-9a-f]{32}$'){
      throw 'core963_session_key_or_nonce_missing'
    }
    # Receiver independently verifies the secret-bound HMAC.
    $launchBytes=$frameBytes
    $flag='--synthetic-core-file-batch-session-stdin'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments=$flag
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()){throw 'native_launch_failed'}
  $process.StandardInput.BaseStream.Write($launchBytes,0,$launchBytes.Length)
  $process.StandardInput.Close()
  $desktop=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 85;$i++){
    $wins=@($desktop.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    ) | Where-Object {
      try{$_.Current.ProcessId -eq $process.Id -and
        $_.Current.Name -like 'MedOrigin Native Rust*' -and -not $_.Current.IsOffscreen
      }catch{$false}
    })
    if($wins.Count -eq 1){$window=$wins[0];break}
    if($wins.Count -gt 1){throw 'multiple_native_windows'}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window){throw 'source_receipt_native_window_absent'}
  function Nodes {
    return @($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition
    ))
  }
  function Names {
    return @(Nodes | ForEach-Object {try{$_.Current.Name}catch{''}})
  }
  function Expect([string]$wanted) {
    for($i=0;$i -lt 28;$i++){
      if(@(Names | Where-Object {$_ -like ('*'+$wanted+'*')}).Count -gt 0){return}
      Start-Sleep -Milliseconds 140
    }
    throw ('Core D2 source UIA missing: '+$wanted)
  }
  function Press([string]$wanted) {
    for($i=0;$i -lt 28;$i++){
      $matches=@(Nodes | Where-Object {
        try{$_.Current.Name -ceq $wanted -and
            $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button
        }catch{$false}
      })
      if($matches.Count -eq 1){
        $pattern=$matches[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $pattern.Invoke()
        return
      }
      if($matches.Count -gt 1){throw ('duplicate button: '+$wanted)}
      Start-Sleep -Milliseconds 140
    }
    throw ('Core D2 button missing: '+$wanted)
  }
  Expect 'Core encrypted fictional file batch'
  Expect 'REDACTED RECEIPT ONLY'
  Expect 'Core: 2 independent fictional imports; 6 total resources; 4 reconstructed timeline events'
  Expect 'Source-shaped Core v1 report; transport sender and freshness NOT authenticated'
  Expect 'Core batch: Import 1 - 3 source resources, 2 verified timeline events'
  Expect 'Core batch: Import 2 - 3 source resources, 2 verified timeline events'
  Expect 'Core batch exploration: 0 of 2 visible fictional imports opened'
  Expect 'Core batch: No fictional import opened this session'
  Press 'Core batch: Open next unexplored import'
  Expect 'Core batch: Selected import 1'
  Expect 'Core batch exploration: 1 of 2 visible fictional imports opened'
  Expect 'Core batch: Selected source resources: 3'
  # User-visible redacted side-by-side counts, without opening import 2.
  Press 'Core batch: Compare with import 2'
  Expect 'Core batch: Comparing import 1 with import 2'
  Expect 'Core batch: Resource totals: 3 versus 3; difference +0'
  Expect 'Core batch: Event totals: 2 versus 2; difference +0'
  Press 'Core batch: Clear source comparison'
  Start-Sleep -Milliseconds 230
  if(@(Names | Where-Object {$_ -like '*Core batch: Comparing import 1 with import 2*'}).Count -ne 0){
    throw 'source_comparison_not_cleared'
  }
  Press 'Core batch: Compare with import 2'
  Expect 'Core batch: Comparing import 1 with import 2'
  # The newly integrated native session-only facet must not expose unopened
  # fictional imports or mislabel session navigation as clinical review.
  Press 'Core batch: Only imports opened this session'
  Expect 'Core batch: Show opened and unopened imports'
  Expect 'Core batch exploration: 1 of 1 visible fictional imports opened'
  Start-Sleep -Milliseconds 230
  if(@(Names | Where-Object {
    $_ -like '*Core batch: Comparing import 1 with import 2*' -or
    $_ -ceq 'Core batch: Compare with import 2'
  }).Count -ne 0){
    throw 'hidden_import_comparison_exposed_after_opened_filter'
  }
  if(@(Names | Where-Object {
    $_ -ceq 'Core batch: Open import 2' -or
    $_ -ceq 'Core batch: Open next unexplored import'
  }).Count -ne 0){
    throw 'opened_only_facet_reexposed_unopened_import'
  }
  Press 'Core batch: Only imports with activity'
  Expect 'Core batch: Show all imports'
  Expect 'Core batch exploration: 1 of 1 visible fictional imports opened'
  Press 'Core batch: Show all imports'
  Press 'Core batch: Show opened and unopened imports'
  Expect 'Core batch exploration: 1 of 2 visible fictional imports opened'
  Press 'Core batch: Next visible import'
  Expect 'Core batch: Selected import 2'
  Expect 'Core batch exploration: 2 of 2 visible fictional imports opened'
  Press 'Core batch: Previous visible import'
  Expect 'Core batch: Selected import 1'
  # Product first/last visible jump controls must stay within the real
  # source-scoped session filter, not hidden fictional imports.
  Press 'Core batch: Last visible import'
  Expect 'Core batch: Selected import 2'
  Press 'Core batch: First visible import'
  Expect 'Core batch: Selected import 1'
  Expect 'Keyboard in this fictional worklist: Left/Right'
  Press 'Core batch: Only imports with activity'
  Expect 'Core batch: Show all imports'
  Expect 'Core batch exploration: 2 of 2 visible fictional imports opened'
  Press 'Core batch: Reset session exploration'
  Expect 'Core batch: No fictional import opened this session'
  Expect 'Core batch exploration: 0 of 2 visible fictional imports opened'
  Press 'Core batch: Open import 2'
  Expect 'Core batch: Selected import 2'
  if(@(Names | Where-Object {$_ -like '*fictional-patient-001*' -or $_ -like '*INVENTED_PRIVATE_NAME*'}).Count -gt 0){
    throw 'native_receipt_patient_identity_visible'
  }
  Press 'Core batch: Clear redacted receipt'
  Expect 'Native Rust Experiment'
  if(@(Names | Where-Object {$_ -like '*Core: 2 independent fictional imports*'}).Count -gt 0){
    throw 'native_receipt_not_cleared'
  }
  Write-Output 'WINDOWS_REAL_CORE963_TWO_FILES_ENCRYPTED_REOPEN_REDACTED_D2_NATIVE_UIA_PASS_NONCLINICAL'
  Write-Output 'D2_CORE_BATCH_OPENED_ONLY_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL'
  Write-Output 'D2_CORE_BATCH_VISIBLE_BOUNDARY_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL'
  Write-Output 'D2_CORE_BATCH_REDACTED_SIDE_BY_SIDE_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL'
} catch {
  [Console]::Error.WriteLine('WINDOWS_REAL_CORE963_REDACTED_BATCH_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
} finally {
  if($process -and -not $process.HasExited){
    if(-not $process.CloseMainWindow() -or -not $process.WaitForExit(4500)){
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
