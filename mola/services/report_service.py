"""Dönem filtreleme, özet hesabı ve CSV dışa aktarma.

Eski sürümde `show_summary` ve `generate_report` aynı toplam-süre
biriktirme mantığını iki ayrı yerde kopyalıyordu. Burada tek
`ozet_hesapla()` var, ikisi de onu kullanır.

Dönemler artık **takvim tabanlı**. Eski `filter_breaks_by_period` kayan
pencere kullanıyordu: "haftalık" son 7 gün, "aylık" son 28 gün demekti.
Salı günü alınan "bu hafta" raporu geçen haftanın çarşambasını da
kapsıyordu. Şimdi "bu hafta" pazartesi 00:00'da başlar.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from pathlib import Path

from config import TARIH_FORMATI
from i18n import Metin
from models import MolaKaydi, MolaTipi, saat_metni
from repository import AyarDeposu, MolaDeposu


class Donem(Enum):
    BUGUN = "bugun"
    HAFTA = "hafta"
    AY = "ay"
    TUMU = "tumu"

    @property
    def etiket(self) -> str:
        return {
            Donem.BUGUN: Metin.DONEM_BUGUN,
            Donem.HAFTA: Metin.DONEM_HAFTA,
            Donem.AY: Metin.DONEM_AY,
            Donem.TUMU: Metin.DONEM_TUMU,
        }[self]


@dataclass
class Ozet:
    """Bir çalışan ve dönem için hesaplanmış değerler."""

    mola_sayisi: int
    toplam_saniye: int
    ortalama_saniye: int
    gun_sayisi: int
    performans: float | None

    @property
    def toplam_metni(self) -> str:
        return saat_metni(self.toplam_saniye)

    @property
    def ortalama_metni(self) -> str:
        return saat_metni(self.ortalama_saniye)

    @property
    def performans_metni(self) -> str:
        if self.performans is None:
            return "-"
        return f"%{self.performans:.1f}"


@dataclass
class CalisanOzeti:
    calisan: str
    ozet: Ozet


def donem_araligi(
    donem: Donem, simdi: datetime | None = None
) -> tuple[datetime | None, datetime | None]:
    """Dönemin `[baslangic, bitis)` aralığı. TUMU için `(None, None)`.

    Bitiş dışlayıcıdır; gün sınırındaki bir kayıt iki döneme birden girmez.
    """
    an = simdi or datetime.now()
    bugun = an.date()

    if donem is Donem.TUMU:
        return None, None

    if donem is Donem.BUGUN:
        baslangic_gunu = bugun
        bitis_gunu = bugun + timedelta(days=1)
    elif donem is Donem.HAFTA:
        # weekday(): pazartesi 0. Hafta pazartesi başlar.
        baslangic_gunu = bugun - timedelta(days=bugun.weekday())
        bitis_gunu = baslangic_gunu + timedelta(days=7)
    else:  # Donem.AY
        baslangic_gunu = bugun.replace(day=1)
        if baslangic_gunu.month == 12:
            bitis_gunu = baslangic_gunu.replace(year=baslangic_gunu.year + 1, month=1)
        else:
            bitis_gunu = baslangic_gunu.replace(month=baslangic_gunu.month + 1)

    return (
        datetime.combine(baslangic_gunu, time.min),
        datetime.combine(bitis_gunu, time.min),
    )


def doneme_gore_filtrele(
    kayitlar: list[MolaKaydi], donem: Donem, simdi: datetime | None = None
) -> list[MolaKaydi]:
    baslangic, bitis = donem_araligi(donem, simdi)
    if baslangic is None or bitis is None:
        return list(kayitlar)
    return [kayit for kayit in kayitlar if baslangic <= kayit.baslangic < bitis]


def ozet_hesapla(kayitlar: list[MolaKaydi], vardiya_saati: int) -> Ozet:
    """Kayıt listesinden özet üretir.

    Performans yüzdesi, kayıt bulunan **benzersiz gün sayısı** üzerinden
    hesaplanır. Eski kod her dönem için sabit 8 saatlik tek güne bölüyordu;
    aylık raporda bu, yüzdeyi anlamsız biçimde eksiye düşürüyordu.
    """
    sayi = len(kayitlar)
    toplam = sum(kayit.toplam_saniye for kayit in kayitlar)
    gunler = {kayit.baslangic.date() for kayit in kayitlar}
    gun_sayisi = len(gunler)

    ortalama = toplam // sayi if sayi else 0

    performans: float | None = None
    if gun_sayisi and vardiya_saati > 0:
        calisilabilir = gun_sayisi * vardiya_saati * 3600
        performans = max(0.0, (calisilabilir - toplam) / calisilabilir * 100)

    return Ozet(
        mola_sayisi=sayi,
        toplam_saniye=toplam,
        ortalama_saniye=ortalama,
        gun_sayisi=gun_sayisi,
        performans=performans,
    )


class RaporServisi:
    def __init__(self, molalar: MolaDeposu, ayarlar: AyarDeposu) -> None:
        self._molalar = molalar
        self._ayarlar = ayarlar

    def kayitlar(
        self, calisan: str, donem: Donem, simdi: datetime | None = None
    ) -> list[MolaKaydi]:
        return doneme_gore_filtrele(self._molalar.molalar(calisan), donem, simdi)

    def ozet(self, calisan: str, donem: Donem, simdi: datetime | None = None) -> Ozet:
        return ozet_hesapla(
            self.kayitlar(calisan, donem, simdi), self._ayarlar.oku().vardiya_saati
        )

    def tum_calisanlar(
        self, donem: Donem, simdi: datetime | None = None
    ) -> list[CalisanOzeti]:
        """Her çalışan için özet, toplam mola süresine göre azalan sıralı."""
        vardiya = self._ayarlar.oku().vardiya_saati
        sonuc = [
            CalisanOzeti(
                calisan=calisan,
                ozet=ozet_hesapla(doneme_gore_filtrele(kayitlar, donem, simdi), vardiya),
            )
            for calisan, kayitlar in self._molalar.tum_veri().items()
        ]
        sonuc.sort(key=lambda oge: oge.ozet.toplam_saniye, reverse=True)
        return sonuc

    def gunluk_dagilim(
        self, calisan: str, donem: Donem, simdi: datetime | None = None
    ) -> list[tuple[date, int]]:
        """Grafik için `(gün, toplam saniye)` çiftleri, tarihe göre artan."""
        toplamlar: dict[date, int] = {}
        for kayit in self.kayitlar(calisan, donem, simdi):
            gun = kayit.baslangic.date()
            toplamlar[gun] = toplamlar.get(gun, 0) + kayit.toplam_saniye
        return sorted(toplamlar.items())


def csv_disa_aktar(
    yol: Path, calisan: str, kayitlar: list[MolaKaydi]
) -> tuple[bool, str]:
    """Kayıtları CSV olarak yazar. `(basarili, mesaj)` döner.

    `utf-8-sig` kullanılır: Excel, BOM görmeden açtığı CSV'de Türkçe
    karakterleri bozar. Ayraç olarak noktalı virgül seçildi — Türkçe
    Windows yerel ayarında Excel'in beklediği ayraç budur.
    """
    basliklar = [
        Metin.SUTUN_CALISAN,
        Metin.SUTUN_BASLANGIC,
        Metin.SUTUN_BITIS,
        Metin.SUTUN_TIP,
        "Süre (dk)",
        "Süre (sn)",
        "Toplam saniye",
        Metin.SUTUN_NOT,
    ]

    try:
        with open(yol, "w", encoding="utf-8-sig", newline="") as dosya:
            yazici = csv.writer(dosya, delimiter=";")
            yazici.writerow(basliklar)
            for kayit in kayitlar:
                yazici.writerow(
                    [
                        calisan,
                        kayit.baslangic.strftime(TARIH_FORMATI),
                        kayit.bitis.strftime(TARIH_FORMATI),
                        kayit.tip.etiket,
                        kayit.sure_dakika,
                        kayit.sure_saniye,
                        kayit.toplam_saniye,
                        kayit.aciklama,
                    ]
                )
    except OSError as hata:
        return False, Metin.DISA_AKTAR_HATA.format(sebep=hata)

    return True, Metin.DISA_AKTAR_TAMAM.format(sayi=len(kayitlar), yol=yol)


def tip_dagilimi(kayitlar: list[MolaKaydi]) -> dict[MolaTipi, int]:
    """Mola tipine göre toplam saniye. Grafik ve rapor için."""
    dagilim: dict[MolaTipi, int] = {}
    for kayit in kayitlar:
        dagilim[kayit.tip] = dagilim.get(kayit.tip, 0) + kayit.toplam_saniye
    return dagilim
