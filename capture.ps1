Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@

# Find Chrome window with our dashboard
$target = $null
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne '' } | ForEach-Object {
    if ($_.MainWindowTitle -match 'Swing|localhost|5173') {
        $target = $_
    }
}
if ($null -eq $target) {
    $target = Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object -First 1
}
if ($null -ne $target) {
    [WinAPI]::ShowWindow($target.MainWindowHandle, 9) | Out-Null
    [WinAPI]::SetForegroundWindow($target.MainWindowHandle) | Out-Null
    Write-Host "Focused: $($target.MainWindowTitle)"
    Start-Sleep -Milliseconds 1500
}

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp    = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g      = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_chrome.png')
$g.Dispose()
$bmp.Dispose()
Write-Host "Saved screenshot_chrome.png"
