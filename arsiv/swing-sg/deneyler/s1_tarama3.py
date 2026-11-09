import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
izgara = dict(yon_mod=["ema10", "ema10_30", "ha"], hizli=[10, 20], rsi_esik=[50, 55, 60], kismi_R=[1.0, 1.5],
              stop_atr=[1.0, 1.5], iz_atr=[None, 4], max_gun=[15, 30])
df = tara("S1_geri_cekilme", izgara, min_islem=150)
df.to_csv("deneyler/s1_tarama3.csv", index=False)
d = df.copy(); d["n"] = d.IS_n + d.OOS_n
d["WR"] = (d.IS_WR * d.IS_n + d.OOS_WR * d.OOS_n) / d.n
print(d[(d.IS_WR >= .45) & (d.OOS_WR >= .45)].sort_values("OOS_R", ascending=False).head(15).to_string(index=False))
print(df.head(15).to_string(index=False))
