"""Flawless Victory v1 (i3Uc79fF, Trebor_Namor): kapanış Bollinger(20, 1σ) alt bandının altında ve RSI(14) > 42 → long; kapanış üst bandın üstünde ve RSI > 70 → pozisyonu kapat. Varsayılan sürüm 1 (SL/TP yok). Yalnız long."""
import numpy as np
from tv import gost
ISIM = "Flawless Victory v1"; PINE_ID = "i3Uc79fF"
PARAM = dict(bb=20, bb_c=1.0, rsi=14, rsi_al=42.0, rsi_sat=70.0)
TF = "15m"; EVREN = ["kripto"]; YON = 1
NEDEN = "Başlık '15min BTC': 15 dakikalık BTC → kripto 15dk."
def sinyal(df, bb, bb_c, rsi, rsi_al, rsi_sat):
    c = df.c.values; b = gost.sma(c, int(bb)); d = bb_c*gost.stdev(c, int(bb)); r = gost.rsi(c, int(rsi))
    with np.errstate(invalid="ignore"):
        return dict(sig=((c < b-d) & (r > rsi_al)).astype(float), xl=(c > b+d) & (r > rsi_sat))
