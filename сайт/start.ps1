# Запуск демо-сайта Lumo (бэкенд + фронтенд)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$LumoDb = Join-Path (Split-Path -Parent $Root) "lumo.db"

if (-not (Test-Path $LumoDb)) {
    Write-Host "ОШИБКА: не найден lumo.db по пути:" -ForegroundColor Red
    Write-Host "  $LumoDb"
    Write-Host "Сначала запусти бота — он создаст и наполнит базу."
    exit 1
}

Write-Host "База: $LumoDb" -ForegroundColor Green

$env:LUMO_DB = $LumoDb

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$Backend'; `$env:LUMO_DB='$LumoDb'; .\.venv\Scripts\python -m uvicorn main:app --reload --port 8000"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$Frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "Открой: http://localhost:5173" -ForegroundColor Cyan
Write-Host "API:    http://127.0.0.1:8000/api/lumo/status"
