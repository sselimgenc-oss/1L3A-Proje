"""BTC L biçimi kaynağındaki açık örnek profilin kapanış turu uyarlaması."""
from __future__ import annotations

import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis.v3_adaylar_2 import LSekliMaKirilimLong


class LSekliKaynak(LSekliMaKirilimLong):
    """20 mumda ilk yarı tepe → ikinci yarı dip düşüşü, 3 mum sıkışma, SMA100 kırılımı.

    Kaynak satırı: stratejiler/v3_adaylar/kartlar/daytrade__l-sekli-ma-kirilim-long__mgcha85.json
    Birincil kaynak: https://github.com/mgcha85/btc-lshape-long/blob/main/src/crypto_backtest/long_strategy.py
    Sabit profil: README.md örneği, MA100, düşüş %3, sıkışma 3 mum/%5,
    hedef %10, stop %5, +%3'te yarım kâr ve kalan için başabaş.
    Uyarlama: kaynak kapanış fiyatından anında açar; bu tur kapanmış sinyalin
    sonraki mum açılışından dolar. Yüzde seviyeleri sinyal kapanışına göre
    yazılır; dolum boşluğu seviyeleri değiştirebilir.
    """

    ad = "kapanis__l-sekli-kaynak"
    varsayilan_parametreler = {
        "ma_n": 100, "dusus_n": 20, "dusus_yuzde": 0.03,
        "sikisma_n": 3, "sikisma_yuzde": 0.05,
        "stop_yuzde": 0.05, "hedef_yuzde": 0.10,
    }
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(kismi=((0.6, 0.5),), basabas_r_esigi=0.6)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kapanis = mumlar["kapanis"]
        n = int(p["dusus_n"])
        if n < 2 or n % 2:
            raise ValueError("dusus_n çift ve en az 2 olmalı")
        onceki_yuksek = mumlar["yuksek"].shift(1)
        onceki_dusuk = mumlar["dusuk"].shift(1)
        ilk_yari_tepe = onceki_yuksek.shift(n // 2).rolling(n // 2, min_periods=n // 2).max()
        son_yari_dip = onceki_dusuk.rolling(n // 2, min_periods=n // 2).min()
        dusus = (ilk_yari_tepe - son_yari_dip) / ilk_yari_tepe >= float(p["dusus_yuzde"])
        kisa = int(p["sikisma_n"])
        onceki_tepe = onceki_yuksek.rolling(kisa, min_periods=kisa).max()
        onceki_dip = onceki_dusuk.rolling(kisa, min_periods=kisa).min()
        sikisma = (onceki_tepe - onceki_dip) / onceki_dip <= float(p["sikisma_yuzde"])
        ma = g.sma(kapanis, int(p["ma_n"]))
        kirilim = (kapanis.shift(1) < ma.shift(1)) & (kapanis > ma) & (kapanis > mumlar["acilis"])
        long_ok = dusus & sikisma & kirilim
        return cerceve(mumlar, long_ok, False,
                       kapanis * (1.0 - float(p["stop_yuzde"])), None,
                       kapanis * (1.0 + float(p["hedef_yuzde"])), None)
