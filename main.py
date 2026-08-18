#!/usr/bin/env python3
import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QEvent, QObject, Signal, QThread
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMenu,
    QPushButton, QScrollArea, QVBoxLayout, QWidget, QSizePolicy
)

APP_NAME = "PIXEL"
CONFIG_DIR = Path.home() / ".config" / "pixel"
CONFIG_FILE = CONFIG_DIR / "config.json"
ASSET_PATH = Path(__file__).resolve().parent / "assets" / "character.png"

THEMES = {
    "KREM MAVİ": {
        "panel": "#efe9d5",
        "accent": "#b8d8d5",
        "box": "#f7f2dd",
        "text": "#252925",
        "danger": "#e3b3aa",
    },
    "PEMBE": {
        "panel": "#f4e4ea",
        "accent": "#e8b7cb",
        "box": "#faeef3",
        "text": "#33272d",
        "danger": "#e7a4a4",
    },
    "MOR": {
        "panel": "#ece5f4",
        "accent": "#c9b7e8",
        "box": "#f4eef9",
        "text": "#2e2935",
        "danger": "#e2a6b4",
    },
    "YEŞİL": {
        "panel": "#e8efe4",
        "accent": "#b8d3ad",
        "box": "#f2f6ef",
        "text": "#293129",
        "danger": "#e3aaa1",
    },
    "KARANLIK": {
        "panel": "#171a1f",
        "accent": "#32424d",
        "box": "#22272e",
        "text": "#e7ecef",
        "danger": "#7e4242",
    },
}
DEFAULT_THEME = THEMES["KREM MAVİ"].copy()


def load_config():
    data = {
        "note": "BUGÜN: GÜZEL BİR ŞEY YAP",
        "always_on_top": False,
        "width": 330,
        "height": 560,
        "weather_city": "İstanbul",
        "theme": DEFAULT_THEME.copy(),
        "theme_name": "KREM MAVİ",
    }
    try:
        if CONFIG_FILE.exists():
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            data.update(loaded)
            merged_theme = DEFAULT_THEME.copy()
            merged_theme.update(data.get("theme", {}))
            data["theme"] = merged_theme
    except Exception:
        pass
    return data


def save_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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


def playerctl_metadata():
    try:
        status = subprocess.run(
            ["playerctl", "status"],
            capture_output=True, text=True, timeout=0.8,
        )
        playing = status.returncode == 0 and status.stdout.strip().lower() == "playing"

        meta = subprocess.run(
            ["playerctl", "metadata", "--format", "{{title}}\n{{artist}}"],
            capture_output=True, text=True, timeout=0.8,
        )
        if meta.returncode != 0:
            return False, "MÜZİK YOK", ""

        lines = meta.stdout.strip().splitlines()
        title = lines[0].strip() if lines else "BİLİNMEYEN PARÇA"
        artist = lines[1].strip() if len(lines) > 1 else ""
        return playing, title or "BİLİNMEYEN PARÇA", artist
    except (FileNotFoundError, subprocess.SubprocessError):
        return False, "PLAYERCTL BULUNAMADI", ""


class WeatherWorker(QObject):
    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, city):
        super().__init__()
        self.city = city

    def run(self):
        try:
            city = urllib.parse.quote(self.city.strip())
            url = f"https://wttr.in/{city}?format=j1"
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "PIXEL/1.0"}
            )
            with urllib.request.urlopen(request, timeout=7) as response:
                data = json.loads(response.read().decode("utf-8"))

            current = data["current_condition"][0]
            weather = data.get("weather", [{}])[0]
            result = {
                "temp": current.get("temp_C", "?"),
                "feels": current.get("FeelsLikeC", "?"),
                "desc": current.get("weatherDesc", [{"value": "BİLİNMİYOR"}])[0].get("value", "BİLİNMİYOR"),
                "humidity": current.get("humidity", "?"),
                "wind": current.get("windspeedKmph", "?"),
                "max": weather.get("maxtempC", "?"),
                "min": weather.get("mintempC", "?"),
            }
            self.done.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PixelCharacter(QWidget):
    """
    Pixel-snapped multi-frame animation using the original character art.
    The frames are intentionally discrete rather than continuously interpolated,
    so movement feels closer to classic sprite animation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap(str(ASSET_PATH))
        self.dancing = False
        self.started = time.monotonic()
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(90)  # discrete ~11 FPS sprite-like cadence

    def set_dancing(self, value):
        self.dancing = bool(value)

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return

        t = time.monotonic() - self.started
        frame = int(t * (8 if self.dancing else 4))

        # Pixel-snapped keyframes.
        if self.dancing:
            dance = [
                (0, 0, -2.0),
                (2, -2, 0.0),
                (4, 0, 2.0),
                (2, 2, 0.0),
                (0, 0, -2.0),
                (-2, -2, 0.0),
                (-4, 0, 2.0),
                (-2, 2, 0.0),
            ]
            dx, dy, angle = dance[frame % len(dance)]
        else:
            idle = [
                (0, 0, 0.0),
                (0, -1, 0.0),
                (0, -2, 0.0),
                (0, -1, 0.0),
            ]
            dx, dy, angle = idle[frame % len(idle)]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        aw = max(80, self.width() - 8)
        ah = max(100, self.height() - 8)
        ratio = self.pixmap.width() / self.pixmap.height()

        h = ah
        w = int(h * ratio)
        if w > aw:
            w = aw
            h = int(w / ratio)

        scaled = self.pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        painter.save()
        painter.translate(self.width() / 2 + dx, self.height() / 2 + dy)
        painter.rotate(angle)
        painter.translate(-scaled.width() / 2, -scaled.height() / 2)
        painter.drawPixmap(0, 0, scaled)
        painter.restore()


class SystemDragFrame(QFrame):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)


class ResizeHandle(QLabel):
    def __init__(self, parent=None):
        super().__init__("◢", parent)
        self.setObjectName("resizeHandle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("BOYUTLANDIR")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemResize(Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
                event.accept()
                return
        super().mousePressEvent(event)


class Pixel(QWidget):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.weather_thread = None
        self.weather_worker = None

        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(250, 390)

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get("always_on_top"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setFont(app_font(11))
        self.build_ui()
        self.apply_style()

        self.resize(
            max(250, int(self.config.get("width", 330))),
            max(390, int(self.config.get("height", 560))),
        )

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.music_timer = QTimer(self)
        self.music_timer.timeout.connect(self.update_music)
        self.music_timer.start(1800)

        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(15 * 60 * 1000)

        self.update_clock()
        self.update_music()
        QTimer.singleShot(300, self.refresh_weather)

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        self.panel = QFrame()
        self.panel.setObjectName("panel")
        outer.addWidget(self.panel)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(10, 9, 10, 8)
        panel_layout.setSpacing(6)

        self.titlebar = SystemDragFrame()
        self.titlebar.setObjectName("titlebar")
        title_layout = QHBoxLayout(self.titlebar)
        title_layout.setContentsMargins(7, 2, 4, 2)

        brand = QLabel("■ PIXEL")
        brand.setObjectName("brand")
        brand.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title_layout.addWidget(brand)
        title_layout.addStretch()

        min_btn = QPushButton("_")
        min_btn.setObjectName("windowButton")
        min_btn.setFixedSize(27, 24)
        min_btn.setToolTip("KÜÇÜLT")
        min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(min_btn)

        close_btn = QPushButton("X")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(27, 24)
        close_btn.setToolTip("KAPAT")
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        panel_layout.addWidget(self.titlebar)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 6, 2)
        content_layout.setSpacing(7)

        time_box = QFrame()
        time_box.setObjectName("box")
        time_layout = QVBoxLayout(time_box)
        time_layout.setContentsMargins(8, 6, 8, 6)

        self.clock = QLabel("00:00")
        self.clock.setObjectName("clock")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.addWidget(self.clock)

        self.full_date = QLabel("PAZARTESİ • 01 OCAK 2026")
        self.full_date.setObjectName("dateLarge")
        self.full_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.full_date.setWordWrap(True)
        time_layout.addWidget(self.full_date)
        content_layout.addWidget(time_box)

        weather_box = QFrame()
        weather_box.setObjectName("box")
        weather_layout = QVBoxLayout(weather_box)
        weather_layout.setContentsMargins(8, 6, 8, 6)

        weather_header = QHBoxLayout()
        weather_title = QLabel("☁ HAVA DURUMU")
        weather_title.setObjectName("section")
        weather_header.addWidget(weather_title)
        weather_header.addStretch()

        self.weather_city = QLabel(self.config["weather_city"].upper())
        self.weather_city.setObjectName("tiny")
        weather_header.addWidget(self.weather_city)
        weather_layout.addLayout(weather_header)

        self.weather_main = QLabel("YÜKLENİYOR...")
        self.weather_main.setObjectName("weatherMain")
        weather_layout.addWidget(self.weather_main)

        self.weather_detail = QLabel("HAVA DURUMU ALINIYOR")
        self.weather_detail.setObjectName("tiny")
        self.weather_detail.setWordWrap(True)
        weather_layout.addWidget(self.weather_detail)
        content_layout.addWidget(weather_box)

        self.character = PixelCharacter()
        self.character.installEventFilter(self)
        self.character.setCursor(Qt.CursorShape.OpenHandCursor)
        content_layout.addWidget(self.character)

        music_box = QFrame()
        music_box.setObjectName("box")
        music_layout = QVBoxLayout(music_box)
        music_layout.setContentsMargins(8, 6, 8, 6)

        music_title = QLabel("♪ ŞİMDİ ÇALIYOR")
        music_title.setObjectName("section")
        music_layout.addWidget(music_title)

        self.track = QLabel("MÜZİK YOK")
        self.track.setObjectName("track")
        self.track.setWordWrap(True)
        music_layout.addWidget(self.track)
        content_layout.addWidget(music_box)

        quest_box = QFrame()
        quest_box.setObjectName("box")
        quest_layout = QVBoxLayout(quest_box)
        quest_layout.setContentsMargins(8, 6, 8, 6)

        quest_title = QLabel("> MİNİ GÖREV")
        quest_title.setObjectName("section")
        quest_layout.addWidget(quest_title)

        self.note = QLabel(self.config["note"])
        self.note.setWordWrap(True)
        self.note.setObjectName("note")
        quest_layout.addWidget(self.note)
        content_layout.addWidget(quest_box)

        footer = QLabel("TEKERLEK = KAYDIR\nSAĞ TIK = MENÜ")
        footer.setObjectName("tiny")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(footer)

        self.scroll.setWidget(content)
        panel_layout.addWidget(self.scroll, 1)

        bottom = QHBoxLayout()
        hint = QLabel("ÜSTTEN/KARAKTERDEN SÜRÜKLE")
        hint.setObjectName("tiny")
        bottom.addWidget(hint)
        bottom.addStretch()

        self.resize_handle = ResizeHandle()
        bottom.addWidget(self.resize_handle)
        panel_layout.addLayout(bottom)

    def eventFilter(self, obj, event):
        if obj is self.character:
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                handle = self.windowHandle()
                if handle is not None:
                    self.character.setCursor(Qt.CursorShape.ClosedHandCursor)
                    handle.startSystemMove()
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.character.setCursor(Qt.CursorShape.OpenHandCursor)
        return super().eventFilter(obj, event)

    def apply_style(self):
        t = self.config["theme"]
        self.setStyleSheet(f"""
        #panel {{
            background: {t['panel']};
            border: 3px solid {t['text']};
        }}
        #titlebar {{
            background: {t['accent']};
            border: 2px solid {t['text']};
        }}
        #scroll, #scrollContent {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            background: {t['panel']};
            width: 12px;
            border: 2px solid {t['text']};
        }}
        QScrollBar::handle:vertical {{
            background: {t['accent']};
            min-height: 28px;
            border: 1px solid {t['text']};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        #box {{
            background: {t['box']};
            border: 2px solid {t['text']};
        }}
        QLabel {{
            color: {t['text']};
            background: transparent;
        }}
        #brand {{ font-size: 12px; font-weight: 700; }}
        #clock {{ font-size: 29px; font-weight: 700; }}
        #dateLarge {{ font-size: 11px; font-weight: 700; }}
        #weatherMain {{ font-size: 17px; font-weight: 700; padding: 3px 0; }}
        #section {{ font-size: 11px; font-weight: 700; }}
        #track, #note {{ font-size: 11px; }}
        #tiny {{ font-size: 9px; }}

        #windowButton, #closeButton {{
            background: {t['panel']};
            color: {t['text']};
            border: 2px solid {t['text']};
            font-weight: 700;
        }}
        #windowButton:hover {{ background: {t['accent']}; }}
        #closeButton:hover {{ background: {t['danger']}; }}

        #resizeHandle {{
            background: {t['accent']};
            color: {t['text']};
            border: 2px solid {t['text']};
            font-size: 14px;
            font-weight: 700;
        }}

        QMenu {{
            background: {t['panel']};
            color: {t['text']};
            border: 2px solid {t['text']};
        }}
        QMenu::item:selected {{
            background: {t['accent']};
        }}
        """)

    def update_clock(self):
        from PySide6.QtCore import QDateTime
        now = QDateTime.currentDateTime()
        self.clock.setText(now.toString("HH:mm"))

        days = [
            "PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE",
            "CUMA", "CUMARTESİ", "PAZAR"
        ]
        months = [
            "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
            "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"
        ]
        d = now.date()
        day_name = days[d.dayOfWeek() - 1]
        month_name = months[d.month() - 1]
        self.full_date.setText(f"{day_name} • {d.day():02d} {month_name} {d.year()}")

    def update_music(self):
        playing, title, artist = playerctl_metadata()
        self.character.set_dancing(playing)

        if title == "PLAYERCTL BULUNAMADI":
            text = "MÜZİK İÇİN PLAYERCTL GEREKLİ"
        elif artist:
            text = f"{title} - {artist}"
        else:
            text = title

        self.track.setText(text.upper())

    def refresh_weather(self):
        if self.weather_thread and self.weather_thread.isRunning():
            return

        self.weather_main.setText("YÜKLENİYOR...")
        self.weather_detail.setText("HAVA DURUMU GÜNCELLENİYOR")

        self.weather_thread = QThread(self)
        self.weather_worker = WeatherWorker(self.config["weather_city"])
        self.weather_worker.moveToThread(self.weather_thread)

        self.weather_thread.started.connect(self.weather_worker.run)
        self.weather_worker.done.connect(self.weather_loaded)
        self.weather_worker.failed.connect(self.weather_failed)

        self.weather_worker.done.connect(self.weather_thread.quit)
        self.weather_worker.failed.connect(self.weather_thread.quit)
        self.weather_worker.done.connect(self.weather_worker.deleteLater)
        self.weather_worker.failed.connect(self.weather_worker.deleteLater)
        self.weather_thread.finished.connect(self.weather_thread.deleteLater)

        self.weather_thread.start()

    def weather_loaded(self, data):
        self.weather_main.setText(f"{data['temp']}°C  •  {data['desc'].upper()}")
        self.weather_detail.setText(
            f"HİSSEDİLEN {data['feels']}°C  |  "
            f"EN YÜKSEK {data['max']}°  EN DÜŞÜK {data['min']}°\n"
            f"NEM %{data['humidity']}  |  RÜZGAR {data['wind']} KM/S"
        )

    def weather_failed(self, error):
        self.weather_main.setText("HAVA DURUMU ÇEVRİMDIŞI")
        self.weather_detail.setText("SAĞ TIK > ŞEHİR DEĞİŞTİR / YENİLE")

    def change_city(self):
        city, ok = QInputDialog.getText(
            self,
            "HAVA DURUMU ŞEHRİ",
            "ŞEHİR:",
            text=self.config["weather_city"],
        )
        if ok and city.strip():
            self.config["weather_city"] = city.strip()
            save_config(self.config)
            self.weather_city.setText(city.strip().upper())
            self.refresh_weather()

    def edit_note(self):
        text, ok = QInputDialog.getText(
            self,
            "MİNİ GÖREV",
            "GÖREVİN NE?",
            text=self.note.text(),
        )
        if ok and text.strip():
            text = text.strip().upper()
            self.note.setText(text)
            self.config["note"] = text
            save_config(self.config)

    def choose_color(self, key, title):
        current = QColor(self.config["theme"][key])
        color = QColorDialog.getColor(current, self, title)
        if color.isValid():
            self.config["theme"][key] = color.name()
            self.config["theme_name"] = "ÖZEL"
            save_config(self.config)
            self.apply_style()

    def reset_theme(self):
        self.config["theme"] = DEFAULT_THEME.copy()
        self.config["theme_name"] = "KREM MAVİ"
        save_config(self.config)
        self.apply_style()

    def apply_theme_preset(self, name):
        if name not in THEMES:
            return
        self.config["theme_name"] = name
        self.config["theme"] = THEMES[name].copy()
        save_config(self.config)
        self.apply_style()

    def toggle_always_on_top(self):
        self.config["always_on_top"] = not self.config.get("always_on_top", False)
        save_config(self.config)

        size = self.size()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config["always_on_top"]:
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.show()
        self.resize(size)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        city = QAction("HAVA DURUMU ŞEHRİNİ DEĞİŞTİR", self)
        city.triggered.connect(self.change_city)
        menu.addAction(city)

        refresh = QAction("HAVA DURUMUNU YENİLE", self)
        refresh.triggered.connect(self.refresh_weather)
        menu.addAction(refresh)

        menu.addSeparator()

        edit = QAction("MİNİ GÖREVİ DÜZENLE", self)
        edit.triggered.connect(self.edit_note)
        menu.addAction(edit)

        themes_menu = menu.addMenu("HAZIR TEMALAR")
        for theme_name in THEMES:
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.setChecked(self.config.get("theme_name") == theme_name)
            action.triggered.connect(lambda checked=False, n=theme_name: self.apply_theme_preset(n))
            themes_menu.addAction(action)

        colors = menu.addMenu("RENKLER")
        accent = QAction("VURGU RENGİ", self)
        accent.triggered.connect(lambda: self.choose_color("accent", "VURGU RENGİ"))
        colors.addAction(accent)

        panel = QAction("ARKA PLAN RENGİ", self)
        panel.triggered.connect(lambda: self.choose_color("panel", "ARKA PLAN RENGİ"))
        colors.addAction(panel)

        box = QAction("KART RENGİ", self)
        box.triggered.connect(lambda: self.choose_color("box", "KART RENGİ"))
        colors.addAction(box)

        text = QAction("YAZI / ÇERÇEVE RENGİ", self)
        text.triggered.connect(lambda: self.choose_color("text", "YAZI RENGİ"))
        colors.addAction(text)

        colors.addSeparator()

        reset = QAction("VARSAYILAN RENKLERE DÖN", self)
        reset.triggered.connect(self.reset_theme)
        colors.addAction(reset)

        menu.addSeparator()

        top = QAction("HER ZAMAN ÜSTTE", self)
        top.setCheckable(True)
        top.setChecked(self.config.get("always_on_top", False))
        top.triggered.connect(self.toggle_always_on_top)
        menu.addAction(top)

        menu.addSeparator()

        close = QAction("PIEL'İ KAPAT", self)
        close.triggered.connect(self.close)
        menu.addAction(close)

        menu.exec(event.globalPos())

    def resizeEvent(self, event):
        if hasattr(self, "config"):
            self.config["width"] = self.width()
            self.config["height"] = self.height()
            save_config(self.config)
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.config["width"] = self.width()
        self.config["height"] = self.height()
        save_config(self.config)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    widget = Pixel()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
