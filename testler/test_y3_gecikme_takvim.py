"""Denetim Y-3: K1c gecikme stresi (GecikmeliStrateji) takvim sütununu (gun_sonu_kapanis) KAYDIRMAZ; giriş/çıkış sinyalleri
kayar. Kripto çerçevesinde sütun yoktur -> sonuç eski saf shift ile birebir aynı."""
import numpy as np
import pandas as pd

from motor.arastirma import wf_evren as we
from motor.backtest.motor import MotorAyarlari, backtest
from testler.test_bt_motor import Hazir, SIFIR, mumlar_yap


def _sig(df, gsk=True):
    s = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=df.index)
    s.iloc[1, s.columns.get_loc("yon")], s.iloc[1, s.columns.get_loc("stop")] = 1, 98.0
    s.iloc[4, s.columns.get_loc("cikis")] = True
    if gsk:
        s["gun_sonu_kapanis"] = False
        s.iloc[5, s.columns.get_loc("gun_sonu_kapanis")] = True
    return s


def test_takvim_sutunu_kaymaz_sinyaller_kayar():
    df = mumlar_yap([(100, 101, 99.5, 100)] * 8)
    st = Hazir(_sig(df))
    g = we.GecikmeliStrateji(st, 2).sinyaller(df)
    assert g["gun_sonu_kapanis"].dtype == bool
    assert g["gun_sonu_kapanis"].to_numpy().nonzero()[0].tolist() == [5]          # takvim: aynı mum
    assert g["yon"].to_numpy().nonzero()[0].tolist() == [3]                       # giriş 1 -> 3
    assert g["cikis"].to_numpy().nonzero()[0].tolist() == [6]                     # çıkış 4 -> 6
    assert list(g.columns) == list(st.sinyaller(df).columns) and g.index.equals(df.index)


def test_gecikmeli_gun_sonu_kapanisi_dogru_mumda_isler():
    df = mumlar_yap([(100, 101, 99.5, 100), (100, 101, 99.5, 100), (100, 101, 99.5, 100), (100, 101, 99.5, 101),
                     (101, 102, 100.5, 102), (102, 103, 101.5, 103), (103, 104, 102.5, 104), (104, 105, 103.5, 105)])
    s = _sig(df)
    s.iloc[4, s.columns.get_loc("cikis")] = False                # yalnız takvim çıkışı kalsın
    r = backtest(df, we.GecikmeliStrateji(Hazir(s), 1), MotorAyarlari(**SIFIR)).islemler
    t = r.iloc[0]
    assert t.cikis_nedeni == "gun_sonu"                           # kaydırılsaydı (6. mum) farklı mumda kapanırdı
    assert t.cikis_zamani == df.index[5] + pd.Timedelta("1h") and t.cikis_fiyati == 103.0


def test_kripto_cercevesi_eski_saf_shift_ile_birebir_ayni():
    df = mumlar_yap([(100, 101, 99.5, 100)] * 8)
    s = _sig(df, gsk=False)
    g = we.GecikmeliStrateji(Hazir(s), 1).sinyaller(df)
    eski = s.shift(1)
    eski["yon"] = eski["yon"].fillna(0).astype(int)
    eski["cikis"] = eski["cikis"].fillna(False).astype(bool)
    assert "gun_sonu_kapanis" not in g.columns
    pd.testing.assert_frame_equal(g, eski)
