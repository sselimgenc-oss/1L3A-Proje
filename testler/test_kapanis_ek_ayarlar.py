"""Ek araştırma ayarlarının tamamı tekil ve kurulabilir olmalı."""
from __future__ import annotations

import json

import pytest

from motor.arastirma.kapanis.ek_ayarlar import ek_ayarlari_oku, ek_ayarli_strateji


def test_18_ek_ayar_kaynagi_ile_kurulur():
    ayarlar = ek_ayarlari_oku()
    assert len(ayarlar) == 18
    for kimlik, satir in ayarlar.items():
        st = ek_ayarli_strateji(kimlik, ayarlar)
        assert st.ad == satir["hedef"]
        for alan, deger in satir["parametreler"].items():
            assert json.loads(json.dumps(st.parametreler[alan])) == deger


def test_tekrarlanan_ayar_kimligi_reddedilir(tmp_path):
    satir = {"ayar_id": "x", "hedef": "pf__rotasyon", "parametreler": {}, "kaynak_dosya": "a"}
    yol = tmp_path / "ayar.json"
    yol.write_text(json.dumps([satir, satir]))
    with pytest.raises(ValueError, match="tekrarlanan"):
        ek_ayarlari_oku((yol,))
