import pandas as pd
from swing.ayarlar import S1, S2, SINIFLAR
from swing.optimize import tara
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
d2 = tara("S2_kirilim", dict(kismi_R=[1.0, 1.5, 2.0], sikisma=[0.8, 0.9, 1.0], hacim_kat=[1.0, 1.2],
                             kanal=[20, 30], iz_atr=[3, 4]), sabit=S2, siniflar=SINIFLAR["S2_kirilim"], min_islem=100)
d2.to_csv("deneyler/ince_s2.csv", index=False)
print(d2[(d2.IS_WR >= .45) & (d2.OOS_WR >= .45)].sort_values("OOS_R", ascending=False).head(12).to_string(index=False))
d1 = tara("S1_geri_cekilme", dict(rejim=[None, "ha", "sma200"], kismi_R=[0.75, 1.0], rsi_esik=[55, 60, 65],
                                  iz_atr=[3, 4, None]), sabit=S1, siniflar=SINIFLAR["S1_geri_cekilme"], min_islem=100)
d1.to_csv("deneyler/ince_s1.csv", index=False)
print(d1.sort_values("IS_DD", ascending=False).head(12).to_string(index=False))
print(d1.head(12).to_string(index=False))
