# Browser-free D2 native Windows smoke. No release or network-isolation certification.
# Reuses the D1 process-tree socket inspector, which is agnostic to the UI toolkit.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
  [Parameter(Mandatory=$true)][string]$AuditDirectory
)
$ErrorActionPreference='Stop'
$proc=$null
$exitCode=1
try {
  foreach($candidate in @($ExePath,$AuditDirectory)){
    if($candidate -notmatch '^[A-Za-z]:\\'){throw 'Only absolute drive-rooted local paths are accepted'}
    $full=[IO.Path]::GetFullPath($candidate)
    if(([IO.DriveInfo]::new([IO.Path]::GetPathRoot($full))).DriveType -ne [IO.DriveType]::Fixed){
      throw 'Only fixed drives are permitted'
    }
  }
  if((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe'){
    throw 'Only the exact D2 synthetic native executable is accepted'
  }
  if(Test-Path -LiteralPath $AuditDirectory){throw 'Audit directory must not exist'}
  $source=Get-Item -LiteralPath $ExePath -ErrorAction Stop
  if($source.PSIsContainer){throw 'Expected an executable file'}
  foreach($itemPath in @($source.FullName,$AuditDirectory)){
    $walk=if($itemPath -eq $AuditDirectory){Split-Path -Parent ([IO.Path]::GetFullPath($itemPath))}else{$itemPath}
    while($walk -and (Test-Path -LiteralPath $walk)){
      $node=Get-Item -LiteralPath $walk -Force -ErrorAction Stop
      if(($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse-point component rejected'}
      $parent=Split-Path -Parent $walk
      if(-not $parent -or $parent -eq $walk){break}
      $walk=$parent
    }
  }
  $digest=(Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
  if(-not [string]::Equals($digest,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Unapproved SHA-256'
  }
  $probe=Join-Path $PSScriptRoot '..\..\desktop-d1-tauri\tests\windows-egress-snapshot.ps1'
  if(-not (Test-Path -LiteralPath $probe -PathType Leaf)){throw 'Source-controlled network inspector not found'}
  $parentDir=Split-Path -Parent ([IO.Path]::GetFullPath($AuditDirectory))
  if(-not (Test-Path -LiteralPath $parentDir -PathType Container)){throw 'Missing audit parent'}
  New-Item -ItemType Directory -Path $AuditDirectory -ErrorAction Stop | Out-Null
  # Copy the caller-approved bytes into a fresh private test directory. Do not
  # execute the mutable original path after the hash decision.
  $stage=Join-Path $AuditDirectory 'approved-binary'
  New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
  $stagedExe=Join-Path $stage 'medorigin-desktop-d2-native-egui.exe'
  Copy-Item -LiteralPath $source.FullName -Destination $stagedExe -ErrorAction Stop
  $stagedSha=(Get-FileHash -LiteralPath $stagedExe -Algorithm SHA256 -ErrorAction Stop).Hash
  if(-not [string]::Equals($stagedSha,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Staged native binary differs from approved SHA-256'
  }
  if(@(Get-ChildItem -LiteralPath $stage -Force).Count -ne 1){throw 'Unexpected staged binary content'}
  $uia=Join-Path $PSScriptRoot 'windows-native-uia-smoke.ps1'
  if(-not (Test-Path -LiteralPath $uia -PathType Leaf)){throw 'Source-controlled UI Automation test absent'}
  $uiaLog=Join-Path $AuditDirectory 'synthetic-native-uia.txt'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $uia -ExePath $stagedExe *> $uiaLog
  $uiaExit=$LASTEXITCODE
  $uiaMarkers=@(Get-Content -LiteralPath $uiaLog -ErrorAction Stop |
    Where-Object {$_ -eq 'D2_NATIVE_UIA_4_OF_4_PASS (native window, fictional SHA only; no network proof)'})
  if($uiaExit -ne 0 -or $uiaMarkers.Count -ne 1){throw 'Native D2 synthetic UIA 4/4 failed'}
  # Revalidate staged bytes after UIA and before the network-observation launch.
  $afterUiaSha=(Get-FileHash -LiteralPath $stagedExe -Algorithm SHA256).Hash
  if(-not [string]::Equals($afterUiaSha,$ExpectedSha256,[StringComparison]::OrdinalIgnoreCase)){
    throw 'Native staged executable changed during UIA qualification'
  }
  $proc=Start-Process -FilePath $stagedExe -PassThru -ErrorAction Stop
  Start-Sleep -Seconds 3
  if($proc.HasExited){throw 'Native preview exited before smoke'}
  $hostProc=Get-Process -Id $proc.Id -ErrorAction Stop
  $windowPresent=($hostProc.MainWindowHandle -ne 0 -and
    $hostProc.MainWindowTitle -like 'MedOrigin Native Rust*')
  if(-not $windowPresent){throw 'Native top-level window missing after UIA'}
  $maxTcp=0;$maxTcpAny=0;$maxUdp=0;$maxTree=0;$observed=0
  $probeExit=0
  for($sample=1;$sample -le 3;$sample++){
    Start-Sleep -Seconds 5
    if($proc.HasExited){throw 'Native preview exited before final sample'}
    $file=Join-Path $AuditDirectory ('network-sample{0:00}.txt' -f $sample)
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $probe -RootPid $proc.Id *> $file
    $code=$LASTEXITCODE
    if($code -notin @(0,2)){throw 'Process network enumerator failed'}
    $probeExit=[math]::Max($probeExit,$code)
    $lines=Get-Content -LiteralPath $file -ErrorAction Stop
    $counts=@{}
    foreach($label in @('D1_PROCESS_TREE_COUNT','EXTERNAL_ESTABLISHED_TCP','EXTERNAL_TCP_ALL_STATES','UDP_ENDPOINT_COUNT')){
      $matches=@($lines | Where-Object {$_ -match ('^'+$label+'=\d+$')})
      if($matches.Count -ne 1){throw ('Missing/ambiguous count '+$label)}
      $counts[$label]=[int]($matches[0].Split('=')[1])
    }
    $maxTree=[math]::Max($maxTree,$counts['D1_PROCESS_TREE_COUNT'])
    $maxTcp=[math]::Max($maxTcp,$counts['EXTERNAL_ESTABLISHED_TCP'])
    $maxTcpAny=[math]::Max($maxTcpAny,$counts['EXTERNAL_TCP_ALL_STATES'])
    $maxUdp=[math]::Max($maxUdp,$counts['UDP_ENDPOINT_COUNT'])
    $observed++
  }
  $receipt=[ordered]@{
    schema='medorigin-native-d2-host-smoke-v2'
    source_sha256=$digest
    staged_executable_sha256=$stagedSha
    executing_verified_copy=$true
    interactive_uia_4_of_4_pass=$true
    synthetic_only=$true
    native_window_present=[bool]$windowPresent
    sample_count=$observed
    process_tree_max=$maxTree
    established_external_tcp_max=$maxTcp
    any_external_tcp_max=$maxTcpAny
    udp_endpoints_max=$maxUdp
    process_snapshot_exit=$probeExit
    network_isolation_qualified=$false
    clinical_qualified=$false
    release_qualified=$false
    note='Three socket snapshots cannot prove zero outbound packets; independent OS isolation and packet capture absent.'
  }
  $receipt|ConvertTo-Json -Depth 3|Set-Content -LiteralPath (Join-Path $AuditDirectory 'qualification.json') -Encoding UTF8
  Write-Output 'D2_NATIVE_STAGED_SHA256_APPROVED=True'
  Write-Output 'D2_NATIVE_UIA_4_OF_4_PASS=True'
  Write-Output ('D2_NATIVE_WINDOW_PRESENT='+$windowPresent)
  Write-Output ('D2_SAMPLES='+$observed)
  Write-Output ('D2_EXTERNAL_TCP_MAX='+$maxTcp)
  Write-Output ('D2_ANY_EXTERNAL_TCP_MAX='+$maxTcpAny)
  Write-Output ('D2_UDP_MAX='+$maxUdp)
  Write-Output 'D2_NETWORK_ISOLATION_UNQUALIFIED'
  $exitCode=2
} catch {
  Write-Output ('D2_HOST_QUALIFICATION_ERROR='+$_.Exception.Message)
  $exitCode=1
} finally {
  if($proc -and -not $proc.HasExited){
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
}
exit $exitCode
