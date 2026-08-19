#!/usr/bin/env python3
import json
import os
import random
import subprocess
import sys
import signal
import time
import urllib.parse
import urllib.request

import requests
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QEvent, QObject, Signal, QThread, QProcess
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QHBoxLayout, QInputDialog, QLabel, QMenu, QPushButton, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget, QSizePolicy, QCheckBox
)

APP_NAME = "PIXEL"
APP_VERSION = "11.0"
ROOT = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".config" / "pixel"
CONFIG_FILE = CONFIG_DIR / "config.json"
ASSET_PATH = ROOT / "assets" / "character.png"
SPRITE_PATH = ROOT / "assets" / "character-sprites.png"
SPRITE_MANIFEST_PATH = ROOT / "assets" / "sprites.json"
DESKTOP_FILE = Path.home() / ".local" / "share" / "applications" / "pixel.desktop"
AUTOSTART_FILE = Path.home() / ".config" / "autostart" / "pixel.desktop"

THEMES = {
    "KREM MAVİ": {"panel":"#efe9d5","accent":"#b8d8d5","box":"#f7f2dd","text":"#252925","danger":"#e3b3aa"},
    "PEMBE": {"panel":"#f4e4ea","accent":"#e8b7cb","box":"#faeef3","text":"#33272d","danger":"#e7a4a4"},
    "MOR": {"panel":"#ece5f4","accent":"#c9b7e8","box":"#f4eef9","text":"#2e2935","danger":"#e2a6b4"},
    "YEŞİL": {"panel":"#e8efe4","accent":"#b8d3ad","box":"#f2f6ef","text":"#293129","danger":"#e3aaa1"},
    "KARANLIK": {"panel":"#171a1f","accent":"#32424d","box":"#22272e","text":"#e7ecef","danger":"#7e4242"},
    "SAKURA": {"panel":"#f7e8ee","accent":"#efabc4","box":"#fff2f6","text":"#432f38","danger":"#de8996"},
    "TURUNCU": {"panel":"#f3e6d4","accent":"#e7b271","box":"#fbf0e0","text":"#362b20","danger":"#d68172"},
    "CYBER": {"panel":"#10151a","accent":"#4aa7a1","box":"#172126","text":"#d9f4ee","danger":"#a65361"},
}
DEFAULT_THEME = THEMES["KREM MAVİ"].copy()


def default_config():
    return {
        "note": "BUGÜN: GÜZEL BİR ŞEY YAP",
        "always_on_top": False,
        "width": 350,
        "height": 590,
        "weather_city": "İstanbul",
        "auto_location": True,
        "detected_location": "",
        "theme": DEFAULT_THEME.copy(),
        "theme_name": "KREM MAVİ",
        "notifications": True,
        "sleep_after": 75,
        "random_reactions": True,
    }


def load_config():
    data = default_config()
    try:
        if CONFIG_FILE.exists():
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            data.update(loaded)
            merged = DEFAULT_THEME.copy()
            merged.update(data.get("theme", {}))
            data["theme"] = merged
    except Exception:
        pass
    return data


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def app_font(size=11):
    families = {f.lower(): f for f in QFontDatabase.families()}
    for wanted in ("cozette", "cozettevector", "terminus", "monospace"):
        if wanted in families:
            font = QFont(families[wanted], size)
            font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
            return font
    font = QFont("Monospace", size)
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    return font


def run_playerctl(*args):
    try:
        return subprocess.run(["playerctl", *args], capture_output=True, text=True, timeout=0.9)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def player_metadata():
    status = run_playerctl("status")
    if status is None:
        return {"available": False, "playing": False, "title":"PLAYERCTL BULUNAMADI", "artist":"", "position":0.0, "length":0.0}
    if status.returncode != 0:
        return {"available": True, "playing": False, "title":"MÜZİK YOK", "artist":"", "position":0.0, "length":0.0}

    playing = status.stdout.strip().lower() == "playing"
    meta = run_playerctl("metadata", "--format", "{{title}}\n{{artist}}\n{{mpris:length}}")
    title, artist, length = "BİLİNMEYEN PARÇA", "", 0.0
    if meta and meta.returncode == 0:
        lines = meta.stdout.strip().splitlines()
        title = lines[0].strip() if lines else title
        artist = lines[1].strip() if len(lines) > 1 else ""
        try:
            length = float(lines[2].strip()) / 1_000_000 if len(lines) > 2 else 0.0
        except Exception:
            length = 0.0
    pos = run_playerctl("position")
    try:
        position = float(pos.stdout.strip()) if pos and pos.returncode == 0 else 0.0
    except Exception:
        position = 0.0
    return {"available": True, "playing": playing, "title": title, "artist": artist, "position": position, "length": length}


def fmt_time(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds//60:02d}:{seconds%60:02d}"


class Locate:
    """IP-based coarse location lookup used only when Auto Location is enabled.

    The IP address returned by the service is never stored in PIXEL's config.
    """

    @staticmethod
    def get_location():
        try:
            response = requests.get(
                "http://ip-api.com/json/",
                params={"fields": "status,message,country,city,lat,lon,query"},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "success":
                raise ValueError(data.get("message") or "location lookup failed")

            return {
                "country": data.get("country") or "Unknown_Country",
                "city": data.get("city") or "Unknown_City",
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "ip": data.get("query") or "0.0.0.0",
            }
        except (requests.RequestException, ValueError, TypeError):
            return {
                "country": "Unknown_Country",
                "city": "Unknown_City",
                "lat": None,
                "lon": None,
                "ip": "0.0.0.0",
            }


class WeatherWorker(QObject):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, city, auto_location=True):
        super().__init__()
        self.city = city
        self.auto_location = bool(auto_location)

    def run(self):
        try:
            location_label = self.city.strip() or "İstanbul"
            weather_target = location_label
            location_source = "manual"

            if self.auto_location:
                detected = Locate.get_location()
                lat = detected.get("lat")
                lon = detected.get("lon")
                city = detected.get("city")
                country = detected.get("country")

                if lat is not None and lon is not None:
                    # Coordinates avoid same-name city mismatches in wttr.in.
                    weather_target = f"{lat},{lon}"
                    location_label = ", ".join(
                        part for part in (city, country)
                        if part and not part.startswith("Unknown_")
                    ) or location_label
                    location_source = "auto"

            target = urllib.parse.quote(weather_target, safe=",")
            req = urllib.request.Request(
                f"https://wttr.in/{target}?format=j1",
                headers={"User-Agent": "PIXEL/11.0"},
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                # Limit the response size before JSON parsing.
                payload = response.read(1024 * 1024 + 1)
                if len(payload) > 1024 * 1024:
                    raise ValueError("weather response too large")
                data = json.loads(payload.decode("utf-8"))

            current = data["current_condition"][0]
            weather = data.get("weather", [{}])[0]
            self.done.emit({
                "temp": current.get("temp_C", "?"),
                "feels": current.get("FeelsLikeC", "?"),
                "desc": current.get("weatherDesc", [{"value":"BİLİNMİYOR"}])[0].get("value","BİLİNMİYOR"),
                "humidity": current.get("humidity", "?"),
                "wind": current.get("windspeedKmph", "?"),
                "max": weather.get("maxtempC", "?"),
                "min": weather.get("mintempC", "?"),
                "location": location_label,
                "location_source": location_source,
            })
        except Exception as exc:
            self.failed.emit(str(exc))


class SpriteCharacter(QWidget):
    animation_started = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sheet = QPixmap(str(SPRITE_PATH))
        self.manifest = json.loads(SPRITE_MANIFEST_PATH.read_text(encoding="utf-8")) if SPRITE_MANIFEST_PATH.exists() else {}
        self.animation = "idle"
        self.frame = 0
        self.loop = True
        self.override_until = 0.0
        self.music_playing = False
        self.sleeping = False
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(125)

    def info(self, name=None):
        return self.manifest.get("animations", {}).get(name or self.animation, {"row":0,"frames":1,"fps":4})

    def set_music(self, playing):
        self.music_playing = bool(playing)
        if playing and time.monotonic() >= self.override_until:
            self.set_animation("dance")
        elif not playing and self.animation == "dance":
            self.set_animation("idle")

    def set_sleeping(self, sleeping):
        self.sleeping = bool(sleeping)
        if time.monotonic() < self.override_until:
            return
        if sleeping and not self.music_playing:
            self.set_animation("sleep")
        elif self.animation == "sleep":
            self.set_animation("dance" if self.music_playing else "idle")

    def react(self, name, seconds=1.5):
        self.override_until = time.monotonic() + seconds
        self.set_animation(name, force=True)
        self.animation_started.emit(name)

    def set_animation(self, name, force=False):
        if name not in self.manifest.get("animations", {}):
            return
        if not force and time.monotonic() < self.override_until:
            return
        if self.animation != name:
            self.animation = name
            self.frame = 0
            info = self.info(name)
            fps = max(1, int(info.get("fps", 4)))
            self.timer.setInterval(max(35, int(1000/fps)))
            self.update()

    def advance(self):
        if time.monotonic() >= self.override_until and self.animation in ("notify", "walk", "wave"):
            self.set_animation("dance" if self.music_playing else ("sleep" if self.sleeping else "idle"), force=True)
        info = self.info()
        self.frame = (self.frame + 1) % max(1, int(info.get("frames",1)))
        self.update()

    def paintEvent(self, event):
        if self.sheet.isNull():
            return
        info = self.info()
        cw, ch = int(self.manifest.get("cell_width",192)), int(self.manifest.get("cell_height",288))
        row = int(info.get("row",0))
        col = self.frame % max(1, int(info.get("frames",1)))
        frame = self.sheet.copy(col*cw, row*ch, cw, ch)
        target = frame.scaled(max(80,self.width()-8), max(100,self.height()-8), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap((self.width()-target.width())//2, (self.height()-target.height())//2, target)


class NotificationWatcher(QObject):
    notification = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._read)
        self.last_trigger = 0.0
    def start(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.process.start("dbus-monitor", ["--session", "interface='org.freedesktop.Notifications',member='Notify'"])
    def stop(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill(); self.process.waitForFinished(300)
    def _read(self):
        text = bytes(self.process.readAllStandardOutput()).decode(errors="ignore") + bytes(self.process.readAllStandardError()).decode(errors="ignore")
        now = time.monotonic()
        if ("member=Notify" in text or "Notify" in text) and now-self.last_trigger > 1.0:
            self.last_trigger = now
            self.notification.emit()


class SystemDragFrame(QFrame):
    drag_started = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit()
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove(); event.accept(); return
        super().mousePressEvent(event)


class ResizeHandle(QLabel):
    def __init__(self, parent=None):
        super().__init__("◢", parent)
        self.setObjectName("resizeHandle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(28,28)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("BOYUTLANDIR")
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge); event.accept(); return
        super().mousePressEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("PIXEL AYARLARI")
        self.setMinimumWidth(360)
        outer = QVBoxLayout(self)
        form = QFormLayout()

        self.city = QInputDialog  # placeholder to keep imports minimal
        from PySide6.QtWidgets import QLineEdit
        self.city_edit = QLineEdit(config.get("weather_city","İstanbul"))
        form.addRow("Hava durumu şehri:", self.city_edit)

        self.auto_location = QCheckBox("IP konumundan otomatik bul")
        self.auto_location.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_location.setChecked(bool(config.get("auto_location", True)))
        self.auto_location.setToolTip("Açıksa yaklaşık şehir IP konumundan bulunur. VPN kullanıyorsan kapatabilirsin.")
        self.city_edit.setEnabled(not self.auto_location.isChecked())
        self.auto_location.toggled.connect(lambda checked: self.city_edit.setEnabled(not checked))
        form.addRow("Otomatik konum:", self.auto_location)

        self.theme = QComboBox()
        self.theme.addItems(list(THEMES.keys()))
        current = config.get("theme_name","KREM MAVİ")
        if current in THEMES:
            self.theme.setCurrentText(current)
        form.addRow("Hazır tema:", self.theme)

        self.sleep = QSpinBox(); self.sleep.setRange(15, 600); self.sleep.setSuffix(" sn")
        self.sleep.setValue(int(config.get("sleep_after",75)))
        form.addRow("Uykuya geçiş:", self.sleep)

        self.notifications = QCheckBox("Masaüstü bildirimlerine tepki ver")
        self.notifications.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notifications.setChecked(bool(config.get("notifications",True)))
        form.addRow("Bildirim tepkisi:", self.notifications)

        self.random_reactions = QCheckBox("Arada kendi kendine hareket et")
        self.random_reactions.setCursor(Qt.CursorShape.PointingHandCursor)
        self.random_reactions.setChecked(bool(config.get("random_reactions",True)))
        form.addRow("Tatlı tepkiler:", self.random_reactions)

        self.always_top = QCheckBox("Her zaman üstte")
        self.always_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.always_top.setChecked(bool(config.get("always_on_top",False)))
        form.addRow("Pencere:", self.always_top)

        self.autostart = QCheckBox("Oturum açılınca PIXEL'i başlat")
        self.autostart.setChecked(AUTOSTART_FILE.exists())
        form.addRow("Otomatik başlat:", self.autostart)

        self.notifications.setToolTip("Tıklayarak açıp kapatabilirsin")
        self.random_reactions.setToolTip("Tıklayarak açıp kapatabilirsin")
        self.always_top.setToolTip("Tıklayarak açıp kapatabilirsin")
        self.autostart.setToolTip("Tıklayarak açıp kapatabilirsin")

        outer.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def values(self):
        return {
            "weather_city": self.city_edit.text().strip() or "İstanbul",
            "auto_location": self.auto_location.isChecked(),
            "theme_name": self.theme.currentText(),
            "sleep_after": self.sleep.value(),
            "notifications": self.notifications.isChecked(),
            "random_reactions": self.random_reactions.isChecked(),
            "always_on_top": self.always_top.isChecked(),
            "autostart": self.autostart.isChecked(),
        }


class Pixel(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.weather_thread = None
        self.weather_worker = None
        self.last_activity = time.monotonic()
        self.user_seeking = False

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(270, 420)
        self.apply_window_flags()
        self.setFont(app_font(11))
        self.build_ui()
        self.apply_style()

        self.resize(max(270,int(self.config.get("width",350))), max(420,int(self.config.get("height",590))))

        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self.update_clock); self.clock_timer.start(1000)
        self.music_timer = QTimer(self); self.music_timer.timeout.connect(self.update_music); self.music_timer.start(1000)
        self.weather_timer = QTimer(self); self.weather_timer.timeout.connect(self.refresh_weather); self.weather_timer.start(15*60*1000)
        self.behavior_timer = QTimer(self); self.behavior_timer.timeout.connect(self.update_character_state); self.behavior_timer.start(1000)
        self.random_timer = QTimer(self); self.random_timer.timeout.connect(self.random_reaction); self.random_timer.start(35000)

        self.notification_watcher = NotificationWatcher(self)
        self.notification_watcher.notification.connect(self.on_notification)
        self.configure_notification_watcher()

        self.installEventFilter(self)
        self.update_clock(); self.update_music(); QTimer.singleShot(300, self.refresh_weather)

    def apply_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get("always_on_top"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(8,8,8,8)
        self.panel = QFrame(); self.panel.setObjectName("panel"); outer.addWidget(self.panel)
        panel_layout = QVBoxLayout(self.panel); panel_layout.setContentsMargins(10,9,10,8); panel_layout.setSpacing(6)

        self.titlebar = SystemDragFrame(); self.titlebar.setObjectName("titlebar"); self.titlebar.drag_started.connect(lambda: self.character.react("walk",1.2) if hasattr(self,"character") else None)
        title = QHBoxLayout(self.titlebar); title.setContentsMargins(7,2,4,2)
        brand = QLabel("■ PIXEL"); brand.setObjectName("brand"); brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True); title.addWidget(brand); title.addStretch()
        settings_btn = QPushButton("⚙"); settings_btn.setObjectName("windowButton"); settings_btn.setFixedSize(27,24); settings_btn.setToolTip("AYARLAR"); settings_btn.clicked.connect(self.open_settings); title.addWidget(settings_btn)
        min_btn = QPushButton("_"); min_btn.setObjectName("windowButton"); min_btn.setFixedSize(27,24); min_btn.clicked.connect(self.showMinimized); title.addWidget(min_btn)
        close_btn = QPushButton("X"); close_btn.setObjectName("closeButton"); close_btn.setFixedSize(27,24); close_btn.clicked.connect(self.close); title.addWidget(close_btn)
        panel_layout.addWidget(self.titlebar)

        self.scroll = QScrollArea(); self.scroll.setObjectName("scroll"); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(); content.setObjectName("scrollContent"); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(2,2,6,2); content_layout.setSpacing(7)

        time_box = QFrame(); time_box.setObjectName("box"); tl = QVBoxLayout(time_box); tl.setContentsMargins(8,6,8,6)
        self.clock = QLabel("00:00"); self.clock.setObjectName("clock"); self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter); tl.addWidget(self.clock)
        self.full_date = QLabel(); self.full_date.setObjectName("dateLarge"); self.full_date.setAlignment(Qt.AlignmentFlag.AlignCenter); self.full_date.setWordWrap(True); tl.addWidget(self.full_date); content_layout.addWidget(time_box)

        weather_box = QFrame(); weather_box.setObjectName("box"); wl = QVBoxLayout(weather_box); wl.setContentsMargins(8,6,8,6)
        wh = QHBoxLayout(); wt = QLabel("☁ HAVA DURUMU"); wt.setObjectName("section"); wh.addWidget(wt); wh.addStretch(); self.weather_city=QLabel(("OTOMATİK" if self.config.get("auto_location", True) else self.config["weather_city"]).upper()); self.weather_city.setObjectName("tiny"); wh.addWidget(self.weather_city); wl.addLayout(wh)
        self.weather_main=QLabel("YÜKLENİYOR..."); self.weather_main.setObjectName("weatherMain"); wl.addWidget(self.weather_main)
        self.weather_detail=QLabel("HAVA DURUMU ALINIYOR"); self.weather_detail.setObjectName("tiny"); self.weather_detail.setWordWrap(True); wl.addWidget(self.weather_detail); content_layout.addWidget(weather_box)

        self.character = SpriteCharacter(); self.character.installEventFilter(self); self.character.setCursor(Qt.CursorShape.OpenHandCursor); content_layout.addWidget(self.character)

        music_box = QFrame(); music_box.setObjectName("box"); ml=QVBoxLayout(music_box); ml.setContentsMargins(8,6,8,6)
        mt=QLabel("♪ MÜZİK"); mt.setObjectName("section"); ml.addWidget(mt)
        self.track=QLabel("MÜZİK YOK"); self.track.setObjectName("track"); self.track.setWordWrap(True); ml.addWidget(self.track)
        controls=QHBoxLayout();
        self.prev_btn=QPushButton("|<"); self.play_btn=QPushButton(">"); self.next_btn=QPushButton(">|")
        for b in (self.prev_btn,self.play_btn,self.next_btn): b.setObjectName("musicButton"); b.setFixedHeight(28); controls.addWidget(b)
        self.prev_btn.clicked.connect(lambda: self.music_command("previous")); self.play_btn.clicked.connect(lambda: self.music_command("play-pause")); self.next_btn.clicked.connect(lambda: self.music_command("next")); ml.addLayout(controls)
        progress_row=QHBoxLayout(); self.pos_label=QLabel("00:00"); self.pos_label.setObjectName("tiny"); progress_row.addWidget(self.pos_label)
        self.progress=QSlider(Qt.Orientation.Horizontal); self.progress.setRange(0,1000); self.progress.sliderPressed.connect(lambda: setattr(self,"user_seeking",True)); self.progress.sliderReleased.connect(self.seek_music); progress_row.addWidget(self.progress,1)
        self.len_label=QLabel("00:00"); self.len_label.setObjectName("tiny"); progress_row.addWidget(self.len_label); ml.addLayout(progress_row); content_layout.addWidget(music_box)

        quest_box=QFrame(); quest_box.setObjectName("box"); ql=QVBoxLayout(quest_box); ql.setContentsMargins(8,6,8,6)
        qt=QLabel("> MİNİ GÖREV"); qt.setObjectName("section"); ql.addWidget(qt); self.note=QLabel(self.config["note"]); self.note.setWordWrap(True); self.note.setObjectName("note"); ql.addWidget(self.note); content_layout.addWidget(quest_box)

        footer=QLabel("TEKERLEK = KAYDIR • SAĞ TIK = MENÜ"); footer.setObjectName("tiny"); footer.setAlignment(Qt.AlignmentFlag.AlignCenter); content_layout.addWidget(footer)
        self.scroll.setWidget(content); panel_layout.addWidget(self.scroll,1)
        bottom=QHBoxLayout(); hint=QLabel("ÜSTTEN/KARAKTERDEN SÜRÜKLE"); hint.setObjectName("tiny"); bottom.addWidget(hint); bottom.addStretch(); self.resize_handle=ResizeHandle(); bottom.addWidget(self.resize_handle); panel_layout.addLayout(bottom)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress, QEvent.Type.Wheel):
            self.last_activity = time.monotonic(); self.character.set_sleeping(False) if hasattr(self,"character") else None
        if obj is self.character and event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
            self.character.react("walk",1.4)
            handle=self.windowHandle()
            if handle is not None:
                handle.startSystemMove(); return True
        return super().eventFilter(obj,event)

    def apply_style(self):
        t=self.config["theme"]
        self.setStyleSheet(f"""
        #panel {{ background:{t['panel']}; border:3px solid {t['text']}; }}
        #titlebar {{ background:{t['accent']}; border:2px solid {t['text']}; }}
        #scroll,#scrollContent {{ background:transparent; border:none; }}
        QScrollBar:vertical {{ background:{t['panel']}; width:12px; border:2px solid {t['text']}; }}
        QScrollBar::handle:vertical {{ background:{t['accent']}; min-height:28px; border:1px solid {t['text']}; }}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0px; }}
        #box {{ background:{t['box']}; border:2px solid {t['text']}; }}
        QLabel {{ color:{t['text']}; background:transparent; }}
        #brand {{ font-size:12px; font-weight:700; }} #clock {{ font-size:29px; font-weight:700; }}
        #dateLarge {{ font-size:11px; font-weight:700; }} #weatherMain {{ font-size:17px; font-weight:700; padding:3px 0; }}
        #section {{ font-size:11px; font-weight:700; }} #track,#note {{ font-size:11px; }} #tiny {{ font-size:9px; }}
        #windowButton,#closeButton,#musicButton {{ background:{t['panel']}; color:{t['text']}; border:2px solid {t['text']}; font-weight:700; }}
        #windowButton:hover,#musicButton:hover {{ background:{t['accent']}; }} #closeButton:hover {{ background:{t['danger']}; }}
        #resizeHandle {{ background:{t['accent']}; color:{t['text']}; border:2px solid {t['text']}; font-size:14px; font-weight:700; }}
        QMenu {{ background:{t['panel']}; color:{t['text']}; border:2px solid {t['text']}; }} QMenu::item:selected {{ background:{t['accent']}; }}
        QDialog {{ background:{t['panel']}; color:{t['text']}; }}
        QDialog QLabel,QDialog QCheckBox {{ color:{t['text']}; }}
        QCheckBox {{
            spacing: 8px;
            padding: 4px 2px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {t['text']};
            background: {t['box']};
        }}
        QCheckBox::indicator:hover {{
            background: {t['panel']};
            border: 2px solid {t['accent']};
        }}
        QCheckBox::indicator:checked {{
            background: {t['accent']};
            border: 4px solid {t['text']};
        }}
        QComboBox,QSpinBox,QLineEdit {{ background:{t['box']}; color:{t['text']}; border:2px solid {t['text']}; padding:4px; }}
        QSlider::groove:horizontal {{ height:6px; background:{t['panel']}; border:1px solid {t['text']}; }}
        QSlider::handle:horizontal {{ width:12px; margin:-4px 0; background:{t['accent']}; border:1px solid {t['text']}; }}
        """)

    def update_clock(self):
        from PySide6.QtCore import QDateTime
        now=QDateTime.currentDateTime(); self.clock.setText(now.toString("HH:mm"))
        days=["PAZARTESİ","SALI","ÇARŞAMBA","PERŞEMBE","CUMA","CUMARTESİ","PAZAR"]
        months=["OCAK","ŞUBAT","MART","NİSAN","MAYIS","HAZİRAN","TEMMUZ","AĞUSTOS","EYLÜL","EKİM","KASIM","ARALIK"]
        d=now.date(); self.full_date.setText(f"{days[d.dayOfWeek()-1]} • {d.day():02d} {months[d.month()-1]} {d.year()}")

    def update_music(self):
        meta=player_metadata(); self.character.set_music(meta["playing"])
        text=meta["title"] if not meta["artist"] else f"{meta['title']} - {meta['artist']}"; self.track.setText(text.upper())
        self.play_btn.setText("||" if meta["playing"] else ">")
        if not self.user_seeking:
            length=max(0.0,meta["length"]); pos=max(0.0,min(meta["position"],length if length else meta["position"]))
            self.progress.setValue(int((pos/length)*1000) if length>0 else 0); self.pos_label.setText(fmt_time(pos)); self.len_label.setText(fmt_time(length))

    def music_command(self, command):
        run_playerctl(command); self.last_activity=time.monotonic(); QTimer.singleShot(150,self.update_music)

    def seek_music(self):
        meta=player_metadata(); length=meta["length"]
        if length>0:
            target=(self.progress.value()/1000)*length; run_playerctl("position",str(target))
        self.user_seeking=False; self.update_music()

    def update_character_state(self):
        idle_for=time.monotonic()-self.last_activity
        self.character.set_sleeping(idle_for >= int(self.config.get("sleep_after",75)))

    def random_reaction(self):
        if self.config.get("random_reactions",True) and not self.character.music_playing and not self.character.sleeping and random.random() < 0.75:
            self.character.react("wave",1.5)
        self.random_timer.setInterval(random.randint(30000,65000))

    def on_notification(self):
        if self.config.get("notifications",True):
            self.last_activity=time.monotonic(); self.character.react("notify",1.4)

    def configure_notification_watcher(self):
        if self.config.get("notifications",True): self.notification_watcher.start()
        else: self.notification_watcher.stop()

    def refresh_weather(self):
        if self.weather_thread and self.weather_thread.isRunning(): return
        self.weather_main.setText("YÜKLENİYOR..."); self.weather_detail.setText("HAVA DURUMU GÜNCELLENİYOR")
        self.weather_thread=QThread(self); self.weather_worker=WeatherWorker(self.config["weather_city"], self.config.get("auto_location", True)); self.weather_worker.moveToThread(self.weather_thread)
        self.weather_thread.started.connect(self.weather_worker.run); self.weather_worker.done.connect(self.weather_loaded); self.weather_worker.failed.connect(self.weather_failed)
        self.weather_worker.done.connect(self.weather_thread.quit); self.weather_worker.failed.connect(self.weather_thread.quit); self.weather_worker.done.connect(self.weather_worker.deleteLater); self.weather_worker.failed.connect(self.weather_worker.deleteLater); self.weather_thread.finished.connect(self.weather_thread.deleteLater); self.weather_thread.start()

    def weather_loaded(self,data):
        location = (data.get("location") or self.config.get("weather_city") or "İstanbul").strip()
        self.weather_city.setText(location.upper())
        if data.get("location_source") == "auto":
            self.config["detected_location"] = location
            save_config(self.config)
        self.weather_main.setText(f"{data['temp']}°C • {data['desc'].upper()}")
        self.weather_detail.setText(f"HİSSEDİLEN {data['feels']}°C | EN YÜKSEK {data['max']}° EN DÜŞÜK {data['min']}°\nNEM %{data['humidity']} | RÜZGAR {data['wind']} KM/S")
    def weather_failed(self,error):
        self.weather_main.setText("HAVA DURUMU ÇEVRİMDIŞI"); self.weather_detail.setText("SAĞ TIK > HAVA DURUMUNU YENİLE")

    def change_city(self):
        city,ok=QInputDialog.getText(self,"HAVA DURUMU ŞEHRİ","ŞEHİR:",text=self.config["weather_city"])
        if ok and city.strip():
            self.config["weather_city"] = city.strip()
            self.config["auto_location"] = False
            save_config(self.config)
            self.weather_city.setText(city.strip().upper())
            self.refresh_weather()
    def edit_note(self):
        text, ok = QInputDialog.getMultiLineText(
            self,
            "MİNİ GÖREV",
            "GÖREVİN NE?",
            self.note.text(),
        )
        if ok and text.strip():
            text = text.strip().upper()
            self.note.setText(text)
            self.config["note"] = text
            save_config(self.config)

    def apply_theme_preset(self,name):
        if name not in THEMES: return
        self.config["theme_name"]=name; self.config["theme"]=THEMES[name].copy(); save_config(self.config); self.apply_style()
    def choose_color(self,key,title):
        color=QColorDialog.getColor(QColor(self.config["theme"][key]),self,title)
        if color.isValid(): self.config["theme"][key]=color.name(); self.config["theme_name"]="ÖZEL"; save_config(self.config); self.apply_style()
    def reset_theme(self):
        self.apply_theme_preset("KREM MAVİ")

    def set_autostart(self,enabled):
        try:
            AUTOSTART_FILE.parent.mkdir(parents=True,exist_ok=True)
            if enabled:
                if DESKTOP_FILE.exists():
                    AUTOSTART_FILE.write_text(DESKTOP_FILE.read_text(encoding="utf-8"),encoding="utf-8")
                else:
                    AUTOSTART_FILE.write_text(f"[Desktop Entry]\nType=Application\nName=PIXEL\nExec={sys.executable} {ROOT/'main.py'}\nPath={ROOT}\nTerminal=false\n",encoding="utf-8")
            elif AUTOSTART_FILE.exists(): AUTOSTART_FILE.unlink()
        except Exception: pass

    def open_settings(self):
        dlg=SettingsDialog(self.config,self); dlg.setStyleSheet(self.styleSheet())
        if dlg.exec()!=QDialog.DialogCode.Accepted: return
        v=dlg.values(); old_top=self.config.get("always_on_top",False); old_city=self.config.get("weather_city"); old_auto=self.config.get("auto_location",True)
        self.config.update({k:v[k] for k in ("weather_city","auto_location","sleep_after","notifications","random_reactions","always_on_top")})
        self.set_autostart(v["autostart"]); self.apply_theme_preset(v["theme_name"]); save_config(self.config)
        self.weather_city.setText(("OTOMATİK" if self.config.get("auto_location",True) else self.config["weather_city"]).upper()); self.configure_notification_watcher()
        if self.config["weather_city"] != old_city or self.config.get("auto_location",True) != old_auto: self.refresh_weather()
        if self.config["always_on_top"] != old_top:
            size=self.size(); self.apply_window_flags(); self.show(); self.resize(size)

    def contextMenuEvent(self,event):
        menu=QMenu(self)
        settings=QAction("AYARLAR",self); settings.triggered.connect(self.open_settings); menu.addAction(settings)
        menu.addSeparator()
        city=QAction("HAVA DURUMU ŞEHRİNİ DEĞİŞTİR",self); city.triggered.connect(self.change_city); menu.addAction(city)
        refresh=QAction("HAVA DURUMUNU YENİLE",self); refresh.triggered.connect(self.refresh_weather); menu.addAction(refresh)
        edit=QAction("MİNİ GÖREVİ DÜZENLE",self); edit.triggered.connect(self.edit_note); menu.addAction(edit)
        themes=menu.addMenu("HAZIR TEMALAR")
        for name in THEMES:
            a=QAction(name,self); a.setCheckable(True); a.setChecked(self.config.get("theme_name")==name); a.triggered.connect(lambda checked=False,n=name:self.apply_theme_preset(n)); themes.addAction(a)
        colors=menu.addMenu("RENKLER")
        for label,key in (("VURGU RENGİ","accent"),("ARKA PLAN RENGİ","panel"),("KART RENGİ","box"),("YAZI / ÇERÇEVE RENGİ","text")):
            a=QAction(label,self); a.triggered.connect(lambda checked=False,k=key,l=label:self.choose_color(k,l)); colors.addAction(a)
        colors.addSeparator(); r=QAction("VARSAYILAN RENKLERE DÖN",self); r.triggered.connect(self.reset_theme); colors.addAction(r)
        menu.addSeparator(); close=QAction("PIXEL'İ KAPAT",self); close.triggered.connect(self.close); menu.addAction(close); menu.exec(event.globalPos())

    def resizeEvent(self,event):
        if hasattr(self,"config"): self.config["width"]=self.width(); self.config["height"]=self.height(); save_config(self.config)
        super().resizeEvent(event)
    def closeEvent(self,event):
        self.notification_watcher.stop(); self.config["width"]=self.width(); self.config["height"]=self.height(); save_config(self.config); super().closeEvent(event)


def main():
    # Linux'ta terminal kapansa bile PIXEL açık kalsın.
    if sys.platform.startswith("linux") and hasattr(signal, "SIGHUP"):
        try:
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
        except Exception:
            pass

    app=QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    widget=Pixel()
    widget.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
