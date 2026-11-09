import pandas as pd
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
izgara = dict(osc=["rsi2", "bb"], esik=[10], yon_mod=["ema10_30", "ha"], trend_sma=[100, 200],
              stop_atr=[1.5, 2.0, 3.0], limit_atr=[0.5, 1.0], max_gun=[10], cikis_sma=[10],
              cikis_mod=["sma", "yuksek"], cikis_rsi=[70, 90])
df = tara("S3_asiri_satim", izgara, min_islem=150)
df.to_csv("deneyler/s3_tarama2.csv", index=False)
print(df.sort_values("OOS_CAGR", ascending=False).head(12).to_string(index=False))
print(df.head(15).to_string(index=False))
