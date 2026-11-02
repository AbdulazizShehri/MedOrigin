[CmdletBinding()]
param(
  [string]$NativeExecutable,
  [string]$NativeSha256
)
# Tests the real Windows firewall read-only preflight against actual OS policy.
# No firewall mutation, no elevation, no packets or MedOrigin release claim.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$validator=Join-Path $PSScriptRoot 'windows-firewall-policy-preflight.ps1'
$tokens=$null
$parseErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile($validator,[ref]$tokens,[ref]$parseErrors) | Out-Null
if(@($parseErrors).Count -ne 0){ throw 'PREFLIGHT_SOURCE_SYNTAX_INVALID' }

$exe=(Get-Process -Id $PID -ErrorAction Stop).Path
$sha=(Get-FileHash -LiteralPath $exe -Algorithm SHA256 -ErrorAction Stop).Hash
function Test-Rejection([string]$file,[string]$hash,[string]$expectedReason){
  $raw=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $validator -Executable $file -ExpectedSha256 $hash
  $code=$LASTEXITCODE
  $result=($raw | Out-String | ConvertFrom-Json -ErrorAction Stop)
  if($code -eq 0 -or $result.decision -ne 'NO_GO' -or
     $result.os_enforcement_proven -ne $false -or
     $result.release_authorized -ne $false -or
     $result.dns_packet_egress_proven -ne $false -or
     $result.host_policy_modified -ne $false){ throw 'PRE-FLIGHT_FALSE_SUCCESS' }
  if($result.reason -ne $expectedReason){
    throw ('UNEXPECTED_FAIL_CLOSED_REASON: '+$result.reason)
  }
  Write-Output ('PREFLIGHT_REJECTION_PASS: '+$expectedReason)
}
Test-Rejection $exe ('0'*64) 'EXECUTABLE_SHA_MISMATCH'
Test-Rejection (Join-Path $PSScriptRoot 'nonexistent-fixture.exe') $sha 'POLICY_READ_ERROR_OR_INCOMPLETE_OBSERVATION'
Test-Rejection $exe $sha 'EXECUTABLE_NAME_MISMATCH'
if([string]::IsNullOrWhiteSpace($NativeExecutable) -xor [string]::IsNullOrWhiteSpace($NativeSha256)) {
  throw 'Both exact native executable and SHA-256 are required together'
}
if(-not [string]::IsNullOrWhiteSpace($NativeExecutable)) {
  if($NativeSha256 -notmatch '^[0-9A-Fa-f]{64}) { throw 'INVALID_PINNED_NATIVE_SHA' }
  # Actual app test (not a PowerShell control): verify the preflight rejects
  # an incorrect caller-pinned digest *before* consulting the host policy.
  Test-Rejection $NativeExecutable ('0'*64) 'EXECUTABLE_SHA_MISMATCH'
  $raw=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $validator -Executable $NativeExecutable -ExpectedSha256 $NativeSha256
  $code=$LASTEXITCODE
  $result=($raw | Out-String | ConvertFrom-Json -ErrorAction Stop)
  if($code -eq 0 -or $result.decision -ne 'NO_GO' -or
     $result.os_enforcement_proven -ne $false -or
     $result.release_authorized -ne $false -or
     $result.dns_packet_egress_proven -ne $false -or
     $result.host_policy_modified -ne $false) { throw 'NATIVE_PRE-FLIGHT_FALSE_SUCCESS' }
  if($result.reason -notin @('EXACT_FULL_SCOPE_BLOCK_RULE_NOT_FOUND','RULE_CANDIDATE_FOUND_BUT_EGRESS_UNPROVEN')) {
    throw ('NATIVE_POLICY_NOT_INSPECTABLE: '+$result.reason)
  }
  Write-Output ('PREFLIGHT_ACTUAL_NATIVE_D2_NO_GO: '+$result.reason+', exit='+$code)
  Write-Output 'WINDOWS_POLICY_PREFLIGHT_5_OF_5_PASS_NONPUBLISHING'
} else {
  Write-Output 'WINDOWS_POLICY_PREFLIGHT_3_OF_3_PASS_NONPUBLISHING'
}
