# Real Windows UIAutomation for MedOrigin D2 source-verified fictional workspace.
# No PHI, no import or EHR, no network, source/test-only nonclinical preview.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference='Stop'
function Refuse([string]$Reason){
  [Console]::Error.WriteLine('D2_FICTIONAL_WORKSPACE_WINDOWS_UIA_NO_GO: '+$Reason)
  exit 1
}
try{
  if(-not(Test-Path -LiteralPath $ExePath -PathType Leaf)){Refuse 'native source executable missing'}
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){
    Refuse 'unexpected binary filename'
  }
  if((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedSha256){
    Refuse 'native executable SHA mismatch'
  }
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
}catch{Refuse 'binary provenance or UIAutomation unavailable'}
$proc=$null
try{
  $proc=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
  $root=[System.Windows.Automation.AutomationElement]::RootElement
  $window=$null
  for($i=0;$i -lt 70;$i++){
    $matches=@($root.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    )|Where-Object{
      try {
        $_.Current.ProcessId -eq $proc.Id -and
        $_.Current.Name -like 'MedOrigin Native Rust*' -and
        -not $_.Current.IsOffscreen
      }catch{$false}
    })
    if($matches.Count -eq 1){$window=$matches[0];break}
    if($matches.Count -gt 1){throw 'multiple native windows for same source process'}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'real source-bound native window not accessible'}
  function Nodes {
    return @($window.FindAll(
      [System.Windows.Automation.TreeScope]::Descendants,
      [System.Windows.Automation.Condition]::TrueCondition
    ))
  }
  function FindOne([string]$name) {
    $matches=@(Nodes|Where-Object{
      try {
        $_.Current.Name -like $name -and
        $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Button' -and
        $_.Current.IsEnabled
      }catch{$false}
    })
    if($matches.Count -eq 1){return $matches[0]}
    return $null
  }
  function Press([string]$name){
    $node=$null
    for($i=0;$i -lt 45;$i++){
      $node=FindOne $name
      if($node){break}
      Start-Sleep -Milliseconds 130
    }
    if(-not $node){throw ('native Button missing or ambiguous: '+$name)}
    try {
      $invoke=[System.Windows.Automation.InvokePattern]$node.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
      )
      $invoke.Invoke()
    }catch{
      try {
        $toggle=[System.Windows.Automation.TogglePattern]$node.GetCurrentPattern(
          [System.Windows.Automation.TogglePattern]::Pattern
        )
        $toggle.Toggle()
      }catch{throw ('native Button has no actionable UIA pattern: '+$name)}
    }
    Start-Sleep -Milliseconds 450
  }
  function Names {
    return @(Nodes|ForEach-Object{
      try{$_.Current.Name}catch{''}
    })
  }
  function HasLabel([string]$text){
    return @(Names|Where-Object{$_ -like ('*'+$text+'*')}).Count -gt 0
  }
  function Detail([string]$fixture,[string]$sha,[string]$status){
    $ready=$false
    for($i=0;$i -lt 45;$i++){
      if((HasLabel ('Fictional case: '+$fixture)) -and
         (HasLabel ('Source SHA-256: '+$sha)) -and
         (HasLabel ('Expected developer envelope status: '+$status)) -and
         (HasLabel 'Clinical data: PROHIBITED')){
        $ready=$true
        break
      }
      Start-Sleep -Milliseconds 150
    }
    if(-not $ready){throw ('fictional detail missing SHA/status for '+$fixture)}
    Write-Output ('D2_WINDOWS_FICTIONAL_WORKSPACE_CASE_PASS '+$fixture)
  }
  Press 'Fictional Workspace*'
  Press 'Enter fictional workspace (synthetic only)'
  Press 'Open fictional case: observation-minimal*'
  Detail 'observation-minimal' '527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19' 'FHIR_ENVELOPE_OK'
  Press 'Expected-negative developer controls'
  if(HasLabel 'Fictional case: observation-minimal'){throw 'positive detail survived negative filter'}
  Press 'Open fictional case: observation-bad-subject*'
  Detail 'observation-bad-subject' 'd2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838' 'INVALID_REFERENCE'
  Press 'Open fictional case: bundle-dangling*'
  Detail 'bundle-dangling' '1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229' 'INVALID_REFERENCE'
  Press 'Expected-positive developer controls'
  if(HasLabel 'Fictional case: bundle-dangling'){throw 'negative detail survived positive filter'}
  Press 'Open fictional case: bundle-linked*'
  Detail 'bundle-linked' '1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88' 'BUNDLE_GRAPH_OK'
  if(-not(HasLabel '/entry/1/resource/subject/reference')){
    throw 'known fictional bundle pointer not exposed through native GUI'
  }
  # Resource-type facets and genuine native linked-resource navigation.
  # Never accept free text, a patient import path or unreviewed FHIR refs.
  Press 'All fictional cases'
  Press 'Observation (fictional)'
  if(-not (HasLabel 'Fictional worklist: 2 of 6 fixed source cases visible')){
    throw 'Observation resource facet did not show exactly two source cases'
  }
  Press 'Open fictional case: observation-minimal*'
  Press 'Follow fictional reference: Patient/synthetic'
  if(-not(HasLabel 'FAIL CLOSED: fictional linked reference') -or
     (HasLabel 'Fictional case: patient-minimal')){
    throw 'hidden patient target was reached or source detail persisted'
  }
  Press 'All resource types'
  if(-not(HasLabel 'Fictional worklist: 6 of 6 fixed source cases visible')){
    throw 'All resource type facet did not restore six cases'
  }
  Press 'Open fictional case: observation-minimal*'
  Press 'Follow fictional reference: Patient/synthetic'
  Detail 'patient-minimal' '747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0' 'FHIR_ENVELOPE_OK'
  Press 'Back to previous fictional case'
  Detail 'observation-minimal' '527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19' 'FHIR_ENVELOPE_OK'
  if(HasLabel 'Back to previous fictional case'){throw 'one-step back history retained previous case'}
  Press 'Bundle (fictional)'
  if(-not(HasLabel 'Fictional worklist: 3 of 6 fixed source cases visible')){
    throw 'Bundle type facet did not show exactly three source cases'
  }
  Press 'Open fictional case: bundle-linked*'
  Detail 'bundle-linked' '1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88' 'BUNDLE_GRAPH_OK'
  Press 'All resource types'
  Press 'Open fictional case: bundle-linked*'
  Press 'Follow fictional reference: urn:uuid:00000000-0000-4000-8000-000000000002'
  Detail 'observation-minimal' '527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19' 'FHIR_ENVELOPE_OK'
  Press 'Back to previous fictional case'
  Detail 'bundle-linked' '1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88' 'BUNDLE_GRAPH_OK'
  Write-Output 'D2_WINDOWS_FICTIONAL_WORKSPACE_RESOURCE_FACET_LINK_AND_BACK_PASS_NOT_CLINICAL'
  Press 'Close fictional workspace and clear details'
  if(HasLabel 'Fictional case: bundle-linked'){throw 'workspace close retained source detail'}
  if(-not(HasLabel 'Enter fictional workspace (synthetic only)')){
    throw 'fictional workspace close did not return to initial intent gate'
  }
  Write-Output 'D2_WINDOWS_FICTIONAL_WORKSPACE_4_CASES_FILTER_AND_CLEAR_PASS_NOT_CLINICAL'
}catch{
  [Console]::Error.WriteLine('D2_FICTIONAL_WORKSPACE_WINDOWS_UIA_NO_GO: '+$_.Exception.Message)
  exit 1
}finally{
  if($proc -and -not $proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
exit 0
