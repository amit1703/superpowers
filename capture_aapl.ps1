Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win5 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int w, int h, bool repaint);
    [DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int c, int e);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP   = 0x04;
    public const int SW_MAXIMIZE = 3;
    public const int SW_RESTORE  = 9;
}
'@

# ── 1. Find the SWING SCANNER Chrome app window ─────────────────────────
$swingProc = $null
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match 'SWING|Swing|TERMINAL'
} | ForEach-Object { $swingProc = $_ }

# If not found, open a fresh one
if ($null -eq $swingProc) {
    Write-Host "Opening fresh Chrome app window..."
    Start-Process "chrome" "--new-window --app=http://localhost:5173 --window-size=1600,900 --window-position=50,50"
    Start-Sleep -Milliseconds 5000
    Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -match 'SWING|Swing|TERMINAL'
    } | ForEach-Object { $swingProc = $_ }
}

if ($null -eq $swingProc) {
    Write-Host "ERROR: Could not find or open Swing Scanner window"; exit 1
}

Write-Host "Found: $($swingProc.MainWindowTitle) [PID $($swingProc.Id)]"

# ── 2. Restore + move to top-left, known size ────────────────────────────
$hwnd = $swingProc.MainWindowHandle
[Win5]::ShowWindow($hwnd, [Win5]::SW_RESTORE) | Out-Null
Start-Sleep -Milliseconds 300
[Win5]::MoveWindow($hwnd, 0, 0, 1600, 950, $true) | Out-Null
Start-Sleep -Milliseconds 300
[Win5]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 800

# ── 3. Verify it really is in foreground ─────────────────────────────────
$fg = [Win5]::GetForegroundWindow()
Write-Host "Foreground handle: $fg  (ours: $hwnd)"

# ── 4. Click the search input ────────────────────────────────────────────
# In --app mode at 1600px wide, the input is at roughly x=1090, y=38
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point(1090, 38)
Start-Sleep -Milliseconds 300
[Win5]::mouse_event([Win5]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 80
[Win5]::mouse_event([Win5]::MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
Start-Sleep -Milliseconds 500

# Confirm foreground still ours
[Win5]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 300

# ── 5. Type AAPL and Enter ────────────────────────────────────────────────
[System.Windows.Forms.SendKeys]::SendWait("AAPL")
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent: AAPL + Enter"

# ── 6. Wait for chart to load (API call + render) ─────────────────────────
Start-Sleep -Milliseconds 5000

# Re-focus in case something stole it
[Win5]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 500

# ── 7. Screenshot ─────────────────────────────────────────────────────────
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp    = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g      = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_aapl2.png')
$g.Dispose(); $bmp.Dispose()
Write-Host "Screenshot saved: screenshot_aapl2.png"
