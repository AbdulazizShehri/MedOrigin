$ErrorActionPreference = 'Stop'
$probe = Join-Path $PSScriptRoot 'windows-egress-snapshot.ps1'
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) { throw 'Missing D1 egress probe' }
$testDir = Join-Path $env:TEMP ('medorigin-d1-egress-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
try {
  $cases = @(
    @{ name = 'synsent'; expected = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO' },
    @{ name = 'established'; expected = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO' },
    @{ name = 'grandchild-external'; expected = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO' },
    @{ name = 'unrelated-external'; expected = 0; marker = 'D1_SNAPSHOT_NO_EXTERNAL_TCP' },
    @{ name = 'missing-root'; expected = 1; marker = 'D1 root process absent' },
    @{ name = 'missing-creation'; expected = 1; marker = 'D1 root creation timestamp unavailable' },
    @{ name = 'root-exit-mid-snapshot'; expected = 1; marker = 'D1 root process changed during snapshot' },
    @{ name = 'pid-reused'; expected = 1; marker = 'D1 root process changed during snapshot' },
    @{ name = 'child-exit-mid-snapshot'; expected = 1; marker = 'D1 child process changed during snapshot' },
    @{ name = 'child-pid-reused'; expected = 1; marker = 'D1 child process changed during snapshot' },
    @{ name = 'child-reparented'; expected = 1; marker = 'D1 child process changed during snapshot' },
    @{ name = 'missing-child-creation'; expected = 1; marker = 'D1 child process changed during snapshot' },
    @{ name = 'query-error'; expected = 1; marker = 'synthetic socket query failure' },
    @{ name = 'process-error'; expected = 1; marker = 'synthetic process query failure' },
    @{ name = 'udp-error'; expected = 1; marker = 'synthetic UDP query failure' },
    @{ name = 'loopback'; expected = 0; marker = 'D1_SNAPSHOT_NO_EXTERNAL_TCP' }
  )
  foreach ($case in $cases) {
    $launcher = Join-Path $testDir ($case.name + '.ps1')
    $script = @'
function Get-CimInstance {
  [CmdletBinding()] param([string]$ClassName, [string]$Filter)
  $script:processQueries++
  if ('__SCENARIO__' -eq 'process-error') { throw 'synthetic process query failure' }
  if ('__SCENARIO__' -eq 'missing-root') {
    [pscustomobject]@{ ProcessId = 45678; ParentProcessId = 0; CreationDate = '2026-10-29T00:00:00' }
    return
  }
  if ('__SCENARIO__' -eq 'root-exit-mid-snapshot' -and $script:processQueries -gt 1) { return }
  $creation = '2026-10-29T00:00:00'
  if ('__SCENARIO__' -eq 'pid-reused' -and $script:processQueries -gt 1) { $creation = '2026-10-29T00:00:01' }
  if ('__SCENARIO__' -eq 'missing-creation') { $creation = $null }
  [pscustomobject]@{ ProcessId = 12345; ParentProcessId = 0; CreationDate = $creation }
  if ('__SCENARIO__' -eq 'grandchild-external') {
    [pscustomobject]@{ ProcessId = 23456; ParentProcessId = 12345; CreationDate = '2026-10-29T00:00:01' }
    [pscustomobject]@{ ProcessId = 34567; ParentProcessId = 23456; CreationDate = '2026-10-29T00:00:02' }
  }
  if ('__SCENARIO__' -in @('child-exit-mid-snapshot','child-pid-reused','child-reparented','missing-child-creation')) {
    if (-not ('__SCENARIO__' -eq 'child-exit-mid-snapshot' -and $script:processQueries -gt 1)) {
      $childCreation = '2026-10-29T00:00:01'
      if ('__SCENARIO__' -eq 'missing-child-creation') { $childCreation = $null }
      if ('__SCENARIO__' -eq 'child-pid-reused' -and $script:processQueries -gt 1) { $childCreation = '2026-10-29T00:00:03' }
      $childParent = 12345
      if ('__SCENARIO__' -eq 'child-reparented' -and $script:processQueries -gt 1) { $childParent = 45678 }
      [pscustomobject]@{ ProcessId = 23456; ParentProcessId = $childParent; CreationDate = $childCreation }
    }
  }
  if ('__SCENARIO__' -eq 'unrelated-external') {
    [pscustomobject]@{ ProcessId = 45678; ParentProcessId = 0 }
  }
}
function Get-NetTCPConnection {
  [CmdletBinding()] param()
  if ('__SCENARIO__' -eq 'query-error') { throw 'synthetic socket query failure' }
  if ('__SCENARIO__' -eq 'synsent') {
    [pscustomobject]@{ OwningProcess = 12345; RemoteAddress = '2001:db8::1'; RemotePort = 443; State = 'SynSent' }
  }
  if ('__SCENARIO__' -eq 'established') {
    [pscustomobject]@{ OwningProcess = 12345; RemoteAddress = '2001:db8::2'; RemotePort = 443; State = 'Established' }
  }
  if ('__SCENARIO__' -eq 'grandchild-external') {
    [pscustomobject]@{ OwningProcess = 34567; RemoteAddress = '2001:db8::3'; RemotePort = 443; State = 'SynSent' }
  }
  if ('__SCENARIO__' -eq 'unrelated-external') {
    [pscustomobject]@{ OwningProcess = 45678; RemoteAddress = '2001:db8::4'; RemotePort = 443; State = 'Established' }
  }
  if ('__SCENARIO__' -eq 'loopback') {
    [pscustomobject]@{ OwningProcess = 12345; RemoteAddress = '127.0.0.1'; RemotePort = 80; State = 'Established' }
  }
}
function Get-NetUDPEndpoint {
  [CmdletBinding()] param()
  if ('__SCENARIO__' -eq 'udp-error') { throw 'synthetic UDP query failure' }
}
$script:processQueries = 0
& '__PROBE__' -RootPid 12345
exit $LASTEXITCODE
'@
    $script = $script.Replace('__SCENARIO__', $case.name).Replace('__PROBE__', $probe.Replace("'", "''"))
    [System.IO.File]::WriteAllText($launcher, $script, [System.Text.UTF8Encoding]::new($false))
    $ErrorActionPreference = 'Continue' # Expected negative test writes to stderr.
    try {
      $output = @(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher 2>&1 | Out-String)
      $exitCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = 'Stop' }
    $text = $output -join [Environment]::NewLine
    if ($exitCode -ne $case.expected -or -not $text.Contains($case.marker)) {
      throw ('Egress probe regression: ' + $case.name + ' exit=' + $exitCode + ' output=' + $text)
    }
    Write-Output ('PASS egress-probe-' + $case.name + ' exit=' + $exitCode)
  }
}
finally {
  Remove-Item -LiteralPath $testDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output 'D1_EGRESS_PROBE_16_OF_16_PASS (mocked sockets only; NOT zero-egress proof)'
