# acat - Windows Installation Script (Admin/Global)
# Run as Administrator for global install

param(
    [switch]$Local,
    [switch]$NoOllama
)

$ErrorActionPreference = "Stop"

Write-Host "╔═══════════════════════════════════════════════════════════╗"
Write-Host "║              acat CLI - Windows Installation              ║"
Write-Host "╚═══════════════════════════════════════════════════════════╝"
Write-Host ""

# Determine install location
if ($Local) {
    $InstallDir = "$HOME\.acat"
    Write-Host "Installing locally to: $InstallDir"
} else {
    $InstallDir = "C:\Program Files\acat"
    Write-Host "Installing globally to: $InstallDir"
}

# Check for Ollama
if (-not $NoOllama) {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "Ollama is not installed. Installing..." -ForegroundColor Yellow
        # Download and install Ollama
        $OllamaInstaller = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.ai/download/OllamaSetup.exe" -OutFile $OllamaInstaller
        Start-Process -FilePath $OllamaInstaller -ArgumentList "/SILENT" -Wait
    }
}

# Create directories
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Copy files
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Copying files..."
Copy-Item -Path "$ScriptDir\*" -Destination $InstallDir -Recurse -Force

# Create PowerShell wrapper script with colored banner
$WrapperPath = if ($Local) { "$HOME\.local\bin\acat.ps1" } else { "$InstallDir\acat.ps1" }
New-Item -ItemType Directory -Force -Path (Split-Path $WrapperPath) | Out-Null

$WrapperContent = @'
# acat - AI CLI Agent Tool
# PowerShell wrapper for Windows

param(
    [string]$model,
    [string]$command,
    [switch]$init,
    [switch]$help,
    [switch]$version
)

$InstallDir = "{0}"
$AcacPy = "$InstallDir\src\acat.py"

# Colors
$Blue = "`e[0;34m"
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$NC = "`e[0m"

$DefaultModel = "gemma4:latest"

# Get model from config
function Get-Model {{
    $ConfigPath = "$env:USERPROFILE\.acat\config.json"
    if (Test-Path $ConfigPath) {{
        try {{
            $config = Get-Content $ConfigPath | ConvertFrom-Json
            return $config.model
        }} catch {{
            return $DefaultModel
        }}
    }}
    return $DefaultModel
}}

# Show help
function Show-Help {{
    Write-Host @"
acat - AI CLI Agent Tool

Usage:
  acat [options] [command]

Options:
  -m, -model <name>    Use specified model (default: gemma4:latest)
  -c, -command <text>  Run single command and exit
  -init                 Initialize project (create ACAT.md)
  -h, -help             Show this help message
  -v, -version          Show version

Commands:
  acat                          Start interactive mode
  acat "your question"          Run single command
  acat /init                    Initialize project
  acat -m llama2 "question"     Use specific model

Slash Commands (Interactive Mode):
  /init, /model, /resume, /btw, /config, /tools, /history, /clear, /help, /exit

Examples:
  acat                          # Start interactive session
  acat "explain this code"      # Ask a question
  acat /init                    # Initialize project
"@
}}

# Main logic
if ($help) {{ Show-Help; exit 0 }}
if ($version) {{ Write-Host "acat version 0.1.0"; exit 0 }}

if (-not $model) {{ $model = Get-Model }}

if ($init) {{
    python "$AcacPy" -m $model -c "/init"
    exit
}}

if ($command) {{
    python "$AcacPy" -m $model -c $command
    exit
}}

# Interactive mode with ASCII art banner
Write-Host "$Blue    █████╗  ██████╗  █████╗ ████████╗$NC"
Write-Host "$Blue   ██╔══██╗██╔════╝ ██╔══██╗╚══██╔══╝$NC"
Write-Host "$Blue   ███████║██║      ███████║   ██║   $NC"
Write-Host "$Blue   ██╔══██║██║      ██╔══██║   ██║   $NC"
Write-Host "$Blue   ██║  ██║╚██████╗ ██║  ██║   ██║   $NC"
Write-Host "$Blue   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   $NC"
Write-Host ""
Write-Host "$Blue      Aye Chan Aung Thwin's CLI Agent$NC"
Write-Host "$Blue                (ACAT)$NC"
Write-Host ""
Write-Host "$Blue           Powered by Ollama$NC"
Write-Host ""
Write-Host "Model: $Green$model$NC"
Write-Host "Working directory: $Green$(Get-Location)$NC"
Write-Host ""
Write-Host "Type $Yellow/help$NC for available commands."
Write-Host "Press $Yellow`Ctrl+C$NC to cancel, $Yellow`Ctrl+D$NC or $Yellow`Esc$NC to exit."
Write-Host ""

# Run interactive
python "$AcacPy" -m $model
'@ -f $InstallDir

$WrapperContent | Out-File -FilePath $WrapperPath -Encoding utf8

# Add to PATH automatically (both User and Machine)
Add-ToPath {
    param($PathToAdd)

    # Add to User PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$PathToAdd*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$PathToAdd", "User")
        Write-Host "Added to User PATH" -ForegroundColor Green
    }

    # Add to Machine PATH (requires Admin)
    try {
        $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($machinePath -notlike "*$PathToAdd*") {
            [Environment]::SetEnvironmentVariable("Path", "$machinePath;$PathToAdd", "Machine")
            Write-Host "Added to Machine PATH" -ForegroundColor Green
        }
    } catch {
        Write-Host "Machine PATH update skipped (requires Admin)" -ForegroundColor Yellow
    }
}

Add-ToPath "$InstallDir"

# Pull default model
Write-Host "Pulling default model (gemma4:latest)..." -ForegroundColor Green
ollama pull gemma4:latest 2>$null

Write-Host ""
Write-Host "✓ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Run 'acat' to start."
