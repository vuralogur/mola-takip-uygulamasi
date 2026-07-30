"""Ana pencere ve uygulama orkestrasyonu.

Panellerden gelen kullanıcı eylemlerini servislere iletir, sonuçları
panellere yansıtır. Veri katmanına doğrudan dokunmaz.

Canlı sayaç `after(1000, ...)` ile çalışır. Ayrı bir iş parçacığı
kullanılmaz: Tkinter thread-safe değildir ve widget'lara ana döngü dışından
dokunmak rastgele çökmelere yol açar.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config import MOLA_NOTU_MAX_UZUNLUK, UYGULAMA_ADI, VARSAYILAN_AYARLAR
from i18n import Metin
from models import Ayarlar, MolaTipi, saat_metni
from repository import (
    AktifMolaDeposu,
    AyarDeposu,
    CalisanDeposu,
    MolaDeposu,
    UyariKutusu,
)
from services.break_service import LimitDurumu, MolaServisi
from services.employee_service import CalisanServisi
from services.report_service import RaporServisi, csv_disa_aktar, tip_dagilimi
from ui import theme
from ui.dialogs import (
    AyarlarPenceresi,
    GrafikPenceresi,
    NotPenceresi,
    TumCalisanlarPenceresi,
)
from ui.panels import CalisanPaneli, GecmisPaneli, MolaPaneli

SAYAC_ARALIGI_MS = 1000

try:  # Windows dışında winsound yoktur; ses opsiyonel bir ek.
    import winsound
except ImportError:  # pragma: no cover - platforma bağlı
    winsound = None  # type: ignore[assignment]


class MolaTakipUygulamasi(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self._uyarilar = UyariKutusu()
        self._calisan_deposu = CalisanDeposu(self._uyarilar)
        self._mola_deposu = MolaDeposu(self._uyarilar)
        self._aktif_deposu = AktifMolaDeposu(self._uyarilar)
        self._ayar_deposu = AyarDeposu(self._uyarilar)

        self._calisan_servisi = CalisanServisi(
            self._calisan_deposu, self._mola_deposu, self._aktif_deposu
        )
        self._mola_servisi = MolaServisi(
            self._mola_deposu, self._aktif_deposu, self._ayar_deposu
        )
        self._rapor_servisi = RaporServisi(self._mola_deposu, self._ayar_deposu)

        # Limit aşımı sesi çalışan başına yalnızca bir kez çalsın.
        self._sesi_calinan: set[str] = set()
        self._sayac_isi: str | None = None

        ayarlar = self._ayar_deposu.oku()
        self._pencereyi_kur(ayarlar)
        theme.tema_uygula(self, ayarlar.tema)
        self._arayuzu_kur()

        self._verileri_yukle()
        self._bekleyen_uyarilari_goster()
        self._eski_molalari_kurtar()
        self._tik()

    # --- Kurulum ---

    def _pencereyi_kur(self, ayarlar: Ayarlar) -> None:
        self.title(UYGULAMA_ADI)
        self.geometry(ayarlar.pencere_boyutu or VARSAYILAN_AYARLAR["pencere_boyutu"])
        self.minsize(880, 580)
        self.protocol("WM_DELETE_WINDOW", self._kapat)

    def _arayuzu_kur(self) -> None:
        self.columnconfigure(0, weight=0, minsize=250)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)

        ust_serit = ttk.Frame(self, padding=(theme.M, theme.S))
        ust_serit.grid(row=0, column=0, columnspan=3, sticky=tk.EW)
        ust_serit.columnconfigure(0, weight=1)

        ttk.Label(ust_serit, text=UYGULAMA_ADI, style="Baslik.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Button(ust_serit, text=Metin.AYAR_TEMA, command=self._temayi_degistir).grid(
            row=0, column=1, padx=(0, theme.S)
        )
        ttk.Button(ust_serit, text=Metin.BASLIK_AYARLAR, command=self._ayarlari_ac).grid(
            row=0, column=2
        )

        self._calisan_paneli = CalisanPaneli(
            self,
            ekle_geri=self._calisan_ekle,
            sil_geri=self._calisan_sil,
            secim_geri=self._secim_degisti,
        )
        self._calisan_paneli.grid(row=1, column=0, sticky=tk.NSEW)

        ttk.Separator(self, orient=tk.VERTICAL).grid(row=1, column=1, sticky=tk.NS)

        sag = ttk.Frame(self)
        sag.grid(row=1, column=2, sticky=tk.NSEW)
        sag.columnconfigure(0, weight=1)
        sag.rowconfigure(2, weight=1)

        self._mola_paneli = MolaPaneli(
            sag, basla_geri=self._molayi_baslat, bitir_geri=self._molayi_bitir
        )
        self._mola_paneli.grid(row=0, column=0, sticky=tk.EW)

        ttk.Separator(sag, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky=tk.EW, padx=theme.L
        )

        self._gecmis_paneli = GecmisPaneli(
            sag,
            donem_geri=self._gecmisi_yenile,
            sil_geri=self._secili_molalari_sil,
            hepsini_sil_geri=self._tum_molalari_sil,
            disa_aktar_geri=self._csv_disa_aktar,
            grafik_geri=self._grafigi_ac,
            tum_calisanlar_geri=self._tum_calisanlari_ac,
            not_geri=self._mola_notunu_duzenle,
        )
        self._gecmis_paneli.grid(row=2, column=0, sticky=tk.NSEW)

        self._durum_cubugu = ttk.Label(
            self,
            text=Metin.DURUM_HAZIR,
            font=theme.ALT_BASLIK_FONT,
            foreground=theme.RENK_SOLUK,
            padding=(theme.M, theme.XS),
        )
        self._durum_cubugu.grid(row=2, column=0, columnspan=3, sticky=tk.EW)

        self._calisan_paneli.odagi_girise_ver()

    # --- Veri akışı ---

    def _verileri_yukle(self) -> None:
        self._calisan_paneli.yenile(
            self._calisan_servisi.liste(), self._mola_servisi.aktif_molalar()
        )
        self._gecmisi_yenile()

    def _secili_calisan(self) -> str | None:
        return self._calisan_paneli.secili()

    def _secim_degisti(self) -> None:
        self._gecmisi_yenile()
        self._paneli_guncelle()

    def _gecmisi_yenile(self) -> None:
        calisan = self._secili_calisan()
        donem = self._gecmis_paneli.secili_donem()
        if calisan is None:
            self._gecmis_paneli.yenile([], self._rapor_servisi.ozet("", donem))
            return
        kayitlar = self._rapor_servisi.kayitlar(calisan, donem)
        self._gecmis_paneli.yenile(kayitlar, self._rapor_servisi.ozet(calisan, donem))

    def _paneli_guncelle(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            self._mola_paneli.guncelle(
                calisan=None,
                gecen_saniye=None,
                aktif_tip=None,
                limit_durumu=LimitDurumu.NORMAL,
                limit_saniye=0,
                bugun_toplam=0,
                kalan_hak=None,
            )
            return

        aktif = self._mola_servisi.aktif_mola(calisan)
        durum, limit = self._mola_servisi.limit_durumu(calisan)

        self._mola_paneli.guncelle(
            calisan=calisan,
            gecen_saniye=aktif.gecen_saniye() if aktif else None,
            aktif_tip=aktif.tip if aktif else None,
            limit_durumu=durum,
            limit_saniye=limit,
            bugun_toplam=self._mola_servisi.bugunku_toplam_saniye(calisan),
            kalan_hak=self._mola_servisi.gunluk_kalan_saniye(calisan),
        )

        self._limit_sesini_yonet(calisan, durum)

    # --- Canlı sayaç ---

    def _tik(self) -> None:
        """Saniyede bir sayacı tazeler.

        Sol liste burada yeniden kurulmaz: her saniye yeniden doldurmak
        seçimi ve kaydırma konumunu bozar. Liste yalnızca mola başlayınca
        veya bitince yenilenir.
        """
        self._paneli_guncelle()
        self._sayac_isi = self.after(SAYAC_ARALIGI_MS, self._tik)

    def _limit_sesini_yonet(self, calisan: str, durum: LimitDurumu) -> None:
        if durum is not LimitDurumu.ASILDI:
            self._sesi_calinan.discard(calisan)
            return

        if calisan in self._sesi_calinan:
            return

        self._sesi_calinan.add(calisan)
        if winsound is not None and self._ayar_deposu.oku().ses_acik:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except RuntimeError:
                pass

    # --- Çalışan eylemleri ---

    def _calisan_ekle(self, ham_ad: str) -> None:
        basarili, mesaj = self._calisan_servisi.ekle(ham_ad)
        if not basarili:
            messagebox.showerror(Metin.BASLIK_HATA, mesaj, parent=self)
            self._bekleyen_uyarilari_goster()
            return

        self._calisan_paneli.girisi_temizle()
        self._verileri_yukle()
        self._durumu_yaz(mesaj)
        self._bekleyen_uyarilari_goster()

    def _calisan_sil(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        if not messagebox.askyesno(
            Metin.BASLIK_ONAY,
            Metin.CALISAN_SILME_ONAY.format(ad=calisan),
            parent=self,
            icon=messagebox.WARNING,
        ):
            return

        basarili, mesaj = self._calisan_servisi.sil(calisan)
        if not basarili:
            messagebox.showerror(Metin.BASLIK_HATA, mesaj, parent=self)
        else:
            self._durumu_yaz(mesaj)

        self._verileri_yukle()
        self._paneli_guncelle()
        self._bekleyen_uyarilari_goster()

    # --- Mola eylemleri ---

    def _molayi_baslat(self, tip: MolaTipi) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        basarili, mesaj = self._mola_servisi.basla(calisan, tip)
        if not basarili:
            messagebox.showwarning(Metin.BASLIK_UYARI, mesaj, parent=self)
        else:
            self._durumu_yaz(mesaj)

        self._calisan_paneli.yenile(
            self._calisan_servisi.liste(), self._mola_servisi.aktif_molalar()
        )
        self._paneli_guncelle()
        self._bekleyen_uyarilari_goster()

    def _molayi_bitir(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        basarili, mesaj, _kayit = self._mola_servisi.bitir(calisan)
        if not basarili:
            messagebox.showwarning(Metin.BASLIK_UYARI, mesaj, parent=self)
        else:
            self._durumu_yaz(mesaj)

        self._sesi_calinan.discard(calisan)
        self._verileri_yukle()
        self._paneli_guncelle()
        self._bekleyen_uyarilari_goster()

    def _secili_molalari_sil(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        kimlikler = self._gecmis_paneli.secili_kimlikler()
        if not kimlikler:
            messagebox.showinfo(Metin.BASLIK_BILGI, Metin.MOLA_SECILMEDI, parent=self)
            return

        if not messagebox.askyesno(
            Metin.BASLIK_ONAY,
            Metin.MOLA_SIL_ONAY.format(sayi=len(kimlikler)),
            parent=self,
            icon=messagebox.WARNING,
        ):
            return

        silinen = self._mola_deposu.sil(calisan, kimlikler)
        self._durumu_yaz(Metin.MOLA_SILINDI.format(sayi=silinen))
        self._gecmisi_yenile()
        self._paneli_guncelle()
        self._bekleyen_uyarilari_goster()

    def _tum_molalari_sil(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        if not self._mola_deposu.molalar(calisan):
            messagebox.showinfo(Metin.BASLIK_BILGI, Metin.MOLA_YOK, parent=self)
            return

        if not messagebox.askyesno(
            Metin.BASLIK_ONAY,
            Metin.MOLA_HEPSINI_SIL_ONAY.format(ad=calisan),
            parent=self,
            icon=messagebox.WARNING,
        ):
            return

        silinen = self._mola_deposu.hepsini_sil(calisan)
        self._durumu_yaz(Metin.MOLA_SILINDI.format(sayi=silinen))
        self._gecmisi_yenile()
        self._paneli_guncelle()
        self._bekleyen_uyarilari_goster()

    # --- Mola notu ---

    def _mola_notunu_duzenle(self, kimlik: str | None = None) -> None:
        """Not penceresini açar.

        `kimlik` tabloda çift tıklanan satırdan gelir. Düğmeden çağrıldığında
        None'dır; o durumda seçim kullanılır ve tek kayıt şartı aranır, çünkü
        bir not birden çok kayda birlikte yazılmaz.
        """
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        if kimlik is None:
            secili = self._gecmis_paneli.secili_kimlikler()
            if len(secili) != 1:
                messagebox.showinfo(
                    Metin.BASLIK_BILGI, Metin.NOT_TEK_KAYIT, parent=self
                )
                return
            kimlik = next(iter(secili))

        mevcut = self._mola_servisi.not_oku(calisan, kimlik)
        if mevcut is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.NOT_KAYIT_BULUNAMADI, parent=self
            )
            return

        secili_kimlik = kimlik
        NotPenceresi(
            self,
            mevcut,
            MOLA_NOTU_MAX_UZUNLUK,
            lambda yeni_not: self._notu_kaydet(calisan, secili_kimlik, yeni_not),
        )

    def _notu_kaydet(self, calisan: str, kimlik: str, aciklama: str) -> bool:
        """Notu servise verir. Başarısızsa pencere açık kalsın diye False döner."""
        basarili, mesaj = self._mola_servisi.not_kaydet(calisan, kimlik, aciklama)
        if not basarili:
            messagebox.showerror(Metin.BASLIK_HATA, mesaj, parent=self)
            self._bekleyen_uyarilari_goster()
            return False

        self._durumu_yaz(mesaj)
        self._gecmisi_yenile()
        self._bekleyen_uyarilari_goster()
        return True

    # --- Raporlama ---

    def _csv_disa_aktar(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        donem = self._gecmis_paneli.secili_donem()
        kayitlar = self._rapor_servisi.kayitlar(calisan, donem)
        if not kayitlar:
            messagebox.showinfo(Metin.BASLIK_BILGI, Metin.RAPOR_VERI_YOK, parent=self)
            return

        varsayilan_ad = f"{calisan}_{donem.value}_{datetime.now():%Y%m%d}.csv"
        yol = filedialog.asksaveasfilename(
            parent=self,
            title=Metin.DISA_AKTAR_BASLIK,
            defaultextension=".csv",
            initialfile=varsayilan_ad,
            filetypes=[("CSV", "*.csv")],
        )
        if not yol:
            return

        basarili, mesaj = csv_disa_aktar(Path(yol), calisan, kayitlar)
        if basarili:
            messagebox.showinfo(Metin.BASLIK_BILGI, mesaj, parent=self)
            self._durumu_yaz(Metin.RAPOR_DISA_AKTAR)
        else:
            messagebox.showerror(Metin.BASLIK_HATA, mesaj, parent=self)

    def _grafigi_ac(self) -> None:
        calisan = self._secili_calisan()
        if calisan is None:
            messagebox.showwarning(
                Metin.BASLIK_UYARI, Metin.CALISAN_SECILMEDI, parent=self
            )
            return

        donem = self._gecmis_paneli.secili_donem()
        kayitlar = self._rapor_servisi.kayitlar(calisan, donem)
        if not kayitlar:
            messagebox.showinfo(Metin.BASLIK_BILGI, Metin.RAPOR_VERI_YOK, parent=self)
            return

        gunluk = [
            (gun.strftime("%d.%m"), saniye)
            for gun, saniye in self._rapor_servisi.gunluk_dagilim(calisan, donem)
        ]
        tipler = [(tip.etiket, saniye) for tip, saniye in tip_dagilimi(kayitlar).items()]
        GrafikPenceresi(self, f"{calisan} — {donem.etiket}", gunluk, tipler)

    def _tum_calisanlari_ac(self) -> None:
        donem = self._gecmis_paneli.secili_donem()
        TumCalisanlarPenceresi(self, donem, self._rapor_servisi.tum_calisanlar(donem))

    # --- Ayarlar ve tema ---

    def _ayarlari_ac(self) -> None:
        AyarlarPenceresi(self, self._ayar_deposu.oku(), self._ayarlari_kaydet)

    def _ayarlari_kaydet(self, yeni: Ayarlar) -> bool:
        # Pencere boyutu ayar penceresinde düzenlenmez; mevcut değeri koru.
        yeni.pencere_boyutu = self._ayar_deposu.oku().pencere_boyutu
        if not self._ayar_deposu.yaz(yeni):
            self._bekleyen_uyarilari_goster()
            return False

        theme.tema_uygula(self, yeni.tema)
        self._durumu_yaz(Metin.AYAR_KAYDEDILDI)
        self._paneli_guncelle()
        self._gecmisi_yenile()
        return True

    def _temayi_degistir(self) -> None:
        yeni_tema = theme.tema_degistir(self)
        ayarlar = self._ayar_deposu.oku()
        ayarlar.tema = yeni_tema
        self._ayar_deposu.yaz(ayarlar)

    # --- Açılışta kurtarma ---

    def _eski_molalari_kurtar(self) -> None:
        """Vardiya süresinden uzun süredir açık molaları kullanıcıya sorar.

        Uygulama mola sırasında kapanmışsa (çökme, elektrik kesintisi)
        `active_breaks.json` içinde açık kayıt kalır. Sessizce bitirmek
        yanlış süre üretir, sessizce silmek veri kaybettirir — karar
        kullanıcınındır.
        """
        vardiya_saniye = self._ayar_deposu.oku().vardiya_saati * 3600
        simdi = datetime.now()

        for calisan, mola in list(self._mola_servisi.aktif_molalar().items()):
            gecen = mola.gecen_saniye(simdi)
            if gecen <= vardiya_saniye:
                continue

            bitir = messagebox.askyesno(
                Metin.ESKI_MOLA_BASLIK,
                Metin.ESKI_MOLA_SORU.format(ad=calisan, sure=saat_metni(gecen)),
                parent=self,
                icon=messagebox.WARNING,
            )
            if bitir:
                self._mola_servisi.bitir(calisan)
            else:
                self._mola_servisi.iptal(calisan)

        self._verileri_yukle()
        self._bekleyen_uyarilari_goster()

    # --- Ortak yardımcılar ---

    def _durumu_yaz(self, mesaj: str) -> None:
        """Alt durum çubuğuna yazar.

        Başarılı işlemler için `messagebox` yerine bu kullanılır: her
        eylemde pencere açmak akışı gereksiz yere kesiyordu.
        """
        self._durum_cubugu.configure(text=mesaj)

    def _bekleyen_uyarilari_goster(self) -> None:
        """Depo katmanında biriken uyarıları tek tek gösterir."""
        for uyari in self._uyarilar.bosalt():
            goster = messagebox.showerror if uyari.kritik else messagebox.showinfo
            goster(uyari.baslik, uyari.mesaj, parent=self)

    def _kapat(self) -> None:
        """Pencere boyutunu kaydeder ve sayaç işini iptal ederek kapanır."""
        if self._sayac_isi is not None:
            try:
                self.after_cancel(self._sayac_isi)
            except tk.TclError:
                pass

        ayarlar = self._ayar_deposu.oku()
        ayarlar.pencere_boyutu = f"{self.winfo_width()}x{self.winfo_height()}"
        self._ayar_deposu.yaz(ayarlar)

        self.destroy()
