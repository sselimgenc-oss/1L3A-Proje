"""BTC Mean Reversion RSI+Bollinger (95JBkzXV): RSI(14)<30 ve kapanış BB(20,2) alt bandının altında → long; RSI>70 ve üst bandın üstünde → short; long'dan RSI>50 ya da kapanış orta bandı yukarı keserse çıkış (short ters)."""
import numpy as np
from tv import gost
ISIM = "BTC Mean Reversion (RSI+BB)"; PINE_ID = "95JBkzXV"
PARAM = dict(rsi=14, bb=20, bb_c=2.0)
TF = "1h"; EVREN = ["kripto"]
NEDEN = "Yazar 10 sn'lik bir haftalık pencerede test etmiş (anlamsız); saatlik kripto kullanıldı."
def sinyal(df, rsi, bb, bb_c):
    c = df.c.values; r = gost.rsi(c, int(rsi)); b = gost.sma(c, int(bb)); d = bb_c*gost.stdev(c, int(bb))
    with np.errstate(invalid="ignore"):
        le = (r < 30) & (c < b-d); se = (r > 70) & (c > b+d)
        xl = (r > 50) | gost.crossover(c, np.nan_to_num(b)); xs = (r < 50) | gost.crossunder(c, np.nan_to_num(b))
    return dict(sig=gost.flipsig(le, se), xl=xl, xs=xs)
