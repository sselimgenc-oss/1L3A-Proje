"""Dondurma (ON_KAYIT_V3 bölüm 6): ön kayıt, strateji kaynakları, ortak motor modülleri, v3 koşu kodu, maliyet tablosu ve girdi
dosyalarının sha256'sı + git commit `sonuclar/v3/dondurma.json`'a yazılır. `dogrula()` herhangi bir hash farklıysa
`DondurmaHatasi` fırlatır: eleme koşusu DURUR (koşu başladıktan sonra kod değişirse koşu geçersizdir)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Callable, Optional

from motor.arastirma.v3 import sabit

SURUM = 1
_V3_KOK = "motor/arastirma/v3/__main__.py"
_GIT_ZAMAN_ASIMI = 90
_FARK_GOSTER = 25                       # hata iletisinde en çok bu kadar fark yazılır (eşik değil)


class DondurmaHatasi(RuntimeError):
    """Dondurma yok / bozuk / herhangi bir hash farklı: eleme çalışmaz."""


def sha256(yol) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def _rel(p: Path) -> str:
    return Path(p).resolve().relative_to(sabit.KOK).as_posix()


_ON_KAYIT_REL, _MALIYET_V1_REL, _MALIYET_V2_REL = _rel(sabit.ON_KAYIT), _rel(sabit.MALIYET_V1), _rel(sabit.MALIYET_V2)


def girdi_kumeleri() -> dict:
    """{küme adı: [KOK'a göre göreli yol]} — dondurulan dosyalar. Strateji kaynakları v2 ile aynı yöntemle (sınıf + ata modülleri +
    import kapanışı); motor kümeleri v2 `ham.motor_hash_girdisi(_pf)` (otomatik import kapanışı); v3 kodu `__main__` kapanışı."""
    from motor.arastirma.v2 import ham as hm
    from motor.arastirma.v2 import kapsam
    from motor.arastirma import wf_evren_holdout as v1h
    from motor.strateji import kayit
    hm.damga_onbellegini_sifirla()
    k = {"on_kayit": [_rel(sabit.ON_KAYIT)], "kodlama_csv": [_rel(sabit.KODLAMA_CSV)],
         "maliyet": [_rel(sabit.MALIYET_V1), _rel(sabit.MALIYET_V2)], "girdi_takvim": [_rel(sabit.FOMC_CSV)]}
    for s in sabit.satirlar():
        stil = "portfoy" if s.tur == "portfoy" else kayit.al(s.strateji).stil
        dosyalar = [y for y in v1h.strateji_dosyalari(s.strateji, stil) if y.endswith(".py") or y.endswith(".json")]
        py = [y for y in dosyalar if y.endswith(".py")]
        k[f"strateji:{s.strateji}"] = sorted(set(dosyalar) | set(kapsam.kapanis(py)))
    k["motor"] = sorted(set(hm.motor_hash_girdisi()))
    k["motor_pf"] = sorted(set(hm.motor_hash_girdisi_pf()))
    k["v3_kod"] = kapsam.kapanis([_V3_KOK])
    return k


def ozet(kumeler: dict, kok: Optional[Path] = None) -> dict:
    """{küme: {yol: sha256}} (dosya yoksa '' — sonradan eklenir/silinirse fark çıkar)."""
    kok = Path(kok or sabit.KOK)
    return {ad: {y: (sha256(kok / y) if (kok / y).is_file() else "") for y in sorted(yollar)} for ad, yollar in sorted(kumeler.items())}


def git_commit() -> str:
    from motor.arastirma import wf_evren_holdout as v1h
    return v1h.git_commit()


def kirli_dosyalar(kumeler: dict, kok: Optional[Path] = None) -> list:
    """Dondurulan dosyalardan commit edilmemiş (değişmiş/izlenmeyen) olanlar. git yoksa/depo değilse hata (sessiz geçmez)."""
    yollar = sorted({y for yl in kumeler.values() for y in yl})
    r = subprocess.run(["git", "status", "--porcelain", "--"] + yollar, cwd=kok or sabit.KOK, capture_output=True, text=True, timeout=_GIT_ZAMAN_ASIMI)
    if r.returncode != 0:
        raise DondurmaHatasi(f"git status çalışmadı: {r.stderr.strip()[:200]}")
    return [satir[3:] for satir in r.stdout.splitlines() if satir.strip()]


def hesapla(kumeler: Optional[dict] = None, kok: Optional[Path] = None, commit: Optional[str] = None) -> dict:
    kumeler = girdi_kumeleri() if kumeler is None else kumeler
    h = ozet(kumeler, kok)
    return {"surum": SURUM, "on_kayit_sha256": h.get("on_kayit", {}).get(_ON_KAYIT_REL, ""), "git_commit": git_commit() if commit is None else commit,
            "satirlar": [{"no": s.no, "kart": s.kart, "strateji": s.strateji, "tur": s.tur, "tf": s.tf, "evren": list(s.evren),
                          "rapor_evren": list(s.rapor_evren), "bas": "" if s.bas is None else str(s.bas.date())} for s in sabit.satirlar()],
            "veri_sonu": str(sabit.VERI_SONU), "tohum": sabit.TOHUM, "B": sabit.B,
            "maliyet_tablosu_sha256": h.get("maliyet", {}).get(_MALIYET_V1_REL, ""),
            "maliyet_tablosu_v2_sha256": h.get("maliyet", {}).get(_MALIYET_V2_REL, ""),
            "dosyalar": h}


def yaz(yol: Optional[Path] = None, kumeler: Optional[dict] = None, kok: Optional[Path] = None, commit: Optional[str] = None,
        git_kontrol: bool = True) -> dict:
    """dondurma.json'u yazar. git_kontrol: dondurulan dosyalarda commit edilmemiş değişiklik varsa DondurmaHatasi (koşu dondurma
    commit'inden yapılır). Var olan dondurma ÜZERİNE YAZILMAZ (yeniden dondurmak için dosya elle silinmeli)."""
    yol, kok = Path(yol or sabit.DONDURMA), Path(kok or sabit.KOK)
    if yol.exists():
        raise DondurmaHatasi(f"{yol.name} zaten var; dondurma değiştirilemez (yeniden dondurmak için dosyayı bilinçli silin)")
    kumeler = girdi_kumeleri() if kumeler is None else kumeler
    if git_kontrol:
        kirli = kirli_dosyalar(kumeler, kok)
        if kirli:
            raise DondurmaHatasi(f"commit edilmemiş dondurulan dosyalar: {', '.join(kirli[:10])}")
    d = hesapla(kumeler, kok, commit)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return d


def yukle(yol: Optional[Path] = None) -> dict:
    yol = Path(yol or sabit.DONDURMA)
    if not yol.exists():
        raise DondurmaHatasi(f"{yol} yok: önce `python -m motor.arastirma.v3 dondur`")
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
    except ValueError as e:
        raise DondurmaHatasi(f"{yol.name} okunamadı: {e}") from e
    if d.get("surum") != SURUM or "dosyalar" not in d:
        raise DondurmaHatasi(f"{yol.name}: şema sürümü/içeriği geçersiz")
    return d


def dogrula(yol: Optional[Path] = None, kumeler_fn: Optional[Callable] = None, kok: Optional[Path] = None, commit_kontrol: bool = True) -> dict:
    """Şimdiki dosyaları dondurmayla karşılaştırır. Herhangi bir hash farklı / dosya eklenmiş-silinmiş / sabitler (veri sonu, tohum, B,
    satır listesi) farklı / kayıtlı commit HEAD'in atası değil -> DondurmaHatasi (eleme durur). -> yüklenen dondurma sözlüğü."""
    yol, kok = Path(yol or sabit.DONDURMA), Path(kok or sabit.KOK)
    d = yukle(yol)
    simdi = hesapla((kumeler_fn or girdi_kumeleri)(), kok, d["git_commit"])
    fark = []
    for ad in sorted(set(d["dosyalar"]) | set(simdi["dosyalar"])):
        a, b = d["dosyalar"].get(ad), simdi["dosyalar"].get(ad)
        if a is None or b is None:
            fark.append(f"{ad}: küme {'eksik' if b is None else 'yeni'}")
            continue
        for y in sorted(set(a) | set(b)):
            if a.get(y) != b.get(y):
                fark.append(f"{ad}: {y} " + ("yok" if y not in b else "yeni" if y not in a else "değişmiş"))
    for anahtar in ("on_kayit_sha256", "maliyet_tablosu_sha256", "maliyet_tablosu_v2_sha256", "veri_sonu", "tohum", "B", "satirlar"):
        if d.get(anahtar) != simdi.get(anahtar):
            fark.append(f"{anahtar} farklı")
    if commit_kontrol:
        from motor.arastirma import wf_evren_holdout as v1h
        if not v1h._commit_ata_mi(str(d["git_commit"]), git_commit()):
            fark.append(f"git_commit {d['git_commit']} şimdiki HEAD'in atası değil")
    if fark:
        raise DondurmaHatasi("dondurma ihlali (eleme durur): " + "; ".join(fark[:_FARK_GOSTER]) + (f" (+{len(fark) - _FARK_GOSTER})" if len(fark) > _FARK_GOSTER else ""))
    return d
