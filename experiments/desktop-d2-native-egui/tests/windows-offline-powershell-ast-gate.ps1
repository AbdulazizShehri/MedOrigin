# Source-only PS AST gate for all current Windows offline evidence scripts.
# No network, no elevation, no process launches and no host policy changes.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$scriptFiles=@(
  'windows-network-socket-observation.ps1',
  'windows-native-d2-socket-smoke.ps1',
  'windows-firewall-policy-preflight.ps1',
  'windows-firewall-policy-preflight-qa.ps1',
  'windows-native-fictional-compare-uia.ps1',
  'windows-native-fictional-compare-keyboard.ps1',
  'windows-native-fictional-json-pointer-uia.ps1'
)
foreach($name in $scriptFiles){
  $path=Join-Path $PSScriptRoot $name
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ throw ('MISSING_SCRIPT: '+$name) }
  $tokens=$null
  $parseErrors=$null
  [System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$parseErrors) | Out-Null
  if(@($parseErrors).Count -ne 0){
    throw ('POWERSHELL_AST_FAILURE: '+$name+' error_count='+@($parseErrors).Count)
  }
  Write-Output ('PS_AST_PASS: '+$name)
}
Write-Output 'MEDORIGIN_WINDOWS_OFFLINE_POWERSHELL_AST_7_OF_7_PASS_NONPUBLISHING'
