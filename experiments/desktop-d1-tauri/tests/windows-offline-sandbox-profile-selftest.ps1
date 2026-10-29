# Source-only Windows regression. Creates no VM, firewall rule, or executable process.
$ErrorActionPreference = 'Stop'
$generator = Join-Path $PSScriptRoot 'windows-offline-sandbox-profile.ps1'
$root = Join-Path $env:TEMP ('medorigin-d1-sandbox-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $source = Join-Path $root 'medorigin-desktop-d1-preview.exe'
  [IO.File]::WriteAllBytes($source, [byte[]](0x4d, 0x5a, 0x00, 0x01))
  $output = Join-Path $root 'profile & synthetic'
  $logs = @(& $generator -ExePath $source -OutputDirectory $output)
  if (-not ($logs -match 'D1_SANDBOX_PROFILE_CREATED=')) {
    throw 'Generator did not emit profile path'
  }
  $profile = Join-Path $output 'medorigin-synthetic-offline.wsb'
  $payload = Join-Path $output 'synthetic-executable-only'
  $copied = Join-Path $payload 'medorigin-desktop-d1-preview.exe'
  if (-not (Test-Path -LiteralPath $profile -PathType Leaf) -or
      -not (Test-Path -LiteralPath $copied -PathType Leaf)) {
    throw 'Profile or synthetic executable staging missing'
  }
  $raw = [IO.File]::ReadAllText($profile)
  [xml]$xml = $raw
  $cfg = $xml.Configuration
  foreach ($setting in @('Networking','VGpu','AudioInput','VideoInput',
                         'ClipboardRedirection','PrinterRedirection')) {
    if ($cfg.$setting -ne 'Disable') { throw ('Unsafe Sandbox setting: ' + $setting) }
  }
  if ($cfg.ProtectedClient -ne 'Enable') { throw 'Protected Client not enabled' }
  $mappings = @($cfg.MappedFolders.MappedFolder)
  if ($mappings.Count -ne 1) { throw 'Expected exactly one mapped folder' }
  if ($mappings[0].HostFolder -ne $payload -or
      $mappings[0].SandboxFolder -ne 'C:\MedOriginSyntheticOnly' -or
      $mappings[0].ReadOnly -ne 'true') {
    throw ('Profile mapped-folder boundary mismatch: host expected=['+$payload+'] actual=['+$mappings[0].HostFolder+'] sandbox=['+$mappings[0].SandboxFolder+'] readonly=['+$mappings[0].ReadOnly+']')
  }
  if ($raw -notmatch '&amp;' -or $cfg.LogonCommand) {
    throw 'Expected XML escaping and no autorun command'
  }
  if (@(Get-ChildItem -LiteralPath $output -Recurse -File).Count -ne 2) {
    throw 'Unexpected host content exposed to Sandbox'
  }
  if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne
      (Get-FileHash -LiteralPath $copied -Algorithm SHA256).Hash) {
    throw 'Staged executable does not match source'
  }
  $bad = Join-Path $root 'not-the-d1-preview.exe'
  [IO.File]::WriteAllBytes($bad, [byte[]](0x4d, 0x5a))
  $denied = $false
  try { & $generator -ExePath $bad -OutputDirectory (Join-Path $root 'bad-output') | Out-Null }
  catch { $denied = $true }
  if (-not $denied -or (Test-Path -LiteralPath (Join-Path $root 'bad-output'))) {
    throw 'Unexpected executable name was not rejected before staging'
  }
  Write-Output 'D1_OFFLINE_SANDBOX_PROFILE_SELFTEST_PASS (source-only; sandbox NOT launched)'
}
finally {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
