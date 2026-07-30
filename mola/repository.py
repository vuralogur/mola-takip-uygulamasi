"""Depo katmanı — JSON dosyaları ile domain nesneleri arasındaki köprü.

`storage.py` ham JSON okur/yazar; burada o veri `models.py` nesnelerine
dönüşür, önbellekte tutulur ve doğrulanır.

İki tasarım kuralı:

1. **Veri her işlemde diskten okunmaz.** Eski sürümde `save_break_data`,
   `load_break_data` ve `delete_break_data` her çağrıda tüm dosyayı
   yeniden okuyordu. Burada ilk okumadan sonra bellek önbelleği kullanılır.
2. **Yazma başarısızsa bellek geri alınır.** Diske yazılamayan bir
   değişiklik bellekte kalırsa arayüz gerçekte olmayan bir durumu gösterir.
   Her mutasyon önce uygulanır, yazma başarısızsa eski hale döndürülür.

Depolar arayüze bağlı değildir. Kullanıcıya gösterilecek durumlar
`UyariKutusu` içinde biriktirilir, arayüz uygun bir anda okur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import backup
import migrations
import storage
from config import AKTIF_MOLA_DOSYASI, AYAR_DOSYASI, CALISAN_DOSYASI, MOLA_DOSYASI
from i18n import Metin
from models import AktifMola, Ayarlar, MolaKaydi, MolaTipi


@dataclass
class Uyari:
    """Kullanıcıya gösterilmeyi bekleyen tek bir mesaj."""

    baslik: str
    mesaj: str
    kritik: bool = False


@dataclass
class UyariKutusu:
    """Depoların ürettiği uyarılar burada birikir, arayüz boşaltır.

    Depo katmanının `messagebox` çağırmaması için var: veri katmanı
    arayüzü tanımaz, sadece ne olduğunu bildirir.
    """

    _liste: list[Uyari] = field(default_factory=list)

    def ekle(self, baslik: str, mesaj: str, kritik: bool = False) -> None:
        self._liste.append(Uyari(baslik=baslik, mesaj=mesaj, kritik=kritik))

    def bosalt(self) -> list[Uyari]:
        """Biriken uyarıları döndürür ve kutuyu temizler."""
        uyarilar = list(self._liste)
        self._liste.clear()
        return uyarilar

    def bos_mu(self) -> bool:
        return not self._liste


class _Depo:
    """Ortak yükleme ve hata bildirme davranışı."""

    def __init__(self, uyarilar: UyariKutusu) -> None:
        self._uyarilar = uyarilar

    def _guvenli_oku(self, dosya: Path, varsayilan: Any) -> Any:
        """Okur; dosya bozuksa uyarı bırakıp varsayılanla devam eder."""
        try:
            return storage.json_oku(dosya, varsayilan)
        except storage.VeriBozuk as hata:
            if hata.kenara_alinan is not None:
                mesaj = Metin.VERI_BOZUK.format(
                    dosya=dosya.name,
                    sebep=hata.sebep,
                    kenara=hata.kenara_alinan.name,
                )
            else:
                mesaj = Metin.VERI_BOZUK_TASINAMADI.format(
                    dosya=dosya.name, sebep=hata.sebep
                )
            self._uyarilar.ekle(Metin.BASLIK_UYARI, mesaj, kritik=True)
            return varsayilan

    def _destruktif_yedek(self, dosya: Path) -> None:
        """Geri alınamaz bir değişiklikten önce sessiz yedek alır.

        Yedekleme kritik yol değil: başarısız olursa `backup.yedek_al` None
        döner ve işlem yine sürer. Bilerek uyarı üretilmez — her silme
        işleminde pencere açmak akışı boğardı, göç yolundaki bilgilendirme
        ise tek seferliktir.
        """
        backup.yedek_al(dosya)

    def _guvenli_yaz(self, dosya: Path, veri: Any) -> bool:
        """Yazar; başarısızsa uyarı bırakıp False döner."""
        try:
            storage.json_yaz(dosya, veri)
        except storage.YazmaHatasi as hata:
            self._uyarilar.ekle(
                Metin.BASLIK_HATA,
                Metin.VERI_YAZILAMADI.format(dosya=dosya.name, sebep=hata.sebep),
                kritik=True,
            )
            return False
        return True


class CalisanDeposu(_Depo):
    """`employees.json` — düz string listesi. Şema v1'den beri değişmedi."""

    def __init__(self, uyarilar: UyariKutusu) -> None:
        super().__init__(uyarilar)
        self._liste: list[str] = []
        self._yuklendi = False

    def yukle(self) -> None:
        ham = self._guvenli_oku(CALISAN_DOSYASI, [])
        if isinstance(ham, list):
            # Yalnızca boş olmayan string'ler; sıra korunur, tekrarlar atılır.
            gorulen: set[str] = set()
            temiz: list[str] = []
            for oge in ham:
                if isinstance(oge, str) and oge.strip() and oge not in gorulen:
                    gorulen.add(oge)
                    temiz.append(oge)
            self._liste = temiz
        else:
            self._liste = []
        self._yuklendi = True

    def liste(self) -> list[str]:
        if not self._yuklendi:
            self.yukle()
        return list(self._liste)

    def var_mi(self, ad: str) -> bool:
        return ad in self.liste()

    def ekle(self, ad: str) -> bool:
        onceki = self.liste()
        if ad in onceki:
            return False
        yeni = onceki + [ad]
        if not self._guvenli_yaz(CALISAN_DOSYASI, yeni):
            return False
        self._liste = yeni
        return True

    def sil(self, ad: str) -> bool:
        onceki = self.liste()
        if ad not in onceki:
            return False
        yeni = [mevcut for mevcut in onceki if mevcut != ad]
        self._destruktif_yedek(CALISAN_DOSYASI)
        if not self._guvenli_yaz(CALISAN_DOSYASI, yeni):
            return False
        self._liste = yeni
        return True


class MolaDeposu(_Depo):
    """`break_data.json` — tamamlanmış mola kayıtları.

    Yükleme sırasında gerekiyorsa v1'den v2'ye göç uygulanır. Göç öncesi
    her zaman yedek alınır.
    """

    def __init__(self, uyarilar: UyariKutusu) -> None:
        super().__init__(uyarilar)
        self._veri: dict[str, list[MolaKaydi]] = {}
        self._yuklendi = False

    def yukle(self) -> None:
        ham = self._guvenli_oku(MOLA_DOSYASI, dict(migrations.BOS_V2))
        yukseltildi, degisti = migrations.v2ye_yukselt(ham)

        if degisti and MOLA_DOSYASI.exists():
            yedek = backup.yedek_al(MOLA_DOSYASI)
            if yedek is not None:
                self._uyarilar.ekle(
                    Metin.BASLIK_BILGI, Metin.GOC_YAPILDI.format(yedek=yedek.name)
                )

        self._veri = {}
        atlanan = 0
        for calisan, kayitlar in yukseltildi["breaks"].items():
            if not isinstance(calisan, str) or not isinstance(kayitlar, list):
                continue
            cozulen: list[MolaKaydi] = []
            for ham_kayit in kayitlar:
                kayit = MolaKaydi.from_dict(ham_kayit)
                if kayit is None:
                    atlanan += 1
                else:
                    cozulen.append(kayit)
            cozulen.sort(key=lambda mola: mola.baslangic)
            self._veri[calisan] = cozulen

        if atlanan:
            self._uyarilar.ekle(
                Metin.BASLIK_UYARI, Metin.KAYIT_ATLANDI.format(sayi=atlanan)
            )

        self._yuklendi = True

        # Göç yapıldıysa veya bozuk kayıt atlandıysa temizlenmiş hali yaz.
        if degisti or atlanan:
            self._kaydet()

    def _yukle_gerekirse(self) -> None:
        if not self._yuklendi:
            self.yukle()

    def molalar(self, calisan: str) -> list[MolaKaydi]:
        self._yukle_gerekirse()
        return list(self._veri.get(calisan, []))

    def tum_veri(self) -> dict[str, list[MolaKaydi]]:
        self._yukle_gerekirse()
        return {calisan: list(kayitlar) for calisan, kayitlar in self._veri.items()}

    def ekle(self, calisan: str, kayit: MolaKaydi) -> bool:
        self._yukle_gerekirse()
        mevcut = list(self._veri.get(calisan, []))
        mevcut.append(kayit)
        mevcut.sort(key=lambda mola: mola.baslangic)
        return self._degisikligi_uygula(calisan, mevcut)

    def sil(self, calisan: str, kimlikler: set[str]) -> int:
        """Verilen kimliklere sahip kayıtları siler, silinen sayısını döner."""
        self._yukle_gerekirse()
        mevcut = self._veri.get(calisan, [])
        kalan = [kayit for kayit in mevcut if kayit.kimlik not in kimlikler]
        silinen = len(mevcut) - len(kalan)
        if silinen == 0:
            return 0
        self._destruktif_yedek(MOLA_DOSYASI)
        if not self._degisikligi_uygula(calisan, kalan):
            return 0
        return silinen

    def hepsini_sil(self, calisan: str) -> int:
        self._yukle_gerekirse()
        silinen = len(self._veri.get(calisan, []))
        if silinen == 0:
            return 0
        self._destruktif_yedek(MOLA_DOSYASI)
        if not self._degisikligi_uygula(calisan, []):
            return 0
        return silinen

    def not_guncelle(self, calisan: str, kimlik: str, aciklama: str) -> bool:
        """Tek kaydın notunu değiştirir. Kayıt yoksa veya yazma başarısızsa
        False döner ve önceki not geri konur.

        Yedek alınmaz: not eklemek veri silmez, yalnızca boş bir alanı
        doldurur veya değiştirir.
        """
        self._yukle_gerekirse()
        hedef = next(
            (
                kayit
                for kayit in self._veri.get(calisan, [])
                if kayit.kimlik == kimlik
            ),
            None,
        )
        if hedef is None:
            return False

        if hedef.aciklama == aciklama:
            return True

        onceki = hedef.aciklama
        hedef.aciklama = aciklama
        if self._kaydet():
            return True
        hedef.aciklama = onceki
        return False

    def calisani_kaldir(self, calisan: str) -> bool:
        """Çalışan silinirken mola kayıtlarını da kaldırır."""
        self._yukle_gerekirse()
        if calisan not in self._veri:
            return True
        self._destruktif_yedek(MOLA_DOSYASI)
        onceki = self._veri
        self._veri = {ad: kayitlar for ad, kayitlar in onceki.items() if ad != calisan}
        if self._kaydet():
            return True
        self._veri = onceki
        return False

    def _degisikligi_uygula(self, calisan: str, yeni_kayitlar: list[MolaKaydi]) -> bool:
        """Tek çalışanın listesini değiştirir; yazma başarısızsa geri alır."""
        onceki = self._veri.get(calisan)
        if yeni_kayitlar:
            self._veri[calisan] = yeni_kayitlar
        else:
            self._veri.pop(calisan, None)

        if self._kaydet():
            return True

        if onceki is None:
            self._veri.pop(calisan, None)
        else:
            self._veri[calisan] = onceki
        return False

    def _kaydet(self) -> bool:
        govde = {
            calisan: [kayit.to_dict() for kayit in kayitlar]
            for calisan, kayitlar in self._veri.items()
        }
        return self._guvenli_yaz(
            MOLA_DOSYASI,
            {"schema_version": migrations.SEMA_SURUMU, "breaks": govde},
        )


class AktifMolaDeposu(_Depo):
    """`active_breaks.json` — devam eden molalar.

    Eski sürümde başlangıç zamanı `break_start_time` adlı tek bir global
    değişkendeydi: aynı anda yalnızca bir mola sayılabiliyor ve uygulama
    kapanınca mola kayboluyordu. Diske yazılan bu depo iki sorunu da çözer.
    """

    def __init__(self, uyarilar: UyariKutusu) -> None:
        super().__init__(uyarilar)
        self._veri: dict[str, AktifMola] = {}
        self._yuklendi = False

    def yukle(self) -> None:
        ham = self._guvenli_oku(AKTIF_MOLA_DOSYASI, {})
        self._veri = {}
        if isinstance(ham, dict):
            for calisan, govde in ham.items():
                if not isinstance(calisan, str):
                    continue
                mola = AktifMola.from_dict(calisan, govde)
                if mola is not None:
                    self._veri[calisan] = mola
        self._yuklendi = True

    def _yukle_gerekirse(self) -> None:
        if not self._yuklendi:
            self.yukle()

    def hepsi(self) -> dict[str, AktifMola]:
        self._yukle_gerekirse()
        return dict(self._veri)

    def al(self, calisan: str) -> AktifMola | None:
        self._yukle_gerekirse()
        return self._veri.get(calisan)

    def molada_mi(self, calisan: str) -> bool:
        return self.al(calisan) is not None

    def basla(
        self, calisan: str, tip: MolaTipi, baslangic: datetime | None = None
    ) -> AktifMola | None:
        self._yukle_gerekirse()
        if calisan in self._veri:
            return None
        mola = AktifMola(calisan=calisan, baslangic=baslangic or datetime.now(), tip=tip)
        self._veri[calisan] = mola
        if self._kaydet():
            return mola
        self._veri.pop(calisan, None)
        return None

    def bitir(self, calisan: str) -> AktifMola | None:
        """Aktif molayı kaldırır ve döner. Yoksa None."""
        self._yukle_gerekirse()
        mola = self._veri.pop(calisan, None)
        if mola is None:
            return None
        if self._kaydet():
            return mola
        self._veri[calisan] = mola
        return None

    def _kaydet(self) -> bool:
        govde = {calisan: mola.to_dict() for calisan, mola in self._veri.items()}
        return self._guvenli_yaz(AKTIF_MOLA_DOSYASI, govde)


class AyarDeposu(_Depo):
    """`settings.json` — kullanıcı ayarları."""

    def __init__(self, uyarilar: UyariKutusu) -> None:
        super().__init__(uyarilar)
        self._ayarlar: Ayarlar | None = None

    def oku(self) -> Ayarlar:
        if self._ayarlar is None:
            ham = self._guvenli_oku(AYAR_DOSYASI, {})
            self._ayarlar = Ayarlar.from_dict(ham)
        return self._ayarlar

    def yaz(self, ayarlar: Ayarlar) -> bool:
        if not self._guvenli_yaz(AYAR_DOSYASI, ayarlar.to_dict()):
            return False
        self._ayarlar = ayarlar
        return True
