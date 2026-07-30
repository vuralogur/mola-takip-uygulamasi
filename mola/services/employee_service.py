"""Çalışan ekleme, silme ve ad doğrulama."""

from __future__ import annotations

from config import CALISAN_ADI_MAX_UZUNLUK, CALISAN_ADI_MIN_UZUNLUK
from i18n import Metin
from repository import AktifMolaDeposu, CalisanDeposu, MolaDeposu

# Ada izin verilen, harf olmayan karakterler. Kesme işaretinin iki yaygın
# biçimi de kabul edilir ("Ali'nin" ve "Ali’nin").
IZINLI_ISARETLER = frozenset(" .-'’")


class CalisanServisi:
    def __init__(
        self,
        calisanlar: CalisanDeposu,
        molalar: MolaDeposu,
        aktif_molalar: AktifMolaDeposu,
    ) -> None:
        self._calisanlar = calisanlar
        self._molalar = molalar
        self._aktif = aktif_molalar

    def liste(self) -> list[str]:
        return self._calisanlar.liste()

    def ekle(self, ham_ad: str) -> tuple[bool, str]:
        """Çalışan ekler. `(basarili, mesaj)` döner."""
        ad = " ".join(ham_ad.split())

        hata = ad_dogrula(ad)
        if hata is not None:
            return False, hata

        if self._calisanlar.var_mi(ad):
            return False, Metin.CALISAN_ZATEN_VAR

        if not self._calisanlar.ekle(ad):
            # Yazma hatası; ayrıntı zaten UyariKutusu'na düştü.
            return False, Metin.CALISAN_ZATEN_VAR

        return True, Metin.CALISAN_EKLENDI.format(ad=ad)

    def sil(self, ad: str) -> tuple[bool, str]:
        """Çalışanı ve tüm mola verisini siler.

        Onay arayüzün sorumluluğundadır; buraya gelindiğinde onay alınmış
        sayılır. Aktif molası varsa önce o temizlenir, yoksa silinen
        çalışan `active_breaks.json` içinde hayalet kayıt olarak kalırdı.
        """
        if not ad:
            return False, Metin.CALISAN_SECILMEDI

        if not self._calisanlar.var_mi(ad):
            return False, Metin.CALISAN_BULUNAMADI

        self._aktif.bitir(ad)

        if not self._molalar.calisani_kaldir(ad):
            return False, Metin.CALISAN_BULUNAMADI

        if not self._calisanlar.sil(ad):
            return False, Metin.CALISAN_BULUNAMADI

        return True, Metin.CALISAN_SILINDI.format(ad=ad)


def ad_dogrula(ad: str) -> str | None:
    """Geçersizse hata mesajı, geçerliyse None döner.

    Eski sürüm yalnızca boş olup olmadığına bakıyordu. Burada uzunluk ve
    karakter kümesi de kontrol edilir; `str.isalpha()` Unicode farkında
    olduğu için Türkçe harfler sorunsuz geçer.
    """
    if not ad:
        return Metin.CALISAN_ADI_BOS

    if len(ad) < CALISAN_ADI_MIN_UZUNLUK:
        return Metin.CALISAN_ADI_KISA.format(min=CALISAN_ADI_MIN_UZUNLUK)

    if len(ad) > CALISAN_ADI_MAX_UZUNLUK:
        return Metin.CALISAN_ADI_UZUN.format(max=CALISAN_ADI_MAX_UZUNLUK)

    if not any(karakter.isalpha() for karakter in ad):
        return Metin.CALISAN_ADI_GECERSIZ

    for karakter in ad:
        if not karakter.isalpha() and karakter not in IZINLI_ISARETLER:
            return Metin.CALISAN_ADI_GECERSIZ

    return None
