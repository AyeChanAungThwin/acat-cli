#!/bin/bash
#
# acat - Global installation (Linux/Mac)
# Installs to ~/.acat and adds to PATH automatically
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${HOME}/.acat"
BIN_DIR="${HOME}/.local/bin"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           acat CLI - Global Installation                  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create directories
echo -e "${GREEN}Creating installation directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy files
echo -e "${GREEN}Copying files to $INSTALL_DIR...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"

# Ensure bin directory exists and make binaries executable
mkdir -p "$INSTALL_DIR/bin"
if [ -f "$INSTALL_DIR/bin/acat" ]; then
    chmod +x "$INSTALL_DIR/bin/acat"
fi

# Create wrapper in ~/.local/bin
cat > "$BIN_DIR/acat" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.acat/bin/acat" "$@"
WRAPPER
chmod +x "$BIN_DIR/acat"

# Auto-add to PATH
add_to_path() {
    local export_line='export PATH="$HOME/.local/bin:$PATH"'
    local profile_added=""

    # Add to .zshrc
    if [ -f "$HOME/.zshrc" ] && ! grep -q "\.local/bin" "$HOME/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME/.zshrc"
        echo "# Added by acat installer on $(date)" >> "$HOME/.zshrc"
        echo "$export_line" >> "$HOME/.zshrc"
        profile_added="$HOME/.zshrc"
    fi

    # Add to .bashrc
    if [ -f "$HOME/.bashrc" ] && ! grep -q "\.local/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# Added by acat installer on $(date)" >> "$HOME/.bashrc"
        echo "$export_line" >> "$HOME/.bashrc"
        profile_added="$HOME/.bashrc"
    fi

    # Add to .profile
    if [ -f "$HOME/.profile" ] && ! grep -q "\.local/bin" "$HOME/.profile" 2>/dev/null; then
        echo "" >> "$HOME/.profile"
        echo "# Added by acat installer on $(date)" >> "$HOME/.profile"
        echo "$export_line" >> "$HOME/.profile"
    fi

    echo "$profile_added"
}

profile_file=$(add_to_path)
if [ -n "$profile_file" ]; then
    echo -e "${GREEN}✓ Added ~/.local/bin to PATH in $profile_file${NC}"
fi

# Export for current session
export PATH="$BIN_DIR:$PATH"

# Create default configuration
echo -e "${GREEN}Creating default configuration...${NC}"
CONFIG_FILE="$INSTALL_DIR/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'CONFIG'
{
    "model": "gemma4:latest",
    "provider": "ollama"
}
CONFIG
    echo -e "${GREEN}  Created config.json with default model: gemma4:latest${NC}"
else
    echo -e "${YELLOW}  config.json already exists, keeping existing configuration${NC}"
fi

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Ollama is not installed.${NC}"
    read -p "Install Ollama now? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://ollama.ai/install.sh | bash
    fi
fi

# Pull default model
echo ""
echo -e "${GREEN}Pulling default model (gemma4:latest)...${NC}"
if command -v ollama &> /dev/null; then
    ollama pull gemma4:latest 2>/dev/null || echo -e "${YELLOW}Model pull failed. Pull later with: ollama pull gemma4:latest${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ Installation Complete!                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Installation location: $INSTALL_DIR"
echo "Binary location: $BIN_DIR/acat"
echo "Default model: gemma4:latest"
echo ""
echo "To get started:"
if [ -n "$profile_file" ]; then
    echo "  • Restart terminal or run: source $profile_file"
else
    echo "  • PATH is already configured"
fi
echo "  • Run: acat"
echo ""
echo "PATH has been automatically configured in your shell profile."
echo "For help: acat /help"
