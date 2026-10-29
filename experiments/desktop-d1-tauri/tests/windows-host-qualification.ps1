# Fail-closed, synthetic-only D1 host qualification.
# Captures observations; NEVER certifies zero egress from a socket snapshot alone.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256,
  [Parameter(Mandatory=$true)][string]$AuditDirectory
)
$ErrorActionPreference='Stop'
$code=1
$rootProc=$null
try {
  if ($ExePath -notmatch '^[A-Za-z]:\\' -or $AuditDirectory -notmatch '^[A-Za-z]:\\') {
    throw 'Only absolute drive paths may be inspected'
  }
  if ((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d1-preview.exe') {
    throw 'Refusing nonpreview executable'
  }
  foreach($path in @($ExePath,$AuditDirectory)){
    $drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot([IO.Path]::GetFullPath($path)))
    if($drive.DriveType -ne [IO.DriveType]::Fixed){throw 'Nonfixed drive refused'}
  }
  $exe=Get-Item -LiteralPath $ExePath -ErrorAction Stop
  if (($exe.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Refusing executable reparse point'
  }
  $digest=(Get-FileHash -LiteralPath $exe.FullName -Algorithm SHA256).Hash
  if(-not [string]::Equals($digest,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Executable differs from caller-pinned SHA-256'
  }
  if(Test-Path -LiteralPath $AuditDirectory) {throw 'Audit directory must not already exist'}
  $parent=Split-Path -Parent ([IO.Path]::GetFullPath($AuditDirectory))
  if(-not (Test-Path -LiteralPath $parent -PathType Container)){throw 'Audit parent absent'}
  New-Item -ItemType Directory -Path $AuditDirectory -ErrorAction Stop | Out-Null
  $uia=Join-Path $PSScriptRoot 'windows-uia-smoke.ps1'
  $probe=Join-Path $PSScriptRoot 'windows-egress-snapshot.ps1'
  $uiLog=Join-Path $AuditDirectory 'uia.txt'
  $netLog=Join-Path $AuditDirectory 'network-process-tree.txt'
  $receipt=Join-Path $AuditDirectory 'qualification.json'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $uia -ExePath $exe.FullName *> $uiLog
  $uiCode=$LASTEXITCODE
  $uiPass=($uiCode -eq 0) -and (@(Get-Content -LiteralPath $uiLog | Where-Object {$_ -match '^D1_UIA_4_OF_4_PASS'}).Count -eq 1)
  $netCode=-1
  $tcp=-1
  $udp=-1
  $trees=-1
  if($uiPass) {
    $rootProc=Start-Process -FilePath $exe.FullName -PassThru -ErrorAction Stop
    Start-Sleep -Seconds 7
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $probe -RootPid $rootProc.Id *> $netLog
    $netCode=$LASTEXITCODE
    $lines=Get-Content -LiteralPath $netLog
    foreach($pair in @(
      @{label='EXTERNAL_ESTABLISHED_TCP';name='tcp'},
      @{label='UDP_ENDPOINT_COUNT';name='udp'},
      @{label='D1_PROCESS_TREE_COUNT';name='trees'}
    )) {
      $found=@($lines | Where-Object {$_ -match ('^'+$pair.label+'=\d+$')})
      if($found.Count -ne 1){throw ('Missing or ambiguous network count '+$pair.label)}
      $n=[int]($found[0].Split('=')[1])
      switch($pair.name){'tcp'{$tcp=$n};'udp'{$udp=$n};'trees'{$trees=$n}}
    }
  }
  $receiptData=[ordered]@{
    schema='medorigin-d1-host-qualification-v1'
    source_sha256=$digest
    synthetic_only=$true
    unpublished=$true
    ui_4_of_4_pass=[bool]$uiPass
    ui_exit_code=[int]$uiCode
    network_probe_exit_code=[int]$netCode
    external_established_tcp=[int]$tcp
    udp_endpoints=[int]$udp
    process_tree_count=[int]$trees
    network_isolation_qualified=$false
    clinical_qualified=$false
    release_qualified=$false
    note='Socket snapshot cannot prove zero egress; OS-level app-scoped enforcement and packet trace remain missing.'
  }
  $receiptData|ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $receipt -Encoding UTF8
  Write-Output ('D1_HOST_UIA_PASS='+$uiPass)
  Write-Output ('D1_HOST_EXTERNAL_TCP='+$tcp)
  Write-Output ('D1_HOST_UDP_ENDPOINTS='+$udp)
  Write-Output ('D1_HOST_PROCESS_TREE='+$trees)
  Write-Output ('D1_HOST_RECEIPT='+$receipt)
  if(-not $uiPass) {Write-Output 'D1_HOST_UIA_NO_GO'}
  elseif($netCode -eq 2 -and $tcp -gt 0) {Write-Output 'D1_HOST_EGRESS_NO_GO'}
  else {Write-Output 'D1_HOST_NETWORK_UNQUALIFIED'}
  $code=2
}
catch {
  Write-Output ('D1_HOST_QUALIFICATION_ERROR='+$_.Exception.Message)
  $code=1
}
finally {
  if($rootProc -and -not $rootProc.HasExited){
    Stop-Process -Id $rootProc.Id -Force -ErrorAction SilentlyContinue
  }
}
exit $code
