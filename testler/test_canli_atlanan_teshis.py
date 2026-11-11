import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "araclar"))
import canli_atlanan_teshis as t  # noqa: E402


def test_ozet_ve_neden():
    tr = pd.DataFrame({"sembol": ["A", "A", "B", "B"], "islem_no": [0, 1, 0, 1], "r": [4.0, -1.0, 0.5, 5.0]})
    kayit = [dict(sembol="A", islem_no=0, durum="alindi", neden="", qty=1.0), dict(sembol="A", islem_no=1, durum="atlandi", neden="min_tutar", qty=0.0),
             dict(sembol="B", islem_no=0, durum="alindi", neden="", qty=1.0)]       # B/1 kayıtsız -> diger
    d = t.sinyal_tablosu(tr, kayit)
    assert list(d["durum"]) == ["alindi", "atlandi", "alindi", "atlandi"]
    assert list(d["neden"]) == ["", "min_tutar", "", "diger"]
    o = t.ozet(d)
    assert o["alinan"] == 2 and o["atlanan"] == 2 and o["r3_toplam"] == 2 and o["r3_atlanan"] == 1
    assert abs(o["poz_r_atlanan_pay"] - 5.0 / 9.5) < 1e-9
