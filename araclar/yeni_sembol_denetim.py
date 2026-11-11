"""Yeni sembol sınavı — koşu SONRASI bağımsız denetim (sonuç değiştirmez; yalnız kontrol).

(a) Rastgele 3 yeni sembol (tohum 20261111) x 4 strateji: ΣR'yi AYRI yoldan (parquet'i doğrudan okuyup elle yeniden örnekleme,
    elle yazılmış maliyet sayıları, tf_mumlari/maliyet_ayarlari kullanılmadan) yeniden hesapla, kayıtlı işlemlerle karşılaştır.
(b) x2 maliyet: ayar değerleri x1'in tam 2 katı mı; aynı işlemlerde R(x2) <= R(x1) mı; ortalama fark.
(c) Lookahead: veriyi 2025-06-01'de kes, yeniden koş; kesim öncesi KAPANAN işlemler tam run ile birebir aynı olmalı.
Çıktı: sonuclar/evren/yeni_sembol/denetim.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import yeni_sembol_sinavi as y          # noqa: E402
from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest   # noqa: E402
from motor.strateji import funding, kayit            # noqa: E402

CIKTI = y.CIKTI


def elle_mumlar(sembol, tf, bit_sinir=y.OLCUM_BIT_SINIR):
    ham = pd.read_parquet(KOK / "veri" / "mumlar" / sembol / "5m.parquet")
    ham = ham[(ham.index >= y.OKUMA_BAS) & (ham.index < bit_sinir)]
    son = ham.index[ham["quote_hacim"] > 0].max()
    ham = ham[ham.index <= son]
    f = pd.read_parquet(KOK / "veri" / "mumlar" / sembol / "funding.parquet")
    f = f[(f.index >= y.OKUMA_BAS) & (f.index < bit_sinir) & (f.index <= son)]
    kural = {"15m": "15min", "1d": "1D"}[tf]
    adet = {"15m": 3, "1d": 288}[tf]
    g = ham.resample(kural, label="left", closed="left")
    o = pd.DataFrame({"acilis": g["acilis"].first(), "yuksek": g["yuksek"].max(), "dusuk": g["dusuk"].min(),
                      "kapanis": g["kapanis"].last(), "hacim": g["hacim"].sum(), "quote_hacim": g["quote_hacim"].sum(),
                      "islem_sayisi": g["islem_sayisi"].sum(), "_n": g["kapanis"].count()})
    o = o[o["_n"] > 0]
    # tam mum: 5m sayısı eksiksiz olmalı; verinin SON (kısmi) mumu delist/kesim nedeniyle serbest
    tam = (o["_n"] == adet) | (o.index == o.index[-1])
    return o[tam].drop(columns="_n"), f


def elle_kos(sembol, tf, ad, carpan, mumlar, fund, kural):
    k = carpan
    ay = MotorAyarlari(limit_modu="olc", kurallar=kural, komisyon_taker_yuzde=0.05 * k, komisyon_maker_yuzde=0.02 * k,
                       kayma_bps=5.0 * k, stop_kayma_bps=12.0 * k)          # en pahalı kripto satırı: 0.05% / 5 bps / 12 bps
    st = kayit.al(ad)()
    res = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay, fund, islem_baslangic=y.OLCUM_BAS)
    return res.islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True)


def main():
    sem = pd.read_csv(CIKTI / "semboller.csv")
    rng = np.random.default_rng(20261111)
    sec = sorted(rng.choice(sem["sembol"].to_numpy(), 3, replace=False).tolist())
    cikti = {"secilen_semboller": sec, "a_sumr": [], "b_x2": [], "c_lookahead": []}
    sonuc_ok = True
    for s in sec:
        r_ = sem.set_index("sembol").loc[s]
        kural = SembolKurallari(tick_size=float(r_["tick"]), step_size=float(r_["step"]), min_qty=float(r_["step"]), min_notional=5.0)
        for ad, tf in y.STRATEJILER.items():
            mum, fund = elle_mumlar(s, tf)
            kay = {c: pd.read_parquet(CIKTI / "islemler" / f"x{c:g}" / f"{ad}--{s}.parquet") for c in (1.0, 2.0)}
            elle = {c: elle_kos(s, tf, ad, c, mum, fund, kural) for c in (1.0, 2.0)}
            for c in (1.0, 2.0):
                a, b = float(kay[c]["r"].sum()), float(elle[c]["r"].sum())
                ok = abs(a - b) < 1e-9 and len(kay[c]) == len(elle[c])
                sonuc_ok &= ok
                cikti["a_sumr"].append({"sembol": s, "strateji": ad, "carpan": c, "n_kayit": len(kay[c]), "n_elle": len(elle[c]),
                                        "sum_r_kayit": a, "sum_r_elle": b, "esit": bool(ok)})
            # (b) x2 / x1
            k1, k2 = kay[1.0], kay[2.0]
            ayni = len(k1) == len(k2) and (len(k1) == 0 or (k1["giris_zamani"].values == k2["giris_zamani"].values).all())
            kotu = int((k2["r"].values > k1["r"].values + 1e-9).sum()) if ayni else -1
            cikti["b_x2"].append({"sembol": s, "strateji": ad, "ayni_islemler": bool(ayni), "x2_daha_iyi_islem_sayisi": kotu,
                                  "ort_fark_r": float((k1["r"].values - k2["r"].values).mean()) if ayni and len(k1) else None})
            # (c) lookahead: 2025-06-01'de kes
            T = pd.Timestamp("2025-06-01", tz="UTC")
            mk, fk = elle_mumlar(s, tf, bit_sinir=T)
            kes = elle_kos(s, tf, ad, 2.0, mk, fk, kural)
            tam = elle[2.0]
            kes_kapanan = kes[kes["cikis_zamani"] < T - pd.Timedelta(days=2)]
            tam_ayni = tam[tam["cikis_zamani"] < T - pd.Timedelta(days=2)]
            tam_ayni = tam_ayni[tam_ayni["giris_zamani"].isin(kes_kapanan["giris_zamani"]) | True]
            eslesen = (len(kes_kapanan) == len(tam_ayni)
                       and np.allclose(kes_kapanan["r"].values, tam_ayni["r"].values, atol=1e-9)
                       and (kes_kapanan["giris_zamani"].values == tam_ayni["giris_zamani"].values).all()
                       and (kes_kapanan["cikis_zamani"].values == tam_ayni["cikis_zamani"].values).all())
            sonuc_ok &= bool(eslesen)
            cikti["c_lookahead"].append({"sembol": s, "strateji": ad, "kesim_oncesi_kapanan": len(kes_kapanan), "birebir_ayni": bool(eslesen)})
    cikti["hepsi_tamam"] = bool(sonuc_ok)
    (CIKTI / "denetim.json").write_text(json.dumps(cikti, indent=1, ensure_ascii=False))
    print(json.dumps(cikti, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
