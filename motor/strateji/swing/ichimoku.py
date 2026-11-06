"""swing__ichimoku: Ichimoku (Tenkan/Kijun/bulut). Stil alt sınıfı: daytrade/ichimoku.py.

Modlar (`mod`):
  "kijun_bulut": fiyat hem bulutun hem Kijun'un üstüne (altına) yeni çıkarsa long (short) — swing__ichimoku-kijun-bulut__make.
                 Giriş: bu durumun BAŞLADIĞI mum (aynı durum sürerken tekrar sinyal yok). Çıkış: kapanış Kijun'u ters yönde keser.
  "tk_bulut"   : Tenkan > Kijun ve kapanış bulutun üstünde (short: Tenkan < Kijun ve kapanış bulutun altında) durumu yeni
                 oluştuğunda; tk_kesisim=True ise Tenkan/Kijun kesişimi o mumda gerçekleşmiş olmalı (kanonik kural).
                 Çıkış: Tenkan/Kijun ters kesişimi (kart: ters kesişim).
Parametreler: tenkan (9), kijun (26), senkou_b = 2*kijun, kaydirma = kijun (standart 9/26/52/26). Bulut t. mumda kaydirma mum
ÖNCE hesaplananın ileri taşınmasıdır (nedensel; bkz. gostergeler_b2.ichimoku). Chikou kullanılmaz.
Stop (`stop_tipi`): "kijun", "span_a" (Senkou A) veya "bulut" (long için
bulut ALT kenarı, short için bulut ÜST kenarı); -/+ stop_tampon_atr*ATR; risk <= stop_max_atr ATR (daha uzaksa stop yaklaştırılır).
Stop giriş kapanışının yanlış tarafındaysa sinyal düşer. Hedef: hedef_r>0 ise (daytrade kartı 1:3).
Kaynak kartlar: swing__ichimoku-kijun-bulut__make (D1, tek koşul: bulut+Kijun üstü; Tenkan eğimi onayı kodlanmadı),
daytrade__ichimoku-tenkan-kijun-bulut__singhal (1h, stop Span A, 1:3 önerisi, 1d üst filtre önerisi kodlanmadı).
Varsayımlar: kitaplarda stop/çıkış net değil (Make'te hiç yok) -> yukarıdaki stoplar ve ters kesişim çıkışı; kripto 7/24 olduğundan
9/26/52 standardı kullanıldı. Negatif kanıt: aile kaydında yok; arşivde MA/bulut trend denemesi yok, tek kural trend (altın/endeks) başarısız.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class Ichimoku(Strateji):
    ad = "swing__ichimoku"
    stil = "swing"
    _gun_sonu = False
    varsayilan_parametreler = {
        "mod": "kijun_bulut", "tenkan": 9, "kijun": 26, "tk_kesisim": False,
        "stop_tipi": "kijun", "stop_tampon_atr": 0.1, "stop_max_atr": 4.0, "hedef_r": 0.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "mod": ["kijun_bulut", "tk_bulut"],
        "kijun": [26, 52],
        "stop_tipi": ["kijun", "bulut"],
        "tenkan": [9, 12],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        kj = int(p["kijun"])
        ic = b.ichimoku(y, d, int(p["tenkan"]), kj, 2 * kj, kj)
        atr = g.atr(y, d, k, p["atr_periyot"])
        t, kij = ic["tenkan"], ic["kijun"]
        bu, ba = ic["bulut_ust"], ic["bulut_alt"]
        gecerli = atr.notna() & bu.notna() & ba.notna() & t.notna() & kij.notna()
        if p["mod"] == "kijun_bulut":
            long_d = (k > bu) & (k > kij)
            short_d = (k < ba) & (k < kij)
            cikis = b.asagi_kesis(k, kij) | b.yukari_kesis(k, kij)
        elif p["mod"] == "tk_bulut":
            long_d = (t > kij) & (k > bu)
            short_d = (t < kij) & (k < ba)
            if p["tk_kesisim"]:
                long_d &= b.yukari_kesis(t, kij) | b.yukari_kesis(t, kij).shift(1, fill_value=False)
                short_d &= b.asagi_kesis(t, kij) | b.asagi_kesis(t, kij).shift(1, fill_value=False)
            cikis = b.asagi_kesis(t, kij) | b.yukari_kesis(t, kij)
        else:
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        long_ok = b.gecis(long_d & gecerli)
        short_ok = b.gecis(short_d & gecerli) & bool(p["short"])
        tampon = p["stop_tampon_atr"] * atr
        if p["stop_tipi"] == "kijun":
            stop_l, stop_s = kij - tampon, kij + tampon
        elif p["stop_tipi"] == "span_a":
            stop_l, stop_s = ic["span_a"] - tampon, ic["span_a"] + tampon
        elif p["stop_tipi"] == "bulut":
            stop_l, stop_s = ba - tampon, bu + tampon
        else:
            raise ValueError(f"Bilinmeyen stop_tipi: {p['stop_tipi']}")
        stop_l = pd.concat([stop_l, k - p["stop_max_atr"] * atr], axis=1).max(axis=1, skipna=False)
        stop_s = pd.concat([stop_s, k + p["stop_max_atr"] * atr], axis=1).min(axis=1, skipna=False)
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis & gecerli,
                       gun_sonu=self._gun_sonu, seans_saat=p["seans_saat"])
