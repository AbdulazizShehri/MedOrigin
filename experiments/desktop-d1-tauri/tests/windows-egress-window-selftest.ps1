$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'windows-egress-window.ps1'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'Missing window monitor' }
$testDir = Join-Path $env:TEMP ('medorigin-egress-window-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
try {
  Copy-Item -LiteralPath $source -Destination (Join-Path $testDir 'windows-egress-window.ps1')
  $fake = @'
param([Parameter(Mandatory = $true)][int]$RootPid)
switch ($env:MEDORIGIN_WINDOW_SELFTEST) {
  'clear' { Write-Output 'D1_SNAPSHOT_NO_EXTERNAL_TCP'; exit 0 }
  'external' { Write-Output 'D1_NETWORK_ISOLATION_NO_GO'; exit 2 }
  'error' { Write-Output 'synthetic probe failure'; exit 1 }
  'unmarked' { Write-Output 'ambiguous success'; exit 0 }
  'transient' {
    $count = 0
    if (Test-Path -LiteralPath $env:MEDORIGIN_WINDOW_TEST_COUNTER) {
      $count = [int](Get-Content -LiteralPath $env:MEDORIGIN_WINDOW_TEST_COUNTER -Raw)
    }
    $count++
    [System.IO.File]::WriteAllText($env:MEDORIGIN_WINDOW_TEST_COUNTER, [string]$count)
    if ($count -ge 2) { Write-Output 'D1_NETWORK_ISOLATION_NO_GO'; exit 2 }
    Write-Output 'D1_SNAPSHOT_NO_EXTERNAL_TCP'
    exit 0
  }
  default { throw 'Unknown synthetic test scenario' }
}
'@
  [System.IO.File]::WriteAllText((Join-Path $testDir 'windows-egress-snapshot.ps1'), $fake, [System.Text.UTF8Encoding]::new($false))
  $cases = @(
    @{ name = 'clear'; code = 0; marker = 'D1_WINDOW_SNAPSHOT_CLEAR samples=' },
    @{ name = 'external'; code = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO sample=1' },
    @{ name = 'error'; code = 1; marker = 'D1_EGRESS_MONITOR_ERROR:' },
    @{ name = 'unmarked'; code = 1; marker = 'D1_EGRESS_MONITOR_ERROR:' },
    @{ name = 'transient'; code = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO sample=2' }
  )
  foreach ($case in $cases) {
    $env:MEDORIGIN_WINDOW_SELFTEST = $case.name
    $env:MEDORIGIN_WINDOW_TEST_COUNTER = Join-Path $testDir 'counter.txt'
    if (Test-Path -LiteralPath $env:MEDORIGIN_WINDOW_TEST_COUNTER) {
      Remove-Item -LiteralPath $env:MEDORIGIN_WINDOW_TEST_COUNTER
    }
    $result = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $testDir 'windows-egress-window.ps1') -RootPid 12345 -DurationSeconds 1.0 -SampleIntervalMilliseconds 100 2>&1 | Out-String
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne $case.code -or -not $result.Contains($case.marker)) {
      throw ('Monitor selftest failed: ' + $case.name + '; exit=' + $exitCode + '; text=' + $result)
    }
    Write-Output ('PASS monitor-' + $case.name + ' exit=' + $exitCode)
  }
}
finally {
  Remove-Item -LiteralPath $testDir -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item Env:MEDORIGIN_WINDOW_SELFTEST -ErrorAction SilentlyContinue
  Remove-Item Env:MEDORIGIN_WINDOW_TEST_COUNTER -ErrorAction SilentlyContinue
}
Write-Output 'D1_EGRESS_WINDOW_5_OF_5_PASS (mocked snapshots; NOT zero-egress proof)'
