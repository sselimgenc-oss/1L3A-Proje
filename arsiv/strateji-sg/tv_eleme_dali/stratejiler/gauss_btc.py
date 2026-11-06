"""TRADLEWARE Gaussian Channel + StochRSI BTC (d1JxXpid): per=144, çarpan 1.414, StochRSI K>80 ya da <15, rejim ve yeşil mum zorunlu değil; alt bant stop."""
from tv.stratejiler._gauss_tw import cekirdek
ISIM = "TRADLEWARE Gaussian Channel BTC"; PINE_ID = "d1JxXpid"
PARAM = dict(per=144, mult=1.414, ust=80.0, alt=15.0)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "Başlık BTC; saat dilimi belirtilmemiş, 4 saatlik kripto."
def sinyal(df, per, mult, ust, alt): return cekirdek(df, per, mult, ust, alt, False, False)
