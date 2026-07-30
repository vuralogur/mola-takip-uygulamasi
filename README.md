# Mola Takip

Çalışan mola sürelerini takip eden, tamamen çevrimdışı çalışan masaüstü
uygulaması. Python + Tkinter, veriler yerel JSON dosyalarında.

## Özellikler

- **Canlı sayaç** — devam eden mola saniye saniye görünür, uygulama kapansa
  bile mola kaybolmaz
- **Çoklu eşzamanlı mola** — birden fazla çalışan aynı anda molada olabilir
- **Mola tipleri** — Öğle, Çay, Sigara, Diğer; her tipe ayrı dakika limiti
- **Limit uyarısı** — limite yaklaşınca sarı, aşınca kırmızı sayaç + sesli uyarı
- **Günlük mola hakkı** — kişi başı günlük bütçe ve kalan süre gösterimi
- **Sıralanabilir geçmiş tablosu** — takvim tabanlı dönem filtresi
  (Bugün / Bu Hafta / Bu Ay / Tümü)
- **Raporlar** — kişi özeti, tüm çalışanların karşılaştırmalı tablosu,
  çubuk grafikler
- **CSV dışa aktarma** — Excel'de Türkçe karakterler bozulmadan açılır
- **Açık / koyu tema** — Windows 11 görünümü (sv-ttk)
- **Veri güvenliği** — atomik yazma, otomatik yedekleme, bozuk dosya kurtarma

## Kurulum

Python 3.10 veya üzeri gerekir (Tkinter ile birlikte).

```
python -m pip install -r requirements.txt
```

## Çalıştırma

```
cd mola
python main.py
```

## Paketleme (.exe)

Tek dosyalık Windows çalıştırılabiliri PyInstaller ile üretilir:

```
python -m pip install pyinstaller
python build.py
```

Çıktı: `dist/MolaTakip.exe`. Kök dizinde `mola.ico` varsa ikon olarak
kullanılır, yoksa varsayılan ikonla devam eder. Paketlenmiş sürümde veri
dosyaları exe'nin yanına değil `%APPDATA%\MolaTakip` altına yazılır — çünkü
PyInstaller'ın açtığı geçici klasör her çalıştırmada silinir.

## Veri Dosyaları

Kaynaktan çalışırken `mola/` klasöründe, UTF-8 kodlamalı JSON:

| Dosya | İçerik |
| --- | --- |
| `employees.json` | Çalışan adları listesi |
| `break_data.json` | Tamamlanmış mola kayıtları (şema v2) |
| `active_breaks.json` | Devam eden molalar |
| `settings.json` | Vardiya, limitler, tema, pencere boyutu |
| `yedekler/` | Son 10 sürümün otomatik yedeği |

Bu dosyalar depoda tutulmaz (`.gitignore`) — gerçek çalışan adları içerdikleri
için. Yeni bir klon boş başlar; uygulama ilk kaydı yazarken dosyaları kendisi
oluşturur.

Elinizde eski (v1) bir `break_data.json` varsa uygulama ilk açılışta onu
otomatik olarak v2 şemasına yükseltir ve önce yedeğini alır. Hiçbir alan
silinmez.

## Proje Yapısı

```
build.py                       PyInstaller sarmalayıcı (uygulama import etmez)
mola/
├── main.py                    giriş noktası
├── config.py                  sabitler, dosya yolları
├── models.py                  MolaKaydi, AktifMola, Ayarlar, MolaTipi
├── storage.py                 UTF-8 + atomik JSON okuma/yazma
├── backup.py                  sürüm yedekleme
├── migrations.py              v1 -> v2 şema göçü
├── repository.py              depo katmanı, bellek önbelleği
├── i18n.py                    tüm arayüz metinleri
├── services/
│   ├── employee_service.py    çalışan ekleme/silme + ad doğrulama
│   ├── break_service.py       mola yaşam döngüsü, limitler
│   └── report_service.py      dönem filtresi, özet, CSV
└── ui/
    ├── app.py                 ana pencere, orkestrasyon
    ├── panels.py              çalışan / mola / geçmiş panelleri
    ├── dialogs.py             ayarlar, grafik, tüm çalışanlar
    ├── chart.py               Canvas çubuk grafik
    └── theme.py               tema, boşluk ölçeği, fontlar
```

Katman kuralı: `ui` -> `services` -> `repository` -> `storage`. Alt katmanlar
üst katmanı tanımaz; depo ve servisler `messagebox` çağırmaz.

## Bağımlılıklar

Yalnızca `sv-ttk` (tema). Grafikler Tkinter `Canvas` ile çizilir —
matplotlib yoktur. CSV, `csv` standart kütüphanesiyle üretilir.

## Lisans

MIT — ayrıntı için [LICENSE](LICENSE).
