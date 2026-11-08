"""Kilitli dönem (DURUM.md karar 20): bu tarih ve sonrası veri kasada; yalnız final seçimde BİR kez açılır."""
from __future__ import annotations

import atexit
import json
import multiprocessing.util as mp_util
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
KILIT_BASLANGIC = pd.Timestamp("2025-11-01", tz="UTC")
KILIT_LOG = KOK / "sonuclar" / "kilit_acilis.jsonl"
# Sunucu (paper) kendi açılışlarını depodaki izlenen dosyaya değil, durum dizinine yazar (git pull çakışmasın): L3A_KILIT_LOG.
KILIT_LOG_ORTAM = "L3A_KILIT_LOG"


def kilit_log_yolu() -> Path:
    return Path(os.environ[KILIT_LOG_ORTAM]) if os.environ.get(KILIT_LOG_ORTAM) else KILIT_LOG


def kilit_siniri(bitis, kilit_ac: bool, gerekce: str | None = None, sembol: str = "", ne: str = ""):
    """Okuma için etkin `bitis` (hariç). Kilit açıksa bitis aynen döner ve açılış kayda geçer."""
    if kilit_ac:
        if not isinstance(gerekce, str) or not gerekce.strip():
            raise ValueError("kilit_ac=True için boş olmayan `gerekce` zorunlu")
        kilit_acilisi_yaz(sembol, ne, gerekce)
        return bitis
    if bitis is None:
        return KILIT_BASLANGIC
    b = pd.Timestamp(bitis)
    b = b.tz_localize("UTC") if b.tzinfo is None else b.tz_convert("UTC")
    return min(b, KILIT_BASLANGIC)


# Açılış kaydı (denetim Ö10): her okumada satır yazmak binlerce satır üretiyordu. Bir süreç içinde aynı
# (günlük yolu, gerekçe, veri türü, yığın/aşama) anahtarı için İLK açılış hemen yazılır ("tur": "ilk", eski biçim);
# sonraki okumalar bellekte toplanır ve süreç sonunda (atexit + multiprocessing işçi çıkışı) ya da OZET_ARALIK_SN
# aralıkla tek "ozet" satırı yazılır: {zaman_ilk, zaman_son, gerekce, veri, yigin, semboller, n_okuma, pid}.
# Fork havuzunda her işçi kendi ilk/özet satırlarını yazar (çocukta bellek sıfırlanır; ebeveynin bekleyenleri iki kez yazılmaz).
OZET_ARALIK_SN = 3600.0
_kilit = threading.Lock()
_gorulen: set = set()          # ilk satırı yazılmış anahtarlar
_bekleyen: dict = {}           # anahtar -> {zaman_ilk, zaman_son, semboller, n_okuma}
_son_bosaltma = time.monotonic()
_kayitli_pid = None            # çıkış kancalarının kurulduğu süreç


def _satir_yaz(yol: Path, kayit: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def _kancalari_kur() -> None:
    global _kayitli_pid
    if _kayitli_pid == os.getpid():
        return
    _kayitli_pid = os.getpid()
    atexit.register(kilit_ozet_yaz)
    mp_util.Finalize(None, kilit_ozet_yaz, exitpriority=100)   # Pool/Process işçisi os._exit ile çıkar; atexit çalışmaz


def kilit_acilisi_yaz(sembol: str, ne: str, gerekce: str) -> None:
    global _son_bosaltma
    yigin = [f"{Path(f.filename).name}:{f.lineno}:{f.name}"
             for f in traceback.extract_stack()[:-2]
             if "pytest" not in f.filename and "pluggy" not in f.filename][-4:]
    zaman = datetime.now(timezone.utc).isoformat()
    yol = kilit_log_yolu()
    anahtar = (str(yol), gerekce, ne, tuple(yigin))
    with _kilit:
        if anahtar not in _gorulen:
            _gorulen.add(anahtar)
            _satir_yaz(yol, {"zaman": zaman, "sembol": sembol, "veri": ne, "gerekce": gerekce, "yigin": yigin,
                             "tur": "ilk", "pid": os.getpid()})
        b = _bekleyen.setdefault(anahtar, {"zaman_ilk": zaman, "zaman_son": zaman, "semboller": set(), "n_okuma": 0})
        b["zaman_son"] = zaman
        b["semboller"].add(sembol)
        b["n_okuma"] += 1
        _kancalari_kur()
        bosalt = time.monotonic() - _son_bosaltma >= OZET_ARALIK_SN
    if bosalt:
        kilit_ozet_yaz()


def kilit_ozet_yaz() -> int:
    """Bekleyen okumaları anahtar başına tek "ozet" satırı olarak yazar ve belleği boşaltır. Yazılan satır sayısı döner."""
    global _son_bosaltma
    with _kilit:
        bekleyen = dict(_bekleyen)
        _bekleyen.clear()
        _son_bosaltma = time.monotonic()
    for (yol, gerekce, ne, yigin), b in bekleyen.items():
        _satir_yaz(Path(yol), {"tur": "ozet", "zaman": b["zaman_son"], "zaman_ilk": b["zaman_ilk"],
                               "zaman_son": b["zaman_son"], "gerekce": gerekce, "veri": ne, "yigin": list(yigin),
                               "semboller": sorted(b["semboller"]), "n_okuma": b["n_okuma"], "pid": os.getpid()})
    return len(bekleyen)


def _sifirla() -> None:
    """Süreç içi kayıt durumunu temizler (fork sonrası çocukta ve testlerde). Yazmaz."""
    global _kilit, _son_bosaltma
    _kilit = threading.Lock()
    _gorulen.clear()
    _bekleyen.clear()
    _son_bosaltma = time.monotonic()


def _fork_cocugu() -> None:
    global _kayitli_pid
    _sifirla()
    _kayitli_pid = None


os.register_at_fork(after_in_child=_fork_cocugu)
