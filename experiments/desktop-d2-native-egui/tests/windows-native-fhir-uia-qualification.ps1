# Real interactive Windows UI Automation for eight NEW fictional native D2 FHIR cases.
# It uses only approved local synthetic program bytes. NO patient data or packet claim.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
function Refuse([string]$why){[Console]::Error.WriteLine('D2_NATIVE_FHIR_UIA_NO_GO: '+$why);exit 1}
try {
  if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){Refuse 'missing D2 executable'}
  if ((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){Refuse 'unexpected executable filename'}
  if ((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256){Refuse 'binary identity mismatch'}
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
} catch {Refuse 'cannot establish UIA and approved executable identity'}
$proc=$null
try {
  $proc=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru -ErrorAction Stop
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($attempt=0;$attempt -lt 60;$attempt++){
    foreach($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
      try {
        if ($w.Current.ProcessId -eq $proc.Id -and $w.Current.Name -like 'MedOrigin Native Rust*' -and -not $w.Current.IsOffscreen){$window=$w;break}
      }catch {}
    }
    if($window){break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'matching visible native window absent'}
  function UI {
    return @($window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition))
  }
  function Find-Unique([string]$name,[string]$type='ControlType.Button'){
    $matches=@(UI | Where-Object {
      try { $_.Current.Name -eq $name -and $_.Current.ControlType.ProgrammaticName -eq $type -and $_.Current.IsEnabled }catch {$false}
    })
    if ($matches.Count -eq 1){return $matches[0]}
    return $null
  }
  function Perform([System.Windows.Automation.AutomationElement]$element){
    if($null -eq $element){throw 'control missing'}
    try {
      $invoke=[System.Windows.Automation.InvokePattern]$element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
      $invoke.Invoke()
    }catch {
      try {
        $toggle=[System.Windows.Automation.TogglePattern]$element.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $toggle.Toggle()
      }catch {throw 'native UIA invocation/toggle unavailable'}
    }
  }
  $header=$null
  for($i=0;$i -lt 30;$i++){
    $header=Find-Unique 'Additional fictional FHIR/Bundle cases (8)'
    if($header){break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $header){
    $matches=@(UI| Where-Object {
      try {$_.Current.Name -like '*Additional fictional FHIR/Bundle cases*'}catch{$false}
    }| ForEach-Object {
      try {"$($_.Current.ControlType.ProgrammaticName):$($_.Current.Name)"}catch{}
    })
    throw ('Additional cases expansion button not found: '+($matches -join '|'))
  }
  Perform $header
  $cases=@(
    @{id='observation-minimal';bytes=251;sha='527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19';status='FHIR_ENVELOPE_OK'},
    @{id='observation-bad-subject';bytes=253;sha='d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838';status='INVALID_REFERENCE'},
    @{id='bundle-valid';bytes=531;sha='3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983';status='BUNDLE_GRAPH_OK'},
    @{id='bundle-bad-reference';bytes=528;sha='4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082';status='INVALID_REFERENCE'},
    @{id='bundle-duplicate';bytes=531;sha='813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b';status='DUPLICATE_ENTRY'},
    @{id='bundle-wrong-type';bytes=532;sha='293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7';status='INVALID_BUNDLE_TYPE'},
    @{id='bundle-linked';bytes=559;sha='1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88';status='BUNDLE_GRAPH_OK'},
    @{id='bundle-dangling';bytes=559;sha='1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229';status='INVALID_REFERENCE'}
  )
  foreach($case in $cases){
    $label="$($case.id) ($($case.bytes) bytes)"
    $selector=$null
    for($n=0;$n -lt 30;$n++){
      $selector=Find-Unique $label
      if($selector){break}
      Start-Sleep -Milliseconds 200
    }
    if(-not $selector){throw ('new fictional selector missing or not unique: '+$label)}
    Perform $selector
    $verify=Find-Unique 'Verify synthetic SHA-256'
    if(-not $verify){throw 'original Verify button lost when new case selected'}
    Perform $verify
    $expectedSha="Synthetic raw SHA-256 verified: $($case.sha)"
    $expectedStatus="Fictional FHIR envelope: $($case.status) (NOT full FHIR R4 validation)"
    $foundSha=$false;$foundStatus=$false
    for($i=0;$i -lt 35;$i++){
      $nodes=@(UI|Where-Object {
        try {$_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text'}catch{$false}
      })
      $names=@($nodes|ForEach-Object {$_.Current.Name})
      $foundSha=@($names|Where-Object {$_ -ceq $expectedSha}).Count -eq 1
      $foundStatus=@($names|Where-Object {$_ -ceq $expectedStatus}).Count -eq 1
      if($foundSha -and $foundStatus){break}
      Start-Sleep -Milliseconds 200
    }
    if(-not $foundSha -or -not $foundStatus){
      throw ("native UIA verified SHA/status missing for "+$case.id+" sha="+$foundSha+" status="+$foundStatus)
    }
    Write-Output ('D2_NATIVE_FHIR_UIA_PASS='+$case.id+' status='+$case.status)
  }
  Write-Output 'D2_NATIVE_FHIR_UIA_8_OF_8_PASS_NONPUBLISHING'
}catch {
  [Console]::Error.WriteLine('D2_NATIVE_FHIR_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
}finally {
  if($proc -and -not $proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
