"""Testler gerçek sonuclar/deneme_kaydi.jsonl dosyasını kirletmesin."""
import pytest

import pandas as pd

from motor.backtest import deneme_kaydi
from motor.veri import kilit


@pytest.fixture(autouse=True)
def _deneme_kaydi_gecici(tmp_path, monkeypatch):
    monkeypatch.setattr(deneme_kaydi, "VARSAYILAN_YOL", tmp_path / "deneme_kaydi.jsonl")


@pytest.fixture(autouse=True)
def _kilit_gecici(tmp_path, monkeypatch):
    """Kilit günlüğü geçici dizine; sentetik test verisi kilitlenmesin (test_kilit.py kendi sınırını koyar)."""
    monkeypatch.setattr(kilit, "KILIT_LOG", tmp_path / "kilit_acilis.jsonl")
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", pd.Timestamp("2200-01-01", tz="UTC"))
