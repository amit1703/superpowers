Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WinA {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int w, int h, bool repaint);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, ref RECT r);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public const int SW_RESTORE = 9;
}
'@

# Kill existing
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match 'SWING|TERMINAL'
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 1500

# Open at a fixed size that fits on a typical 1920x1080 screen
Start-Process "chrome" "--new-window --app=http://localhost:5173/?ticker=AAPL --window-size=1800,880 --window-position=0,0"
Write-Host "Opened Chrome: 1800x880"
Start-Sleep -Milliseconds 11000

$win = $null
for ($i = 0; $i -lt 20; $i++) {
    Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -match 'SWING|TERMINAL'
    } | ForEach-Object { $win = $_ }
    if ($null -ne $win) { break }
    Start-Sleep -Milliseconds 500
}
if ($null -eq $win) { Write-Host "ERROR: no window"; exit 1 }
Write-Host "Found: '$($win.MainWindowTitle)' [PID $($win.Id)]"

$hwnd = $win.MainWindowHandle
[WinA]::ShowWindow($hwnd, [WinA]::SW_RESTORE) | Out-Null
Start-Sleep -Milliseconds 300
[WinA]::MoveWindow($hwnd, 0, 0, 1800, 880, $true) | Out-Null
Start-Sleep -Milliseconds 600
[WinA]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 800

$rect = New-Object WinA+RECT
[WinA]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
Write-Host "Capturing ${w}x${h} at ($($rect.Left),$($rect.Top))"

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_compact.png')
$g.Dispose(); $bmp.Dispose()
Write-Host "Done: screenshot_compact.png"
