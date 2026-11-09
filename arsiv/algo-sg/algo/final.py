"""Nihai sistem tanımı (STRATEJILER.md ile birebir).

İki bağımsız strateji:
  A  Trend (kırılım) — iki giriş modülü ortak risk bütçesini ve coin başına tek pozisyonu paylaşır
     A1: 4H Donchian(20) + hacim kırılımı
     A2: Günlük Donchian(20) "Turtle" kırılımı (denetimde ayrı strateji olmaktan çıkarıldı: işlemlerinin
         %95'i A1 ile aynı coin/yön/zamanda çakışıyordu, korelasyon 0.77)
  B  Kapitülasyon dönüşü (coin 24 saatte >= %15 düştüğünde long)
"""
import numpy as np

A1 = dict(h4_dc=True, h4_dc_n=20, vol_min=1.5, trigger="now", d1_trend=False, long_only=False, long_btc=200,
          sl_h4atr=2.0, tp1_R=1.0, tp1_frac=0.25, be_R=1.0, trail_h4=True, trail_k=10.0, trail_start_R=0.0,
          exit_h4ema=100, max_bars=720,
          entry_ema_side=True)  # denetim: çıkış koşulu girişte zaten doğruysa işlem açma

A2 = dict(d1_dc=True, d1_dc_n=20, trigger="now", d1_trend=False, long_only=False, long_btc=200,
          sl_h4atr=4.0, tp1_R=1.0, tp1_frac=0.25, be_R=1.0, trail_h4=True, trail_k=15.0, trail_start_R=0.0,
          exit_h4ema=200, max_bars=720, entry_ema_side=True)

# Denetim: kırılgan BTC filtresi ve 6 saatlik pencere kaldırıldı; eşik basit % (raporla birebir)
B = dict(drop24=0.15, bias_win=1, trigger="none", exit=None, tp_R=np.inf, sl_h4atr=4.0, be_R=1.0, max_bars=96)

MODULES = {"A1": ("s5", A1), "A2": ("s5", A2), "B": ("s4", B)}
SLEEVES = {"A": dict(modules=["A1", "A2"], risk=0.005, max_open=10),
           "B": dict(modules=["B"], risk=0.0075, max_open=25)}

# geriye dönük uyumluluk
STRATEGIES = {k: v for k, v in MODULES.items()}
SLEEVE = {"A1": dict(risk=0.005, max_open=10), "A2": dict(risk=0.005, max_open=10), "B": dict(risk=0.0075, max_open=25)}
