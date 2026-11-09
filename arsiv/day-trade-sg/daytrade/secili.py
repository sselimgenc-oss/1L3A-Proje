"""Kullanıcı onayına sunulan seçili kripto stratejileri (bkz. docs/kripto_sonuc2.md).

Hepsi yalnızca alış, 15dk giriş, 4s/1s yön, gün sonunda (UTC 24:00) çıkış, BTC 4s trend filtresi.
Her strateji ayrı alt hesapta çalışır (sermaye ve pozisyon hakkı eşit bölünür).
"""

SECILI = {
    "S13_falsebreak": dict(trend="po_h1", adx_min=25, n_high=80, n_pull=12, k_bars=12,
                           stop_atr_d=1.0, btc_filter=True, yon="long"),
    "S15_tdpullback": dict(level="ema20", move_atr=1.0, from_utc=14, to_utc=21, stop="atr",
                           stop_atr_d=0.75, touch_atr=0.2, btc_filter=True, yon="long"),
    "S10_trendday": dict(at_utc=16, at_end=20, move_atr=1.0, stop_mode="atr", stop_atr_d=1.0,
                         trend="h4+h1", btc_filter=True, yon="long"),
}
PORTFOY = dict(sermaye=10000, risk=0.005, max_pozisyon=9, max_agirlik=0.3,
               max_toplam_agirlik=1.0, gunluk_zarar_limiti=-0.03, ayri_hesap=True)
