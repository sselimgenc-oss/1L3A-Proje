import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
izgara = dict(rsi_esik=[50, 55], momentum_n=[0, 63], momentum_min=[0.0, 0.1], kismi_R=[None, 1.0, 1.5],
              stop_atr=[1, 2], iz_atr=[None, 3], max_gun=[10, 20], hacim_azalan=[False, True])
df = tara("S1_geri_cekilme", izgara, sabit=dict(yon_mod="ema10_30"), min_islem=150)
df.to_csv("deneyler/s1_tarama2.csv", index=False)
print(df.head(25).to_string(index=False))
