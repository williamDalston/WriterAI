# Full pipeline run using local Ollama model.
# Prereqs: Ollama installed and running. Model pulled: ollama run qwen2.5:14b
#
# Usage: .\run_local.ps1 [project]
# Example: .\run_local.ps1 burning-vows-30k

param(
    [string]$Project = "burning-vows-30k"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "`n=== LOCAL PIPELINE RUN ===" -ForegroundColor Cyan
Write-Host "Project: $Project"
Write-Host "Model: qwen2.5:14b (Ollama)`n"

# Quick Ollama health check
try {
    $null = ollama list 2>&1
    Write-Host "Ollama: OK" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama may not be running. Start with: ollama serve" -ForegroundColor Yellow
    Write-Host "Pull model if needed: ollama run qwen2.5:14b`n"
}

# Run overnight script (handles full pipeline + export)
python run_overnight.py $Project
