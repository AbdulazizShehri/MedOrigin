# Actual Windows native UIA for one redacted, source-run Core #963 fictional encrypted receipt.
# Never loads actual patient records: only fixed SHA-qualified synthetic QA report.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedExeSha256,
  [Parameter(Mandatory=$true)][string]$LiveReceiptPath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedReceiptSha256,
  [Parameter(Mandatory=$true)][string]$SessionFramePath
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
  $receipt=(Resolve-Path -LiteralPath $LiveReceiptPath -ErrorAction Stop).Path
  $item=Get-Item -LiteralPath $receipt -ErrorAction Stop
  if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
     $item.Length -lt 1400 -or $item.Length -gt 4096 -or
     (Get-FileHash -LiteralPath $receipt -Algorithm SHA256).Hash -ine $ExpectedReceiptSha256) {
    throw 'core971_unreviewed_live_official_r4_receipt'
  }
  # The launcher already verified a clean, exact Core #971 source, pinned
  # official ZIP digest, canonical redacted receipt and exit-2 semantics.
  # The actual Rust GUI independently fails closed on forged/extra fields.
  $raw=[IO.File]::ReadAllBytes($receipt)
  $text=[Text.Encoding]::UTF8.GetString($raw)
  if($text -notmatch 'official_r4_structural_gate' -or
     $text -match 'urn:uuid:|fictional-patient|INVENTED_PRIVATE_NAME|imaginary-file-') {
    throw 'core971_live_receipt_missing_r4_or_contains_identity'
  }
  # The source runner supplies the canonical true Core971 receipt in a
  # fresh per-launch HMAC-bound session. Never downgrade to legacy stdin.
  $frameItem=Get-Item -LiteralPath $SessionFramePath -ErrorAction Stop
  if($frameItem.PSIsContainer -or
     ($frameItem.Attributes -band [IO.FileAttributes]::ReparsePoint)){
    throw 'core971_session_frame_not_reviewed'
  }
  $frameBytes=[IO.File]::ReadAllBytes($frameItem.FullName)
  $domain=[Text.Encoding]::ASCII.GetBytes("MedOrigin-D2-FICTIONAL-CORE-BATCH-V1" + [char]0)
  $headerLength=$domain.Length+16+32
  if($frameBytes.Length -ne $raw.Length+$headerLength -or
     $frameBytes.Length -gt 4096+$headerLength){
    throw 'core971_session_frame_size_refused'
  }
  for($i=0;$i -lt $domain.Length;$i++){
    if($frameBytes[$i] -ne $domain[$i]){throw 'core971_session_domain_refused'}
  }
  $sourceBytes=[byte[]]$frameBytes[$headerLength..($frameBytes.Length-1)]
  if([Convert]::ToBase64String($sourceBytes) -cne [Convert]::ToBase64String($raw)){
    throw 'core971_session_payload_not_actual_live_source'
  }
  if($env:MEDORIGIN_D2_FICTIONAL_SESSION_KEY -notmatch '^[0-9a-f]{64}$' -or
     $env:MEDORIGIN_D2_FICTIONAL_SESSION_NONCE -notmatch '^[0-9a-f]{32}$'){
    throw 'core971_session_key_or_nonce_missing'
  }
  # Native Rust performs independent HMAC and nonce verification.
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments='--synthetic-core-file-batch-session-stdin'
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()){throw 'native_launch_failed'}
  $process.StandardInput.BaseStream.Write($frameBytes,0,$frameBytes.Length)
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
  Expect 'Official R4: 2 of 2 invented files structurally assessed (NOT FHIR validated)'
  Expect 'Offline official HL7 R4 v4.0.1 JSON Schema structure-only preflight was reported BEFORE the ephemeral encrypted import.'
  Expect 'Source-shaped Core v1 report; transport sender and freshness NOT authenticated'
  Expect 'Core batch: Import 1 - 3 source resources, 2 verified timeline events'
  Expect 'Core batch: Import 2 - 3 source resources, 2 verified timeline events'
  if(@(Names | Where-Object {$_ -like '*fictional-patient-001*' -or $_ -like '*INVENTED_PRIVATE_NAME*'}).Count -gt 0){
    throw 'native_receipt_patient_identity_visible'
  }
  Expect 'Core batch exploration: 0 of 2 visible fictional imports opened'
  Expect 'Core batch: No fictional import opened this session'
  Press 'Core batch: Open next unexplored import'
  Expect 'Core batch: Selected import 1'
  Expect 'Core batch: Import 1 R4 structure: source-reported checked, NOT FHIR validated'
  Press 'Core batch: Next visible import'
  Expect 'Core batch: Selected import 2'
  Expect 'Core batch: Import 2 R4 structure: source-reported checked, NOT FHIR validated'
  Press 'Core batch: Only imports with activity'
  Expect 'Core batch: Show all imports'
  Press 'Core batch: Reset session exploration'
  Expect 'Core batch: No fictional import opened this session'
  Expect 'Official R4: 2 of 2 invented files structurally assessed (NOT FHIR validated)'
  Press 'Core batch: Clear redacted receipt'
  Expect 'Native Rust Experiment'
  if(@(Names | Where-Object {$_ -like '*Core: 2 independent fictional imports*'}).Count -gt 0){
    throw 'native_receipt_not_cleared'
  }
  Write-Output 'WINDOWS_CORE971_OFFICIAL_R4_STRUCTURAL_REDACTED_NATIVE_UIA_PASS_NONCLINICAL'
} catch {
  [Console]::Error.WriteLine('WINDOWS_CORE971_OFFICIAL_R4_NATIVE_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
} finally {
  if($process -and -not $process.HasExited){
    if(-not $process.CloseMainWindow() -or -not $process.WaitForExit(4500)){
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
