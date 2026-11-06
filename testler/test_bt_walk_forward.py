"""Walk-forward pencereleri ve uçtan uca çalışma."""
import pandas as pd

from motor.backtest.metrikler import hesapla
from motor.backtest.walk_forward import pencereler_uret, walk_forward
from motor.strateji.ma_kesisim import MaKesisim
from testler.test_bt_strateji import rastgele_mumlar


def test_pencereler_cakismaz():
    bas = pd.Timestamp("2024-01-01", tz="UTC")
    bit = pd.Timestamp("2024-12-31", tz="UTC")
    p = pencereler_uret(bas, bit, egitim_gun=90, test_gun=30)
    assert len(p) > 5
    for e0, e1, t0, t1 in p:
        assert e0 < e1 == t0 < t1 <= bit
        assert (e1 - e0).days == 90 and (t1 - t0).days == 30
    for a, b in zip(p, p[1:]):
        assert b[3 - 1] == a[3]                # test pencereleri uç uca, kesişmez
        assert a[3] - a[2] == b[2] - a[2]      # adım = test uzunluğu
        assert b[2] >= a[3]


def test_walk_forward_uctan_uca():
    df = rastgele_mumlar(n=24 * 200, seed=3)    # 200 gün saatlik
    s = MaKesisim()
    s.parametre_izgarasi = {"hizli": [5, 9], "yavas": [21, 34]}
    r = walk_forward(s, df, egitim_gun=60, test_gun=20, min_islem=1, isinma_mum=100)
    assert len(r["pencereler"]) >= 4
    secilenler = [p["secilen"] for p in r["pencereler"] if p["secilen"]]
    assert secilenler and all(set(x) == {"hizli", "yavas"} for x in secilenler)
    # OOS özsermaye indeksi artan ve tekrarsız -> pencereler kesişmedi
    assert r["ozsermaye"].index.is_monotonic_increasing and r["ozsermaye"].index.is_unique
    if len(r["islemler"]):
        assert r["islemler"]["giris_zamani"].is_unique
    assert "sharpe" in r["metrikler"]


def test_metrikler_basit():
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    oz = pd.Series([100, 110, 99, 120, 130.0], index=idx)
    isl = pd.DataFrame({
        "net_pnl": [10.0, -11.0, 21.0, 10.0], "r": [1.0, -1.0, 2.0, 1.0],
        "komisyon": [1.0] * 4, "funding": [0.5] * 4,
        "giris_zamani": idx[:4], "cikis_zamani": idx[1:]})
    m = hesapla(isl, oz, 100.0)
    assert abs(m["net_getiri"] - 0.30) < 1e-12
    assert abs(m["max_dusus"] - 0.10) < 1e-12
    assert abs(m["profit_factor"] - 41 / 11) < 1e-12
    assert m["kazanma_orani"] == 0.75 and m["islem_sayisi"] == 4
    assert m["toplam_komisyon"] == 4.0 and m["ortalama_tutma_saat"] == 24.0
    assert abs(m["beklenen_deger"] - 7.5) < 1e-12
