# Real Windows UIAutomation of native D2 source-pinned Core report panel.
# Synthetic-only. Requires exact locally built executable hash, no PHI/network.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
function Refuse([string]$why) {
  [Console]::Error.WriteLine('D2_CORE_PROVENANCE_UIA_NO_GO: '+$why)
  exit 1
}
try {
  if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    Refuse 'source-bound executable missing'
  }
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    Refuse 'unexpected native executable identity'
  }
  if((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256) {
    Refuse 'native executable SHA256 mismatch'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
} catch { Refuse 'cannot attest binary or access Windows UIAutomation' }

$proc=$null
try {
  $proc=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($attempt=0;$attempt -lt 70;$attempt++){
    $targets=@($root.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition))
    $candidate=@($targets | Where-Object {
      try {
        $_.Current.ProcessId -eq $proc.Id -and
        $_.Current.Name -like 'MedOrigin Native Rust*' -and
        -not $_.Current.IsOffscreen
      } catch {$false}
    })
    if($candidate.Count -eq 1){$window=$candidate[0];break}
    if($candidate.Count -gt 1){throw 'multiple windows for exact process'}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'source-pinned native D2 window not accessible'}
  function Nodes {
    return @($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition))
  }
  function Get-Control([string]$pattern,[string]$type){
    $found=@(Nodes | Where-Object {
      try {
        $_.Current.Name -like $pattern -and
        $_.Current.ControlType.ProgrammaticName -eq $type -and
        $_.Current.IsEnabled
      }catch {$false}
    })
    if($found.Count -eq 1){return $found[0]}
    return $null
  }
  function Press([string]$pattern,[string]$type='ControlType.Button'){
    $node=$null
    for($i=0;$i -lt 40;$i++){
      $node=Get-Control $pattern $type
      if($node){break}
      Start-Sleep -Milliseconds 150
    }
    if(-not $node){throw ('missing/ambiguous UIA control: '+$pattern+' ('+$type+')')}
    try {
      $invoke=[System.Windows.Automation.InvokePattern]$node.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern)
      $invoke.Invoke()
    }catch{
      try {
        $toggle=[System.Windows.Automation.TogglePattern]$node.GetCurrentPattern(
          [System.Windows.Automation.TogglePattern]::Pattern)
        $toggle.Toggle()
      }catch{throw ('native UIA action not available for '+$pattern)}
    }
    Start-Sleep -Milliseconds 450
  }
  function Assert-Receipt([string]$digest,[string]$case){
    $found=$false
    for($i=0;$i -lt 40;$i++){
      $names=@(Nodes | ForEach-Object {
        try { $_.Current.Name }catch { '' }
      })
      $foundSha=@($names | Where-Object {$_ -ceq ('Source report SHA-256: '+$digest)}).Count -eq 1
      $foundStatus=@($names | Where-Object {$_ -ceq 'Core status: not_validated'}).Count -eq 1
      $foundWarning=@($names | Where-Object {$_ -like '*FHIR R4 NOT validated*'}).Count -ge 1
      if($foundSha -and $foundStatus -and $foundWarning){$found=$true;break}
      Start-Sleep -Milliseconds 150
    }
    if(-not $found){
      throw ('source Core report not visible: '+$case+' sha='+$foundSha+
        ' status='+$foundStatus+' warning='+$foundWarning)
    }
    Write-Output ('D2_WINDOWS_CORE_PROVENANCE_UIA_SOURCE_REPORT_PASS '+$case)
  }
  Press 'Core provenance: two fictional reports (NOT validated)'
  Press 'Inspect Core synthetic provenance (read-only)'
  Assert-Receipt '165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08' 'known'
  Press 'Unknown fictional resource*' 'ControlType.Button'
  Press 'Inspect Core synthetic provenance (read-only)'
  Assert-Receipt '7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c' 'negative'
  $stale=@(Nodes|Where-Object {
    try {$_.Current.Name -eq 'Source report SHA-256: 165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08'}
    catch{$false}
  })
  if($stale.Count -gt 0){throw 'stale positive receipt survived selection change'}
  Write-Output 'D2_WINDOWS_CORE_PROVENANCE_UIA_2_OF_2_PASS_NONPUBLISHING'
}catch{
  [Console]::Error.WriteLine('D2_CORE_PROVENANCE_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
}finally{
  if($proc -and -not $proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
# Ensure a real zero exit status even when the invoking PowerShell session
# carries a stale nonzero native-command $LASTEXITCODE from earlier work.
exit 0
