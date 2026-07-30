"""Ana pencerenin üç paneli: çalışan listesi, mola kontrolü, geçmiş.

Paneller veriyi kendileri okumaz ve yazmaz. Kullanıcı eylemlerini geri
çağırma (callback) ile `MolaTakipUygulamasi`'na bildirir, o da servisleri
çağırır ve panelleri günceller. Böylece arayüz ile iş mantığı ayrık kalır.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from i18n import Metin
from models import AktifMola, MolaKaydi, MolaTipi, saat_metni
from services.break_service import LimitDurumu
from services.report_service import Donem, Ozet
from ui import theme


class CalisanPaneli(ttk.Frame):
    """Sol panel: çalışan listesi, ekleme ve silme.

    Eski sürümdeki `ttk.OptionMenu` yerine `Treeview` kullanılır. Menü
    kapalıyken kimin molada olduğu görünmüyordu; liste her zaman açık ve
    molada olanları işaretli gösteriyor.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        ekle_geri: Callable[[str], None],
        sil_geri: Callable[[], None],
        secim_geri: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=(theme.M, theme.M))
        self._ekle_geri = ekle_geri
        self._sil_geri = sil_geri
        self._secim_geri = secim_geri

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text=Metin.BASLIK_CALISANLAR, style="Bolum.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, theme.S)
        )

        self._liste = ttk.Treeview(
            self, columns=("durum",), show="tree headings", selectmode="browse"
        )
        # Başlıklar boş bırakılırsa sv-ttk iki boş kutu çizer; gerçek
        # etiket vermek hem o boşluğu doldurur hem sütunları açıklar.
        self._liste.heading("#0", text=Metin.SUTUN_CALISAN)
        self._liste.heading("durum", text=Metin.SUTUN_DURUM)
        self._liste.column("#0", width=150, minwidth=110, stretch=True)
        self._liste.column("durum", width=70, minwidth=60, stretch=False, anchor=tk.E)
        self._liste.grid(row=1, column=0, sticky=tk.NSEW)
        self._liste.bind("<<TreeviewSelect>>", lambda *_: self._secim_geri())

        # Molada olan satırlar renkle ayrılır; yalnızca renge güvenmemek
        # için ayrıca "molada" metni de yazılır.
        self._liste.tag_configure("molada", foreground=theme.RENK_NORMAL)

        kaydirma = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._liste.yview)
        self._liste.configure(yscrollcommand=kaydirma.set)
        kaydirma.grid(row=1, column=1, sticky=tk.NS)

        giris_cerceve = ttk.Frame(self)
        giris_cerceve.grid(
            row=2, column=0, columnspan=2, sticky=tk.EW, pady=(theme.M, 0)
        )
        giris_cerceve.columnconfigure(0, weight=1)

        self._ad_girisi = ttk.Entry(giris_cerceve)
        self._ad_girisi.grid(row=0, column=0, sticky=tk.EW, padx=(0, theme.S))
        # Enter ile ekleme; fare kullanmadan çalışan eklenebilsin.
        self._ad_girisi.bind("<Return>", lambda *_: self._ekle_tiklandi())

        ttk.Button(giris_cerceve, text=Metin.EKLE, command=self._ekle_tiklandi).grid(
            row=0, column=1
        )

        ttk.Button(self, text=Metin.CALISAN_SIL, command=self._sil_geri).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, pady=(theme.S, 0)
        )

    def _ekle_tiklandi(self) -> None:
        self._ekle_geri(self._ad_girisi.get())

    def girisi_temizle(self) -> None:
        self._ad_girisi.delete(0, tk.END)

    def odagi_girise_ver(self) -> None:
        self._ad_girisi.focus_set()

    def secili(self) -> str | None:
        secim = self._liste.selection()
        return secim[0] if secim else None

    def sec(self, ad: str) -> None:
        if self._liste.exists(ad):
            self._liste.selection_set(ad)
            self._liste.see(ad)

    def yenile(self, calisanlar: list[str], aktif: dict[str, AktifMola]) -> None:
        """Listeyi yeniden kurar ve mümkünse önceki seçimi korur."""
        onceki = self.secili()
        self._liste.delete(*self._liste.get_children())

        for ad in calisanlar:
            molada = ad in aktif
            self._liste.insert(
                "",
                tk.END,
                iid=ad,
                text=ad,
                values=(Metin.MOLADA if molada else "",),
                tags=("molada",) if molada else (),
            )

        if onceki and self._liste.exists(onceki):
            self._liste.selection_set(onceki)
        elif calisanlar:
            self._liste.selection_set(calisanlar[0])


def _limit_renkleri(durum: LimitDurumu) -> tuple[str, str]:
    """Limit durumuna karşılık gelen `(sayaç rengi, durum rengi)`.

    Renk ttk stili yerine doğrudan widget'a verilir. sv-ttk'nın Windows
    tema motoru etiket metnini kendi paletiyle çiziyor ve türetilmiş
    stildeki `foreground` ekrana yansımıyor; widget seçeneği ise her
    zaman kazanıyor.
    """
    if durum is LimitDurumu.ASILDI:
        return theme.RENK_TEHLIKE, theme.RENK_TEHLIKE
    if durum is LimitDurumu.YAKLASTI:
        return theme.RENK_UYARI, theme.RENK_UYARI
    return theme.RENK_NORMAL, theme.RENK_SOLUK


class MolaPaneli(ttk.Frame):
    """Sağ üst panel: seçili çalışanın canlı sayacı ve mola kontrolleri."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        basla_geri: Callable[[MolaTipi], None],
        bitir_geri: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=(theme.L, theme.M))
        self._basla_geri = basla_geri
        self._bitir_geri = bitir_geri

        self.columnconfigure(0, weight=1)

        self._ad_etiketi = ttk.Label(self, text="—", style="Baslik.TLabel")
        self._ad_etiketi.grid(row=0, column=0, sticky=tk.W)

        self._sayac = ttk.Label(
            self,
            text=Metin.SAYAC_BOS,
            font=theme.SAYAC_FONT,
            foreground=theme.RENK_SOLUK,
        )
        self._sayac.grid(row=1, column=0, sticky=tk.W, pady=(theme.S, 0))

        self._durum = ttk.Label(
            self,
            text=Metin.DURUM_HAZIR,
            font=theme.SAYAC_KUCUK_FONT,
            foreground=theme.RENK_SOLUK,
        )
        self._durum.grid(row=2, column=0, sticky=tk.W)

        kontrol = ttk.Frame(self)
        kontrol.grid(row=3, column=0, sticky=tk.EW, pady=(theme.L, 0))

        ttk.Label(kontrol, text=Metin.MOLA_TIPI).grid(
            row=0, column=0, sticky=tk.W, padx=(0, theme.S)
        )

        self._tip_degeri = tk.StringVar(value=MolaTipi.CAY.etiket)
        self._tip_kutusu = ttk.Combobox(
            kontrol,
            textvariable=self._tip_degeri,
            values=[tip.etiket for tip in MolaTipi],
            state="readonly",
            width=10,
        )
        self._tip_kutusu.grid(row=0, column=1, padx=(0, theme.M))

        self._basla_butonu = ttk.Button(
            kontrol,
            text=Metin.MOLA_BASLAT,
            style="Buyuk.TButton",
            command=lambda: self._basla_geri(self.secili_tip()),
        )
        self._basla_butonu.grid(row=0, column=2, padx=(0, theme.S))

        self._bitir_butonu = ttk.Button(
            kontrol,
            text=Metin.MOLA_BITIR,
            style="Buyuk.TButton",
            command=self._bitir_geri,
        )
        self._bitir_butonu.grid(row=0, column=3)

        self._bugun = ttk.Label(
            self, text="", font=theme.SAYAC_KUCUK_FONT, foreground=theme.RENK_SOLUK
        )
        self._bugun.grid(row=4, column=0, sticky=tk.W, pady=(theme.M, 0))

    def secili_tip(self) -> MolaTipi:
        etiket = self._tip_degeri.get()
        for tip in MolaTipi:
            if tip.etiket == etiket:
                return tip
        return MolaTipi.DIGER

    def guncelle(
        self,
        *,
        calisan: str | None,
        gecen_saniye: int | None,
        aktif_tip: MolaTipi | None,
        limit_durumu: LimitDurumu,
        limit_saniye: int,
        bugun_toplam: int,
        kalan_hak: int | None,
    ) -> None:
        """Paneli tek çağrıda güncel duruma getirir."""
        if calisan is None:
            self._ad_etiketi.configure(text="—")
            self._sayac.configure(text=Metin.SAYAC_BOS, foreground=theme.RENK_SOLUK)
            self._durum.configure(
                text=Metin.CALISAN_YOK, foreground=theme.RENK_SOLUK
            )
            self._bugun.configure(text="")
            self._basla_butonu.state(["disabled"])
            self._bitir_butonu.state(["disabled"])
            return

        self._ad_etiketi.configure(text=calisan)
        molada = gecen_saniye is not None

        self._basla_butonu.state(["disabled"] if molada else ["!disabled"])
        self._bitir_butonu.state(["!disabled"] if molada else ["disabled"])
        self._tip_kutusu.state(["disabled"] if molada else ["!disabled"])

        if not molada:
            self._sayac.configure(text=Metin.SAYAC_BOS, foreground=theme.RENK_SOLUK)
            self._durum.configure(text=Metin.DURUM_HAZIR, foreground=theme.RENK_SOLUK)
        else:
            sayac_rengi, durum_rengi = _limit_renkleri(limit_durumu)
            self._sayac.configure(
                text=saat_metni(gecen_saniye), foreground=sayac_rengi
            )

            parcalar = []
            if aktif_tip is not None:
                parcalar.append(aktif_tip.etiket)
            parcalar.append(
                Metin.LIMIT_BILGI.format(dakika=limit_saniye // 60)
                if limit_saniye
                else Metin.LIMIT_YOK
            )
            if limit_durumu is LimitDurumu.ASILDI:
                parcalar.append(Metin.LIMIT_ASILDI)
            elif limit_durumu is LimitDurumu.YAKLASTI:
                parcalar.append(Metin.LIMITE_YAKLASILDI)

            self._durum.configure(
                text="  ·  ".join(parcalar), foreground=durum_rengi
            )

        alt_satir = f"{Metin.DONEM_BUGUN}: {saat_metni(bugun_toplam)}"
        if kalan_hak is not None:
            alt_satir += "  ·  " + (
                Metin.GUNLUK_HAK_BITTI
                if kalan_hak <= 0
                else Metin.GUNLUK_HAK_KALAN.format(sure=saat_metni(kalan_hak))
            )
        self._bugun.configure(text=alt_satir)


class GecmisPaneli(ttk.Frame):
    """Sağ alt panel: dönem seçimi, mola tablosu ve özet.

    Eski sürüm mola listesini `messagebox` içinde düz metin olarak
    gösteriyordu; kayıt sayısı arttıkça okunamaz hale geliyordu. Tablo
    sıralanabilir ve çoklu seçim yapılabilir.
    """

    SUTUNLAR = ("baslangic", "bitis", "sure", "tip")

    def __init__(
        self,
        master: tk.Misc,
        *,
        donem_geri: Callable[[], None],
        sil_geri: Callable[[], None],
        hepsini_sil_geri: Callable[[], None],
        disa_aktar_geri: Callable[[], None],
        grafik_geri: Callable[[], None],
        tum_calisanlar_geri: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=(theme.L, theme.M))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ust = ttk.Frame(self)
        ust.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, theme.S))
        ust.columnconfigure(1, weight=1)

        ttk.Label(ust, text=Metin.BASLIK_GECMIS, style="Bolum.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )

        self._donem_degeri = tk.StringVar(value=Donem.BUGUN.etiket)
        donem_kutusu = ttk.Combobox(
            ust,
            textvariable=self._donem_degeri,
            values=[donem.etiket for donem in Donem],
            state="readonly",
            width=12,
        )
        donem_kutusu.grid(row=0, column=2, sticky=tk.E)
        donem_kutusu.bind("<<ComboboxSelected>>", lambda *_: donem_geri())

        self._tablo = ttk.Treeview(
            self, columns=self.SUTUNLAR, show="headings", selectmode="extended"
        )
        basliklar = {
            "baslangic": (Metin.SUTUN_BASLANGIC, 150),
            "bitis": (Metin.SUTUN_BITIS, 150),
            "sure": (Metin.SUTUN_SURE, 90),
            "tip": (Metin.SUTUN_TIP, 90),
        }
        for sutun in self.SUTUNLAR:
            baslik, genislik = basliklar[sutun]
            self._tablo.heading(
                sutun, text=baslik, command=lambda s=sutun: self._sirala(s)
            )
            self._tablo.column(sutun, width=genislik, anchor=tk.W)
        self._tablo.grid(row=1, column=0, sticky=tk.NSEW)

        kaydirma = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tablo.yview)
        self._tablo.configure(yscrollcommand=kaydirma.set)
        kaydirma.grid(row=1, column=1, sticky=tk.NS)

        self._ozet = ttk.Label(
            self, text="", font=theme.SAYAC_KUCUK_FONT, foreground=theme.RENK_SOLUK
        )
        self._ozet.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(theme.S, 0))

        butonlar = ttk.Frame(self)
        butonlar.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(theme.M, 0))
        for sira, (metin, geri) in enumerate(
            (
                (Metin.RAPOR_DISA_AKTAR, disa_aktar_geri),
                (Metin.RAPOR_GRAFIK, grafik_geri),
                (Metin.RAPOR_TUM_CALISANLAR, tum_calisanlar_geri),
                (Metin.SIL, sil_geri),
                (f"{Metin.SIL} ({Metin.DONEM_TUMU})", hepsini_sil_geri),
            )
        ):
            ttk.Button(butonlar, text=metin, command=geri).grid(
                row=0, column=sira, padx=(0, theme.S)
            )

        # Sıralama durumu
        self._sirali_sutun: str | None = None
        self._ters_sirali = False
        self._kayitlar: list[MolaKaydi] = []

    def secili_donem(self) -> Donem:
        etiket = self._donem_degeri.get()
        for donem in Donem:
            if donem.etiket == etiket:
                return donem
        return Donem.BUGUN

    def secili_kimlikler(self) -> set[str]:
        return set(self._tablo.selection())

    def yenile(self, kayitlar: list[MolaKaydi], ozet: Ozet) -> None:
        self._kayitlar = list(kayitlar)
        self._tabloyu_doldur()

        if ozet.mola_sayisi == 0:
            self._ozet.configure(text=Metin.RAPOR_VERI_YOK)
            return

        # Kısa etiketler: uzun biçim dar pencerede sağdan taşıyordu.
        self._ozet.configure(
            text=(
                f"{ozet.mola_sayisi} mola"
                f"   ·   Toplam {ozet.toplam_metni}"
                f"   ·   Ort. {ozet.ortalama_metni}"
                f"   ·   Performans {ozet.performans_metni}"
            )
        )

    def _tabloyu_doldur(self) -> None:
        self._tablo.delete(*self._tablo.get_children())
        for kayit in self._sirali_kayitlar():
            self._tablo.insert(
                "",
                tk.END,
                iid=kayit.kimlik,
                values=(
                    kayit.baslangic.strftime("%d.%m.%Y %H:%M:%S"),
                    kayit.bitis.strftime("%d.%m.%Y %H:%M:%S"),
                    saat_metni(kayit.toplam_saniye),
                    kayit.tip.etiket,
                ),
            )

    def _sirali_kayitlar(self) -> list[MolaKaydi]:
        if self._sirali_sutun is None:
            return self._kayitlar

        anahtarlar = {
            "baslangic": lambda kayit: kayit.baslangic,
            "bitis": lambda kayit: kayit.bitis,
            "sure": lambda kayit: kayit.toplam_saniye,
            "tip": lambda kayit: kayit.tip.etiket,
        }
        return sorted(
            self._kayitlar,
            key=anahtarlar[self._sirali_sutun],
            reverse=self._ters_sirali,
        )

    def _sirala(self, sutun: str) -> None:
        """Aynı sütuna ikinci tıklama yönü ters çevirir."""
        if self._sirali_sutun == sutun:
            self._ters_sirali = not self._ters_sirali
        else:
            self._sirali_sutun = sutun
            self._ters_sirali = False
        self._tabloyu_doldur()
