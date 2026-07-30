"""Veri dosyaları için basit sürüm yedekleme.

Destrüktif bir işlemden önce çağrılır. Yedekler `mola/yedekler/` altında
zaman damgalı adlarla tutulur, sayı sınırı aşılınca en eskiler silinir.

Yedekleme bir kolaylık katmanıdır, kritik yol değil: yedek alınamazsa
asıl işlem engellenmez, sadece None döner. Asıl veri güvenliği
`storage.json_yaz` içindeki atomik yazmadan gelir.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import DOSYA_ADI_ZAMAN_FORMATI, SAKLANACAK_YEDEK_SAYISI, YEDEK_DIZINI

YEDEK_UZANTISI = ".yedek"


def yedek_al(dosya: Path, saklanacak: int = SAKLANACAK_YEDEK_SAYISI) -> Path | None:
    """`dosya`nın zaman damgalı bir kopyasını yedek dizinine alır.

    Dosya yoksa yapacak iş yoktur, None döner. Kopyalama başarısız olursa
    yine None döner — çağıran işlemi durdurmaz.
    """
    if not dosya.exists():
        return None

    damga = datetime.now().strftime(DOSYA_ADI_ZAMAN_FORMATI)

    try:
        YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
        hedef = _bos_hedef(dosya.name, damga)
        hedef.write_bytes(dosya.read_bytes())
    except OSError:
        return None

    _eski_yedekleri_temizle(dosya.name, saklanacak)
    return hedef


def yedekleri_listele(dosya_adi: str) -> list[Path]:
    """Bir veri dosyasının yedeklerini en yeniden en eskiye sıralar."""
    if not YEDEK_DIZINI.exists():
        return []
    try:
        adaylar = list(YEDEK_DIZINI.glob(f"{dosya_adi}.*{YEDEK_UZANTISI}"))
    except OSError:
        return []
    # Ad içindeki zaman damgası sabit genişlikte, sözlük sırası kronolojik.
    return sorted(adaylar, key=lambda yol: yol.name, reverse=True)


def _bos_hedef(dosya_adi: str, damga: str) -> Path:
    """Üzerine yazmayacak bir yedek adı üretir.

    Zaman damgası saniye çözünürlüklü. Aynı saniye içinde iki destrüktif
    işlem yapılırsa (üst üste iki silme) ikinci yedek birincinin üzerine
    yazardı; `_2`, `_3` ... soneki ikisini de korur. Sonek `.` yerine `_`
    çünkü `_` sıralamada `.`ten sonra gelir ve `yedekleri_listele`nin ada
    dayalı kronolojisi bozulmaz.
    """
    hedef = YEDEK_DIZINI / f"{dosya_adi}.{damga}{YEDEK_UZANTISI}"
    if not hedef.exists():
        return hedef

    for sira in range(2, 100):
        aday = YEDEK_DIZINI / f"{dosya_adi}.{damga}_{sira}{YEDEK_UZANTISI}"
        if not aday.exists():
            return aday

    # Aynı saniyede 99 yedek: pratikte imkânsız, yine de bir ad döndür.
    return hedef


def _eski_yedekleri_temizle(dosya_adi: str, saklanacak: int) -> None:
    """Sınırı aşan en eski yedekleri siler."""
    if saklanacak <= 0:
        return
    for eski in yedekleri_listele(dosya_adi)[saklanacak:]:
        try:
            eski.unlink()
        except OSError:
            # Silinemeyen yedek zararsız; yer kaplar, veri kaybettirmez.
            pass
