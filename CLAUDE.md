# CLAUDE.md

## Project: Break Tracker (mola-takip-uygulamasi)

Offline desktop app for tracking employee break times. Python + Tkinter,
local JSON storage, Turkish UI.

Goals: simple, reliable, offline, easy to maintain.

**Do not** turn this into a web app.
**Do not** migrate to another GUI framework unless explicitly requested.
**Do not** replace JSON storage with SQLite or another database unless explicitly requested.
**Do not** add a second runtime dependency without asking. Currently only `sv-ttk`.

---

## Run

```
python -m pip install -r requirements.txt
cd mola
python main.py
```

Python 3.10+ (uses `X | None` syntax). Verified on 3.14.

Git repository, default branch `main`, no remote configured yet. Runtime data
files are gitignored — see Data Files.

---

## Architecture

Layered. Each layer knows only the one below it:

```
ui  ->  services  ->  repository  ->  storage
```

```
mola/
├── main.py                    entry point, sys.path setup, crash guard
├── config.py                  constants, file paths, defaults
├── models.py                  MolaKaydi, AktifMola, Ayarlar, MolaTipi
├── storage.py                 UTF-8 + atomic JSON read/write
├── backup.py                  timestamped version backups
├── migrations.py              v1 -> v2 schema migration
├── repository.py              repositories + in-memory cache + UyariKutusu
├── i18n.py                    every user-visible string (class Metin)
├── services/
│   ├── employee_service.py    employee CRUD, name validation
│   ├── break_service.py       break lifecycle, limits, daily budget
│   └── report_service.py      period filtering, summaries, CSV
└── ui/
    ├── app.py                 MolaTakipUygulamasi — orchestration, timer
    ├── panels.py              CalisanPaneli, MolaPaneli, GecmisPaneli
    ├── dialogs.py             settings, chart, all-employees windows
    ├── chart.py               CubukGrafik — Canvas bar chart
    └── theme.py               sv-ttk theme, spacing scale, fonts
```

`build.py` sits at the repo root, outside the layers. It shells out to
PyInstaller (`--onefile --windowed`, `--collect-data sv_ttk`) and is never
imported by the app. Uses `mola.ico` if present, warns and continues if not.

### Layer rules — do not break these

- `storage.py` and `repository.py` **never** call `messagebox`. They raise
  typed exceptions (`VeriBozuk`, `YazmaHatasi`) or push messages into
  `UyariKutusu`. Only `ui/` shows dialogs.
- Services return `(basarili, mesaj)` tuples the UI can display directly.
- Panels never read or write data. They fire callbacks; `app.py` calls services.

---

## Naming Convention

Python identifiers are **Turkish** (`MolaKaydi`, `baslangic`, `sure_dakika`).
JSON keys are **English** and frozen by the v1 schema (`start_time`,
`duration_minutes`). `to_dict` / `from_dict` bridge the two.

Match the surrounding code. Do not introduce English identifiers into
existing Turkish modules or vice versa.

- `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants
- Type hints on every function you write or modify
- No abbreviations; avoid `data`, `temp`, `value`

---

## Data Files

In `mola/` when run from source; in `%APPDATA%/MolaTakip` when frozen by
PyInstaller (`config._veri_dizini_bul()`). Never write to `sys._MEIPASS` —
it is wiped every run.

| File | Shape |
| --- | --- |
| `employees.json` | `list[str]` |
| `break_data.json` | v2 wrapper, see below |
| `active_breaks.json` | `{employee: {start_time, break_type}}` |
| `settings.json` | theme, shift hours, limits, window size |
| `yedekler/` | last 10 timestamped backups |

All of them are gitignored — a fresh clone contains no data files. The
repositories fall back to empty defaults on first run and write the file only
when there is something to save. Never commit a data file; it would ship real
employee names.

### Schema v2 — do not break

```json
{
  "schema_version": 2,
  "breaks": {
    "Ada": [
      {
        "id": "a3f1c9",
        "start_time": "2026-07-29 09:15:00",
        "end_time": "2026-07-29 09:27:30",
        "duration_minutes": 12,
        "duration_seconds": 30,
        "break_type": "diger",
        "note": ""
      }
    ]
  }
}
```

All seven fields are required. Never remove or rename one. To change the
schema: bump `SEMA_SURUMU` in `config.py`, add the transform in
`migrations.py`, take a backup first, preserve every existing record.

`duration_minutes` / `duration_seconds` are two halves of one duration
(seconds always 0–59), not independent totals. Sum via
`MolaKaydi.toplam_saniye`.

Date format is `"%Y-%m-%d %H:%M:%S"` everywhere. Never introduce a second one.

---

## Rules Learned the Hard Way

- **Always `encoding="utf-8"`.** Windows defaults to cp1252, which destroys
  Turkish names. `storage.py` enforces this — go through it, never call
  `open()` on a data file directly. Use `ensure_ascii=False` when dumping.
- **Never write JSON directly to the target file.** `storage.json_yaz` writes
  to a temp file and `os.replace`s it, so a crash mid-write cannot truncate
  data.
- **Corrupt file: move aside, never overwrite.** `_bozuk_dosyayi_kenara_al`
  renames it with a timestamp so the user can recover records by hand.
- **Back up before every destructive write.** `_Depo._destruktif_yedek` runs
  ahead of `MolaDeposu.sil` / `hepsini_sil` / `calisani_kaldir` and
  `CalisanDeposu.sil`. It stays silent on success and on failure — a dialog per
  delete would drown the flow, and `backup.yedek_al` never blocks the write.
  Adding a note is not destructive and takes no backup.
- **Backup names are second-resolution.** Two deletes inside one second used to
  overwrite the same file; `backup._bos_hedef` appends `_2`, `_3` … and uses
  `_` (sorts after `.`) so name order stays chronological.
- **ttk style `foreground` does not reach the screen under sv-ttk.** The
  Windows theme engine draws label text in its own palette. `theme.py`
  intentionally defines font-only styles; set colors with a widget-level
  `foreground=` argument, which always wins.
- **No threads.** Tkinter is not thread-safe. The live counter uses
  `after(1000, ...)`. Never touch widgets from outside the main loop.
- **Do not rebuild the employee list on every tick.** It destroys selection
  and scroll position. Refresh it only when a break starts or ends.
- **Periods are calendar-based**, not rolling windows. "This week" starts
  Monday 00:00. Ranges are `[start, end)` so a record never lands in two
  periods.
- **Performance % divides by unique days with records**, not a fixed 8-hour
  day. The old code produced meaningless values on multi-day reports.

---

## Error Handling

Never assume a file exists or its contents are valid. `try` / `except` around
file I/O, `json.loads` (`JSONDecodeError`), and `strptime` (`ValueError`).

One bad record must not reject the whole file: `MolaKaydi.from_dict` returns
`None` for unparseable entries, the repository counts them and warns.
`MolaTipi.coz` downgrades unknown values to `DIGER` instead of raising.

Never show a stack trace to the user. `main.py` has a last-resort handler
that logs to console and shows a plain message.

---

## UI and UX

- Keep `ttk` widgets and `grid`. Spacing comes from `theme.py` (4px scale:
  `XS`/`S`/`M`/`L`/`XL`) — no hardcoded pixels in panel files.
- Counter uses a monospace font so digits do not shift the layout each second.
- Success feedback goes to the status bar, not a `messagebox`. Reserve dialogs
  for errors and confirmations.
- Every destructive action requires confirmation.
- All strings live in `i18n.py`. Never inline a user-visible string.
- Never block the main loop.

---

## Security

- Validate employee names (`services/employee_service.ad_dogrula`).
- Never use `eval` or `exec`; never run external commands.
- Never hardcode secrets, never auto-install packages.
- Never write outside the data directory.

---

## Testing

No test suite in the repo. Verification is manual — after any change:

- add employee: duplicate rejected, empty rejected, digits rejected,
  Turkish characters accepted
- delete employee: break data and any active break go with it
- start / end break; record lands in `break_data.json`
- end break with no employee selected; end without starting
- two employees on break at once, both counters correct
- close and reopen while on break — counter resumes, does not reset
- limit warning colors at 80% and 100% of the type limit
- period filters, including the empty-data case
- delete selected breaks, delete all breaks — a fresh file lands in `yedekler/`
  each time, two deletes in the same second produce two files
- add / edit / clear a break note: double-click a row and use the Not button;
  the note survives reload, shows in the table and in the CSV
- Not button with no selection and with two rows selected — both refuse
- launch with missing JSON; launch with corrupt JSON
- Turkish characters survive save/load and CSV export
- both light and dark theme, window resized — no widget overflow

After touching storage or migrations: copy a v1 `break_data.json`, load it,
and confirm record count and total duration are unchanged.

---

## Review Checklist

- no duplicated logic, no dead code, no unused imports
- no hardcoded paths, pixels, or user-visible strings
- layer rules intact (no `messagebox` below `ui/`)
- new/changed functions have type hints
- every data-file access goes through `storage.py`
- existing features still work

---

## Assistant Rules

- Never assume requirements, never invent features.
- Never silently change behavior.
- Prefer minimal, safe changes. Do not touch unrelated areas.
- Explain trade-offs. If uncertain, ask first.
- Priority: correctness, data safety, maintainability, readability.

---

## Commit Style

`feat:` `fix:` `refactor:` `docs:` `style:` `test:` `perf:` `chore:`
