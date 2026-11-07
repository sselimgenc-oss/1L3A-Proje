"""Gerçek yerel veriyle (veri/mumlar, repoda yok) kilitli dönem eşleşmesi. Veri yoksa atlanır. Tam 7'li sonuç: sonuclar/final/paper_esleme.json."""
import json
from pathlib import Path

import pandas as pd
import pytest

from motor.canli import paper_esleme as es
from motor.canli import paper_durum as pdr
from motor.canli import paper_sinyal as psg
from motor.veri import depo

VAR = (depo.MUM_DIZINI / "SOLUSDT" / "5m.parquet").exists() and (depo.MUM_DIZINI / "DK_AAPL" / "1h.parquet").exists()
pytestmark = pytest.mark.skipif(not VAR, reason="yerel mum verisi yok (veri/mumlar repoda değildir)")


@pytest.mark.parametrize("kimlik", ["swing__cci-esik|SOLUSDT|1d", "swing__konsolidasyon-kirilim|SOLUSDT|4h", "pf__kesit_ls|kripto|1d",
                                    "pf__kanarya|hisse_emtia|1d"])
def test_kilit_donemi_ilk_90_gun_bit_bit_ayni(kimlik):
    r = es.kilit_calistir([kimlik], gun=90)[0]
    assert r["tam_esit"], r["farklar"][:2]


def test_kayitli_tam_donem_sonucu_tutarli():
    yol = Path(es.__file__).resolve().parents[2] / "sonuclar" / "final" / "paper_esleme.json"
    if not yol.exists():
        pytest.skip("paper_esleme.json yok")
    d = json.loads(yol.read_text(encoding="utf-8"))["sonuclar"]
    assert len(d) == 7 and all(x["tam_esit_zaman_haric"] and x["max_mutlak_fark"] <= 1e-9 for x in d)


def test_ayar_yenileme_uyarisi_yazilir():
    import dataclasses
    from testler.test_paper_motor import TAN, kural, sentetik
    from motor.canli import paper as pp
    t = dataclasses.replace(TAN["swing__cci-esik|SOLUSDT|1d"], sonraki_yenileme="2025-02-01")
    m = sentetik(420, "1d", 3)
    p = pp.tekrar_calistir([t], {("SOLUSDT", "1d"): m}, {}, {"SOLUSDT": kural("SOLUSDT")}, m.index[400], None, kapat=False)
    o = pdr.olustur(p, m.index[-1] + pd.Timedelta(days=1, minutes=5), kaynak_saglik=[])
    assert any("AYAR YENİLEME" in u and "guncel_ayar" in u for u in o["saglik"]["uyarilar"])
