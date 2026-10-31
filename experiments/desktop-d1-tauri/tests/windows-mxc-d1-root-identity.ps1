# NONPUBLISHING Windows D1 MXC process identity predicate.
# A PID/executable path match alone cannot exclude a process restart or PID reuse.
function Assert-MxcD1RootIdentity {
    [CmdletBinding()]
    param(
        $Process,
        [int]$ExpectedPid,
        [string]$ExpectedExePath,
        [string]$ExpectedStartTicks
    )
    if ($null -eq $Process -or $ExpectedPid -lt 1 -or
        [string]::IsNullOrWhiteSpace($ExpectedExePath) -or
        $ExpectedStartTicks -notmatch '^\d{15,20}$') {
        throw 'D1_MXC_ROOT_IDENTITY_NO_GO: invalid expected process identity'
    }
    if ($null -eq $Process.ProcessId -or [int]$Process.ProcessId -ne $ExpectedPid -or
        [string]$Process.Name -ine 'medorigin-desktop-d1-preview.exe' -or
        -not [string]::Equals([string]$Process.ExecutablePath, $ExpectedExePath,
            [System.StringComparison]::OrdinalIgnoreCase) -or
        $Process.CreationDate -isnot [datetime]) {
        throw 'D1_MXC_ROOT_IDENTITY_NO_GO: PID/name/path/start time unavailable or changed'
    }
    $actualTicks = [string]$Process.CreationDate.ToUniversalTime().Ticks
    if ($actualTicks -cne $ExpectedStartTicks) {
        throw 'D1_MXC_ROOT_IDENTITY_NO_GO: root process creation identity changed'
    }
    return $true
}
