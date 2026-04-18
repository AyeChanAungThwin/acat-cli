# acat CLI Agent Tool

AI CLI Agent Tool with multi-provider support (Ollama offline / OpenAI / Gemini / Groq online) and tool calling capabilities.

## Features

- **Multi-Provider Support**: Offline (Ollama) or Online (OpenAI / Gemini / Groq)
- **Tool Calling**: Read/write files, search, execute commands, scaffold projects
- **Project Scaffolding**: Static web, Spring Boot, WPF C#, React, React Native, Electron
- **Slash Commands**: Claude Code-like commands for productivity
- **Confirmation Before Changes**: Shows diff and asks for user confirmation (y/Y/n)
- **Toggle Explanations**: Use `/toggle` to show/hide detailed AI responses
- **Keyboard Shortcuts**: Ctrl+C (cancel), Ctrl+D (exit), Ctrl+L (clear)
- **Session Persistence**: Auto-save conversation history

## Quick Install

### One-Line Install (Linux/Mac)

**Option 1: Download and run (recommended)**

```bash
curl -fsSL https://github.com/AyeChanAungThwin/acat-cli/raw/main/install.sh -o install.sh && source install.sh
```

This downloads and runs the installer in one command. After installation, `acat` will be available immediately.

**Option 2: Pipe to bash**

```bash
curl -fsSL https://github.com/AyeChanAungThwin/acat-cli/raw/main/install.sh | bash
```

After installation, restart your terminal or run `source ~/.zshrc` (or `source ~/.bashrc`).

The installer automatically:
- Installs acat to `~/.acat`
- Adds `~/.local/bin` to your PATH in `.zshrc`/`.bashrc`
- Pulls the default model (gemma4:latest)
- Installs Ollama if not present

### Manual Install

#### Linux/Mac (Global - Auto PATH)

```bash
git clone https://github.com/AyeChanAungThwin/acat-cli.git ~/.acat
cd ~/.acat
./install-global.sh
```

This installs to `~/.acat` and automatically adds `~/.local/bin` to your PATH in `.zshrc`/`.bashrc`.

#### Linux/Mac (Local - No PATH change)

```bash
git clone https://github.com/AyeChanAungThwin/acat-cli.git
cd acat
./install-local.sh
./acat
```

#### Windows (Admin/Global - Auto PATH)

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invoke-WebRequest -Uri "https://github.com/AyeChanAungThwin/acat-cli/raw/main/install-windows.ps1" -OutFile "$env:TEMP\install-acat.ps1"
& "$env:TEMP\install-acat.ps1"
```

Automatically adds acat to User and Machine PATH.

#### Windows (Local, No Admin - Optional PATH)

```powershell
Invoke-WebRequest -Uri "https://github.com/AyeChanAungThwin/acat-cli/raw/main/install-windows-local.ps1" -OutFile "$env:TEMP\install-acat-local.ps1"
& "$env:TEMP\install-acat-local.ps1"
```

Prompts to add to User PATH (no admin required).

## Requirements

- **Python 3.8+**
- **Ollama** (for offline mode): Install from https://ollama.ai
- **API Key** (for online mode): OpenAI, Gemini, or Groq API key

## Usage

### Interactive Mode

```bash
acat
```

### Single Command

```bash
acat "explain how to create a REST API in Spring Boot"
```

### With Specific Model

```bash
acat -m llama2 "your question"
acat --model codellama "generate a Python function"
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/init` | Analyze project, create/update ACAT.md |
| `/model [name]` | Get or set the AI model |
| `/provider [name]` | Switch provider (ollama/openai/gemini/groq) |
| `/key [key]` | Set API key for online providers |
| `/endpoint [url]` | Set API endpoint for online providers |
| `/resume` | Resume previous session |
| `/btw <note>` | Add context/note to conversation |
| `/toggle` | Toggle show/hide AI explanation details |
| `/config` | Show current configuration |
| `/tools` | List available tools |
| `/history [n]` | Show last n messages |
| `/clear` | Clear conversation history |
| `/help` | Show help message |
| `/exit` | Exit acat |
| `/scaffold <template> <name>` | Create project from template |
| `/templates` | List available templates |
| `/explain <file>` | Explain code in a file |
| `/fix <file> [issue]` | Find and fix issues in code |
| `/test <file>` | Generate tests for code |
| `/summarize [file]` | Summarize code or conversation |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current response |
| `Ctrl+D` | Exit acat |
| `Ctrl+L` | Clear screen |
| `Esc` | Stop agent (via signal) |

## Project Scaffolding

Create new projects with built-in templates:

```bash
acat "/scaffold static-web my-website"
acat "/scaffold spring-boot my-api"
acat "/scaffold react my-app"
acat "/scaffold react-native my-mobile-app"
acat "/scaffold wpf-csharp my-desktop-app"
acat "/scaffold electron my-electron-app"
```

### Templates

- **static-web**: Vanilla HTML/CSS/JavaScript
- **spring-boot**: Java 17+, Maven, Spring Boot 3.2
- **wpf-csharp**: .NET 8 WPF desktop app
- **react**: React 18 with Create React App structure
- **react-native**: React Native mobile app
- **electron**: Electron desktop app (wraps React/static web)

## Providers: Offline vs Online

acat supports four providers:

| Provider | Mode | Backend | API Key Required |
|----------|------|---------|-----------------|
| `ollama` | Offline | Local Ollama | No |
| `openai` | Online | OpenAI-compatible API | Yes |
| `gemini` | Online | Google Gemini API | Yes |
| `groq` | Online | Groq (fast inference) | Yes |

### Switching Providers

```bash
# Switch to offline (Ollama)
acat /provider ollama

# Switch to online (OpenAI-compatible)
acat /provider openai

# Switch to online (Google Gemini)
acat /provider gemini

# Switch to online (Groq - fast inference)
acat /provider groq
```

### Setting Up Online Provider

```bash
# Set your API key
acat /key sk-your-api-key-here

# Optionally change the API endpoint (default: https://api.openai.com/v1)
acat /endpoint https://api.openai.com/v1

# Set the model
acat /model gpt-4o-mini
```

Works with any OpenAI-compatible API (OpenRouter, Together AI, etc.):

```bash
# Example: OpenRouter
acat /endpoint https://openrouter.ai/api/v1
acat /key sk-or-your-key
acat /model openai/gpt-4o-mini
```

### Setting Up Gemini Provider

```bash
# Switch to Gemini (auto-sets model and endpoint)
acat /provider gemini

# Set your Gemini API key (get one at https://aistudio.google.com/apikey)
acat /key AIzaSy...

# Optionally change the model (default: gemini-2.0-flash)
acat /model gemini-2.5-flash
```

Supported Gemini models with function calling:
- `gemini-2.0-flash` (default, fast and capable)
- `gemini-2.5-flash` (latest Flash)
- `gemini-2.5-pro` (most capable)

### Setting Up Groq Provider

```bash
# Switch to Groq (auto-sets model and endpoint)
acat /provider groq

# Set your Groq API key (get one at https://console.groq.com/keys)
acat /key gsk_your-key

# Optionally change the model (default: llama-3.3-70b-versatile)
acat /model llama-3.3-70b-versatile
```

Supported Groq models with function calling:
- `llama-3.3-70b-versatile` (default, balanced)
- `llama-3.1-8b-instant` (fastest)
- `mixtral-8x7b-32768` (large context)
- `gemma2-9b-it` (lightweight)

### Configuration File

All settings are saved to `~/.acat/config.json`:

```json
{
  "model": "gpt-4o-mini",
  "provider": "openai",
  "api_key": "sk-...",
  "api_endpoint": "https://api.openai.com/v1",
  "theme": "dark",
  "history_limit": 100
}
```

### Default Model

Default model is `gemma4:latest` with Ollama. Change with:

```bash
acat /model llama2
```

Or in config file `~/.acat/config.json`:

```json
{
  "model": "codellama"
}
```

## Tools

acat supports the following tools for AI-assisted tasks:

- `read_file` - Read file contents
- `write_file` - Write content to file
- `list_files` - List directory contents
- `search_files` - Search for files by pattern
- `run_command` - Execute shell commands
- `create_directory` - Create directories
- `file_exists` - Check if file/directory exists
- `scaffold_project` - Create project from template

## Project Context (ACAT.md)

Run `/init` to create an `ACAT.md` file in your project root. This file contains:

- Project overview and structure
- Technology stack detection
- Key files and directories
- Development setup instructions

Example:
```bash
cd my-project
acat /init
```

## Examples

### Analyze a project
```bash
acat /init
```

### Ask a question
```bash
acat "How do I add authentication to this Spring Boot app?"
```

### Scaffold a new project
```bash
acat "/scaffold react my-new-app"
cd my-new-app
npm install
npm start
```

### Change model
```bash
acat /model codellama:7b
```

## Troubleshooting

### Ollama not running
```bash
ollama serve
```

### Model not found
```bash
ollama pull gemma4:latest
```

### Permission denied (Linux/Mac)
```bash
chmod +x ~/.acat/bin/acat
```

### Windows execution policy
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## License

MIT
