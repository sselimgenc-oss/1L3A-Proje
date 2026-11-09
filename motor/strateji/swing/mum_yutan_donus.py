"""swing__mum-yutan-donus — yutan mum / dış bar tersine dönüş.

Kural (kartların ortak çekirdeği):
  Long: önceki trend aşağı (kapanış[t-1] < kapanış[t-1-trend_mum] ve düşüş >= trend_min_atr*ATR),
  önceki mum düşüş (kırmızı), mevcut mum yükseliş (yeşil) ve gövdesi önceki gövdeyi tamamen yutar
  (açılış <= önceki kapanış, kapanış >= önceki açılış, gövde daha büyük). Hacim onayı: hacim >
  hacim_k * ortalama(hacim_ort_mum) (hacim_k=0: kapalı). Giriş: yutan mumun KAPANIŞINDA.
  Short: ayna (yükseliş trendi sonunda ayı yutan).
  Stop: yutan + yutulan mumun karşı ucu (stop_modu="uc": iki mumun dip/tepesi, tampon_atr ile),
  "yarim": iki mum aralığının %50 seviyesi (Day kartı). Risk > maks_risk_atr*ATR ise işlem yok.
  Hedef: hedef_r * risk (kartlar net hedef vermiyor; 1.5-3R backtest aralığı).

Kaynak kartlar: yutma-formasyonu__hogan, yutan-mum-hacim__graham, yutan-mum-trend-sonu__day,
  iki-bar-tersine-donus__day, yutan-mum-doji-donus__jordan, bar-inversiyon-tersine-donus__derr, vb.
Kanıt: ailede pozitif/negatif sayısal kanıt YOK (Bulkowski yüzdeleri Graham'dan dolaylı aktarım).
Varsayımlar: "trend" tanımı kartlarda yok; N-mum kapanış karşılaştırması + ATR büyüklük eşiği
  tarafımızdan seçildi. Gövde yutması (fitil değil) esas alındı (Hogan); Derr'in dış-bar (high/low
  yutma) varyantı kodlanmadı. Destek/direnç yakınlığı filtresi yok.

d11j EK MOD (varsayılan "donus" = eski davranış; ızgaraya girmez; kaynak aile marubozu-yutan-mum-devam, NFI yutan mum devamı/marubozu):
  mod="devam" -> trend DEVAMI: desen "yutan" (boğa yutan, eski tanım), "marubozu" (yeşil mum, gövde/aralık >= maru_oran=0.9 ve gövde >=
  %maru_govde=0.5 açılışın) ya da "ikisi" (biri yeterli); ek olarak long için kapanış > EMA(devam_ma=200) ve RSI(14) > devam_rsi (50);
  short aynası. Önceki-trend (trend_mum) koşulu bu modda aranmaz. Stop/hedef/hacim filtresi eskisiyle aynı. NFI'nin 1sa RSI3/CMF ve
  4sa EMA12>EMA200 üst-zaman-dilimi filtreleri KODLANMADI (tek zaman dilimi).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MumYutanDonus(Strateji):
    ad = "swing__mum-yutan-donus"
    stil = "swing"
    varsayilan_parametreler = {
        "trend_mum": 6, "trend_min_atr": 1.0, "hacim_k": 0.0, "hacim_ort_mum": 20,
        "stop_modu": "uc", "tampon_atr": 0.1, "maks_risk_atr": 3.0,
        "hedef_r": 2.0, "atr_periyot": 14, "short": True,
        "mod": "donus", "desen": "yutan", "maru_oran": 0.9, "maru_govde": 0.5, "devam_ma": 200, "devam_rsi": 50.0,
    }
    parametre_izgarasi = {
        "trend_mum": [5, 7, 10],
        "hacim_k": [0.0, 1.0, 1.5],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        ac, yu, du, kap = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(yu, du, kap, p["atr_periyot"])
        ac1, kap1 = ac.shift(1), kap.shift(1)
        N = int(p["trend_mum"])
        dusus = (kap1 < kap.shift(1 + N)) & ((kap.shift(1 + N) - kap1) >= p["trend_min_atr"] * atr)
        yukselis = (kap1 > kap.shift(1 + N)) & ((kap1 - kap.shift(1 + N)) >= p["trend_min_atr"] * atr)
        boga = ((kap1 < ac1) & (kap > ac) & (ac <= kap1) & (kap >= ac1)
                & ((kap - ac) > (ac1 - kap1)))
        ayi = ((kap1 > ac1) & (kap < ac) & (ac >= kap1) & (kap <= ac1)
               & ((ac - kap) > (kap1 - ac1)))
        if p["mod"] == "devam":
            aralik = (yu - du).where(lambda x: x > 0)
            govde = (kap - ac).abs()
            maru_ok = (govde / aralik >= p["maru_oran"]) & (govde / ac >= p["maru_govde"] / 100.0)
            maru_boga, maru_ayi = maru_ok & (kap > ac), maru_ok & (kap < ac)
            if p["desen"] == "yutan":
                d_l, d_s = boga, ayi
            elif p["desen"] == "marubozu":
                d_l, d_s = maru_boga, maru_ayi
            elif p["desen"] == "ikisi":
                d_l, d_s = boga | maru_boga, ayi | maru_ayi
            else:
                raise ValueError(f"Bilinmeyen desen: {p['desen']}")
            ema = g.ema(kap, int(p["devam_ma"]))
            rsi = g.rsi(kap, 14)
            long_ok = d_l & (kap > ema) & (rsi > p["devam_rsi"])
            short_ok = d_s & (kap < ema) & (rsi < 100.0 - p["devam_rsi"]) & bool(p["short"])
        elif p["mod"] == "donus":
            long_ok, short_ok = boga & dusus, ayi & yukselis & bool(p["short"])
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        if p["hacim_k"] > 0:
            ort = mumlar["hacim"].shift(1).rolling(int(p["hacim_ort_mum"]), min_periods=int(p["hacim_ort_mum"])).mean()
            hok = mumlar["hacim"] > p["hacim_k"] * ort
            long_ok, short_ok = long_ok & hok, short_ok & hok

        alt2 = np.minimum(du, du.shift(1))
        ust2 = np.maximum(yu, yu.shift(1))
        tamp = p["tampon_atr"] * atr
        if p["stop_modu"] == "uc":
            stop_l, stop_s = alt2 - tamp, ust2 + tamp
        else:
            stop_l = stop_s = (alt2 + ust2) / 2.0
        risk_l, risk_s = kap - stop_l, stop_s - kap
        if p["maks_risk_atr"] > 0:
            long_ok = long_ok & (risk_l <= p["maks_risk_atr"] * atr)
            short_ok = short_ok & (risk_s <= p["maks_risk_atr"] * atr)
        long_ok = (long_ok & (risk_l > 0) & atr.notna()).fillna(False).to_numpy()
        short_ok = (short_ok & (risk_s > 0) & atr.notna()).fillna(False).to_numpy()

        yon = np.where(long_ok, 1, np.where(short_ok, -1, 0))
        stop = np.where(long_ok, stop_l, np.where(short_ok, stop_s, np.nan))
        k = kap.to_numpy()
        hedef = np.where(long_ok, k + p["hedef_r"] * risk_l.to_numpy(),
                         np.where(short_ok, k - p["hedef_r"] * risk_s.to_numpy(), np.nan))
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)

    def cikis_var_mi(self) -> bool:
        """hedef_r > 0 ise hedef var."""
        return self.parametreler["hedef_r"] > 0
