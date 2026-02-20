Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win7 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int w, int h, bool repaint);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, ref RECT r);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public const int SW_RESTORE = 9;
}
'@

# Kill any existing app-mode window for this URL and open a fresh one
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match 'SWING|TERMINAL'
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 1000

# Open a fresh --app mode window (dedicated frameless window)
Start-Process "chrome" "--new-window --app=http://localhost:5173 --window-size=1620,960 --window-position=0,0"
Start-Sleep -Milliseconds 7000

# Find the app window (app mode title has no "- Google Chrome" suffix)
$win = $null
for ($i = 0; $i -lt 15; $i++) {
    Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -match 'SWING|TERMINAL'
    } | ForEach-Object { $win = $_ }
    if ($null -ne $win) { break }
    Start-Sleep -Milliseconds 500
}

if ($null -eq $win) { Write-Host "ERROR: window not found"; exit 1 }
Write-Host "Found: '$($win.MainWindowTitle)' [PID $($win.Id)]"

$hwnd = $win.MainWindowHandle
[Win7]::ShowWindow($hwnd, [Win7]::SW_RESTORE) | Out-Null
Start-Sleep -Milliseconds 400
[Win7]::MoveWindow($hwnd, 0, 0, 1620, 960, $true) | Out-Null
Start-Sleep -Milliseconds 400
[Win7]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 1500

# The input has autoFocus — it should already be focused.
# Just type the ticker and press Enter.
[System.Windows.Forms.SendKeys]::SendWait("AAPL")
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent: AAPL + Enter"

# Wait for chart data to load and render
Start-Sleep -Milliseconds 7000

[Win7]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 500

# Screenshot — window area only
$rect = New-Object Win7+RECT
[Win7]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
Write-Host "Capturing ${w}x${h} at ($($rect.Left),$($rect.Top))"
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_aapl4.png')
$g.Dispose(); $bmp.Dispose()
Write-Host "Done: screenshot_aapl4.png"
