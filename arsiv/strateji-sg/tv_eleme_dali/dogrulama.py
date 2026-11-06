"""B3: yazarın kendi sembol/zaman dilimi/dönemindeki iddiası ↔ bizim çeviri. python3 -m tv.dogrulama  → tv/sonuclar/dogrulama.csv
Karşılaştırılan: işlem sayısı, kazanma oranı, kâr faktörü (boyutlandırma farklı olduğundan net getiri karşılaştırılmaz).
Veri: kripto Binance (önbellek), hisse/endeks Yahoo (tam geçmiş, önbellek tv/veri/dogr_*.pkl)."""
import sys, importlib, numpy as np, pandas as pd, pathlib, time
from tv import motor, veri
K = pathlib.Path(__file__).parent
def yahoo_tam(sym, iv="1d"):
    f = veri.KOK/f"dogr_{sym}_{iv}.pkl"
    if f.exists(): return pd.read_pickle(f)
    import yfinance as yf
    for i in range(4):
        try:
            d = yf.Ticker(sym).history(auto_adjust=True, interval=iv, period="max")
            if len(d): break
        except Exception: pass
        time.sleep(3)
    else: return None
    d = d[["Open","High","Low","Close","Volume"]]; d.columns = ["o","h","l","c","v"]
    if d.index.tz is not None: d.index = d.index.tz_convert("UTC").tz_localize(None)
    d.index = d.index.normalize() if iv == "1d" else d.index
    d = d[~d.index.duplicated()]; d.to_pickle(f); return d
def veri_al(kod, tf):
    if kod.startswith("^") or kod in ("AAPL","QQQ","TQQQ","SPY","AMD","NVDA","ALTIN"): 
        if kod == "ALTIN": return veri.al("ALTIN", tf)
        return yahoo_tam(kod, "1d")
    if kod in ("ONE","BCH"):
        return veri.kripto(kod, tf, bas="2019-01-01" if kod == "ONE" else "2025-06-01")
    return veri.al(kod, tf)
# (modül, tanım, veri_kodu, tf, başlangıç, bitiş, iddia_n, iddia_kazanma, iddia_kf, not)
TABLO = [
 ("macd_sma200","SPX500 günlük 1970–bugün","^GSPC","1d","1970-01-01","2026-12-31",None,0.68,6.4,"yazar: işlemlerin %68'i kârlı, KF 6.4"),
 ("macd_sma200","DOWI günlük 1915–bugün","^DJI","1d","1915-01-01","2026-12-31",None,0.51,10.8,"yazar: %51 kârlı, KF 10.8"),
 ("alphatrend","BTCUSDT günlük varsayılan","BTC","1d","2019-01-01","2026-12-31",41,None,None,"yazar: 41 işlem (1000$, %0.1 komisyon)"),
 ("compress_brk","AAPL günlük 2005–2026","AAPL","1d","2005-01-01","2026-12-31",None,0.59,4.33,"yazar: +%899, KF 4.33, %59 kazanan, DD %14.4"),
 ("channel_rev","QQQ günlük 1999–2026","QQQ","1d","1999-03-01","2026-12-31",58,0.64,2.28,"yazar: +%104, 58 işlem"),
 ("vol_target","TQQQ günlük 2010–2026 (yaklaşık çeviri)","TQQQ","1d","2010-02-01","2026-12-31",155,0.677,3.33,"yazar: 155 yeniden dengeleme olayı; bizde yalnız rejim girişi"),
 ("spy_bear","SPY günlük 1994–2025","SPY","1d","1994-01-01","2025-12-31",None,0.7016,None,"yazar: kazanma %70.16"),
 ("ibs_rev","SPX günlük 2006–2026","^GSPC","1d","2006-01-01","2026-12-31",None,0.73,2.1,"yazar: S&P/Nasdaq/altın 4S/1G toplam 1232 işlem, %73, KF 2.1, DD %14.8"),
 ("mr_2bar","ONEUSDT günlük (yazar 1S)","ONE","1d","2019-06-01","2025-12-31",237,0.7468,4.02,"yazar saatlik; bizde günlük"),
 ("mr_2bar","ONEUSDT 1S","ONE","1h","2019-06-01","2025-12-31",237,0.7468,4.02,"yazar: 237 işlem, %74.68, KF 4.02"),
 ("t3_sqz","BTCUSD 30dk 2024-01–2025-07","BTC","30m","2024-01-01","2025-07-03",181,0.478,2.01,"yazar: 181 işlem, %47.8, KF 2.01"),
 ("kst_sky","BTCUSDT 1S 2023-01–2025-05","BTC","1h","2023-01-01","2025-05-01",120,0.5667,1.75,"yazar: 120 işlem, %56.67, KF 1.75"),
 ("triple_cci","BTCUSDT 2S 2022-04–2024-11","BTC","2h","2022-04-01","2024-11-25",108,0.4444,2.01,"yazar: 108 işlem, %44.44, KF 2.01"),
 ("double_cci","BTCUSDT 2S 2022-07–2024-08","BTC","2h","2022-07-01","2024-08-01",104,0.3654,2.31,"yazar: 104 işlem, %36.54, KF 2.31"),
 ("macd_stoch1d","BTCUSDT 45dk 2023-01–2024-08","BTC","45m","2023-01-01","2024-08-01",123,0.4472,1.62,"yazar: 123 işlem, %44.72, KF 1.62"),
 ("fractal_sky","BTCUSDT 4S 2023-01–2024-05","BTC","4h","2023-01-01","2024-05-01",83,0.2892,1.95,"yazar: 83 işlem, %28.92, KF 1.95"),
 ("hash_st","SOL 12S","SOL","12h","2020-09-01","2026-12-31",None,0.45,2.0,"yazar: ~%45 kazanma, KF 2.0+ (yaklaşık)"),
 ("turtle3c","ETHUSDT 4S tüm geçmiş","ETH","4h","2019-01-01","2026-12-31",281,0.4021,1.70,"yazar: 281 işlem, %40.21, KF 1.70"),
 ("ha_rsi_fade","BCHUSDT 15dk 2025-11–2026-06","BCH","15m","2025-11-19","2026-06-03",177,0.6102,1.17,"yazar: 177 işlem, %61.02, KF 1.17"),
 ("williams_zone","BTC 5dk 2025-03-24–04-28","BTC","5m","2025-03-24","2025-04-28",198,0.5505,1.29,"yazar: 198 işlem, %55.05, KF 1.29"),
 ("gap_fill","AMD saatlik (yazar 15dk)","AMD","1h","2024-01-01","2026-12-31",272,0.6507,None,"yazar: AMD 15dk %65.07, 272 işlem; bizde saatlik"),
 ("vix_macd","SPY günlük (yazar Nikkei)","SPY","1d","2000-01-01","2026-12-31",70,0.671,None,"yazar: Nikkei 225, 70 işlem %67.1"),
 ("atr_rider","SPY günlük 2024-2026 (yazar: 5 endeks vadelisi)","SPY","1d","2024-01-01","2026-07-31",102,None,3.46,"yazar: 5 vadeli toplam 102 işlem, medyan KF 3.46"),
]
def olc(T):
    if len(T) == 0: return 0, np.nan, np.nan
    w = T.kar[T.kar > 0].sum(); l = -T.kar[T.kar < 0].sum()
    return len(T), float((T.kar > 0).mean()), float(w/l) if l > 0 else np.inf
def kos(r):
    mod, tanim, kod, tf, bas, son, in_, iw, ipf, notu = r
    m = importlib.import_module(f"tv.stratejiler.{mod}")
    d = veri_al(kod, tf)
    if d is None or len(d) < 50: return dict(modul=mod, tanim=tanim, durum="veri yok", not_=notu)
    gr = "kripto" if (kod in veri.KRIPTO or kod in ("ONE","BCH")) else "abd"
    ev = d.copy()
    S = m.sinyal(ev, **m.PARAM)
    res = []
    for B in (S["bacaklar"] if "bacaklar" in S else [S]):
        res.append(motor.islem_tablosu(motor.calistir(ev, B, gr, kod, 1.0, getattr(m, "YON", 0), 1)))
    T = pd.concat(res, ignore_index=True) if res else pd.DataFrame()
    if len(T) == 0: return dict(modul=mod, tanim=tanim, durum="işlem yok", not_=notu)
    T = T[(T.giris >= pd.Timestamp(bas)) & (T.giris <= pd.Timestamp(son))]
    n, w, pf = olc(T)
    nb = T.groupby("gi").ngroups if len(T) else 0
    return dict(modul=mod, tanim=tanim, veri_aralik=f"{d.index[0].date()}→{d.index[-1].date()}", bizim_islem=nb, iddia_islem=in_, bizim_kazanma=round(w, 4), iddia_kazanma=iw,
                bizim_kf=round(pf, 3), iddia_kf=ipf, not_=notu, durum="tamam")
if __name__ == "__main__":
    out = []
    for r in TABLO:
        try: x = kos(r)
        except Exception as e: x = dict(modul=r[0], tanim=r[1], durum="hata: "+repr(e)[:80], not_=r[9])
        print(x, flush=True); out.append(x)
    (K/"sonuclar").mkdir(exist_ok=True)
    pd.DataFrame(out).to_csv(K/"sonuclar/dogrulama.csv", index=False)
