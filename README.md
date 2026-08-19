# PIXEL V12

PIXEL, CachyOS / Arch Linux ve özellikle KDE Plasma + Wayland için hazırlanmış retro 8-bit masaüstü companion widget'ıdır.

## V9 ile gelen büyük yenilikler

### Gerçek sprite sheet sistemi
Karakter artık tek görseli sadece sallamak yerine `assets/character-sprites.png` sprite sheet'i ve `assets/sprites.json` manifest'i üzerinden frame frame oynatılır.

Mevcut animasyon durumları:

- `idle` — boşta bekleme
- `walk` — pencere sürüklenirken yürüme tepkisi
- `sleep` — kullanıcı bir süre etkileşmezse uyuma
- `dance` — müzik çalarken dans
- `notify` — masaüstü bildirimi geldiğinde tepki
- `wave` — ara sıra kendi kendine selam / tatlı tepki

> Not: Sprite sheet motoru gerçek frame tabanlıdır. V9'daki frame görselleri mevcut tek karakter çiziminden üretilen ilk animasyon setidir. İleride elle çizilmiş ayrı kol/bacak pozlarıyla değiştirilmesi kolaydır.

### Uyuma animasyonu
PIXEL belirlenen süre boyunca etkileşim algılamazsa karakter uyku moduna geçer. Süre Ayarlar penceresinden değiştirilebilir.

### Bildirim tepkileri
Linux masaüstü bildirimleri `dbus-monitor` üzerinden dinlenir. Yeni bildirim geldiğinde karakter kısa bir şaşırma / zıplama animasyonu oynatır.

Bu özellik ayarlardan kapatılabilir.

### Ayarlar penceresi
Üst bardaki `⚙` düğmesiyle yeni Ayarlar penceresi açılır.

Buradan:

- hava durumu şehri
- hazır tema
- uykuya geçiş süresi
- bildirim tepkileri
- rastgele karakter tepkileri
- her zaman üstte
- otomatik başlatma

ayarları değiştirilebilir.

### Gelişmiş müzik kontrolleri
`playerctl` / MPRIS üzerinden:

- önceki parça
- oynat / duraklat
- sonraki parça
- parça adı + sanatçı
- geçen süre
- toplam süre
- seek / parçada ileri geri sarma

özellikleri eklendi.

### Daha fazla tema
Hazır temalar:

- KREM MAVİ
- PEMBE
- MOR
- YEŞİL
- KARANLIK
- SAKURA
- TURUNCU
- CYBER

Ayrıca özel renk seçimi devam eder.

## Diğer özellikler

- Türkçe saat ve tam tarih
- Hava durumu
- Hissedilen sıcaklık
- En yüksek / en düşük sıcaklık
- Nem ve rüzgar
- Mini Görev alanı
- Kaydırılabilir arayüz
- Native Wayland pencere sürükleme
- Sağ alttan yeniden boyutlandırma
- Sağ üstten küçültme ve kapatma
- Cozette / monospace font desteği
- KDE `.desktop` kurulumu
- PIXEL ikonu
- İsteğe bağlı autostart
- JSON tabanlı kalıcı ayarlar

## Kurulum — CachyOS / Arch Linux

```bash
chmod +x install.sh
./install.sh
```

Manuel bağımlılıklar:

```bash
sudo pacman -S --needed pyside6 playerctl
```

Sonra:

```bash
python main.py
```

## Ayar dosyası

```text
~/.config/pixel/config.json
```

## Proje yapısı

```text
PIXEL-v9/
├── assets/
│   ├── character.png
│   ├── character-sprites.png
│   ├── pixel-icon.png
│   └── sprites.json
├── .gitignore
├── LICENSE
├── README.md
├── install.sh
├── main.py
├── requirements.txt
└── uninstall.sh
```

## Bildirim tepkisi hakkında

V9 Linux/KDE tarafında `dbus-monitor` kullanır. Komut sistemde yoksa uygulama çalışmaya devam eder; yalnızca bildirim animasyonu devre dışı kalabilir.

## Windows

V9 halen Linux odaklıdır. Ana uygulama PySide6 olduğu için ileride Windows sürümü yapılabilir; fakat `playerctl`, `.desktop`, KDE autostart ve Linux bildirim izleme katmanları Windows için ayrıca uyarlanmalıdır.

## Lisans

MIT License — Copyright (c) 2026 blupn


## V10 düzeltmeleri

- Ayarlar penceresindeki aç/kapat kutuları daha büyük ve belirgin hale getirildi.
- Kutuların üstüne gelince görsel geri bildirim var.
- Linux'ta terminal kapatıldığında PIXEL'in kapanmaması için `SIGHUP` sinyali yok sayılıyor.
- Terminalden bağımsız başlatmak için `pixel-launch.sh` eklendi.

Terminalden bağımsız açmak için:

```bash
./pixel-launch.sh
```

Normal kullanımda KDE uygulama menüsündeki PIXEL kısayolunu kullanmak en temiz yöntemdir.


## V11 — Automatic Weather Location

- Added optional automatic IP-based city detection for weather.
- Automatic mode uses latitude/longitude from the coarse IP location to reduce wrong-city matches.
- Manual city mode is still available; changing the city manually disables auto location.
- VPN/proxy users can turn Auto Location off in Settings.
- The detected IP address is **not stored** by PIXEL.
- Weather responses are size-limited before JSON parsing.

### Privacy

When **Auto Location** is enabled, PIXEL contacts `ip-api.com` to estimate a coarse city/country and coordinates from the network IP. The detected IP itself is not saved in PIXEL's configuration. Weather data is then requested from `wttr.in`, using the detected coordinates when available. Disable **Auto Location** to use only the city entered manually.


## V12 — Multi-line Notes

- Mini Task / Note editor now supports multiple lines.
- Press Enter while editing to continue on a new line.
- Saved line breaks are preserved and displayed with word wrapping.
