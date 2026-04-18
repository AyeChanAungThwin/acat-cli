#!/bin/bash
#
# acat - Local installation (current directory)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing acat locally in: $SCRIPT_DIR"

# Make binary executable
chmod +x "$SCRIPT_DIR/bin/acat"

# Create symlink
ln -sf "$SCRIPT_DIR/bin/acat" "$SCRIPT_DIR/acat"

# Ask if user wants to add to PATH
echo ""
read -p "Add acat to your PATH automatically? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    export_line="export PATH=\"$SCRIPT_DIR:\$PATH\""

    # Detect shell and add to appropriate profile
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "acat" "$HOME/.zshrc" 2>/dev/null; then
            echo "" >> "$HOME/.zshrc"
            echo "# Added by acat installer on $(date)" >> "$HOME/.zshrc"
            echo "$export_line" >> "$HOME/.zshrc"
            echo -e "✓ Added to \033[0;32m$HOME/.zshrc\033[0m"
        fi
    fi

    if [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "acat" "$HOME/.bashrc" 2>/dev/null; then
            echo "" >> "$HOME/.bashrc"
            echo "# Added by acat installer on $(date)" >> "$HOME/.bashrc"
            echo "$export_line" >> "$HOME/.bashrc"
            echo -e "✓ Added to \033[0;32m$HOME/.bashrc\033[0m"
        fi
    fi

    # Export for current session
    export PATH="$SCRIPT_DIR:$PATH"
    echo ""
    echo "  Restart your terminal or run: source ~/.zshrc (or ~/.bashrc)"
fi

echo ""
echo "✓ Local installation complete!"
echo ""
echo "Run with: ./acat"
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Or add alias to your shell:"
    echo "  alias acat='$SCRIPT_DIR/acat'"
fi
