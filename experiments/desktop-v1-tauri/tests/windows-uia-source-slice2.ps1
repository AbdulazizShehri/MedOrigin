param([Parameter(Mandatory=$true)][string]$ExePath,
      [string]$ScreenshotDir = 'tests\screenshots\native')
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath $ExePath -PathType Leaf)){throw 'Missing locally built v1 executable'}
New-Item -ItemType Directory -Force $ScreenshotDir | Out-Null
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class MoV1Win32 {
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out MoV1Rect lpRect);
    [DllImport("user32.dll")]
    public static extern uint GetDpiForWindow(IntPtr hwnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct MoV1Rect { public int Left, Top, Right, Bottom; }
}
'@
$SWP_NOZORDER = 0x0004
$SWP_NOACTIVATE = 0x0010
$title = 'MedOrigin — Synthetic Developer Preview (v1)'
$golden = '1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f'
$goldenLen = '425'
$process = Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru

function Find-MainWindow {
  param([int]$TimeoutMs = 60000)
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($w in $windows) {
      if ($w.Current.ProcessId -eq $process.Id -and $w.Current.Name -eq $title) { return $w }
    }
  }
  throw 'Native Tauri window was not accessible by UIA'
}

function Click-ElementByName {
  param([System.Windows.Automation.AutomationElement]$Window, [string]$NamePrefix, [string]$Type = 'Button', [int]$TimeoutMs = 20000)
  $typeMap = @{ 'Button' = [System.Windows.Automation.ControlType]::Button; 'Hyperlink' = [System.Windows.Automation.ControlType]::Hyperlink; 'TextBox' = [System.Windows.Automation.ControlType]::Edit }
  $condition = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, $typeMap[$Type])
  $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
  while ((Get-Date) -lt $deadline) {
    $found = $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
    foreach ($el in $found) {
      if ($el.Current.Name.StartsWith($NamePrefix, [System.StringComparison]::Ordinal)) {
        if ($Type -eq 'TextBox') { return $el }
        $errors = @()
        try {
          $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
          return $el
        } catch { $errors += ('Invoke: ' + $_.Exception.Message) }
        try {
          $el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle()
          return $el
        } catch { $errors += ('Toggle: ' + $_.Exception.Message) }
        try {
          $el.SetFocus()
          Add-Type -AssemblyName System.Windows.Forms
          [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
          return $el
        } catch { $errors += ('SetFocus+Enter: ' + $_.Exception.Message) }
        throw ('No usable activation pattern for: ' + $NamePrefix + ' (' + ($errors -join '; ') + ')')
      }
    }
    Start-Sleep -Milliseconds 250
  }
  throw ('Missing accessible ' + $Type + ': ' + $NamePrefix)
}

function Set-TextBoxValue {
  param([System.Windows.Automation.AutomationElement]$Window, [string]$NamePrefix, [string]$Value)
  $box = Click-ElementByName -Window $Window -NamePrefix $NamePrefix -Type 'TextBox'
  $box.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Value)
  return $box
}

function Get-VisibleText {
  param([System.Windows.Automation.AutomationElement]$Window)
  $cond = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
  $names = @()
  foreach ($item in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) { $names += $item.Current.Name }
  return ,$names
}

function Wait-Text {
  param([System.Windows.Automation.AutomationElement]$Window, [scriptblock]$Predicate, [int]$TimeoutMs = 20000)
  $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
  while ((Get-Date) -lt $deadline) {
    $names = Get-VisibleText -Window $Window
    $joined = [string]::Join("`n", $names)
    if (& $Predicate $joined) { return $true }
    Start-Sleep -Milliseconds 200
  }
  return $false
}

function Measure-CaptureDiversity {
  param([System.Drawing.Bitmap]$Bitmap)
  $distinct = [System.Collections.Generic.HashSet[int]]::new()
  $w = $Bitmap.Width; $h = $Bitmap.Height
  $step = [Math]::Max(1, [int]($w / 160))
  for ($y = 0; $y -lt $h; $y += $step) {
    for ($x = 0; $x -lt $w; $x += $step) {
      $px = $Bitmap.GetPixel($x, $y)
      [void]$distinct.Add($px.ToArgb())
    }
  }
  return $distinct.Count
}

function Capture-Window {
  param([System.Windows.Automation.AutomationElement]$Window, [string]$Label)
  $hwnd = [IntPtr]($Window.Current.NativeWindowHandle)
  [void][MoV1Win32]::SetForegroundWindow($hwnd)
  Start-Sleep -Milliseconds 700
  $rect = New-Object MoV1Win32+MoV1Rect
  if (-not [MoV1Win32]::GetWindowRect($hwnd, [ref]$rect)) { throw 'GetWindowRect failed' }
  $w = $rect.Right - $rect.Left; $h = $rect.Bottom - $rect.Top
  if ($w -le 0 -or $h -le 0) { throw 'Empty window rect' }
  $bmp = [System.Drawing.Bitmap]::new($w, $h)
  $gfx = [System.Drawing.Graphics]::FromImage($bmp)
  $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [System.Drawing.Size]::new($w, $h))
  $gfx.Dispose()
  $distinct = Measure-CaptureDiversity -Bitmap $bmp
  $path = Join-Path $ScreenshotDir $Label
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  Write-Output ('CAPTURE ' + $path + ' distinct_colors=' + $distinct + ' size=' + $w + 'x' + $h)
  if ($distinct -lt 16) { throw ('Blank or near-blank capture rejected: ' + $Label) }
}

try {
  $window = Find-MainWindow
  Write-Output ('UIA window found: ProcessId=' + $process.Id + ' Title=' + $window.Current.Name)

  if (-not (Wait-Text -Window $window -Predicate { param($t) $t -match 'Home' } -TimeoutMs 30000)) { throw 'Home heading not exposed via UIA' }
  if (-not (Wait-Text -Window $window -Predicate { param($t) $t -match [regex]::Escape('SYNTHETIC — NOT EGRESS-QUALIFIED') })) { throw 'Honesty banner not exposed via UIA' }
  Write-Output 'PASS honesty_banner_visible'

  [void](Click-ElementByName -Window $window -NamePrefix 'FHIR fixture inspector' -Type 'Hyperlink')
  if (-not (Wait-Text -Window $window -Predicate { param($t) $t -match 'FHIR fixture inspector' -or $t -match 'Synthetic fixtures' })) { throw 'Fixture inspector did not open' }
  [void](Click-ElementByName -Window $window -NamePrefix 'Fixture fixture-patient-alpha' -Type 'Button')
  [void](Click-ElementByName -Window $window -NamePrefix 'Verify fixture with native Rust' -Type 'Button')
  $verified = Wait-Text -Window $window -Predicate { param($t) $t.Contains($golden) -and $t -match '(?i)byte-identical' -and $t.Contains('medorigin-fixture-verify-v1') } -TimeoutMs 30000
  if (-not $verified) { throw 'Native verification result text not observed via UIA' }
  Write-Output 'PASS native_fixture_verified_golden_sha256'

  # Slice 2: real WebView2 + Rust source command; not browser mock evidence.
  [void](Click-ElementByName -Window $window -NamePrefix 'Inspect verified fictional JSON source' -Type 'Button')
  $sourceShown = Wait-Text -Window $window -Predicate {
    param($t)
    $t.Contains('FICTIONAL SOURCE') -and $t.Contains('EXAMPLEPERSON') -and $t.Contains('resourceType')
  } -TimeoutMs 30000
  if (-not $sourceShown) { throw 'Native fictional JSON source failed to appear in UIA after verification' }
  Write-Output 'PASS native_source_read_verified_fictional_json'

  # The embedded UI deliberately excludes developer-only arbitrary-id probes.
  # Rust unit tests exercise unknown/traversal IDs; this native test covers
  # the real allowlisted source command, actual WebView2 rendering and UIA.
  Write-Output 'NOTE developer-id probe absent in embedded UI; Rust negative tests are separate'

  [void](Click-ElementByName -Window $window -NamePrefix 'Light' -Type 'Button')
  Start-Sleep -Milliseconds 400
  Capture-Window -Window $window -Label 'mo-v1-native-light-1440x900.png'
  [void](Click-ElementByName -Window $window -NamePrefix 'Dark' -Type 'Button')
  Start-Sleep -Milliseconds 400
  Capture-Window -Window $window -Label 'mo-v1-native-dark-1440x900.png'

  $sizes = @(@{w=1280;h=800}, @{w=1440;h=900})
  $hwnd = [IntPtr]($window.Current.NativeWindowHandle)
  $dpi = [double][MoV1Win32]::GetDpiForWindow($hwnd)
  $scale = $dpi / 96.0
  Write-Output ('WINDOW_DPI=' + $dpi + ' scale=' + $scale)
  foreach ($s in $sizes) {
    $physW = [int][Math]::Round($s.w * $scale); $physH = [int][Math]::Round($s.h * $scale)
    Write-Output ('Setting logical {0}x{1} -> physical {2}x{3}' -f $s.w, $s.h, $physW, $physH)
    [void][MoV1Win32]::SetWindowPos($hwnd, [IntPtr]::Zero, 20, 20, $physW, $physH, ($SWP_NOZORDER -bor $SWP_NOACTIVATE))
    Start-Sleep -Milliseconds 600
    Capture-Window -Window $window -Label ('mo-v1-native-dark-{0}x{1}.png' -f $s.w, $s.h)
    [void](Click-ElementByName -Window $window -NamePrefix 'Light' -Type 'Button')
    Start-Sleep -Milliseconds 400
    Capture-Window -Window $window -Label ('mo-v1-native-light-{0}x{1}.png' -f $s.w, $s.h)
    [void](Click-ElementByName -Window $window -NamePrefix 'Dark' -Type 'Button')
    Start-Sleep -Milliseconds 400
  }
  Write-Output 'NOTE 1920x1080 NOT RUN on this display (primary logical bounds 1536x960 at 125% DPI); browser 1920x1080 captures recorded separately.'
  Write-Output 'V1_SLICE2_UIA_SOURCE_PASS (native fictional JSON source; NOT FHIR validation; NOT egress qualification)'
  exit 0
}
catch {
  Write-Output ('V1_UIA_SMOKE_FAIL: ' + $_.Exception.Message)
  exit 1
}
finally {
  if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
