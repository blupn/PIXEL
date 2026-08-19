#!/usr/bin/env bash
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
setsid -f /usr/bin/python "$APP_DIR/main.py" >/dev/null 2>&1
