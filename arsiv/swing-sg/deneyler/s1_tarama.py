import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
izgara = dict(yon_mod=["ema10", "ema10_30", "macd"], rsi_esik=[40, 50], temas_atr=[0.3, 0.75],
              hedef_R=[None, 2, 3], iz_atr=[None, 2.5, 4], basabas_R=[None, 1], stop_atr=[1, 2])
df = tara("S1_geri_cekilme", izgara)
df.to_csv("deneyler/s1_tarama.csv", index=False)
print(df.head(25).to_string(index=False))
print("WR>=45 olan konfig sayısı:", (df.IS_WR >= .45).sum(), "/", len(df))
