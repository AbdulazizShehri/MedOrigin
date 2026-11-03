param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class MoCapWin32 {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out MoCapRect r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct MoCapRect { public int Left, Top, Right, Bottom; }
}
'@
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process = Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
try {
  Start-Sleep -Seconds 8
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $hwnd = [IntPtr]::Zero
  foreach ($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)) {
    if ($w.Current.ProcessId -eq $process.Id) { $hwnd = [IntPtr]$w.Current.NativeWindowHandle; break }
  }
  if ($hwnd -eq [IntPtr]::Zero) { throw 'window not found' }
  [void][MoCapWin32]::SetForegroundWindow($hwnd)
  Start-Sleep -Milliseconds 800
  $rect = New-Object MoCapWin32+MoCapRect
  [void][MoCapWin32]::GetWindowRect($hwnd, [ref]$rect)
  $w = $rect.Right - $rect.Left; $h = $rect.Bottom - $rect.Top
  Write-Output ('rect=' + $w + 'x' + $h)
  $bmp = [System.Drawing.Bitmap]::new($w, $h)
  $gfx = [System.Drawing.Graphics]::FromImage($bmp)
  $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
  $out = Join-Path $PWD 'tests\screenshots\native\probe-launch.png'
  New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
  $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
  Write-Output ('saved ' + $out)
} finally {
  if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
