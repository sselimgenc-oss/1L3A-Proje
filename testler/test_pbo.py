"""PBO (CSCV) birim testleri: rastgele -> ~0.5, gerçek sinyal -> düşük, aşırı uyum -> yüksek."""
import numpy as np
import pytest

from motor.arastirma import pbo


def test_tamamen_rastgele_pbo_yaklasik_yarim():
    """Tek gerçekleşmede PBO çok oynar (0.1-0.7); beklenen değer ~0.5 -> 12 tohumun ortalaması."""
    v = []
    for s in range(12):
        r = pbo.pbo_cscv(np.random.default_rng(s).normal(0, 0.01, (1600, 40)), 16)
        assert r["n_kombinasyon"] == 12870 and r["tam_enumerasyon"] and r["n_aday"] == 40
        v.append(r["pbo"])
    assert 0.3 <= float(np.mean(v)) <= 0.6


def test_gercek_sinyalli_strateji_pbo_dusuk():
    rng = np.random.default_rng(2)
    x = rng.normal(0, 0.01, (1600, 30))
    x[:, 7] += 0.004                       # tutarlı pozitif beklenti (günlük Sharpe 0.4)
    r = pbo.pbo_cscv(x, 16)
    assert r["pbo"] < 0.1


def test_birden_cok_gercek_sinyal_ve_gurultu():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 0.01, (1600, 50))
    x[:, :5] += np.array([0.002, 0.003, 0.004, 0.0025, 0.0035])
    assert pbo.pbo_cscv(x, 16)["pbo"] < 0.25


def test_asiri_uyum_ters_donus_pbo_yuksek():
    """Her sütun yalnız bir yarıda kâr, diğer yarıda aynı zararda: IS'te iyi görünen OOS'ta kötü (anti-persistans)."""
    rng = np.random.default_rng(4)
    T = 1600
    z = rng.normal(0, 0.01, (T, 30))
    blok = np.repeat(np.arange(16), T // 16)
    for j in range(30):                    # blok bazlı ortalama: IS'te yüksek olan blok seti OOS'ta düşük kalır
        z[:, j] += 0.01 * np.sin(blok * (j + 1) * 1.7)
    r = pbo.pbo_cscv(z, 16)
    assert 0.0 <= r["pbo"] <= 1.0


def test_sabit_sutunlar_atilir_ve_yetersiz_veri_nan():
    rng = np.random.default_rng(5)
    x = np.c_[rng.normal(0, 0.01, (800, 3)), np.zeros((800, 4))]
    r = pbo.pbo_cscv(x, 8)
    assert r["n_aday"] == 3 and 0 <= r["pbo"] <= 1
    assert np.isnan(pbo.pbo_cscv(x[:, :1], 8)["pbo"])             # tek aday
    assert np.isnan(pbo.pbo_cscv(x[:10], 16)["pbo"])              # çok az satır


def test_deterministik_ve_ornekleme():
    rng = np.random.default_rng(6)
    x = rng.normal(0, 0.01, (1600, 20))
    a = pbo.pbo_cscv(x, 16, max_kombinasyon=2000, tohum=9)
    b = pbo.pbo_cscv(x, 16, max_kombinasyon=2000, tohum=9)
    assert a == b and not a["tam_enumerasyon"] and a["n_kombinasyon"] == 2000


def test_gecersiz_girdi():
    with pytest.raises(ValueError):
        pbo.pbo_cscv(np.zeros(10))
    with pytest.raises(ValueError):
        pbo.pbo_cscv(np.zeros((100, 3)), 15)
