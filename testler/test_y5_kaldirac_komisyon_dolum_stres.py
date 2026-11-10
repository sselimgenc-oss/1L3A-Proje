"""Y-5: tek-grafik kaldıraç tavanı komisyon payı dahil (portföy motoruyla aynı: kap = K·E/(1+K·taker));
gecikmeli giriş atlama anlamı (dolum denetimi önerisi 2); opt-in olumsuz dolum stresi (öneri 4/5; varsayılan kapalı)."""
import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_evren as we
from motor.backtest.motor import MotorAyarlari, backtest
from testler.test_bt_motor import Hazir, SIFIR, mumlar_yap, sinyal_yap

TAKER = 0.15   # %, belirgin olsun diye yüksek


def _yuksek_kaldirac_df():
    return mumlar_yap([(100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100), (100, 100.5, 99.5, 100)])


def test_kaldirac_tavani_komisyon_payi_dahil():
    df = _yuksek_kaldirac_df()
    sig = sinyal_yap(df, {0: (1, 99.99, np.nan)}, cikislar=[2])     # dar stop -> risk bazlı miktar çok büyük, tavan bağlar
    ay = MotorAyarlari(komisyon_taker_yuzde=TAKER, kayma_bps=0.0, stop_kayma_bps=0.0, risk_yuzde=1.0, kaldirac=3.0)
    t = backtest(df, Hazir(sig), ay).islemler.iloc[0]
    notional = t.miktar * t.giris_fiyati
    giris_kom = notional * TAKER / 100
    assert notional + giris_kom <= 3.0 * 10000 + 1e-6                # eski kod: ~30045 > 30000
    # tavan sıkı kullanılır (step 0.001 yuvarlaması dışında): 3·E/(1+3·taker)
    assert notional == pytest.approx(3.0 * 10000 / (1 + 3.0 * TAKER / 100), rel=1e-4)


def test_kaldirac_tavani_komisyonsuz_eski_deger_ayni():
    df = _yuksek_kaldirac_df()
    sig = sinyal_yap(df, {0: (1, 99.99, np.nan)}, cikislar=[2])
    t = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, kaldirac=3.0)).islemler.iloc[0]
    assert t.miktar * t.giris_fiyati == pytest.approx(30000.0, rel=1e-4)


# ---- gecikmeli giriş atlama anlamı ----
def _atlama_df():
    # bar0 sinyal; bar1 açılış 100 (stop 98 üstünde) giriş; bar1'de stop 98'e iner (base stop yer);
    # gecikmeli koşu bar2 açılışında girer: açılış 97 < stop 98 -> gecersiz_stop.
    return mumlar_yap([(100, 101, 99.5, 100), (100, 100.5, 97.5, 97.8), (97, 98, 96, 97), (97, 98, 96, 97), (97, 98, 96, 97)])


def test_gecikmeli_giris_stop_altina_acilinca_reddedilir():
    df = _atlama_df()
    s = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    base = backtest(df, Hazir(s), MotorAyarlari(**SIFIR))
    assert len(base.islemler) == 1
    t = base.islemler.iloc[0]
    assert t.giris_zamani == df.index[1] and t.giris_fiyati == 100.0       # open[i+1]'de girer
    assert t.cikis_nedeni == "stop" and t.cikis_zamani == df.index[1] + pd.Timedelta("1h")   # aynı mumda stoplanır
    gec = backtest(df, we.GecikmeliStrateji(Hazir(s), 1), MotorAyarlari(**SIFIR))
    assert gec.islemler.empty
    assert [r["neden"] for r in gec.reddedilenler] == ["gecersiz_stop"]


# ---- olumsuz dolum stresi ----
def _ornek():
    rng = np.random.default_rng(7)
    c = 100 + np.cumsum(rng.normal(0, 0.6, 400))
    o = np.r_[c[0], c[:-1]] + rng.normal(0, 0.1, 400)
    h = np.maximum(o, c) + rng.uniform(0.05, 0.8, 400)
    l = np.minimum(o, c) - rng.uniform(0.05, 0.8, 400)
    df = mumlar_yap(list(zip(o, h, l, c)))
    s = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=df.index)
    for k, i in enumerate(range(5, 380, 12)):
        y = 1 if k % 2 == 0 else -1
        s.iloc[i, s.columns.get_loc("yon")] = y
        s.iloc[i, s.columns.get_loc("stop")] = c[i] - y * 2.0
        s.iloc[i + 6, s.columns.get_loc("cikis")] = True
    return df, s


def test_olumsuz_dolum_varsayilan_birebir_ayni():
    df, s = _ornek()
    a = backtest(df, Hazir(s), MotorAyarlari())
    b = backtest(df, Hazir(s), MotorAyarlari(olumsuz_dolum=0.0))
    assert len(a.islemler) > 5
    pd.testing.assert_frame_equal(a.islemler, b.islemler)
    pd.testing.assert_series_equal(a.ozsermaye, b.ozsermaye)


def test_olumsuz_dolum_giris_cikis_en_az_kotu_ve_mum_icinde():
    df, s = _ornek()
    base = backtest(df, Hazir(s), MotorAyarlari()).islemler
    for x in (0.10, 0.15, 0.25):
        st = backtest(df, Hazir(s), MotorAyarlari(olumsuz_dolum=x)).islemler
        assert len(st) > 5
        m = base.merge(st, on="giris_zamani", suffixes=("_b", "_s"))
        assert len(m) > 5
        # giriş: long daha yüksek, short daha düşük alır/satar (>=); her dolum mum aralığında
        assert ((m.giris_fiyati_s - m.giris_fiyati_b) * m.yon_b >= -1e-9).all()
        assert (((m.giris_fiyati_s - m.giris_fiyati_b) * m.yon_b) > 0).any()
        # çıkış fiyatı da yönüne göre kötü ya da eşit (aynı çıkış nedeni/zamanı olanlarda)
        ayni = m[(m.cikis_zamani_b == m.cikis_zamani_s) & (m.cikis_nedeni_b == m.cikis_nedeni_s)]
        assert ((ayni.cikis_fiyati_s - ayni.cikis_fiyati_b) * ayni.yon_b <= 1e-9).all()
        for _, r in st.iterrows():
            gi = df.loc[r.giris_zamani]
            assert gi.dusuk - 1e-9 <= r.giris_fiyati <= gi.yuksek + 0.5   # kayma payı ile
        assert st.net_pnl.sum() <= base.net_pnl.sum() + 1e-6


def test_olumsuz_dolum_lookahead_yok():
    """Dolum mumundan SONRAKİ barları değiştirmek, o mumdaki girişleri etkilemez (yalnız dolum mumunun aralığı kullanılır)."""
    df, s = _ornek()
    ay = MotorAyarlari(olumsuz_dolum=0.25)
    a = backtest(df, Hazir(s), ay).islemler
    df2 = df.copy()
    cut = 200
    df2.iloc[cut + 1:, df2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 1.3
    b = backtest(df2, Hazir(s), ay).islemler
    on = a[a.cikis_zamani <= df.index[cut]]
    on2 = b[b.cikis_zamani <= df.index[cut]]
    assert len(on) > 3
    pd.testing.assert_frame_equal(on.reset_index(drop=True), on2.reset_index(drop=True))
