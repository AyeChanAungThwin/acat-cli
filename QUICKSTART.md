# acat CLI Pro - Quick Start Guide

## 1. One-Line Installation (Linux/Mac)

**Recommended - Auto PATH configuration:**

```bash
curl -fsSL https://github.com/AyeChanAungThwin/acat-cli/raw/main/install.sh | bash
```

The installer automatically:
- Installs acat to `~/.acat`
- Adds `~/.local/bin` to your PATH in `.zshrc`/`.bashrc`
- Pulls the default model (gemma4:latest)
- Installs Ollama if not present

**Note:** Restart your terminal or run `source ~/.zshrc` (or `source ~/.bashrc`) after installation.

## 2. Manual Installation

### Linux/Mac (Global - Auto PATH)

```bash
# Clone repository
git clone https://github.com/AyeChanAungThwin/acat-cli.git ~/.acat
cd ~/.acat

# Run installation (auto PATH)
chmod +x install-global.sh bin/acat
./install-global.sh
```

This installs to `~/.acat` and automatically adds `~/.local/bin` to your PATH.

### Linux/Mac (Local, no PATH change)

```bash
git clone https://github.com/AyeChanAungThwin/acat-cli.git
cd acat
chmod +x bin/acat install-local.sh
./install-local.sh
./acat
```

### Windows (PowerShell - Admin, Auto PATH)

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invoke-WebRequest -Uri "https://github.com/AyeChanAungThwin/acat-cli/raw/main/install-windows.ps1" -OutFile "$env:TEMP\install-acat.ps1"
& "$env:TEMP\install-acat.ps1"

# Verify
acat --version
```

Automatically adds acat to User and Machine PATH.

### Windows (Local, no Admin, Optional PATH)

```powershell
Invoke-WebRequest -Uri "https://github.com/AyeChanAungThwin/acat-cli/raw/main/install-windows-local.ps1" -OutFile "$env:TEMP\install-acat-local.ps1"
& "$env:TEMP\install-acat-local.ps1"
.\acat.bat --version
```

Prompts to add to User PATH (no admin required).

## 3. First Run

```bash
# Start acat
acat

# Or with specific model
acat -m llama2
```

## 4. Basic Usage

### Interactive Mode
```bash
acat
> /help
> /init
> /toggle          # Toggle show/hide AI explanations
> "How do I create a REST API?"
> /exit
```

### Single Command
```bash
acat "Explain how to use async/await in JavaScript"
```

### Scaffold Project
```bash
acat "/scaffold react my-app"
cd my-app
npm install
npm start
```

## 5. Common Commands

```bash
# Initialize current project
acat /init

# Change model
acat /model codellama

# Toggle show/hide AI explanations
acat /toggle

# View conversation history
acat /history 5

# Clear conversation
acat /clear

# Scaffold different project types
acat "/scaffold spring-boot my-api"
acat "/scaffold static-web my-site"
acat "/scaffold electron my-desktop-app"
```

## 6. Keyboard Shortcuts

- `Ctrl+C` - Cancel current response
- `Ctrl+D` - Exit acat
- `Ctrl+L` - Clear screen

## 7. Troubleshooting

### Ollama not running
```bash
ollama serve
```

### Pull model manually
```bash
ollama pull gemma4:latest
```

### Check installation
```bash
acat --version
acat /tools
```
