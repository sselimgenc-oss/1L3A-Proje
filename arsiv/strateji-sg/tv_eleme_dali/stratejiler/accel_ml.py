"""MultiLayer Acceleration/Deceleration (ErcSuPyN, Skyrexio): AC osilatörü dönüş desenleri (signal1: AC>0 yükseliş devamı; signal2: AC<0 yükseliş) + trend=1 + kapanış>EMA100 → sinyal tepesine stop-giriş, en çok 5 kademe ekleme; trend dönünce hepsi kapanır."""
import numpy as np
from tv import gost
from tv.stratejiler._skyr_kademe import bacaklar_stop
ISIM = "MultiLayer Acceleration/Deceleration"; PINE_ID = "ErcSuPyN"
PARAM = dict(ema=100)
TF = "3h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 3 saat."
def _sg(b, ac):
    s_ = lambda k: gost.sh(ac, k); diff = ac - s_(1)
    with np.errstate(invalid="ignore"):
        s1 = (ac > 0) & (ac > s_(1)) & (s_(1) > s_(2)) & (s_(2) < s_(3)); s2 = (ac < 0) & (ac > s_(1)) & (s_(1) > s_(2)) & (s_(2) > s_(3)) & (s_(3) < s_(4))
        s = (s1 | s2) & (b["tr"] == 1) & (b["c"] > b["ema"])
    return np.nan_to_num(s.astype(float)) > 0, diff
def sinyal(df, ema): return dict(bacaklar=bacaklar_stop(df, _sg, ema))
