"""v3 parti 6: Cuma 15:00 EST sonrası saatlik tutma (Miralles-Quiros & Miralles-Quiros 2022)."""
from __future__ import annotations

import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class Cuma15EstTutma(Strateji):
    """Cuma 15:00 EST olay mumunun kapanışında long, 4 saat tut (BTC 1h).

    Kaynak: https://oeconomia.pl/index.php/oc/article/download/2091/1935/2736 (Oeconomia Copernicana 13(3), 2022;
    Kraken saatlik BTC/USD, Eq.1 s.751, s.756-757).
    Kural (kart + ön kayıt): olay mumu = Cuma 15:00-15:59:59 EST; P0 = olay mumunun kapanışı = Cuma 16:00 EST;
    4 saat tutma, "19:59:59'da sat" = 20:00 EST. Yalnız long, yalnız Cuma, tek hücre (komşu saat/ufuk denenmez).
    Saat dilimi: kaynak "EST" der, yaz saatinden söz etmez (52.608 = 2192 x 24 -> sabit ofset); bu yüzden SABİT UTC-5
    kullanılır (DST yok): 15:00 EST = 20:00 UTC, giriş 21:00 UTC, çıkış Cumartesi 01:00 UTC.
    Zamanlama (mum indeksi = AÇILIŞ zamanı): sinyal 20:00 UTC açılışlı mumda (kapanışı 21:00 UTC bilinir), motor
    dolumu bir sonraki mumun açılışında (21:00 UTC) yapar. Çıkış sinyali Cumartesi 00:00 UTC açılışlı mumda,
    dolum 01:00 UTC açılışında (21,22,23,00 UTC = 4 mum tutulur).
    Stop kaynakta yok; bizim eklememiz: kapanış - 2 x ATR(14) (1h).
    """

    ad, stil = "v3__cuma-15-est-tutma", "daytrade"
    varsayilan_parametreler = {"sinyal_saat_utc": 20, "tut_saat": 4, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        idx = m.index
        u = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
        giris_saat = int(self.parametreler["sinyal_saat_utc"])
        cikis_saat = giris_saat + int(self.parametreler["tut_saat"])        # 24 -> ertesi gün (Cumartesi) 00:00 UTC
        long_ok = pd.Series((u.day_of_week == 4) & (u.hour == giris_saat) & (u.minute == 0), index=idx)
        # Çıkış mumu: giriş gününden sonraki gün (tut_saat <= 24 için Cumartesi) ya da aynı gün, saat = (giriş+tut) % 24.
        gun_kaydir = cikis_saat // 24
        cikis = pd.Series((u.day_of_week == (4 + gun_kaydir) % 7) & (u.hour == cikis_saat % 24) & (u.minute == 0),
                          index=idx)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(self.parametreler["atr_n"]))
        k = float(self.parametreler["atr_k"])
        return cerceve(m, long_ok, False, m["kapanis"] - atr * k, m["kapanis"] + atr * k, cikis=cikis)
