"""Ek kripto verisi: 15dk (tüm kripto evreni) ve 5dk (SOL/BTC/ETH). python3 -m tv.veri_ek"""
import sys, concurrent.futures as cf
from tv import veri
def i(a): 
    d = veri.kripto(a[0], a[1]); print(a, None if d is None else len(d), flush=True)
if __name__ == "__main__":
    isler = [("SOL","5m"),("BTC","5m"),("ETH","5m")] + [(s,"15m") for s in veri.KRIPTO]
    with cf.ThreadPoolExecutor(3) as ex: list(ex.map(i, isler))
