"""Yardımcı pencereler: ayarlar, tüm çalışanlar raporu, grafik."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from i18n import Metin
from models import Ayarlar, MolaTipi, saat_metni
from services.report_service import CalisanOzeti, Donem
from ui import theme
from ui.chart import CubukGrafik


class _Pencere(tk.Toplevel):
    """Ortak Toplevel davranışı: başlık, ana pencereye bağlılık, Esc ile kapanma."""

    def __init__(self, master: tk.Misc, baslik: str, boyut: str) -> None:
        super().__init__(master)
        self.title(f"{Metin.UYGULAMA} — {baslik}")
        self.geometry(boyut)
        self.transient(master.winfo_toplevel())
        self.bind("<Escape>", lambda _olay: self.destroy())


class AyarlarPenceresi(_Pencere):
    """Vardiya, limitler, tema ve yedekleme ayarları.

    Kaydet'e basılana kadar hiçbir değişiklik kalıcı olmaz; İptal veya Esc
    mevcut ayarları olduğu gibi bırakır.
    """

    def __init__(
        self,
        master: tk.Misc,
        ayarlar: Ayarlar,
        kaydet_geri: Callable[[Ayarlar], bool],
    ) -> None:
        super().__init__(master, Metin.BASLIK_AYARLAR, "460x540")
        self._kaydet_geri = kaydet_geri

        govde = ttk.Frame(self, padding=theme.L)
        govde.pack(fill=tk.BOTH, expand=True)
        govde.columnconfigure(1, weight=1)

        satir = 0

        ttk.Label(govde, text=Metin.AYAR_TEMA, style="Bolum.TLabel").grid(
            row=satir, column=0, sticky=tk.W, pady=(0, theme.XS)
        )
        self._tema = tk.StringVar(value=ayarlar.tema)
        tema_cerceve = ttk.Frame(govde)
        tema_cerceve.grid(row=satir, column=1, sticky=tk.W, pady=(0, theme.XS))
        for deger, etiket in (
            ("light", Metin.AYAR_TEMA_ACIK),
            ("dark", Metin.AYAR_TEMA_KOYU),
        ):
            ttk.Radiobutton(
                tema_cerceve, text=etiket, value=deger, variable=self._tema
            ).pack(side=tk.LEFT, padx=(0, theme.M))
        satir += 1

        self._vardiya = self._sayi_satiri(
            govde, satir, Metin.AYAR_VARDIYA, ayarlar.vardiya_saati
        )
        satir += 1

        self._gunluk_hak = self._sayi_satiri(
            govde, satir, Metin.AYAR_GUNLUK_HAK, ayarlar.gunluk_toplam_hak
        )
        satir += 1

        self._yedek = self._sayi_satiri(
            govde, satir, Metin.AYAR_YEDEK, ayarlar.yedek_sayisi
        )
        satir += 1

        self._ses = tk.BooleanVar(value=ayarlar.ses_acik)
        ttk.Checkbutton(govde, text=Metin.AYAR_SES, variable=self._ses).grid(
            row=satir, column=0, columnspan=2, sticky=tk.W, pady=(theme.M, theme.M)
        )
        satir += 1

        ttk.Separator(govde, orient=tk.HORIZONTAL).grid(
            row=satir, column=0, columnspan=2, sticky=tk.EW, pady=theme.S
        )
        satir += 1

        ttk.Label(govde, text=Metin.AYAR_LIMITLER, style="Bolum.TLabel").grid(
            row=satir, column=0, columnspan=2, sticky=tk.W, pady=(0, theme.S)
        )
        satir += 1

        self._limitler: dict[MolaTipi, tk.StringVar] = {}
        for tip in MolaTipi:
            self._limitler[tip] = self._sayi_satiri(
                govde, satir, tip.etiket, ayarlar.limit_dakika(tip)
            )
            satir += 1

        butonlar = ttk.Frame(govde)
        butonlar.grid(row=satir, column=0, columnspan=2, sticky=tk.E, pady=(theme.L, 0))
        ttk.Button(butonlar, text=Metin.IPTAL, command=self.destroy).pack(
            side=tk.LEFT, padx=(0, theme.S)
        )
        ttk.Button(butonlar, text=Metin.KAYDET, command=self._kaydet).pack(side=tk.LEFT)

    def _sayi_satiri(
        self, ana: ttk.Frame, satir: int, etiket: str, deger: int
    ) -> tk.StringVar:
        ttk.Label(ana, text=etiket).grid(row=satir, column=0, sticky=tk.W, pady=theme.XS)
        degisken = tk.StringVar(value=str(deger))
        ttk.Entry(ana, textvariable=degisken, width=8).grid(
            row=satir, column=1, sticky=tk.W, pady=theme.XS
        )
        return degisken

    def _sayi_oku(self, degisken: tk.StringVar, alan: str, alt_sinir: int) -> int | None:
        """Metni tam sayıya çevirir; geçersizse uyarı gösterip None döner."""
        try:
            sayi = int(degisken.get().strip())
        except ValueError:
            sayi = None

        if sayi is None or sayi < alt_sinir:
            messagebox.showerror(
                Metin.BASLIK_HATA,
                Metin.AYAR_GECERSIZ_SAYI.format(alan=alan),
                parent=self,
            )
            return None
        return sayi

    def _kaydet(self) -> None:
        vardiya = self._sayi_oku(self._vardiya, Metin.AYAR_VARDIYA, 1)
        if vardiya is None:
            return
        hak = self._sayi_oku(self._gunluk_hak, Metin.AYAR_GUNLUK_HAK, 0)
        if hak is None:
            return
        yedek = self._sayi_oku(self._yedek, Metin.AYAR_YEDEK, 0)
        if yedek is None:
            return

        limitler: dict[str, int] = {}
        for tip, degisken in self._limitler.items():
            dakika = self._sayi_oku(degisken, tip.etiket, 0)
            if dakika is None:
                return
            limitler[tip.value] = dakika

        yeni = Ayarlar(
            tema=self._tema.get(),
            vardiya_saati=vardiya,
            ses_acik=bool(self._ses.get()),
            yedek_sayisi=yedek,
            pencere_boyutu="",  # Çağıran mevcut pencere boyutunu korur.
            mola_limitleri=limitler,
            gunluk_toplam_hak=hak,
        )

        if self._kaydet_geri(yeni):
            self.destroy()


class NotPenceresi(_Pencere):
    """Tek bir mola kaydının notunu düzenler.

    Kaydet'e basılana kadar hiçbir şey değişmez; İptal veya Esc kaydı olduğu
    gibi bırakır. Not tek satırlık bir `Entry`: tablo hücresi ve CSV satırı
    çok satırlı metni okunaksız gösterir.
    """

    def __init__(
        self,
        master: tk.Misc,
        mevcut_not: str,
        max_uzunluk: int,
        kaydet_geri: Callable[[str], bool],
    ) -> None:
        super().__init__(master, Metin.NOT_BASLIK, "480x170")
        self._kaydet_geri = kaydet_geri

        govde = ttk.Frame(self, padding=theme.L)
        govde.pack(fill=tk.BOTH, expand=True)
        govde.columnconfigure(0, weight=1)

        ttk.Label(govde, text=Metin.NOT_ETIKET.format(max=max_uzunluk)).grid(
            row=0, column=0, sticky=tk.W, pady=(0, theme.XS)
        )

        self._deger = tk.StringVar(value=mevcut_not)
        giris = ttk.Entry(govde, textvariable=self._deger)
        giris.grid(row=1, column=0, sticky=tk.EW)
        giris.focus_set()
        giris.icursor(tk.END)
        giris.bind("<Return>", lambda _olay: self._kaydet())

        butonlar = ttk.Frame(govde)
        butonlar.grid(row=2, column=0, sticky=tk.E, pady=(theme.L, 0))
        ttk.Button(butonlar, text=Metin.IPTAL, command=self.destroy).pack(
            side=tk.LEFT, padx=(0, theme.S)
        )
        ttk.Button(butonlar, text=Metin.KAYDET, command=self._kaydet).pack(side=tk.LEFT)

    def _kaydet(self) -> None:
        """Kaydetme başarısızsa pencere açık kalır, kullanıcı düzeltebilir."""
        if self._kaydet_geri(self._deger.get()):
            self.destroy()


class TumCalisanlarPenceresi(_Pencere):
    """Bütün çalışanların seçili dönemdeki karşılaştırmalı tablosu."""

    SUTUNLAR = ("calisan", "sayi", "toplam", "ortalama", "performans")

    def __init__(
        self, master: tk.Misc, donem: Donem, ozetler: list[CalisanOzeti]
    ) -> None:
        super().__init__(
            master, f"{Metin.RAPOR_TUM_CALISANLAR} — {donem.etiket}", "760x460"
        )

        govde = ttk.Frame(self, padding=theme.L)
        govde.pack(fill=tk.BOTH, expand=True)
        govde.columnconfigure(0, weight=1)
        govde.rowconfigure(0, weight=1)

        tablo = ttk.Treeview(govde, columns=self.SUTUNLAR, show="headings")
        basliklar = {
            "calisan": (Metin.SUTUN_CALISAN, 200, tk.W),
            "sayi": (Metin.SUTUN_MOLA_SAYISI, 80, tk.E),
            "toplam": (Metin.SUTUN_TOPLAM, 120, tk.E),
            "ortalama": (Metin.SUTUN_ORTALAMA, 120, tk.E),
            "performans": (Metin.SUTUN_PERFORMANS, 110, tk.E),
        }
        for sutun in self.SUTUNLAR:
            baslik, genislik, hiza = basliklar[sutun]
            tablo.heading(sutun, text=baslik)
            tablo.column(sutun, width=genislik, anchor=hiza)
        tablo.grid(row=0, column=0, sticky=tk.NSEW)

        kaydirma = ttk.Scrollbar(govde, orient=tk.VERTICAL, command=tablo.yview)
        tablo.configure(yscrollcommand=kaydirma.set)
        kaydirma.grid(row=0, column=1, sticky=tk.NS)

        for oge in ozetler:
            tablo.insert(
                "",
                tk.END,
                values=(
                    oge.calisan,
                    oge.ozet.mola_sayisi,
                    oge.ozet.toplam_metni,
                    oge.ozet.ortalama_metni,
                    oge.ozet.performans_metni,
                ),
            )

        if not ozetler:
            ttk.Label(
                govde, text=Metin.RAPOR_VERI_YOK, foreground=theme.RENK_SOLUK
            ).grid(row=1, column=0, sticky=tk.W, pady=(theme.M, 0))

        ttk.Button(govde, text=Metin.KAPAT, command=self.destroy).grid(
            row=2, column=0, columnspan=2, sticky=tk.E, pady=(theme.M, 0)
        )


class GrafikPenceresi(_Pencere):
    """Günlük dağılım ve mola tipi dağılımı grafikleri."""

    def __init__(
        self,
        master: tk.Misc,
        baslik: str,
        gunluk: list[tuple[str, int]],
        tipler: list[tuple[str, int]],
    ) -> None:
        super().__init__(master, f"{Metin.RAPOR_GRAFIK} — {baslik}", "820x560")

        govde = ttk.Frame(self, padding=theme.L)
        govde.pack(fill=tk.BOTH, expand=True)
        govde.columnconfigure(0, weight=1)
        govde.rowconfigure(1, weight=1)
        govde.rowconfigure(3, weight=1)

        ttk.Label(govde, text="Günlük mola süresi", style="Bolum.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        gunluk_grafik = CubukGrafik(govde)
        gunluk_grafik.grid(row=1, column=0, sticky=tk.NSEW, pady=(theme.XS, theme.L))
        gunluk_grafik.veri_ata(gunluk, saat_metni)

        ttk.Label(govde, text="Mola tipine göre dağılım", style="Bolum.TLabel").grid(
            row=2, column=0, sticky=tk.W
        )
        tip_grafik = CubukGrafik(govde)
        tip_grafik.grid(row=3, column=0, sticky=tk.NSEW, pady=(theme.XS, 0))
        tip_grafik.veri_ata(tipler, saat_metni)

        ttk.Button(govde, text=Metin.KAPAT, command=self.destroy).grid(
            row=4, column=0, sticky=tk.E, pady=(theme.M, 0)
        )
