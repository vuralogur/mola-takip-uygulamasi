"""Şema göçleri.

v1 (eski): `break_data.json` kökü doğrudan çalışan sözlüğüydü.

    {"Ada": [{"start_time": ..., "end_time": ...,
              "duration_minutes": 12, "duration_seconds": 30}]}

v2 (güncel): sürüm bilgisi taşıyan sarmalayıcı, kayıt başına `id`,
`break_type` ve `note` alanları eklendi.

    {"schema_version": 2,
     "breaks": {"Ada": [{"id": "a3f1c9", "start_time": ..., "end_time": ...,
                         "duration_minutes": 12, "duration_seconds": 30,
                         "break_type": "diger", "note": ""}]}}

Kural: mevcut dört alan asla silinmez veya yeniden adlandırılmaz. Eski
kayıtlar eksik alanları varsayılan değerlerle alır. Dönüşüm çağıran
tarafından yedek alındıktan sonra yapılır.
"""

from __future__ import annotations

from typing import Any

from config import SEMA_SURUMU
from models import MolaTipi, yeni_kimlik

BOS_V2: dict[str, Any] = {"schema_version": SEMA_SURUMU, "breaks": {}}


def sema_surumu_tespit_et(ham: Any) -> int:
    """Ham JSON'un şema sürümünü belirler.

    `schema_version` anahtarı yoksa v1 kabul edilir — v1'de böyle bir
    anahtar hiç yoktu, kök seviyedeki her anahtar bir çalışan adıydı.
    Tanınmayan yapı için 0 döner.
    """
    if not isinstance(ham, dict):
        return 0
    surum = ham.get("schema_version")
    if isinstance(surum, int):
        return surum
    return 1


def v2ye_yukselt(ham: Any) -> tuple[dict[str, Any], bool]:
    """Ham JSON'u v2 biçimine getirir.

    `(veri, degisti_mi)` döner. `degisti_mi` True ise çağıran sonucu diske
    yazmalıdır. Tanınmayan yapı boş v2 ile sonuçlanır — bu durumda çağıran
    önce yedek almış olmalıdır.
    """
    surum = sema_surumu_tespit_et(ham)

    if surum >= SEMA_SURUMU:
        return _v2_dogrula(ham), False

    if surum <= 0:
        return dict(BOS_V2), True

    return _v1den_v2ye(ham), True


def _v1den_v2ye(ham: dict[str, Any]) -> dict[str, Any]:
    """v1 sözlüğünü v2 sarmalayıcısına taşır ve eksik alanları doldurur."""
    molalar: dict[str, list[dict[str, Any]]] = {}

    for calisan, kayitlar in ham.items():
        if not isinstance(calisan, str) or not isinstance(kayitlar, list):
            continue
        molalar[calisan] = [
            _kaydi_zenginlestir(kayit) for kayit in kayitlar if isinstance(kayit, dict)
        ]

    return {"schema_version": SEMA_SURUMU, "breaks": molalar}


def _kaydi_zenginlestir(kayit: dict[str, Any]) -> dict[str, Any]:
    """v1 kaydına v2 alanlarını ekler. Mevcut alanlara dokunmaz."""
    yeni = dict(kayit)
    yeni.setdefault("id", yeni_kimlik())
    yeni.setdefault("break_type", MolaTipi.DIGER.value)
    yeni.setdefault("note", "")
    return yeni


def _v2_dogrula(ham: dict[str, Any]) -> dict[str, Any]:
    """Zaten v2 olan veriyi yapısal olarak güvenli hale getirir.

    Elle düzenlenmiş bir dosyada `breaks` eksik veya yanlış tipte olabilir;
    bu durumda çökmek yerine boş sözlükle devam edilir.
    """
    molalar = ham.get("breaks")
    if not isinstance(molalar, dict):
        molalar = {}
    return {"schema_version": SEMA_SURUMU, "breaks": molalar}
