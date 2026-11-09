"""KGT günlük/saatlik sinyal üretici.

Canlı kullanım (Binance açık API'si, anahtar gerekmez):
    python3 -m backtest.kripto_sinyal --sermaye 10000
Çevrimdışı test (yerel backtest verisiyle, geçmiş bir anda):
    python3 -m backtest.kripto_sinyal --yerel --tarih "2025-11-05 14:00" --sermaye 10000

Çıktı:
  * İZLEME LİSTESİ: ilk 15 coin için bugünün dar CPR durumu, günlük trend, R1 (giriş tetiği), S1 (stop),
    1R kısmi kâr seviyesi, 4S trend durumu.
  * YENİ SİNYAL: son kapanan 1S mumunda tetiklenen girişler -> bir sonraki saatin açılışında al.
  * ÇIKIŞ UYARISI: 4S trendi aşağı dönmüş coinler -> bu coinlerde açık pozisyon varsa kapat.
Kurallar backtest ile aynı fonksiyonları kullanır (strateji.gunluk_kirilim, kripto_strateji trend tanımı).
"""
import argparse
import time
import numpy as np
import pandas as pd
from . import strateji as st, gostergeler as g, kripto_final as KF
from .kripto_evren import HARIC

API = "https://fapi.binance.com"


def _get(yol, **params):
    import requests
    for i in range(5):
        try:
            r = requests.get(API + yol, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(2 ** i)
    raise RuntimeError(f"Binance API yanıt vermedi: {yol}")


def canli_evren(n=10):
    info = _get("/fapi/v1/exchangeInfo")
    uygun = {s["symbol"] for s in info["symbols"] if s.get("contractType") == "PERPETUAL"
             and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING" and s["symbol"] not in HARIC}
    t24 = sorted((x for x in _get("/fapi/v1/ticker/24hr") if x["symbol"] in uygun),
                 key=lambda x: -float(x["quoteVolume"]))[:40]
    hacim = {}
    for x in t24:   # evren tanımı: son 30 günlük USDT hacmi, en az 90 gün geçmiş
        k = _get("/fapi/v1/klines", symbol=x["symbol"], interval="1d", limit=120)
        if len(k) >= 91:
            hacim[x["symbol"]] = sum(float(r[7]) for r in k[-31:-1])
    return [s for s, _ in sorted(hacim.items(), key=lambda kv: -kv[1])[:n]]


def canli_mumlar(sym, gun=120):
    bitis = int(time.time() * 1000)
    bas = bitis - gun * 86400 * 1000
    satir = []
    while bas < bitis:
        k = _get("/fapi/v1/klines", symbol=sym, interval="1h", startTime=bas, limit=1500)
        if not k:
            break
        satir += k
        bas = k[-1][0] + 3600 * 1000
        if len(k) < 1500:
            break
    d = pd.DataFrame(satir).iloc[:, :6].astype(float)
    d.columns = ["t", "open", "high", "low", "close", "volume"]
    d.index = pd.to_datetime(d.t, unit="ms")
    d = d[~d.index.duplicated()].drop(columns="t")
    simdi = pd.Timestamp.utcnow().tz_localize(None).floor("h")
    return d[d.index < simdi]          # yalnız kapanmış mumlar


def yerel_veri(tarih, n=KF.KGT["evren_n"]):
    evren = pd.read_pickle(KF.ks.KOK / "evren.pkl")
    ay = pd.Timestamp(tarih).to_period("M").to_timestamp()
    liste = evren.get(ay, [])[:n]
    out = {}
    for s in liste:
        d = pd.read_pickle(KF.ks.KOK / "1h" / f"{s}.pkl")
        out[s] = d[(d.index < pd.Timestamp(tarih)) & (d.index >= pd.Timestamp(tarih) - pd.Timedelta(days=120))]
    return out


def analiz(sym, df, sermaye, risk=KF.KGT["risk"], max_pay=KF.KGT["max_pay"], gun_bas=0.0):
    """sermaye: bu alt-portföyün sermayesi (topluluk kullanımında toplam sermaye / 6)."""
    st._IND.clear()
    p = dict(KF.GIRIS, gun_bas=float(gun_bas))
    sig, stop, _, _, _ = st.gunluk_kirilim(df, p)
    lv, kol, gun, hr = st.gunluk_seviyeler(df, p["tz"], p.get("gun_bas", 0.0))
    L = {k: lv[-1, i] for i, k in enumerate(kol)}
    dar = (L["TC"] - L["BC"]) / L["datr"]
    d = KF.ks._htf(df, "1D"); dc = d.close.to_numpy()
    es_d = g.ema(dc[:-1], p["htf_s"]) if len(dc) > 25 else None                                # kapanmış günler
    d_up = es_d is not None and g.ema(dc[:-1], p["htf_f"])[-1] > es_d[-1] and \
        (not p.get("htf_ust") or dc[-2] > es_d[-1])                                          # v3: kapanış > EMA20
    h4 = KF.ks._htf(df, "4h")
    son4 = h4.index + pd.Timedelta(hours=4) <= df.index[-1] + pd.Timedelta(hours=1)
    hc = h4.close[son4].to_numpy()
    ef, es = g.ema(hc, KF.TREND["h4_f"]), g.ema(hc, KF.TREND["h4_s"])
    h4_yon = 1 if (ef[-1] > es[-1] and hc[-1] > ef[-1]) else (-1 if (ef[-1] < es[-1] and hc[-1] < ef[-1]) else 0)
    a = g.atr(df.high.values, df.low.values, df.close.values, 14)[-1]
    giris = L["R1"]
    stop_mesafe = np.clip(giris - L["S1"], p["stop_min_atr"] * a, p["stop_max_atr"] * a)
    miktar_usdt = min(risk * sermaye / (stop_mesafe / giris), max_pay * sermaye)
    return dict(sembol=sym, son_kapanis=df.close.iloc[-1], dar_cpr=bool(dar <= p["dar"]), cpr_orani=round(dar, 3),
                gunluk_trend="YUKARI" if d_up else "aşağı/nötr", R1_giris=giris, S1_stop=giris - stop_mesafe,
                kismi_1R=giris + stop_mesafe, h4_trend={1: "yukarı", -1: "AŞAĞI", 0: "nötr"}[h4_yon],
                pozisyon_usdt=round(miktar_usdt, 2), yeni_sinyal=bool(sig[-1] > 0),
                sinyal_stop=stop[-1] if sig[-1] > 0 else np.nan,            # stop MESAFESİ (backtest ile aynı)
                sinyal_stop_seviye=(df.close.iloc[-1] - stop[-1]) if sig[-1] > 0 else np.nan,
                sinyal_kismi=(df.close.iloc[-1] + stop[-1]) if sig[-1] > 0 else np.nan,
                sinyal_pozisyon=round(min(risk * sermaye / (stop[-1] / df.close.iloc[-1]), max_pay * sermaye), 2)
                if sig[-1] > 0 else np.nan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sermaye", type=float, default=10000)
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--tarih", default=None)
    a = ap.parse_args()
    if a.yerel:
        veri = yerel_veri(a.tarih or "2026-09-30 12:00")
    else:
        veri = {s: canli_mumlar(s) for s in canli_evren(KF.KGT["evren_n"])}
    alt = a.sermaye / len(KF.GUN_BASLARI)
    zaman = max(d.index[-1] for d in veri.values())
    print(f"\nKGT v3 topluluk sinyal raporu — son kapanan 1S mumu: {zaman} UTC")
    print(f"Toplam sermaye {a.sermaye:,.0f} USDT = {len(KF.GUN_BASLARI)} alt-portföy x {alt:,.0f} USDT; "
          f"her alt-portföyde işlem başına %{100*KF.KGT['risk']:g} risk, en fazla {KF.KGT['max_poz']} pozisyon.\n")
    cik_set = set()
    with pd.option_context("display.width", 220, "display.float_format", "{:.6g}".format):
        for gb in KF.GUN_BASLARI:
            r = pd.DataFrame([analiz(s, d, alt, gun_bas=gb) for s, d in veri.items() if len(d) > 24 * 60])
            cik_set |= set(r[r.h4_trend == "AŞAĞI"].sembol)
            yeni = r[r.yeni_sinyal]
            print(f"--- Alt-portföy G{gb:02d} (pivotlar her gün {gb:02d}:00 UTC'de yenilenir) ---")
            if len(yeni):
                print(yeni[["sembol", "son_kapanis", "sinyal_stop_seviye", "sinyal_kismi", "sinyal_pozisyon"]].to_string(index=False))
            else:
                izle = r[(r.dar_cpr) & (r.gunluk_trend == "YUKARI")][["sembol", "R1_giris", "S1_stop"]]
                print("  yeni sinyal yok; izleme (dar CPR + günlük trend yukarı): " +
                      (", ".join(f"{x.sembol} R1={x.R1_giris:.6g}" for x in izle.itertuples()) if len(izle) else "-"))
        print("\nÇIKIŞ UYARISI (4S trend aşağı — bu coinlerdeki TÜM alt-portföy longlarını bir sonraki açılışta kapat):")
        print("  " + ", ".join(sorted(cik_set)) if cik_set else "  yok")
    print("\nYönetim: fiyat 1R seviyesine ulaşınca o pozisyonun %15'ini kapat ve stopu giriş fiyatına çek; kalanı 4S trend "
          "aşağı dönene kadar tut. Her alt-portföy kendi pozisyon sınırını (5) ayrı takip eder.")


if __name__ == "__main__":
    main()
