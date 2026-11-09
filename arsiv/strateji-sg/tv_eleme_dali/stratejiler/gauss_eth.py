"""TRADLEWARE Gaussian Channel ETH (egTb7TgJ): per=89, çarpan 1.5, StochRSI K>80 ya da <25, SMA200 rejimi, yeşil mum zorunlu; alt bant stop."""
from tv.stratejiler._gauss_tw import cekirdek
ISIM = "TRADLEWARE Gaussian Channel ETH"; PINE_ID = "egTb7TgJ"
PARAM = dict(per=89, mult=1.5, ust=80.0, alt=25.0)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "Başlık ETH; saat dilimi belirtilmemiş, 4 saatlik kripto."
def sinyal(df, per, mult, ust, alt): return cekirdek(df, per, mult, ust, alt, True, True)
