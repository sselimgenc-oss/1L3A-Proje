import json

import pandas as pd
import pytest

from motor.veri import kilit
from motor.veri.depo import funding_oku, mum_oku


@pytest.fixture
def veri(tmp_path, monkeypatch):
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", pd.Timestamp("2025-11-01", tz="UTC"))
    idx = pd.date_range("2025-10-30", periods=6, freq="1D", tz="UTC")
    d = tmp_path / "veri" / "S"
    d.mkdir(parents=True)
    pd.DataFrame({"acilis": 1.0}, index=idx).to_parquet(d / "1d.parquet")
    pd.DataFrame({"oran": 0.01}, index=idx).to_parquet(d / "funding.parquet")
    return tmp_path / "veri"


def test_varsayilan_kilitli(veri):
    assert mum_oku("S", "1d", dizin=veri).index.max() == pd.Timestamp("2025-10-31", tz="UTC")
    assert len(funding_oku("S", dizin=veri)) == 2
    assert len(mum_oku("S", "1d", bitis="2025-10-31", dizin=veri)) == 1
    assert len(mum_oku("S", "1d", bitis="2026-01-01", dizin=veri)) == 2
    assert not kilit.KILIT_LOG.exists()


def test_kilit_ac_gerekce_ve_kayit(veri):
    with pytest.raises(ValueError):
        mum_oku("S", "1d", dizin=veri, kilit_ac=True)
    with pytest.raises(ValueError):
        mum_oku("S", "1d", dizin=veri, kilit_ac=True, gerekce="  ")
    assert len(mum_oku("S", "1d", dizin=veri, kilit_ac=True, gerekce="final")) == 6
    assert len(funding_oku("S", dizin=veri, kilit_ac=True, gerekce="final")) == 6
    satirlar = [json.loads(x) for x in kilit.KILIT_LOG.read_text().splitlines()]
    assert len(satirlar) == 2 and satirlar[0]["sembol"] == "S" and satirlar[0]["gerekce"] == "final"
    assert satirlar[0]["zaman"] and isinstance(satirlar[0]["yigin"], list)
