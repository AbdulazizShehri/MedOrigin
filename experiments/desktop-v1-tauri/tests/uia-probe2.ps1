param([Parameter(Mandatory=$true)][string]$ExePath)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
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
  Start-Sleep -Seconds 6
  $all = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  Write-Output ('total elements: ' + $all.Count)
  foreach ($el in $all) {
    $name = $el.Current.Name
    $ct = $el.Current.ControlType.ProgrammaticName
    $patterns = @()
    foreach ($p in $el.GetSupportedPatterns()) { $patterns += $p.ProgrammaticName }
    Write-Output ('[' + $ct + '] name="' + $name + '" patterns=' + ($patterns -join ','))
  }
} finally {
  if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
