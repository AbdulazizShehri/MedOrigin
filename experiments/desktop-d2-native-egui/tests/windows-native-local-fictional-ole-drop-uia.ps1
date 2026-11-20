# Owner-private physical Windows OLE file drag/drop on EXACT native nonclinical D2.
# Test-only source and cursor movement; never patient files, release, network.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedExeSHA256,
  [Parameter(Mandatory=$true)][string]$FictionalFixturePath,
  [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedFixtureSHA256
)
$ErrorActionPreference='Stop'
$native=$null
try {
  if ((Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash -ine $ExpectedExeSHA256) {
    throw 'native_exe_sha_refused'
  }
  $sourceFixture=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\fixtures\core\synthetic-multipatient-fhir-bundle.json') -ErrorAction Stop).Path
  $proposedFixture=(Resolve-Path -LiteralPath $FictionalFixturePath -ErrorAction Stop).Path
  if ($proposedFixture -cne $sourceFixture -or
      $ExpectedFixtureSHA256 -ine '92004ddb54302dd70c899dc5ace1a88147e36d81d101f67616b9ee031365cd10') {
    throw 'source_reviewed_fictional_fixture_path_or_digest_required'
  }
  if ((Get-FileHash -LiteralPath $FictionalFixturePath -Algorithm SHA256).Hash -ine $ExpectedFixtureSHA256) {
    throw 'fictional_bundle_sha_refused'
  }
  if ((Split-Path -Leaf $ExePath) -cne 'medorigin-desktop-d2-native-egui.exe') {
    throw 'native_exe_filename_refused'
  }
  $file=Get-Item -LiteralPath $FictionalFixturePath -ErrorAction Stop
  if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or $file.Length -gt 32768 -or $file.Length -le 0) {
    throw 'fixture_file_unreviewed'
  }
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  if ([Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA') {
    throw 'windows_ole_drag_requires_sta'
  }
  Add-Type -ReferencedAssemblies 'System.Windows.Forms','System.Drawing' -TypeDefinition @'
using System;
using System.Collections.Specialized;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
public static class MedOriginPrivateOleDrag {
  [DllImport("user32.dll", SetLastError=true)]
  public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
        int X, int Y, int cx, int cy, uint uFlags);
  [DllImport("user32.dll", SetLastError=true)]
  public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll", SetLastError=true)]
  static extern bool GetCursorPos(out Point p);
  [DllImport("user32.dll", SetLastError=true)]
  static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
  public static string DragOneFile(string filePath, int startX, int startY, int endX, int endY) {
    Point before;
    GetCursorPos(out before);
    string outcome = "NOT_INVOKED";
    var form = new Form();
    form.Text = "MedOrigin fictional drag source only";
    form.StartPosition = FormStartPosition.Manual;
    form.Location = new Point(startX-85,startY-45);
    form.Size = new Size(220,145);
    form.TopMost = true;
    form.ShowInTaskbar = false;
    form.FormBorderStyle = FormBorderStyle.FixedToolWindow;
    form.BackColor = Color.WhiteSmoke;
    var timeout = new System.Windows.Forms.Timer();
    timeout.Interval = 10000;
    timeout.Tick += (sender, args) => { timeout.Stop(); form.Close(); };
    form.MouseDown += (sender, args) => {
      try {
        var names = new StringCollection();
        names.Add(filePath);
        var data = new DataObject();
        data.SetFileDropList(names);
        outcome = "DRAG_EFFECT_" + form.DoDragDrop(data, DragDropEffects.Copy).ToString();
      } catch (Exception ex) {
        outcome = "DRAG_EXCEPTION_" + ex.GetType().Name;
      }
      form.Close();
    };
    form.Shown += (sender, args) => {
      timeout.Start();
      var mover = new Thread(() => {
        try {
          Thread.Sleep(500);
          SetCursorPos(startX,startY);
          Thread.Sleep(200);
          mouse_event(0x0002,0,0,0,UIntPtr.Zero);
          for(int step=1;step<=24;step++){
            int x=startX + (endX-startX)*step/24;
            int y=startY + (endY-startY)*step/24;
            SetCursorPos(x,y);
            Thread.Sleep(24);
          }
          Thread.Sleep(320);
          mouse_event(0x0004,0,0,0,UIntPtr.Zero);
        } finally {
          Thread.Sleep(150);
          SetCursorPos(before.X,before.Y);
        }
      });
      mover.IsBackground = true;
      mover.Start();
    };
    try {
      Application.Run(form);
    } finally {
      timeout.Stop();
      timeout.Dispose();
      form.Dispose();
      SetCursorPos(before.X,before.Y);
    }
    return outcome;
  }
}
'@ -ErrorAction Stop

  $native=Start-Process -FilePath (Resolve-Path -LiteralPath $ExePath).Path -PassThru -ErrorAction Stop
  $window=$null
  $desktop=[System.Windows.Automation.AutomationElement]::RootElement
  for($i=0;$i -lt 60;$i++){
    foreach($item in $desktop.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
      try{
        if($item.Current.ProcessId -eq $native.Id -and $item.Current.Name -like 'MedOrigin Native Rust*'){
          $window=$item;break
        }
      }catch{}
    }
    if($window){break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $window){throw 'visible_native_app_window_not_found'}
  function HasText([string]$text) {
    $nodes=$window.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
    foreach($node in $nodes){
      try{
        if($node.Current.ControlType.ProgrammaticName -eq 'ControlType.Text' -and $node.Current.Name -ceq $text){
          return $true
        }
      }catch{}
    }
    return $false
  }
  $screen=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  if($screen.Width -lt 1100 -or $screen.Height -lt 720){throw 'insufficient_screen_resolution_for_safe_source_and_target'}
  $targetX=[int]($screen.Width*0.68)
  $targetY=[int]($screen.Height*0.52)
  $sourceX=[int]($screen.Width*0.12)
  $sourceY=[int]($screen.Height*0.36)
  $positioned=[MedOriginPrivateOleDrag]::SetWindowPos($native.MainWindowHandle,[IntPtr]::Zero,580,140,880,660,0x0040)
  if(-not $positioned){throw 'cannot_position_reviewed_native_window'}
  Start-Sleep -Milliseconds 400
  $hint='Open a local imaginary FHIR Bundle by dragging one canonical synthetic-only .json file into this window (no patient records).'
  if(-not (HasText $hint)){throw 'native_drop_hint_not_exposed_accessibly'}
  Write-Output 'PHYSICAL_WINDOWS_NATIVE_DROP_HINT_AND_REVIEWED_SOURCE_PASS'
  $dragResult=[MedOriginPrivateOleDrag]::DragOneFile($FictionalFixturePath,$sourceX,$sourceY,$targetX,$targetY)
  Write-Output ('PHYSICAL_OLE_WINDOWS_SYNTHETIC_FILE_DRAG_EFFECT='+$dragResult)
  $admitted=$false
  $expected='Bundle: Opened local synthetic-only JSON (no PHI, session-only)'
  for($k=0;$k -lt 55;$k++){
    if(HasText $expected){$admitted=$true;break}
    Start-Sleep -Milliseconds 200
  }
  if(-not $admitted){throw 'real_windows_ole_drop_was_not_admitted_by_native_app'}
  Write-Output 'REAL_WINDOWS_OLE_DRAG_DROP_LOCAL_FICTIONAL_FHIR_BUNDLE_UIA_PASS_NONCLINICAL'
} catch {
  [Console]::Error.WriteLine('MEDORIGIN_PHYSICAL_WINDOWS_OLE_DRAG_QA_NO_GO: '+$_.Exception.Message)
  exit 2
} finally {
  if($native){
    if(-not $native.HasExited){
      Stop-Process -Id $native.Id -Force -ErrorAction SilentlyContinue
    }
    # Termination is asynchronous: the installer must never be asked to
    # uninstall while this QA-owned native executable is still exiting.
    if(-not $native.WaitForExit(15000)){
      throw 'native_test_process_cleanup_timed_out'
    }
  }
}