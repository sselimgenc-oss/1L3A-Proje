"""scalp__bas-omuz — baş-omuz / ters baş-omuz boyun çizgisi kırılımı (15m).

Çekirdek swing `BasOmuz` (swing/bas_omuz.py; formasyon_b3.bas_omuz_cekirdek) ile aynıdır, ondan türer; yalnız
varsayılanlar 15m'ye göre: sag_omuz_filtre=1 (Scheier kartı bu stilin kaynağı), min_yuk_atr=3.0 (formasyon
yüksekliği maliyeti karşılamalı), gecerlilik=30 mum. Kural/stop/hedef için bkz. swing/bas_omuz.py.
Kaynak kartlar: gun-ici-bas-omuz-ust-kisa__bulkowski, gun-ici-bas-omuz-dip-uzun__bulkowski,
  bas-omuz-sag-omuz-filtre__scheier (+ aile kartları).
Varsayımlar: kartlar 1m/5m; min zaman dilimi kararı gereği 15m'ye taşındı (zigzag ATR eşiğiyle ölçeklenir).
  Kartlardaki "1 kuruş/tik" tamponları ATR tamponuna çevrildi; "hedefte veya kapanışta kapat" gün sonu kuralı
  scalp'ta uygulanmadı (scalp çıkışı hedef/stop/iz süren stop).
Negatif kanıt: Bulkowski sayıları günlük hisse; gün içi istatistik yok (kartlar: "Gün içi istatistik yok").
  arsiv/OZET.md §3: kısa TF + maliyet kombinasyonu başarısız (1S/5dk denemeleri PF<1) — komisyon baskın.
"""
from motor.strateji.swing.bas_omuz import BasOmuz as _Swing


class BasOmuz(_Swing):
    ad = "scalp__bas-omuz"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "sag_omuz_filtre": 1, "min_yuk_atr": 3.0, "gecerlilik": 30}
    parametre_izgarasi = {
        "sim_tol": [0.25, 0.4, 0.6],
        "hedef_olcu": [0.75, 1.0, 1.5],
        "zigzag_esik_k": [1.5, 2.0, 3.0],
    }
