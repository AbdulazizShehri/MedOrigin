# Windows D1 T1: NONADMIN, READ-ONLY PROVIDER/CHANNEL METADATA ONLY.
# No packet capture, no events/payloads, no session start, no firewall changes.
# Emits exactly one bounded anonymous JSON object (no IP/process/user strings).
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$admin = (
    [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Read-ProviderRegistration([string]$name) {
    try {
        $null = Get-WinEvent -ListProvider $name -ErrorAction Stop
        return 'REGISTERED'
    } catch {
        return 'UNAVAILABLE'
    }
}
function Read-ChannelEnablement([string]$name) {
    try {
        $log = Get-WinEvent -ListLog $name -ErrorAction Stop
        if ($log.IsEnabled) { return 'ENABLED' }
        return 'DISABLED'
    } catch {
        return 'UNAVAILABLE'
    }
}
$receipt = [ordered]@{
    osBuild = [string]$os.Version
    elevated = [bool]$admin
    wfpProvider = [string](Read-ProviderRegistration 'Microsoft-Windows-WFP')
    tcpipProvider = [string](Read-ProviderRegistration 'Microsoft-Windows-TCPIP')
    dnsProvider = [string](Read-ProviderRegistration 'Microsoft-Windows-DNS-Client')
    kernelNetworkProvider = [string](Read-ProviderRegistration 'Microsoft-Windows-Kernel-Network')
    wfpChannel = [string](Read-ChannelEnablement 'Microsoft-Windows-WFP/Operational')
    dnsChannel = [string](Read-ChannelEnablement 'Microsoft-Windows-DNS-Client/Operational')
    pktmonExecutable = [bool](Get-Command pktmon.exe -ErrorAction SilentlyContinue)
    netEventReadCmdlet = [bool](Get-Command Get-NetEventSession -ErrorAction SilentlyContinue)
}
$receipt | ConvertTo-Json -Compress -Depth 2
