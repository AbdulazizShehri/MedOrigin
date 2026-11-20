# Actual native Windows UIAutomation of the new in-process, fictional-only JSON reader.
# Requires an exact externally pinned executable digest. No PHI or user files.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){throw 'missing executable'}
if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){throw 'wrong executable'}
if((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256){throw 'wrong SHA256 before launch'}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process=$null
try {
  $process=Start-Process -FilePath (Resolve-Path $ExePath).Path -PassThru
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 60;$i++){
    foreach($node in $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
      try {
        if($node.Current.ProcessId -eq $process.Id -and $node.Current.Name -like 'MedOrigin Native Rust*' -and -not $node.Current.IsOffscreen){$window=$node;break}
      }catch{}
    }
    if($window){break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'native preview window not visible'}
  function Nodes { @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)) }
  function One([string]$label,[string]$kind='ControlType.Button'){
    $results=@(Nodes | Where-Object {
      try{$_.Current.Name -ceq $label -and $_.Current.ControlType.ProgrammaticName -eq $kind -and $_.Current.IsEnabled}catch{$false}
    })
    if($results.Count -ne 1){throw ('missing or ambiguous native control '+$label+' count='+$results.Count)}
    return $results[0]
  }
  function Press([System.Windows.Automation.AutomationElement]$el){
    try {
      $action=[System.Windows.Automation.InvokePattern]$el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
      $action.Invoke()
    }catch{
      $action=[System.Windows.Automation.TogglePattern]$el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
      $action.Toggle()
    }
  }
  function ExpectText([string]$expected,[bool]$present=$true){
    for($retry=0;$retry -lt 30;$retry++){
      $found=@(Nodes | Where-Object {
        try{$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text' -and $_.Current.Name -ceq $expected}catch{$false}
      }).Count
      if($present -and $found -eq 1){return}
      if((-not $present) -and $found -eq 0){return}
      Start-Sleep -Milliseconds 180
    }
    throw ('accessibility text mismatch present='+$present+' text='+$expected)
  }
  $button='Inspect fictional JSON (verified, read-only)'
  $fictional='{"resourceType":"Patient","id":"synthetic","active":true}'
  Press (One $button)
  ExpectText $fictional
  ExpectText 'Raw fictional source JSON - no normalization or FHIR R4 validation'
  Write-Output 'NATIVE_JSON_PREVIEW_PATIENT_UIA_PASS'

  Press (One 'patient-invalid-utf8 (1 bytes)')
  ExpectText $fictional $false
  Press (One $button)
  ExpectText 'No JSON preview for this raw-byte boundary test fixture.'
  ExpectText $fictional $false
  Write-Output 'NATIVE_JSON_PREVIEW_INVALID_UTF8_REFUSAL_PASS'

  Press (One 'Additional fictional FHIR/Bundle cases (8)')
  $bundleSelector=$null
  for($i=0;$i -lt 40;$i++){
    $candidates=@(Nodes | Where-Object {
      try{$_.Current.Name -ceq 'bundle-valid (531 bytes)' -and $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and $_.Current.IsEnabled}catch{$false}
    })
    if($candidates.Count -eq 1){$bundleSelector=$candidates[0];break}
    Start-Sleep -Milliseconds 180
  }
  if(-not $bundleSelector){throw 'advanced Bundle selector not present after expansion'}
  Press $bundleSelector
  Press (One $button)
  $bundle = (Get-Content -LiteralPath (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'desktop-d0-rust\fixtures\bundle-valid.json') -Raw).Trim()
  # Source fixture file is local to test harness; actual app never opens files.
  ExpectText $bundle
  ExpectText $fictional $false
  Write-Output 'NATIVE_JSON_PREVIEW_BUNDLE_UIA_PASS'
  Write-Output 'NATIVE_JSON_PREVIEW_3_OF_3_PASS_NONPUBLISHING'
}catch {
  [Console]::Error.WriteLine('NATIVE_JSON_PREVIEW_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
}finally {
  if($process -and -not $process.HasExited){Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue}
}
