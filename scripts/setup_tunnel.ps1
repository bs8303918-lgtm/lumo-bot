# HTTPS tunnel for Telegram Mini App "Open" button
# Usage: .\scripts\setup_tunnel.ps1

function Find-Cloudflared {
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        "$env:ProgramFiles\Cloudflare\cloudflared\cloudflared.exe",
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

# Refresh PATH (winget install may not be visible in old terminals)
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$cloudflared = Find-Cloudflared

Write-Host "Starting cloudflared -> http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Make sure the bot is running first: python main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "When you see https://....trycloudflare.com add to .env:" -ForegroundColor Green
Write-Host "PUBLIC_BASE_URL=https://....trycloudflare.com"
Write-Host "MINI_APP_MENU_TEXT=Open"
Write-Host ""
Write-Host "Restart the bot. The Open button will appear in Telegram." -ForegroundColor Green
Write-Host ""
Write-Host "Tip: HTTP/2 mode (more stable on Windows than QUIC)." -ForegroundColor DarkGray
Write-Host "502 Bad gateway = bot not on :8000 yet, or old tunnel URL in .env" -ForegroundColor DarkGray
Write-Host ""

$botOk = $false
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 3
    $botOk = $true
}
catch {
    $botOk = $false
}

if ($botOk) {
    Write-Host "Bot API on :8000 - OK" -ForegroundColor Green
}
else {
    Write-Host "WARNING: nothing on http://127.0.0.1:8000 - start bot first: python main.py" -ForegroundColor Red
    Write-Host "Mini App will show 502 until the bot is running." -ForegroundColor Red
}
Write-Host ""

if (-not $cloudflared) {
    Write-Host "cloudflared not found. Install:" -ForegroundColor Red
    Write-Host "  winget install Cloudflare.cloudflared"
    Write-Host "Then CLOSE this terminal, open a NEW one, and run this script again."
    exit 1
}

Write-Host "Using: $cloudflared" -ForegroundColor DarkGray
Write-Host ""

& $cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000
