param(
    [switch]$docker,
    [switch]$build
)

$root = "C:\Users\trist\course-rag\starting-ragchatbot-codebase"

if ($docker) {
    $cmd = if ($build) { "docker compose up --build" } else { "docker compose up" }
    Write-Host "Demarrage Docker ($cmd)..." -ForegroundColor Cyan
    $job = Start-Job -ScriptBlock {
        param($r, $b)
        Set-Location $r
        if ($b) { docker compose up --build } else { docker compose up }
    } -ArgumentList $root, $build
} else {
    Write-Host "Demarrage du serveur local..." -ForegroundColor Cyan
    $job = Start-Job -ScriptBlock {
        param($r)
        Set-Location "$r\backend"
        uv run uvicorn app:app --reload --port 8000
    } -ArgumentList $root
}

do {
    Start-Sleep -Seconds 2
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/api/courses" -TimeoutSec 2 -ErrorAction Stop | Out-Null
        $ready = $true
    } catch {
        $ready = $false
    }
} while (-not $ready)

Add-Type -AssemblyName System.Speech
(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("le serveur est pret")

Write-Host "Serveur pret sur http://localhost:8000" -ForegroundColor Green

Receive-Job $job -Wait
