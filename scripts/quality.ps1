# Run all code quality checks from the project root.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Formatting with black ===" -ForegroundColor Cyan
uv run black backend/

Write-Host ""
Write-Host "=== Running tests ===" -ForegroundColor Cyan
uv run pytest backend/tests/ -v

Write-Host ""
Write-Host "Quality checks passed." -ForegroundColor Green
