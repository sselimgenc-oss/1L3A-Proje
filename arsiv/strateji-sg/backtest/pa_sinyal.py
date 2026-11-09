"""SKA (Sıkışma Kırılım Arızası, 4S) sinyal üretici — her 4 saatlik mum kapanışından sonra çalıştırın
(00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC = TSİ 03, 07, 11, 15, 19, 23).

Canlı:      python3 -m backtest.pa_sinyal --sermaye 10000
Çevrimdışı: python3 -m backtest.pa_sinyal --yerel --tarih "2024-11-09 20:00" --sermaye 10000

Backtest ile aynı fonksiyonları kullanır (kripto_strateji.ozellikler, pa_arastirma.kurulum_listesi/diziler).
Çıktı:
  * BEKLEYEN EMİRLER: son kapanan 4S mumunda kurulum oluşan coinler -> tetik seviyesine ALIŞ STOP emri
    (yalnız bu 4S mum boyunca geçerli; dolmazsa iptal), stop seviyesi, 1R kısmi kâr seviyesi, pozisyon büyüklüğü.
  * ÇIKIŞ UYARISI: 4S eğilimi aşağı dönen coinler -> açık long varsa bir sonraki açılışta kapat.
  * EĞİLİM TABLOSU: ilk 20 coinin 4S eğilim durumu.
"""
import argparse
import time
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, pa_arastirma as P, pa_final as PF
from .kripto_sinyal import _get, canli_evren


def canli_4s(sym, gun=200):
    bitis = int(time.time() * 1000); bas = bitis - gun * 86400 * 1000; satir = []
    while bas < bitis:
        k = _get("/fapi/v1/klines", symbol=sym, interval="4h", startTime=bas, limit=1500)
        if not k:
            break
        satir += k; bas = k[-1][0] + 4 * 3600 * 1000
        if len(k) < 1500:
            break
    d = pd.DataFrame(satir).iloc[:, :6].astype(float)
    d.columns = ["t", "open", "high", "low", "close", "volume"]
    d.index = pd.to_datetime(d.t, unit="ms")
    d = d[~d.index.duplicated()].drop(columns="t")
    simdi = pd.Timestamp.utcnow().tz_localize(None)
    return d[d.index + pd.Timedelta(hours=4) <= simdi]       # yalnız kapanmış mumlar


def mini_V(veri):
    """Coin -> 4S DataFrame sözlüğünden backtest ile aynı T x N yapı."""
    sem = list(veri)
    z = pd.DatetimeIndex(sorted(set().union(*[d.index for d in veri.values()])))
    T, N = len(z), len(sem)
    V = {k: np.full((T, N), np.nan) for k in ("O", "H", "L", "C")}
    for j, s in enumerate(sem):
        d = veri[s].reindex(z)
        for k, c in (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close")):
            V[k][:, j] = d[c].to_numpy()
    V.update(FUND=np.zeros((T, N)), UYE=np.ones((T, N), bool),
             ONC=np.tile(np.arange(N, dtype=float), (T, 1)), zaman=z, semboller=sem)
    return V


def yerel(tarih, n=20, gun=200):
    evren = pd.read_pickle(ks.KOK / "evren.pkl")
    ay = pd.Timestamp(tarih).to_period("M").to_timestamp()
    out = {}
    for s in evren.get(ay, [])[:n]:
        d = pd.read_pickle(ks.KOK / "1h" / f"{s}.pkl")
        d = d[(d.index < pd.Timestamp(tarih)) & (d.index >= pd.Timestamp(tarih) - pd.Timedelta(days=gun))]
        d4 = d.resample("4h", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        out[s] = d4[d4.index + pd.Timedelta(hours=4) <= pd.Timestamp(tarih)]
    return out


def analiz(veri, sermaye, p=PF.SKA):
    V = mini_V(veri)
    F = ks.ozellikler(V, P.TREND)
    L = {("CBF", y): P.kurulum_listesi(V, F, "CBF", y, cbf_n=p["cbf_n"]) for y in (1, -1)}
    SIG, STOP, GSEV, CIK = P.diziler(V, F, L, dict(p, evren_n=len(V["semboller"])))
    son = -1
    satir = []
    for j, s in enumerate(V["semboller"]):
        c = V["C"][son, j]
        kur = SIG[son, j] > 0
        tet = GSEV[son, j]; mes = STOP[son, j]
        miktar = min(P.PORTFOY["risk"] * sermaye / (mes / tet), P.PORTFOY["max_pay"] * sermaye) if kur else np.nan
        satir.append(dict(sembol=s, son_kapanis=c, egilim_4s={1: "yukarı", -1: "AŞAĞI", 0: "nötr"}[int(F["h4_yon"][son, j] or 0)],
                          kurulum=bool(kur), alis_stop_emri=tet if kur else np.nan, stop=(tet - mes) if kur else np.nan,
                          kismi_1R=(tet + mes) if kur else np.nan, pozisyon_usdt=round(miktar, 2) if kur else np.nan,
                          cikis=bool(CIK[son, j] < 0), stop_mesafe=mes if kur else np.nan))
    return pd.DataFrame(satir), V["zaman"][son]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sermaye", type=float, default=10000)
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--tarih", default=None)
    a = ap.parse_args()
    veri = yerel(a.tarih or "2026-09-30 20:00") if a.yerel else {s: canli_4s(s) for s in canli_evren(PF.SKA["evren_n"])}
    r, son = analiz(veri, a.sermaye)
    print(f"\nSKA sinyal raporu — son kapanan 4S mumu açılışı: {son} UTC (sermaye {a.sermaye:,.0f} USDT, işlem başına %1 risk)\n")
    with pd.option_context("display.width", 220, "display.float_format", "{:.6g}".format):
        k = r[r.kurulum]
        print("BEKLEYEN EMİRLER (bu 4S mum boyunca geçerli ALIŞ STOP; dolmazsa iptal):")
        print(k[["sembol", "son_kapanis", "alis_stop_emri", "stop", "kismi_1R", "pozisyon_usdt"]].to_string(index=False) if len(k) else "  yok")
        c = r[r.cikis]
        print("\nÇIKIŞ UYARISI (4S eğilim aşağı — açık long varsa bir sonraki açılışta kapat):")
        print("  " + ", ".join(c.sembol) if len(c) else "  yok")
        print("\nEĞİLİM TABLOSU:")
        print(r[["sembol", "son_kapanis", "egilim_4s"]].to_string(index=False))
    print("\nYönetim: +1R'de pozisyonun 1/4'ünü kapat, stopu giriş fiyatına çek; kalan pozisyonu 4S eğilim aşağı dönene "
          "kadar tut. Aynı anda en fazla 5 pozisyon.")


if __name__ == "__main__":
    main()
