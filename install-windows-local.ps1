# acat - Windows Local Installation Script
# Equivalent to install-local.sh for Windows
# No admin rights required

param(
    [switch]$NoOllama
)

$ErrorActionPreference = "Stop"

# Colors
$Red = "`e[0;31m"
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$Blue = "`e[0;34m"
$Cyan = "`e[0;36m"
$NC = "`e[0m"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = "$HOME\.acat"
$BinDir = "$HOME\.local\bin"
$GITHUB_REPO = "https://github.com/AyeChanAungThwin/acat-cli"

Write-Host "$Blue╔═══════════════════════════════════════════════════════════╗$NC"
Write-Host "$Blue║           acat CLI - Local Installation                   ║$NC"
Write-Host "$Blue╚═══════════════════════════════════════════════════════════╝$NC"
Write-Host ""

# Step 1: Check for Ollama
Write-Host "$Cyan[1/6] Checking Ollama...$NC"
if (-not $NoOllama) {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "$Yellow  Ollama is not installed.$NC"
        Write-Host "$Cyan      Installing Ollama...$NC"
        $OllamaInstaller = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.ai/download/OllamaSetup.exe" -OutFile $OllamaInstaller
        Start-Process -FilePath $OllamaInstaller -ArgumentList "/SILENT" -Wait
        if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
            Write-Host "$Green  ✓ Ollama installed$NC"
        }
    } else {
        Write-Host "$Green  ✓ Ollama already installed$NC"
    }
} else {
    Write-Host "$Yellow  Ollama check skipped (NoOllama flag)$NC"
}
Write-Host ""

# Step 2: Create directories
Write-Host "$Cyan[2/6] Creating directories...$NC"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\bin" | Out-Null
Write-Host "$Green  ✓ Created $InstallDir$NC"
Write-Host "$Green  ✓ Created $BinDir$NC"
Write-Host ""

# Step 3: Copy from local source
Write-Host "$Cyan[3/6] Copying acat from local source...$NC"
if ((Test-Path "$ScriptDir\bin\acat") -and (Test-Path "$ScriptDir\src")) {
    # Remove old installation first to ensure clean override
    Get-ChildItem -Path $InstallDir -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item -Path "$ScriptDir\*" -Destination $InstallDir -Recurse -Force
    Write-Host "$Green  ✓ Copied acat source files$NC"
} else {
    Write-Host "$Red  ✗ Error: acat source files not found in $ScriptDir$NC"
    Write-Host "  Make sure you are running this script from the acat-cli directory."
    exit 1
}
Write-Host ""

# Step 4: Create PATH wrapper
Write-Host "$Cyan[4/6] Creating PATH wrapper...$NC"

# Create main PowerShell launcher in install dir
$MainWrapperPath = "$InstallDir\bin\acat.ps1"
$MainWrapperContent = @'
# acat - AI CLI Agent Tool
# PowerShell launcher for Windows
# Equivalent to bin/acat

param(
    [Alias("m")]
    [string]$model,
    [Alias("c")]
    [string]$command,
    [switch]$init,
    [switch]$help,
    [switch]$version
)

$InstallDir = "$HOME\.acat"
$AcacPy = "$InstallDir\src\acat.py"
$ConfigDir = "$env:USERPROFILE\.acat"
$DefaultModel = "gemma4:latest"

# Colors
$Red = "`e[0;31m"
$Green = "`e[0;32m"
$Yellow = "`e[1;33m"
$Blue = "`e[0;34m"
$NC = "`e[0m"

# Get model from config
function Get-Model {
    $ConfigPath = "$ConfigDir\config.json"
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

# Check if Ollama is available
function Test-Ollama {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "$RedError: Ollama is not installed.$NC"
        Write-Host "Install Ollama: https://ollama.ai"
        exit 1
    }

    # Check if Ollama is running
    $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if (-not $ollamaProcess) {
        Write-Host "$YellowWarning: Ollama is not running. Starting Ollama...$NC"
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }
}

# Check if model is available
function Test-Model {
    param($ModelName)
    try {
        $models = ollama list 2>$null
        if ($models -notmatch [regex]::Escape($ModelName)) {
            Write-Host "$YellowModel '$ModelName' not found. Pulling...$NC"
            ollama pull $ModelName
        }
    } catch {
        # If ollama list fails, skip check
    }
}

# Show help
function Show-Help {
    Write-Host @"
acat - AI CLI Agent Tool

Usage:
  acat [options] [command]

Options:
  -m, --model <name>    Use specified model (default: gemma4:latest)
  -c, --command <text>  Run single command and exit
  --init                Initialize project (create ACAT.md)
  -h, --help            Show this help message
  -v, --version         Show version

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
}

# Resolve model
$resolvedModel = if ($model) { $model } else { Get-Model }

# Handle flags
if ($help) { Show-Help; exit 0 }
if ($version) { Write-Host "acat version 0.1.0"; exit 0 }

# Check Ollama
Test-Ollama
Test-Model $resolvedModel

# Determine command
$resolvedCmd = if ($command) { $command } elseif ($init) { "/init" } else { "" }

# Handle positional arguments as command
if (-not $resolvedCmd -and $args.Count -gt 0) {
    $resolvedCmd = $args -join " "
}

# Run Python agent
if ($resolvedCmd) {
    # Single command mode
    python "$AcacPy" -m $resolvedModel -c $resolvedCmd
} else {
    # Interactive mode with banner
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
    Write-Host "Model: $Green$resolvedModel$NC"
    Write-Host "Working directory: $Green$(Get-Location)$NC"
    Write-Host ""
    Write-Host "Type $Yellow/help$NC for available commands."
    Write-Host "Press $Yellow`Ctrl+C$NC to cancel, $Yellow`Ctrl+D$NC or $Yellow`Esc$NC to exit."
    Write-Host ""

    # Run interactive
    python "$AcacPy" -m $resolvedModel
}
'@
$MainWrapperContent | Out-File -FilePath $MainWrapperPath -Encoding utf8
Write-Host "$Green  ✓ Created $MainWrapperPath$NC"

# Create simple PATH wrapper that delegates to main launcher
$PathWrapperPath = "$BinDir\acat.ps1"
$PathWrapperContent = @"
& "$InstallDir\bin\acat.ps1" @args
"@
$PathWrapperContent | Out-File -FilePath $PathWrapperPath -Encoding utf8
Write-Host "$Green  ✓ Created $BinDir\acat.ps1$NC"
Write-Host ""

# Step 5: Configure PATH for global access
Write-Host "$Cyan[5/6] Configuring PATH for global access...$NC"

$profileAdded = ""

# Add to User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $profileAdded = "User PATH"
    Write-Host "$Green  ✓ Added PATH entry to User PATH$NC"
} else {
    Write-Host "$Yellow  ! PATH already configured in User PATH$NC"
}

# Refresh current session PATH
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path

if ([string]::IsNullOrEmpty($profileAdded)) {
    Write-Host "$Yellow  ! PATH already configured$NC"
}
Write-Host ""

# Step 6: Pull default model
Write-Host "$Cyan[6/6] Pulling default model (gemma4:latest)...$NC"
ollama pull gemma4:latest 2>$null
if ($?) {
    Write-Host "$Green  ✓ Model pulled successfully$NC"
} else {
    Write-Host "$Yellow  ! Model pull failed. Run 'ollama pull gemma4:latest' later.$NC"
}
Write-Host ""

# Installation complete summary
Write-Host ""
Write-Host "$Green╔═══════════════════════════════════════════════════════════╗$NC"
Write-Host "$Green║              ✓ Installation Complete!                     ║$NC"
Write-Host "$Green╚═══════════════════════════════════════════════════════════╝$NC"
Write-Host ""
Write-Host "$CyanInstallation Summary:$NC"
Write-Host "  * acat installed to: $InstallDir"
Write-Host "  * Wrapper created at: $BinDir\acat.ps1"
Write-Host "  * PATH configured in: User PATH"
Write-Host ""
Write-Host "$YellowNext steps:$NC"
Write-Host "  1. Restart PowerShell"
Write-Host "  2. Then run: acat --version"
Write-Host ""
Write-Host "$CyanAfter restarting, 'acat' will be available globally from anywhere!$NC"