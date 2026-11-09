"""Kalp atışı: paper motoru çalışırken düzenli zaman damgası yazar; yeniden başlatmadaki kesinti süresi bundan ölçülür.

Neden: olay kayıtlarında `yeniden_baslatma` olayının süresi yoktu (kesinti_olc ölçemiyordu). Artık motor
  - her turda (en çok `KALP_SN` = 60 sn'de bir diske) `durum/kalp_atisi.json` yazar ve aynı zamanı `paper_state.json` içinde de saklar
    (`kalp_atisi` alanı, kaydet ile birlikte); eski durum dosyasında bu alan yoktur (uyumluluk: `.get`);
  - başlarken ÖNCEKİ kalp atışını okur (dosya ile paper_state'in daha yenisi), "son kalp atışı -> başlangıç" aralığını
    `yeniden_baslatma` olayına "(A -> B)" biçiminde yazar (aylik_rapor.kesinti_olc bu aralığı okur);
  - düzgün kapanışta (SIGTERM/SIGINT) son bir kalp atışı yazar: kapanış ile açılış arası ölçülür.
Çökme (kill -9, elektrik) halinde kesinti ölçüsü en çok `KALP_SN` + tur süresi kadar eksik kalır (alt sınır, kesin değil).
Zamanlar UTC. Zaman damgasını çağıran verir (sunucu zamanı); bu modül saat okumaz.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from motor.canli import durum as d

DOSYA = "kalp_atisi.json"
SEMA = "1l3a.durum.kalp_atisi"
KALP_SN = 60


def yaz(dizin, zaman, baslangic, onceki: Optional[str] = None, durdu: bool = False) -> Path:
    """Atomik yazar. `baslangic`: bu sürecin başlangıç zamanı; `onceki`: başlarken bulunan önceki kalp atışı (yoksa None)."""
    veri = {"sema": SEMA, "surum": d.SURUM, "zaman": d.zaman_str(pd.Timestamp(zaman)), "baslangic": d.zaman_str(pd.Timestamp(baslangic)),
            "onceki_kalp_atisi": onceki, "durdu": bool(durdu), "aralik_sn": KALP_SN}
    return d.atomik_yaz_json(Path(dizin) / DOSYA, veri)


def oku(dizin) -> Optional[dict]:
    """Yoksa None (ilk çalışma / eski motor). Bozuksa DurumHatasi (çağıran olay olarak yazar; sessiz atlanmaz)."""
    yol = Path(dizin) / DOSYA
    if not yol.exists():
        return None
    try:
        v = json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise d.DurumHatasi(f"{DOSYA}: bozuk JSON ({e})") from e
    if not isinstance(v, dict) or "zaman" not in v:
        raise d.DurumHatasi(f"{DOSYA}: 'zaman' alanı yok")
    d._zaman_dogrula(v["zaman"], DOSYA)
    return v


def en_yeni(*zamanlar: Optional[str]) -> Optional[str]:
    """Verilen UTC ISO damgalarının en yenisi (None'lar yok sayılır)."""
    dolu = [z for z in zamanlar if z]
    return max(dolu, key=lambda z: pd.Timestamp(z)) if dolu else None


def kesinti(onceki: Optional[str], baslangic) -> dict:
    """-> {onceki, baslangic, sn (None: ölçülemedi), neden}. Önceki yoksa veya saat geri gittiyse sn None + neden."""
    b = pd.Timestamp(baslangic)
    b = b.tz_localize("UTC") if b.tzinfo is None else b.tz_convert("UTC")
    if not onceki:
        return {"onceki": None, "baslangic": d.zaman_str(b), "sn": None,
                "neden": "önceki kalp atışı kayıtlı değil (kalp atışından önceki durum dosyası): kesinti süresi ölçülemedi"}
    o = pd.Timestamp(onceki)
    o = o.tz_localize("UTC") if o.tzinfo is None else o.tz_convert("UTC")
    sn = (b - o).total_seconds()
    if sn < 0:
        return {"onceki": d.zaman_str(o), "baslangic": d.zaman_str(b), "sn": None,
                "neden": f"saat geri gitti (önceki kalp atışı {d.zaman_str(o)} > başlangıç {d.zaman_str(b)})"}
    return {"onceki": d.zaman_str(o), "baslangic": d.zaman_str(b), "sn": sn, "neden": None}


def olay_mesaji(k: dict) -> str:
    """`yeniden_baslatma` olay metni. Ölçülebildiyse "(A -> B)" aralığı tek parantez grubunda (kesinti_olc bunu okur)."""
    if k["sn"] is None:
        return f"Durum diskten yüklendi; kaçan mumlar REST'ten tamamlanacak. Kesinti süresi ölçülemedi: {k['neden']}"
    return (f"Durum diskten yüklendi; kesinti ({k['onceki']} -> {k['baslangic']}) = {k['sn']:.0f} sn "
            f"(son kalp atışından başlangıca); kaçan mumlar REST'ten tamamlanacak")
