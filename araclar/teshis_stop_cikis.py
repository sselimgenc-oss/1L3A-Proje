"""TEST C — stop/çıkış teşhisi (ON_KAYIT_TESHIS.md'nin birebir uygulaması). TEŞHİS (descriptive): ayar arama, varyant
optimizasyonu, "ne olurdu" simülasyonu YOK. Yalnız geliştirme dönemi (< 2025-11-08; yüklemede süzülür, sonda sert doğrulanır).

Giriş fiyatı ham dosyada YOK. Türetme: motor girişi, işlem zaman ölçeğindeki (tf) giriş mumunun AÇILIŞINDA doldurur
(motor.py: bekleyen_giris -> açılış ± kayma). giris_zamani = o mumun açılış anı. Giriş fiyatı = en ince fiyat serisinde
[giris_zamani, giris_zamani + tf) içindeki İLK mumun açılışı (kayma payı hariç: stop mesafesinin çok küçük bir kesri).
Pencere (alt sınır): en ince mumlardan açılışı [giris_zamani + tf, cikis_zamani) olanlar = giriş tf-mumundan SONRAKİ,
çıkış tf-mumundan ÖNCEKİ. Uçlar (giriş mumu ve çıkış mumu) dışarıda => MAE/MFE gerçek değerin ALT SINIRI. Boş pencere => 0.
Fiyat serisi: kripto 5m; DK_ (hisse/emtia) 1h (motorun kullandığı kaynak; DK 5m eksik günlü).
Kullanım: python araclar/teshis_stop_cikis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "sonuclar" / "evren" / "v2" / "ham" / "x2"
MUM = KOK / "veri" / "mumlar"
CIKTI = KOK / "sonuclar" / "teshis" / "stop_cikis"

HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")
STRATEJILER = ["dis__e0v1en", "dis__ewo-ema-ofset", "dis__hma-atr-rider", "dis__lube", "dis__gauss-stoch-eth",
               "dis__haftalik-macd-gunluk-ma", "dis__uc-ortalama-boga-sma60", "dis__jt-awesome-osilator",
               "dis__voltarget-trend"]
TF_SURE = {"1d": pd.Timedelta("1D"), "15m": pd.Timedelta("15min")}
# ön kayıtlı eşikler
TAM_STOP_ESIK = -0.85          # kayıp r <= bu => "tam stop" (−1R ± maliyet, boşluk dahil)
MAE_ESIK = (0.5, 0.8)
MFE_ESIK = (0.5, 1.0, 2.0)


def sinifla(kazanma: float, payoff: float) -> str:
    if kazanma <= 0.45 and payoff >= 2:
        return "kayıp kısa / kâr uzun"
    if kazanma >= 0.60 and payoff < 1:
        return "çok kazan az kazan"
    return "karma"


def mae_mfe(yon, gf, sm, g_ns, c_ns, dur_ns, t_ns, hi, lo):
    """(mae_r, mfe_r, n_mum). Pencere: açılışı [g+dur, c) olan mumlar. Boş pencere -> (0,0,0). Yöne göre."""
    a = int(np.searchsorted(t_ns, g_ns + dur_ns, side="left"))
    b = int(np.searchsorted(t_ns, c_ns, side="left"))
    if b <= a:
        return 0.0, 0.0, 0
    h = float(hi[a:b].max())
    l = float(lo[a:b].min())
    if yon > 0:
        mfe, mae = (h - gf) / sm, (gf - l) / sm
    else:
        mfe, mae = (gf - l) / sm, (h - gf) / sm
    return max(mae, 0.0), max(mfe, 0.0), b - a


def giris_fiyati(g_ns, dur_ns, t_ns, acilis):
    i = int(np.searchsorted(t_ns, g_ns, side="left"))
    if i >= len(t_ns) or t_ns[i] >= g_ns + dur_ns:
        return np.nan
    return float(acilis[i])


def mum_yukle(sembol: str):
    """-> (t_ns, acilis, yuksek, dusuk); yalnız < HOLDOUT_BAS (sert)."""
    dosya = "1h.parquet" if sembol.startswith("DK_") else "5m.parquet"
    m = pd.read_parquet(MUM / sembol / dosya, columns=["acilis", "yuksek", "dusuk"])
    m = m[m.index < HOLDOUT_BAS]
    if len(m) and m.index.max() >= HOLDOUT_BAS:
        raise RuntimeError("holdout verisi okundu")
    return m.index.as_unit("ns").asi8, m["acilis"].to_numpy(float), m["yuksek"].to_numpy(float), m["dusuk"].to_numpy(float)


def islem_olc(df: pd.DataFrame, sembol: str, tf: str) -> pd.DataFrame:
    """Ham işlem tablosu -> MAE/MFE sütunları eklenmiş tablo (sm geçersizse NaN)."""
    if len(df) and (df["cikis_zamani"].max() >= HOLDOUT_BAS or df["giris_zamani"].max() >= HOLDOUT_BAS):
        raise RuntimeError(f"{sembol}: işlem tarihi geliştirme dönemi dışında")
    t, o, h, l = mum_yukle(sembol)
    dur = TF_SURE[tf].value
    g = pd.DatetimeIndex(df["giris_zamani"]).as_unit("ns").asi8
    c = pd.DatetimeIndex(df["cikis_zamani"]).as_unit("ns").asi8
    yon = df["yon"].to_numpy(); sm = df["stop_mesafe"].to_numpy(float)
    mae = np.full(len(df), np.nan); mfe = np.full(len(df), np.nan); nm = np.zeros(len(df), int); gfy = np.full(len(df), np.nan)
    for i in range(len(df)):
        if not (np.isfinite(sm[i]) and sm[i] > 0) or c[i] <= g[i]:
            continue
        gf = giris_fiyati(g[i], dur, t, o)
        gfy[i] = gf
        if not np.isfinite(gf):
            continue
        mae[i], mfe[i], nm[i] = mae_mfe(yon[i], gf, sm[i], g[i], c[i], dur, t, h, l)
    out = df.copy()
    out["sembol"], out["tf"] = sembol, tf
    out["giris_fiyati_turetilen"], out["mae_r"], out["mfe_r"], out["n_mum_pencere"] = gfy, mae, mfe, nm
    return out


def _yuzde(x, esik):
    return float((x >= esik).mean() * 100) if len(x) else np.nan


def strateji_olcu(d: pd.DataFrame) -> dict:
    """d: r, mae_r, mfe_r, giris_zamani, cikis_zamani (MAE/MFE NaN olanlar yalnız MAE/MFE ölçülerinden çıkar)."""
    r = d["r"].to_numpy(float)
    kaz = r > 0
    n = len(d)
    ok = d["mae_r"].notna().to_numpy()
    sure = (pd.to_datetime(d["cikis_zamani"], utc=True) - pd.to_datetime(d["giris_zamani"], utc=True)).dt.total_seconds().to_numpy() / 86400
    ort_k = float(r[kaz].mean()) if kaz.any() else np.nan
    ort_l = float(r[~kaz].mean()) if (~kaz).any() else np.nan
    payoff = ort_k / abs(ort_l) if np.isfinite(ort_k) and np.isfinite(ort_l) and ort_l != 0 else np.nan
    kazanma = float(kaz.mean()) if n else np.nan
    mk = d.loc[kaz & ok, "mae_r"].to_numpy(float)
    fl = d.loc[(~kaz) & ok, "mfe_r"].to_numpy(float)
    geri = (d.loc[kaz & ok, "mfe_r"] - d.loc[kaz & ok, "r"]).to_numpy(float)
    kayip_r = r[~kaz]
    o = {"n_islem": n, "n_mae_mfe_olculen": int(ok.sum()), "n_pencere_bos": int(((d["n_mum_pencere"] == 0) & ok).sum()),
         "kazanma_orani": kazanma, "ort_kazanc_r": ort_k, "ort_kayip_r": ort_l, "payoff": payoff, "beklenti_r": float(r.mean()),
         "tip": sinifla(kazanma, payoff) if np.isfinite(payoff) else "karma",
         "kaz_mae_medyan": float(np.median(mk)), "kaz_mae_p75": float(np.percentile(mk, 75)), "kaz_mae_p90": float(np.percentile(mk, 90)),
         "kaz_pct_mae_05": _yuzde(mk, 0.5), "kaz_pct_mae_08": _yuzde(mk, 0.8),
         "kay_pct_mfe_05": _yuzde(fl, 0.5), "kay_pct_mfe_1": _yuzde(fl, 1.0), "kay_pct_mfe_2": _yuzde(fl, 2.0),
         "kaz_geri_verilen_medyan": float(np.median(geri)),
         "sure_gun_medyan_kazanan": float(np.median(sure[kaz])) if kaz.any() else np.nan,
         "sure_gun_medyan_kaybeden": float(np.median(sure[~kaz])) if (~kaz).any() else np.nan,
         "kayip_pct_tam_stop": float((kayip_r <= TAM_STOP_ESIK).mean() * 100) if len(kayip_r) else np.nan,
         "kayip_pct_kucuk": float((kayip_r > TAM_STOP_ESIK).mean() * 100) if len(kayip_r) else np.nan}
    return o


def ham_yukle(strateji: str):
    """-> {(sembol, tf): DataFrame}. Dosya hatası / hata alanı dolu => RuntimeError (sessiz geçiş yok)."""
    sonuc = {}
    for p in sorted(HAM.glob(f"{strateji}--*--*.parquet")):
        _, tf, sembol = p.stem.split("--")
        meta = json.loads(p.with_suffix(".json").read_text())
        if meta.get("hata"):
            raise RuntimeError(f"{p.name}: ham hata alanı dolu: {meta['hata']}")
        if meta.get("veri_yok"):
            continue
        sonuc[(sembol, tf)] = pd.read_parquet(p)
    if not sonuc:
        raise RuntimeError(f"{strateji}: ham dosya yok")
    return sonuc


def main():
    CIKTI.mkdir(parents=True, exist_ok=True)
    satirlar, ozet, islemler = [], {}, []
    for s in STRATEJILER:
        parcalar = []
        for (sembol, tf), df in ham_yukle(s).items():
            if len(df):
                parcalar.append(islem_olc(df, sembol, tf))
        d = pd.concat(parcalar, ignore_index=True)
        d["strateji"] = s
        o = {"strateji": s, "tf": d["tf"].iloc[0], "n_sembol": int(d["sembol"].nunique()), **strateji_olcu(d)}
        satirlar.append(o); islemler.append(d)
        print(s, o["n_islem"], round(o["kazanma_orani"], 3), round(o["payoff"], 2), o["tip"], flush=True)
    sonuc = pd.DataFrame(satirlar)
    tum = pd.concat(islemler, ignore_index=True)
    assert tum["cikis_zamani"].max() < HOLDOUT_BAS and tum["giris_zamani"].max() < HOLDOUT_BAS, "tarih sınırı"
    sonuc.to_csv(CIKTI / "sonuc.csv", index=False)
    tum[["strateji", "sembol", "tf", "giris_zamani", "cikis_zamani", "yon", "r", "stop_mesafe", "giris_fiyati_turetilen",
         "mae_r", "mfe_r", "n_mum_pencere"]].to_parquet(CIKTI / "islem_mae_mfe.parquet", index=False)
    json.dump({"max_cikis": str(tum["cikis_zamani"].max()), "n_islem_toplam": int(len(tum)),
               "stratejiler": sonuc.set_index("strateji").to_dict("index")},
              open(CIKTI / "ozet.json", "w"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    sys.exit(main())
