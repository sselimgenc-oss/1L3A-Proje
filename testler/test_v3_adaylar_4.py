"""Parti 4 sinyal kuralları; piyasa sonucu veya backtest çalıştırmaz."""
import numpy as np
import pandas as pd

from motor.strateji.dis.v3_adaylar_4 import BtcGecelikMax10, GuniciMomentumNoise
from motor.strateji.kayit import al


def _mum(idx, fiyat):
    k = pd.Series(fiyat, index=idx, dtype=float)
    return pd.DataFrame({"acilis": k - 0.1, "yuksek": k + 0.2,
                         "dusuk": k - 0.2, "kapanis": k,
                         "hacim": 10.0}, index=idx)


def test_noise_alaninda_on_dort_gun_sonrasi_kirilim_stop_ve_gun_sonu():
    gunler = pd.bdate_range("2024-01-02", periods=17, tz="America/New_York")
    idx = pd.DatetimeIndex([t + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=30*i)
                            for t in gunler for i in range(13)]).tz_convert("UTC")
    fiyat = np.full(len(idx), 100.0)
    fiyat[-13 + 3] = 105.0
    m = _mum(idx, fiyat)
    s = GuniciMomentumNoise().sinyaller(m)
    assert s.yon.iloc[-13 + 3] == 1
    assert s.stop.iloc[-13 + 3] < m.kapanis.iloc[-13 + 3]
    assert s.cikis.iloc[-1]
    assert not (s.yon.iloc[:14*13] != 0).any()
    assert al(GuniciMomentumNoise.ad) is GuniciMomentumNoise


def test_btc_max10_cuma_giris_hafta_sonu_tutma_pazartesi_cikis():
    idx = pd.date_range("2024-01-01", periods=30*24, freq="1h", tz="UTC")
    m = _mum(idx, np.linspace(100, 120, len(idx)))
    s = BtcGecelikMax10().sinyaller(m)
    ny = idx.tz_convert("America/New_York")
    friday = np.where((ny.day_of_week == 4) & (ny.hour == 15) & (ny.date >= pd.Timestamp("2024-01-19").date()))[0][0]
    assert s.yon.iloc[friday] == 1 and s.stop.iloc[friday] < m.kapanis.iloc[friday]
    monday = np.where((ny.day_of_week == 0) & (ny.hour == 9) & (ny.date == pd.Timestamp("2024-01-22").date()))[0][0]
    assert s.cikis.iloc[monday]
    assert not s.cikis.iloc[friday + 1:monday].any()
    assert al(BtcGecelikMax10.ad) is BtcGecelikMax10
