# Source-only Windows regression. Creates no VM, firewall rule, or executable process.
$ErrorActionPreference = 'Stop'
$generator = Join-Path $PSScriptRoot 'windows-offline-sandbox-profile.ps1'
$root = Join-Path $env:TEMP ('medorigin-d1-sandbox-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $source = Join-Path $root 'medorigin-desktop-d1-preview.exe'
  [IO.File]::WriteAllBytes($source, [byte[]](0x4d, 0x5a, 0x00, 0x01))
  $output = Join-Path $root 'profile & synthetic'
  $approvedSha = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  $logs = @(& $generator -ExePath $source -OutputDirectory $output -ExpectedSha256 $approvedSha)
  if (-not ($logs -match ('D1_SOURCE_SHA256=' + $approvedSha))) {
    throw 'Staging receipt omitted the pinned source digest'
  }
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
  # Windows runners can expose the same folder via short (RUNNER~1) and long
  # (runneradmin) paths. Resolve BOTH sides through the filesystem before
  # comparing; never allow the XML to map an unrelated physical directory.
  $expectedHost = (Get-Item -LiteralPath $payload -ErrorAction Stop).FullName
  $mappedHost = (Get-Item -LiteralPath ([string]$mappings[0].HostFolder) -ErrorAction Stop).FullName
  if (-not [string]::Equals($mappedHost, $expectedHost, [StringComparison]::OrdinalIgnoreCase) -or
      $mappings[0].SandboxFolder -ne 'C:\MedOriginSyntheticOnly' -or
      $mappings[0].ReadOnly -ne 'true') {
    throw 'Profile mapped-folder boundary mismatch (canonical host path, sandbox target, or read-only mode)'
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
  try { & $generator -ExePath $bad -OutputDirectory (Join-Path $root 'bad-output') -ExpectedSha256 $approvedSha | Out-Null }
  catch { $denied = $true }
  if (-not $denied -or (Test-Path -LiteralPath (Join-Path $root 'bad-output'))) {
    throw 'Unexpected executable name was not rejected before staging'
  }
  # A correctly named file with an unexpected digest is not authorized to stage.
  $wrongSha = if ($approvedSha -eq ('0' * 64)) { '1' * 64 } else { '0' * 64 }
  foreach ($scenario in @(
    @{ name = 'wrong-digest'; digest = $wrongSha },
    @{ name = 'malformed-digest'; digest = 'not-a-sha256' }
  )) {
    $denied = $false
    $rejectedOutput = Join-Path $root $scenario.name
    try { & $generator -ExePath $source -OutputDirectory $rejectedOutput -ExpectedSha256 $scenario.digest | Out-Null }
    catch { $denied = $true }
    if (-not $denied -or (Test-Path -LiteralPath $rejectedOutput)) {
      throw ('Unapproved source hash allowed staging: ' + $scenario.name)
    }
  }
  Write-Output 'D1_OFFLINE_SANDBOX_PROFILE_SELFTEST_PASS (pinned SHA-256; source-only; sandbox NOT launched)'
}
finally {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
