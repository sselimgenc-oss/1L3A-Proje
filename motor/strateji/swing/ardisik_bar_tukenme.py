"""swing__ardisik-bar-tukenme: 3-5 ardışık aynı yönlü mum (veya Woods yavaşlama/doruk) sonrası ters yönde giriş (4h/1d).

Kural (desen="renk", kanon + Velez/Ladha): son `seri_n` mum ardışık düşüş mumu (kapanış<açılış) ise long (yükseliş mumları
ardışıksa short). `zincir=True`: ek olarak her mumun zirvesi ve dibi bir öncekinden düşük (Velez Pristine PBS: lower high + lower
low + kırmızı mum). Tetik: "seri_sonu" -> serinin son mumunun kapanışında giriş (Velez "3-5 mum tükenmesi"); "kirilim" -> seriden
SONRAKİ mum, serinin son mumunun zirvesinin (short: dibinin) ÜSTÜNDE (altında) kapanırsa (Pristine "önceki günün yükseğini kır").
desen="yavaslama" / "doruk" (Woods): son `seri_n` mumda dipler ardışık düşer (short: zirveler yükselir); aşılan mesafeler
"yavaslama"da AZALIR, "doruk"ta (doruğa karşı) ARTAR; tetik "kirilim" (kurulum mumunun zirvesinin üstünde kapanış). 
Opsiyonel trend filtresi: trend_ma>0 ise long için kapanış > SMA(trend_ma) (Ladha/Velez: yükseliş trendinde düşüş serisi alınır; short ayna).
Stop = seri dibi (kirilimde giriş mumu dahil son seri_n+1 mumun en düşüğü; short zirvesi) -/+ stop_tampon_atr*ATR; risk > max_risk_atr*ATR
ise işlem yok. Hedef = hedef_r*R. Zaman çıkışı: zaman_cikisi_mum>0 ise `zaman_cikisi_mum` sütunu (Ladha ~2.5 gün, Pristine 1-5 gün).
Çıkış: hedef/stop (gün sonu yok).
Kaynak kartlar: swing__3-5-mum-tukenme__velez, swing__pristine-anahtar-alis-pbs__velez ve ...-satis-pss__velez, swing__2-5-gun-geri-donus__ladha
  (1G; yükseliş trendinde 2 gün düşüş + hacim azalması), swing__ortalamaya-donus__ladha (aylık dip + yeşil kapanış gün zirvesine yakın: ayrı
  mekanik, KODLANMADI), daytrade__yavaslama__woods ve daytrade__doruga-karsi__woods (desen="yavaslama"/"doruk"), scalp__iki-mum-kurulumu__grail
  (iki mum kurulumu, sabit pip hedef: KODLANMADI).
Kodlanmayan: hacim azalması (Ladha/Pristine), 5'ten fazla seri uyarısı (Velez), Woods'un yapısal pivot filtresi, trend yanında kullanım.
Varsayımlar: Velez/Pristine tick tamponları ATR tamponuna çevrildi; Woods'un 1 tik stop-emri girişi kapanış bazlı kırılıma çevrildi.
Negatif kanıt: yok; ancak Velez: 5'ten fazla art arda mum "felaket kayıp" riski (bıçak yakalama). Arşivde ortalamaya dönüş başarısız (arsiv/OZET.md §3).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


def _seri_ok(a, y, d, k, n: int, desen: str, zincir: bool, asagi: bool) -> pd.Series:
    """Son n mum 'düşüş serisi' (asagi=True; long için ters yön kurulumu) veya 'yükseliş serisi' ise True (mum n'de biter)."""
    if desen == "renk":
        renk = (k < a) if asagi else (k > a)
        ok = renk.rolling(n, min_periods=n).sum() == n
        if zincir:
            if asagi:
                zz = ((y < y.shift(1)) & (d < d.shift(1))).astype(float)
            else:
                zz = ((y > y.shift(1)) & (d > d.shift(1))).astype(float)
            ok &= zz.rolling(n - 1, min_periods=n - 1).sum() == (n - 1)
        return ok
    # Woods: uç fiyatın ardışık ilerleyişi (dipler düşer / zirveler yükselir) ve adım büyüklüğü azalır/artar
    uc = d if asagi else y
    adim = (uc.shift(1) - uc) if asagi else (uc - uc.shift(1))      # >0: seri yönünde ilerleme
    ok = (adim > 0).rolling(n - 1, min_periods=n - 1).sum() == (n - 1)
    for j in range(n - 2):
        kucul = adim.shift(j) < adim.shift(j + 1)       # son adım öncekinden küçük (yavaşlama)
        ok &= kucul if desen == "yavaslama" else (adim.shift(j) > adim.shift(j + 1))
    return ok


class ArdisikBarTukenme(Strateji):
    ad = "swing__ardisik-bar-tukenme"
    stil = "swing"
    varsayilan_parametreler = {
        "desen": "renk", "seri_n": 3, "zincir": False, "tetik": "kirilim", "trend_ma": 0,
        "stop_tampon_atr": 0.25, "max_risk_atr": 6.0, "hedef_r": 2.0, "zaman_cikisi_mum": 0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "seri_n": [3, 4, 5],
        "tetik": ["seri_sonu", "kirilim"],
        "zincir": [False, True],
        "hedef_r": [2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0 or self.parametreler["zaman_cikisi_mum"] > 0

    def _cekirdek(self, mumlar: pd.DataFrame, gun_sonu: bool = False, seans_saat: float = 0.0) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = int(p["seri_n"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        tetik = "kirilim" if p["desen"] != "renk" else p["tetik"]
        dus = _seri_ok(a, y, d, k, n, p["desen"], bool(p["zincir"]), True)      # düşüş serisi -> long kurulumu
        yuk = _seri_ok(a, y, d, k, n, p["desen"], bool(p["zincir"]), False)     # yükseliş serisi -> short kurulumu
        if tetik == "seri_sonu":
            long_ok, short_ok = dus, yuk
            pencere = n
        else:
            long_ok = dus.shift(1, fill_value=False) & (k > y.shift(1))
            short_ok = yuk.shift(1, fill_value=False) & (k < d.shift(1))
            pencere = n + 1
        short_ok = short_ok & bool(p["short"])
        if p["trend_ma"]:
            tr = g.sma(k, int(p["trend_ma"]))
            long_ok &= k > tr
            short_ok &= k < tr
        gecerli = atr.notna()
        long_ok &= gecerli
        short_ok &= gecerli
        tampon = p["stop_tampon_atr"] * atr
        stop_l = d.rolling(pencere, min_periods=pencere).min() - tampon
        stop_s = y.rolling(pencere, min_periods=pencere).max() + tampon
        long_ok &= (k - stop_l) <= p["max_risk_atr"] * atr
        short_ok &= (stop_s - k) <= p["max_risk_atr"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        sig = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, gun_sonu=gun_sonu, seans_saat=seans_saat)
        if p["zaman_cikisi_mum"] > 0:
            sig["zaman_cikisi_mum"] = np.where(sig["yon"] != 0, float(p["zaman_cikisi_mum"]), np.nan)
        return sig

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return self._cekirdek(mumlar)
