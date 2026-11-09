"""Tüm dış depo stratejilerini aynı ölçütlerle koşturur ve sonuç tablosu üretir.

Kullanım: python3 -m dis_kaynak.calistir [grup ...]   (gruplar: kural, awesome, freqtrade)
"""
import sys, os, glob, json, zipfile, pickle
import numpy as np, pandas as pd
from . import ortak as O, kurallar as K, awesome as A

OUT = os.path.dirname(__file__)
SER = os.environ.get("DIS_SERI", "/tmp/dis_seriler")

# (id, kaynak, ad, tip, tf, fn, kapsadığı kopyalar / not)
KURAL = [
    # backtrader
    ("BT01", "backtrader", "SMA 10/30 kesişim long", "pos", "1D", K.ma_cross(10, 30), "B1,B3,B5(St0),B7,B15,P2 aynı kural"),
    ("BT02", "backtrader", "SMA 10/20 kesişim long", "pos", "1D", K.ma_cross(10, 20), "B2,B4"),
    ("BT03", "backtrader", "SMA 15/50 kesişim long", "pos", "1D", K.ma_cross(15, 50), "B6"),
    ("BT04", "backtrader", "SMA 13/50 kesişim long", "pos", "1D", K.ma_cross(13, 50), "B10"),
    ("BT05", "backtrader", "SMA 10/30 long-short (dön)", "pos", "1D", K.ma_cross(10, 30, ls=True), "B8,B9"),
    ("BT06", "backtrader", "Kapanış SMA15 long-short", "pos", "1D", K.close_vs_ma(15, ls=True), "B16,B17,B18,B24(reverser)"),
    ("BT07", "backtrader", "Kapanış SMA15 long", "pos", "1D", K.close_vs_ma(15), "B21,B22,B23,B25,B40"),
    ("BT08", "backtrader", "Kapanış SMA30 long-short", "pos", "1D", K.close_vs_ma(30, ls=True), "B26 (B19,B20 long sürümü BT09)"),
    ("BT09", "backtrader", "Kapanış SMA30 long", "pos", "1D", K.close_vs_ma(30), "B19,B20"),
    ("BT10", "backtrader", "Kapanış SMA10 long", "pos", "1D", K.close_vs_ma(10), "B5(St1)"),
    ("BT11", "backtrader", "SMA5/15 kesişim + %2 stop/%2 hedef", "isl", "1D", K.bt_bracket, "B12 (limit giriş -> sonraki açılış), B13 OCO benzeri"),
    ("BT12", "backtrader", "EMA10/20 kesişim + %2 stop", "isl", "1D", K.bt_stop2, "B14"),
    ("BT13", "backtrader", "RSI 35/65 kesişim, 50'de çık (L/S)", "pos", "1D", K.bt_ksignal, "B27"),
    ("BT14", "backtrader", "MACD kesişim + düşen SMA30, 3xATR stop (Tharp)", "isl", "1D", K.bt_macd_tharp, "B28"),
    ("BT15", "backtrader", "BTFD: low/high-1 <= -%1, 2 gün tut", "isl", "1D", K.bt_btfd, "B29 (2x kaldıraç yok)"),
    ("BT16", "backtrader", "20 mum zirvesine dokununca al, 2 gün tut", "isl", "1D", K.bt_pinkfish, "B30"),
    ("BT17", "backtrader", "Hafta günü braket (Sa/Pe/Cu, ±%3, 7 gün)", "isl", "1D", K.bt_weekday, "B32"),
    ("BT18", "backtrader", "MACD+SMA çift sinyal (SMA10/30 & MACD 12/26/9)", "pos", "1D",
     lambda b: 0.5 * K.ma_cross(10, 30)(b) + 0.5 * K.durum(K.cross_up(*[pd.Series(x, index=b.index) for x in K.talib.MACD(b['close'].values, 12, 26, 9)[:2]]),
                                                             K.cross_dn(*[pd.Series(x, index=b.index) for x in K.talib.MACD(b['close'].values, 12, 26, 9)[:2]])), "B11"),
    # backtesting.py
    ("BP01", "backtesting.py", "SMA 10/20 dur-ve-dön", "pos", "1D", K.ma_cross(10, 20, ls=True), "P1 (README aynı)"),
    ("BP02", "backtesting.py", "SMA 10/25 + 2xATR(100) iz süren stop", "isl", "1D", K.btpy_trail, "P3, P4 temel sınıf"),
    ("BP03", "backtesting.py", "Sma4Cross 50/100 rejim, 20 giriş 10 çıkış", "pos", "1D", K.btpy_sma4cross, "P5"),
    ("BP04", "backtesting.py", "Çoklu zaman dilimi RSI(30) günlük+haftalık >70, %8 stop", "isl", "1D", K.btpy_mtf_rsi, "P6"),
    ("BP05", "backtesting.py", "Makine öğrenmesi kNN ileri yürüyen (1h, ±%0.4)", "isl", "1h", K.btpy_knn, "P8 (P7 tek eğitim sürümü aynı model)"),
    # finmarketpy
    ("FM01", "finmarketpy", "SMA200 üstü long altı short, %10 vol hedefi", "pos", "1D", K.fin_sma200_volt, "F1-F5"),
    ("FM02", "finmarketpy", "TechIndicator SMA20 L/S", "pos", "1D", K.close_vs_ma(20, ls=True), "F6 SMA"),
    ("FM03", "finmarketpy", "TechIndicator EMA20 L/S", "pos", "1D", K.close_vs_ma(20, ls=True, kind="ema"), "F6 EMA"),
    ("FM04", "finmarketpy", "TechIndicator ROC20 L/S", "pos", "1D", K.ti_roc(20), "F6 ROC"),
    ("FM05", "finmarketpy", "TechIndicator SMA2 (20/50) L/S", "pos", "1D", K.ma_cross(20, 50, ls=True), "F6 SMA2"),
    ("FM06", "finmarketpy", "TechIndicator GMMA L/S", "pos", "1D", K.ti_gmma, "F6 GMMA"),
    ("FM07", "finmarketpy", "TechIndicator Bollinger(20,2) kırılım L/S", "pos", "1D", K.ti_bb(), "F6 BB"),
    # QuantDinger
    ("QD01", "QuantDinger", "Tek SMA50 long", "pos", "1D", K.close_vs_ma(50), "Q1"),
    ("QD02", "QuantDinger", "SMA20/60 L/S (4h, BTC şablonu)", "pos", "4h", K.ma_cross(20, 60, ls=True), "Q2"),
    ("QD03", "QuantDinger", "Üç ortalamayı kesen boğa mumu", "pos", "1D", K.qd_three_lines(), "Q3"),
    ("QD04", "QuantDinger", "Üç ortalama boğa mumu + SMA60 trend", "pos", "1D", K.qd_three_lines(True), "Q4"),
    ("QD05", "QuantDinger", "Turtle 20/10 + 2xATR stop", "isl", "1D", K.qd_turtle, "Q5"),
    ("QD06", "QuantDinger", "Gösterge rezonansı MACD>0, 50<RSI<75, ADX>20", "pos", "1D", K.qd_resonance, "Q6"),
    ("QD07", "QuantDinger", "MACD+KDJ (4h), %2 stop, +%5 sonra %1 iz", "isl", "4h", K.qd_macd_kdj, "Q7"),
    ("QD08", "QuantDinger", "SuperTrend(10,3) long", "pos", "1D", K.qd_supertrend, "Q8, Q28, OctoBot O9 (günlük)"),
    ("QD09", "QuantDinger", "SMA20/50 long", "pos", "1D", K.ma_cross(20, 50), "Q13, Q20 (SMA20/60 benzeri)"),
    ("QD10", "QuantDinger", "EMA20/50 long", "pos", "1D", K.ma_cross(20, 50, kind="ema"), "Q14"),
    ("QD11", "QuantDinger", "Kapanış SMA20 long", "pos", "1D", K.close_vs_ma(20), "Q15, Q16"),
    ("QD12", "QuantDinger", "BTC long çekirdek + SMA50 altı hedge (1h)", "pos", "1h", K.qd_btc_hedge, "Q18"),
    ("QD13", "QuantDinger", "Martingale (1h)", "bot", "1h", K.bot_martingale, "Q23, Q24 katmanlı varyant"),
    ("QD14", "QuantDinger", "DCA botu (1h)", "bot", "1h", K.bot_dca, "Q22"),
    ("QD15", "QuantDinger", "Momentum top 4 (60g), haftalık", "agr", "1D", K.qd_mom_top, "Q10"),
    ("QD16", "QuantDinger", "Düşük volatilite top 4 (60g), haftalık", "agr", "1D", K.qd_lowvol, "Q11"),
    ("QD17", "QuantDinger", "Momentum_20 top 5, haftalık", "agr", "1D", K.qd_mom20, "Q19"),
    ("QD18", "QuantDinger", "Grid botu (1h, OctoBot ızgarasıyla aynı test)", "bot", "1h", K.bot_grid, "Q21; OctoBot O39,O58,O59"),
    # ai_quant_trade
    ("AQ01", "ai_quant_trade", "MA10/20 long", "pos", "1D", K.ma_cross(10, 20), "A1 (BT02 ile aynı)"),
    ("AQ02", "ai_quant_trade", "MA5/20 long", "pos", "1D", K.ma_cross(5, 20), "A2"),
    ("AQ03", "ai_quant_trade", "Momentum rotasyonu (skor, BTC filtresi, %15 iz)", "agr", "1D", K.aqt_mom_rotation, "A3"),
    ("AQ04", "ai_quant_trade", "MA5>10>30 dizilimi", "pos", "1D", K.aqt_ma_stack, "A4 (küçük ölçek filtresi yok)"),
    ("AQ05", "ai_quant_trade", "Trend yargısı + %5 stop", "isl", "1D", K.aqt_trend_judge, "A5, A7"),
    ("AQ06", "ai_quant_trade", "Kapanış > 1.01 x MA5", "pos", "1D", K.aqt_template, "A9"),
    ("AQ07", "ai_quant_trade", "Eşit ağırlık (aylık)", "agr", "1D", K.aqt_eq, "A14 ders 4"),
    ("AQ08", "ai_quant_trade", "Ters volatilite ağırlık (aylık)", "agr", "1D", K.aqt_invvol, "A14 ders 4; risk paritesi makalesine yakın"),
    ("AQ09", "ai_quant_trade", "Minervini trend şablonu + %10 stop", "isl", "1D", K.aqt_minervini, "A18 (RPS hariç)"),
    # OctoBot
    ("OB01", "OctoBot", "Bollinger momentum (ortalamaya dönüş, 4h)", "pos", "4h", K.okt_bb, "O3"),
    ("OB02", "OctoBot", "EMA21 ±%2 (4h)", "pos", "4h", K.okt_ema_mom, "O4"),
    ("OB03", "OctoBot", "EMA50 sapma (4h)", "pos", "4h", K.okt_ema_div, "O12"),
    ("OB04", "OctoBot", "StochRSI uçları (4h)", "pos", "4h", K.okt_stochrsi, "O13"),
    ("OB05", "OctoBot", "SMA50/200 altın kesişim", "pos", "1D", K.ma_cross(50, 200), "O10"),
    ("OB06", "OctoBot", "RSI(10)<28 al, %15 stop %25 hedef", "isl", "1D", K.okt_rsi_script, "O69"),
    ("OB07", "OctoBot", "EMA9/21 kesişim (4h; doküman 5m)", "pos", "4h", K.ma_cross(9, 21, kind="ema"), "O70"),
    ("OB08", "OctoBot", "RSI-MA uç seviyeler 39.57/67.45", "pos", "1D", K.okt_rsi_ma(True), "O71"),
    ("OB09", "OctoBot", "RSI-MA normal seviyeler 48.62/53.63", "pos", "1D", K.okt_rsi_ma(False), "O71"),
    ("OB10", "OctoBot", "Smart DCA (4h)", "bot", "4h", K.bot_smart_dca, "O56"),
    ("OB11", "OctoBot", "Simple DCA haftalık, satış yok", "bot", "1h", K.bot_dca_simple, "O55, O38 DCA modu"),
    ("OB12", "OctoBot", "Endeks: BTC/ETH/SOL eşit, ±%5 sapma", "agr", "1D", K.okt_index, "O44, O63"),
    # binance-trading-bot
    ("BB01", "binance-trading-bot", "Trailing Trade (1h, örnek ayar)", "bot", "1h", K.bot_trailing_trade, "trailing-trade"),
    ("BB02", "binance-trading-bot", "Momentum EMA9/21 + SMA200 + %5 iz (1h)", "isl", "1h", K.btb_momentum, "momentum"),
    ("BB03", "binance-trading-bot", "Rebalance sabit BTC.5/ETH.3/SOL.2 (4h)", "agr", "4h", K.btb_rebal_fixed, "rebalance fixed"),
    ("BB04", "binance-trading-bot", "Rebalance momentum top 3 (1h, 30 mum)", "agr", "1h", K.btb_rebal_mom, "rebalance momentum"),
]

AWESOME = [
    ("AS01", "awesome-systematic-trading", "12 aylık döngü (L/S)", "agr", "1D", A.ay12_dongu, "#1 (koddaki iki bacak long hatası düzeltildi)"),
    ("AS02", "awesome-systematic-trading", "52 hafta zirvesi (L/S, 3 dilim)", "agr", "1D", A.zirve52, "#2 (sektör yerine coin)"),
    ("AS03", "awesome-systematic-trading", "Momentum rotasyonu top 5 (365g)", "agr", "1D", A.mom_rotasyon, "#4, #45"),
    ("AS04", "awesome-systematic-trading", "Trend takibi (kapanış > 300g SMA)", "agr", "1D", A.trend_takip, "#5"),
    ("AS05", "awesome-systematic-trading", "Düşük beta (BAB) BTC'ye göre", "agr", "1D", A.bab, "#7, #8"),
    ("AS06", "awesome-systematic-trading", "Tutarlı momentum (6 ay tut)", "agr", "1D", A.tutarli_mom, "#11"),
    ("AS07", "awesome-systematic-trading", "Momentum 3/3 (365g)", "agr", "1D", A.mom_3_3, "#13"),
    ("AS08", "awesome-systematic-trading", "Momentum faktörü 5/5 (365g)", "agr", "1D", A.mom_5_5, "#29, #32"),
    ("AS09", "awesome-systematic-trading", "Momentum 1/1 (stil rotasyonu)", "agr", "1D", A.mom_1_1, "#30"),
    ("AS10", "awesome-systematic-trading", "6 ay momentum top 3, çeyreklik", "agr", "1D", A.fon_mom, "#33"),
    ("AS11", "awesome-systematic-trading", "Düşük volatilite top 6", "agr", "1D", A.dusuk_vol, "#26"),
    ("AS12", "awesome-systematic-trading", "Momentum + yüksek volatilite (6 dilim)", "agr", "1D", A.mom_vol, "#28"),
    ("AS13", "awesome-systematic-trading", "Eşli geçiş BTC/ETH (90g, çeyreklik)", "agr", "1D", A.esli_gecis, "#35"),
    ("AS14", "awesome-systematic-trading", "Çift işlemi mesafe (120g, 5 çift, 0.5sd)", "agr", "1D", A.cift_mesafe, "#36"),
    ("AS15", "awesome-systematic-trading", "Çift işlemi mesafe (365g, 20 çift, 2sd)", "agr", "1D",
     lambda C: A.cift_mesafe(C, form=365, period=365, npairs=20, k=2.0, stocks=True), "#37"),
    ("AS16", "awesome-systematic-trading", "Yeniden dengeleme primi", "agr", "1D", A.dengeleme_primi, "#40 (kripto, doğrudan)"),
    ("AS17", "awesome-systematic-trading", "Getiri asimetrisi (5/5)", "agr", "1D", A.asimetri, "#42"),
    ("AS18", "awesome-systematic-trading", "Kısa vadeli dönüş (haftalık)", "agr", "1D", A.kisa_donus, "#47"),
    ("AS19", "awesome-systematic-trading", "Çarpıklık (5/5)", "agr", "1D", A.carpiklik, "#49"),
    ("AS20", "awesome-systematic-trading", "Zaman serisi momentumu (vol hedefli)", "agr", "1D", A.tsmom, "#54"),
    ("AS21", "awesome-systematic-trading", "Küçük ölçek (dolar hacmi vekil)", "agrqv", "1D", A.kucuk_olcek, "#50*"),
    ("AS22", "awesome-systematic-trading", "ETH/BTC yayılımı 20g SMA", "agr", "1D", A.eth_btc_yayilim, "#55* (WTI-Brent uyarlaması)"),
    ("AS23", "awesome-systematic-trading", "Kalıntı momentum (BTC faktörü)", "agr", "1D", A.kalinti_mom, "#41*"),
    ("AS24", "awesome-systematic-trading", "Ay dönümü", "pos", "1D", A.ay_donumu, "#57"),
    ("AS25", "awesome-systematic-trading", "Maaş günü (15->16)", "pos", "1D", A.maas_gunu, "#38"),
    ("AS26", "awesome-systematic-trading", "Ocak barometresi", "pos", "1D", A.ocak_barometre, "#25"),
    ("AS27", "awesome-systematic-trading", "Vade haftası (son Cuma)", "pos", "1D", A.vade_haftasi, "#34*"),
    ("AS28", "awesome-systematic-trading", "Bitcoin gün içi mevsimsellik 22-00 UTC", "pos", "1h", A.gece_seans_btc, "#24"),
    ("AS29", "awesome-systematic-trading", "Tüm zamanların zirvesi + 1xATR(10) iz", "isl", "1D", A.ath_trend, "#56"),
    ("AS30", "awesome-systematic-trading", "MAX: 10 gün zirvesinde long (Padysak-Vojtko)", "pos", "1D", A.btc_max10, "kripto makale #3 (literatür tanımı)"),
    ("AS31", "awesome-systematic-trading", "MIN: 10 gün dibinde long (Padysak-Vojtko)", "pos", "1D", A.btc_min10, "kripto makale #3 (literatür tanımı)"),
    ("AS32", "awesome-systematic-trading", "Aşırı tepki ertesi gün (Caporale-Plastun)", "pos", "1D", A.asiri_tepki, "kripto makale #6 (literatür tanımı)"),
]


def _seri_kaydet(ad, g):
    os.makedirs(SER, exist_ok=True)
    g.to_pickle(os.path.join(SER, f"{ad}.pkl"))


def calistir_kural(liste):
    rows = []
    for (kid, kaynak, ad, tip, tf, fn, notu) in liste:
        res = {}
        try:
            evrenler = ("ana", "stres", "gel") if tf == "1D" else ("ana", "stres")
            for ev in evrenler:
                bars, fund = O.barlar(ev, tf)
                if tip == "pos":
                    g, tr = O.pozisyon_degerlendir({s: fn(b) for s, b in bars.items()}, bars, fund)
                elif tip == "isl":
                    g, tr = K.isl_degerlendir(fn, bars, fund)
                elif tip == "bot":
                    g, tr = K.bot_degerlendir(fn, bars)
                elif ev in ("gel", "stres") and tip.startswith("agr") and any(k in getattr(fn, "__name__", "") for k in ("esli", "eth_btc", "rebal_fixed", "index")):
                    continue  # belirli coinlere (BTC/ETH/SOL) bağlı kural bu evrende tanımsız
                else:
                    C = O.panel(bars)
                    W = fn(C, O.panel(bars, "quote_volume")) if tip == "agrqv" else fn(C)
                    W = W.reindex(columns=C.columns).fillna(0.0)
                    g, tr = O.agirlik_degerlendir(W, bars, fund)
                res[ev] = O.donemler(g, tr)
                if ev == "ana":
                    _seri_kaydet(kid, g)
            r = O.tablo_satiri(ad, res["ana"], res.get("stres"))
            if "gel" in res:
                gg = res["gel"]
                for per, k in (("IS", "is"), ("OOS", "oos")):
                    d = gg[per] or {}
                    r[f"pf_gel_{k}"] = d.get("pf", np.nan); r[f"sh_gel_{k}"] = d.get("sharpe", np.nan)
        except Exception as e:  # bir kuralın hatası diğerlerini durdurmasın
            r = {"strateji": ad, "hata": f"{type(e).__name__}: {e}"[:200]}
        r.update({"id": kid, "kaynak": kaynak, "tf": tf, "tip": tip, "kapsam": notu})
        rows.append(r)
        print(kid, ad, {k: (round(v, 2) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("islem", "wr", "pf_is", "pf_oos", "pf_2022", "sh_is", "sh_oos", "pf_stres", "dd", "hata")}, flush=True)
    return pd.DataFrame(rows)


# ------------------------------------------------------------ freqtrade sonuçları
FT_DIR = os.environ.get("FT_RES", "")


def ft_islemler(strat, uni):
    z = glob.glob(os.path.join(FT_DIR, f"{strat}_{uni}", "*.zip"))
    if not z:
        return None
    zf = zipfile.ZipFile(sorted(z)[-1])
    n = [x for x in zf.namelist() if x.endswith(".json") and not x.endswith("_config.json")][0]
    d = json.load(zf.open(n))
    t = pd.DataFrame(list(d["strategy"].values())[0]["trades"])
    if t.empty:
        return t
    t["close_date"] = pd.to_datetime(t["close_date"], utc=True)
    return t


def ft_degerlendir(strat):
    res = {}
    for uni, ev in (("main", "ana"), ("stress", "stres")):
        t = ft_islemler(strat, uni)
        if t is None:
            return None
        if t.empty:
            res[ev] = {k: None for k in ("TUM", "IS", "OOS", "2022")}; continue
        g = (t.set_index("close_date")["profit_abs"] / 10000).resample("1D").sum()
        full = pd.date_range("2020-01-01", "2026-10-08", freq="1D", tz="UTC")
        g = g.reindex(full).fillna(0.0)
        tr = t.set_index("close_date")["profit_ratio"].sort_index()
        res[ev] = O.donemler(g, tr)
        if ev == "ana":
            _seri_kaydet("FT_" + strat, g)
    return O.tablo_satiri(strat, res["ana"], res["stres"])


if __name__ == "__main__":
    gr = sys.argv[1:] or ["kural", "awesome"]
    if "kural" in gr:
        calistir_kural(KURAL).to_csv(os.path.join(OUT, "sonuc_kural.csv"), index=False)
    if "awesome" in gr:
        calistir_kural(AWESOME).to_csv(os.path.join(OUT, "sonuc_awesome.csv"), index=False)
    if "freqtrade" in gr:
        names = sorted({os.path.basename(p).rsplit("_", 1)[0] for p in glob.glob(os.path.join(FT_DIR, "*_main"))})
        rows = []
        for s in names:
            r = ft_degerlendir(s)
            if r:
                r.update({"id": "FT_" + s, "kaynak": "freqtrade-strategies"}); rows.append(r)
                print(s, {k: (round(v, 2) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("islem", "wr", "pf_is", "pf_oos", "pf_2022", "sh_is", "sh_oos", "pf_stres", "dd")}, flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(OUT, "sonuc_freqtrade.csv"), index=False)
