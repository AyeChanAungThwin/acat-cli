#!/bin/bash
#
# Ollama integration script for acat
# This script enables: ollama launch acat
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACAT_BIN="$SCRIPT_DIR/bin/acat"

# Ollama expects launch scripts in ~/.ollama/launchers/
OLLAMA_LAUNCHERS_DIR="${HOME}/.ollama/launchers"

# Create launchers directory
mkdir -p "$OLLAMA_LAUNCHERS_DIR"

# Create symlink for ollama launch
ln -sf "$ACAT_BIN" "$OLLAMA_LAUNCHERS_DIR/acat"

# Also create a wrapper that ollama can call
cat > "$OLLAMA_LAUNCHERS_DIR/acat-launcher" << 'EOF'
#!/bin/bash
# Ollama launcher wrapper for acat
exec "$HOME/.acat/bin/acat" "$@"
EOF

chmod +x "$OLLAMA_LAUNCHERS_DIR/acat-launcher"

echo "✓ Ollama integration complete!"
echo ""
echo "You can now run:"
echo "  ollama launch acat"
echo ""
echo "Or with a specific model:"
echo "  ollama launch acat -m llama2"
