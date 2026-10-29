# Stage only an approved synthetic desktop preview in a fresh fixed-drive folder.
# Source-only helper; never launches an executable or creates an installer.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ExpectedSha256,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
function Assert-FixedPath([string]$candidate,[bool]$mustExist) {
  if($candidate -notmatch '^[A-Za-z]:\\'){throw 'Only absolute drive-rooted paths are allowed'}
  $full=[IO.Path]::GetFullPath($candidate)
  $drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($full))
  if($drive.DriveType -ne [IO.DriveType]::Fixed){throw 'Nonfixed Windows drive refused'}
  $walk=if($mustExist){$full}else{Split-Path -Parent $full}
  while($walk -and (Test-Path -LiteralPath $walk)) {
    $item=Get-Item -LiteralPath $walk -Force -ErrorAction Stop
    if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
      throw 'Reparse-point path component refused'
    }
    $parent=Split-Path -Parent $walk
    if(-not $parent -or $parent -eq $walk){break}
    $walk=$parent
  }
  return $full
}
$sourceFull=Assert-FixedPath $ExePath $true
$outputFull=Assert-FixedPath $OutputDirectory $false
if((Split-Path -Leaf $sourceFull) -cne 'medorigin-desktop-d1-preview.exe'){
  throw 'Only synthetic D1 preview executable may be staged'
}
$source=Get-Item -LiteralPath $sourceFull -ErrorAction Stop
if($source.PSIsContainer){throw 'Source must be a file'}
if((Test-Path -LiteralPath $outputFull)){throw 'Stage output directory must be new'}
$parent=Split-Path -Parent $outputFull
if(-not (Test-Path -LiteralPath $parent -PathType Container)){throw 'Stage parent missing'}
$sourceSha=(Get-FileHash -LiteralPath $sourceFull -Algorithm SHA256 -ErrorAction Stop).Hash
if(-not [string]::Equals($sourceSha,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
  throw 'Source SHA-256 does not match caller-pinned identity'
}
New-Item -ItemType Directory -Path $outputFull -ErrorAction Stop | Out-Null
try {
  $copied=Join-Path $outputFull 'medorigin-desktop-d1-preview.exe'
  Copy-Item -LiteralPath $sourceFull -Destination $copied -ErrorAction Stop
  $copySha=(Get-FileHash -LiteralPath $copied -Algorithm SHA256 -ErrorAction Stop).Hash
  if(-not [string]::Equals($copySha,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Staged executable SHA-256 mismatch'
  }
  if((@(Get-ChildItem -LiteralPath $outputFull -Force).Count) -ne 1){
    throw 'Unexpected staged content'
  }
} catch {
  Remove-Item -LiteralPath $outputFull -Recurse -Force -ErrorAction SilentlyContinue
  throw
}
Write-Output ('D1_STAGED_SHA256='+$copySha)
Write-Output ('D1_STAGED_EXECUTABLE='+$copied)
Write-Output 'D1_STAGE_SOURCE_ONLY_PASS (no executable launched; not network/release qualified)'
