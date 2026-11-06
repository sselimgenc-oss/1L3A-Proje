"""Nihai strateji tanımları ve enstrüman ayarları."""

# ---- Strateji 1: SAKK — Seans Açılış Kutusu Kırılımı (5 dakika, scalp) ----
SAKK_ORTAK = dict(tampon=0.2, stop_kutu=1.0, rr=1.5, gecerli=1.0, kutu_max=0.35, stop_min_atr=0.5,
                  htf_ema=1, htf="1h", htf_f=21, htf_s=50)
# kutu = enstrümanın ana seansının ilk saati (7/24 piyasalarda Asya seansı); saatler yerel saattir
SAKK_KUTU = {
    "SPX":     dict(tz="America/New_York", kutu_bas=9.5, kutu_bit=10.5, kapat=15.9),    # NYSE açılışı
    "UKOIL":   dict(tz="America/New_York", kutu_bas=9.0, kutu_bit=10.0, kapat=14.5),    # NYMEX petrol açılışı
    "XAUUSD":  dict(tz="America/New_York", kutu_bas=8.33, kutu_bit=9.33, kapat=16.0),   # COMEX altın açılışı
    "BTCUSDT": dict(tz="UTC", kutu_bas=0.0, kutu_bit=8.0, kapat=23.0),                  # Asya seansı kutusu
    "XU030":   dict(tz="Europe/Istanbul", kutu_bas=10.0, kutu_bit=11.0, kapat=17.9),    # BIST/VİOP açılışı
}

# ---- Strateji 2: GPK — Günlük Pivot/CPR Kırılımı (1 saat, day trade) ----
GPK_ORTAK = dict(seviye="r1s1", dar_mod="cpr", dar=0.25, stop_mod="seviye", stop_atr=1.5, stop_min_atr=0.75,
                 stop_max_atr=3.0, rr=2.0, htf_ema=1, htf="1D", htf_f=10, htf_s=20, yon=0)
# v3 (Faz 6): kripto girişinde ek olarak günlük kapanış > EMA20 (Brooks "always-in long"); kripto_final.GIRIS ekler
# gün tanımı (gun_bas: yerel saatte gün başlangıcı) ve işlem penceresi (gün başından itibaren saat)
GPK_GUN = {
    "BTCUSDT": dict(tz="UTC", gun_bas=0.0, bas=0, bit=20, kapat=23),
    "XAUUSD":  dict(tz="America/New_York", gun_bas=18.0, bas=8, bit=20, kapat=22),   # 02:00-14:00 ET
    "UKOIL":   dict(tz="America/New_York", gun_bas=18.0, bas=8, bit=20, kapat=22),
    "SPX":     dict(tz="America/New_York", gun_bas=18.0, bas=15, bit=21, kapat=21.5), # 09:00-15:00 ET
    "XU030":   dict(tz="Europe/Istanbul", gun_bas=0.0, bas=10, bit=17, kapat=17.9),
}
