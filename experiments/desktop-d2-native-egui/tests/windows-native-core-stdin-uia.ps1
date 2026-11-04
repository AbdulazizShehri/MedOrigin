# Windows real native GUI acceptance: one-shot source-fixed synthetic Core stdin.
# No PHI, Core launching, installed security approval, EHR or release.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
function Refuse([string]$reason) {
  [Console]::Error.WriteLine('D2_WINDOWS_ONE_SHOT_CORE_STDIN_UIA_NO_GO: '+$reason)
  exit 1
}
try {
  if(-not(Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    Refuse 'native executable missing'
  }
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    Refuse 'unexpected native binary filename'
  }
  $exe=(Resolve-Path -LiteralPath $ExePath).Path
  if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    Refuse 'actual native binary SHA mismatch'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
} catch {
  Refuse 'binary hash or Windows UIAutomation unavailable'
}
$cases=@(
  @{name='known'; file='known-structure-definition.json'; sha='165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08'},
  @{name='negative'; file='unknown-fictional-negative.json'; sha='7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c'}
)
$root=[System.Windows.Automation.AutomationElement]::RootElement
function SpawnFixedInput([byte[]]$data) {
  $start=New-Object System.Diagnostics.ProcessStartInfo
  $start.FileName=$exe
  $start.Arguments='--synthetic-core-stdin'
  $start.UseShellExecute=$false
  $start.RedirectStandardInput=$true
  $start.RedirectStandardOutput=$false
  $start.RedirectStandardError=$false
  $start.CreateNoWindow=$false
  $proc=New-Object System.Diagnostics.Process
  $proc.StartInfo=$start
  if(-not $proc.Start()){throw 'real source-bound GUI process did not start'}
  try {
    $proc.StandardInput.BaseStream.Write($data,0,$data.Length)
  } finally {
    $proc.StandardInput.Close()
  }
  return $proc
}
function FindWindow([int]$pid) {
  for($i=0;$i -lt 65;$i++){
    $windows=@($root.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    )|Where-Object {
      try {
        $_.Current.ProcessId -eq $pid -and
        $_.Current.Name -like 'MedOrigin Native Rust*' -and
        -not $_.Current.IsOffscreen
      } catch {$false}
    })
    if($windows.Count -eq 1){return $windows[0]}
    if($windows.Count -gt 1){throw 'ambiguous native GUI PID window count'}
    Start-Sleep -Milliseconds 150
  }
  throw 'actual native GUI window not accessible'
}
function ContainsLabel($window,[string]$text) {
  $nodes=@($window.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
  ))
  return @($nodes|Where-Object{
    try {$_.Current.Name -like ('*'+$text+'*')}catch{$false}
  }).Count -gt 0
}
foreach($case in $cases) {
  $fixture=Join-Path (Join-Path $PSScriptRoot '..\fixtures\core') $case.file
  if(-not(Test-Path -LiteralPath $fixture -PathType Leaf)) {
    Refuse 'required source-compiled synthetic report missing'
  }
  if((Get-FileHash -LiteralPath $fixture -Algorithm SHA256).Hash -ine $case.sha) {
    Refuse 'source-compiled canonical input changed'
  }
  $payload=[System.IO.File]::ReadAllBytes((Resolve-Path $fixture).Path)
  if($payload.Length -gt 2048 -or $payload.Length -lt 150) {
    Refuse 'source-compiled fixed report length outside contract'
  }
  $proc=$null
  try {
    $proc=SpawnFixedInput $payload
    $window=FindWindow $proc.Id
    $accepted=$false
    for($i=0;$i -lt 45;$i++) {
      if((ContainsLabel $window ('Source report SHA-256: '+$case.sha)) -and
         (ContainsLabel $window 'Core status: not_validated') -and
         (ContainsLabel $window 'FHIR R4 NOT validated') -and
         (ContainsLabel $window 'One-shot external stdin synthetic Core report accepted')) {
        $accepted=$true
        break
      }
      Start-Sleep -Milliseconds 170
    }
    if(-not $accepted) {throw ('actual native UIA receipt missing for '+$case.name)}
    if($proc.HasExited) {throw ('native GUI exited before live observation '+$case.name)}
    Write-Output ('D2_WINDOWS_ONE_SHOT_CORE_STDIN_GUI_SOURCE_REPORT_PASS '+$case.name)
  }catch{
    Refuse $_.Exception.Message
  }finally{
    if($proc -and -not $proc.HasExited) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    if($proc){$proc.Dispose()}
  }
}
# A false medical claim must stop BEFORE creating any GUI window.
$bad=$null
try {
  $bad=SpawnFixedInput ([System.Text.Encoding]::UTF8.GetBytes('{"status":"valid"}'))
  if(-not $bad.WaitForExit(5000)) {
    throw 'unapproved report blocked forever instead of fail closed'
  }
  if($bad.ExitCode -eq 0) {
    throw 'forged clinical validity accepted by GUI'
  }
  Write-Output 'D2_WINDOWS_ONE_SHOT_CORE_STDIN_FORGED_VALID_REFUSED'
} catch {
  Refuse $_.Exception.Message
} finally {
  if($bad -and -not $bad.HasExited) {
    Stop-Process -Id $bad.Id -Force -ErrorAction SilentlyContinue
  }
  if($bad){$bad.Dispose()}
}
if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ine $ExpectedSha256) {
  Refuse 'native executable mutated after GUI test'
}
Write-Output 'D2_WINDOWS_ONE_SHOT_CORE_STDIN_NATIVE_UIA_2_OF_2_PASS_NOT_CLINICAL'
exit 0
