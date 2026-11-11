"""Strateji başına islem_risk (CANLI_PLAN.md): yapılandırma doğrulaması, boyut (%1,5 ve min(islem_risk, %3)), risk_adim_kontrol yardımcısı."""
import json
from decimal import Decimal as D

import pytest

from motor.canli.borsa import canli_ayar as ca
from motor.canli.borsa import kurallar as kr
from motor.canli.borsa import risk_adim_kontrol as rk
from testler.test_canli_borsa import COST, bilgi

S = {"id": "A", "api_key_env": "K1", "api_secret_env": "S1", "tahsis_usd": 250}


def test_islem_risk_varsayilan_ve_yalniz_015_kabul():
    assert ca.coz({"stratejiler": [S]}, {}).stratejiler[0].islem_risk == D("0.015")
    for v in (0.015, "0.015", "0.0150", D("0.015")):
        assert ca.coz({"stratejiler": [{**S, "islem_risk": v}]}, {}).stratejiler[0].islem_risk == D("0.015")


@pytest.mark.parametrize("v", [0.02, 0.03, 0.01, "0.025", 0.0149, 0.0151, 0, 0.0301, 0.05, 1, -0.02, "abc", None, True, [0.02], float("nan"), float("inf")])
def test_islem_risk_aralik_disi_reddedilir(v):
    with pytest.raises(ca.CanliAyarHatasi):
        ca.coz({"stratejiler": [{**S, "islem_risk": v}]}, {})


def test_islem_risk_hata_mesaji_plana_atif_yapar():
    with pytest.raises(ca.CanliAyarHatasi, match="CANLI_PLAN_V2.md §3"):
        ca.coz({"stratejiler": [{**S, "islem_risk": 0.03}]}, {})


def test_ornek_ayar_asama1_kadrosu():
    from pathlib import Path
    a = ca.yukle(Path(__file__).resolve().parents[1] / "stratejiler/canli_ayar.ornek.json", {})
    assert [s.id for s in a.stratejiler] == ["dis__e0v1en", "dis__ewo-ema-ofset"]
    assert all(s.tahsis_usd == 60 and s.islem_risk == D("0.015") for s in a.stratejiler)


def _boyut(E=D(250), **kw):
    k = kr.kural_cikar(bilgi(), "BTCUSDT")
    a = dict(ozsermaye=E, tahsis=D(250), yon=1, giris=D(50000), stop=D(47500), kural=k, **COST)
    a.update(kw)
    return kr.boyutlandir(**a)


def test_boyut_islem_risk_015_ve_3_ile_karsilastirma():
    b15 = _boyut(E=D(2500), tahsis=D(2500), islem_risk=D("0.015"))
    b30 = _boyut(E=D(2500), tahsis=D(2500))
    assert b15.neden is None and b30.neden is None and b15.baglayan == "kayip"
    assert b15.risk_yuzde <= 1.5 + 1e-9 and b15.risk_yuzde > 1.4              # ~ %1,5 (adıma aşağı yuvarlama)
    assert b30.risk_yuzde <= 3.0 and b30.qty > b15.qty * D("1.9")             # %3 yaklaşık iki katı


def test_boyut_etkin_tavan_min_islem_risk_ve_yuzde3():
    # islem_risk %3'ten büyük verilse bile (savunma) etkin tavan %3
    b = _boyut(E=D(2500), tahsis=D(2500), islem_risk=D("0.05"))
    assert b.neden is None and b.risk_yuzde <= 3.0 + 1e-9
    assert b.qty == _boyut(E=D(2500), tahsis=D(2500)).qty
    # 250 USD kasa, %1,5: stop %5 -> BTC min tutar 100: 3,75/(2500+75..) ham 0.0014 -> tutar < 100 -> atlanır
    assert _boyut(islem_risk=D("0.015")).neden == "min_tutar_alti"


def test_yurutucu_islem_risk_boyuta_gecer(tmp_path):
    from motor.canli.borsa.canli_yurutucu import Ayar
    from testler.test_canli_borsa import Ortam, ac_niyeti, gor
    e3 = Ortam(tmp_path / "a", tahsis=1000)                                     # islem_risk yok: %3 tavanı (eski davranış)
    e3.y.adim(gor([ac_niyeti()]))
    e15 = Ortam(tmp_path / "b", tahsis=1000)
    e15.ayar = Ayar("testnet", D(1000), D("0.015"))
    e15.y = e15.yeni()
    e15.y.adim(gor([ac_niyeti()]))
    q3, q15 = e3.borsa.poz["BTCUSDT"], e15.borsa.poz["BTCUSDT"]
    assert q3 == D("0.027") and q15 == D("0.013")                               # 15/1075 = 0.01395 -> 0.013
    assert q15 * (D(1000) + D(50000) * D("0.0015")) / D(1000) <= D("0.015")


# ---------------------------------------------------------------------------------------------- risk_adim_kontrol
def _dizin(tmp_path, kill=False, hesap_kill=False, hata=False, kars=None, olay_dosyasi=True):
    c = tmp_path / "canli"
    c.mkdir()
    (c / "yurutucu_a.json").write_text(json.dumps({"strateji": "A", "kill": kill}))
    (c / "yurutucu_b.json").write_text(json.dumps({"strateji": "B", "kill": False}))
    (c / "hesap_durumu.json").write_text(json.dumps({"kill": hesap_kill}))
    if olay_dosyasi:
        satirlar = [{"zaman": "2026-12-20T10:00:00Z", "tur": "canli_emir_doldu", "mesaj": "[A] ok"}]
        if hata:
            satirlar.append({"zaman": "2026-12-21T10:00:00Z", "tur": "canli_yurutucu_hatasi", "mesaj": "[A] ValueError: x"})
        (tmp_path / "olaylar.jsonl").write_text("\n".join(json.dumps(s) for s in satirlar))
    if kars is not None:
        (c / "haftalik_karsilastirma.json").write_text(json.dumps(kars))
    return tmp_path


def test_kontrol_hepsi_evet(tmp_path):
    d = _dizin(tmp_path, kars={"A": {"canli_maliyet_bps": 9, "model_maliyet_bps": 6, "eslesme_orani": 0.97}, "B": {"canli_maliyet_bps": 6, "model_maliyet_bps": 6, "eslesme_orani": 0.95}})
    r = rk.kontrol(d)
    assert r["A"] == dict(sistem_hatasi_yok="evet", maliyet_orani_ok="evet", eslesme_ok="evet", kill_yok="evet", hepsi="evet")
    assert r["B"]["hepsi"] == "evet"


def test_kontrol_hayir_durumlari(tmp_path):
    d = _dizin(tmp_path, kill=True, hata=True, kars={"A": {"canli_maliyet_bps": 9.1, "model_maliyet_bps": 6, "eslesme_orani": 0.94}})
    r = rk.kontrol(d)["A"]
    assert (r["sistem_hatasi_yok"], r["maliyet_orani_ok"], r["eslesme_ok"], r["kill_yok"], r["hepsi"]) == ("hayir",) * 5
    assert rk.kontrol(d)["B"]["sistem_hatasi_yok"] == "evet"                    # B'nin hatası yok (olaylar strateji önekiyle ayrılır)
    assert rk.kontrol(d, baslangic="2026-12-22")["A"]["sistem_hatasi_yok"] == "evet"   # pencere dışı


def test_kontrol_hesap_kill_ve_bilinmiyor(tmp_path):
    d = _dizin(tmp_path, hesap_kill=True, olay_dosyasi=False)
    r = rk.kontrol(d)["B"]
    assert r["kill_yok"] == "hayir" and r["sistem_hatasi_yok"] == "bilinmiyor" and r["maliyet_orani_ok"] == "bilinmiyor" and r["hepsi"] == "hayir"
    # veri yoksa tek başına 'bilinmiyor' (şart tutmuş sayılmaz)
    (tmp_path / "x").mkdir()
    d2 = _dizin(tmp_path / "x")
    assert rk.kontrol(d2)["A"]["hepsi"] == "bilinmiyor"


def test_kontrol_salt_okunur_ve_cli(tmp_path, capsys):
    d = _dizin(tmp_path)
    once = sorted((p.name, p.stat().st_mtime_ns) for p in d.rglob("*") if p.is_file())
    assert rk.main(["--durum", str(d)]) == 0
    assert "bilinmiyor" in capsys.readouterr().out
    assert once == sorted((p.name, p.stat().st_mtime_ns) for p in d.rglob("*") if p.is_file())
    assert rk.main(["--durum", str(tmp_path / "bos")]) == 1
