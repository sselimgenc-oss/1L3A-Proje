"""Gap Filling (ghocsiv7): yeni seansın ilk saatlik mumunda yukarı boşluk → short, aşağı boşluk → long (boşluğu kapanışa doğru fade); hedef = önceki mumun gövde kenarı (boşluk dolum seviyesi); stop yok; sonraki seansın başında kapat."""
import numpy as np
from tv import gost
ISIM = "Gap Filling"; PINE_ID = "ghocsiv7"
PARAM = dict()
TF = "1h"; EVREN = ["abd", "bist"]
NEDEN = "Seans başı boşluk mantığı gün içi grafik ister; saatlik hisse."
def sinyal(df):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; n = len(c)
    gun = df.index.normalize().values; ses = np.r_[False, gun[1:] != gun[:-1]]
    po, pc, ph, pl = gost.sh(o), gost.sh(c), gost.sh(h), gost.sh(l)
    with np.errstate(invalid="ignore"):
        up = (o > ph) & (np.minimum(c, o) > np.maximum(pc, po)); dn = (o < pl) & (np.minimum(pc, po) > np.maximum(c, o))
    val = np.where(up, np.maximum(pc, po), np.minimum(pc, po))
    g = ses & (up | dn)
    sig = np.where(g & dn, 1.0, np.where(g & up, -1.0, 0.0))
    return dict(sig=sig, tp=np.where(g, val, np.nan), xl=ses, xs=ses)
