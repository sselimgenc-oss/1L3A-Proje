"""Mutasyon testleri (c) ve (d): portföy motorunda (motor/portfoy/motor.py; YALNIZ OKUNUR, değiştirilmez)
 (c) grup payı boyutlandırma: kolların hedef ağırlık payları (özsermayenin kesri) miktara birebir yansır; tavan aşılınca
     paylar ORANTILI küçülür (oran korunur).
 (d) hesap düzeyi kaldıraç kapısı: toplam brüt <= kaldirac/(1+kaldirac*taker)·özsermaye; ayar sert limiti (3x) aşamaz;
     tavan dolunca sıradaki giriş kırpılır / reddedilir."""
import pytest

from motor.portfoy.motor import portfoy_backtest
from testler.test_portfoy_motor import Elle, SIFIR, ayar, duz, tablo

SEMB = list("ABCD")        # hedef ağırlık kol başına en çok 1.0 (temel.py)


def _kos(paylar, stoplar=None, giris_satiri=0, cikis_satiri=6, n=9, **ay):
    v = {x: duz(n, 100.0) for x in paylar}
    k = list(paylar)
    h, s = tablo(v[k[0]].index, k), tablo(v[k[0]].index, k)
    for x in k:
        h.iloc[giris_satiri, h.columns.get_loc(x)] = paylar[x]
        s.iloc[giris_satiri, s.columns.get_loc(x)] = (stoplar or {}).get(x, 99.4)
        h.iloc[cikis_satiri, h.columns.get_loc(x)] = 0.0
    return portfoy_backtest(v, Elle(h, s), ayar(**{**SIFIR, **ay}))


def test_grup_payi_miktara_birebir_yansir():
    r = _kos({"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1})            # toplam 1.0x < 3x; stop dar (99.4, bar dibi 99.5 üstünde): risk bağlamaz
    q = r.pozisyon_gecmisi.iloc[2]
    # E=10000, fiyat 100 -> miktar = pay·E/100
    assert [float(q[x]) for x in SEMB] == pytest.approx([40.0, 30.0, 20.0, 10.0])
    assert not any(k["tur"] in ("kaldirac_orantili", "kaldirac", "portfoy_risk", "toplam_risk") for k in r.kirpmalar)


def test_grup_payi_tavan_asilinca_oran_korunur():
    r = _kos({"A": 1.0, "B": 1.0, "C": 1.0, "D": 0.6, "E": 0.6})   # toplam 4.2x -> 3x'e orantılı: 1:1:1:0.6:0.6
    q = r.pozisyon_gecmisi.iloc[2]
    assert q["B"] / q["A"] == pytest.approx(1.0, rel=2e-3) and q["C"] / q["A"] == pytest.approx(1.0, rel=2e-3)
    assert q["D"] / q["A"] == pytest.approx(0.6, rel=5e-3) and q["E"] / q["A"] == pytest.approx(0.6, rel=5e-3)
    assert r.maruziyet_dolum.max() == pytest.approx(3.0, abs=5e-3)
    assert any(k["tur"] == "kaldirac_orantili" for k in r.kirpmalar)


def test_grup_payi_risk_siniri_bagliyorsa_miktar_payin_altinda():
    # tek pozisyon toplam risk tavanı %5: stop 100'e çok yakın değil ama pay büyük -> pay yerine risk bağlar
    r = _kos({"A": 1.0}, stoplar={"A": 90.0})                      # pay 1x = 100 birim; risk/birim 10 -> %5 tavan = 50 birim
    assert float(r.pozisyon_gecmisi.iloc[2]["A"]) == pytest.approx(50.0, rel=1e-3)


def test_hesap_kaldiraci_komisyon_payli_tavan():
    r = _kos({"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}, komisyon_taker_yuzde=0.05, kayma_bps=0.0, stop_kayma_bps=0.0)
    # dolum anı nominali <= 3E/(1+3·taker) -> komisyon özsermayeden düşüldükten SONRA brüt/özsermaye <= 3x (komisyon payı
    # olmasaydı 3/(1-3·taker) ≈ 3.0045 olurdu) ve tavan gerçekten doldurulur
    assert r.maruziyet_dolum.max() <= 3.0 + 1e-9
    assert r.maruziyet_dolum.max() > 2.999


def test_ayar_kaldiraci_sert_limiti_asamaz_ve_alti_uygulanir():
    # 3x'in üstü istenir -> 3x; ayar 2x ise 2x
    r10 = _kos({"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}, kaldirac=10.0)
    assert r10.maruziyet_dolum.max() <= 3.0 + 1e-9 and r10.maruziyet_dolum.max() > 2.95
    assert any("sert limit" in u for u in r10.uyarilar)
    r2 = _kos({"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}, kaldirac=2.0)
    assert r2.maruziyet_dolum.max() <= 2.0 + 1e-9 and r2.maruziyet_dolum.max() > 1.95
    assert not any("sert limit" in u for u in r2.uyarilar)


def test_tavan_dolunca_sonraki_giris_kirpilir_sonra_reddedilir():
    kol = list("ABCDE")
    v = {x: duz(12, 100.0) for x in kol}
    h, s = tablo(v["A"].index, kol), tablo(v["A"].index, kol)
    for x, w in (("A", 1.0), ("B", 1.0), ("C", 0.9)):                  # satır 1'de toplam 2.9x dolar
        h.iloc[0, kol.index(x)], s.iloc[0, kol.index(x)] = w, 99.4
    h.iloc[3, kol.index("D")], s.iloc[3, kol.index("D")] = 1.0, 99.4   # satır 4'te yalnız ~0.1x oda var
    h.iloc[6, kol.index("E")], s.iloc[6, kol.index("E")] = 1.0, 99.4   # D sonrası oda ~0 -> red
    h.iloc[10] = 0.0
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    assert r.maruziyet_dolum.max() <= 3.0 + 1e-9
    kirp = [k for k in r.kirpmalar if k["sembol"] == "D" and k["tur"] in ("kaldirac", "kaldirac_orantili")]
    assert kirp, r.kirpmalar
    assert float(r.pozisyon_gecmisi.iloc[5]["D"]) == pytest.approx(10.0, abs=0.5)    # ~0.1x·10000/100
    assert float(r.pozisyon_gecmisi.iloc[8]["E"]) <= 0.5
    assert float(r.maruziyet_dolum.max()) <= 3.0 + 1e-9
