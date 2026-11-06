"""Seçilmiş strateji parametreleri (örneklem-içi 2015-2022 taramasından seçildi, 2023+ ile doğrulandı)."""

S1 = dict(yon_mod="ha", hizli=10, yavas=50, rsi_esik=65, bakis=3, kismi_R=1.0, stop_atr=1.0, iz_atr=None,
          max_gun=30, rejim="ha")
S2 = dict(yon_mod="ema10_30", kanal=20, hacim_kat=1.0, sikisma=0.9, sikisma_bakis=5, kapanis_konum=0.6,
          kismi_R=1.5, iz_atr=4, stop_atr=2.0, cikis_kanal=20, max_gun=30, rejim="ema10")
S3 = dict(osc="rsi2", esik=10, yon_mod="ha", trend_sma=200, stop_atr=2.0, limit_atr=0.5, max_gun=10,
          cikis_sma=10, cikis_rsi=70, cikis_mod="sma", rejim="ema10_30")

SECILI = {"S1_geri_cekilme": S1, "S2_kirilim": S2, "S3_asiri_satim": S3}

# Strateji–varlık sınıfı eşlemesi. BIST (USD bazında) S1 ve S3'te hem IS hem OOS'ta negatif beklenti
# verdiği için yalnızca S2 ile işlenir; emtia S3'te IS döneminde negatif olduğu için S3 dışında tutulur.
SINIFLAR = {
    "S1_geri_cekilme": ["kripto", "mag7", "emtia"],
    "S2_kirilim": ["kripto", "mag7", "bist", "emtia"],
    "S3_asiri_satim": ["kripto", "mag7"],
}

# Portföy kuralları
RISK = 0.01          # işlem başına özsermaye riski
MAX_POZ = 10         # aynı anda en fazla pozisyon
MAX_AGIRLIK = 0.20   # tek pozisyon üst sınırı
