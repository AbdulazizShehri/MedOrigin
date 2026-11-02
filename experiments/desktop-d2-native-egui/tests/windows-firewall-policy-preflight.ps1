# Read-only Windows Defender Firewall rule preflight for one exact binary.
# This NEVER proves WFP enforcement, socket containment, DNS or packet zero-egress.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$Executable,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
function Refuse([string]$reason,[int]$code,[int]$candidates) {
  [pscustomobject]@{
    schema='medorigin-windows-offline-firewall-preflight-v1'
    decision='NO_GO'
    reason=$reason
    syntactic_full_scope_block_candidates=$candidates
    release_authorized=$false
    os_enforcement_proven=$false
    dns_packet_egress_proven=$false
    host_policy_modified=$false
  } | ConvertTo-Json -Compress
  exit $code
}
try {
  $file=(Resolve-Path -LiteralPath $Executable -ErrorAction Stop).Path
  if(-not (Test-Path -LiteralPath $file -PathType Leaf)) { Refuse 'EXECUTABLE_NOT_FILE' 4 0 }
  $digest=(Get-FileHash -LiteralPath $file -Algorithm SHA256 -ErrorAction Stop).Hash
  if($digest -ine $ExpectedSha256) { Refuse 'EXECUTABLE_SHA_MISMATCH' 4 0 }
  $profiles=@(Get-NetFirewallProfile -PolicyStore ActiveStore -ErrorAction Stop)
  $enabledNames=@($profiles | Where-Object { [bool]$_.Enabled } | ForEach-Object { [string]$_.Name })
  foreach($name in @('Domain','Private','Public')) {
    if($name -notin $enabledNames) { Refuse 'FIREWALL_PROFILE_DISABLED_OR_MISSING' 2 0 }
  }
  $rules=@(Get-NetFirewallRule -PolicyStore ActiveStore -Enabled True -Direction Outbound -Action Block -ErrorAction Stop)
  $matching=0
  foreach($rule in $rules) {
    if([string]$rule.Profile -ne 'Any') { continue }
    $apps=@($rule | Get-NetFirewallApplicationFilter -ErrorAction Stop)
    if($apps.Count -ne 1 -or [string]$apps[0].Program -ine $file) { continue }
    $addresses=@($rule | Get-NetFirewallAddressFilter -ErrorAction Stop)
    $ports=@($rule | Get-NetFirewallPortFilter -ErrorAction Stop)
    $interfaces=@($rule | Get-NetFirewallInterfaceFilter -ErrorAction Stop)
    $interfaceTypes=@($rule | Get-NetFirewallInterfaceTypeFilter -ErrorAction Stop)
    $services=@($rule | Get-NetFirewallServiceFilter -ErrorAction Stop)
    if($addresses.Count -ne 1 -or $ports.Count -ne 1 -or $interfaces.Count -ne 1 -or $interfaceTypes.Count -ne 1 -or $services.Count -ne 1){ continue }
    if([string]$addresses[0].LocalAddress -ne 'Any' -or [string]$addresses[0].RemoteAddress -ne 'Any'){ continue }
    if([string]$ports[0].Protocol -notin @('Any','256') -or [string]$ports[0].LocalPort -ne 'Any' -or [string]$ports[0].RemotePort -ne 'Any'){ continue }
    if([string]$interfaces[0].InterfaceAlias -ne 'Any' -or [string]$interfaceTypes[0].InterfaceType -ne 'Any'){ continue }
    if([string]$services[0].Service -ne 'Any'){ continue }
    $matching++
  }
  if($matching -eq 0) { Refuse 'EXACT_FULL_SCOPE_BLOCK_RULE_NOT_FOUND' 2 0 }
  # A textual rule match does not prove enforcement or coverage of brokers,
  # DNS services, WFP exceptions, escapes, or packet-level negative control.
  Refuse 'RULE_CANDIDATE_FOUND_BUT_EGRESS_UNPROVEN' 3 $matching
} catch {
  # Never print exception paths, policy contents, rules, or host details.
  Refuse 'POLICY_READ_ERROR_OR_INCOMPLETE_OBSERVATION' 4 0
}
