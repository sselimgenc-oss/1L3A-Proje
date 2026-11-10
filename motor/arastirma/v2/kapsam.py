"""B16b: kimlik damgasının otomatik kapsamı — proje-içi import kapanışı (statik AST; kod ÇALIŞTIRILMAZ).

Elle yazılmış modül listesi, paylaşılan gösterge modüllerini (gostergeler_b2, pivotlar, ...) kaçırıyordu. Burada bir kök dosyadan
başlayıp proje içindeki her `import` / `from .. import ..` bağını (fonksiyon içi tembel import dahil) izleyerek TÜM dosya kümesi bulunur;
damga bu kümenin içerik özetinden hesaplanır. Yeni bir import eklenince kapsam kendiliğinden genişler.
Yalnız dosya sistemindeki proje dosyaları izlenir (stdlib/üçüncü taraf paketler dosya sisteminde yok -> dışarıda kalır).
Sonuç sıralı ve deterministiktir. Sözdizimi hatalı dosya sessizce atlanmaz (SyntaxError yukarı çıkar)."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from motor.arastirma import wf_evren as we

_GRAF: dict = {}                  # göreli yol -> {göreli yol}: dosyanın doğrudan proje-içi bağları


def onbellegi_sifirla() -> None:
    _GRAF.clear()


def _dosya_var(rel: Path) -> bool:
    return (we.KOK / rel).is_file()


def _modul_dosyalari(parcalar: list) -> list:
    """['motor','strateji','kayit'] -> [motor/__init__.py, motor/strateji/__init__.py, motor/strateji/kayit.py] (var olanlar; bir
    modül içe aktarılınca üst paketlerin __init__'i de çalışır). Proje dışı ad (stdlib / üçüncü taraf): []."""
    if not (_dosya_var(Path(parcalar[0]) / "__init__.py") or _dosya_var(Path(parcalar[0] + ".py"))):
        return []
    out = []
    for i in range(1, len(parcalar) + 1):
        yol = Path(*parcalar[:i])
        if i == len(parcalar) and _dosya_var(yol.with_suffix(".py")):
            out.append(yol.with_suffix(".py"))
        elif _dosya_var(yol / "__init__.py"):
            out.append(yol / "__init__.py")
    return out


def _dogrudan(rel: Path) -> set:
    """rel dosyasının doğrudan proje-içi bağları (fonksiyon içi tembel importlar dahil: kapsam geniş tarafta kalır)."""
    k = str(rel)
    if k in _GRAF:
        return _GRAF[k]
    kaynak = (we.KOK / rel).read_text(encoding="utf-8")
    agac = ast.parse(kaynak, filename=str(rel))
    paket = list(rel.parent.parts)
    bulunan: set = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            for a in d.names:
                bulunan.update(_modul_dosyalari(a.name.split(".")))
        elif isinstance(d, ast.ImportFrom):
            if d.level:
                taban = paket[: len(paket) - (d.level - 1)] if d.level > 1 else paket
                modul = taban + (d.module.split(".") if d.module else [])
            else:
                modul = d.module.split(".") if d.module else []
            if not modul:
                continue
            bulunan.update(_modul_dosyalari(modul))
            for a in d.names:                            # `from paket import altmodul`
                if a.name != "*":
                    alt = _modul_dosyalari(modul + [a.name])
                    if alt and alt[-1].stem == a.name:
                        bulunan.update(alt)
    bulunan.discard(rel)
    _GRAF[k] = bulunan
    return bulunan


def kapanis(kokler: Iterable[str]) -> list:
    """kokler (KOK'a göre göreli yollar) ve onlardan proje-içi import zinciriyle ulaşılan tüm .py dosyaları. -> sıralı göreli yol
    (posix) listesi. Var olmayan kök: FileNotFoundError (kapsam sessizce daralmaz)."""
    gorulen: set = set()
    bekleyen = []
    for y in kokler:
        p = Path(y)
        if not _dosya_var(p):
            raise FileNotFoundError(f"kapsam kökü yok: {y}")
        bekleyen.append(p)
    while bekleyen:
        p = bekleyen.pop()
        if p in gorulen:
            continue
        gorulen.add(p)
        bekleyen.extend(_dogrudan(p) - gorulen)
    return sorted(g.as_posix() for g in gorulen)
