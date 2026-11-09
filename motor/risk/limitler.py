"""Sert risk limitleri.

Değerler kullanıcı onaylı (2026-11-06). Değiştirmek kullanıcı kararıdır.

Bu limitler motor tarafından HER ZAMAN uygulanır. Strateji parametreleri
veya LLM ajanları bunları aşamaz; aşan değer tavana kırpılır.
Birimler yüzde: 1.0 = %1.

İŞLEM BAŞI RİSKİN TANIMI (kullanıcı kararı 2026-11-09; denetim O7/Ö8): "işlem başı %1" MALİYET DAHİL ölçülür.
Stop'ta toplam kayıp = fiyat riski |giriş−stop| + stop kayması + giriş ve çıkış komisyonu; bu toplam özsermayenin
`islem_basi_max_risk_yuzde`'sini aşmayacak şekilde miktar hesaplanır (bkz. `maliyetli_risk_birim`):
    miktar = nakit·risk_oran / (|giriş−stop| + max(giriş, stop)·(stop_kayma + 2·taker))
`max(giriş, stop)`: çıkış tarafı maliyeti stop fiyatı üzerinden işler; short'ta stop > giriş olduğundan giriş fiyatı az
sayardı (tutucu seçim; long'da = giriş). Sınır değerleri (aşağıdaki sabitler) DEĞİŞMEDİ, yalnız risk tanımı genişledi.
Kapsam dışı (bilinçli): gap'li stop dolumu (stop ötesinde açılış) ve funding bu sınırı aşabilir; portföy toplam stop riski
(%5) fiyat riski olarak ölçülmeye devam eder. Uygulandığı yerler (hepsi bu fonksiyonu kullanır):
  - motor/backtest/motor.py (giriş boyutu)
  - motor/portfoy/motor.py `_Motor._istenen_qty` sinyal kolları (sembol bazlı maliyet: PortfoyAyarlari.maliyet_sembol)
  - motor/canli/paper_motor.py `PaperMotor._istenen_qty` sinyal kolları
  - motor/arastirma/secim.py `yeniden_oyna` (ham r ile tek kasa oynatma; işlem fiyat riski = kasa·risk·sf/(sf+maliyet_payi))
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SertLimitler:
    islem_basi_max_risk_yuzde: float = 1.0   # bir işlemde özsermayenin en fazla %1'i riske edilir
    gunluk_max_kayip_yuzde: float = 3.0      # UTC günü içinde -%3'e inilirse o gün yeni işlem yok
    max_kaldirac: float = 3.0                # nominal / özsermaye üst sınırı
    kill_switch_dusus_yuzde: float = 20.0    # zirveden -%20 düşüşte tüm işlemler durur
    # Kullanıcı onaylı 2026-11-07, karar 25: hedef-ağırlık (portföy) stratejilerinde pozisyon başına %1 yerine
    # tüm açık pozisyonların stopa kadar TOPLAM riski <= %5 (tek pozisyon da en fazla %5). Tek-grafik (sinyal)
    # stratejilerinde işlem başı %1 aynen kalır.
    portfoy_toplam_risk_yuzde: float = 5.0


SERT_LIMITLER = SertLimitler()


def maliyetli_risk_birim(giris, stop, stop_kayma_oran, taker_oran):
    """Birim başına stop'taki toplam kayıp (maliyet dahil işlem başı risk tanımı; modül belgesi).
    Decimal ya da float ile çalışır. Oranlar kesir (0.0005 = %0.05)."""
    return abs(giris - stop) + max(giris, stop) * (stop_kayma_oran + 2 * taker_oran)
