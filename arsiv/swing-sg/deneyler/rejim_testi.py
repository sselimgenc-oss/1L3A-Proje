"""Piyasa rejimi filtresinin (sınıf endeksi trendi) etkisi, sınıf bazında."""
import pandas as pd
from swing.ayarlar import SECILI
from swing.calistir import OOS_BASLANGIC, islemler
from swing.motor import istatistik
rows = []
for st, p in SECILI.items():
    for rj in (None, "ema10_30", "ha", "ema10", "sma200"):
        tr = islemler(st, {**p, "rejim": rj})
        for sinif in ("bist", "kripto", "mag7", "emtia", "HEPSİ"):
            for per in ("IS", "OOS"):
                x = [t for t in tr if (sinif == "HEPSİ" or t.sinif == sinif) and
                     ((t.giris_tarih < OOS_BASLANGIC) == (per == "IS"))]
                s = istatistik(x)
                if s.get("islem"):
                    rows.append(dict(strateji=st, rejim=rj or "-", sinif=sinif, donem=per, n=s["islem"],
                                     WR=round(s["kazanma_orani"], 3), R=round(s["ort_R"], 3)))
df = pd.DataFrame(rows)
pv = df.pivot_table(index=["strateji", "sinif"], columns=["rejim", "donem"], values=["R"])
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(pv.round(2).to_string())
pv2 = df.pivot_table(index=["strateji", "sinif"], columns=["rejim", "donem"], values=["WR"])
print(pv2.round(2).to_string())
df.to_csv("deneyler/rejim_testi.csv", index=False)
