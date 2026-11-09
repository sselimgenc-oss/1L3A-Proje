import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
parcalar = []
for osc, esikler in (("rsi2", [5, 10]), ("stok", [20]), ("bb", [0])):
    izgara = dict(osc=[osc], esik=esikler, yon_mod=["ema10", "ema10_30"], trend_sma=[100, 200],
                  stop_atr=[2.0, 3.0], limit_atr=[None, 0.5], max_gun=[5, 10], cikis_sma=[5, 10],
                  ardisik_dusus=[0, 2])
    parcalar.append(tara("S3_asiri_satim", izgara, min_islem=200))
df = pd.concat(parcalar).sort_values("skor", ascending=False)
df.to_csv("deneyler/s3_tarama.csv", index=False)
print(df.head(25).to_string(index=False))
