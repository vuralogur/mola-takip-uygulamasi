"""PyInstaller ile tek dosyalık `.exe` üretir.

Kullanım:

    python -m pip install pyinstaller
    python build.py

Çıktı: `dist/MolaTakip.exe`

Paketlenmiş sürümde veri dosyaları uygulamanın yanına değil
`%APPDATA%/MolaTakip` altına yazılır (bkz. `config._veri_dizini_bul`).
PyInstaller'ın açtığı geçici klasör her çalıştırmada silindiği için oraya
yazmak tüm kayıtları kaybettirirdi.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
KAYNAK = KOK / "mola"
GIRIS = KAYNAK / "main.py"
IKON = KOK / "mola.ico"
UYGULAMA_ADI = "MolaTakip"


def main() -> int:
    if not GIRIS.exists():
        print(f"Giris dosyasi bulunamadi: {GIRIS}", file=sys.stderr)
        return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller kurulu degil.", file=sys.stderr)
        print("Kurulum: python -m pip install pyinstaller", file=sys.stderr)
        return 1

    komut = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        # Konsol penceresi acilmasin; bu bir GUI uygulamasi.
        "--windowed",
        "--name",
        UYGULAMA_ADI,
        # Modul importlari 'from config import ...' seklinde duz oldugu icin
        # kaynak klasoru arama yoluna eklenmeli.
        "--paths",
        str(KAYNAK),
        # sv-ttk kendi .tcl tema dosyalarini paketle tasimali.
        "--collect-data",
        "sv_ttk",
    ]

    if IKON.exists():
        komut += ["--icon", str(IKON)]
    else:
        print(f"Not: {IKON.name} bulunamadi, varsayilan ikon kullanilacak.")

    komut.append(str(GIRIS))

    print("Calistiriliyor:\n  " + " ".join(komut) + "\n")
    sonuc = subprocess.run(komut, cwd=KOK, check=False)

    if sonuc.returncode != 0:
        print("\nPaketleme basarisiz.", file=sys.stderr)
        return sonuc.returncode

    exe = KOK / "dist" / f"{UYGULAMA_ADI}.exe"
    print(f"\nTamamlandi: {exe}")
    print("Veri konumu: %APPDATA%\\MolaTakip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
