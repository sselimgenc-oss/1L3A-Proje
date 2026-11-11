"""TEST D — düzenlilik teşhisi (ON_KAYIT_TESHIS.md'nin birebir uygulaması). TEŞHİS: ayar/varyant/strateji değişikliği YOK.
Veri: sonuclar/evren/v2/ham/x2 (maliyet ×2, funding dahil R). Yalnız < 2025-11-08 (sert doğrulama).

Tanımlar (ön kayıtlı):
- Takvim aralığı: ilk giriş ayından 2025-10'a (dahil) tüm aylar; yıllar ilk giriş yılından 2025'e. Aylık işlem sayısı GİRİŞ ayına
  göre; yıl/ay ΣR'si ÇIKIŞ zamanına göre (gerçekleşen).
- En uzun işlemsiz gün: ardışık iki GİRİŞ arası en büyük boşluk (gün), son girişten 2025-11-08'e kadar kuyruk dahil.
- En iyi %5 işlem: k = ceil(0.05 n). Pay = en iyi k işlemin ΣR'si / toplam ΣR (toplam <= 0 ise pay NaN).
- Ardışık kaybeden: çıkış zamanına göre sıralı r < 0 serisi (tüm semboller birlikte).
- Düşüş süresi: kümülatif R (çıkış sırası) zirvesinden yeni zirveye (ya da 2025-11-08'e) kadar en uzun gün.
- pf__ (portföy): işlem yerine günlük getiri; "işlem" = dengeleme günü; ΣR yerine ΣGünlükGetiri (yüzde puan); en iyi %5 GÜN;
  sembol ve seri ölçüleri uygulanmaz.
Kullanım: python araclar/teshis_duzenlilik.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "sonuclar" / "evren" / "v2" / "ham" / "x2"
CIKTI = KOK / "sonuclar" / "teshis" / "duzenlilik"
HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")
SON_AY = pd.Period("2025-10", "M")
STRATEJILER = ["dis__e0v1en", "dis__ewo-ema-ofset", "dis__hma-atr-rider", "dis__lube", "dis__gauss-stoch-eth",
               "dis__haftalik-macd-gunluk-ma", "dis__uc-ortalama-boga-sma60", "dis__jt-awesome-osilator",
               "dis__voltarget-trend"]
PF = "pf__sabit_sepet"
AY_ESIK, YIL_ESIK = 0.80, 0.70


def _per(ts, f):
    """Dönem etiketi. Veri sonunda zorunlu kapanan işlemin çıkış damgası = 2025-11-08 00:00 (son geliştirme mumunun bitişi);
    dönem ataması için 1 ns geriye alınır (2025-11'e taşmaz)."""
    t = pd.DatetimeIndex(ts).as_unit("ns").tz_convert("UTC")
    t = t.where(t < HOLDOUT_BAS, HOLDOUT_BAS - pd.Timedelta(1, "ns"))
    return t.tz_localize(None).to_period(f)


def _u(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def en_uzun_bosluk_gun(giris, bitis=HOLDOUT_BAS) -> float:
    g = np.sort(pd.DatetimeIndex(giris).as_unit("ns").asi8)
    b = _u(bitis).as_unit("ns").value
    adaylar = list(np.diff(g)) + [b - g[-1]]
    return float(max(adaylar) / 86_400e9)


def en_uzun_kayip_serisi(r) -> int:
    en, s = 0, 0
    for x in r:
        s = s + 1 if x < 0 else 0
        en = max(en, s)
    return en


def en_uzun_dusus_gun(zaman, r, baslangic, bitis=HOLDOUT_BAS) -> float:
    """zaman: çıkış zamanları (sıralı), r: o andaki getiri. Zirve = max(0, kümülatif)."""
    cum = np.cumsum(np.asarray(r, float))
    t = pd.DatetimeIndex(zaman)
    zirve, t_zirve, en = 0.0, _u(baslangic), 0.0
    for tt, c in zip(t, cum):
        if c >= zirve:
            en = max(en, (tt - t_zirve).total_seconds() / 86400)
            zirve, t_zirve = c, tt
    if cum[-1] < zirve:                      # dönem sonunda hâlâ zirvenin altında
        en = max(en, (_u(bitis) - t_zirve).total_seconds() / 86400)
    return float(en)


def en_iyi_pay(r, oran=0.05, adet=None):
    r = np.sort(np.asarray(r, float))[::-1]
    k = adet if adet is not None else max(1, math.ceil(oran * len(r)))
    top, toplam = float(r[:k].sum()), float(r.sum())
    return (top / toplam if toplam > 0 else np.nan), toplam - top, k


def etiketle(ay_pct, yil_pct, kalan5) -> tuple:
    tutmayan = []
    if not ay_pct >= AY_ESIK * 100:
        tutmayan.append(f"işlemli ay %{ay_pct:.0f} < %80")
    if not yil_pct >= YIL_ESIK * 100:
        tutmayan.append(f"artı yıl %{yil_pct:.0f} < %70")
    if not kalan5 > 0:
        tutmayan.append("en iyi %5 çıkınca ΣR <= 0")
    return ("DÜZENLİ" if not tutmayan else "DÜZENSİZ"), "; ".join(tutmayan)


def _takvim(ilk_giris):
    aylar = pd.period_range(_per([ilk_giris], "M")[0], SON_AY, freq="M")
    yillar = pd.period_range(aylar[0].asfreq("Y"), SON_AY.asfreq("Y"), freq="Y")
    return aylar, yillar


def olc_islem(d: pd.DataFrame) -> dict:
    """d: giris_zamani, cikis_zamani, r, sembol."""
    if d["cikis_zamani"].max() > HOLDOUT_BAS or d["giris_zamani"].max() >= HOLDOUT_BAS:       # Ek-1: çıkış == HOLDOUT_BAS serbest
        raise RuntimeError("tarih sınırı aşıldı")
    d = d.sort_values(["cikis_zamani", "giris_zamani"], kind="stable").reset_index(drop=True)
    r = d["r"].to_numpy(float)
    aylar, yillar = _takvim(d["giris_zamani"].min())
    ay_say = pd.Series(_per(d["giris_zamani"], "M")).value_counts().reindex(aylar, fill_value=0)
    ay_r = pd.Series(r, index=_per(d["cikis_zamani"], "M")).groupby(level=0).sum().reindex(aylar, fill_value=0.0)
    yil_r = pd.Series(r, index=_per(d["cikis_zamani"], "Y")).groupby(level=0).sum().reindex(yillar, fill_value=0.0)
    p5, kalan5, k5 = en_iyi_pay(r, 0.05)
    p10, _, _ = en_iyi_pay(r, adet=10)
    sem = d.groupby("sembol")["r"].sum()
    ay_pct = float((ay_say >= 1).mean() * 100)
    yil_pct = float((yil_r > 0).mean() * 100)
    et, neden = etiketle(ay_pct, yil_pct, kalan5)
    return {"n_islem": len(d), "n_veri_sonu_kapanis": int((d["cikis_zamani"] == HOLDOUT_BAS).sum()), "n_ay": len(aylar), "ayda_ort_islem": float(ay_say.mean()), "ayda_medyan_islem": float(ay_say.median()),
            "islemli_ay_pct": ay_pct, "en_uzun_islemsiz_gun": en_uzun_bosluk_gun(d["giris_zamani"]),
            "yil_r": {str(k): float(v) for k, v in yil_r.items()}, "n_yil": len(yillar), "arti_yil": int((yil_r > 0).sum()),
            "arti_yil_pct": yil_pct, "arti_ay_pct": float((ay_r > 0).mean() * 100), "toplam_sigma": float(r.sum()),
            "en_iyi10_pay": p10, "en_iyi5pct_adet": k5, "en_iyi5pct_pay": p5, "en_iyi5pct_cikinca_sigma": kalan5,
            "en_iyi_sembol": str(sem.idxmax()), "en_iyi_sembol_cikinca_sigma": float(r.sum() - sem.max()),
            "en_uzun_kayip_serisi": en_uzun_kayip_serisi(r),
            "en_uzun_dusus_gun": en_uzun_dusus_gun(d["cikis_zamani"], r, d["giris_zamani"].min()),
            "etiket": et, "tutmayan": neden, "birim": "R"}


def olc_portfoy(g: pd.DataFrame) -> dict:
    """g: gun, getiri, dengeleme (günlük). Yüzde puan cinsinden."""
    g = g[g["gun"] < HOLDOUT_BAS]
    g = g.sort_values("gun").reset_index(drop=True)
    nz = g.index[g["getiri"] != 0]
    g = g.loc[nz[0]:].reset_index(drop=True)
    x = g["getiri"].to_numpy(float) * 100
    aylar, yillar = _takvim(g["gun"].iloc[0])
    deng = g[g["dengeleme"]]
    ay_say = pd.Series(_per(deng["gun"], "M")).value_counts().reindex(aylar, fill_value=0)
    ay_r = pd.Series(x, index=_per(g["gun"], "M")).groupby(level=0).sum().reindex(aylar, fill_value=0.0)
    yil_r = pd.Series(x, index=_per(g["gun"], "Y")).groupby(level=0).sum().reindex(yillar, fill_value=0.0)
    p5, kalan5, k5 = en_iyi_pay(x, 0.05)
    p10, _, _ = en_iyi_pay(x, adet=10)
    ay_pct, yil_pct = float((ay_say >= 1).mean() * 100), float((yil_r > 0).mean() * 100)
    et, neden = etiketle(ay_pct, yil_pct, kalan5)
    return {"n_islem": int(len(deng)), "n_veri_sonu_kapanis": 0, "n_ay": len(aylar), "ayda_ort_islem": float(ay_say.mean()), "ayda_medyan_islem": float(ay_say.median()),
            "islemli_ay_pct": ay_pct, "en_uzun_islemsiz_gun": en_uzun_bosluk_gun(deng["gun"]),
            "yil_r": {str(k): float(v) for k, v in yil_r.items()}, "n_yil": len(yillar), "arti_yil": int((yil_r > 0).sum()),
            "arti_yil_pct": yil_pct, "arti_ay_pct": float((ay_r > 0).mean() * 100), "toplam_sigma": float(x.sum()),
            "en_iyi10_pay": p10, "en_iyi5pct_adet": k5, "en_iyi5pct_pay": p5, "en_iyi5pct_cikinca_sigma": kalan5,
            "en_iyi_sembol": "", "en_iyi_sembol_cikinca_sigma": np.nan, "en_uzun_kayip_serisi": np.nan,
            "en_uzun_dusus_gun": en_uzun_dusus_gun(g["gun"], x, g["gun"].iloc[0]),
            "etiket": et, "tutmayan": neden, "birim": "yüzde puan (günlük getiri toplamı; en iyi %5 = gün)"}


def ham_yukle(strateji: str) -> pd.DataFrame:
    parcalar = []
    for p in sorted(HAM.glob(f"{strateji}--*--*.parquet")):
        _, tf, sembol = p.stem.split("--")
        meta = json.loads(p.with_suffix(".json").read_text())
        if meta.get("hata"):
            raise RuntimeError(f"{p.name}: ham hata: {meta['hata']}")
        if meta.get("veri_yok"):
            continue
        df = pd.read_parquet(p)
        if len(df):
            parcalar.append(df.assign(sembol=sembol))
    if not parcalar:
        raise RuntimeError(f"{strateji}: ham dosya yok")
    return pd.concat(parcalar, ignore_index=True)


def main():
    CIKTI.mkdir(parents=True, exist_ok=True)
    satir = []
    for s in STRATEJILER:
        o = {"strateji": s, **olc_islem(ham_yukle(s))}
        satir.append(o); print(s, o["etiket"], o["tutmayan"], flush=True)
    g = pd.read_parquet(HAM / f"{PF}--1d--_PORTFOY.parquet")
    satir.append({"strateji": PF, **olc_portfoy(g)})
    print(PF, satir[-1]["etiket"], satir[-1]["tutmayan"])
    df = pd.DataFrame(satir)
    df.assign(yil_r=df["yil_r"].map(lambda v: json.dumps(v))).to_csv(CIKTI / "sonuc.csv", index=False)
    json.dump({r["strateji"]: r for r in satir}, open(CIKTI / "ozet.json", "w"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    sys.exit(main())
