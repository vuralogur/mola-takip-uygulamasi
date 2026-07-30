"""JSON okuma/yazma katmanı.

Eski sürümdeki üç problemi çözer:

1. Hiçbir `open()` çağrısında `encoding=` yoktu. Windows'ta bu cp1252
   demek, yani Türkçe karakterler (ş, ğ, ı, ö, ü, ç) bozuluyordu.
   Burada her okuma ve yazma UTF-8.
2. Hiç `try/except` yoktu. Bozuk veya eksik dosya traceback ile çökme
   üretiyordu. Burada bozuk dosya kenara alınır, çağırana `VeriBozuk`
   fırlatılır ve mevcut veri asla üzerine yazılmaz.
3. `json.dump` doğrudan hedef dosyaya yazıyordu. Yazma ortasında çökme
   dosyayı yarım bırakırdı. Burada geçici dosyaya yazılıp `os.replace`
   ile atomik olarak taşınır.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DOSYA_ADI_ZAMAN_FORMATI


class DepolamaHatasi(Exception):
    """Depolama katmanının taban hatası."""


class VeriBozuk(DepolamaHatasi):
    """Dosya okunabildi ama içeriği geçerli JSON değil.

    Bozuk dosya kenara alınmıştır; `kenara_alinan` yeni yolu tutar
    (yeniden adlandırma başarısızsa None).
    """

    def __init__(self, dosya: Path, sebep: str, kenara_alinan: Path | None) -> None:
        super().__init__(f"{dosya.name}: {sebep}")
        self.dosya = dosya
        self.sebep = sebep
        self.kenara_alinan = kenara_alinan


class YazmaHatasi(DepolamaHatasi):
    """Dosya yazılamadı. Mevcut dosya değişmemiştir."""

    def __init__(self, dosya: Path, sebep: str) -> None:
        super().__init__(f"{dosya.name}: {sebep}")
        self.dosya = dosya
        self.sebep = sebep


def json_oku(dosya: Path, varsayilan: Any) -> Any:
    """Dosyayı UTF-8 olarak okur ve JSON çözer.

    Dosya yoksa veya boşsa `varsayilan` döner — bu normal bir ilk çalıştırma
    durumu, hata değil. Dosya var ama içeriği bozuksa dosya kenara alınır ve
    `VeriBozuk` fırlatılır; orijinal içerik silinmez.
    """
    if not dosya.exists():
        return varsayilan

    try:
        ham = dosya.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Eski sürüm cp1252 ile yazmış olabilir. Veri kaybetmemek için
        # tolere ederek oku; bir sonraki yazmada UTF-8'e dönecek.
        try:
            ham = dosya.read_text(encoding="utf-8", errors="replace")
        except OSError as hata:
            raise VeriBozuk(dosya, str(hata), None) from hata
    except OSError as hata:
        raise VeriBozuk(dosya, str(hata), None) from hata

    if not ham.strip():
        return varsayilan

    try:
        return json.loads(ham)
    except json.JSONDecodeError as hata:
        kenara = _bozuk_dosyayi_kenara_al(dosya)
        raise VeriBozuk(dosya, f"gecersiz JSON (satir {hata.lineno})", kenara) from hata


def json_yaz(dosya: Path, veri: Any) -> None:
    """JSON'u atomik ve UTF-8 olarak yazar.

    Önce aynı dizinde geçici dosyaya yazar, diske senkronize eder, sonra
    `os.replace` ile hedefin üzerine taşır. Bu işlem sırasında çökme olursa
    hedef dosya ya eski ya yeni haliyle kalır, asla yarım kalmaz.

    `ensure_ascii=False` Türkçe karakterlerin kaçış dizisi yerine okunabilir
    şekilde yazılmasını sağlar.
    """
    try:
        dosya.parent.mkdir(parents=True, exist_ok=True)
    except OSError as hata:
        raise YazmaHatasi(dosya, str(hata)) from hata

    gecici: Path | None = None
    try:
        tanitici, gecici_ad = tempfile.mkstemp(
            dir=str(dosya.parent), prefix=f".{dosya.name}.", suffix=".tmp"
        )
        gecici = Path(gecici_ad)
        with os.fdopen(tanitici, "w", encoding="utf-8") as akis:
            json.dump(veri, akis, ensure_ascii=False, indent=2)
            akis.flush()
            os.fsync(akis.fileno())
        os.replace(gecici, dosya)
        gecici = None
    except (OSError, TypeError, ValueError) as hata:
        raise YazmaHatasi(dosya, str(hata)) from hata
    finally:
        if gecici is not None:
            try:
                gecici.unlink(missing_ok=True)
            except OSError:
                pass


def _bozuk_dosyayi_kenara_al(dosya: Path) -> Path | None:
    """Bozuk dosyayı zaman damgalı bir adla yeniden adlandırır.

    Üzerine yazmak yerine kenara almak, kullanıcının veriyi elle
    kurtarabilmesini sağlar. Yeniden adlandırma başarısız olursa None
    döner ve dosya olduğu yerde bırakılır.
    """
    damga = datetime.now().strftime(DOSYA_ADI_ZAMAN_FORMATI)
    hedef = dosya.with_name(f"{dosya.name}.bozuk-{damga}")
    try:
        os.replace(dosya, hedef)
    except OSError:
        return None
    return hedef
