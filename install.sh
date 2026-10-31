#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/LowCoreLauncher"
ICON="$DIR/_internal/assets/logo.png"

# Fallback if logo is placed directly in assets
if [ ! -f "$ICON" ]; then
    ICON="$DIR/assets/logo.png"
fi

# Ensure launcher binary is executable
chmod +x "$BIN"

# Create application shortcut entry
mkdir -p "$HOME/.local/share/applications"
DESKTOP_FILE="$HOME/.local/share/applications/LowCoreLauncher.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=LowCore Launcher
Comment=Lightweight Custom Minecraft Launcher
Exec="$BIN"
Icon=$ICON
Terminal=false
Categories=Game;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

# Copy to Desktop folder if it exists
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/LowCoreLauncher.desktop"
    # Mark as trusted on GNOME / Ubuntu desktops
    gio set "$HOME/Desktop/LowCoreLauncher.desktop" metadata::trusted true 2>/dev/null || true
fi

# Update desktop database
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "=== LowCore Launcher Installed Successfully! ==="
echo "You can now open it from your Applications menu or Desktop."
