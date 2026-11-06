import json

import pytest

from motor.strateji import kayit


def test_dogrula_bos():
    assert kayit.dogrula() == []


def test_kgt_iki_varyant():
    t = kayit.tum_stratejiler()
    assert t["onceki__kgt"].stil == "swing" and t["onceki__kgt-gun"].stil == "daytrade"
    assert t["onceki__kgt"]().parametreler["gun_sonu_kapat"] is False
    assert t["onceki__kgt-gun"]().parametreler["gun_sonu_kapat"] is True
    assert "onceki__kgt-gun" in kayit.stile_gore("daytrade") and "onceki__kgt" not in kayit.stile_gore("daytrade")
    assert "swing__ma-kesisim" in t
    with pytest.raises(KeyError):
        kayit.al("yok")


def test_kart_ayarli_strateji(tmp_path, monkeypatch):
    monkeypatch.setattr(kayit, "KART_AYAR_DIZINI", tmp_path)
    (tmp_path / "onceki__kgt.json").write_text(json.dumps([
        {"kart_id": "a", "parametreler": {"cpr_esik": 0.3}, "cikis_ayarlari": {"kismi": [[1.0, 0.5]]}, "not": ""},
        {"kart_id": "b", "parametreler": {"yok": 1}, "cikis_ayarlari": None, "not": ""}]))
    s = kayit.kart_ayarli_strateji("onceki__kgt", "a")
    assert s.parametreler["cpr_esik"] == 0.3 and s.cikis_ayarlari.kismi == ((1.0, 0.5),)
    with pytest.raises(ValueError):
        kayit.kart_ayarli_strateji("onceki__kgt", "b")
    with pytest.raises(KeyError):
        kayit.kart_ayarli_strateji("onceki__kgt", "c")
    assert any("kart_id" in x for x in kayit.dogrula())
    assert kayit.kart_ayarlari("baska") == []
