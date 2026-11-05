# Actual Windows native UIA for one redacted, source-run Core #963 fictional encrypted receipt.
# Never loads actual patient records: only fixed SHA-qualified synthetic QA report.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedExeSha256,
  [string]$LiveReceiptPath = ''
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
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments='--synthetic-core-file-batch-receipt-stdin'
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()){throw 'native_launch_failed'}
  $raw=[IO.File]::ReadAllBytes($receipt)
  $process.StandardInput.BaseStream.Write($raw,0,$raw.Length)
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
  if(@(Names | Where-Object {$_ -like '*fictional-patient-001*' -or $_ -like '*INVENTED_PRIVATE_NAME*'}).Count -gt 0){
    throw 'native_receipt_patient_identity_visible'
  }
  Press 'Core batch: Clear redacted receipt'
  Expect 'Native Rust Experiment'
  if(@(Names | Where-Object {$_ -like '*Core: 2 independent fictional imports*'}).Count -gt 0){
    throw 'native_receipt_not_cleared'
  }
  Write-Output 'WINDOWS_REAL_CORE963_TWO_FILES_ENCRYPTED_REOPEN_REDACTED_D2_NATIVE_UIA_PASS_NONCLINICAL'
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
