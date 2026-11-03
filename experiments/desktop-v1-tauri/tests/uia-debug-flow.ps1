param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
$title = 'MedOrigin — Synthetic Developer Preview (v1)'
$process = Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru

function Wait-Window {
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  for ($i = 0; $i -lt 80; $i++) {
    Start-Sleep -Milliseconds 250
    foreach ($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)) {
      if ($w.Current.ProcessId -eq $process.Id -and $w.Current.Name -eq $title) { return $w }
    }
  }
  throw 'window not found'
}
function Activate-ByName {
  param($Window, [string]$NamePrefix, [string]$Type)
  $typeMap = @{ 'Button' = [System.Windows.Automation.ControlType]::Button; 'Hyperlink' = [System.Windows.Automation.ControlType]::Hyperlink }
  $cond = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, $typeMap[$Type])
  for ($i = 0; $i -lt 40; $i++) {
    foreach ($el in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) {
      if ($el.Current.Name.StartsWith($NamePrefix, [System.StringComparison]::Ordinal)) {
        try { $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Write-Output ('INVOKE ok: ' + $NamePrefix); return } catch { }
        try { $el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern).Toggle(); Write-Output ('TOGGLE ok: ' + $NamePrefix); return } catch { }
        try { $el.SetFocus(); [System.Windows.Forms.SendKeys]::SendWait('{ENTER}'); Write-Output ('ENTER ok: ' + $NamePrefix); return } catch { }
        Write-Output ('FAIL activate: ' + $NamePrefix)
        return
      }
    }
    Start-Sleep -Milliseconds 500
  }
  Write-Output ('NOTFOUND: ' + $NamePrefix)
}
function Dump-Texts {
  param($Window, [string]$Label)
  $cond = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
  $names = @()
  foreach ($el in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) { $names += $el.Current.Name }
  Write-Output ('=== texts [' + $Label + '] count=' + $names.Count)
  $names | Select-Object -Skip 40 | ForEach-Object { Write-Output ('    ' + $_) }
}

try {
  $window = Wait-Window
  Write-Output 'window found'
  Start-Sleep -Seconds 3
  Activate-ByName $window 'FHIR fixture inspector' 'Hyperlink'
  Start-Sleep -Seconds 2
  Dump-Texts $window 'inspector-initial'
  Activate-ByName $window 'Fixture fixture-patient-alpha' 'Button'
  Start-Sleep -Milliseconds 800
  Activate-ByName $window 'Verify fixture with native Rust' 'Button'
  Start-Sleep -Seconds 2
  Dump-Texts $window 'after-verify'
} finally {
  if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
