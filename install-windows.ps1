# acat - Windows Installation Script
# Equivalent to install.sh for Windows
# Usage: iex (Invoke-WebRequest -Uri "https://.../install-windows.ps1" -UseBasicParsing)

param(
    [switch]$NoOllama
)

$ErrorActionPreference = "Stop"

# Colors - using [char]27 for Windows PowerShell 5.1 compatibility
$ESC = [char]27
$Red = "$ESC[0;31m"
$Green = "$ESC[0;32m"
$Yellow = "$ESC[1;33m"
$Blue = "$ESC[0;34m"
$Cyan = "$ESC[0;36m"
$NC = "$ESC[0m"

# Configuration
$InstallDir = "$HOME\.acat"
$BinDir = "$HOME\.local\bin"
$GITHUB_REPO = "https://github.com/AyeChanAungThwin/acat-cli"

Write-Host "${Blue}+===========================================================+${NC}"
Write-Host "${Blue}|              acat CLI - Installation                      |${NC}"
Write-Host "${Blue}+===========================================================+${NC}"
Write-Host ""

# Step 1: Check for Ollama
Write-Host "${Cyan}[1/7] Checking Ollama...${NC}"
if (-not $NoOllama) {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "${Yellow}  Ollama is not installed.${NC}"
        Write-Host "${Cyan}      Installing Ollama...${NC}"
        $OllamaInstaller = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.ai/download/OllamaSetup.exe" -OutFile $OllamaInstaller
        Start-Process -FilePath $OllamaInstaller -ArgumentList "/SILENT" -Wait
        if (Get-Command "ollama" -ErrorAction SilentlyContinue) {
            Write-Host "${Green}  [OK] Ollama installed${NC}"
        }
    } else {
        Write-Host "${Green}  [OK] Ollama already installed${NC}"
    }
} else {
    Write-Host "${Yellow}  Ollama check skipped (NoOllama flag)${NC}"
}
Write-Host ""

# Step 2: Create directories
Write-Host "${Cyan}[2/7] Creating directories...${NC}"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallDir\bin" | Out-Null
Write-Host "${Green}  [OK] Created $InstallDir${NC}"
Write-Host "${Green}  [OK] Created $BinDir${NC}"
Write-Host ""

# Step 3: Download acat from GitHub
Write-Host "${Cyan}[3/7] Downloading acat from GitHub...${NC}"
$TempDir = Join-Path $env:TEMP "acat-$(Get-Random)"
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
$downloaded = $false
try {
    $ZipPath = Join-Path $TempDir "acat.zip"
    Invoke-WebRequest -Uri "$GITHUB_REPO/archive/refs/heads/main.zip" -OutFile $ZipPath
    Expand-Archive -Path $ZipPath -DestinationPath $TempDir -Force
    $ExtractedDir = Join-Path $TempDir "acat-cli-main"
    if ((Test-Path "$ExtractedDir\bin\acat") -and (Test-Path "$ExtractedDir\src")) {
        # Remove old installation first to ensure clean override
        Get-ChildItem -Path $InstallDir -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item -Path "$ExtractedDir\*" -Destination $InstallDir -Recurse -Force
        Write-Host "${Green}  [OK] Downloaded acat from GitHub${NC}"
        Write-Host "${Green}  [OK] Copied acat source files${NC}"
        $downloaded = $true
    } else {
        Write-Host "${Red}  [FAIL] Error: Invalid acat archive structure${NC}"
    }
} catch {
    Write-Host "${Red}  [FAIL] Error: Failed to download from GitHub${NC}"
    Write-Host "  Trying local copy..."
}

if (-not $downloaded) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if ((Test-Path "$ScriptDir\bin\acat") -and (Test-Path "$ScriptDir\src")) {
        # Remove old installation first to ensure clean override
        Get-ChildItem -Path $InstallDir -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item -Path "$ScriptDir\*" -Destination $InstallDir -Recurse -Force
        Write-Host "${Green}  [OK] Copied from local source${NC}"
    } else {
        Write-Host "${Red}  [FAIL] Error: acat source files not found${NC}"
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        exit 1
    }
}
Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ""

# Step 4: Create default configuration
Write-Host "${Cyan}[4/7] Creating default configuration...${NC}"
$ConfigPath = "$InstallDir\config.json"
if (-not (Test-Path $ConfigPath)) {
    $ConfigContent = '{"model": "gemma4:latest", "provider": "ollama"}'
    [System.IO.File]::WriteAllText($ConfigPath, $ConfigContent, [System.Text.Encoding]::UTF8)
    Write-Host "${Green}  [OK] Created config.json with default model: gemma4:latest${NC}"
} else {
    Write-Host "${Yellow}  [!] config.json already exists, keeping existing configuration${NC}"
}
Write-Host ""

# Step 5: Create PATH wrapper
Write-Host "${Cyan}[5/7] Creating PATH wrapper...${NC}"

# Create main PowerShell launcher in install dir (equivalent to bin/acat for Windows)
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

$ESC = [char]27
$Red = "$ESC[0;31m"
$Green = "$ESC[0;32m"
$Yellow = "$ESC[1;33m"
$Blue = "$ESC[0;34m"
$NC = "$ESC[0m"

$InstallDir = "$HOME\.acat"
$AcatPy = "$InstallDir\src\acat.py"
$ConfigDir = "$env:USERPROFILE\.acat"
$DefaultModel = "gemma4:latest"

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
        Write-Host "${Red}Error: Ollama is not installed.${NC}"
        Write-Host "Install Ollama: https://ollama.ai"
        exit 1
    }

    # Check if Ollama is running
    $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if (-not $ollamaProcess) {
        Write-Host "${Yellow}Warning: Ollama is not running. Starting Ollama...${NC}"
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
            Write-Host "${Yellow}Model '$ModelName' not found. Pulling...${NC}"
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
  acat -m llama2 "question"    Use specific model

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
    python "$AcatPy" -m $resolvedModel -c $resolvedCmd
} else {
    # Interactive mode with banner
    Write-Host "${Blue}    ======  ========  ====== ==========${NC}"
    Write-Host "${Blue}   ==  ==== ========  ==  ==== ==========${NC}"
    Write-Host "${Blue}   =======  ===       =======    ===   ${NC}"
    Write-Host "${Blue}   ==  ==== ===       ==  ====    ===   ${NC}"
    Write-Host "${Blue}   ==   === ========  ==   ===    ===   ${NC}"
    Write-Host "${Blue}   ===   == ========  ===   ==    ===   ${NC}"
    Write-Host ""
    Write-Host "${Blue}      Aye Chan Aung Thwin's CLI Agent${NC}"
    Write-Host "${Blue}                (ACAT)${NC}"
    Write-Host ""
    Write-Host "${Blue}           Powered by Ollama${NC}"
    Write-Host ""
    Write-Host "Model: ${Green}${resolvedModel}${NC}"
    Write-Host "Working directory: ${Green}$(Get-Location)${NC}"
    Write-Host ""
    Write-Host "Type ${Yellow}/help${NC} for available commands."
    Write-Host "Press ${Yellow}Ctrl+C${NC} to cancel, ${Yellow}Ctrl+D${NC} or ${Yellow}Esc${NC} to exit."
    Write-Host ""

    # Run interactive
    python "$AcatPy" -m $resolvedModel
}
'@
$MainWrapperContent | Out-File -FilePath $MainWrapperPath -Encoding utf8
Write-Host "${Green}  [OK] Created $MainWrapperPath${NC}"

# Create CMD wrapper that bypasses PowerShell execution policy
# Using .cmd instead of .ps1 because .ps1 scripts are blocked by default execution policy
# Remove old .ps1 wrapper if it exists from a previous installation
if (Test-Path "$BinDir\acat.ps1") {
    Remove-Item "$BinDir\acat.ps1" -Force -ErrorAction SilentlyContinue
}
$CmdWrapperPath = "$BinDir\acat.cmd"
$CmdWrapperContent = @"
@echo off
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "$InstallDir\bin\acat.ps1" %*
"@
Set-Content -Path $CmdWrapperPath -Value $CmdWrapperContent -Encoding ASCII
Write-Host "${Green}  [OK] Created ${BinDir}\acat.cmd${NC}"
Write-Host ""

# Step 6: Add to PATH for global access
Write-Host "${Cyan}[6/7] Configuring PATH for global access...${NC}"

$profileAdded = ""

# Add to User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    $profileAdded = "User PATH"
    Write-Host "${Green}  [OK] Added PATH entry to User PATH${NC}"
} else {
    Write-Host "${Yellow}  [!] PATH already configured in User PATH${NC}"
}

# Export for current session
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + $env:Path

if ([string]::IsNullOrEmpty($profileAdded)) {
    Write-Host "${Yellow}  [!] PATH already configured${NC}"
}
Write-Host ""

# Step 7: Pull default model
Write-Host "${Cyan}[7/7] Pulling default model (gemma4:latest)...${NC}"
$pullSuccess = $false
try {
    $ErrorActionPreference = "Continue"
    ollama pull gemma4:latest 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $pullSuccess = $true
    }
} catch {
    $pullSuccess = $false
}
if ($pullSuccess) {
    Write-Host "${Green}  [OK] Model pulled successfully${NC}"
} else {
    Write-Host "${Yellow}  [!] Model pull failed. Run 'ollama pull gemma4:latest' later.${NC}"
}
Write-Host ""

# Installation complete summary
Write-Host ""
Write-Host "${Green}+===========================================================+${NC}"
Write-Host "${Green}|              [OK] Installation Complete!                  |${NC}"
Write-Host "${Green}+===========================================================+${NC}"
Write-Host ""
Write-Host "${Cyan}Installation Summary:${NC}"
Write-Host "  * acat installed to: $InstallDir"
Write-Host "  * Wrapper created at: ${BinDir}\acat.cmd"
Write-Host "  * PATH configured in: User PATH"
Write-Host "  * Default model: gemma4:latest"
Write-Host ""
Write-Host "${Yellow}Next steps:${NC}"
Write-Host "  1. Restart PowerShell"
Write-Host "  2. Then run: acat --version"
Write-Host ""
Write-Host "${Cyan}After restarting, 'acat' will be available globally from anywhere!${NC}"