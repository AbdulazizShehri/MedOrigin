# Experimental developer-only cleanup; never targets the shared WebView2 executable globally.
function Stop-MxcOwnedProcessTree {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][int]$RootPid,
        [Parameter(Mandatory = $true)][string]$ExePath,
        [Parameter(Mandatory = $true)][datetime]$ExpectedCreationDate
    )
    if ($RootPid -le 0) { throw 'Invalid owned process PID' }
    $root = Get-CimInstance Win32_Process -Filter "ProcessId=$RootPid" -ErrorAction Stop
    if (-not $root) {
        # Windows may leave native descendants alive after their parent exits.
        # A missing root alone is not proof that its process tree was cleaned.
        # Do not kill by an unverified, potentially recycled parent PID.
        $possibleOrphans = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$RootPid" -ErrorAction Stop |
            Where-Object { [datetime]$_.CreationDate -ge $ExpectedCreationDate })
        if ($possibleOrphans.Count -gt 0) {
            throw 'MXC cleanup root exited with possible surviving descendants; refusing unverified termination'
        }
        return
    }
    if ($root.ExecutablePath -ine $ExePath -or
        [datetime]$root.CreationDate -ne $ExpectedCreationDate) {
        throw 'MXC cleanup process identity changed; refusing unrelated termination'
    }

    # Capture the exact observed descendants for post-termination verification.
    $all = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $known = @($RootPid)
    do {
        $before = $known.Count
        foreach ($process in $all) {
            if ($known -contains [int]$process.ParentProcessId -and
                $known -notcontains [int]$process.ProcessId) {
                $known += [int]$process.ProcessId
            }
        }
    } while ($known.Count -gt $before)

    # taskkill /T is scoped to this verified root PID and its children only.
    $result = @(& taskkill.exe /PID $RootPid /T /F 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw ('MXC owned-process tree termination failed: ' + ($result -join '; '))
    }
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $remaining = @($known | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
        if ($remaining.Count -eq 0) { return }
        Start-Sleep -Milliseconds 100
    }
    throw ('MXC owned-process tree remained after cleanup: ' + ($remaining -join ','))
}