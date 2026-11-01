# Read-only nonadmin WFP AUDIT POLICY visibility. NO auditpol /set; no Security event reads.
# GUIDs per Microsoft Learn WFP auditing-and-logging: connection/packet-drop.
# Output only an anonymous bounded field inventory, never raw command output.
$ErrorActionPreference='Stop'
$os=Get-CimInstance Win32_OperatingSystem
$admin=(
    [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Read-WfpAuditVisibility([string]$subcategory) {
    # auditpol /get is a query, not a policy mutation. On a nonadmin host,
    # ERROR_PRIVILEGE_NOT_HELD (1314) is expected; treat it as NOT READABLE.
    # Discard command text: it may contain host/localized identifying data.
    try {
        $global:LASTEXITCODE=0
        & auditpol.exe /get /subcategory:$subcategory /r *> $null
        $code=$LASTEXITCODE
        if ($code -eq 0) { return 'READABLE_UNVERIFIED' }
        if ($code -eq 1314 -or $code -eq 5) { return 'PRIVILEGE_DENIED' }
        return 'OTHER_ERROR'
    } catch {
        return 'OTHER_ERROR'
    }
}
function Read-SecurityLogMetadata() {
    # -ListLog only asks whether the Security log is accessible.
    # Never read records, messages, process names, connections or IPs.
    try {
        $null=Get-WinEvent -ListLog 'Security' -ErrorAction Stop
        return 'AVAILABLE_METADATA'
    } catch {
        return 'ACCESS_DENIED'
    }
}
$receipt=[ordered]@{
    osBuild=[string]$os.Version
    elevated=[bool]$admin
    connectionAuditState=[string](Read-WfpAuditVisibility '{0CCE9226-69AE-11D9-BED3-505054503030}')
    packetDropAuditState=[string](Read-WfpAuditVisibility '{0CCE9225-69AE-11D9-BED3-505054503030}')
    securityLogMetadata=[string](Read-SecurityLogMetadata)
}
$receipt | ConvertTo-Json -Compress -Depth 2
