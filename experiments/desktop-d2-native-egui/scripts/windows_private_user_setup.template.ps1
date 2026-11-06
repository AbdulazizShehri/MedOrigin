# MedOrigin D2 private fictional-only user install. Generated/pinned at build time.
# Not signed, authenticated, patient-ready, or a production installer.
[CmdletBinding()]
param([ValidateSet('Install','Verify','Uninstall')][string]$Action='Install')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$expectedCommit='__EXPECTED_COMMIT__'
$expectedArchiveSha256='__EXPECTED_ARCHIVE_SHA256__'
$archiveName='MedOrigin-Reviewed-Archive.zip'
$expected=@{
__EXPECTED_HASHES__
}
$binary='medorigin-desktop-d2-native-egui.exe'
$scriptName='Install-MedOrigin-Private.ps1'
$shortcutName='MedOrigin Synthetic Preview.lnk'
$uninstallName='Uninstall MedOrigin Synthetic Preview.lnk'

function Require-ExistingUnredirected([string]$path, [bool]$directory) {
    if (-not [IO.Path]::IsPathRooted($path) -or $path -notmatch '^[A-Za-z]:\\') {
        throw 'refuse_unc_relative_or_unreviewed_drive_path'
    }
    if (-not (Test-Path -LiteralPath $path)) { throw 'required_path_absent' }
    $current=[IO.Path]::GetFullPath($path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item=Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw 'reparse_ancestor_refused'
            }
        }
        $parent=Split-Path -Parent $current
        if (-not $parent -or $parent -eq $current) { break }
        $current=$parent
    }
    if ($directory -and -not (Test-Path -LiteralPath $path -PathType Container)) {
        throw 'expected_directory'
    }
    if (-not $directory -and -not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'expected_regular_file'
    }
}

function Get-PinnedSha256([string]$path) {
    Require-ExistingUnredirected $path $false
    $stream=$null
    $sha=$null
    try {
        $stream=[IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $sha=[Security.Cryptography.SHA256]::Create()
        $hash=$sha.ComputeHash($stream)
        return [BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
    } finally {
        if ($stream) { $stream.Dispose() }
        if ($sha) { $sha.Dispose() }
    }
}

function Expand-PinnedArchive([string]$path, [string]$destination) {
    Require-ExistingUnredirected $path $false
    Require-ExistingUnredirected $destination $true
    # Use signed framework ZIP classes without relying on an auto-imported
    # PowerShell Gallery/Archive module or shell subprocess.
    [Reflection.Assembly]::Load(
        'System.IO.Compression.FileSystem, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089'
    ) | Out-Null
    [IO.Compression.ZipFile]::ExtractToDirectory($path, $destination)
}

function Confirm-Payload([string]$folder, [bool]$installed) {
    Require-ExistingUnredirected $folder $true
    $expectedNames=@($expected.Keys)
    if ($installed) { $expectedNames+=@($scriptName) }
    $files=@(Get-ChildItem -LiteralPath $folder -Force)
    if (@($files | Where-Object { $_.PSIsContainer -or ($expectedNames -cnotcontains $_.Name) }).Count -ne 0) {
        throw 'payload_contains_unreviewed_files'
    }
    if ($files.Count -ne $expectedNames.Count) { throw 'payload_incomplete' }
    foreach ($entry in $expected.GetEnumerator()) {
        $file=Join-Path $folder $entry.Key
        Require-ExistingUnredirected $file $false
        $actual=Get-PinnedSha256 $file
        if ($actual -cne $entry.Value) { throw 'payload_sha256_refused' }
    }
    $manifest=Get-Content -LiteralPath (Join-Path $folder 'MANIFEST.json') -Raw | ConvertFrom-Json
    if ($manifest.source_commit -cne $expectedCommit -or
        $manifest.binary_sha256 -cne $expected[$binary] -or
        $manifest.synthetic_only -cne $true -or
        $manifest.clinical_use_authorized -cne $false -or
        $manifest.patient_data_supported -cne $false -or
        $manifest.production_installer -cne $false -or
        $manifest.release_authorized -cne $false -or
        $manifest.signed_or_notarized -cne $false) {
        throw 'synthetic_manifest_scope_refused'
    }
}

function Confirm-Shortcut([string]$path, [string]$target, [string]$arguments) {
    Require-ExistingUnredirected $path $false
    Require-ExistingUnredirected $target $false
    $shell=New-Object -ComObject WScript.Shell
    $link=$shell.CreateShortcut($path)
    # The Windows Shell may expand RUNNER~1 / PROGRA~1 (8.3 names) in the
    # saved shortcut target. Compare only normalized *existing local files*,
    # not untrusted arbitrary textual names, and still pin exact arguments.
    $observed=$link.TargetPath
    Require-ExistingUnredirected $observed $false
    # GetFullPath alone does not expand an 8.3 filesystem alias. Get-Item
    # returns the canonical long path after the ancestor/reparse checks above.
    $observedFile=(Get-Item -LiteralPath $observed -Force).FullName
    $targetFile=(Get-Item -LiteralPath $target -Force).FullName
    if ($observedFile -ine $targetFile) {
        throw 'existing_shortcut_target_refused'
    }
    if ($link.Arguments -cne $arguments) {
        throw 'existing_shortcut_arguments_refused'
    }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'windows_x64_required' }
    if (-not $env:LOCALAPPDATA -or -not $env:APPDATA) { throw 'user_profile_paths_required' }
    Require-ExistingUnredirected $env:LOCALAPPDATA $true
    Require-ExistingUnredirected $env:APPDATA $true
    $appParent=Join-Path $env:LOCALAPPDATA 'MedOrigin-D2-Private-Developer-QA'
    $destination=Join-Path $appParent 'InstalledPreview'
    $programs=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    $shortcut=Join-Path $programs $shortcutName
    $uninstallShortcut=Join-Path $programs $uninstallName
    $exe=Join-Path $destination $binary
    $installedScript=Join-Path $destination $scriptName
    $psExe=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $uninstallArguments='-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$installedScript+'" -Action Uninstall'

    if ($Action -eq 'Install') {
        if (Test-Path -LiteralPath $destination) { throw 'existing_install_not_overwritten' }
        if (-not (Test-Path -LiteralPath $programs -PathType Container)) {
            throw 'start_menu_parent_missing'
        }
        Require-ExistingUnredirected $programs $true
        if ((Test-Path -LiteralPath $shortcut) -or (Test-Path -LiteralPath $uninstallShortcut)) {
            throw 'existing_shortcut_not_overwritten'
        }
        # Only a source-hash-pinned ZIP, our static .cmd bootstrap and the
        # generated source-verified .ps1 can be present in IExpress extraction.
        Require-ExistingUnredirected $PSScriptRoot $true
        $archive=Join-Path $PSScriptRoot $archiveName
        Require-ExistingUnredirected $archive $false
        Require-ExistingUnredirected (Join-Path $PSScriptRoot $scriptName) $false
        $sourceNames=@($archiveName,$scriptName,'Install-MedOrigin-Private.cmd')
        $actualNames=@(Get-ChildItem -LiteralPath $PSScriptRoot -Force)
        if ($actualNames.Count -ne $sourceNames.Count -or
            @($actualNames | Where-Object {
                $_.PSIsContainer -or ($sourceNames -cnotcontains $_.Name)
            }).Count -ne 0) { throw 'iexpress_source_contains_unreviewed_files' }
        if ((Get-PinnedSha256 $archive) -cne $expectedArchiveSha256) { throw 'reviewed_archive_sha256_refused' }
        if (-not (Test-Path -LiteralPath $appParent)) {
            New-Item -ItemType Directory -Path $appParent -ErrorAction Stop | Out-Null
        }
        Require-ExistingUnredirected $appParent $true
        $stage=Join-Path $appParent ('PendingPrivatePreview-'+[Guid]::NewGuid().ToString('N'))
        $expand=Join-Path $appParent ('PendingPrivateExtract-'+[Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
        New-Item -ItemType Directory -Path $expand -ErrorAction Stop | Out-Null
        $committed=$false
        $ownShortcut=$false
        $ownUninstallerShortcut=$false
        $nonce=[Guid]::NewGuid().ToString('N')
        $pendingShortcut=Join-Path $programs ('MedOrigin-Private-pending-'+$nonce+'.lnk')
        $pendingUninstall=Join-Path $programs ('MedOrigin-Private-uninstall-pending-'+$nonce+'.lnk')
        try {
            # Archive SHA checked before extraction; strict five-file canonical
            # source is checked again before copying any payload to staging.
            Expand-PinnedArchive $archive $expand
            $expanded=Join-Path $expand 'MedOrigin-Synthetic-Preview'
            Require-ExistingUnredirected $expanded $true
            if (@(Get-ChildItem -LiteralPath $expand -Force).Count -ne 1) {
                throw 'reviewed_archive_extra_root_refused'
            }
            Confirm-Payload $expanded $false
            foreach ($entry in $expected.GetEnumerator()) {
                Copy-Item -LiteralPath (Join-Path $expanded $entry.Key) -Destination (Join-Path $stage $entry.Key) -ErrorAction Stop
            }
            Copy-Item -LiteralPath (Join-Path $PSScriptRoot $scriptName) -Destination (Join-Path $stage $scriptName) -ErrorAction Stop
            Confirm-Payload $stage $true
            Move-Item -LiteralPath $stage -Destination $destination -ErrorAction Stop
            $committed=$true
            $shell=New-Object -ComObject WScript.Shell
            $link=$shell.CreateShortcut($pendingShortcut)
            $link.TargetPath=$exe
            $link.WorkingDirectory=$destination
            $link.IconLocation=$exe
            $link.Description='MedOrigin synthetic-only desktop engineering preview. NOT for patients.'
            $link.Save()
            Confirm-Shortcut $pendingShortcut $exe ''
            Move-Item -LiteralPath $pendingShortcut -Destination $shortcut -ErrorAction Stop
            $ownShortcut=$true
            $unlink=$shell.CreateShortcut($pendingUninstall)
            $unlink.TargetPath=$psExe
            $unlink.Arguments=$uninstallArguments
            $unlink.WorkingDirectory=$destination
            $unlink.Description='Uninstall private fictional MedOrigin Desktop preview'
            $unlink.Save()
            Confirm-Shortcut $pendingUninstall $psExe $uninstallArguments
            Move-Item -LiteralPath $pendingUninstall -Destination $uninstallShortcut -ErrorAction Stop
            $ownUninstallerShortcut=$true
            Confirm-Shortcut $shortcut $exe ''
            Confirm-Shortcut $uninstallShortcut $psExe $uninstallArguments
        } catch {
            # Roll back only our own successfully moved links, not a
            # competing existing shortcut. Never erase unreviewed modifications.
            if ($ownShortcut -and (Test-Path -LiteralPath $shortcut)) {
                Remove-Item -LiteralPath $shortcut -Force
            }
            if ($ownUninstallerShortcut -and (Test-Path -LiteralPath $uninstallShortcut)) {
                Remove-Item -LiteralPath $uninstallShortcut -Force
            }
            if ($committed -and (Test-Path -LiteralPath $destination)) {
                try {
                    Confirm-Payload $destination $true
                    Remove-Item -LiteralPath $destination -Recurse -Force
                } catch {
                    Write-Warning 'Private preview failed; review the installed folder manually, no unverified contents deleted.'
                }
            }
            throw
        } finally {
            if (Test-Path -LiteralPath $pendingShortcut) {
                Remove-Item -LiteralPath $pendingShortcut -Force
            }
            if (Test-Path -LiteralPath $pendingUninstall) {
                Remove-Item -LiteralPath $pendingUninstall -Force
            }
            if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
            if (Test-Path -LiteralPath $expand) { Remove-Item -LiteralPath $expand -Recurse -Force }
        }
        Write-Output 'MEDORIGIN_PRIVATE_WINDOWS_USER_INSTALL_PASS_SYNTHETIC_NOT_RELEASED'
    } elseif ($Action -eq 'Verify') {
        Confirm-Payload $destination $true
        Confirm-Shortcut $shortcut $exe ''
        Confirm-Shortcut $uninstallShortcut $psExe $uninstallArguments
        Write-Output 'MEDORIGIN_PRIVATE_WINDOWS_USER_INSTALL_VERIFY_PASS_SYNTHETIC'
    } else {
        # Uninstall is runnable only from the exact installed script, never
        # from the IExpress temporary extraction or an arbitrary folder.
        if ($PSScriptRoot -ine $destination) { throw 'uninstall_requires_installed_script' }
        Confirm-Payload $destination $true
        Confirm-Shortcut $shortcut $exe ''
        Confirm-Shortcut $uninstallShortcut $psExe $uninstallArguments
        if (@(Get-Process -Name 'medorigin-desktop-d2-native-egui' -ErrorAction SilentlyContinue).Count -ne 0) {
            throw 'refuse_uninstall_while_native_app_running'
        }
        Remove-Item -LiteralPath $shortcut -Force -ErrorAction Stop
        Remove-Item -LiteralPath $uninstallShortcut -Force -ErrorAction Stop
        Remove-Item -LiteralPath $destination -Recurse -Force -ErrorAction Stop
        if (Test-Path -LiteralPath $destination) { throw 'uninstall_directory_remaining' }
        Write-Output 'MEDORIGIN_PRIVATE_WINDOWS_USER_UNINSTALL_PASS_SYNTHETIC'
    }
} catch {
    Write-Error ('MEDORIGIN_PRIVATE_WINDOWS_USER_SETUP_NO_GO: '+$_.Exception.Message)
    exit 2
}