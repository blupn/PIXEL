#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"
AUTOSTART_DIR="$HOME/.config/autostart"

mkdir -p "$DESKTOP_DIR" "$ICON_DIR" "$AUTOSTART_DIR"
chmod +x "$APP_DIR/pixel-launch.sh" 2>/dev/null || true

sudo pacman -S --needed pyside6 python-requests playerctl

cp "$APP_DIR/assets/pixel-icon.png" "$ICON_DIR/pixel.png"

printf '%s\n' \
'[Desktop Entry]' \
'Version=1.0' \
'Type=Application' \
'Name=PIXEL' \
'Comment=8-bit masaüstü companion widget' \
"Exec=/usr/bin/python $APP_DIR/main.py" \
"Path=$APP_DIR" \
'Icon=pixel' \
'Terminal=false' \
'Categories=Utility;' \
'StartupNotify=false' \
> "$DESKTOP_DIR/pixel.desktop"

chmod +x "$DESKTOP_DIR/pixel.desktop"

if ! command -v dbus-monitor >/dev/null 2>&1; then
  echo "Not: dbus-monitor bulunamadı; bildirim tepkileri çalışmayabilir."
fi

read -r -p "PIXEL bilgisayar açılınca otomatik başlasın mı? [e/H]: " cevap
case "$cevap" in
  e|E|y|Y)
    cp "$DESKTOP_DIR/pixel.desktop" "$AUTOSTART_DIR/pixel.desktop"
    echo "Otomatik başlatma açıldı."
    ;;
  *)
    rm -f "$AUTOSTART_DIR/pixel.desktop"
    echo "Otomatik başlatma kapalı."
    ;;
esac

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
fi

echo
echo "PIXEL V11 kuruldu. KDE uygulama menüsünde PIXEL diye aratabilirsin."
