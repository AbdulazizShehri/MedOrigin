# Actual Windows UI Automation acceptance for the unpublished native Rust D2.
# Synthetic in-memory fixtures only. Does not launch apps, alter the firewall,
# generate network traffic, install a browser or authorize any public release.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$AppPid,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedExeSha256
)
$ErrorActionPreference = 'Stop'
function Deny([string]$Reason) {
    [Console]::Error.WriteLine("D2_WINDOWS_UIA_NO_GO: $Reason")
    exit 1
}
try {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
} catch { Deny 'Windows UI Automation API unavailable' }

$expected = [ordered]@{
    'patient-minimal' = '747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0'
    'patient-invalid-utf8' = 'a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89'
    'patient-over-limit' = 'b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538'
    'patient-exact-limit' = 'ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e'
}
try {
    $app = Get-Process -Id $AppPid -ErrorAction Stop
    if ($app.ProcessName -ne 'medorigin-desktop-d2-native-egui') {
        Deny 'process is not the approved synthetic D2 executable'
    }
    $exePath = $app.Path
    if ([string]::IsNullOrWhiteSpace($exePath) -or
        -not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
        Deny 'native process executable path unavailable'
    }
    $actualSha = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
    if ($actualSha -ine $ExpectedExeSha256) {
        Deny 'running native executable SHA-256 does not match provided exact build identity'
    }
} catch { Deny 'approved native D2 process or binary identity not verified' }

$root = [System.Windows.Automation.AutomationElement]::RootElement
function Get-AppWindow {
    $windows = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Children,
        [System.Windows.Automation.Condition]::TrueCondition
    )
    $selected = @()
    foreach ($candidate in $windows) {
        try {
            if ($candidate.Current.ProcessId -ne $AppPid) { continue }
            if ($candidate.Current.NativeWindowHandle -ne $app.MainWindowHandle) { continue }
            if ($candidate.Current.Name -notlike 'MedOrigin Native Rust*') { continue }
            if ($candidate.Current.IsOffscreen) { continue }
            $selected += $candidate
        } catch { continue }
    }
    if ($selected.Count -eq 1) { return $selected[0] }
    return $null
}
$window = $null
for ($i=0; $i -lt 25; $i++) {
    $window=Get-AppWindow
    if ($null -ne $window) { break }
    Start-Sleep -Milliseconds 200
}
if ($null -eq $window) { Deny 'exactly one visible native D2 window not found' }
Write-Output 'D2_WINDOWS_NATIVE_WINDOW_UIA_PASS'

function Read-UI {
    # AccessKit may not publish the tree until the first native UIA request.
    return @($window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    ))
}
function Find-Control([string]$Name, [string]$Type) {
    $matches = @(Read-UI | Where-Object {
        try {
            $_.Current.Name -eq $Name -and
            $_.Current.ControlType.ProgrammaticName -eq $Type
        } catch { $false }
    })
    if ($matches.Count -ne 1) { return $null }
    return $matches[0]
}
function Invoke-Control(
    [System.Windows.Automation.AutomationElement]$Element,
    [string]$Action
) {
    if ($null -eq $Element) { Deny 'required UIA Button missing or ambiguous' }
    try {
        if ($Action -eq 'select') {
            $toggle = [System.Windows.Automation.TogglePattern]$Element.GetCurrentPattern(
                [System.Windows.Automation.TogglePattern]::Pattern
            )
            $toggle.Toggle()
        } elseif ($Action -eq 'verify') {
            $invoke = [System.Windows.Automation.InvokePattern]$Element.GetCurrentPattern(
                [System.Windows.Automation.InvokePattern]::Pattern
            )
            $invoke.Invoke()
        } else { Deny 'unknown UIA action' }
    } catch { Deny ('UIA action unsupported or failed: ' + $_.Exception.Message) }
}
$ids=@($expected.Keys)
foreach ($id in $ids) {
    $name = switch ($id) {
        'patient-minimal' { 'patient-minimal (57 bytes)' }
        'patient-invalid-utf8' { 'patient-invalid-utf8 (1 bytes)' }
        'patient-over-limit' { 'patient-over-limit (32769 bytes)' }
        'patient-exact-limit' { 'patient-exact-limit (32768 bytes)' }
    }
    $selector = $null; $verify=$null
    for ($n=0; $n -lt 20; $n++) {
        $selector = Find-Control $name 'ControlType.Button'
        $verify = Find-Control 'Verify synthetic SHA-256' 'ControlType.Button'
        if ($null -ne $selector -and $null -ne $verify) { break }
        Start-Sleep -Milliseconds 200
    }
    if ($null -eq $selector -or $null -eq $verify) {
        Deny "missing native synthetic selector or Verify for $id"
    }
    Invoke-Control $selector 'select'
    $verify = Find-Control 'Verify synthetic SHA-256' 'ControlType.Button'
    Invoke-Control $verify 'verify'
    $digest=$expected[$id]
    $found=$false
    for($n=0; $n -lt 25; $n++) {
        $textNodes=@(Read-UI | Where-Object {
            try {
                $_.Current.ControlType.ProgrammaticName -eq 'ControlType.Text' -and
                $_.Current.Name -eq "Synthetic raw SHA-256 verified: $digest"
            } catch { $false }
        })
        if ($textNodes.Count -eq 1) { $found=$true; break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $found) { Deny "native rendered SHA-256 mismatch after UIA action for $id" }
    Write-Output "D2_WINDOWS_UIA_FIXTURE_PASS $id"
}
# A bounded process-tree observation, not kernel enforced zero-egress.
try {
    $processes=@(Get-CimInstance Win32_Process)
    $known = [System.Collections.Generic.HashSet[int]]::new()
    [void]$known.Add($AppPid)
    for($round=0;$round -lt 12;$round++) {
        $added=0
        foreach($proc in $processes) {
            if ($known.Contains([int]$proc.ParentProcessId) -and $known.Add([int]$proc.ProcessId)) {
                $added++
            }
        }
        if ($added -eq 0) { break }
    }
    $descendants=@($processes | Where-Object {
        $known.Contains([int]$_.ProcessId) -and [int]$_.ProcessId -ne $AppPid
    })
    if (@($descendants | Where-Object { $_.Name -ieq 'msedgewebview2.exe' }).Count -gt 0) {
        Deny 'WebView2 child unexpectedly observed in browser-free native D2'
    }
    $connections=@(Get-NetTCPConnection -State Established -ErrorAction Stop | Where-Object {
        $known.Contains([int]$_.OwningProcess) -and
        $_.RemoteAddress -notin @('127.0.0.1', '::1', '0.0.0.0', '::', '::ffff:127.0.0.1')
    })
    if ($connections.Count -gt 0) { Deny 'non-loopback established TCP connection observed in D2 process tree' }
    Write-Output "D2_WINDOWS_PROCESS_TREE_SNAPSHOT_PASS descendants=$($descendants.Count) external_established_tcp=0"
} catch { Deny 'bounded process and TCP snapshot could not be verified' }
Write-Output 'D2_WINDOWS_NATIVE_UIA_4_OF_4_PASS_NONPUBLISHING'
