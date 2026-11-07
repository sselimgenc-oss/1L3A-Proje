"""D11-G — GitHub kaynaklı yeni aileler (kodlama_kuyrugu_github.csv, g harfi, 19 aile). KOD KOPYALANMADI: kaynaklar
(kripto bot repoları, MT5/Pine EA açıklamaları) VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__`. Hepsi nedensel.

Ortak uyarlamalar
  * Stopu olmayan ya da mutlak birimli orijinallere ATR (stop_atr_k x ATR) ya da yüzde stop (stop_yuzde) eklendi.
  * Martingale / ekleme / katlama / ızgara KODLANMADI; yalnız giriş + stoplu çıkış.
  * Tüm sinyaller bar kapanışında; dolum sonraki açılışta (motor).
  * Kaynakta stop/hedef yoksa varsayım: 2-3 ATR stop, gerektiğinde 2R hedef — ilgili sınıf docstring'inde "VARSAYIM".

Sınıflar: dis__adx-seviye-durumu, dis__aroon-uc-deger, dis__asiri-bolge-osilator-kesisimi, dis__cci-stochrsi-donus,
dis__gosterge-oy-toplami, dis__hafta-sonu-bosluk, dis__iki-gosterge-egimi, dis__linreg-rsi-dip, dis__momentum-ema-dizilim,
dis__obv-onculu-fiyat, dis__pump-mumu-devam, dis__rsi-boga-ayi-rejim, dis__sma400-tukenme, dis__tepeden-dusus-dip,
dis__uo-obv-dip, dis__yuzde-zigzag, dis__alligator-dizilim, dis__andean-osilator, dis__bb-stoch-gu-dip
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import ao_ac, choppiness, hma, kur, linreg, wma
from motor.strateji.dis._gosterge_d2 import stoch_rsi
from motor.strateji.dis._gosterge_d9 import r_hedefi
from motor.strateji.dis._gosterge_d10b import obv
from motor.strateji.dis._gosterge_d10c import aroon
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, gecis, yukari_kesis
from motor.strateji.temel import Strateji

from ._gosterge_d11g import andean, d_u_orani, momentum, trix, ultimate_osc, yuzde_zigzag

ORTAK = {
    "yonler": "long",        # "long" | "short" | "ls"
    "stop_yuzde": 0.0,       # > 0: sabit yüzde stop; 0: ATR stop (stop_atr_k x ATR)
    "stop_atr_k": 2.5,
    "atr_periyot": 14,
    "hedef_yuzde": 0.0,      # > 0: sabit yüzde hedef
    "hedef_r": 0.0,          # > 0 (ve hedef_yuzde == 0): hedef = kapanış +/- hedef_r x (kapanış - stop)
    "zaman_cikisi": 0,       # > 0: N mum sonra çık
}


class D11Taban(Strateji):
    """Alt sınıf `kosullar(m)` ({"long","short","cikis_long","cikis_short"} bool Series) ve gerekirse `stoplar(m)` yazar."""
    stil = "daytrade"

    def kosullar(self, m: pd.DataFrame) -> dict:
        raise NotImplementedError

    def stoplar(self, m: pd.DataFrame):
        p = self.parametreler
        kap = m["kapanis"]
        if p["stop_yuzde"] > 0:
            return kap * (1 - p["stop_yuzde"]), kap * (1 + p["stop_yuzde"])
        a = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_periyot"])) * p["stop_atr_k"]
        return kap - a, kap + a

    def cikis_var_mi(self) -> bool:
        return True   # alt sınıflar kendi cikis_long/cikis_short, hedef, zaman çıkışı ya da ATR stop üretir

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = self.kosullar(m)
        idx = m.index
        kap = m["kapanis"]
        bos = pd.Series(False, index=idx)

        def al(ad):
            s = k.get(ad)
            return bos if s is None else s.reindex(idx).fillna(False).astype(bool)

        long_ok = al("long") if p["yonler"] in ("long", "ls") else bos
        short_ok = al("short") if p["yonler"] in ("short", "ls") else bos
        stop_l, stop_s = self.stoplar(m)
        hl = hs = None
        if p["hedef_yuzde"] > 0:
            hl, hs = kap * (1 + p["hedef_yuzde"]), kap * (1 - p["hedef_yuzde"])
        out = kur(m, long_ok, short_ok, stop_l, stop_s, hl, hs, al("cikis_long"), al("cikis_short"),
                  zaman_cikisi=float(p["zaman_cikisi"]) if p["zaman_cikisi"] > 0 else None)
        if p["hedef_yuzde"] <= 0 and p["hedef_r"] > 0:
            ham = out.copy()
            out = r_hedefi(ham, kap, float(p["hedef_r"]))
        return out


def _dusuk_son(m, n):
    return m["dusuk"].rolling(int(n), min_periods=int(n)).min()


def _yuksek_son(m, n):
    return m["yuksek"].rolling(int(n), min_periods=int(n)).max()


# =============================================================================== 1
class AdxSeviyeDurumu(D11Taban):
    """dis__adx-seviye-durumu (daytrade, 1h) — kaynak: github:tulip-adx (kripto bot reposu, `tulip-adx` stratejisi).
    Kural: ADX(15) 30'un üstüne ÇIKINCA long, 20'nin altına İNİNCE short (kaynakta durum: ADX>30 long, <20 short; sürekli
    durum yerine kesişim olayı alındı, aksi halde her mumda yeniden giriş sinyali olurdu). ADX yön bilgisi içermez: bu
    sınıf bir kontrol örneğidir. Çıkış: long ADX alt seviyenin altına inince, short ADX üst seviyeyi aşınca; ATR stop.
    VARSAYIM: stop 2.5 ATR, kaynakta stop yok."""
    ad = "dis__adx-seviye-durumu"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "adx_n": 15, "ust": 30.0, "alt": 20.0}
    parametre_izgarasi = {"adx_n": [10, 15, 20], "ust": [25.0, 30.0, 35.0], "alt": [15.0, 20.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        a = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], int(p["adx_n"]))["adx"]
        return {"long": yukari_kesis(a, p["ust"]), "short": asagi_kesis(a, p["alt"]),
                "cikis_long": a < p["alt"], "cikis_short": a > p["ust"]}


# =============================================================================== 2
class AroonUcDeger(D11Taban):
    """dis__aroon-uc-deger (daytrade, 1h) — kaynak: github:aroon_public (kripto bot reposu).
    Kural (uç değerde KARŞI yön): Aroon(46) up > 99 ve down < 35 (yeni zirve, dip uzakta) -> SHORT; down > 99 ve up < 30
    -> LONG. Yalnız koşulun ilk oluştuğu mumda giriş (olay). Çıkış: zaman_cikisi mum + ATR stop.
    VARSAYIM: kaynakta çıkış tarifi yok; zaman çıkışı 24 mum, stop 2.5 ATR."""
    ad = "dis__aroon-uc-deger"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "zaman_cikisi": 24, "aroon_n": 46, "uc": 99.0,
                               "karsi_short": 35.0, "karsi_long": 30.0}
    parametre_izgarasi = {"aroon_n": [25, 46, 70], "uc": [90.0, 95.0, 99.0], "zaman_cikisi": [12, 24, 48]}

    def kosullar(self, m):
        p = self.parametreler
        a = aroon(m["yuksek"], m["dusuk"], int(p["aroon_n"]))
        short = (a["up"] > p["uc"]) & (a["down"] < p["karsi_short"])
        long = (a["down"] > p["uc"]) & (a["up"] < p["karsi_long"])
        return {"long": gecis(long), "short": gecis(short)}


# =============================================================================== 3
class AsiriBolgeOsilatorKesisimi(D11Taban):
    """dis__asiri-bolge-osilator-kesisimi (daytrade, 15m-1h) — kaynaklar: github:RSI-PHA (kripto bot), mt_pine: "MACD + RSI
    (aşırı bölge sonrası MACD kesişimi)", "ADX + Stokastik (güçlü trendde stokastik dönüşü)".
    mod="rsi_macd": son `pencere` mumda (bu mum dahil) RSI <= alt_esik olmuş VE MACD çizgisi sinyali yukarı keser -> long
      (ayna: RSI >= ust_esik olmuş ve MACD aşağı keser -> short).
    mod="stoch_adx": ADX > adx_esik, son `pencere` mumda %K <= stoch_alt olmuş ve %K, %D'yi yukarı keser -> long (ayna short).
    RSI-PHA'nın eksik EMA koşulları ve "gövde > %5 ise işlem yok" filtresi kodlanmadı (kaynakta tam değil).
    Çıkış: ATR stop + hedef_r x R hedefi (VARSAYIM: 2R)."""
    ad = "dis__asiri-bolge-osilator-kesisimi"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "hedef_r": 2.0, "mod": "rsi_macd", "pencere": 10, "rsi_n": 14,
                               "alt_esik": 30.0, "ust_esik": 70.0, "stoch_n": 14, "stoch_alt": 20.0, "stoch_ust": 80.0,
                               "adx_n": 14, "adx_esik": 20.0}
    parametre_izgarasi = {"mod": ["rsi_macd", "stoch_adx"], "pencere": [5, 10, 20], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, w = m["kapanis"], int(p["pencere"])
        if p["mod"] == "rsi_macd":
            r = g.rsi(k, int(p["rsi_n"]))
            md = g.macd(k)
            lo = r.rolling(w, min_periods=1).min() <= p["alt_esik"]
            hi = r.rolling(w, min_periods=1).max() >= p["ust_esik"]
            return {"long": lo & yukari_kesis(md["macd"], md["sinyal"]),
                    "short": hi & asagi_kesis(md["macd"], md["sinyal"])}
        if p["mod"] == "stoch_adx":
            s = g.stokastik(m["yuksek"], m["dusuk"], k, int(p["stoch_n"]), 3)
            ad_ = g.adx(m["yuksek"], m["dusuk"], k, int(p["adx_n"]))["adx"] > p["adx_esik"]
            lo = s["k"].rolling(w, min_periods=1).min() <= p["stoch_alt"]
            hi = s["k"].rolling(w, min_periods=1).max() >= p["stoch_ust"]
            return {"long": ad_ & lo & yukari_kesis(s["k"], s["d"]), "short": ad_ & hi & asagi_kesis(s["k"], s["d"])}
        raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")


# =============================================================================== 4
class CciStochrsiDonus(D11Taban):
    """dis__cci-stochrsi-donus (daytrade, 15m-30m) — kaynak: github:cci_srsi (kripto bot reposu; kaynak 20 dk, burada 15m/30m).
    Long: bir ÖNCEKİ mumda CCI(14) <= cci_alt (-90) ve StochRSI %K <= k_alt (18), şimdi ikisi de yukarı döndü (CCI ve %K
    önceki mumdan yüksek). Short: önceki mumda CCI >= cci_ust (140) ve %K >= k_ust (85), ikisi de aşağı döndü.
    Trend filtresi: EMA(30) eğimi = bir mumluk yüzde değişim (x100); |eğim| < egim_esik (0.03) ise iki yön açık, eğim >
    egim_esik ise yalnız long, < -egim_esik ise yalnız short. Çıkış: ATR stop + hedef_r x R (VARSAYIM: 1.5R)."""
    ad = "dis__cci-stochrsi-donus"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "hedef_r": 1.5, "cci_n": 14, "cci_alt": -90.0, "cci_ust": 140.0,
                               "k_alt": 18.0, "k_ust": 85.0, "ema_n": 30, "egim_esik": 0.03}
    parametre_izgarasi = {"cci_alt": [-110.0, -90.0, -70.0], "k_alt": [10.0, 18.0, 25.0], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        c = cci(m["yuksek"], m["dusuk"], k, int(p["cci_n"]))
        sk = stoch_rsi(k)["k"]
        ema = g.ema(k, int(p["ema_n"]))
        egim = 100.0 * ema.pct_change()
        yukari = (c > c.shift(1)) & (sk > sk.shift(1))
        asagi = (c < c.shift(1)) & (sk < sk.shift(1))
        long = (c.shift(1) <= p["cci_alt"]) & (sk.shift(1) <= p["k_alt"]) & yukari & (egim > -p["egim_esik"])
        short = (c.shift(1) >= p["cci_ust"]) & (sk.shift(1) >= p["k_ust"]) & asagi & (egim < p["egim_esik"])
        return {"long": long, "short": short}


# =============================================================================== 5
class GostergeOyToplami(D11Taban):
    """dis__gosterge-oy-toplami (daytrade, 15m) — kaynak: github:MultiSignalStrategy (kripto bot reposu; kaynak 5m-15m).
    Üç oy toplanır: RSI(14) >= rsi_ust +1 / <= rsi_alt -1 (arası 0); CCI(30) >= 10 +1 / <= -10 -1 (arası 0); SMA5 > SMA20 +1
    aksi -1. Toplam -3..+3 "hedef pozisyon". Tek hesapta: toplam >= esik olunca long GİRİŞ (olay), <= -esik olunca short;
    pozisyon büyüklüğü (3x gibi) UYGULANMAZ (risk limitleri kodda). Çıkış: long için toplam <= cikis_skor, short için
    toplam >= -cikis_skor; ATR stop. rsi_alt = 100 - rsi_ust. VARSAYIM: stop 2.5 ATR (kaynakta yok)."""
    ad = "dis__gosterge-oy-toplami"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "esik": 2, "cikis_skor": 0, "rsi_n": 14, "rsi_ust": 70.0,
                               "cci_n": 30, "cci_esik": 10.0, "sma_h": 5, "sma_y": 20}
    parametre_izgarasi = {"esik": [1, 2, 3], "rsi_ust": [65.0, 70.0, 75.0], "cikis_skor": [-1, 0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        c = cci(m["yuksek"], m["dusuk"], k, int(p["cci_n"]))
        s_rsi = (r >= p["rsi_ust"]).astype(int) - (r <= 100.0 - p["rsi_ust"]).astype(int)
        s_cci = (c >= p["cci_esik"]).astype(int) - (c <= -p["cci_esik"]).astype(int)
        s_sma = np.where(g.sma(k, int(p["sma_h"])) > g.sma(k, int(p["sma_y"])), 1, -1)
        gecerli = r.notna() & c.notna() & g.sma(k, int(p["sma_y"])).notna()
        skor = (s_rsi + s_cci + s_sma).where(gecerli)
        return {"long": gecis(skor >= p["esik"]), "short": gecis(skor <= -p["esik"]),
                "cikis_long": skor <= p["cikis_skor"], "cikis_short": skor >= -p["cikis_skor"]}


# =============================================================================== 6
class HaftaSonuBosluk(D11Taban):
    """dis__hafta-sonu-bosluk (daytrade, 1h) — kaynak: github:momentum:weekendGap (chrisleekr/binance-trading-bot,
    docs/concepts/strategies/momentum.md; Apache-2.0).
    Kural: Cuma `cuma_saat` (UTC, 20) saatinde AÇILAN son mumun (<= bu saat) kapanışı = referans. Pazar günü `pazar_saat`
    (22) UTC ve sonrasındaki İLK mumun kapanışı referansın `min_gap` (%1) fazla ALTINDAysa (ve referans 4 günden eski
    değilse) long. Çıkış: kapanış >= referans (boşluk doldu) ya da `zaman_cikisi` (72) mum, ATR stop (VARSAYIM 3 ATR).
    yonler="ls": ayna kural (referansın üstünde boşluk -> short, kapanış <= referans çıkış). Binance 7/24 kriptoda gerçek
    boşluk yok; TradFi perpetual'larda anlamlı. Referans yalnız geçmişten (ffill) alınır."""
    ad = "dis__hafta-sonu-bosluk"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 72, "cuma_saat": 20.0, "pazar_saat": 22.0,
                               "min_gap": 0.01}
    parametre_izgarasi = {"min_gap": [0.005, 0.01, 0.02], "zaman_cikisi": [24, 48, 72], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        idx = m.index
        k = m["kapanis"]
        dk = idx.hour * 60 + idx.minute
        hg = idx.dayofweek
        cuma = pd.Series((hg == 4) & (dk <= p["cuma_saat"] * 60), index=idx)
        ref = k.where(cuma).ffill()
        ref_zaman = pd.Series(idx, index=idx).where(cuma).ffill()
        taze = (pd.Series(idx, index=idx) - ref_zaman) < pd.Timedelta(days=4)
        pazar = pd.Series((hg == 6) & (dk >= p["pazar_saat"] * 60), index=idx)
        ilk_pazar = pazar & ~pazar.shift(1, fill_value=False)
        alt = ilk_pazar & taze & (k < ref * (1 - p["min_gap"]))
        ust = ilk_pazar & taze & (k > ref * (1 + p["min_gap"]))
        return {"long": alt, "short": ust, "cikis_long": k >= ref, "cikis_short": k <= ref}


# =============================================================================== 7
class IkiGostergeEgimi(D11Taban):
    """dis__iki-gosterge-egimi (daytrade, 1h) — kaynaklar: github:Bro-StochRSI-ADX-DI, ao-fab-base, hma-fab-base,
    trix-fab (kripto bot repoları). "Çift gösterge eğimi" sınıfı (tek gösterge/yüzde eşik ailesinden ayrı).
    Eğim = gösterge[t] - gösterge[t-egim_n] işareti. Girişler olay (durum ilk oluşunda):
      mod="adx_srsi": ADX yükseliyor VE StochRSI %K yükseliyor -> long; ADX yükseliyor VE %K düşüyor -> short.
      mod="ao_hma":   AO ve HMA(per) ikisi de yükseliyor -> long; ikisi de düşüyor -> short.
      mod="hma_trix": HMA(per) ve TRIX(per) eğimi aynı yönde -> long/short.
      mod="trix_trix": TRIX(per) ve TRIX(2 x per) birlikte yükseliyor -> long, birlikte düşüyor -> short.
    Çıkış: karşı durum oluşunca (long için karşı durum = short koşulu); ATR stop (VARSAYIM 3 ATR ~ kaynaktaki %3 stop) ve
    1R kârda stop girişe çekilir (kaynakta "%2 kârdan sonra stop yukarı"). ADOSC yerine HMA kullanıldı (hacim yok)."""
    ad = "dis__iki-gosterge-egimi"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "mod": "ao_hma", "per": 14, "egim_n": 1}
    parametre_izgarasi = {"mod": ["adx_srsi", "ao_hma", "hma_trix", "trix_trix"], "egim_n": [1, 3], "per": [7, 14, 21]}
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0)

    def kosullar(self, m):
        p = self.parametreler
        k, n, per = m["kapanis"], int(p["egim_n"]), int(p["per"])
        up = lambda s: s > s.shift(n)       # noqa: E731
        dn = lambda s: s < s.shift(n)       # noqa: E731
        if p["mod"] == "adx_srsi":
            a = g.adx(m["yuksek"], m["dusuk"], k, per)["adx"]
            s = stoch_rsi(k, per, per)["k"]
            long, short = up(a) & up(s), up(a) & dn(s)
        elif p["mod"] == "ao_hma":
            ao = ao_ac(m["yuksek"], m["dusuk"])["ao"]
            h = hma(k, per)
            long, short = up(ao) & up(h), dn(ao) & dn(h)
        elif p["mod"] == "hma_trix":
            h, t = hma(k, per), trix(k, per)
            long, short = up(h) & up(t), dn(h) & dn(t)
        elif p["mod"] == "trix_trix":
            t1, t2 = trix(k, per), trix(k, 2 * per)
            long, short = up(t1) & up(t2), dn(t1) & dn(t2)
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']!r}")
        return {"long": gecis(long), "short": gecis(short), "cikis_long": short, "cikis_short": long}


# =============================================================================== 8
class LinregRsiDip(D11Taban):
    """dis__linreg-rsi-dip (daytrade, 1h) — kaynak: github:lsma (lineer regresyon + RSI + ATR; kripto bot reposu).
    Long: kapanış VE açılış lineer regresyon(20) çizgisinin altında, RSI(14) < rsi_esik (30), ATR/kapanış >= atr_min.
    Stop: son `stop_n` (2) mumun en düşüğü. Hedef: risk x hedef_r (1). Ayna short (yonler="ls"): kapanış ve açılış çizginin
    üstünde, RSI > 100 - rsi_esik, stop son stop_n mumun en yükseği.
    VARSAYIM: kaynaktaki ATR eşiği (fiyatın %0.01'i) anlamsız küçük; atr_min = %0.2 alındı."""
    ad = "dis__linreg-rsi-dip"
    varsayilan_parametreler = {**ORTAK, "hedef_r": 1.0, "lr_n": 20, "rsi_n": 14, "rsi_esik": 30.0, "atr_min": 0.002,
                               "stop_n": 2}
    parametre_izgarasi = {"lr_n": [14, 20, 30], "rsi_esik": [25.0, 30.0, 35.0], "hedef_r": [1.0, 1.5, 2.0]}

    def stoplar(self, m):
        n = self.parametreler["stop_n"]
        return _dusuk_son(m, n), _yuksek_son(m, n)

    def kosullar(self, m):
        p = self.parametreler
        k, o = m["kapanis"], m["acilis"]
        lr = linreg(k, int(p["lr_n"]))
        r = g.rsi(k, int(p["rsi_n"]))
        a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_periyot"])) / k
        vol = a >= p["atr_min"]
        return {"long": (k < lr) & (o < lr) & (r < p["rsi_esik"]) & vol,
                "short": (k > lr) & (o > lr) & (r > 100.0 - p["rsi_esik"]) & vol}


# =============================================================================== 9
class MomentumEmaDizilim(D11Taban):
    """dis__momentum-ema-dizilim (daytrade, 1h) — kaynak: mt_pine: 2MOMEMA (iki Momentum + iki EMA; zaman dilimi belirtilmemiş,
    1h varsayıldı).
    Momentum(n) = 100 x kapanış / n mum önceki kapanış. Long: hızlı Momentum(10) önceki mumda <= 100 iken şimdi > 100 VE son
    `bar` (9) mumun (bu dahil) hepsinde yavaş Momentum(34) > 100 ve EMA10 > EMA34. Short ayna. Çıkış: long için EMA hızlı <
    EMA yavaş (short için tersi); ATR stop (VARSAYIM 2.5 ATR)."""
    ad = "dis__momentum-ema-dizilim"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "mom_h": 10, "mom_y": 34, "ema_h": 10, "ema_y": 34, "bar": 9}
    parametre_izgarasi = {"mom_h": [8, 10, 14], "bar": [5, 9, 13], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, b = m["kapanis"], int(p["bar"])
        mh, my = momentum(k, int(p["mom_h"])), momentum(k, int(p["mom_y"]))
        eh, ey = g.ema(k, int(p["ema_h"])), g.ema(k, int(p["ema_y"]))
        yuk = ((my > 100) & (eh > ey)).astype(float).rolling(b, min_periods=b).min() == 1.0
        asg = ((my < 100) & (eh < ey)).astype(float).rolling(b, min_periods=b).min() == 1.0
        return {"long": (mh.shift(1) <= 100) & (mh > 100) & yuk & my.notna(),
                "short": (mh.shift(1) >= 100) & (mh < 100) & asg & my.notna(),
                "cikis_long": eh < ey, "cikis_short": eh > ey}


# =============================================================================== 10
class ObvOnculuFiyat(D11Taban):
    """dis__obv-onculu-fiyat (daytrade, 1h) — kaynak: github:momentum:obvLead (chrisleekr/binance-trading-bot; Apache-2.0).
    Long: OBV son `pencere` (168) mumun (bu dahil) en yüksek değerinde iken kapanış aynı pencerenin en yüksek kapanışının
    ALTINDA (hacim fiyatı geride bırakıyor) VE Choppiness(14) < chop_esik (50). Çıkış: stop_atr_k (3) x ATR izleyen stop
    (CikisAyarlari.atr_iz_suren_k) + başlangıç ATR stopu. yonler="ls": ayna (OBV pencere dibi, fiyat dibin üstünde)."""
    ad = "dis__obv-onculu-fiyat"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "pencere": 168, "chop_n": 14, "chop_esik": 50.0}
    parametre_izgarasi = {"pencere": [72, 168, 336], "chop_esik": [40.0, 50.0, 60.0], "stop_atr_k": [2.0, 3.0, 4.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def kosullar(self, m):
        p = self.parametreler
        k, w = m["kapanis"], int(p["pencere"])
        o = obv(m)
        ch = choppiness(m["yuksek"], m["dusuk"], k, int(p["chop_n"]))
        tepe = (o >= o.rolling(w, min_periods=w).max()) & (k < k.rolling(w, min_periods=w).max())
        dip = (o <= o.rolling(w, min_periods=w).min()) & (k > k.rolling(w, min_periods=w).min())
        return {"long": tepe & (ch < p["chop_esik"]), "short": dip & (ch < p["chop_esik"])}


# =============================================================================== 11
class PumpMumuDevam(D11Taban):
    """dis__pump-mumu-devam (daytrade, 1h) — kaynak: github:Martingale V3 giriş kuralı (kripto bot reposu). SADECE tek giriş;
    kaynaktaki -%5'te ekleme/katlama KODLANMADI (martingale yasağı).
    Long: son `kisa_n` (1) mumun açılış->kapanış getirisi > kisa_esik (%2.6) VE o aralıktaki en yüksek / kapanış - 1 <
    fitil_max (%3); YA DA son `uzun_n` (4) mumluk (4 x 1h = 4sa mum) getiri > uzun_esik (%4.6) VE üst fitil < fitil_max.
    Çıkış: kaynakta "kâr >= %1 ve zirveden %1 geri çekilme" -> izleyen stop ile yaklaşıldı (1.5 ATR iz süren, mum bazında);
    kaynaktaki -%5 ekleme eşiği burada STOP olarak alındı (stop_yuzde 0.05). VARSAYIM: bu iki yaklaşım."""
    ad = "dis__pump-mumu-devam"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.05, "kisa_n": 1, "kisa_esik": 0.026, "uzun_n": 4,
                               "uzun_esik": 0.046, "fitil_max": 0.03}
    parametre_izgarasi = {"kisa_esik": [0.02, 0.026, 0.035], "fitil_max": [0.01, 0.03, 0.05],
                          "stop_yuzde": [0.03, 0.05, 0.07]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=1.5)

    def kosullar(self, m):
        p = self.parametreler
        k, o, y = m["kapanis"], m["acilis"], m["yuksek"]
        n1, n2 = int(p["kisa_n"]), int(p["uzun_n"])
        g1 = k / o.shift(n1 - 1) - 1.0
        f1 = y.rolling(n1, min_periods=n1).max() / k - 1.0
        g2 = k / o.shift(n2 - 1) - 1.0
        f2 = y.rolling(n2, min_periods=n2).max() / k - 1.0
        return {"long": ((g1 > p["kisa_esik"]) & (f1 < p["fitil_max"])) | ((g2 > p["uzun_esik"]) & (f2 < p["fitil_max"]))}


# =============================================================================== 12
class RsiBogaAyiRejim(D11Taban):
    """dis__rsi-boga-ayi-rejim (daytrade, 1h-4h) — kaynaklar: github:RSI_BULL_BEAR ailesi, NEO (üç rejimli RSI),
    MK_RSI_BULL_BEAR (kripto bot repoları). Rejime göre farklı RSI periyodu ve eşik:
      boğa  (SMA(sma_h)=50 > SMA(sma_y)=500 ve |ROC| >= roc_idle): RSI(10); long RSI < boga_long (60), short RSI > boga_short (75)
      ayı   (SMA50 < SMA500 ve |ROC| >= roc_idle):               RSI(15); long RSI < ayi_long (25),  short RSI > ayi_short (50)
      idle  (|ROC(roc_n=24)| < roc_idle=%1):                      RSI(12); long RSI < idle_long (39), short RSI > idle_short (65)
    Girişler olay (koşulun ilk oluşu). Çıkış: long için RSI > o rejimin short eşiği, short için RSI < long eşiği; ATR stop
    (VARSAYIM 3 ATR). KODLANMADI: ADX(3) eşik kaydırmaları, stop/pingpong/min-kâr varyantları, MK hızlı-yavaş RSI kesişimi,
    BB / Combination / STC varyantları. 500 mumluk SMA ısınması gerekir (kaynakta 1000)."""
    ad = "dis__rsi-boga-ayi-rejim"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "sma_h": 50, "sma_y": 500, "roc_n": 24,
                               "roc_idle": 0.01, "boga_rsi_n": 10, "boga_long": 60.0, "boga_short": 75.0,
                               "ayi_rsi_n": 15, "ayi_long": 25.0, "ayi_short": 50.0,
                               "idle_rsi_n": 12, "idle_long": 39.0, "idle_short": 65.0}
    parametre_izgarasi = {"boga_long": [50.0, 60.0, 65.0], "ayi_long": [20.0, 25.0, 30.0], "ayi_short": [45.0, 50.0, 60.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sh, sy = g.sma(k, int(p["sma_h"])), g.sma(k, int(p["sma_y"]))
        roc = k / k.shift(int(p["roc_n"])) - 1.0
        idle = roc.abs() < p["roc_idle"]
        hazir = sy.notna() & roc.notna()
        boga = hazir & ~idle & (sh > sy)
        ayi = hazir & ~idle & (sh <= sy)
        idle = hazir & idle
        rb, ra, ri = (g.rsi(k, int(p[f"{r}_rsi_n"])) for r in ("boga", "ayi", "idle"))
        rsi = pd.Series(np.select([boga, ayi, idle], [rb, ra, ri], np.nan), index=k.index)
        lo = pd.Series(np.select([boga, ayi, idle], [p["boga_long"], p["ayi_long"], p["idle_long"]], np.nan), index=k.index)
        hi = pd.Series(np.select([boga, ayi, idle], [p["boga_short"], p["ayi_short"], p["idle_short"]], np.nan), index=k.index)
        return {"long": gecis(rsi < lo), "short": gecis(rsi > hi), "cikis_long": rsi > hi, "cikis_short": rsi < lo}


# =============================================================================== 13
class Sma400Tukenme(D11Taban):
    """dis__sma400-tukenme (daytrade, 1h) — kaynak: github:momentum:exhaustion (chrisleekr/binance-trading-bot; Apache-2.0).
    Long: kapanış SMA(400)'ün %5'ten (sapma) fazla altında VE Choppiness(14) < 30 (tek yönlü düşüş) VE RSI(14) < 25.
    Çıkış: 1.5 x ATR izleyen stop (CikisAyarlari.atr_iz_suren_k) + başlangıç stopu 1.5 ATR. yonler="ls": ayna
    (kapanış SMA400'ün %5 üstünde, chop < 30, RSI > 75)."""
    ad = "dis__sma400-tukenme"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 1.5, "sma_n": 400, "sapma": 0.05, "chop_n": 14, "chop_esik": 30.0,
                               "rsi_n": 14, "rsi_esik": 25.0}
    parametre_izgarasi = {"sapma": [0.03, 0.05, 0.07], "chop_esik": [30.0, 40.0, 50.0], "rsi_esik": [25.0, 30.0, 35.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=1.5)

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s = g.sma(k, int(p["sma_n"]))
        ch = choppiness(m["yuksek"], m["dusuk"], k, int(p["chop_n"])) < p["chop_esik"]
        r = g.rsi(k, int(p["rsi_n"]))
        return {"long": (k < s * (1 - p["sapma"])) & ch & (r < p["rsi_esik"]),
                "short": (k > s * (1 + p["sapma"])) & ch & (r > 100.0 - p["rsi_esik"])}


# =============================================================================== 14
class TepedenDususDip(D11Taban):
    """dis__tepeden-dusus-dip (daytrade, 1h) — kaynaklar: github:Martingale V2 giriş kuralı (2 günlük zirveden düşüş),
    Dave (son zirveden %1 düşünce long, %3 stop, 30 mum azami süre), freqtrade NFI (derin düşüş + Williams %R) — kripto
    bot repoları. SADECE tek giriş: V2'nin katlama eklemeleri KODLANMADI.
    Long: kapanış son `pencere` (48 mum = 2 gün @1h) mumun en yükseğinin (yüksek) `dusus` (%4) altına inince (olay).
    İsteğe bağlı NFI filtresi: wr_esik < 0 ise Williams %R(14) < wr_esik (0: kapalı). Çıkış: hedef_yuzde (%2), stop_yuzde (%4)
    ve zaman_cikisi (30 mum). VARSAYIM: stop %4 (V2'de stop yok, Dave'de %3). saichovsky ("son işlem fiyatı") ve NFI'nin
    4sa/1sa çok zaman dilimli şartları kodlanmadı (işlem geçmişi / MTF verisi gerekir)."""
    ad = "dis__tepeden-dusus-dip"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.04, "hedef_yuzde": 0.02, "zaman_cikisi": 30, "pencere": 48,
                               "dusus": 0.04, "wr_n": 14, "wr_esik": 0.0}
    parametre_izgarasi = {"pencere": [24, 48, 96], "dusus": [0.03, 0.04, 0.06], "hedef_yuzde": [0.02, 0.03, 0.05]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        zirve = _yuksek_son(m, p["pencere"])
        kosul = k <= zirve * (1 - p["dusus"])
        if p["wr_esik"] < 0:
            n = int(p["wr_n"])
            hh, ll = _yuksek_son(m, n), _dusuk_son(m, n)
            wr = -100.0 * (hh - k) / (hh - ll).where(hh != ll)
            kosul = kosul & (wr < p["wr_esik"])
        return {"long": gecis(kosul)}


# =============================================================================== 15
class UoObvDip(D11Taban):
    """dis__uo-obv-dip (daytrade, 1h) — kaynak: github:ult-obv-fab (kripto bot reposu).
    Long: Ultimate Oscillator(7,14,28) < uo_alt (30) VE OBV artıyor (OBV > `obv_n` mum önceki OBV). Kaynaktaki "OBV toplamı"
    penceresi belirsiz: obv_n (3) mumluk artış alındı. Çıkış: UO > cikis_uo (60) olunca; ATR stop (VARSAYIM 2.5 ATR).
    yonler="ls": ayna (UO > 100 - uo_alt ve OBV düşüyor -> short, UO < 100 - cikis_uo çıkış)."""
    ad = "dis__uo-obv-dip"
    varsayilan_parametreler = {**ORTAK, "uo_alt": 30.0, "cikis_uo": 60.0, "obv_n": 3}
    parametre_izgarasi = {"uo_alt": [25.0, 30.0, 35.0], "obv_n": [1, 3, 5], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        uo = ultimate_osc(m["yuksek"], m["dusuk"], m["kapanis"])
        o = obv(m)
        n = int(p["obv_n"])
        return {"long": (uo < p["uo_alt"]) & (o > o.shift(n)),
                "short": (uo > 100.0 - p["uo_alt"]) & (o < o.shift(n)),
                "cikis_long": uo > p["cikis_uo"], "cikis_short": uo < 100.0 - p["cikis_uo"]}


# =============================================================================== 16
class YuzdeZigzagDonus(D11Taban):
    """dis__yuzde-zigzag (daytrade, 1h) — kaynaklar: github:custom-fab (yüzde zigzag), trust_distrust (kripto bot repoları).
    NEDENSEL ve ONAYLI yüzde ZigZag (kapanış bazlı): ilk durum long; long iken kapanış son zirveden `yuzde` (%1-%3) düşünce
    short'a DÖNÜŞ (o mumun kapanışında bilinir, geriye boyama yok), short iken kapanış son dipten `yuzde` yükselince long'a
    dönüş. Dönüş mumunda ilgili yönde giriş; karşı yöndeki dönüş açık pozisyonu kapatır; ATR stop (VARSAYIM 3 ATR).
    Gürültü: 15m+ barda %1 eşik maliyet baskındır; ızgarada %1-%3. trust_distrust'ın panik satış / açgözlülük kâr hedefi
    kodlanmadı (eşikleri belirsiz). Başlangıçtaki varsayılan long durumu işlem açmaz."""
    ad = "dis__yuzde-zigzag"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "yuzde": 0.02}
    parametre_izgarasi = {"yuzde": [0.01, 0.02, 0.03], "stop_atr_k": [2.0, 3.0, 4.0], "zaman_cikisi": [0, 48, 96]}

    def kosullar(self, m):
        z = yuzde_zigzag(m["kapanis"], float(self.parametreler["yuzde"]))
        return {"long": z["donus_long"], "short": z["donus_short"],
                "cikis_long": z["donus_short"], "cikis_short": z["donus_long"]}


# =============================================================================== 17
class AlligatorDizilim(D11Taban):
    """dis__alligator-dizilim (daytrade, 1h) — kaynak: mt_pine: EA31337 Alligator + Gator (EA31337/EA31337-strategies;
    GPL — kod kopyalanmadı). Williams Alligator: çene LWMA(cene_n), diş LWMA(dis_n), dudak LWMA(dudak_n) — tipik fiyat
    (H+L+C)/3 üzerinde; MT'deki ileri kaydırma (shift) YAPILMAZ (nedensel). Kaynak ayarı 30/6/4 (standart 13/8/5 değil).
    Long: dudak - diş > esik x ATR ve diş > çene (dizilim yukarı) ve üç çizgi de son `egim_n` (2) mumda yükseliyor;
    gator=1 ise ayrıca Gator ağzı açılıyor: üst histogram |çene-diş| ve alt histogram |diş-dudak| son 2 mumda artıyor.
    Short ayna. Giriş olay (koşulun ilk oluşu). Çıkış: dizilim bozulunca (long için dudak < diş); ATR stop (VARSAYIM 2.5).
    Pip eşiği (4 pip) ATR çarpanına normalize edildi (esik)."""
    ad = "dis__alligator-dizilim"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "cene_n": 30, "dis_n": 6, "dudak_n": 4, "esik": 0.1, "egim_n": 2,
                               "gator": 1}
    parametre_izgarasi = {"cene_n": [13, 21, 30], "esik": [0.0, 0.1, 0.25], "gator": [0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        tp = (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0
        cene, dis, dudak = (wma(tp, int(p[a])) for a in ("cene_n", "dis_n", "dudak_n"))
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        e = int(p["egim_n"])
        yuk = (cene > cene.shift(e)) & (dis > dis.shift(e)) & (dudak > dudak.shift(e))
        asg = (cene < cene.shift(e)) & (dis < dis.shift(e)) & (dudak < dudak.shift(e))
        long = (dudak - dis > p["esik"] * a) & (dis > cene) & yuk
        short = (dis - dudak > p["esik"] * a) & (cene > dis) & asg
        if p["gator"]:
            ust, alt = (cene - dis).abs(), (dis - dudak).abs()
            agiz = (ust > ust.shift(1)) & (ust.shift(1) > ust.shift(2)) & (alt > alt.shift(1)) & (alt.shift(1) > alt.shift(2))
            long, short = long & agiz, short & agiz
        return {"long": gecis(long), "short": gecis(short), "cikis_long": dudak < dis, "cikis_short": dudak > dis}


# =============================================================================== 18
class AndeanOsilator(D11Taban):
    """dis__andean-osilator (daytrade, 30m-4h; kaynak EA 4h) — kaynak: mt_pine: 2MAAOS (geraked/metatrader5, MIT) iki MA +
    Andean Osilatör. Yalnız saf giriş/SL/TP kuralı (kaynaktaki Grid KODLANMADI); AFAOSMD ve DHLAOS (ters sinyal EA'ya özgü,
    Average Force/MACD ve önceki gün yüksek/düşük çizgileri) kodlanmadı.
    Andean Osilatör(50, sinyal 9): boğa/ayı bileşenleri (gosterge dosyasında formül), sinyal = EMA(max(boğa, ayı), 9).
    Long: boğa sinyal çizgisini yukarı keser, boğa > ayı, SMA50 > SMA200 ve kapanış >= SMA50 - (SMA50 - SMA200)/2 (fiyat
    SMA50'nin, iki SMA farkının yarısından daha fazla altına inmemiş). Short ayna (ayı sinyali keser, SMA50 < SMA200,
    kapanış <= SMA50 + (SMA200 - SMA50)/2). Stop: son `stop_n` (10) mumun dibi/zirvesi. Hedef: hedef_r x R (kaynakta TP 1R;
    VARSAYIM 1.5R). "Son girişten >= 6 mum" kuralı motorda zaten tek pozisyon olduğundan ayrıca kodlanmadı."""
    ad = "dis__andean-osilator"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "hedef_r": 1.5, "uzunluk": 50, "sinyal_n": 9, "sma_h": 50,
                               "sma_y": 200, "stop_n": 10}
    parametre_izgarasi = {"uzunluk": [30, 50, 70], "stop_n": [5, 10, 20], "hedef_r": [1.0, 1.5, 2.0]}

    def stoplar(self, m):
        n = self.parametreler["stop_n"]
        return _dusuk_son(m, n), _yuksek_son(m, n)

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a = andean(m["acilis"], k, int(p["uzunluk"]), int(p["sinyal_n"]))
        sh, sy = g.sma(k, int(p["sma_h"])), g.sma(k, int(p["sma_y"]))
        yari = (sh - sy) / 2.0
        long = (yukari_kesis(a["boga"], a["sinyal"]) & (a["boga"] > a["ayi"]) & (sh > sy) & (k >= sh - yari))
        short = (yukari_kesis(a["ayi"], a["sinyal"]) & (a["ayi"] > a["boga"]) & (sh < sy) & (k <= sh - yari))
        return {"long": long, "short": short}


# =============================================================================== 19
class BbStochGuDip(D11Taban):
    """dis__bb-stoch-gu-dip (daytrade, 1h) — kaynaklar: github:2xTheMarket-min, bear-market (xFFFFF/Gekko-Strategies;
    base64 obfuske kaynaktan çözülmüş anlatım; kod kopyalanmadı). YALNIZ LONG.
    Long: kapanış < BB(19,2) alt bandı x bb_oran (1.03; bear-market 1.019) VE Stochastic(14,3) %D, [stoch_alt (5), stoch_ust
    (35)] aralığında ve yükseliyor (%D > önceki %D) VE önceki mum yükseldi (kapanış[t-1] > kapanış[t-2]) VE EMA(20)
    yükseliyor VE GU oranı: son 60 mumda (kapanış düşüşleri toplamı / yükselişleri toplamı) < gu60_max (2.0) ve son 12 mumda
    < gu12_max (3.5). Çıkış: StochD > cikis_d (96) ya da zaman_cikisi (30) mum ya da stop_yuzde (%1.5, kaynakta alışın %98.5'i).
    KODLANMADI: EMA-fiyat mutlak birim farkı (-25/-16, sembole özgü mutlak değer), BB orta bant yeniden kesişim durumu, kademeli
    hedef revizyonu ve 5 kez BB altı kapanış çıkışı."""
    ad = "dis__bb-stoch-gu-dip"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.015, "zaman_cikisi": 30, "bb_n": 19, "bb_k": 2.0, "bb_oran": 1.03,
                               "stoch_n": 14, "stoch_alt": 5.0, "stoch_ust": 35.0, "ema_n": 20, "gu60_max": 2.0,
                               "gu12_max": 3.5, "cikis_d": 96.0}
    parametre_izgarasi = {"bb_oran": [1.01, 1.03, 1.05], "stoch_ust": [30.0, 35.0, 45.0], "gu60_max": [1.0, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        d = g.stokastik(m["yuksek"], m["dusuk"], k, int(p["stoch_n"]), 3)["d"]
        ema = g.ema(k, int(p["ema_n"]))
        long = ((k < bb["alt"] * p["bb_oran"]) & (d >= p["stoch_alt"]) & (d <= p["stoch_ust"]) & (d > d.shift(1))
                & (k.shift(1) > k.shift(2)) & (ema > ema.shift(1))
                & (d_u_orani(k, 60) < p["gu60_max"]) & (d_u_orani(k, 12) < p["gu12_max"]))
        return {"long": long, "cikis_long": d > p["cikis_d"]}
