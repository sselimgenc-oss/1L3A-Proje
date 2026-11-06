"""Testler gerçek sonuclar/deneme_kaydi.jsonl dosyasını kirletmesin."""
import pytest

from motor.backtest import deneme_kaydi


@pytest.fixture(autouse=True)
def _deneme_kaydi_gecici(tmp_path, monkeypatch):
    monkeypatch.setattr(deneme_kaydi, "VARSAYILAN_YOL", tmp_path / "deneme_kaydi.jsonl")
