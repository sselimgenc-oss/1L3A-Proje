"""Haftalık yön + günlük işlem (1W/1D) nihai strateji tanımları (STRATEJILER_GUNLUK.md ile birebir)."""

# D1 — Elder haftalık yön + Halsey %50 geri çekilme (long/short), Turtle 10 gün çıkışı
D1 = dict(trigger="half", wdir="elder", leg_n=20, sl_atr=3.0, atr="atr20",
          tp1_R=0.6, tp1_frac=0.33, be_R=0.6, exit="dc", exit_dc=10, max_bars=90)

# D2 — Elder haftalık "kırmızı değil" + günlük kapitülasyon dönüşü (yalnız long), Connors SMA5 çıkışı
D2 = dict(trigger="capit", wdir="elder", cap_k=2, cap_drop=0.20, cap_ctx="not_down", long_only=True,
          sl_atr=3.0, atr="atr20", exit="sma5", max_bars=15)

STRATEGIES = {"D1": D1, "D2": D2}
SLEEVES = {"D1": dict(risk=0.01, max_open=10), "D2": dict(risk=0.01, max_open=10)}
