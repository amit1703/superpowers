Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI2 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@

# Open fresh Chrome window pointed at the dashboard
Start-Process "chrome" "--new-window http://localhost:5173 --window-size=1600,900"
Start-Sleep -Milliseconds 4000

# Find it by title
$target = $null
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne '' } | ForEach-Object {
    if ($_.MainWindowTitle -match 'Swing|SWING|Terminal|TERMINAL') {
        $target = $_
    }
}
if ($null -ne $target) {
    [WinAPI2]::ShowWindow($target.MainWindowHandle, 9) | Out-Null
    [WinAPI2]::SetForegroundWindow($target.MainWindowHandle) | Out-Null
    Write-Host "Focused window: $($target.MainWindowTitle)"
    Start-Sleep -Milliseconds 2000
} else {
    Write-Host "Window not found by title, using top window"
}

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp    = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g      = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_dashboard2.png')
$g.Dispose()
$bmp.Dispose()
Write-Host "Screenshot saved"
