param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$title = 'MedOrigin — Synthetic Developer Preview (v1)'
$process = Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru
try {
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $window = $null
  for ($i = 0; $i -lt 60 -and -not $window; $i++) {
    Start-Sleep -Milliseconds 250
    foreach ($w in $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)) {
      if ($w.Current.ProcessId -eq $process.Id) { $window = $w; break }
    }
  }
  if (-not $window) { throw 'window not found' }
  Write-Output ('window: ' + $window.Current.Name)
  Start-Sleep -Seconds 3
  $cond = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)
  $items = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
  Write-Output ('text elements: ' + $items.Count)
  foreach ($it in ($items | Select-Object -First 25)) { Write-Output ('  [' + $it.Current.ControlType.ProgrammaticName + '] ' + $it.Current.Name) }
  $buttons = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button))
  Write-Output ('button elements: ' + $buttons.Count)
  foreach ($b in ($buttons | Select-Object -First 25)) { Write-Output ('  [btn] ' + $b.Current.Name) }
  $links = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Hyperlink))
  Write-Output ('hyperlink elements: ' + $links.Count)
  foreach ($l in ($links | Select-Object -First 15)) { Write-Output ('  [link] ' + $l.Current.Name) }
} finally {
  if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
