# Source-only negative tests for host qualification; no app is launched.
$ErrorActionPreference='Stop'
$qual=Join-Path $PSScriptRoot 'windows-host-qualification.ps1'
$root=Join-Path $env:TEMP ('medorigin-host-qual-selftest-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $exe=Join-Path $root 'medorigin-desktop-d1-preview.exe'
  [IO.File]::WriteAllBytes($exe,[byte[]](0x4d,0x5a,0x00,0x01))
  $good=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  $badHash=if($good -eq ('0'*64)){'1'*64}else{'0'*64}
  $wrongName=Join-Path $root 'untrusted.exe'
  [IO.File]::WriteAllBytes($wrongName,[byte[]](0x4d,0x5a))
  $cases=@(
    @{name='digest';source=$exe;digest=$badHash},
    @{name='name';source=$wrongName;digest=(Get-FileHash -LiteralPath $wrongName -Algorithm SHA256).Hash},
    @{name='relative';source=$exe;digest=$good;relative=$true}
  )
  foreach($c in $cases) {
    $audit=Join-Path $root ('refused-'+$c.name)
    if($c.relative){$audit='medorigin-host-qual-refuse-'+[guid]::NewGuid().ToString('N')}
    $output=@(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $qual -ExePath $c.source -ExpectedSha256 $c.digest -AuditDirectory $audit 2>&1 | Out-String)
    $code=$LASTEXITCODE
    $joined=$output -join [Environment]::NewLine
    if($code -eq 0 -or $joined -notmatch 'D1_HOST_QUALIFICATION_ERROR=' -or (Test-Path -LiteralPath $audit)) {
      throw ('Host qualification did not fail closed for '+$c.name)
    }
    Write-Output ('PASS host-qualification-'+$c.name)
  }
}
finally {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output 'D1_HOST_QUALIFICATION_NEGATIVE_3_OF_3_PASS (no app or Sandbox launched)'
