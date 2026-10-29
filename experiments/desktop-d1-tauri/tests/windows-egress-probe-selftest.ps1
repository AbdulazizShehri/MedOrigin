$ErrorActionPreference = 'Stop'
$probe = Join-Path $PSScriptRoot 'windows-egress-snapshot.ps1'
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) { throw 'Missing D1 egress probe' }
$testDir = Join-Path $env:TEMP ('medorigin-d1-egress-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
try {
  $cases = @(
    @{ name = 'synsent'; expected = 2; marker = 'D1_NETWORK_ISOLATION_NO_GO' },
    @{ name = 'query-error'; expected = 1; marker = 'synthetic socket query failure' },
    @{ name = 'loopback'; expected = 0; marker = 'D1_SNAPSHOT_NO_EXTERNAL_TCP' }
  )
  foreach ($case in $cases) {
    $launcher = Join-Path $testDir ($case.name + '.ps1')
    $script = @'
function Get-CimInstance {
  [CmdletBinding()] param([string]$ClassName)
  [pscustomobject]@{ ProcessId = 12345; ParentProcessId = 0 }
}
function Get-NetTCPConnection {
  [CmdletBinding()] param()
  if ('__SCENARIO__' -eq 'query-error') { throw 'synthetic socket query failure' }
  if ('__SCENARIO__' -eq 'synsent') {
    [pscustomobject]@{ OwningProcess = 12345; RemoteAddress = '2001:db8::1'; RemotePort = 443; State = 'SynSent' }
  }
  if ('__SCENARIO__' -eq 'loopback') {
    [pscustomobject]@{ OwningProcess = 12345; RemoteAddress = '127.0.0.1'; RemotePort = 80; State = 'Established' }
  }
}
function Get-NetUDPEndpoint { [CmdletBinding()] param() }
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
Write-Output 'D1_EGRESS_PROBE_3_OF_3_PASS (mocked sockets only; NOT zero-egress proof)'
