# acat - Windows Local Installation Script
# No admin rights required

param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = "$ScriptDir"

Write-Host "Installing acat locally to: $InstallDir"

# Create batch wrapper with ASCII art banner
$WrapperPath = "$InstallDir\acat.bat"
$BatchContent = @"
@echo off
:: acat - AI CLI Agent Tool
:: Windows Batch wrapper

set "ACAT_PY=%~dp0src\acat.py"
set "DEFAULT_MODEL=gemma4:latest"

:: Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo Error: Ollama is not installed.
    echo Install from: https://ollama.ai
    exit /b 1
)

:: Show ASCII art banner
powershell -Command "Write-Host '    █████╗  ██████╗  █████╗ ████████╗' -ForegroundColor Blue; `
Write-Host '   ██╔══██╗██╔════╝ ██╔══██╗╚══██╔══╝' -ForegroundColor Blue; `
Write-Host '   ███████║██║      ███████║   ██║   ' -ForegroundColor Blue; `
Write-Host '   ██╔══██║██║      ██╔══██║   ██║   ' -ForegroundColor Blue; `
Write-Host '   ██║  ██║╚██████╗ ██║  ██║   ██║   ' -ForegroundColor Blue; `
Write-Host '   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ' -ForegroundColor Blue; `
Write-Host ''; `
Write-Host '      Aye Chan Aung Thwin'\''s CLI Agent' -ForegroundColor Blue; `
Write-Host '                (ACAT)' -ForegroundColor Blue; `
Write-Host ''; `
Write-Host '           Powered by Ollama' -ForegroundColor Blue; `
Write-Host ''; `
Write-Host 'Model: gemma4:latest' -ForegroundColor Green; `
Write-Host 'Working directory: %CD%' -ForegroundColor Green; `
Write-Host ''; `
Write-Host 'Type /help for available commands.' -ForegroundColor Yellow; `
Write-Host 'Press Ctrl+C to cancel, Ctrl+D or Esc to exit.' -ForegroundColor Yellow; `
Write-Host ''"

:: Run Python
python "%~dp0src\acat.py" %*
"@
$BatchContent | Out-File -FilePath $WrapperPath -Encoding utf8

# Create PowerShell wrapper with ASCII art banner
$PsWrapperPath = "$InstallDir\acat.ps1"
$PsContent = @'
# acat - AI CLI Agent Tool
# PowerShell wrapper for Windows

param(
    [string]$model,
    [string]$command,
    [switch]$init,
    [switch]$help,
    [switch]$version
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AcacPy = "$ScriptDir\src\acat.py"

# Colors using ANSI escape codes
$Blue = "`e[0;34m"
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$NC = "`e[0m"

$DefaultModel = "gemma4:latest"

# Get model from config
function Get-Model {
    $ConfigPath = "$env:USERPROFILE\.acat\config.json"
    if (Test-Path $ConfigPath) {
        try {
            $config = Get-Content $ConfigPath | ConvertFrom-Json
            return $config.model
        } catch {
            return $DefaultModel
        }
    }
    return $DefaultModel
}

# Show help
function Show-Help {
    Write-Host @"
acat - AI CLI Agent Tool

Usage:
  acat [options] [command]

Options:
  -model <name>      Use specified model (default: gemma4:latest)
  -command <text>    Run single command and exit
  -init              Initialize project (create ACAT.md)
  -help              Show this help message
  -version           Show version

Commands:
  acat                      Start interactive mode
  acat "your question"      Run single command
  acat /init                Initialize project

Slash Commands (Interactive Mode):
  /init, /model, /resume, /btw, /config, /tools, /history, /clear, /help, /exit
"@
}

if ($help) { Show-Help; exit 0 }
if ($version) { Write-Host "acat version 0.1.0"; exit 0 }

if (-not $model) { $model = Get-Model }

if ($init) {
    python "$AcacPy" -m $model -c "/init"
    exit
}

if ($command) {
    python "$AcacPy" -m $model -c $command
    exit
}

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
'@
$PsContent | Out-File -FilePath $PsWrapperPath -Encoding utf8

# Ask if user wants to add to PATH
Write-Host ""
$addPath = Read-Host "Add acat to PATH automatically? [y/N]"
if ($addPath -eq "y" -or $addPath -eq "Y") {
    # Add to User PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$InstallDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
        Write-Host "✓ Added $InstallDir to User PATH" -ForegroundColor Green
        Write-Host "  Restart PowerShell for changes to take effect" -ForegroundColor Yellow
    } else {
        Write-Host "✓ PATH already configured" -ForegroundColor Green
    }

    # Refresh current session PATH
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path
}

Write-Host ""
Write-Host "✓ Local installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Run with: .\acat.bat or .\acat.ps1"
if ($addPath -ne "y" -and $addPath -ne "Y") {
    Write-Host "Or add alias in PowerShell:"
    Write-Host "  Set-Alias acat '$WrapperPath'"
}
