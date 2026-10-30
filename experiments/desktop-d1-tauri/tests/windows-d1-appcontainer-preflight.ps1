# Read-only D1 process token audit. No networking, firewall edits, launch or release approval.
# Live: powershell -File windows-d1-appcontainer-preflight.ps1 -RootPid 123 -ExpectedExePath 'D:\...\medorigin-desktop-d1-preview.exe'
# Test: powershell -File windows-d1-appcontainer-preflight.ps1 -SelfTest
[CmdletBinding()]
param(
    [ValidateRange(1, 2147483647)][int]$RootPid = 1,
    [string]$ExpectedExePath = '',
    [switch]$SelfTest,
    [switch]$NativeSelfTest
)
$ErrorActionPreference = 'Stop'

function Get-D1TokenVerdict {
    param(
        [int]$Build,
        [bool]$RootIdentityMatches,
        [bool]$ProcessTreeStable,
        [object[]]$ProcessEvidence
    )
    if ($Build -lt 26100) { return 'D1_OS_BUILD_UNSUPPORTED_NO_GO' }
    if (-not $RootIdentityMatches) { return 'D1_ROOT_IDENTITY_UNVERIFIED_NO_GO' }
    if (-not $ProcessTreeStable) { return 'D1_PROCESS_TREE_CHANGED_NO_GO' }
    if ($null -eq $ProcessEvidence -or $ProcessEvidence.Count -lt 2) {
        return 'D1_PROCESS_TREE_UNVERIFIED_NO_GO'
    }
    if (@($ProcessEvidence | Where-Object { $_.Name -ieq 'msedgewebview2.exe' }).Count -lt 1) {
        return 'D1_WEBVIEW2_NOT_OBSERVED_NO_GO'
    }
    if (@($ProcessEvidence | Where-Object { $_.IsAppContainer -ne 1 }).Count -gt 0) {
        return 'D1_FULLTRUST_OR_TOKEN_UNVERIFIED_NO_GO'
    }
    if (@($ProcessEvidence | Where-Object { $_.NetworkCapabilityState -ne 0 }).Count -gt 0) {
        return 'D1_NETWORK_CAPABILITY_PRESENT_OR_UNVERIFIED_NO_GO'
    }
    # Known network-capability SIDs are absent in the observed token snapshot.
    return 'D1_TOKEN_PRECHECK_ONLY_NETWORK_ISOLATION_NO_GO'
}

if ($SelfTest) {
    $restricted = @(
        [pscustomobject]@{ Name = 'medorigin-desktop-d1-preview.exe'; IsAppContainer = 1; NetworkCapabilityState = 0 },
        [pscustomobject]@{ Name = 'msedgewebview2.exe'; IsAppContainer = 1; NetworkCapabilityState = 0 }
    )
    $cases = @(
        @{Name='restricted-precheck'; Build=26100; Identity=$true; Stable=$true; Rows=$restricted; Expected='D1_TOKEN_PRECHECK_ONLY_NETWORK_ISOLATION_NO_GO'},
        @{Name='unsupported-fallback'; Build=19045; Identity=$true; Stable=$true; Rows=$restricted; Expected='D1_OS_BUILD_UNSUPPORTED_NO_GO'},
        @{Name='root-mismatch'; Build=26100; Identity=$false; Stable=$true; Rows=$restricted; Expected='D1_ROOT_IDENTITY_UNVERIFIED_NO_GO'},
        @{Name='process-race'; Build=26100; Identity=$true; Stable=$false; Rows=$restricted; Expected='D1_PROCESS_TREE_CHANGED_NO_GO'},
        @{Name='absent-child'; Build=26100; Identity=$true; Stable=$true; Rows=@($restricted[0]); Expected='D1_PROCESS_TREE_UNVERIFIED_NO_GO'},
        @{Name='no-webview'; Build=26100; Identity=$true; Stable=$true; Rows=@([pscustomobject]@{Name='app.exe';IsAppContainer=1},[pscustomobject]@{Name='helper.exe';IsAppContainer=1}); Expected='D1_WEBVIEW2_NOT_OBSERVED_NO_GO'},
        @{Name='fulltrust-child'; Build=26100; Identity=$true; Stable=$true; Rows=@($restricted[0],[pscustomobject]@{Name='msedgewebview2.exe';IsAppContainer=0}); Expected='D1_FULLTRUST_OR_TOKEN_UNVERIFIED_NO_GO'},
        @{Name='unknown-token'; Build=26100; Identity=$true; Stable=$true; Rows=@($restricted[0],[pscustomobject]@{Name='msedgewebview2.exe';IsAppContainer=-1}); Expected='D1_FULLTRUST_OR_TOKEN_UNVERIFIED_NO_GO'}
    )
    $cases += @(
        @{Name='browser-internetclient'; Build=26100; Identity=$true; Stable=$true; Rows=@($restricted[0],[pscustomobject]@{Name='msedgewebview2.exe';IsAppContainer=1;NetworkCapabilityState=1}); Expected='D1_NETWORK_CAPABILITY_PRESENT_OR_UNVERIFIED_NO_GO'},
        @{Name='browser-capability-unreadable'; Build=26100; Identity=$true; Stable=$true; Rows=@($restricted[0],[pscustomobject]@{Name='msedgewebview2.exe';IsAppContainer=1;NetworkCapabilityState=-1}); Expected='D1_NETWORK_CAPABILITY_PRESENT_OR_UNVERIFIED_NO_GO'}
    )
    foreach ($case in $cases) {
        $verdict = Get-D1TokenVerdict -Build $case.Build -RootIdentityMatches $case.Identity -ProcessTreeStable $case.Stable -ProcessEvidence $case.Rows
        if ($verdict -ne $case.Expected) { throw ('D1 token logic failed: ' + $case.Name) }
    }
    Write-Output 'D1_TOKEN_LOGIC_10_OF_10_PASS_NOT_LIVE_OR_NETWORK_PROOF'
    Write-Output 'D1_NETWORK_ISOLATION_NO_GO'
    exit 0
}
if (-not $NativeSelfTest -and [string]::IsNullOrWhiteSpace($ExpectedExePath)) {
    Write-Output 'D1_TOKEN_AUDIT_INCONCLUSIVE: expected executable path required'
    exit 1
}
# No token modifications; inspect AppContainer and bounded network capability SIDs.
$native = @'
using System;
using System.Runtime.InteropServices;
public static class MedOriginD1AppContainerToken {
    private const uint QUERY_LIMITED = 0x1000;
    private const uint TOKEN_QUERY = 0x0008;
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint desired, bool inherit, uint pid);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(IntPtr process, uint desired, out IntPtr token);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetTokenInformation(IntPtr token, int infoClass,
        out int value, int length, out int returned);
    [DllImport("advapi32.dll", EntryPoint = "GetTokenInformation", SetLastError = true)]
    private static extern bool GetTokenInformationBuffer(IntPtr token, int infoClass,
        IntPtr buffer, int length, out int returned);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertSidToStringSid(IntPtr sid, out IntPtr value);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr value);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);
    public static int IsAppContainer(int processId) {
        IntPtr process = OpenProcess(QUERY_LIMITED, false, (uint)processId);
        if (process == IntPtr.Zero) return -1;
        IntPtr token = IntPtr.Zero;
        try {
            if (!OpenProcessToken(process, TOKEN_QUERY, out token)) return -1;
            int value = 0;
            int returned = 0;
            // TOKEN_INFORMATION_CLASS::TokenIsAppContainer = 29, DWORD.
            if (!GetTokenInformation(token, 29, out value, 4, out returned)
                || returned != 4) return -1;
            return value != 0 ? 1 : 0;
        } finally {
            if (token != IntPtr.Zero) CloseHandle(token);
            CloseHandle(process);
        }
    }

    // Return 1 when known internet/network SIDs exist, 0 when none appear,
    // -1 for any failed, unknown or malformed token read. Never output SIDs.
    // TokenCapabilities = 30, TOKEN_GROUPS of SID_AND_ATTRIBUTES.
    public static int NetworkCapabilityState(int processId) {
        IntPtr process = OpenProcess(QUERY_LIMITED, false, (uint)processId);
        if (process == IntPtr.Zero) return -1;
        IntPtr token = IntPtr.Zero;
        IntPtr buffer = IntPtr.Zero;
        try {
            if (!OpenProcessToken(process, TOKEN_QUERY, out token)) return -1;
            int needed = 0;
            GetTokenInformationBuffer(token, 30, IntPtr.Zero, 0, out needed);
            if (needed < 4 || needed > 65536) return -1;
            buffer = Marshal.AllocHGlobal(needed);
            int actual = 0;
            if (!GetTokenInformationBuffer(token, 30, buffer, needed, out actual)
                || actual < 4 || actual > needed) return -1;
            int count = Marshal.ReadInt32(buffer, 0);
            if (count < 0 || count > 512) return -1;
            if (count == 0) return 0;
            int offset = IntPtr.Size == 8 ? 8 : 4;
            int stride = IntPtr.Size == 8 ? 16 : 8;
            if (offset + (long)count * stride > actual) return -1;
            for (int i = 0; i < count; i++) {
                IntPtr sid = Marshal.ReadIntPtr(buffer, offset + i * stride);
                if (sid == IntPtr.Zero) return -1;
                IntPtr sidString = IntPtr.Zero;
                if (!ConvertSidToStringSid(sid, out sidString)) return -1;
                try {
                    string value = Marshal.PtrToStringUni(sidString);
                    if (value == null) return -1;
                    if (value == "S-1-15-3-1" || value == "S-1-15-3-2"
                        || value == "S-1-15-3-3") return 1;
                } finally {
                    if (sidString != IntPtr.Zero) LocalFree(sidString);
                }
            }
            return 0;
        } catch {
            return -1;
        } finally {
            if (buffer != IntPtr.Zero) Marshal.FreeHGlobal(buffer);
            if (token != IntPtr.Zero) CloseHandle(token);
            CloseHandle(process);
        }
    }
}
'@
try {
    if (-not ([System.Management.Automation.PSTypeName]'MedOriginD1AppContainerToken').Type) {
        Add-Type -TypeDefinition $native -ErrorAction Stop
    }
    if ($NativeSelfTest) {
        $flag = [MedOriginD1AppContainerToken]::IsAppContainer($PID)
        if ($flag -notin @(0, 1)) { throw 'Read-only Win32 token API returned unknown status' }
        $capabilities = [MedOriginD1AppContainerToken]::NetworkCapabilityState($PID)
        if ($capabilities -notin @(0, 1)) { throw 'Read-only Win32 TokenCapabilities API returned unknown status' }
        Write-Output 'D1_NATIVE_TOKEN_API_READ_PASS_NOT_ISOLATION_PROOF'
        Write-Output 'D1_NETWORK_ISOLATION_NO_GO'
        exit 0
    }
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $build = [int]$os.BuildNumber
    $before = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $root = @($before | Where-Object { $_.ProcessId -eq $RootPid })
    if ($root.Count -ne 1 -or -not $root[0].ExecutablePath) {
        Write-Output 'D1_ROOT_IDENTITY_UNVERIFIED_NO_GO'
        exit 2
    }
    $sameRoot = [string]::Equals(
        [IO.Path]::GetFullPath($ExpectedExePath),
        [IO.Path]::GetFullPath([string]$root[0].ExecutablePath),
        [StringComparison]::OrdinalIgnoreCase
    )
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    [void]$ids.Add($RootPid)
    do {
        $changed = $false
        foreach ($p in $before) {
            if ($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)) {
                [void]$ids.Add([int]$p.ProcessId)
                $changed = $true
            }
        }
    } while ($changed)
    $rows = @(
        foreach ($p in $before) {
            if ($ids.Contains([int]$p.ProcessId)) {
                [pscustomobject]@{
                    Name = [string]$p.Name
                    IsAppContainer = [MedOriginD1AppContainerToken]::IsAppContainer([int]$p.ProcessId)
                    NetworkCapabilityState = [MedOriginD1AppContainerToken]::NetworkCapabilityState([int]$p.ProcessId)
                }
            }
        }
    )
    $after = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $currentRoot = @($after | Where-Object { $_.ProcessId -eq $RootPid })
    $stable = $currentRoot.Count -eq 1 -and [string]$currentRoot[0].CreationDate -eq [string]$root[0].CreationDate
    if ($stable) {
        $afterIds = [System.Collections.Generic.HashSet[int]]::new()
        [void]$afterIds.Add($RootPid)
        do {
            $changed = $false
            foreach ($p in $after) {
                if ($afterIds.Contains([int]$p.ParentProcessId) -and -not $afterIds.Contains([int]$p.ProcessId)) {
                    [void]$afterIds.Add([int]$p.ProcessId)
                    $changed = $true
                }
            }
        } while ($changed)
        $stable = $ids.SetEquals($afterIds)
    }
    $result = Get-D1TokenVerdict -Build $build -RootIdentityMatches $sameRoot -ProcessTreeStable $stable -ProcessEvidence $rows
    Write-Output $result
    Write-Output 'D1_NETWORK_ISOLATION_NO_GO'
    if ($result -eq 'D1_TOKEN_PRECHECK_ONLY_NETWORK_ISOLATION_NO_GO') { exit 0 }
    exit 2
} catch {
    Write-Output 'D1_TOKEN_AUDIT_INCONCLUSIVE'
    Write-Output 'D1_NETWORK_ISOLATION_NO_GO'
    exit 1
}
