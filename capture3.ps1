Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI3 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP   = 0x04;
}
'@

# Kill any existing Chrome on port 5173 window, open a clean one
Start-Process "chrome" "--new-window --app=http://localhost:5173 --window-size=1600,900 --window-position=0,0"
Start-Sleep -Milliseconds 4500

# Find and focus it
$target = $null
for ($i = 0; $i -lt 10; $i++) {
    Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne '' } | ForEach-Object {
        if ($_.MainWindowTitle -match 'SWING|Swing|TERMINAL|Terminal|localhost') {
            $target = $_
        }
    }
    if ($null -ne $target) { break }
    Start-Sleep -Milliseconds 500
}

if ($null -ne $target) {
    [WinAPI3]::ShowWindow($target.MainWindowHandle, 3)
    Start-Sleep -Milliseconds 300
    [WinAPI3]::SetForegroundWindow($target.MainWindowHandle)
    Write-Host "Window: $($target.MainWindowTitle)"
    Start-Sleep -Milliseconds 2000
} else {
    Write-Host "Window not found, screenshotting top window"
}

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp    = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g      = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_final.png')
$g.Dispose()
$bmp.Dispose()
Write-Host "Saved screenshot_final.png"
