"""Denetim Y-4: holdout mührü sürüm 3 = v2 + evren üyeliği (stil başına sembol listesi + imza), git commit ('yok' olabilir) ve
ortak motor/takvim modül hash'leri. v2 mühürleri hâlâ okunur. Holdout KOŞULMAZ (yalnız muhur_yaz / muhur_kontrol)."""
import json

import pytest

from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_holdout as wh
from testler.test_wf_evren import _holdout_cikti, _maliyet_ve_gunluk, veri_dizini  # noqa: F401  (fikstürler)


@pytest.fixture
def cikti(tmp_path, monkeypatch):
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    return _holdout_cikti(tmp_path)


def test_surum3_alanlari(cikti):
    m = json.loads((cikti / wh.MUHUR).read_text())
    assert m["surum"] == 3
    assert set(m["evren"]) == set(we.EVREN_STIL)
    assert m["evren"]["swing"]["semboller"] == ["TESTUSDT"] and m["evren"]["swing"]["imza"] == we.evren_imza(["TESTUSDT"])
    assert m["evren"]["daytrade"]["semboller"] == sorted(we.EVREN_GENEL)
    assert m["git_commit"] == "yok" or len(m["git_commit"]) >= 7
    assert set(m["ortak_modul_hash"]) == set(wh.ORTAK_MODULLER)
    for y in ("motor/backtest/motor.py", "motor/strateji/seans_takvimi.py", "motor/strateji/daytrade/_ortak.py",
              "motor/risk/limitler.py"):
        assert m["ortak_modul_hash"][y], y                          # dosya var ve hash'li
    wh.muhur_kontrol(cikti)


def test_evren_degisirse_dur(cikti, monkeypatch):
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT", "BTCUSDT"))
    with pytest.raises(wh.HoldoutHatasi, match="evren"):
        wh.muhur_kontrol(cikti)
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    wh.muhur_kontrol(cikti)
    monkeypatch.setitem(we.EVREN_STIL, "scalp", we.EVREN_GENEL[:-1])        # başka stilin evreni de kapsanır
    with pytest.raises(wh.HoldoutHatasi, match="evren"):
        wh.muhur_kontrol(cikti)


def test_ortak_modul_degisirse_dur(cikti, monkeypatch):
    gercek = wh.ortak_modul_hashleri()
    monkeypatch.setattr(wh, "ortak_modul_hashleri", lambda: {**gercek, "motor/backtest/motor.py": "ff"})
    with pytest.raises(wh.HoldoutHatasi, match="ortak motor modülü.*motor/backtest/motor.py"):
        wh.muhur_kontrol(cikti)
    monkeypatch.setattr(wh, "ortak_modul_hashleri", lambda: {**gercek, "motor/strateji/seans_takvimi.py": "ff"})
    with pytest.raises(wh.HoldoutHatasi, match="seans_takvimi"):
        wh.muhur_kontrol(cikti)


def test_ortak_modul_alani_silinirse_dur(cikti):
    m = json.loads((cikti / wh.MUHUR).read_text())
    del m["ortak_modul_hash"]
    (cikti / wh.MUHUR).write_text(json.dumps(m))
    with pytest.raises(wh.HoldoutHatasi, match="ortak motor modülü"):
        wh.muhur_kontrol(cikti)


def test_git_commit_kontrolu(cikti, monkeypatch):
    m = json.loads((cikti / wh.MUHUR).read_text())
    gercek = wh.git_commit
    monkeypatch.setattr(wh, "git_commit", lambda: "yok")                 # git yok: karşılaştırılamaz -> geçer
    wh.muhur_kontrol(cikti)
    m["git_commit"] = "0" * 40                                           # HEAD'in atası olmayan commit
    (cikti / wh.MUHUR).write_text(json.dumps(m))
    monkeypatch.setattr(wh, "git_commit", gercek)
    if gercek() != "yok":
        with pytest.raises(wh.HoldoutHatasi, match="commit"):
            wh.muhur_kontrol(cikti)


def test_v2_muhur_hala_okunur(cikti):
    m = json.loads((cikti / wh.MUHUR).read_text())
    for k in ("evren", "git_commit", "ortak_modul_hash"):
        m.pop(k)
    m["surum"] = 2
    (cikti / wh.MUHUR).write_text(json.dumps(m))
    assert wh.muhur_kontrol(cikti)["surum"] == 2
    m["surum"] = 4                                                        # bilinmeyen sürüm reddedilir
    (cikti / wh.MUHUR).write_text(json.dumps(m))
    with pytest.raises(wh.HoldoutHatasi, match="eski/eksik"):
        wh.muhur_kontrol(cikti)


def test_git_commit_bicimi():
    h = wh.git_commit()
    assert h == "yok" or (len(h) == 40 and set(h) <= set("0123456789abcdef"))
