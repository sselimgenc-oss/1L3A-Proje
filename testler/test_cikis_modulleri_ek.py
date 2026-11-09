"""Ek çıkış modülleri (varsayılanda kapalı): geriye dönük birebir aynılık + her modülün elle hesaplı senaryosu."""
import hashlib
import warnings

import numpy as np
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import cikislar as cks
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.ma_kesisim import MaKesisim
from motor.strateji.swing.dar_aralik_kirilim import DarAralikKirilim
from testler.test_bt_motor import SIFIR, Hazir, mumlar_yap, sinyal_yap
from testler.test_bt_strateji import rastgele_mumlar

# ---------- 1) varsayılanlar kapalıyken eski sonuçlarla birebir aynılık ----------
# Özetler, ek modüller koda eklenmeden ÖNCEKİ motorla üretildi (git stash ile eski/yeni karşılaştırıldı: aynı).
VARYANTLAR = [dict(), dict(atr_iz_suren_k=3.0), dict(atr_iz_suren_k=2.0, basabas_r_esigi=1.0), dict(basabas_r_esigi=0.5),
              dict(zaman_cikisi_mum=24), dict(sabit_r_hedefi=2.0), dict(sabit_r_hedefi=2.0, kismi=((1.0, 0.5),)),
              dict(atr_iz_suren_k=2.5, kismi=((1.0, 0.25), (2.0, 0.25)), basabas_r_esigi=1.0),
              dict(zaman_cikisi_mum=10, atr_iz_suren_k=1.5, atr_periyot=7), dict(sabit_r_hedefi=3.0, basabas_r_esigi=1.5),
              dict(atr_iz_suren_k=4.0, zaman_cikisi_mum=60), dict(kismi=((0.5, 0.3),), zaman_cikisi_mum=30)]
ALTIN = {
    "0.0.7": ("230bf5ccfb31d817", 38),
    "0.0.21": ("9cec6a4bde3592ef", 54),
    "0.1.7": ("e0a06e406506d9c6", 39),
    "0.1.21": ("a44fac23c6dc2d45", 57),
    "0.2.7": ("d33757987282aca5", 39),
    "0.2.21": ("92ffddbee4cea10a", 57),
    "0.3.7": ("cc5aff90df868e76", 37),
    "0.3.21": ("4ecbb0659c8b54e8", 55),
    "0.4.7": ("fe82ccb886203930", 38),
    "0.4.21": ("5b47b29f565faaa8", 56),
    "0.5.7": ("17554f24db97c9c2", 38),
    "0.5.21": ("54d93d1f98568c22", 56),
    "0.6.7": ("538b5f1dd0b804c7", 39),
    "0.6.21": ("64eaddbaa4f0061d", 57),
    "0.7.7": ("6090ebd2a547b371", 39),
    "0.7.21": ("73dcff4fe508630e", 57),
    "0.8.7": ("bdfb1347169b510e", 39),
    "0.8.21": ("c01703f14b2a3ade", 57),
    "0.9.7": ("c7ec1e6a0c4f5e3f", 37),
    "0.9.21": ("0a2773e201cb96dc", 55),
    "0.10.7": ("d60e8930b1021b6b", 38),
    "0.10.21": ("302df19c7f8a061a", 56),
    "0.11.7": ("0344060bf4c50108", 38),
    "0.11.21": ("aebe0bba83341030", 56),
    "1.0.7": ("921b219175c34109", 86),
    "1.0.21": ("c9903bb5026d9870", 58),
    "1.1.7": ("6e67a27b4a9cc7d6", 95),
    "1.1.21": ("3ccb63ef7183f046", 55),
    "1.2.7": ("cd89341b73aeadb7", 105),
    "1.2.21": ("987222e41d878095", 91),
    "1.3.7": ("432c9b0c2e7f4a5a", 108),
    "1.3.21": ("957cd9d37476c27e", 78),
    "1.4.7": ("351a8597d1eb11af", 94),
    "1.4.21": ("6b7f2c3aed31a5f0", 56),
    "1.5.7": ("921b219175c34109", 86),
    "1.5.21": ("c9903bb5026d9870", 58),
    "1.6.7": ("7d5c252af6bac88a", 87),
    "1.6.21": ("9ad44e9d937a109b", 76),
    "1.7.7": ("2cc7edcd2a556aec", 103),
    "1.7.21": ("97d71465c97cfb8a", 72),
    "1.8.7": ("223e01645daa6dad", 117),
    "1.8.21": ("6b8311fb032e5122", 94),
    "1.9.7": ("3fe054687f957351", 92),
    "1.9.21": ("f5e8d86a15752ce2", 64),
    "1.10.7": ("39f744c59eb6a27a", 90),
    "1.10.21": ("a1782ee82b289f84", 55),
    "1.11.7": ("8e0ac1bbd67666c7", 93),
    "1.11.21": ("79e6f029ceb7dcc7", 61),
}


def _ozet(sinif, v, seed):
    df = rastgele_mumlar(1200, seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            r = backtest(df, sinif(cikis_ayarlari=CikisAyarlari(**v)), MotorAyarlari())
            x = r.islemler.round(6).to_csv() + "|" + str(round(float(r.ozsermaye.iloc[-1]), 6)) + str(r.reddedilenler)
        except Exception as e:  # noqa: BLE001
            return hashlib.sha256(repr(e).encode()).hexdigest()[:16], 0
    return hashlib.sha256(x.encode()).hexdigest()[:16], len(r.islemler)


def test_varsayilanlar_kapaliyken_eski_sonuclar_birebir_ayni(monkeypatch):
    # Çıkış modüllerinin geriye dönük aynılığı: boyut eski (yalnız fiyat riski) formülle sabitlenir; maliyet dahil boyut (2026-11-09)
    # bilinçli bir boyut değişikliğidir ve test_maliyet_dahil_risk.py'de sınanır.
    import motor.backtest.motor as bm
    monkeypatch.setattr(bm, "maliyetli_risk_birim", lambda g, s, k, t: abs(g - s))
    sapan = []
    for si, sinif in enumerate((MaKesisim, DarAralikKirilim)):
        for vi, v in enumerate(VARYANTLAR):
            for seed in (7, 21):
                if _ozet(sinif, v, seed) != ALTIN[f"{si}.{vi}.{seed}"]:
                    sapan.append((si, vi, seed))
    assert not sapan, sapan


def test_yeni_alanlar_varsayilanda_kapali():
    ca = CikisAyarlari()
    assert ca.stop_basamaklari == () and ca.azalan_roi == () and ca.kar_rsi_esikleri == ()
    for ad in ("geri_cekilme_yuzde", "elder_guvenli_bolge_k", "agresif_iz_esigi", "agresif_iz_atr_k",
               "stop_sonrasi_bekleme_mum"):
        assert getattr(ca, ad) is None


# ---------- 2) modüller ----------
def _tek(df, giris, ca, **kw):
    sig = sinyal_yap(df, giris)
    return backtest(df, Hazir(sig, ca), MotorAyarlari(**SIFIR), **kw)


def test_stop_basamaklari_kademeli_stop():
    df = mumlar_yap([(100, 100, 100, 100),
                     (100, 102.5, 100, 102),       # giriş 100, risk 2; zirve 102.5 >= 1R -> stop 100
                     (102, 104.5, 101, 104),       # zirve >= 2R -> stop 102 (sonraki mumdan itibaren)
                     (104, 104, 101.5, 102.4),     # düşük 101.5 <= 102 -> stop 102'den
                     (102, 102, 102, 102)])
    r = _tek(df, {0: (1, 98.0, np.nan)}, CikisAyarlari(stop_basamaklari=((1.0, 0.0), (2.0, 1.0))))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(102.0) and t.r == pytest.approx(1.0)
    # kapalıyken aynı veri veri sonuna kadar taşınır
    t0 = _tek(df, {0: (1, 98.0, np.nan)}, CikisAyarlari(zaman_cikisi_mum=50)).islemler.iloc[0]
    assert t0.cikis_nedeni == "veri_sonu"


def test_stop_basamagi_fonksiyonu_gevsemez_ve_short():
    assert cks.stop_basamagi(1, 105.0, 100.0, 103.0, 2.0, ((1.0, 0.0),)) == 105.0     # mevcut stop daha sıkı
    assert cks.stop_basamagi(-1, 102.0, 100.0, 97.0, 2.0, ((1.0, 0.0), (1.5, 1.0))) == 98.0
    assert cks.stop_basamagi(1, 98.0, 100.0, 101.0, 2.0, ((1.0, 0.0),)) == 98.0       # eşik yok


def test_azalan_roi_tablosu():
    df = mumlar_yap([(100, 100, 100, 100),
                     (100, 101, 99.5, 100.5), (100.5, 101, 100, 100.8), (100.8, 101.5, 100.5, 101.2),
                     (101.5, 101.6, 101.4, 101.5), (101.5, 101.5, 101.5, 101.5)])
    r = _tek(df, {0: (1, 98.0, np.nan)}, CikisAyarlari(azalan_roi=((0, 5.0), (3, 1.0))))
    t = r.islemler.iloc[0]
    # 3. kapanışta (tutulan=3) kâr %1.2 >= %1 -> sonraki açılışta (mum 4) çıkış
    assert t.cikis_nedeni == "roi" and t.cikis_fiyati == pytest.approx(101.5)
    assert cks.azalan_roi_doldu(2, 4.9, ((0, 5.0), (3, 1.0))) is False
    assert cks.azalan_roi_doldu(3, 1.0, ((0, 5.0), (3, 1.0))) is True
    assert cks.azalan_roi_doldu(0, 0.5, ((5, 1.0),)) is False                           # henüz basamak yok


def test_zirveden_geri_cekilme():
    df = mumlar_yap([(100, 100, 100, 100),
                     (100, 104, 100, 103),         # zirve %4, kâr %3 (geri çekilme 1)
                     (103, 104, 101.5, 101.5),     # kâr %1.5 -> geri çekilme 2.5 >= 2 -> çıkış
                     (101, 101, 101, 101), (101, 101, 101, 101)])
    ca = CikisAyarlari(geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0)
    t = _tek(df, {0: (1, 98.0, np.nan)}, ca).islemler.iloc[0]
    assert t.cikis_nedeni == "geri_cekilme" and t.cikis_fiyati == pytest.approx(101.0)
    # zirve min kârı geçmediyse çıkış yok
    ca2 = CikisAyarlari(geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=5.0)
    assert _tek(df, {0: (1, 98.0, np.nan)}, ca2).islemler.iloc[0].cikis_nedeni == "veri_sonu"


def test_kar_rsi_yalniz_karda():
    # saf fonksiyon: zararda/sıfırda asla; kârda en yüksek ulaşılan basamak
    tablo = ((0.5, 70.0), (2.0, 55.0))
    assert cks.kar_rsi_doldu(1, -3.0, 99.0, tablo) is False
    assert cks.kar_rsi_doldu(1, 0.0, 99.0, tablo) is False
    assert cks.kar_rsi_doldu(1, 0.4, 99.0, tablo) is False          # henüz basamak yok
    assert cks.kar_rsi_doldu(1, 1.0, 69.0, tablo) is False
    assert cks.kar_rsi_doldu(1, 1.0, 71.0, tablo) is True
    assert cks.kar_rsi_doldu(1, 2.5, 56.0, tablo) is True           # kâr arttı -> eşik 55
    assert cks.kar_rsi_doldu(-1, 1.0, 29.0, tablo) is True and cks.kar_rsi_doldu(-1, 1.0, 31.0, tablo) is False
    # motor: sürekli yükselen seri -> kârda RSI 100 -> "kar_rsi"; sürekli düşen seri -> zararda çıkış yok
    n = 40
    yuk = [(100 + .5 * k, 100.3 + .5 * k, 99.9 + .5 * k, 100.2 + .5 * k) for k in range(n)]
    ca = CikisAyarlari(kar_rsi_esikleri=((0.5, 70.0),))
    t = _tek(mumlar_yap(yuk), {20: (1, 80.0, np.nan)}, ca).islemler.iloc[0]
    assert t.cikis_nedeni == "kar_rsi" and t.net_pnl > 0
    dus = [(100 - .5 * k, 100.1 - .5 * k, 99.7 - .5 * k, 99.8 - .5 * k) for k in range(n)]
    t = _tek(mumlar_yap(dus), {20: (1, 50.0, np.nan)}, ca).islemler.iloc[0]
    assert t.cikis_nedeni == "veri_sonu" and t.net_pnl < 0          # zararda sinyal çıkışı yok


def test_elder_guvenli_bolge_hesap():
    dusuk = [10, 9, 10, 8, 9, 10]
    assert cks.elder_guvenli_bolge(dusuk, 4, 3, 2, 1.0) == pytest.approx(7.0)   # j=3: 8-1*2=6 ; j=4: 9-1*2/... -> n2 içinde en yüksek 7
    assert np.isnan(cks.elder_guvenli_bolge(dusuk, 1, 3, 2, 1.0))
    assert cks.elder_guvenli_bolge(dusuk, 5, 3, 2, 1.0) == pytest.approx(10.0)  # son mumlarda düşüş yok -> dip


def test_elder_stopu_yukari_ceker():
    satir = [(100 + k, 100.8 + k, 99.5 + k, 100.5 + k) for k in range(16)]
    satir.append((116, 116, 90, 91))                    # sert düşüş: yükselmiş Elder stopuna çarpar
    satir += [(91, 91, 91, 91)] * 2
    df = mumlar_yap(satir)
    t = _tek(df, {2: (1, 90.0, np.nan)}, CikisAyarlari(elder_guvenli_bolge_k=1.0, elder_n1=4, elder_n2=2)).islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati > 105.0 and t.r > 0.5
    t0 = _tek(df, {2: (1, 90.0, np.nan)}, CikisAyarlari(zaman_cikisi_mum=100)).islemler.iloc[0]
    assert t0.cikis_fiyati <= 91.0


def test_farley_agresif_iz():
    satir = [(100, 101, 99, 100)] * 20 + [(100, 116, 100, 115), (115, 115, 110, 111), (111, 111, 111, 111)]
    df = mumlar_yap(satir)
    giris = {19: (1, 90.0, 130.0)}
    # aşama 2: geniş ATR izi; aşama 3: hedef yolunun %50'sinde dar iz
    ca = CikisAyarlari(atr_iz_suren_k=5.0, agresif_iz_esigi=0.5, agresif_iz_atr_k=0.5)
    t = _tek(df, giris, ca).islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati > 114.0
    t0 = _tek(df, giris, CikisAyarlari(atr_iz_suren_k=5.0)).islemler.iloc[0]
    assert t0.cikis_nedeni == "veri_sonu"


def test_stop_sonrasi_bekleme():
    satir = [(100, 100, 100, 100), (100, 100, 99, 99.5), (99.5, 99.5, 97, 97.5)] + [(100, 100, 99.9, 100)] * 5
    df = mumlar_yap(satir)
    sinyaller = {0: (1, 98.0, np.nan), 2: (1, 98.0, np.nan), 3: (1, 98.0, np.nan), 5: (1, 98.0, np.nan)}
    r0 = _tek(df, sinyaller, CikisAyarlari(zaman_cikisi_mum=100))
    assert r0.reddedilenler == [] and r0.islemler.iloc[0].cikis_nedeni == "stop"
    r = _tek(df, sinyaller, CikisAyarlari(zaman_cikisi_mum=100, stop_sonrasi_bekleme_mum=2))
    assert [x["neden"] for x in r.reddedilenler] == ["bekleme", "bekleme"]
    assert len(r.islemler) == 2 and r.islemler.iloc[1].giris_zamani == df.index[6]


def test_brooks_yonetimi_mevcut_alanlarla():
    # 2 kat stopta yarım, 3 katta çeyrek, ilk hedef (2R) sonrası başabaş: ek kod gerekmez
    df = mumlar_yap([(100, 100, 100, 100), (100, 104.5, 100, 104), (104, 106.5, 103, 106), (106, 106, 99, 100),
                     (100, 100, 100, 100)])
    ca = CikisAyarlari(kismi=((2.0, 0.5), (3.0, 0.25)), basabas_r_esigi=2.0, zaman_cikisi_mum=100)
    t = _tek(df, {0: (1, 98.0, np.nan)}, ca).islemler.iloc[0]
    assert t.kismi_sayisi == 2 and t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(100.0)
    assert t.net_pnl == pytest.approx(25 * 4 + 12.5 * 6)


def test_dogrulama_hatalari():
    for kw in (dict(kar_rsi_esikleri=((0.0, 60.0),)), dict(kar_rsi_esikleri=((-1.0, 60.0),)),
               dict(azalan_roi=((10, -1.0),)), dict(stop_basamaklari=((0.0, 0.0),)),
               dict(geri_cekilme_yuzde=0.0), dict(agresif_iz_esigi=0.75), dict(stop_sonrasi_bekleme_mum=0),
               dict(elder_guvenli_bolge_k=2.0, elder_n1=1)):
        with pytest.raises(ValueError):
            CikisAyarlari(**kw)


def test_kayit_alanlari_ve_json_listeleri():
    from motor.strateji import kayit
    from dataclasses import fields
    assert {f.name for f in fields(CikisAyarlari)} == kayit._CIKIS_ALANLARI
    ca = CikisAyarlari(**{"stop_basamaklari": [[1, 0], [2, 1]], "kar_rsi_esikleri": [[1, 70]]})
    assert ca.stop_basamaklari == ((1.0, 0.0), (2.0, 1.0))
    hash(ca)
