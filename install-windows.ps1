# Cài claude-restore trên Windows.
#   powershell -ExecutionPolicy Bypass -File .\install-windows.ps1              cài / cập nhật
#   powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -Uninstall   gỡ
param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Tìm python thật (bỏ qua lối tắt mở Microsoft Store)
$py = $null
$probe = 'import sys; print(sys.executable)'
foreach ($c in 'py', 'python', 'python3') {
    try {
        if ($c -eq 'py') { $exe = & py -3 -c $probe 2>$null } else { $exe = & $c -c $probe 2>$null }
        if ($LASTEXITCODE -eq 0 -and $exe) {
            $exe = ([string]$exe).Trim()
            if (Test-Path $exe) { $py = $exe; break }
        }
    } catch {}
}
if (-not $py) { Write-Host "Cần Python 3: cài từ https://www.python.org/downloads/ (tick 'Add python.exe to PATH')."; exit 1 }

$claudeDir = Join-Path $HOME '.claude'
$hook = Join-Path $claudeDir 'hooks\session-registry.py'
$binDir = Join-Path $claudeDir 'bin'
$restore = Join-Path $binDir 'claude-restore.py'
$cmd = Join-Path $binDir 'claude-restore.cmd'

if ($Uninstall) {
    & $py merge_settings.py --remove
    foreach ($f in @($hook, $restore, $cmd)) {
        if (Test-Path $f) { Move-Item $f "$f.removed" -Force; Write-Host "Đã đổi tên $f -> $f.removed" }
    }
    Write-Host "Đã gỡ. Mở lại Claude Code để áp dụng."
    exit 0
}

New-Item -ItemType Directory -Force (Split-Path $hook) | Out-Null
New-Item -ItemType Directory -Force $binDir | Out-Null
Copy-Item session-registry.py $hook -Force
Copy-Item claude-restore.py $restore -Force
Set-Content -Path $cmd -Encoding ASCII -Value "@`"$py`" `"$restore`" %*"
Write-Host "Đã chép: $hook"
Write-Host "Đã chép: $restore (+ claude-restore.cmd)"

& $py merge_settings.py $py $hook
if ($LASTEXITCODE -ne 0) { Write-Host "Ghép settings.json lỗi, chưa đổi gì."; exit 1 }

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not ($userPath -split ';' | Where-Object { $_ -eq $binDir })) {
    [Environment]::SetEnvironmentVariable('Path', ($userPath.TrimEnd(';') + ';' + $binDir), 'User')
    Write-Host "Đã thêm $binDir vào PATH (mở cửa sổ terminal mới để có hiệu lực)."
}

Write-Host ""
Write-Host "Xong. Việc còn lại:"
Write-Host "  1. Thoát và mở lại các phiên Claude Code đang chạy (hoặc gõ /hooks một lần) để nạp hook."
Write-Host "  2. Sau khi máy tắt/bật lại: mở terminal, gõ  claude-restore"
Write-Host "     Tab mở bằng Windows Terminal (wt); không có thì mở cửa sổ cmd riêng."
