"""Arayüz metinleri.

Tüm kullanıcıya görünen metin burada toplanır; widget kodunda düz string
gömülmez. Böylece hem yazım tutarlılığı korunur hem de ileride ikinci bir
dil eklemek tek dosyaya dokunmak olur.

Bu dosyanın UTF-8 olarak okunabilmesi Türkçe karakterler için şarttır;
`storage.py` tüm veri okuma/yazmayı UTF-8'e sabitler.
"""

from __future__ import annotations

from typing import Final


class Metin:
    """Türkçe arayüz metinleri."""

    # --- Genel ---
    UYGULAMA: Final = "Mola Takip"
    TAMAM: Final = "Tamam"
    IPTAL: Final = "İptal"
    KAPAT: Final = "Kapat"
    SIL: Final = "Sil"
    EKLE: Final = "Ekle"
    KAYDET: Final = "Kaydet"

    # --- Başlıklar ---
    BASLIK_CALISANLAR: Final = "Çalışanlar"
    BASLIK_GECMIS: Final = "Mola Geçmişi"
    BASLIK_AYARLAR: Final = "Ayarlar"
    BASLIK_HATA: Final = "Hata"
    BASLIK_UYARI: Final = "Uyarı"
    BASLIK_BILGI: Final = "Bilgi"
    BASLIK_ONAY: Final = "Onay"
    BASLIK_OZET: Final = "Özet"
    BASLIK_RAPOR: Final = "Rapor"

    # --- Çalışan işlemleri ---
    CALISAN_ADI: Final = "Çalışan adı"
    CALISAN_EKLE: Final = "Çalışan Ekle"
    CALISAN_SIL: Final = "Çalışanı Sil"
    CALISAN_SECILMEDI: Final = "Önce bir çalışan seçin."
    CALISAN_ZATEN_VAR: Final = "Bu isimde bir çalışan zaten kayıtlı."
    CALISAN_BULUNAMADI: Final = "Çalışan bulunamadı."
    CALISAN_ADI_BOS: Final = "Çalışan adı boş olamaz."
    CALISAN_ADI_KISA: Final = "Çalışan adı en az {min} karakter olmalı."
    CALISAN_ADI_UZUN: Final = "Çalışan adı en fazla {max} karakter olabilir."
    CALISAN_ADI_GECERSIZ: Final = (
        "Çalışan adı yalnızca harf, boşluk, nokta ve kesme işareti içerebilir."
    )
    CALISAN_SILME_ONAY: Final = (
        "{ad} silinecek.\n\nBu çalışana ait tüm mola kayıtları da silinecek. "
        "Bu işlem geri alınamaz.\n\nDevam edilsin mi?"
    )
    CALISAN_SILINDI: Final = "{ad} silindi."
    CALISAN_EKLENDI: Final = "{ad} eklendi."
    CALISAN_YOK: Final = "Henüz çalışan eklenmemiş."

    # --- Mola işlemleri ---
    MOLA_BASLAT: Final = "Mola Başlat"
    MOLA_BITIR: Final = "Mola Bitir"
    MOLA_TIPI: Final = "Mola tipi"
    MOLADA: Final = "molada"
    MOLA_BASLAMADI: Final = "{ad} için başlamış bir mola yok."
    MOLA_ZATEN_BASLADI: Final = "{ad} zaten molada."
    MOLA_BASLADI: Final = "{ad} molaya çıktı."
    MOLA_BITTI: Final = "{ad} molası bitti — {sure}"
    MOLA_YOK: Final = "Seçili çalışan için mola kaydı yok."
    MOLA_SIL_ONAY: Final = "Seçili {sayi} mola kaydı silinecek. Devam edilsin mi?"
    MOLA_HEPSINI_SIL_ONAY: Final = (
        "{ad} çalışanına ait TÜM mola kayıtları silinecek. "
        "Bu işlem geri alınamaz.\n\nDevam edilsin mi?"
    )
    MOLA_SILINDI: Final = "{sayi} mola kaydı silindi."
    MOLA_SECILMEDI: Final = "Silinecek mola kaydı seçilmedi."

    # --- Sayaç ve durum ---
    SAYAC_BOS: Final = "--:--:--"
    DURUM_HAZIR: Final = "Hazır"
    LIMIT_YOK: Final = "limit yok"
    LIMIT_BILGI: Final = "limit {dakika} dk"
    LIMIT_ASILDI: Final = "Limit aşıldı"
    LIMITE_YAKLASILDI: Final = "Limite yaklaşıldı"
    GUNLUK_HAK_KALAN: Final = "Bugün kalan hak: {sure}"
    GUNLUK_HAK_BITTI: Final = "Günlük mola hakkı doldu"

    # --- Tablo sütunları ---
    SUTUN_BASLANGIC: Final = "Başlangıç"
    SUTUN_BITIS: Final = "Bitiş"
    SUTUN_SURE: Final = "Süre"
    SUTUN_TIP: Final = "Tip"
    SUTUN_CALISAN: Final = "Çalışan"
    SUTUN_DURUM: Final = "Durum"
    SUTUN_MOLA_SAYISI: Final = "Mola"
    SUTUN_TOPLAM: Final = "Toplam"
    SUTUN_ORTALAMA: Final = "Ortalama"
    SUTUN_PERFORMANS: Final = "Performans"

    # --- Dönemler ---
    DONEM_BUGUN: Final = "Bugün"
    DONEM_HAFTA: Final = "Bu Hafta"
    DONEM_AY: Final = "Bu Ay"
    DONEM_TUMU: Final = "Tümü"

    # --- Raporlar ---
    RAPOR_OZET: Final = "Özet"
    RAPOR_TUM_CALISANLAR: Final = "Tüm Çalışanlar"
    RAPOR_GRAFIK: Final = "Grafik"
    RAPOR_DISA_AKTAR: Final = "Dışa Aktar"
    RAPOR_YAZDIR: Final = "Yazdır"
    RAPOR_VERI_YOK: Final = "Seçilen dönem için kayıt bulunamadı."
    RAPOR_TOPLAM_MOLA: Final = "Toplam mola süresi"
    RAPOR_MOLA_SAYISI: Final = "Mola sayısı"
    RAPOR_GUN_PERFORMANSI: Final = "Gün performansı"
    RAPOR_ORTALAMA_MOLA: Final = "Ortalama mola"

    # --- Dışa aktarma ---
    DISA_AKTAR_BASLIK: Final = "CSV olarak kaydet"
    DISA_AKTAR_TAMAM: Final = "{sayi} kayıt dışa aktarıldı:\n{yol}"
    DISA_AKTAR_HATA: Final = "Dosya yazılamadı:\n{sebep}"

    # --- Ayarlar ---
    AYAR_TEMA: Final = "Tema"
    AYAR_TEMA_ACIK: Final = "Açık"
    AYAR_TEMA_KOYU: Final = "Koyu"
    AYAR_VARDIYA: Final = "Vardiya süresi (saat)"
    AYAR_SES: Final = "Limit aşımında sesli uyarı"
    AYAR_YEDEK: Final = "Saklanacak yedek sayısı"
    AYAR_LIMITLER: Final = "Mola limitleri (dakika, 0 = sınırsız)"
    AYAR_GUNLUK_HAK: Final = "Günlük toplam mola hakkı (dakika, 0 = sınırsız)"
    AYAR_KAYDEDILDI: Final = "Ayarlar kaydedildi."
    AYAR_GECERSIZ_SAYI: Final = "{alan} için geçerli bir sayı girin."

    # --- Veri hataları ---
    VERI_BOZUK: Final = (
        "{dosya} dosyası okunamadı: {sebep}\n\n"
        "Dosya bozulmadan {kenara} adıyla kenara alındı. "
        "Uygulama boş veriyle açılıyor — eski kayıtları kurtarmak için bu "
        "dosyayı inceleyebilirsiniz."
    )
    VERI_BOZUK_TASINAMADI: Final = (
        "{dosya} dosyası okunamadı: {sebep}\n\n"
        "Dosya olduğu yerde bırakıldı ve üzerine yazılmayacak."
    )
    VERI_YAZILAMADI: Final = (
        "{dosya} dosyasına yazılamadı: {sebep}\n\n"
        "Mevcut kayıtlar değişmedi. Son işlem kaydedilmemiş olabilir."
    )
    KAYIT_ATLANDI: Final = "{sayi} bozuk mola kaydı atlandı."
    GOC_YAPILDI: Final = (
        "Veri dosyası yeni sürüme yükseltildi. Eski sürümün yedeği alındı: {yedek}"
    )

    # --- Aktif mola kurtarma ---
    ESKI_MOLA_BASLIK: Final = "Devam eden mola bulundu"
    ESKI_MOLA_SORU: Final = (
        "{ad} çalışanının molası {sure} önce başlamış ve hâlâ açık.\n\n"
        "Uygulama kapanmadan mola bitirilmemiş olabilir.\n\n"
        "Evet: molayı şimdi bitir ve kaydet\n"
        "Hayır: molayı iptal et, kayıt oluşturma"
    )
