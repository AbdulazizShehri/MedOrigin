# Noninvasive source-only negative tests. Never launches the MZ fixture.
$ErrorActionPreference='Stop'
$runner=Join-Path $PSScriptRoot 'windows-native-host-qualification.ps1'
$root=Join-Path $env:TEMP ('medorigin-native-d2-selftest-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root -ErrorAction Stop | Out-Null
try {
  $exe=Join-Path $root 'medorigin-desktop-d2-native-egui.exe'
  [IO.File]::WriteAllBytes($exe,[byte[]](0x4d,0x5a,0x00,0x01))
  $sha=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  $other=Join-Path $root 'not-approved.exe'
  [IO.File]::WriteAllBytes($other,[byte[]](0x4d,0x5a))
  $otherSha=(Get-FileHash -LiteralPath $other -Algorithm SHA256).Hash
  $wrongSha=if($sha -eq ('0'*64)){'1'*64}else{'0'*64}
  $occupied=Join-Path $root 'occupied-audit'
  New-Item -ItemType Directory -Path $occupied -ErrorAction Stop | Out-Null
  $marker=Join-Path $occupied 'do-not-modify.txt'
  [IO.File]::WriteAllText($marker,'protect-existing-user-data')
  $scenarios=@(
    @{name='bad-hash'; source=$exe; digest=$wrongSha; output=(Join-Path $root 'bad-hash-out')},
    @{name='wrong-name'; source=$other; digest=$otherSha; output=(Join-Path $root 'wrong-name-out')},
    @{name='relative-audit-path'; source=$exe; digest=$sha; output=('d2-forbidden-'+[guid]::NewGuid().ToString('N'))},
    @{name='unc-source'; source='\\server-do-not-connect\share\medorigin-desktop-d2-native-egui.exe'; digest=$sha; output=(Join-Path $root 'unc-out')},
    @{name='existing-audit'; source=$exe; digest=$sha; output=$occupied; existing=$true}
  )
  foreach($item in $scenarios){
    $out=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -ExePath $item.source -ExpectedSha256 $item.digest -AuditDirectory $item.output 2>&1|Out-String
    $code=$LASTEXITCODE
    $outputUnexpected=if($item.existing){
      (-not (Test-Path -LiteralPath $marker)) -or
      ([IO.File]::ReadAllText($marker) -ne 'protect-existing-user-data') -or
      (@(Get-ChildItem -LiteralPath $occupied -Force).Count -ne 1)
    } else {
      Test-Path -LiteralPath $item.output
    }
    if($code -ne 1 -or $out -notmatch 'D2_HOST_QUALIFICATION_ERROR=' -or $outputUnexpected){
      throw ('Negative case did not refuse before launch '+$item.name)
    }
    Write-Output ('D2_HOST_NEGATIVE_PASS='+$item.name)
  }
}
finally {
  Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Output 'D2_HOST_NEGATIVE_5_OF_5_PASS (fake bytes never launched; existing audit preserved)'
