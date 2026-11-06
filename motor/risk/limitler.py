"""Sert risk limitleri.

Değerler kullanıcı onaylı (2026-11-06). Değiştirmek kullanıcı kararıdır.

Bu limitler motor tarafından HER ZAMAN uygulanır. Strateji parametreleri
veya LLM ajanları bunları aşamaz; aşan değer tavana kırpılır.
Birimler yüzde: 1.0 = %1.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SertLimitler:
    islem_basi_max_risk_yuzde: float = 1.0   # bir işlemde özsermayenin en fazla %1'i riske edilir
    gunluk_max_kayip_yuzde: float = 3.0      # UTC günü içinde -%3'e inilirse o gün yeni işlem yok
    max_kaldirac: float = 3.0                # nominal / özsermaye üst sınırı
    kill_switch_dusus_yuzde: float = 20.0    # zirveden -%20 düşüşte tüm işlemler durur


SERT_LIMITLER = SertLimitler()
