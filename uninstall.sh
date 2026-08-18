#!/usr/bin/env bash
set -e
rm -f "$HOME/.local/share/applications/pixel.desktop"
rm -f "$HOME/.local/share/icons/pixel.png"
rm -f "$HOME/.config/autostart/pixel.desktop"
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
fi
echo "PIXEL menü/autostart kayıtları kaldırıldı."
