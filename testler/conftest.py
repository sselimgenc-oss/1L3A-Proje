"""Testler gerçek sonuclar/deneme_kaydi.jsonl dosyasını kirletmesin. Gerçek veri testleri için ortak skip/fail yardımcısı."""
import os

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
    kilit._sifirla()                  # süreç içi "ilk açılış" belleği testler arası taşınmasın
    yield
    kilit._sifirla()                  # bekleyen özetler (geçici yollara) süreç sonunda yazılmasın


# ------------------------------------------------------------- gerçek veriye bağlı testler (denetim Ö10)
# Gerçek veri (veri/mumlar, sonuclar/kilit ...) repoda yok; temiz ortamda bu testler atlanır. PAPER_GERCEK_VERI=1 ya da
# L3A_GERCEK_VERI=1 verilirse veri yokluğu SESSİZ ATLAMA değil HATA olur (sunucu/yerel tam doğrulama).
GERCEK_VERI_ORTAM = ("PAPER_GERCEK_VERI", "L3A_GERCEK_VERI")


def gercek_veri_zorunlu() -> bool:
    return any(os.environ.get(a) == "1" for a in GERCEK_VERI_ORTAM)


def gercek_veri_yok_isle(neden: str):
    """Gerçek veri yok: varsayılan pytest.skip; PAPER_GERCEK_VERI=1 / L3A_GERCEK_VERI=1 ise pytest.fail."""
    if gercek_veri_zorunlu():
        pytest.fail(f"gerçek veri zorunlu ({'/'.join(GERCEK_VERI_ORTAM)}=1) ama yok: {neden}", pytrace=False)
    pytest.skip(neden)


@pytest.fixture
def gercek_veri_yok():
    """Test/fixture içinde: `if not yol.exists(): gercek_veri_yok("neden")`."""
    return gercek_veri_yok_isle


def pytest_configure(config):
    config.addinivalue_line("markers", "gercek_veri(var, reason): var False ise skip; PAPER_GERCEK_VERI=1 ise fail")


def pytest_runtest_setup(item):
    for m in item.iter_markers("gercek_veri"):
        if not m.args[0]:
            gercek_veri_yok_isle(m.kwargs.get("reason", "gerçek veri yok"))
