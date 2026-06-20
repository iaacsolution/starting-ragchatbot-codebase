$job = Start-Job -ScriptBlock {
    Set-Location "C:\Users\trist\course-rag\starting-ragchatbot-codebase\backend"
    uv run uvicorn app:app --reload --port 8000
}

Write-Host "Demarrage du serveur..." -ForegroundColor Cyan

do {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/courses" -TimeoutSec 2 -ErrorAction Stop
        $ready = $true
    } catch {
        $ready = $false
    }
} while (-not $ready)

Add-Type -AssemblyName System.Speech
(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("le serveur est pret")

Write-Host "Serveur pret sur http://localhost:8000" -ForegroundColor Green

Receive-Job $job -Wait
