import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
izgara = dict(yon_mod=["ema10", "ema10_30"], kanal=[20, 55], hacim_kat=[1.0, 1.5], sikisma=[0.75, 0.9, 99],
              kismi_R=[None, 1.5, 2.0], iz_atr=[3, 4], stop_atr=[1.5, 2.0], cikis_kanal=[10, 20])
df = tara("S2_kirilim", izgara, min_islem=150)
df.to_csv("deneyler/s2_tarama.csv", index=False)
print(df.head(25).to_string(index=False))
