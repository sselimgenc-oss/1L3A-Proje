"""MultiLayer Awesome Oscillator Saucer (HyzpDR9t, Skyrexio): trend=1 (fraktal kırılımı) iken AO 'tabak' (AO>0, dip dönüşü) + kapanış>EMA100 sinyali; sinyal tepesine stop-giriş; aynı trendde sinyal tekrarladıkça en çok 5 kademe ekleme; trend aşağı dönünce hepsi kapanır."""
import numpy as np
from tv import gost
from tv.stratejiler._skyr_kademe import bacaklar_stop
ISIM = "MultiLayer AO Saucer"; PINE_ID = "HyzpDR9t"
PARAM = dict(ema=100)
TF = "3h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 3 saat."
def _sg(b, ac):
    ao = b["ao"]; diff = ao - gost.sh(ao)
    with np.errstate(invalid="ignore"):
        s = (ao > gost.sh(ao)) & (gost.sh(ao) < gost.sh(ao, 2)) & (ao > 0) & (gost.sh(ao) > 0) & (gost.sh(ao, 2) > 0) & (b["tr"] == 1) & (b["c"] > b["ema"])
    return np.nan_to_num(s.astype(float)) > 0, diff
def sinyal(df, ema): return dict(bacaklar=bacaklar_stop(df, _sg, ema))
