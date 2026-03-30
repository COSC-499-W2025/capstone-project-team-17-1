# Install LaTeX dependencies required for PDF resume export (Windows).
# Run in PowerShell as Administrator:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "Installing LaTeX for PDF resume export..." -ForegroundColor Cyan

# ── Try winget (Windows 10 1709+ / Windows 11) ───────────────────────────────
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "winget found — installing MiKTeX..."
    winget install --id MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements
    Write-Host "Done. Restart your terminal, then verify with: xelatex --version" -ForegroundColor Green
    exit 0
}

# ── Try Chocolatey ────────────────────────────────────────────────────────────
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Chocolatey found — installing MiKTeX..."
    choco install miktex --yes
    Write-Host "Done. Restart your terminal, then verify with: xelatex --version" -ForegroundColor Green
    exit 0
}

# ── Fallback: manual download ─────────────────────────────────────────────────
Write-Host ""
Write-Host "Neither winget nor Chocolatey found." -ForegroundColor Yellow
Write-Host "Please install MiKTeX manually:"
Write-Host "  https://miktex.org/download"
Write-Host ""
Write-Host "After installation, restart your terminal and verify with:"
Write-Host "  xelatex --version"
