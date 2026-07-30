"""Uygulama giriş noktası.

Çalıştırma:

    cd mola
    python main.py

Eski `mola.py` modül seviyesinde `tk.Tk()` çağırıyordu; dosya import
edilir edilmez pencere açılıyordu. Burada pencere yalnızca `main()`
çağrıldığında kurulur, böylece modüller test veya araç amacıyla import
edilebilir.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Proje kökünü import yoluna ekle. Uygulama hangi çalışma dizininden
# başlatılırsa başlatılsın `config`, `storage`, `ui` gibi modüller bulunur.
PROJE_KOKU = Path(__file__).resolve().parent
if str(PROJE_KOKU) not in sys.path:
    sys.path.insert(0, str(PROJE_KOKU))


def main() -> int:
    try:
        from ui.app import MolaTakipUygulamasi
    except ImportError as hata:
        # En olası sebep sv-ttk'nın kurulu olmaması.
        print(f"Gerekli paket bulunamadi: {hata}", file=sys.stderr)
        print("Kurulum: python -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    try:
        uygulama = MolaTakipUygulamasi()
        uygulama.mainloop()
    except Exception:  # noqa: BLE001 - son savunma hattı
        # Buraya düşen her şey beklenmeyen bir hatadır. Konsola tam izi
        # yaz, kullanıcıya sade bir mesaj göster; veri dosyalarına dokunma.
        traceback.print_exc()
        _cokme_mesaji_goster()
        return 1

    return 0


def _cokme_mesaji_goster() -> None:
    """Ana pencere kurulamadıysa bile bir hata kutusu göstermeyi dener."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        kok = tk.Tk()
        kok.withdraw()
        messagebox.showerror(
            "Mola Takip",
            "Uygulama beklenmedik bir hatayla karşılaştı ve kapanıyor.\n\n"
            "Kayıtlarınız değiştirilmedi. Ayrıntılar konsola yazıldı.",
        )
        kok.destroy()
    except Exception:  # noqa: BLE001 - konsol çıktısı zaten yazıldı
        pass


if __name__ == "__main__":
    raise SystemExit(main())
