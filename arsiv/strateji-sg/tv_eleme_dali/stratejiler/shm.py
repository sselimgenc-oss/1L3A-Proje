"""Sovereign Horizon Matrix v8.0 (wVNfdkHu): hızlı WMA(63) ve makro WMA(510) (ohlc4); kapanış ya da tepe/dip bu WMA'ları yukarı/aşağı keserse, kapanış > SMA(41) (aşağı için <) ve günlük RSI(33) (iki gün gecikmeli) 42–48 (long) / 46–52 (short) bandındaysa giriş; stop tetik mumunun dibi/tepesi ∓%3 (varsayılan 'Candle-Close Trail' modülü %77 mesafede olduğundan fiilen yalnız bu stop çalışır); ters sinyalde dön."""
import numpy as np
from tv import gost
ISIM = "Sovereign Horizon Matrix"; PINE_ID = "wVNfdkHu"
PARAM = dict(hizli=63, yavas=510, hassas=41, rsi=33, l_alt=42.0, l_ust=48.0, s_alt=46.0, s_ust=52.0, sl=3.0)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "RSI'si günlük (1440) kilitli, WMA(510) uzun; gün içi grafik → saatlik."
def sinyal(df, hizli, yavas, hassas, rsi, l_alt, l_ust, s_alt, s_ust, sl):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; src = (o+h+l+c)/4
    f, s = gost.wma(src, int(hizli)), gost.wma(src, int(yavas)); fm = gost.sma(src, int(hassas))
    nn = lambda x: np.nan_to_num(x, nan=1e18)
    up = gost.crossover(c, nn(f)) | gost.crossover(c, nn(s)) | gost.crossover(h, nn(f)) | gost.crossover(h, nn(s))
    dn = gost.crossunder(c, nn(f)) | gost.crossunder(c, nn(s)) | gost.crossunder(l, nn(f)) | gost.crossunder(l, nn(s))
    r = gost.htf(df, "1D", lambda d: gost.sh(gost.rsi((d.o.values+d.h.values+d.l.values+d.c.values)/4, int(rsi)), 1))
    with np.errstate(invalid="ignore"):
        lg = up & (c > fm) & (r >= l_alt) & (r <= l_ust); sh = dn & (c < fm) & (r <= s_ust) & (r >= s_alt)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sl=np.where(lg, l*(1-sl/100), np.where(sh, h*(1+sl/100), np.nan)))
