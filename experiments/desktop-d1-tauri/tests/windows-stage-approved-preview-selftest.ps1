# Source-only approved executable stage regression: never starts an app.
$ErrorActionPreference='Stop'
$stage=Join-Path $PSScriptRoot 'windows-stage-approved-preview.ps1'
$root=Join-Path $env:TEMP ('medorigin-stage-test-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $source=Join-Path $root 'medorigin-desktop-d1-preview.exe'
  [IO.File]::WriteAllBytes($source,[byte[]](0x4d,0x5a,0x01,0x02))
  $sha=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  $approved=Join-Path $root 'approved'
  $output=@(& $stage -ExePath $source -ExpectedSha256 $sha -OutputDirectory $approved)
  if(-not ($output -contains ('D1_STAGED_SHA256='+$sha))){throw 'Missing pinned hash receipt'}
  $copy=Join-Path $approved 'medorigin-desktop-d1-preview.exe'
  if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne $sha){throw 'Copied bytes mismatch'}
  if(@(Get-ChildItem -LiteralPath $approved -File).Count -ne 1){throw 'Unexpected staged file'}
  Write-Output 'PASS approved-binary-stage'
  $denied=$false
  try { & $stage -ExePath $source -ExpectedSha256 $sha -OutputDirectory $approved | Out-Null }
  catch { $denied=$true }
  if(-not $denied){throw 'Overwriting stage was allowed'}
  Write-Output 'PASS no-overwrite'
  $wrong=if($sha -eq ('0'*64)){'1'*64}else{'0'*64}
  $bad=Join-Path $root 'wrong-digest'
  $denied=$false
  try { & $stage -ExePath $source -ExpectedSha256 $wrong -OutputDirectory $bad | Out-Null }
  catch { $denied=$true }
  if(-not $denied -or (Test-Path -LiteralPath $bad)){throw 'Unapproved binary staged'}
  Write-Output 'PASS wrong-digest'
  $other=Join-Path $root 'untrusted.exe'
  [IO.File]::WriteAllBytes($other,[byte[]](0x4d,0x5a))
  $nameDir=Join-Path $root 'wrong-name'
  $denied=$false
  try { & $stage -ExePath $other -ExpectedSha256 (Get-FileHash $other -Algorithm SHA256).Hash -OutputDirectory $nameDir | Out-Null }
  catch { $denied=$true }
  if(-not $denied -or (Test-Path -LiteralPath $nameDir)){throw 'Wrong name staged'}
  Write-Output 'PASS wrong-name'
}
finally {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output 'D1_STAGE_SOURCE_ONLY_4_OF_4_PASS (no app or Sandbox launched)'
