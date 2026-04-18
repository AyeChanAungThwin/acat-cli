#!/bin/bash
#
# acat - One-line installation script
# Usage: curl -fsSL https://.../install.sh -o install.sh && source install.sh
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${HOME}/.acat"
BIN_DIR="${HOME}/.local/bin"
GITHUB_REPO="https://github.com/AyeChanAungThwin/acat-cli"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              acat CLI - Installation                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check for Ollama
echo -e "${CYAN}[1/6] Checking Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}  Ollama is not installed.${NC}"
    echo -e "${CYAN}      Installing Ollama...${NC}"
    curl -fsSL https://ollama.ai/install.sh | bash
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}  ✓ Ollama installed${NC}"
    fi
else
    echo -e "${GREEN}  ✓ Ollama already installed${NC}"
fi
echo ""

# Step 2: Create directories
echo -e "${CYAN}[2/6] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$INSTALL_DIR/bin"
echo -e "${GREEN}  ✓ Created $INSTALL_DIR${NC}"
echo -e "${GREEN}  ✓ Created $BIN_DIR${NC}"
echo ""

# Step 3: Download acat files from GitHub
echo -e "${CYAN}[3/6] Downloading acat from GitHub...${NC}"
TEMP_DIR=$(mktemp -d)
if curl -fsSL "${GITHUB_REPO}/archive/refs/heads/main.tar.gz" -o "$TEMP_DIR/acat.tar.gz" 2>/dev/null; then
    tar -xzf "$TEMP_DIR/acat.tar.gz" -C "$TEMP_DIR"
    # Find the extracted directory
    EXTRACTED_DIR="$TEMP_DIR/acat-cli-main"
    if [ -f "$EXTRACTED_DIR/bin/acat" ] && [ -d "$EXTRACTED_DIR/src" ]; then
        # Remove old installation first to ensure clean override
        rm -rf "$INSTALL_DIR"/*
        cp -rf "$EXTRACTED_DIR"/* "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/bin/acat"
        echo -e "${GREEN}  ✓ Downloaded acat from GitHub${NC}"
        echo -e "${GREEN}  ✓ Copied acat source files${NC}"
        echo -e "${GREEN}  ✓ Made binaries executable${NC}"
    else
        echo -e "${RED}  ✗ Error: Invalid acat archive structure${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
else
    echo -e "${RED}  ✗ Error: Failed to download from GitHub${NC}"
    echo "  Trying local copy..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/bin/acat" ] && [ -d "$SCRIPT_DIR/src" ]; then
        cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/bin/acat"
        echo -e "${GREEN}  ✓ Copied from local source${NC}"
    else
        echo -e "${RED}  ✗ Error: acat source files not found${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
fi
rm -rf "$TEMP_DIR"
echo ""

# Step 4: Create wrapper script
echo -e "${CYAN}[4/6] Creating PATH wrapper...${NC}"
cat > "$BIN_DIR/acat" << 'WRAPPER'
#!/bin/bash
exec "$HOME/.acat/bin/acat" "$@"
WRAPPER
chmod +x "$BIN_DIR/acat"
echo -e "${GREEN}  ✓ Created $BIN_DIR/acat${NC}"
echo ""

# Step 5: Add to PATH in shell profile
echo -e "${CYAN}[5/6] Configuring PATH for global access...${NC}"

modify_profile() {
    local export_line="export PATH=\"\$HOME/.local/bin:\$PATH\""
    local modified=""

    # Add to .zshrc
    if [ -f "$HOME/.zshrc" ] && ! grep -q "\.local/bin" "$HOME/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME/.zshrc"
        echo "# Added by acat installer on $(date)" >> "$HOME/.zshrc"
        echo "$export_line" >> "$HOME/.zshrc"
        modified="$HOME/.zshrc"
        echo -e "${GREEN}  ✓ Added PATH entry to $HOME/.zshrc${NC}"
    fi

    # Add to .bashrc
    if [ -f "$HOME/.bashrc" ] && ! grep -q "\.local/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo "" >> "$HOME/.bashrc"
        echo "# Added by acat installer on $(date)" >> "$HOME/.bashrc"
        echo "$export_line" >> "$HOME/.bashrc"
        modified="$HOME/.bashrc"
        echo -e "${GREEN}  ✓ Added PATH entry to $HOME/.bashrc${NC}"
    fi

    # Add to .profile for login shells
    if [ -f "$HOME/.profile" ] && ! grep -q "\.local/bin" "$HOME/.profile" 2>/dev/null; then
        echo "" >> "$HOME/.profile"
        echo "# Added by acat installer on $(date)" >> "$HOME/.profile"
        echo "$export_line" >> "$HOME/.profile"
        echo -e "${GREEN}  ✓ Added PATH entry to $HOME/.profile${NC}"
    fi

    if [ -z "$modified" ]; then
        echo -e "${YELLOW}  ! PATH already configured in shell profile${NC}"
    fi
}

modify_profile
echo ""

# Step 6: Pull default model
echo -e "${CYAN}[6/6] Pulling default model (gemma4:latest)...${NC}"
ollama pull gemma4:latest 2>/dev/null && echo -e "${GREEN}  ✓ Model pulled successfully${NC}" || echo -e "${YELLOW}  ! Model pull failed. Run 'ollama pull gemma4:latest' later.${NC}"
echo ""

# Installation complete summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ Installation Complete!                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Installation Summary:${NC}"
echo "  • acat installed to: $INSTALL_DIR"
echo "  • Wrapper created at: $BIN_DIR/acat"
echo "  • PATH configured in: ~/.zshrc, ~/.bashrc, ~/.profile"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Run: source ~/.zshrc    (for zsh users)"
echo "     or   source ~/.bashrc   (for bash users)"
echo "  2. Then run: acat --version"
echo ""
echo -e "${CYAN}After sourcing, 'acat' will be available globally from anywhere!${NC}"
