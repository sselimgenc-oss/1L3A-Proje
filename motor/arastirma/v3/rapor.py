"""v3 eleme raporu: `sonuclar/v3/eleme.csv` (satır başına tüm kapı değerleri, p'ler, rapor ekleri, hata) ve `ELEME_RAPORU.md` (sade Türkçe
özet). Eleme sayıları performans beklentisi DEĞİLDİR (ON_KAYIT_V3 0.1); kanıt yalnız ileri veridir (bölüm 4)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from motor.arastirma.v3 import dondurma, sabit

KAPILAR_TEK = ("v1", "v2", "v3", "v4", "v5")
KAPILAR_PF = ("p1", "p2", "p3", "p4", "p5", "p6")
ON = ["no", "kart", "strateji", "tur", "tf", "evren", "bas", "durum", "gecti", "hata_turu", "hata", "nedenler"] + list(KAPILAR_TEK) + list(KAPILAR_PF)
KAPI_ACIKLAMA = {"v1": "Kârlılık (net×2 > 0 ve PF×1 eşiği)", "v2": "Örnek (işlem sayısı)", "v3": "Yoğunlaşma (en iyi yıl çıkarılınca ΣR > 0)",
                 "v4": "Rastgele girişten ayrışma (p)", "v5": "Hayatta kalma (kill yok)",
                 "p1": "Kârlılık (net×2 > 0 ve Sharpe×1 eşiği)", "p2": "Örnek (gün ve yeniden dengeleme)",
                 "p3": "Yoğunlaşma (en iyi yıl çıkarılınca net > 0)", "p4": "Rastgele ağırlıktan ayrışma (p)",
                 "p5": "Hayatta kalma (kill yok)", "p6": "Al-tut kıyası (Sharpe)"}


def satir_yolu(no: int) -> Path:
    return sabit.SATIR_DIZINI / f"satir_{no}.json"


def satirlari_oku(dizin: Path = sabit.SATIR_DIZINI) -> dict:
    out = {}
    for s in sabit.satirlar():
        y = Path(dizin) / f"satir_{s.no}.json"
        if y.exists():
            out[s.no] = json.loads(y.read_text(encoding="utf-8"))
    return out


def tablo_olustur(satirlar: dict) -> pd.DataFrame:
    """9 satır (koşulmayan: durum 'kosulmadi'; elenmiş değil, eksik). Sütunlar: ON + kalan alfabetik."""
    rows = []
    for s in sabit.satirlar():
        r = dict(satirlar.get(s.no) or {"no": s.no, "kart": s.kart, "strateji": s.strateji, "tur": s.tur, "tf": s.tf,
                                       "evren": ",".join(s.evren), "bas": "" if s.bas is None else str(s.bas.date()),
                                       "durum": "kosulmadi", "gecti": False})
        r.pop("hata_iz", None)
        rows.append(r)
    df = pd.DataFrame(rows)
    sut = [c for c in ON if c in df.columns]
    return df[sut + sorted(c for c in df.columns if c not in sut)]


def _g(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "yok"
    return "GEÇTİ" if bool(v) else "KALDI"


def _p(v) -> str:
    return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{float(v):.4f}"


def rapor_metni(df: pd.DataFrame, dd: dict) -> str:
    L = ["# v3 eleme raporu", "",
         "> Bu rapor yalnız ELEME sonucudur (geçmiş veri). Geçen strateji \"işe yarıyor\" sayılmaz; kanıt yalnız ileri veridir (ON_KAYIT_V3 bölüm 4). "
         "Buradaki sayılar performans beklentisi olarak okunmamalıdır.", "",
         f"- Dondurma: git `{dd['git_commit'][:12]}`, ön kayıt sha256 `{dd['on_kayit_sha256'][:12]}`, maliyet tablosu sha256 `{dd['maliyet_tablosu_sha256'][:12]}`",
         f"- Veri sonu: {dd['veri_sonu']}; tohum {dd['tohum']}; rastgele test tekrarı B = {dd['B']}", ""]
    gecen = df[df["durum"] == "gecti"]
    kosulmayan = df[df["durum"] == "kosulmadi"]
    L += [f"**Sonuç: {len(gecen)} / {len(df)} satır elemeyi geçti.**" + (f" ({len(kosulmayan)} satır henüz koşulmadı.)" if len(kosulmayan) else ""), ""]
    if len(gecen) == 0 and len(kosulmayan) == 0:
        L += ["Eleme sıfır strateji verdi; v3 sonucu \"0\"dır (bölüm 5). Eşik gevşetilmez, yeni varyant denenmez.", ""]
    L += ["| # | Kart | Tür | Durum | Kalan kapılar | p (rastgele) |", "|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        kap = KAPILAR_PF if r["tur"] == "portfoy" else KAPILAR_TEK
        kal = [k.upper() for k in kap if k in df.columns and r.get(k) is False]
        durum = {"gecti": "GEÇTİ", "elendi": "ELENDİ", "hata": "HATA (elendi)", "kosulmadi": "koşulmadı"}.get(r["durum"], r["durum"])
        L.append(f"| {r['no']} | {r['kart']} | {'portföy' if r['tur'] == 'portfoy' else 'tek grafik'} | {durum} | {', '.join(kal) or '-'} | {_p(r.get('p_rastgele'))} |")
    L += ["", "## Satır ayrıntıları (kapı sonuçları)", ""]
    for _, r in df.iterrows():
        L.append(f"### {r['no']}. {r['kart']}  ({r['strateji']})")
        if r["durum"] == "kosulmadi":
            L += ["Henüz koşulmadı.", ""]
            continue
        if r["durum"] == "hata":
            L += [f"HATA ({r.get('hata_turu', '')}): `{r.get('hata', '')}`. Hata veren satır elenmiş sayılır (bölüm 3).", ""]
            continue
        kap = KAPILAR_PF if r["tur"] == "portfoy" else KAPILAR_TEK
        for k in kap:
            L.append(f"- {k.upper()} {KAPI_ACIKLAMA[k]}: {_g(r.get(k))}")
        if isinstance(r.get("nedenler"), str) and r["nedenler"]:
            L.append(f"- Nedenler: {r['nedenler']}")
        L.append("")
    L += ["## Notlar", "",
          "- Rapor ekleri (Sharpe, düşüş, maliyet ×3, yıllara göre net, geniş stop ATR×20 koşusu, satır 7-8 tüm dönem, satır 9 BTCUSDT) `eleme.csv`'de; "
          "kapı değildir.",
          "- Hata veren satır elenmiş sayılır; altyapı hatası (veri okuma/bellek) hiçbir metrik üretilmeden olduysa bir kez yeniden koşulur ve "
          "\"Güncelleme\" olarak yazılır.", ""]
    return "\n".join(L)


def rapor_yaz(satir_dizini: Path = sabit.SATIR_DIZINI, csv_yol: Path = sabit.ELEME_CSV, md_yol: Path = sabit.RAPOR_MD,
              dondurma_yol: Path = sabit.DONDURMA, dogrula: bool = True) -> pd.DataFrame:
    """Satır sonuçlarından eleme.csv ve ELEME_RAPORU.md. dogrula: dondurma doğrulanır ve her satırın dondurma damgası eşleşmeli."""
    dd = dondurma.dogrula(dondurma_yol) if dogrula else dondurma.yukle(dondurma_yol)
    st = dondurma.sha256(dondurma_yol)
    satirlar = satirlari_oku(satir_dizini)
    for no, r in satirlar.items():
        if r.get("dondurma_sha256") != st:
            raise dondurma.DondurmaHatasi(f"satır {no}: dondurma damgası uyuşmuyor (başka bir dondurmayla koşulmuş)")
    df = tablo_olustur(satirlar)
    csv_yol, md_yol = Path(csv_yol), Path(md_yol)
    csv_yol.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_yol, index=False)
    md_yol.write_text(rapor_metni(df, dd), encoding="utf-8")
    return df
