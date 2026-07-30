"""Uygulama geneli sabitler, dosya yolları ve varsayılan ayarlar.

Yollar `Path(__file__).parent` üzerinden mutlaklaştırılır. Eski sürümde
dosya adları göreli string'di (`"break_data.json"`), bu yüzden uygulama
repo kökünden başlatıldığında yanlış konumda ikinci bir JSON çifti
oluşuyordu. Artık çalışma dizini ne olursa olsun aynı dosyalar kullanılır.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Final

UYGULAMA_ADI: Final[str] = "Mola Takip"
SURUM: Final[str] = "2.0.0"

# JSON şema sürümü. Değiştirmeden önce migrations.py'ye dönüşüm ekle.
SEMA_SURUMU: Final[int] = 2

# Projenin tek tarih formatı. İkinci bir format eklenmez; değiştirmek
# mevcut break_data.json üzerinde migration gerektirir.
TARIH_FORMATI: Final[str] = "%Y-%m-%d %H:%M:%S"
DOSYA_ADI_ZAMAN_FORMATI: Final[str] = "%Y%m%d-%H%M%S"

def _veri_dizini_bul() -> Path:
    """Veri dosyalarının yaşayacağı dizin.

    Kaynaktan çalışırken proje klasörü kullanılır — veriler kodun yanında
    durur, taşınabilir olur.

    PyInstaller ile paketlendiğinde durum değişir: `sys._MEIPASS` her
    çalıştırmada silinip yeniden kurulan geçici bir klasördür. Oraya yazmak
    tüm kayıtların kapanışta kaybolması demektir. Bu yüzden paketlenmiş
    sürümde `%APPDATA%/MolaTakip` kullanılır.
    """
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "MolaTakip"
        return Path.home() / ".molatakip"
    return Path(__file__).resolve().parent


VERI_DIZINI: Final[Path] = _veri_dizini_bul()
YEDEK_DIZINI: Final[Path] = VERI_DIZINI / "yedekler"

CALISAN_DOSYASI: Final[Path] = VERI_DIZINI / "employees.json"
MOLA_DOSYASI: Final[Path] = VERI_DIZINI / "break_data.json"
AKTIF_MOLA_DOSYASI: Final[Path] = VERI_DIZINI / "active_breaks.json"
AYAR_DOSYASI: Final[Path] = VERI_DIZINI / "settings.json"

SAKLANACAK_YEDEK_SAYISI: Final[int] = 10

# Çalışan adı doğrulama sınırları
CALISAN_ADI_MIN_UZUNLUK: Final[int] = 2
CALISAN_ADI_MAX_UZUNLUK: Final[int] = 60

# Mola notu uzunluk sınırı. Alan (`note`) şemada v1'den beri var; sınır
# yalnızca girişi makul tutmak için, şemayı etkilemez.
MOLA_NOTU_MAX_UZUNLUK: Final[int] = 200

VARSAYILAN_AYARLAR: Final[dict[str, Any]] = {
    "tema": "light",
    "vardiya_saati": 8,
    "ses_acik": True,
    "yedek_sayisi": SAKLANACAK_YEDEK_SAYISI,
    "pencere_boyutu": "1000x640",
    # Mola tipi -> dakika cinsinden limit. 0 = limit yok.
    "mola_limitleri": {
        "ogle": 60,
        "cay": 15,
        "sigara": 10,
        "diger": 0,
    },
    # Kişi başı günlük toplam mola bütçesi (dakika). 0 = sınırsız.
    "gunluk_toplam_hak": 90,
}
