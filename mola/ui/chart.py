"""Canvas ile çizilen çubuk grafik.

matplotlib eklemek yerine Tkinter'ın kendi `Canvas`'ı kullanıldı: tek
bağımlılık daha az, paketlenmiş exe onlarca MB küçük kalıyor ve renkler
uygulama temasıyla birlikte değişiyor.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui import theme

KENAR_BOSLUGU = 32
ALT_BOSLUK = 40
UST_BOSLUK = 16
EN_AZ_CUBUK_GENISLIGI = 12
CUBUK_ARALIGI = 8


class CubukGrafik(ttk.Frame):
    """Etiketli yatay eksenli basit dikey çubuk grafik.

    Veriler `(etiket, deger)` çiftleridir. Değer birimi çağırana aittir;
    grafik yalnızca oranları çizer ve `deger_bicimi` ile metne dönüştürür.
    """

    def __init__(self, master: tk.Misc, yukseklik: int = 220) -> None:
        super().__init__(master)
        self._veriler: list[tuple[str, int]] = []
        self._deger_bicimi = str

        self._canvas = tk.Canvas(self, height=yukseklik, highlightthickness=0, bd=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Pencere yeniden boyutlandığında grafiği yeniden çiz.
        self._canvas.bind("<Configure>", lambda _olay: self._ciz())

    def veri_ata(self, veriler: list[tuple[str, int]], deger_bicimi=str) -> None:
        self._veriler = list(veriler)
        self._deger_bicimi = deger_bicimi
        self._ciz()

    def temizle(self) -> None:
        self._veriler = []
        self._ciz()

    def _ciz(self) -> None:
        arka, on = theme.canvas_renkleri(self)
        self._canvas.configure(background=arka)
        self._canvas.delete("all")

        genislik = self._canvas.winfo_width()
        yukseklik = self._canvas.winfo_height()
        if genislik <= 1 or yukseklik <= 1:
            return  # Henüz yerleşim yapılmadı.

        if not self._veriler:
            self._canvas.create_text(
                genislik // 2,
                yukseklik // 2,
                text="—",
                fill=theme.RENK_SOLUK,
                font=theme.ALT_BASLIK_FONT,
            )
            return

        cizim_genisligi = genislik - 2 * KENAR_BOSLUGU
        cizim_yuksekligi = yukseklik - UST_BOSLUK - ALT_BOSLUK
        if cizim_genisligi <= 0 or cizim_yuksekligi <= 0:
            return

        taban = yukseklik - ALT_BOSLUK
        self._canvas.create_line(
            KENAR_BOSLUGU, taban, genislik - KENAR_BOSLUGU, taban, fill=theme.RENK_SOLUK
        )

        adet = len(self._veriler)
        cubuk_genisligi = max(
            EN_AZ_CUBUK_GENISLIGI,
            (cizim_genisligi - CUBUK_ARALIGI * (adet + 1)) // adet,
        )
        en_buyuk = max(deger for _etiket, deger in self._veriler) or 1

        for sira, (etiket, deger) in enumerate(self._veriler):
            sol = (
                KENAR_BOSLUGU + CUBUK_ARALIGI + sira * (cubuk_genisligi + CUBUK_ARALIGI)
            )
            sag = sol + cubuk_genisligi
            if sol >= genislik - KENAR_BOSLUGU:
                break  # Sığmayan çubukları çizme.

            oran = deger / en_buyuk
            tepe = taban - max(2, int(cizim_yuksekligi * oran))
            renk = theme.GRAFIK_RENKLERI[sira % len(theme.GRAFIK_RENKLERI)]

            self._canvas.create_rectangle(sol, tepe, sag, taban, fill=renk, width=0)

            self._canvas.create_text(
                (sol + sag) // 2,
                tepe - 10,
                text=self._deger_bicimi(deger),
                fill=on,
                font=theme.SAYAC_KUCUK_FONT,
            )

            self._canvas.create_text(
                (sol + sag) // 2,
                taban + 14,
                text=etiket,
                fill=theme.RENK_SOLUK,
                font=("Segoe UI", 8),
            )
