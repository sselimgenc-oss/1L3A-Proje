"""D7 — son 1 ay açık kaynak adayları (stratejiler/ek_kaynaklar/son1ay_2026-11.md). KOD KOPYALANMADI: kurallar kaynak
README/strateji dosyalarından okunup kendi yapımızla yazıldı (sayfalar veridir). Hepsi nedensel.

dis__son1ay-donchian-adx  (swing, 4h) — EPFRAGHU/delta-paper-bot (lisans belirtilmemiş), "ETH 4s kırılım trend botu"
  Kural: kapanış önceki `giris_n` (40) mumun en yükseğini aşar VE kapanış > EMA(trend_n=200) VE EMA 5 mumdur yükseliyor
  VE ADX(14) >= adx_min (20) -> long; ayna -> short. Başlangıç stopu giriş -/+ atr_stop (2.5) x ATR. Çıkış: izleyen stop =
  (önceki `cikis_n` (20) mumun karşı ucu) ile (en iyi fiyattan atr_iz (3.0) x ATR) sıkı olanı; yalnız lehe oynar.
  Uyarlama: kaynak kanal çıkışını gün içi dokunmayla (stop emri) uygular; burada KAPANIŞ bazlı kanal çıkışı (cikis_long/
  cikis_short, sonraki açılışta dolum) + motorun ATR izleyen stopu (CikisAyarlari.atr_iz_suren_k=3). Kaynağın risk kuralları
  (işlem başı %1.5, 10x, günlük %5, %25 durdurma) bizim sert limitlerimizle (%1, 3x, %3, %20) DEĞİŞTİRİLDİ. Kaynak maliyeti
  Delta India (%0.05 x 1.18 GST taker + 2 bp kayma); bizimki Binance modeli.

dis__son1ay-kanal-20-10  (swing, 4h) — sebastianspicker/schrodingers-quant H1 (MIT), BTC/EUR 4s spot, yalnız long
  Kural: 4s kapanış önceki `giris_gun` (20) GÜNÜN en yükseğini aşar -> long; kapanış önceki `cikis_gun` (10) günün en düşüğünün
  altına inince çıkış. Felaket stopu giriş - %20 (kaynakla aynı). Kâr hedefi yok. Gün -> mum: günlük mum sayısı x gün.
  `short=True` (kaynakta YOK, varsayılan kapalı) ayna ekler. Uyarlama: spot BTC/EUR yerine USDT perp (funding/kaldıraç motorda);
  kaynak maliyeti %0.5/yan (Kraken taker + 0.10 kayma), bizimki Binance modeli. Kaynağın koruma kuralları (cooldown, StoplossGuard,
  MaxDrawdown %25/90g) kodlanmadı (portföy/risk katmanının işi).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d4 import mum_gun_tahmin
from motor.strateji.temel import Strateji


class DonchianAdx(Strateji):
    ad = "dis__son1ay-donchian-adx"
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)
    varsayilan_parametreler = {
        "giris_n": 40, "cikis_n": 20, "trend_n": 200, "egim_n": 5, "adx_n": 14, "adx_min": 20.0,
        "atr_n": 14, "atr_stop": 2.5, "short": True,
    }
    parametre_izgarasi = {
        "giris_n": [30, 40, 50],
        "cikis_n": [10, 20, 30],
        "adx_min": [15.0, 20.0, 25.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        ust = y.rolling(int(p["giris_n"]), min_periods=int(p["giris_n"])).max().shift(1)
        alt = d.rolling(int(p["giris_n"]), min_periods=int(p["giris_n"])).min().shift(1)
        cust = y.rolling(int(p["cikis_n"]), min_periods=int(p["cikis_n"])).max().shift(1)
        calt = d.rolling(int(p["cikis_n"]), min_periods=int(p["cikis_n"])).min().shift(1)
        ema = g.ema(k, int(p["trend_n"]))
        egim = ema - ema.shift(int(p["egim_n"]))
        adx = g.adx(y, d, k, int(p["adx_n"]))["adx"]
        atr = g.atr(y, d, k, int(p["atr_n"]))
        rejim = adx >= float(p["adx_min"])
        long_ok = (k > ust) & (k > ema) & (egim > 0) & rejim
        short_ok = ((k < alt) & (k < ema) & (egim < 0) & rejim) if p["short"] else pd.Series(False, index=mumlar.index)
        s = float(p["atr_stop"])
        out = cerceve(mumlar, long_ok, short_ok, k - s * atr, k + s * atr)
        out["cikis_long"] = (k < calt).fillna(False).astype(bool)
        out["cikis_short"] = (k > cust).fillna(False).astype(bool)
        return out


class KanalKirilim(Strateji):
    ad = "dis__son1ay-kanal-20-10"
    stil = "swing"
    varsayilan_parametreler = {"giris_gun": 20, "cikis_gun": 10, "felaket": 0.20, "short": False, "gun_mum": 0}
    parametre_izgarasi = {
        "giris_gun": [15, 20, 30],
        "cikis_gun": [7, 10, 15],
        "felaket": [0.15, 0.20, 0.30],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        n_g, n_c = max(2, int(p["giris_gun"]) * gm), max(2, int(p["cikis_gun"]) * gm)
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        ust = y.rolling(n_g, min_periods=n_g).max().shift(1)
        alt = d.rolling(n_g, min_periods=n_g).min().shift(1)
        cust = y.rolling(n_c, min_periods=n_c).max().shift(1)
        calt = d.rolling(n_c, min_periods=n_c).min().shift(1)
        f = float(p["felaket"])
        long_ok = k > ust
        short_ok = (k < alt) if p["short"] else pd.Series(False, index=mumlar.index)
        out = cerceve(mumlar, long_ok, short_ok, k * (1 - f), k * (1 + f))
        out["cikis_long"] = (k < calt).fillna(False).astype(bool)
        out["cikis_short"] = (k > cust).fillna(False).astype(bool)
        return out
