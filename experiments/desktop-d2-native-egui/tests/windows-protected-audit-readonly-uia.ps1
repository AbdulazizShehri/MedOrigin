# Physical Windows egui UIAutomation from actual Core #981 fictional protected audit.
# Strict redacted verify-only HMAC frame. No key create/forget, patient or PHI.
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
    throw 'unreviewed_native_name'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedExeSha256){
    throw 'changed_native_exe'
  }
  $receipt=Get-Item -LiteralPath $LiveReceiptPath -ErrorAction Stop
  $frame=Get-Item -LiteralPath $SessionFramePath -ErrorAction Stop
  if($receipt.PSIsContainer -or $frame.PSIsContainer -or
     ($receipt.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
     ($frame.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
     $receipt.Length -lt 100 -or $receipt.Length -gt 1024 -or
     (Get-FileHash -LiteralPath $receipt.FullName -Algorithm SHA256).Hash -ine $ExpectedReceiptSha256){
    throw 'unreviewed_redacted_core_receipt'
  }
  $raw=[IO.File]::ReadAllBytes($receipt.FullName)
  $text=[Text.Encoding]::UTF8.GetString($raw)
  if($text -notmatch '"operation":"verify"' -or
     $text -notmatch '"verified_audit_events":1' -or
     $text -notmatch '"anchor_matched":true' -or
     $text -match '"operation":"forget"|"patient_name"|"patient_id"|"source_path"|urn:uuid:'){
    throw 'invalid_core_audit_source_claim'
  }
  $bytes=[IO.File]::ReadAllBytes($frame.FullName)
  $domain=[Text.Encoding]::ASCII.GetBytes("MedOrigin-D2-FICTIONAL-PROTECTED-AUDIT-V1"+[char]0)
  $header=$domain.Length+16+32
  if($bytes.Length -ne $raw.Length+$header -or $bytes.Length -gt 1024+$header){
    throw 'audit_frame_length_refused'
  }
  for($i=0;$i -lt $domain.Length;$i++){
    if($bytes[$i] -ne $domain[$i]){throw 'audit_frame_domain_refused'}
  }
  $payload=[byte[]]$bytes[$header..($bytes.Length-1)]
  if([Convert]::ToBase64String($payload) -cne [Convert]::ToBase64String($raw)){
    throw 'audit_frame_not_live_core_receipt'
  }
  if($env:MEDORIGIN_D2_FICTIONAL_SESSION_KEY -notmatch '^[0-9a-f]{64}$' -or
     $env:MEDORIGIN_D2_FICTIONAL_SESSION_NONCE -notmatch '^[0-9a-f]{32}$'){
    throw 'audit_session_env_missing'
  }
  # Native Rust *independently* verifies nonce and HMAC before parsing source.
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments='--synthetic-protected-audit-session-stdin'
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()){throw 'audit_gui_start_failed'}
  $process.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
  $process.StandardInput.Close()
  $desktop=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 85;$i++){
    $matches=@($desktop.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    ) | Where-Object {
      try{$_.Current.ProcessId -eq $process.Id -and
          $_.Current.Name -like 'MedOrigin Native Rust*' -and
          -not $_.Current.IsOffscreen}catch{$false}
    })
    if($matches.Count -eq 1){$window=$matches[0];break}
    if($matches.Count -gt 1){throw 'multiple_native_windows'}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window){throw 'native_audit_window_missing'}
  function Nodes {
    return @($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition
    ))
  }
  function Names {
    return @(Nodes | ForEach-Object {try{$_.Current.Name}catch{''}})
  }
  function Expect([string]$needle) {
    for($i=0;$i -lt 28;$i++){
      if(@(Names | Where-Object {$_ -like ('*'+$needle+'*')}).Count -gt 0){return}
      Start-Sleep -Milliseconds 140
    }
    throw 'protected_audit_gui_control_missing'
  }
  function Press([string]$label) {
    for($i=0;$i -lt 28;$i++){
      $buttons=@(Nodes | Where-Object {
        try{$_.Current.Name -ceq $label -and
            $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button
        }catch{$false}
      })
      if($buttons.Count -eq 1){
        $buttons[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        return
      }
      if($buttons.Count -gt 1){throw 'duplicate_audit_button'}
      Start-Sleep -Milliseconds 140
    }
    throw 'protected_audit_clear_button_missing'
  }
  Expect 'Protected fictional Workspace status'
  Expect 'Windows Credential Manager-backed audit verification (DEVELOPER QA ONLY)'
  Expect 'Protected audit: 1 independently anchored fictional event verified'
  Expect 'Root credential was NOT deleted'
  Expect 'NO patient records were imported'
  Expect 'This per-launch HMAC result is not a signed Core identity'
  if(@(Names | Where-Object {$_ -like '*fictional-patient-*' -or
     $_ -like '*INVENTED_PRIVATE_NAME*' -or $_ -like '*urn:uuid:*'}).Count -gt 0){
    throw 'invented_patient_identifiers_visible'
  }
  Press 'Protected audit: Clear verification result'
  Expect 'Native Rust Experiment'
  if(@(Names | Where-Object {$_ -like '*Protected audit: 1 independently anchored*'}).Count -gt 0){
    throw 'redacted_audit_status_not_cleared'
  }
  Write-Output 'WINDOWS_REAL_CORE981_PROTECTED_AUDIT_STATUS_UIA_PASS_NONCLINICAL'
} catch {
  [Console]::Error.WriteLine('WINDOWS_CORE981_PROTECTED_AUDIT_NATIVE_UIA_NO_GO')
  exit 1
} finally {
  if($process -and -not $process.HasExited){
    if(-not $process.CloseMainWindow() -or -not $process.WaitForExit(4500)){
      Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
