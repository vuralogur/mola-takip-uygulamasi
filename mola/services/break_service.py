"""Mola başlatma, bitirme ve limit değerlendirmesi."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from i18n import Metin
from models import AktifMola, MolaKaydi, MolaTipi, saat_metni
from repository import AktifMolaDeposu, AyarDeposu, MolaDeposu

# Limitin bu oranına ulaşıldığında "yaklaşıldı" uyarısı verilir.
YAKLASMA_ORANI = 0.8


class LimitDurumu(Enum):
    NORMAL = "normal"
    YAKLASTI = "yaklasti"
    ASILDI = "asildi"


class MolaServisi:
    """Mola yaşam döngüsü.

    Eski `end_break()` süreyi hesapladıktan **sonra** çalışanı okuyordu;
    çalışan seçili değilse geçen mola sessizce kayboluyordu. Burada mola
    zaten bir çalışana bağlı olarak başlatıldığı için o hata yapısal olarak
    mümkün değil.
    """

    def __init__(
        self,
        molalar: MolaDeposu,
        aktif_molalar: AktifMolaDeposu,
        ayarlar: AyarDeposu,
    ) -> None:
        self._molalar = molalar
        self._aktif = aktif_molalar
        self._ayarlar = ayarlar

    # --- Durum sorguları ---

    def aktif_molalar(self) -> dict[str, AktifMola]:
        return self._aktif.hepsi()

    def aktif_mola(self, calisan: str) -> AktifMola | None:
        return self._aktif.al(calisan)

    def molada_mi(self, calisan: str) -> bool:
        return self._aktif.molada_mi(calisan)

    def gecen_saniye(self, calisan: str, simdi: datetime | None = None) -> int | None:
        mola = self._aktif.al(calisan)
        if mola is None:
            return None
        return mola.gecen_saniye(simdi)

    # --- İşlemler ---

    def basla(self, calisan: str, tip: MolaTipi) -> tuple[bool, str]:
        if not calisan:
            return False, Metin.CALISAN_SECILMEDI

        if self._aktif.molada_mi(calisan):
            return False, Metin.MOLA_ZATEN_BASLADI.format(ad=calisan)

        if self._aktif.basla(calisan, tip) is None:
            # Yazma hatası; ayrıntı UyariKutusu'nda.
            return False, Metin.MOLA_ZATEN_BASLADI.format(ad=calisan)

        return True, Metin.MOLA_BASLADI.format(ad=calisan)

    def bitir(
        self, calisan: str, bitis: datetime | None = None
    ) -> tuple[bool, str, MolaKaydi | None]:
        """Molayı bitirir ve kalıcı kayda dönüştürür.

        `(basarili, mesaj, kayit)` döner. Kayıt yazılamazsa aktif mola geri
        konur — böylece geçen süre kaybolmaz, kullanıcı tekrar deneyebilir.
        """
        if not calisan:
            return False, Metin.CALISAN_SECILMEDI, None

        mola = self._aktif.bitir(calisan)
        if mola is None:
            return False, Metin.MOLA_BASLAMADI.format(ad=calisan), None

        kayit = MolaKaydi.olustur(
            baslangic=mola.baslangic,
            bitis=bitis or datetime.now(),
            tip=mola.tip,
        )

        if not self._molalar.ekle(calisan, kayit):
            self._aktif.basla(calisan, mola.tip, baslangic=mola.baslangic)
            return False, Metin.MOLA_BASLAMADI.format(ad=calisan), None

        sure = saat_metni(kayit.toplam_saniye)
        return True, Metin.MOLA_BITTI.format(ad=calisan, sure=sure), kayit

    def iptal(self, calisan: str) -> bool:
        """Molayı kayıt oluşturmadan siler. Çökme kurtarmada kullanılır."""
        return self._aktif.bitir(calisan) is not None

    # --- Limit değerlendirmesi ---

    def limit_saniye(self, tip: MolaTipi) -> int:
        """Tipin saniye cinsinden limiti. 0 = limit yok."""
        return self._ayarlar.oku().limit_dakika(tip) * 60

    def limit_durumu(
        self, calisan: str, simdi: datetime | None = None
    ) -> tuple[LimitDurumu, int]:
        """`(durum, limit_saniye)` döner. Limit yoksa daima NORMAL."""
        mola = self._aktif.al(calisan)
        if mola is None:
            return LimitDurumu.NORMAL, 0

        limit = self.limit_saniye(mola.tip)
        if limit <= 0:
            return LimitDurumu.NORMAL, 0

        gecen = mola.gecen_saniye(simdi)
        if gecen >= limit:
            return LimitDurumu.ASILDI, limit
        if gecen >= limit * YAKLASMA_ORANI:
            return LimitDurumu.YAKLASTI, limit
        return LimitDurumu.NORMAL, limit

    # --- Günlük bütçe ---

    def bugunku_toplam_saniye(self, calisan: str, gun: date | None = None) -> int:
        """Bugün tamamlanmış molaların toplamı. Devam eden mola dahil değil."""
        hedef = gun or date.today()
        return sum(
            kayit.toplam_saniye
            for kayit in self._molalar.molalar(calisan)
            if kayit.baslangic.date() == hedef
        )

    def gunluk_kalan_saniye(
        self, calisan: str, simdi: datetime | None = None
    ) -> int | None:
        """Günlük mola hakkından kalan süre. Hak sınırsızsa None.

        Devam eden mola da düşülür, böylece sayaç ilerledikçe kalan hak
        gerçek zamanlı azalır.
        """
        hak_dakika = self._ayarlar.oku().gunluk_toplam_hak
        if hak_dakika <= 0:
            return None

        kullanilan = self.bugunku_toplam_saniye(calisan)
        devam_eden = self.gecen_saniye(calisan, simdi)
        if devam_eden is not None:
            kullanilan += devam_eden

        return max(0, hak_dakika * 60 - kullanilan)
