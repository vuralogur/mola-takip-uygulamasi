"""Veri modelleri.

Python tarafındaki alan adları Türkçe, JSON tarafındaki anahtarlar
İngilizce ve v1 şemasıyla birebir aynı. `to_dict` / `from_dict` bu iki
tarafı birbirine bağlar. JSON anahtarları bir sözleşmedir — CLAUDE.md
gereği migration olmadan değiştirilemez.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from config import TARIH_FORMATI, VARSAYILAN_AYARLAR


class MolaTipi(Enum):
    """Mola türü. Değer JSON'a yazılan anahtar, etiket arayüzde görünen ad.

    v1 verisinde tip alanı yoktu; migration eski kayıtlara DIGER atar.
    """

    OGLE = "ogle"
    CAY = "cay"
    SIGARA = "sigara"
    DIGER = "diger"

    @property
    def etiket(self) -> str:
        return {
            MolaTipi.OGLE: "Öğle",
            MolaTipi.CAY: "Çay",
            MolaTipi.SIGARA: "Sigara",
            MolaTipi.DIGER: "Diğer",
        }[self]

    @classmethod
    def coz(cls, deger: Any) -> "MolaTipi":
        """Bilinmeyen veya bozuk değeri DIGER'e düşürür, hata fırlatmaz."""
        if isinstance(deger, cls):
            return deger
        try:
            return cls(str(deger).strip().lower())
        except ValueError:
            return cls.DIGER


def yeni_kimlik() -> str:
    """Kayıt kimliği. Kısa tutuldu; tek makinede çakışma olasılığı ihmal
    edilebilir ve JSON'u okunabilir bırakır."""
    return uuid.uuid4().hex[:8]


def sure_metni(dakika: int, saniye: int) -> str:
    """`12:05` biçiminde süre metni."""
    return f"{dakika}:{saniye:02d}"


def saat_metni(toplam_saniye: int) -> str:
    """`01:23:45` biçiminde sayaç metni. Sabit genişlik, sayaç zıplamaz."""
    toplam_saniye = max(0, int(toplam_saniye))
    saat, kalan = divmod(toplam_saniye, 3600)
    dakika, saniye = divmod(kalan, 60)
    return f"{saat:02d}:{dakika:02d}:{saniye:02d}"


@dataclass
class MolaKaydi:
    """Tamamlanmış tek bir mola."""

    baslangic: datetime
    bitis: datetime
    sure_dakika: int
    sure_saniye: int
    tip: MolaTipi = MolaTipi.DIGER
    aciklama: str = ""
    kimlik: str = field(default_factory=yeni_kimlik)

    @property
    def toplam_saniye(self) -> int:
        """Dakika ve saniye tek bir sürenin parçalarıdır, iki ayrı toplam
        değil. Toplama yaparken daima bu değer üzerinden git."""
        return self.sure_dakika * 60 + self.sure_saniye

    @classmethod
    def olustur(
        cls,
        baslangic: datetime,
        bitis: datetime,
        tip: MolaTipi = MolaTipi.DIGER,
        aciklama: str = "",
    ) -> "MolaKaydi":
        """Süreyi başlangıç/bitişten hesaplayarak kayıt üretir."""
        toplam = max(0, int((bitis - baslangic).total_seconds()))
        dakika, saniye = divmod(toplam, 60)
        return cls(
            baslangic=baslangic,
            bitis=bitis,
            sure_dakika=dakika,
            sure_saniye=saniye,
            tip=tip,
            aciklama=aciklama,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.kimlik,
            "start_time": self.baslangic.strftime(TARIH_FORMATI),
            "end_time": self.bitis.strftime(TARIH_FORMATI),
            "duration_minutes": self.sure_dakika,
            "duration_seconds": self.sure_saniye,
            "break_type": self.tip.value,
            "note": self.aciklama,
        }

    @classmethod
    def from_dict(cls, ham: dict[str, Any]) -> "MolaKaydi | None":
        """Sözlükten kayıt üretir. Zorunlu alanlar okunamıyorsa None döner.

        Tek bozuk kayıt yüzünden tüm dosyayı reddetmemek için hata
        fırlatmaz; çağıran None dönenleri atlar ve kullanıcıyı bilgilendirir.
        """
        if not isinstance(ham, dict):
            return None

        try:
            baslangic = datetime.strptime(str(ham["start_time"]), TARIH_FORMATI)
            bitis = datetime.strptime(str(ham["end_time"]), TARIH_FORMATI)
        except (KeyError, TypeError, ValueError):
            return None

        try:
            dakika = int(ham["duration_minutes"])
            saniye = int(ham["duration_seconds"])
        except (KeyError, TypeError, ValueError):
            # Süre alanları bozuksa zaman damgalarından yeniden hesapla.
            toplam = max(0, int((bitis - baslangic).total_seconds()))
            dakika, saniye = divmod(toplam, 60)

        return cls(
            baslangic=baslangic,
            bitis=bitis,
            sure_dakika=max(0, dakika),
            sure_saniye=max(0, min(59, saniye)),
            tip=MolaTipi.coz(ham.get("break_type", MolaTipi.DIGER.value)),
            aciklama=str(ham.get("note", "")),
            kimlik=str(ham.get("id") or yeni_kimlik()),
        )


@dataclass
class AktifMola:
    """Devam eden mola. `active_breaks.json` içinde tutulur, böylece
    uygulama kapansa bile mola kaybolmaz."""

    calisan: str
    baslangic: datetime
    tip: MolaTipi = MolaTipi.DIGER

    def gecen_saniye(self, simdi: datetime | None = None) -> int:
        return max(0, int(((simdi or datetime.now()) - self.baslangic).total_seconds()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.baslangic.strftime(TARIH_FORMATI),
            "break_type": self.tip.value,
        }

    @classmethod
    def from_dict(cls, calisan: str, ham: Any) -> "AktifMola | None":
        if not isinstance(ham, dict):
            return None
        try:
            baslangic = datetime.strptime(str(ham["start_time"]), TARIH_FORMATI)
        except (KeyError, TypeError, ValueError):
            return None
        return cls(
            calisan=calisan,
            baslangic=baslangic,
            tip=MolaTipi.coz(ham.get("break_type", MolaTipi.DIGER.value)),
        )


@dataclass
class Ayarlar:
    """Kullanıcı ayarları. Eksik veya bozuk anahtarlar varsayılana düşer."""

    tema: str = VARSAYILAN_AYARLAR["tema"]
    vardiya_saati: int = VARSAYILAN_AYARLAR["vardiya_saati"]
    ses_acik: bool = VARSAYILAN_AYARLAR["ses_acik"]
    yedek_sayisi: int = VARSAYILAN_AYARLAR["yedek_sayisi"]
    pencere_boyutu: str = VARSAYILAN_AYARLAR["pencere_boyutu"]
    mola_limitleri: dict[str, int] = field(
        default_factory=lambda: dict(VARSAYILAN_AYARLAR["mola_limitleri"])
    )
    gunluk_toplam_hak: int = VARSAYILAN_AYARLAR["gunluk_toplam_hak"]

    def limit_dakika(self, tip: MolaTipi) -> int:
        """Tipin dakika limiti. 0 = limit yok."""
        try:
            return max(0, int(self.mola_limitleri.get(tip.value, 0)))
        except (TypeError, ValueError):
            return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tema": self.tema,
            "vardiya_saati": self.vardiya_saati,
            "ses_acik": self.ses_acik,
            "yedek_sayisi": self.yedek_sayisi,
            "pencere_boyutu": self.pencere_boyutu,
            "mola_limitleri": dict(self.mola_limitleri),
            "gunluk_toplam_hak": self.gunluk_toplam_hak,
        }

    @classmethod
    def from_dict(cls, ham: Any) -> "Ayarlar":
        if not isinstance(ham, dict):
            return cls()

        def tam_sayi(anahtar: str, alt_sinir: int = 0) -> int:
            try:
                return max(alt_sinir, int(ham.get(anahtar, VARSAYILAN_AYARLAR[anahtar])))
            except (TypeError, ValueError):
                return int(VARSAYILAN_AYARLAR[anahtar])

        limitler = dict(VARSAYILAN_AYARLAR["mola_limitleri"])
        gelen_limitler = ham.get("mola_limitleri")
        if isinstance(gelen_limitler, dict):
            for anahtar, deger in gelen_limitler.items():
                if anahtar in limitler:
                    try:
                        limitler[anahtar] = max(0, int(deger))
                    except (TypeError, ValueError):
                        pass

        tema = str(ham.get("tema", VARSAYILAN_AYARLAR["tema"])).lower()
        if tema not in ("light", "dark"):
            tema = VARSAYILAN_AYARLAR["tema"]

        return cls(
            tema=tema,
            vardiya_saati=max(1, tam_sayi("vardiya_saati", 1)),
            ses_acik=bool(ham.get("ses_acik", VARSAYILAN_AYARLAR["ses_acik"])),
            yedek_sayisi=tam_sayi("yedek_sayisi"),
            pencere_boyutu=str(
                ham.get("pencere_boyutu", VARSAYILAN_AYARLAR["pencere_boyutu"])
            ),
            mola_limitleri=limitler,
            gunluk_toplam_hak=tam_sayi("gunluk_toplam_hak"),
        )
