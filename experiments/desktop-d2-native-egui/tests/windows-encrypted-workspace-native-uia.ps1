# Real Windows 11 native UIAutomation: SOURCE-VERIFIED synthetic encrypted
# Workspace counters only, no patient data or installed Python worker.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
  [string]$LiveReceiptPath = ''
)
$ErrorActionPreference='Stop'
$fixtureSha='25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e'
function Refuse([string]$why) {
  [Console]::Error.WriteLine('D2_WINDOWS_ENCRYPTED_WORKSPACE_UIA_NO_GO: '+$why)
  exit 1
}
try {
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){
    Refuse 'unapproved D2 executable filename'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath -ErrorAction Stop).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    Refuse 'native Windows GUI binary source mismatch'
  }
  $fixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\workspace-ephemeral-demo.json')).Path
  if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $fixtureSha) {
    Refuse 'fictional encrypted summary source changed'
  }
  $live=$fixture
  if($LiveReceiptPath) {
    $resolved=(Resolve-Path -LiteralPath $LiveReceiptPath -ErrorAction Stop).Path
    $entry=Get-Item -LiteralPath $resolved -ErrorAction Stop
    if($entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
       $entry.Length -ne 391 -or
       (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash -ine $fixtureSha) {
      Refuse 'live ephemeral source summary changed or nonregular'
    }
    # QA-only: never accept a clinical resource, arbitrary FHIR/URL, or
    # report text which differs by even one byte from the reviewed fixture.
    $live=$resolved
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
} catch { Refuse 'binary/fixture provenance or Windows UIAutomation unavailable' }

function SpawnFixed([byte[]]$bytes) {
  $info=New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName=$exe
  $info.Arguments='--synthetic-workspace-receipt-stdin'
  $info.UseShellExecute=$false
  $info.RedirectStandardInput=$true
  $info.CreateNoWindow=$false
  $process=New-Object System.Diagnostics.Process
  $process.StartInfo=$info
  if(-not $process.Start()){throw 'native D2 process did not start'}
  try {
    $process.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
  } finally { $process.StandardInput.Close() }
  return $process
}
$process=$null
try {
  $bytes=[System.IO.File]::ReadAllBytes($live)
  $process=SpawnFixed $bytes
  $desktop=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 65;$i++){
    $wins=@($desktop.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    )|Where-Object{
      try {$_.Current.ProcessId -eq $process.Id -and
           $_.Current.Name -like 'MedOrigin Native Rust*' -and
           -not $_.Current.IsOffscreen} catch {$false}
    })
    if($wins.Count -eq 1){$window=$wins[0];break}
    if($wins.Count -gt 1){throw 'ambiguous native window PID'}
    Start-Sleep -Milliseconds 150
  }
  if(-not $window){throw 'expected native D2 window not accessible'}
  $required=@(
    ('Workspace demo SHA-256: '+$fixtureSha),
    'Fictional resources: 3',
    'Fictional provenance records: 3',
    'Audit events: 1',
    'Verified encrypted reopen: true',
    'Temporary encrypted store removed: true',
    'Synthetic encrypted ephemeral Workspace QA only',
    'source and freshness NOT authenticated by GUI'
  )
  $ok=$false
  for($i=0;$i -lt 40;$i++){
    $nodes=@($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition
    ))
    $names=@($nodes|ForEach-Object {try{$_.Current.Name}catch{''}})
    if(@($required|Where-Object{
      $target=$_
      -not @($names|Where-Object{$_ -like ('*'+$target+'*')}).Count
    }).Count -eq 0){$ok=$true;break}
    Start-Sleep -Milliseconds 170
  }
  if(-not $ok){throw 'actual GUI lacks exact encrypted demo counts/limitations'}
  if($process.HasExited){throw 'native GUI exited before UIA receipt verification'}
  Write-Output ('WINDOWS_NATIVE_ENCRYPTED_WORKSPACE_SOURCE_SHA_AX_PASS '+$fixtureSha)
}catch{
  Refuse $_.Exception.Message
}finally{
  if($process -and -not $process.HasExited){
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
  if($process){$process.Dispose()}
}
$forgery=[System.Text.Encoding]::UTF8.GetBytes(
  ([System.IO.File]::ReadAllText($fixture)).Replace(
    '"clinical_use_authorized":false',
    '"clinical_use_authorized":true'
  )
)
if([System.Text.Encoding]::UTF8.GetString($forgery) -notmatch 'clinical_use_authorized":true'){
  Refuse 'invalid forged-clinical test control'
}
$bad=$null
try {
  $bad=SpawnFixed $forgery
  if(-not $bad.WaitForExit(5000)){throw 'forged report did not refuse before GUI startup'}
  if($bad.ExitCode -eq 0){throw 'unsafe forged clinical flag accepted'}
  Write-Output 'WINDOWS_FORGED_CLINICAL_WORKSPACE_APPROVAL_REFUSED'
}catch{Refuse $_.Exception.Message}finally{
  if($bad -and -not $bad.HasExited){Stop-Process -Id $bad.Id -Force -ErrorAction SilentlyContinue}
  if($bad){$bad.Dispose()}
}
if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256){
  Refuse 'native GUI executable mutated during acceptance'
}
Write-Output 'D2_WINDOWS_ENCRYPTED_WORKSPACE_NATIVE_UIA_PASS_NONCLINICAL'
exit 0
