Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinAPI4 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int hCmd);
    [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int c, int e);
    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP   = 0x04;
}
'@

# Focus the Swing Scanner window
$target = $null
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match 'SWING|Swing|TERMINAL' } | ForEach-Object {
    $target = $_
}
if ($null -ne $target) {
    [WinAPI4]::ShowWindow($target.MainWindowHandle, 9) | Out-Null
    [WinAPI4]::SetForegroundWindow($target.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 600
}

# Click the search input (top-right area)
# In the 1600x900 Chrome app window the input is at roughly x=1090, y=38
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(1090, 38)
Start-Sleep -Milliseconds 200
[WinAPI4]::mouse_event([WinAPI4]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 60
[WinAPI4]::mouse_event([WinAPI4]::MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
Start-Sleep -Milliseconds 400

# Type AAPL and press Enter
[System.Windows.Forms.SendKeys]::SendWait("AAPL")
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")

# Wait for chart data to load
Start-Sleep -Milliseconds 4500

# Screenshot
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp    = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g      = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_aapl.png')
$g.Dispose()
$bmp.Dispose()
Write-Host "Saved screenshot_aapl.png"
