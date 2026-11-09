"""daytrade__orb: açılış aralığı kırılımı (Opening Range Breakout), gün sonunda kapanır.

Seans = `seans_saat` (UTC; varsayılan 0.0 = UTC gün başı; ABD açılışı için 13.5). Açılış aralığı = seans
başından itibaren ilk `aralik_dk` dakika içinde AÇILAN mumların en yüksek/en düşüğü (mum granülaritesi:
1h mumda 30 ve 60 dk aynıdır = ilk 1h mum). Aralık bitmeden sinyal yok. Aralığın üstünde kapanış (+tampon_atr*ATR)
-> long, altında kapanış -> short. `ust_yari_filtre`: kırılım mumunun kapanışı kendi aralığının üst yarısında
(short: alt yarı) olmalı (Bulkowski). `gunde_tek`: seansta yalnız ilk kırılım işlenir. İsteğe bağlı
`giris_penceresi_saat`: seans başından bu kadar saat sonra yeni giriş yok (0: sınırsız).
Stop: "karsi" = aralığın karşı ucu, "orta" = aralık ortası, "atr" = giriş -/+ atr_k*ATR. Hedef: hedef_r*R (0: yok;
yalnız gün sonu çıkışı). Çıkış: seansın son mumunda `cikis`.
Kaynak kartlar: daytrade__acilis-araligi-kirilimi__bulkowski, daytrade__ilk-saat-yon-takibi__derr (stop/kâr
  yok, "ilk 15 dk işlem yapma" kuralıyla çelişir: kodlanmadı), swing__orb-3-bar__scheier, orb-flama,
  eslesen-yuksek-dusuk, test-reddet-2-trend, kalici-trend-orb-geri-cekilme, maymun-barlari-orb-geri-donus
  (Scheier varyantları: yalnız temel kırılım kodlandı), swing__bosluk-aralik-kirilim__penn (boşluk filtresi yok).
NEGATİF KANIT (aile kaydı): Bulkowski, 60.801 gün x 555 hisse testi — ORB mekanik çıkışlarla (sabit stop,
  izleyen stop, yuvarlak sayı, gün sonu) komisyon sonrası ZARARLI; kâr yalnızca yazarın mekanik olmayan çıkış
  yorumlarıyla oluşuyor. Sabit stoplar kayıpları kısıyor ama kazananları da kesiyor; EMA10 filtresi ve giriş
  gecikmesi kötü. Scheier'in "çok yüksek tutarlılık" iddiası sayısal değil. DURUM.md: testte doğrulanırsa elenir.
Varsayımlar: kriptoda "açılış" yapaydır (UTC 00:00); kitaplar 1m veriyle yazılmıştır, burada 30m/1h mumdur.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi
from motor.strateji.temel import Strateji


class Orb(Strateji):
    ad = "daytrade__orb"
    stil = "daytrade"
    varsayilan_parametreler = {
        "aralik_dk": 60, "tampon_atr": 0.0, "ust_yari_filtre": True, "gunde_tek": True,
        "giris_penceresi_saat": 0.0, "stop_modu": "karsi", "atr_k": 1.0, "hedef_r": 0.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "aralik_dk": [30, 60, 120],
        "stop_modu": ["karsi", "orta", "atr"],
        "hedef_r": [0.0, 1.0, 2.0],
    }

    def cikis_var_mi(self) -> bool:
        return True   # gün sonu çıkışı

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        seans = seans_kimligi(mumlar.index, p["seans_saat"])
        gun_basi = (mumlar.index - pd.Timedelta(hours=float(p["seans_saat"]))).floor("D") \
            + pd.Timedelta(hours=float(p["seans_saat"]))
        ofset_dk = pd.Series((mumlar.index - gun_basi) / pd.Timedelta(minutes=1), index=mumlar.index)
        aralikta = ofset_dk < p["aralik_dk"]
        orh = y.where(aralikta).groupby(seans).cummax().groupby(seans).ffill()
        orl = d.where(aralikta).groupby(seans).cummin().groupby(seans).ffill()
        atr = g.atr(y, d, k, p["atr_periyot"])
        hazir = (~aralikta) & orh.notna() & atr.notna()
        if p["giris_penceresi_saat"]:
            hazir &= ofset_dk <= p["giris_penceresi_saat"] * 60.0
        tb = p["tampon_atr"] * atr
        long_ok = hazir & (k > orh + tb)
        short_ok = hazir & (k < orl - tb) & bool(p["short"])
        if p["ust_yari_filtre"]:
            konum = (k - d) / (y - d).replace(0.0, np.nan)
            long_ok &= konum >= 0.5
            short_ok &= konum <= 0.5
        if p["gunde_tek"]:
            ilk = (long_ok | short_ok).astype(int).groupby(seans).cumsum() == 1
            long_ok &= ilk
            short_ok &= ilk
        if p["stop_modu"] == "karsi":
            stop_l, stop_s = orl, orh
        elif p["stop_modu"] == "orta":
            stop_l = stop_s = (orh + orl) / 2.0
        else:
            stop_l, stop_s = k - p["atr_k"] * atr, k + p["atr_k"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s,
                       gun_sonu=True, seans_saat=p["seans_saat"])
