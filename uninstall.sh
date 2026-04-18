#!/bin/bash
#
# acat - Uninstall Script
# Removes acat CLI completely (does NOT uninstall Ollama or models)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              acat CLI - Uninstall                         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

ACAT_DIR="${HOME}/.acat"
BIN_FILE="${HOME}/.local/bin/acat"

echo "This will remove:"
echo "  - $ACAT_DIR"
echo "  - $BIN_FILE"
echo ""
echo -e "${YELLOW}Note: Ollama and its models will NOT be uninstalled.${NC}"
echo ""

# Confirm uninstall
read -p "Continue uninstalling acat? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

removed=()

# Remove acat directory
if [ -d "$ACAT_DIR" ]; then
    rm -rf "$ACAT_DIR"
    removed+=("$ACAT_DIR")
    echo -e "${GREEN}✓ Removed $ACAT_DIR${NC}"
fi

# Remove bin wrapper
if [ -f "$BIN_FILE" ]; then
    rm -f "$BIN_FILE"
    removed+=("$BIN_FILE")
    echo -e "${GREEN}✓ Removed $BIN_FILE${NC}"
fi

# Optional: Clean PATH from shell profiles
if [[ "$1" == "--clean-path" ]]; then
    echo ""
    echo "Cleaning PATH entries from shell profiles..."

    for profile in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
        if [ -f "$profile" ]; then
            # Remove acat installer entries
            if grep -q "acat installer" "$profile" 2>/dev/null; then
                grep -v "acat installer" "$profile" > "$profile.tmp" && mv "$profile.tmp" "$profile"
                echo -e "${GREEN}✓ Cleaned $profile${NC}"
            fi
        fi
    done
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ Uninstallation Complete!                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Removed:"
for item in "${removed[@]}"; do
    echo "  - $item"
done

echo ""
echo "Note: Ollama and its models are NOT uninstalled."
echo "To remove Ollama separately, visit: https://ollama.ai"
