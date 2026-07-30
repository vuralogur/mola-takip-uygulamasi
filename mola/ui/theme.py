"""Tema, boşluk ölçeği ve font seçimleri.

Görsel kararlar tek yerde toplanır; panel dosyalarında sabit piksel veya
renk kodu bulunmaz.

Ölçek 4 piksel tabanlıdır. Tkinter'ın gölge, yuvarlak köşe veya geçiş
animasyonu desteği yok; tutarlılık boşluk ritmi, hizalama ve ayraçlarla
kurulur.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import sv_ttk

# --- Boşluk ölçeği ---
XS = 4
S = 8
M = 12
L = 16
XL = 24

# --- Fontlar ---
# Sayaç sabit genişlikli olmalı: orantılı fontta rakam değiştikçe metin
# genişliği oynar ve sayaç her saniye yatay olarak zıplar.
SAYAC_FONT = ("Consolas", 40, "bold")
SAYAC_KUCUK_FONT = ("Consolas", 11)
BASLIK_FONT = ("Segoe UI", 16, "bold")
ALT_BASLIK_FONT = ("Segoe UI", 10)
BOLUM_FONT = ("Segoe UI", 9, "bold")

# --- Durum renkleri ---
# Her iki temada da okunur olacak şekilde seçildi; sv-ttk arka planları
# açıkta beyaza, koyuda koyu griye yakındır.
RENK_NORMAL = "#3E9E4E"
RENK_UYARI = "#D08B1F"
RENK_TEHLIKE = "#D64545"
RENK_SOLUK = "#8A8A8A"

# Grafik çubuğu renkleri
GRAFIK_RENKLERI = ("#4B8BBE", "#3E9E4E", "#D08B1F", "#9B72C6")

# Buton iç boşluğu. Yükseklik ~40px'e çıkar; küçük hedefler tıklamayı
# zorlaştırır.
BUTON_DOLGU = (14, 10)


def tema_uygula(kok: tk.Misc, tema: str) -> None:
    """sv-ttk temasını uygular ve özel stilleri kaydeder.

    ttk widget'larının kendisi değişmez — yalnızca görünümleri. Bu yüzden
    tema değişimi mevcut arayüz kodunu etkilemez.
    """
    sv_ttk.set_theme("dark" if tema == "dark" else "light")
    _stilleri_kur(kok)


def tema_degistir(kok: tk.Misc) -> str:
    """Açık/koyu arasında geçiş yapar ve yeni temanın adını döner."""
    yeni = "light" if sv_ttk.get_theme() == "dark" else "dark"
    sv_ttk.set_theme(yeni)
    _stilleri_kur(kok)
    return yeni


def _stilleri_kur(kok: tk.Misc) -> None:
    """Uygulamaya özel ttk stillerini tanımlar.

    Tema her değiştiğinde yeniden çağrılır: sv_ttk stil tablosunu
    sıfırladığı için özel stiller aksi halde kaybolur.
    """
    stil = ttk.Style(kok)

    # Yalnızca font taşıyan stiller burada tanımlanır.
    #
    # Renk taşıyan stiller kasıtlı olarak yok: sv-ttk'nın Windows tema
    # motoru etiket metnini kendi paletiyle çiziyor ve türetilmiş bir
    # stilin `foreground` değeri ekrana yansımıyor (stil tablosunda
    # görünüyor ama çizimde kullanılmıyor). Renk gereken yerlerde widget'a
    # doğrudan `foreground=` verilir; widget seçeneği her zaman kazanır.
    stil.configure("Baslik.TLabel", font=BASLIK_FONT)
    stil.configure("Bolum.TLabel", font=BOLUM_FONT)

    stil.configure("Buyuk.TButton", padding=BUTON_DOLGU)

    # Tablo satır yüksekliği: varsayılan 20px sıkışık duruyor.
    stil.configure("Treeview", rowheight=28)
    stil.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))


def canvas_renkleri(kok: tk.Misc) -> tuple[str, str]:
    """Canvas için `(arka plan, ön plan)` renkleri.

    Canvas bir ttk widget'ı değildir, temayı otomatik almaz. Renkleri
    temalı bir widget'tan okuyup elle uygularız.
    """
    stil = ttk.Style(kok)
    arka = stil.lookup("TFrame", "background") or "#ffffff"
    on = stil.lookup("TLabel", "foreground") or "#000000"
    return arka, on
