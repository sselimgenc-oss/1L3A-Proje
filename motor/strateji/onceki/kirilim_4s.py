"""onceki__4s-kirilim — N-mum Donchian kırılımı + hacim teyidi + EMA trend filtresi (algo-sg A1 + swing-sg S2).

ORİJİNAL KAYNAK
  algo-sg A1: arsiv/algo-sg/algo/final.py:15-18 (A1 sözlüğü), mantık arsiv/algo-sg/algo/strategies.py:182-252
  (`s5_momentum`, trigger="now"): 4H kapanış önceki 20 mumun zirvesini/dibini kırar (strategies.py:208-209,
  features.py:35-37 dcp_hi), 4H hacim oranı > 1.5 (features.py:45 vol_ratio = quote_hacim / önceki 20 mum ort.),
  kapanış 4H EMA100'ün doğru tarafında (entry_ema_side, strategies.py:240-244), long için BTC günlük > EMA200
  (long_btc=200, strategies.py:228-230). Giriş "olay" (koşulun ilk doğru olduğu mum; strategies.py:262-263).
  Stop 2x ATR(4H); %25 1R'de kapanır + başabaş; kalan için 10x ATR(4H) iz süren stop (trail_start_R=0);
  4H kapanış EMA100'ü ters keserse çık; en çok 720 saat (=180 4H mum) (final.py:15-18, strategies.py:264-275).
  swing-sg S2: arsiv/swing-sg/swing/stratejiler.py:115-147, ayarlar.py:5-6: günlük 20 mum Donchian kırılımı,
  ATR(5)/ATR(50) < 0.9 son 5 mumda "sıkışma" (opsiyonel), hacim > 20 mum ort., kapanış günlük aralığın
  üst %60'ında, stop 2 ATR, +1.5R'de %50 + başabaş, iz süren 4 ATR, 20 mum dip çıkışı, 30 gün.

1L3A'YA UYARLAMADA DEĞİŞENLER
  - Tek sembol: BTC rejim filtresi (long_btc=200) yerine AYNI sembolün günlük EMA(gunluk_ema=200) filtresi
    (ust_zaman, kapanmış günlük mumdan). Filtre short'a da AYNA uygulanır (orijinalde short'ta rejim filtresi
    yoktu: arsiv/ANALIZ_algo-sg.md §4 "short BTC filtresi yok"). Bu bir sapmadır.
  - Giriş 1H yerine mumun kendi TF'sinde (varsayılan 4h): orijinal 4H sinyalini 1H açılışta alıyordu.
  - Varsayılan çıkış yapılandırması CikisAyarlari ile A1 değerleri (kısmi %25@1R, başabaş 1R, iz 10xATR).
    S2'nin 1.5R/4xATR değerleri ızgara dışı; CikisAyarlari ile verilebilir.
  - Sıkışma (sikisma), kapanış konumu (kapanis_konum) ve kanal çıkışı (cikis_kanal) S2'den alındı; varsayılan
    KAPALI (S2 analizinde sıkışmanın IS'te etkisi yok: arsiv/ANALIZ_swing-sg.md §4.6).
  - Fiyat tabanlı ATR(14); hacim: quote_hacim.
  - Short orijinal A1'de vardı (long_only=False), varsayılan short=True.

ORİJİNAL RAPORLANAN SONUÇLAR (25 coin, 1H motor, %0.07/taraf, 2020-2026; arsiv/ANALIZ_algo-sg.md §4)
  A (A1+A2): 3147 işlem, WR %50.1, PF 1.61; IS PF 1.66, OOS PF 1.545; MTM yıllık %26.9, DD -%34.2.
  swing-sg S2 (günlük): n=501, PF_R 1.85, ort R +0.43; kripto IS +0.80R / OOS +0.58R.

KIRMIZI BAYRAKLAR (analiz raporlarından)
  - OOS kirli: ~3600 ızgara satırında OOS görüldü; denetimde kabul ölçütü IS+OOS+stres (algo-sg), S2 için ~648
    deneme hepsinde OOS görünür. Bu sonuçlar üst sınırdır.
  - Kâr yoğunlaşması: A'da en iyi %5 işlem +1351R, kalan %95 -551R (kuyruk bağımlı); 2025 PF 1.17, 2026 WR %39.6.
  - Short bacağı OOS'ta BTC<EMA200 rejiminde PF 0.90; "short=False" ızgara dışı ama denenmeli.
  - Evren bugünün büyükleri (hayatta kalma yanlılığı); tek sembolde (BTC) sonuç farklı olacaktır.
  - 1H kırılımlar sahte (Davey bar boyutu); bu strateji 4h/1d içindir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.htf import ust_zaman
from motor.strateji.onceki._ortak import cerceve, hacim_serisi, olay
from motor.strateji.temel import Strateji


class Kirilim4S(Strateji):
    ad = "onceki__4s-kirilim"
    stil = "swing"
    varsayilan_parametreler = {
        "donchian": 20,            # kırılım penceresi (mum)
        "hacim_k": 1.5,            # hacim > k x önceki `hacim_pencere` mum ortalaması; 0 = kapalı
        "hacim_pencere": 20,
        "ema_trend": 100,          # kapanış EMA'nın doğru tarafında; 0 = kapalı
        "gunluk_ema": 200,         # günlük kapanış > günlük EMA (ust_zaman); 0 = kapalı
        "sikisma": 0.0,            # S2: ATR(5)/ATR(50) < eşik (son sikisma_bakis mumda); 0 = kapalı
        "sikisma_bakis": 5,
        "kapanis_konum": 0.0,      # S2: kapanış mum aralığının üst (long) / alt (short) bu oranında; 0 = kapalı
        "stop_atr": 2.0,           # ilk stop = kapanış -/+ stop_atr x ATR
        "atr_periyot": 14,
        "cikis_ema": True,         # A1: kapanış EMA'yı ters keserse `cikis` (ema_trend > 0 gerekir)
        "cikis_kanal": 0,          # S2: ters yönde N mumluk kanal kırılımı ile çık; 0 = kapalı
        "max_mum": 180,            # zaman çıkışı (mum). A1: 720 saat = 180 x 4H; 0 = kapalı
        "short": True,
    }
    parametre_izgarasi = {
        "donchian": [20, 40, 55],
        "hacim_k": [0.0, 1.5, 2.0],
        "stop_atr": [2.0, 3.0, 4.0],
    }
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=10.0, atr_periyot=14, basabas_r_esigi=1.0, kismi=((1.0, 0.25),))

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        yu, du, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["donchian"])
        atr = g.atr(yu, du, kap, int(p["atr_periyot"]))
        ust = yu.shift(1).rolling(n, min_periods=n).max()
        alt = du.shift(1).rolling(n, min_periods=n).min()
        long_ok = (kap > ust) & atr.notna()
        short_ok = (kap < alt) & atr.notna() & bool(p["short"])

        if p["hacim_k"] > 0:
            hp = int(p["hacim_pencere"])
            v = hacim_serisi(mumlar)
            oran = v / v.rolling(hp, min_periods=max(1, hp // 2)).mean().shift(1)
            ok = oran > p["hacim_k"]
            long_ok &= ok
            short_ok &= ok
        ema = None
        if p["ema_trend"]:
            ema = g.ema(kap, int(p["ema_trend"]))
            long_ok &= kap > ema
            short_ok &= kap < ema
        if p["gunluk_ema"]:
            ge = int(p["gunluk_ema"])
            gd = ust_zaman(mumlar, "1d", lambda u: pd.DataFrame(
                {"kap": u["kapanis"], "ema": g.ema(u["kapanis"], ge)}))
            long_ok &= gd["kap"] > gd["ema"]
            short_ok &= gd["kap"] < gd["ema"]
        if p["sikisma"] > 0:
            oran_atr = g.atr(yu, du, kap, 5) / g.atr(yu, du, kap, 50)
            b = int(p["sikisma_bakis"])
            sik = (oran_atr < p["sikisma"]).astype(float).rolling(b, min_periods=b).max().fillna(0.0).astype(bool)
            long_ok &= sik
            short_ok &= sik
        if p["kapanis_konum"] > 0:
            konum = (kap - du) / (yu - du).replace(0, np.nan)
            long_ok &= konum >= p["kapanis_konum"]
            short_ok &= konum <= 1 - p["kapanis_konum"]

        long_ok, short_ok = olay(long_ok), olay(short_ok)      # trigger="now": koşulun ilk doğru olduğu mum
        stop_l = kap - p["stop_atr"] * atr
        stop_s = kap + p["stop_atr"] * atr

        cl = pd.Series(False, index=mumlar.index)
        cs = pd.Series(False, index=mumlar.index)
        if p["cikis_ema"] and ema is not None:
            cl |= kap < ema
            cs |= kap > ema
        m = int(p["cikis_kanal"])
        if m:
            cl |= kap < du.shift(1).rolling(m, min_periods=m).min()
            cs |= kap > yu.shift(1).rolling(m, min_periods=m).max()
        return cerceve(mumlar.index, long_ok, short_ok, stop_l, stop_s, None, p["max_mum"],
                       cikis_long=cl, cikis_short=cs)

    def cikis_var_mi(self) -> bool:
        p = self.parametreler
        return bool((p["cikis_ema"] and p["ema_trend"]) or p["cikis_kanal"] or p["max_mum"])
