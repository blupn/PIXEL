<img width="378" height="505" alt="17" src="https://github.com/user-attachments/assets/845b8a93-5de4-4cff-9ca1-5b75ce8c0582" />
<img width="378" height="504" alt="16" src="https://github.com/user-attachments/assets/3023ef71-2163-4693-a6d8-9ede7407081a" />
<img width="373" height="506" alt="15" src="https://github.com/user-attachments/assets/f9f8c958-4bb1-4925-b1f0-f23c0518276a" />
<img width="378" height="508" alt="14" src="https://github.com/user-attachments/assets/d10504ef-0aaf-4acf-acb8-ef9619d55157" />
<img width="376" height="508" alt="13" src="https://github.com/user-attachments/assets/9fd5a261-6a03-43e8-8aff-992e35f65d80" />




# PIXEL

PIXEL, Linux masaüstü için hazırlanmış retro 8-bit görünümlü bir masaüstü widget / pixel companion uygulamasıdır.

Özellikle **CachyOS + KDE Plasma + Wayland** üzerinde geliştirilmiştir. Saat, tarih, hava durumu, müzik bilgisi, mini görevler, temalar ve animasyonlu pixel karakter gibi özellikleri tek bir küçük masaüstü widget'ında bir araya getirir.

## Özellikler

- Retro 8-bit / pixel arayüz
- Pixel karakter
- Idle animasyonu
- Müzik çalarken dans animasyonu
- Saat
- Tam Türkçe tarih
- Hava durumu
  - Anlık sıcaklık
  - Hissedilen sıcaklık
  - Günün en yüksek / en düşük sıcaklığı
  - Nem
  - Rüzgar
- Hava durumu şehrini değiştirme
- Hava durumunu manuel yenileme
- Yaklaşık 15 dakikada bir otomatik hava durumu yenileme
- `playerctl` ile Now Playing / Şimdi Çalıyor bilgisi
- Mini Görev alanı
- Kaydırılabilir içerik
- KDE / Wayland uyumlu native sürükleme
- Sağ alttan yeniden boyutlandırma
- Kapatma ve küçültme düğmeleri
- Her zaman üstte seçeneği
- Cozette / monospace pixel font desteği
- Hazır temalar
  - Krem Mavi
  - Pembe
  - Mor
  - Yeşil
  - Karanlık
- Manuel renk özelleştirme
- Ayarları JSON dosyasında saklama
- KDE uygulama menüsü için `.desktop` kurulumu
- Özel PIXEL uygulama ikonu
- İsteğe bağlı otomatik başlatma
- Uninstall script

## Ekran Yapısı

PIXEL içinde şu bölümler bulunur:

- Saat ve tarih
- Hava durumu
- Pixel karakter
- Şimdi Çalıyor
- Mini Görev

İçerik fazla olduğunda mouse tekerleğiyle yukarı / aşağı kaydırılabilir.

## Gereksinimler

- Linux
- Python 3
- PySide6 / Qt 6
- playerctl
- İnternet bağlantısı (hava durumu için)

CachyOS / Arch Linux:

```bash
sudo pacman -S --needed pyside6 playerctl
```

## Kurulum

Projeyi klonla:

```bash
git clone <REPO_URL>
cd PIXEL
```

Kurulum script'ini çalıştır:

```bash
chmod +x install.sh
./install.sh
```

Kurulum sırasında PIXEL'in oturum açıldığında otomatik başlamasını isteyip istemediğin sorulur.

Kurulumdan sonra KDE uygulama menüsünde:

```text
PIXEL
```

diye aratıp uygulamayı terminal açmadan çalıştırabilirsin.

## Manuel Çalıştırma

```bash
python main.py
```

## Kullanım

- Üst bar veya karakter: pencereyi sürükle
- Sağ alt `◢`: boyutlandır
- Mouse tekerleği: içeriği kaydır
- Sağ üst `X`: kapat
- Sağ üst `_`: küçült
- Sağ tık: ayarlar menüsü

## Tema Değiştirme

Sağ tık:

```text
HAZIR TEMALAR
```

Buradan hazır temalardan birini seçebilirsin.

Daha detaylı özelleştirme için:

```text
RENKLER
```

menüsünden arka plan, kart, vurgu ve yazı/çerçeve renklerini ayrı ayrı değiştirebilirsin.

## Hava Durumu

Varsayılan şehir İstanbul'dur.

Şehri değiştirmek için:

```text
Sağ tık → HAVA DURUMU ŞEHRİNİ DEĞİŞTİR
```

Hava durumu internet üzerinden alınır ve yaklaşık 15 dakikada bir yenilenir.

## Ayar Dosyası

Kullanıcı ayarları şu konumda tutulur:

```text
~/.config/pixel/config.json
```

Bu dosya GitHub reposuna eklenmemelidir.

## Kaldırma

Menü kısayolunu, ikonu ve autostart kaydını kaldırmak için:

```bash
./uninstall.sh
```

Bu işlem proje klasörünü silmez.

## Proje Yapısı

```text
PIXEL/
├── assets/
│   ├── character.png
│   └── pixel-icon.png
├── .gitignore
├── LICENSE
├── README.md
├── install.sh
├── main.py
└── uninstall.sh
```

## Geliştirme Durumu

PIXEL aktif geliştirme aşamasındadır.

Planlanan geliştirmeler:

- Gerçek sprite sheet animasyonları
- Daha fazla karakter animasyonu
- Uyuma animasyonu
- Yürüme animasyonu
- Bildirim tepkileri
- Daha fazla tema
- Ayarlar penceresi
- Daha gelişmiş müzik kontrolleri

## Lisans


Bu proje MIT Lisansı ile lisanslanmıştır.

Copyright (c) 2026 blupn
