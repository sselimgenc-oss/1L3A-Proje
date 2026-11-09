"""Gün sonu kapanışı (`gun_sonu_kapanis`) paritesi: tek-grafik backtest ↔ birleşik portföy motoru ↔ paper tekrar modu (seanslı 30m ABD
hissesi benzeri sentetik veri) + paper'ın desteklemediği çıkış ayarlarında kurulum hatası (fail-closed).

Denetim bulgusu (2026-11-09): gün sonu çıkışı yalnız tek-grafik backtest'e eklenmişti; portföy/paper motoru bayrağı yok sayıp
pozisyonu ertesi seans açılışına taşıyordu (ORB 30m: backtest 158 işlem / paper 157 işlem, farklı K/Z).
"""
import dataclasses
from decimal import Decimal

import pandas as pd
import pytest

from motor.arastirma import wf_tarama as wf
from motor.backtest.motor import SembolKurallari, backtest
from motor.canli import paper_esleme as es
from motor.canli import paper_sinyal as psg
from motor.canli.paper_motor import (PAPER_CIKIS_ALANLARI, Birim, PaperDesteklemiyorHatasi, PaperMotor, PKol,
                                     desteklenmeyen_cikis_alanlari)
from motor.portfoy.birlesik import birlesik_backtest
from motor.portfoy.motor import PortfoyAyarlari
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.kayit import al
from testler.test_gun_sonu_seans import _hisse_index, _mumlar

KURAL = SembolKurallari(0.01, 0.01, 0.01, 1.0)
SEMBOL = "DK_AAPL"
SUTUNLAR = ["yon", "giris_zamani", "giris_fiyati", "cikis_zamani", "cikis_fiyati", "miktar", "net_pnl", "cikis_nedeni"]


@pytest.fixture(scope="module")
def veri():
    idx = _hisse_index("2024-01-02", "2024-06-28", "30min")
    return _mumlar(idx, 3, gece_boslugu=0.02)


@pytest.fixture(scope="module")
def strateji():
    return al("daytrade__gap-devam")()


def _esit(a: pd.DataFrame, b: pd.DataFrame):
    assert len(a) == len(b)
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    for c in ("yon", "giris_zamani", "cikis_zamani", "cikis_nedeni"):
        assert (a[c] == b[c]).all(), c
    for c in ("giris_fiyati", "cikis_fiyati", "miktar", "net_pnl"):
        assert (a[c] - b[c]).abs().max() <= 1e-9, c


def test_backtest_gun_sonu_sinyali_ve_islemleri_var(veri, strateji):
    assert "gun_sonu_kapanis" in strateji.sinyaller(veri).columns
    isl = backtest(veri, strateji, wf.maliyet_ayarlari(KURAL)).islemler
    assert len(isl) >= 20 and (isl["cikis_nedeni"] == "gun_sonu").sum() >= 5
    assert {"stop", "hedef", "gun_sonu"} >= set(isl["cikis_nedeni"])


def test_portfoy_motoru_backtest_ile_ayni(veri, strateji):
    ay = dataclasses.replace(wf.maliyet_ayarlari(KURAL), limit_modu="uygula")
    bt = backtest(veri, strateji, ay).islemler
    pf_ay = PortfoyAyarlari(limit_modu="uygula", kurallar={SEMBOL: KURAL})
    pf = birlesik_backtest({SEMBOL: veri}, [(strateji, SEMBOL)], pf_ay, toplam_risk_tavani_yuzde=5.0).islemler
    assert (pf["cikis_nedeni"] == "gun_sonu").sum() == (bt["cikis_nedeni"] == "gun_sonu").sum() > 0
    _esit(bt[SUTUNLAR], pf[SUTUNLAR])


def test_paper_tekrar_modu_backtest_ile_ayni(veri, strateji):
    t = psg.StratejiTanim("x", "daytrade", "tek_grafik", strateji.ad, SEMBOL, "30m", "x", strateji, "g", Decimal(1))
    r = es.tek_esle(t, veri, None, {SEMBOL: KURAL}, veri.index[100])
    assert r["n_backtest"] == r["n_paper"] >= 20
    assert r["tam_esit"], r["farklar"][:3]          # zaman etiketi dahil: gun_sonu çıkışı mumun kapanış anıdır
    assert r["max_mutlak_fark"] <= 1e-9


def test_gun_sonu_bayragi_paper_kararinda_yalniz_seansli_veride(veri, strateji):
    t = psg.StratejiTanim("x", "daytrade", "tek_grafik", strateji.ad, SEMBOL, "30m", "x", strateji, "g", Decimal(1))
    son_mum = veri.index[veri.index.get_loc(veri.index[veri.index.tz_convert("America/New_York").time == pd.Timestamp("15:30").time()][5])]
    k = psg.tek_karar(t, veri.loc[:son_mum], None)["x"]
    assert k["gsk"] is True                                   # seansın son mumunun kapanışında bilinir (takvim; lookahead yok)
    k2 = psg.tek_karar(t, veri.loc[:veri.index[veri.index.get_loc(son_mum) - 1]], None)["x"]
    assert k2["gsk"] is False


# ------------------------------------------------------------------ Y-2: desteklenmeyen çıkış ayarı -> kurulum hatası
DESTEKSIZ = [
    dict(stop_basamaklari=((1.0, 0.0),)),
    dict(azalan_roi=((0, 4.0), (30, 1.0))),
    dict(geri_cekilme_yuzde=1.0),
    dict(kar_rsi_esikleri=((1.0, 70.0),)),
    dict(elder_guvenli_bolge_k=2.0),
    dict(agresif_iz_esigi=0.75, agresif_iz_atr_k=1.0),
    dict(stop_sonrasi_bekleme_mum=3),
]


def _birim(ca):
    kol = PKol(kimlik="k", sembol=SEMBOL, mod="sinyal", strateji_ad="s", cikis_ayarlari=ca)
    return Birim("b", "30m", pd.Timedelta("30min"), [kol], [SEMBOL])


def test_paper_cikis_alanlari_cikis_ayarlari_alanlarinin_alt_kumesi():
    assert PAPER_CIKIS_ALANLARI <= {f.name for f in dataclasses.fields(CikisAyarlari)}


@pytest.mark.parametrize("kw", DESTEKSIZ)
def test_desteklenmeyen_cikis_ayari_kurulumda_hata(kw):
    m = PaperMotor(PortfoyAyarlari(), {SEMBOL: KURAL})
    ca = CikisAyarlari(zaman_cikisi_mum=5, **kw)
    assert desteklenmeyen_cikis_alanlari(ca)
    with pytest.raises(PaperDesteklemiyorHatasi, match=next(iter(kw))):
        m.birim_ekle(_birim(ca))
    assert not m.birimler and not m.tum_kollar            # yarım kurulum kalmaz


def test_desteklenen_cikis_ayarlari_kabul_edilir():
    m = PaperMotor(PortfoyAyarlari(), {SEMBOL: KURAL})
    ca = CikisAyarlari(atr_iz_suren_k=2.0, atr_periyot=10, zaman_cikisi_mum=5, sabit_r_hedefi=2.0, basabas_r_esigi=1.0,
                       kismi=((1.0, 0.25),))
    assert desteklenmeyen_cikis_alanlari(ca) == []
    m.birim_ekle(_birim(ca))
    assert "b" in m.birimler
