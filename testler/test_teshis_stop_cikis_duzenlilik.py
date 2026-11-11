"""Teşhis betikleri (araclar/teshis_stop_cikis.py, araclar/teshis_duzenlilik.py): sentetik doğrulama."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

KOK = Path(__file__).resolve().parents[1]


def _yukle(ad):
    s = importlib.util.spec_from_file_location(ad, KOK / "araclar" / f"{ad}.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


C = _yukle("teshis_stop_cikis")
D = _yukle("teshis_duzenlilik")
GUN = 86_400 * 10**9


def _mumlar(n=10):
    t = np.arange(n, dtype=np.int64) * GUN
    return t, np.full(n, 100.0), np.full(n, 101.0), np.full(n, 99.0)


def test_mae_mfe_long_uclar_haric():
    t, o, h, l = _mumlar()
    h[3], l[3] = 110.0, 90.0          # pencerenin İÇİNDE
    h[1], l[1] = 200.0, 1.0           # giriş mumu (index 1) -> dışarıda
    h[8], l[8] = 300.0, 0.0           # çıkış mumu (index 8) -> dışarıda
    mae, mfe, n = C.mae_mfe(1, 100.0, 5.0, 1 * GUN, 8 * GUN, GUN, t, h, l)
    assert (mae, mfe, n) == (2.0, 2.0, 6)     # mumlar 2..7; en kötü 90 -> 10/5, en iyi 110 -> 10/5


def test_mae_mfe_short_yon():
    t, o, h, l = _mumlar()
    h[4], l[5] = 106.0, 80.0
    mae, mfe, n = C.mae_mfe(-1, 100.0, 5.0, 1 * GUN, 8 * GUN, GUN, t, h, l)
    assert mae == pytest.approx(1.2) and mfe == pytest.approx(4.0)    # short: ters = yukarı (106), lehte = aşağı (80)


def test_mae_mfe_bos_pencere_ve_sifira_kirpma():
    t, o, h, l = _mumlar()
    assert C.mae_mfe(1, 100.0, 5.0, 1 * GUN, 2 * GUN, GUN, t, h, l) == (0.0, 0.0, 0)      # giriş+1 = çıkış
    mae, mfe, _ = C.mae_mfe(1, 50.0, 5.0, 0, 5 * GUN, GUN, t, h, l)                        # fiyat hep lehte
    assert mae == 0.0 and mfe > 0


def test_giris_fiyati_ilk_mum_ve_yok():
    t = np.array([5, 6, 30], dtype=np.int64)
    o = np.array([1.0, 2.0, 3.0])
    assert C.giris_fiyati(4, 3, t, o) == 1.0          # [4,7) içindeki ilk mum t=5
    assert np.isnan(C.giris_fiyati(10, 3, t, o))      # [10,13) boş


def test_sinifla():
    assert C.sinifla(0.40, 2.0) == "kayıp kısa / kâr uzun"
    assert C.sinifla(0.46, 3.0) == "karma"
    assert C.sinifla(0.60, 0.9) == "çok kazan az kazan"
    assert C.sinifla(0.60, 1.0) == "karma"


def test_strateji_olcu_basit():
    g = pd.to_datetime(["2020-01-01"] * 4, utc=True)
    c = pd.to_datetime(["2020-01-03", "2020-01-02", "2020-01-02", "2020-01-02"], utc=True)
    d = pd.DataFrame({"r": [3.0, -1.0, -0.3, -1.1], "mae_r": [0.9, 0.0, 0.0, 0.0], "mfe_r": [3.5, 1.2, 0.2, 0.1],
                      "n_mum_pencere": [5, 5, 5, 5], "giris_zamani": g, "cikis_zamani": c})
    o = C.strateji_olcu(d)
    assert o["kazanma_orani"] == 0.25 and o["payoff"] == pytest.approx(3.0 / ((1 + 0.3 + 1.1) / 3))
    assert o["kaz_pct_mae_08"] == 100.0 and o["kay_pct_mfe_1"] == pytest.approx(100 / 3)
    assert o["kaz_geri_verilen_medyan"] == pytest.approx(0.5)
    assert o["kayip_pct_tam_stop"] == pytest.approx(200 / 3)
    assert o["sure_gun_medyan_kazanan"] == 2.0 and o["sure_gun_medyan_kaybeden"] == 1.0


def test_islem_olc_tarih_siniri():
    df = pd.DataFrame({"giris_zamani": pd.to_datetime(["2025-11-08"], utc=True), "cikis_zamani": pd.to_datetime(["2025-11-09"], utc=True),
                       "yon": [1], "stop_mesafe": [1.0]})
    with pytest.raises(RuntimeError):
        C.islem_olc(df, "BTCUSDT", "1d")


def test_serisi_ve_dusus():
    assert D.en_uzun_kayip_serisi([1, -1, -2, -0.1, 3, -1]) == 3
    assert D.en_uzun_kayip_serisi([1, 2]) == 0
    z = pd.to_datetime(["2020-01-11", "2020-01-21", "2020-01-31", "2020-02-10"], utc=True)
    # başlangıç 01-01; +1 (zirve 01-11), -1, -0.5 (dip), +2.0 -> yeni zirve 02-10: düşüş süresi 30 gün
    assert D.en_uzun_dusus_gun(z, [1, -1, -0.5, 2.0], "2020-01-01", bitis="2020-03-01") == pytest.approx(30)
    # toparlanmayan: son zirve 01-11 -> bitiş 02-10 = 30 gün
    assert D.en_uzun_dusus_gun(z[:2], [1, -1], "2020-01-01", bitis="2020-02-10") == pytest.approx(30)


def test_bosluk_ve_pay():
    g = pd.to_datetime(["2020-01-01", "2020-01-05", "2020-03-01"], utc=True)
    assert D.en_uzun_bosluk_gun(g, bitis="2020-03-05") == pytest.approx(56)
    pay, kalan, k = D.en_iyi_pay([10, 1, 1, 1, 1, 1, 1, 1, 1, 1], 0.05)       # k = 1
    assert k == 1 and pay == pytest.approx(10 / 19) and kalan == pytest.approx(9)
    assert np.isnan(D.en_iyi_pay([-1.0, -2.0])[0])


def test_etiket():
    assert D.etiketle(90, 80, 1) == ("DÜZENLİ", "")
    e, n = D.etiketle(70, 60, -1)
    assert e == "DÜZENSİZ" and "ay" in n and "yıl" in n and "%5" in n


def test_olc_islem_ay_yil_semboller():
    g = pd.to_datetime(["2020-01-10", "2020-03-10", "2021-01-05"], utc=True)
    c = g + pd.Timedelta(days=2)
    d = pd.DataFrame({"giris_zamani": g, "cikis_zamani": c, "r": [2.0, -1.0, 1.0], "sembol": ["A", "B", "A"]})
    o = D.olc_islem(d)
    assert o["n_ay"] == 70 and o["islemli_ay_pct"] == pytest.approx(3 / 70 * 100)
    assert o["n_yil"] == 6                                                                  # 2020..2025
    assert o["yil_r"]["2020"] == 1.0 and o["yil_r"]["2021"] == 1.0 and o["arti_yil"] == 2
    assert o["en_iyi_sembol"] == "A" and o["en_iyi_sembol_cikinca_sigma"] == -1.0
    assert o["etiket"] == "DÜZENSİZ"


def test_olc_islem_tarih_siniri():
    d = pd.DataFrame({"giris_zamani": pd.to_datetime(["2025-11-07"], utc=True), "cikis_zamani": pd.to_datetime(["2025-11-08"], utc=True),
                      "r": [1.0], "sembol": ["A"]})
    with pytest.raises(RuntimeError):
        D.olc_islem(d)


def test_sabit_holdout_v2_ile_ayni():
    from motor.arastirma.v2 import sabit
    assert C.HOLDOUT_BAS == sabit.HOLDOUT_BAS and D.HOLDOUT_BAS == sabit.HOLDOUT_BAS


def test_veri_sonu_kapanisi_serbest_ama_sonrasi_degil():
    """Ek-1: veri sonunda zorunlu kapanan işlemin çıkış damgası tam HOLDOUT_BAS olabilir; 1 ns sonrası ya da giriş >= HOLDOUT_BAS hata."""
    ok = pd.DataFrame({"giris_zamani": pd.to_datetime(["2025-10-01"], utc=True), "cikis_zamani": [D.HOLDOUT_BAS], "r": [1.0], "sembol": ["A"]})
    o = D.olc_islem(ok)
    assert o["n_veri_sonu_kapanis"] == 1 and o["yil_r"]["2025"] == 1.0
    assert pd.Period("2025-11", "M") not in D._per([D.HOLDOUT_BAS], "M")
    kotu = ok.assign(cikis_zamani=[D.HOLDOUT_BAS + pd.Timedelta(1, "ns")])
    with pytest.raises(RuntimeError):
        D.olc_islem(kotu)
    with pytest.raises(RuntimeError):
        D.olc_islem(ok.assign(giris_zamani=[D.HOLDOUT_BAS]))
