# Synthetic process-tree cleanup regression. No MedOrigin app, network, or admin changes.
$ErrorActionPreference = 'Stop'
$helper = Join-Path $PSScriptRoot 'windows-mxc-owned-process-cleanup.ps1'
if (-not (Test-Path -LiteralPath $helper)) { throw 'Missing MXC owned-process cleanup helper' }
. $helper
$exe = (Get-Command powershell.exe -ErrorAction Stop).Source
$fixture = Join-Path $env:TEMP ('medorigin-mxc-cleanup-' + [guid]::NewGuid().ToString('N') + '.ps1')
$root = $null
$childId = $null
try {
    Set-Content -LiteralPath $fixture -Encoding UTF8 -Value @'
Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile', '-Command', 'Start-Sleep -Seconds 40') | Out-Null
Start-Sleep -Seconds 40
'@
    $root = Start-Process -FilePath $exe -ArgumentList @('-NoProfile', '-File', ('"' + $fixture + '"')) -PassThru
    $record = $null
    for ($i = 0; $i -lt 30; $i++) {
        $record = Get-CimInstance Win32_Process -Filter "ProcessId=$($root.Id)" -ErrorAction Stop
        $child = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($root.Id)" -ErrorAction Stop |
            Where-Object { $_.Name -eq 'powershell.exe' })
        if ($record -and $child.Count -eq 1) { $childId = [int]$child[0].ProcessId; break }
        Start-Sleep -Milliseconds 100
    }
    if (-not $childId) { throw 'Synthetic child not created' }
    $wrongPath = Join-Path $env:WINDIR 'System32\notepad.exe'
    $rejected = $false
    try {
        Stop-MxcOwnedProcessTree -RootPid $root.Id -ExePath $wrongPath -ExpectedCreationDate $record.CreationDate
    } catch { $rejected = $true }
    if (-not $rejected) { throw 'Mismatched executable path accepted' }
    if (-not (Get-Process -Id $root.Id -ErrorAction SilentlyContinue)) {
        throw 'Identity mismatch killed synthetic root'
    }
    Stop-MxcOwnedProcessTree -RootPid $root.Id -ExePath $exe -ExpectedCreationDate $record.CreationDate
    Start-Sleep -Milliseconds 700
    if (Get-Process -Id $root.Id -ErrorAction SilentlyContinue) { throw 'Synthetic root survived cleanup' }
    if (Get-Process -Id $childId -ErrorAction SilentlyContinue) { throw 'Synthetic descendant survived cleanup' }
    Write-Output 'MXC_CLEANUP_SELFTEST_2_OF_2_PASS'
} finally {
    if ($childId) { Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue }
    if ($root) { Stop-Process -Id $root.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $fixture -Force -ErrorAction SilentlyContinue
}