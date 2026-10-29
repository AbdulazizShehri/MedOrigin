# Generate a manually launched, network-disabled Windows Sandbox profile.
# Synthetic D1 preview only. Does NOT certify normal-host WebView2 egress.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference = 'Stop'

# Refuse UNC, drive-relative and other nonlocal inputs BEFORE reading the file.
# A normal file lookup or hash on a UNC path could otherwise trigger SMB I/O.
if ($ExePath -notmatch '^[A-Za-z]:\\' -or $OutputDirectory -notmatch '^[A-Za-z]:\\') {
  throw 'Only absolute local drive paths are allowed'
}
$source = Get-Item -LiteralPath $ExePath -ErrorAction Stop
if ($source.PSIsContainer -or $source.Name -cne 'medorigin-desktop-d1-preview.exe') {
  throw 'Only the synthetic MedOrigin D1 preview executable is permitted'
}
if (($source.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
  throw 'Refusing source executable reparse point'
}
# Matching staged bytes does not establish source identity. Pin the approved build hash.
$actualSourceSha256 = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
if (-not [string]::Equals($actualSourceSha256, $ExpectedSha256, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Source executable SHA-256 differs from the caller-pinned expected digest'
}
$root = [IO.Path]::GetFullPath($OutputDirectory)
if ($source.FullName -notmatch '^[A-Za-z]:\\' -or $root -notmatch '^[A-Za-z]:\\') {
  throw 'Only absolute local drive paths are allowed'
}
if (Test-Path -LiteralPath $root) {
  throw 'Output directory must not already exist'
}
$parent = Split-Path -Path $root -Parent
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
  throw 'Create the parent output directory explicitly before generating the profile'
}
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $payload = Join-Path $root 'synthetic-executable-only'
  New-Item -ItemType Directory -Path $payload -ErrorAction Stop | Out-Null
  $copy = Join-Path $payload $source.Name
  Copy-Item -LiteralPath $source.FullName -Destination $copy -ErrorAction Stop
  if ((Get-FileHash -LiteralPath $copy -Algorithm SHA256 -ErrorAction Stop).Hash -ne $actualSourceSha256) {
    throw 'Staged executable SHA-256 mismatch'
  }
  $escapedFolder = [Security.SecurityElement]::Escape($payload)
  $configuration = @"
<Configuration>
  <Networking>Disable</Networking>
  <VGpu>Disable</VGpu>
  <AudioInput>Disable</AudioInput>
  <VideoInput>Disable</VideoInput>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <PrinterRedirection>Disable</PrinterRedirection>
  <ProtectedClient>Enable</ProtectedClient>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$escapedFolder</HostFolder>
      <SandboxFolder>C:\MedOriginSyntheticOnly</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
</Configuration>
"@
  [xml]$check = $configuration
  if ($check.Configuration.Networking -ne 'Disable' -or
      $check.Configuration.MappedFolders.MappedFolder.ReadOnly -ne 'true') {
    throw 'Generated sandbox profile violates required isolation flags'
  }
  $profile = Join-Path $root 'medorigin-synthetic-offline.wsb'
  [IO.File]::WriteAllText($profile, $configuration, [Text.UTF8Encoding]::new($false))
}
catch {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
  throw
}
Write-Output ('D1_SOURCE_SHA256=' + $actualSourceSha256)
Write-Output ('D1_SANDBOX_PROFILE_CREATED=' + $profile)
Write-Output 'Do not launch automatically. Inspect the profile and then open manually on a Windows host with Windows Sandbox available.'
Write-Output 'The mapped folder contains only a SHA-256-verified copy of the synthetic preview executable.'
Write-Output 'This isolation rehearsal does NOT establish app-level zero egress on a normal host, PHI authorization, or release readiness.'
