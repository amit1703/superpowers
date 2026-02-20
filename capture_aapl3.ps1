Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win6 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int n);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int w, int h, bool repaint);
    [DllImport("user32.dll")] public static extern void mouse_event(int f, int dx, int dy, int c, int e);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, ref RECT rect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public const int MOUSEEVENTF_LEFTDOWN = 0x02;
    public const int MOUSEEVENTF_LEFTUP   = 0x04;
    public const int SW_RESTORE  = 9;
}
'@

# ── 1. Find the SWING SCANNER Chrome app window ─────────────────────────
$swingProc = $null
Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match 'SWING|Swing|TERMINAL'
} | ForEach-Object { $swingProc = $_ }

if ($null -eq $swingProc) {
    Write-Host "Opening fresh Chrome app window..."
    Start-Process "chrome" "--new-window --app=http://localhost:5173 --window-size=1600,950 --window-position=0,0"
    Start-Sleep -Milliseconds 6000
    Get-Process -Name 'chrome' -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -match 'SWING|Swing|TERMINAL'
    } | ForEach-Object { $swingProc = $_ }
}

if ($null -eq $swingProc) { Write-Host "ERROR: no window"; exit 1 }
Write-Host "Found: $($swingProc.MainWindowTitle) [PID $($swingProc.Id)]"

# ── 2. Position window ────────────────────────────────────────────────────
$hwnd = $swingProc.MainWindowHandle
[Win6]::ShowWindow($hwnd, [Win6]::SW_RESTORE) | Out-Null
Start-Sleep -Milliseconds 400
[Win6]::MoveWindow($hwnd, 0, 0, 1620, 980, $true) | Out-Null
Start-Sleep -Milliseconds 600
[Win6]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 1000

# ── 3. Get actual window rect to compute click coords ─────────────────────
$rect = New-Object Win6+RECT
[Win6]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
Write-Host "Window rect: L=$($rect.Left) T=$($rect.Top) R=$($rect.Right) B=$($rect.Bottom)"

# Chrome app mode: title bar is ~32px tall
# Header web content is 62px, search input centered => web y ~31
# Screen y = rect.Top + titlebar(32) + 31 = rect.Top + 63
# Search input is centered horizontally in the middle third
# Layout: 340px left | flex-1 center | ~180px right  =>  center at ~(340 + (width-520)/2)
$winWidth = $rect.Right - $rect.Left
$searchX  = $rect.Left + [int](340 + ($winWidth - 520) / 2)
$searchY  = $rect.Top + 63
Write-Host "Clicking at screen: x=$searchX y=$searchY"

# ── 4. Click the search input ─────────────────────────────────────────────
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($searchX, $searchY)
Start-Sleep -Milliseconds 400
[Win6]::mouse_event([Win6]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
Start-Sleep -Milliseconds 80
[Win6]::mouse_event([Win6]::MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
Start-Sleep -Milliseconds 600

# Re-assert focus
[Win6]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 400

# ── 5. Clear any existing text, type AAPL + Enter ─────────────────────────
[System.Windows.Forms.SendKeys]::SendWait("^a")
Start-Sleep -Milliseconds 100
[System.Windows.Forms.SendKeys]::SendWait("{DEL}")
Start-Sleep -Milliseconds 100
[System.Windows.Forms.SendKeys]::SendWait("AAPL")
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
Write-Host "Sent: AAPL + Enter"

# ── 6. Wait for chart to render ────────────────────────────────────────────
Start-Sleep -Milliseconds 6000

# Re-focus
[Win6]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 500

# ── 7. Screenshot the window area only ────────────────────────────────────
# Re-read rect in case it moved
[Win6]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right  - $rect.Left
$h = $rect.Bottom - $rect.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save('C:\Users\1\OneDrive\Desktop\claudeSkillsTest\screenshot_aapl3.png')
$g.Dispose(); $bmp.Dispose()
Write-Host "Screenshot saved: screenshot_aapl3.png"
