"""Paper motoru -> yürütücü köprüsü. Paper motorunu DEĞİŞTİRMEZ; yalnız durumunu OKUR (aynı sinyal yolu).

Her paper turundan sonra (tur kancası) bir stratejinin hesabındaki `PaperMotor` şu bilgiyi verir:
  - bekleyen giriş (`kol.giris_emri`; paper bunu bir sonraki satırda doldurur): "ac" niyeti (stop/hedef dahil) -> canlıda şimdi piyasa emri
  - bekleyen çıkış (`kol.cikis_emri`: sinyal, zaman, kill_switch, gunluk_limit): "kapat" niyeti -> canlıda şimdi piyasa kapatma
  - açık pozisyonun güncel stopu (iz süren/başabaş): stop yükseltme
Desteklenmeyen (fail-closed): ağırlık (portföy) kolu ve kısmi çıkış. Canlıda sessizce yok sayılmaz, kurulumda açık hata.
"""
from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd

from motor.canli.borsa.canli_yurutucu import MotorGorunumu, Niyet, PozGorunum

D = Decimal


class CanliDesteklemiyorHatasi(ValueError):
    pass


def uygunluk_kontrol(motor, birimler: list) -> None:
    """Canlıda taklit edilemeyen kollar = açık hata (paper'da çalışıp canlıda sessizce farklı davranmasın)."""
    sorun = []
    for b in birimler:
        for k in b.kollar:
            if k.mod != "sinyal":
                sorun.append(f"{k.kimlik}: ağırlık (portföy) kolu canlıda henüz desteklenmiyor (yeniden boyutlandırma/ekleme/küçültme taklit edilmiyor)")
            elif k.cikis_ayarlari.kismi:
                sorun.append(f"{k.kimlik}: kısmi çıkış canlıda desteklenmiyor")
    if sorun:
        raise CanliDesteklemiyorHatasi("; ".join(sorun))


def gorunum(motor, birimler: list, son_mum=None) -> MotorGorunumu:
    """`son_mum(sembol, tf, t)` (canlıda `kaynak.gecmis(...).index[-1]`): sembolün t'ye kadarki SON mumunun açılış zamanı. Paper kararı yalnız
    sembolün mumu olan satırlarda yenilenir; mumsuz satırda `giris_emri` eski kalır. Sinyal zamanı = sinyalin üretildiği GERÇEK bar
    (b.son_t DEĞİL): eski sinyal her satırda 'yeni' görünüp stop sonrası yeniden girişe yol açmasın; 900 sn bayatlık bu zamana göre işler."""
    g = MotorGorunumu()
    engel = motor.kill or motor.gunluk_blok
    for b in birimler:
        for k in b.kollar:
            g.kollar[k.kimlik] = k.sembol
            if b.son_t is not None:
                g.son_satir[k.kimlik] = b.son_t
            g.aralik[k.kimlik] = b.aralik
            p = motor.acik.get(k.kimlik)
            if p is not None:
                g.pozlar[k.kimlik] = PozGorunum(p.sembol, int(p.yon), D(p.stop), D(p.hedef) if p.hedef is not None else None)
                if k.cikis_emri:
                    g.niyetler.append(Niyet("kapat", k.kimlik, k.sembol, p.yon, neden=str(k.cikis_emri), aralik=b.aralik))
                continue
            if k.giris_emri is None or engel or b.son_t is None:
                continue
            yon, stop, hedef, _zc = k.giris_emri
            if stop is None or (isinstance(stop, float) and np.isnan(stop)):
                continue
            s = k.sembol
            sz = pd.Timestamp(b.son_t)
            if son_mum is not None:
                m = son_mum(s, b.tf, b.son_t)
                if m is not None:
                    sz = min(sz, pd.Timestamp(m))
            g.niyetler.append(Niyet(
                "ac", k.kimlik, s, int(yon), stop=D(repr(float(stop))), hedef=(D(repr(float(hedef))) if hedef is not None and not np.isnan(hedef) else None),
                sinyal_zamani=sz, aralik=b.aralik, sabit_r=(k.cikis_ayarlari.sabit_r_hedefi or None), risk_oran=D(motor.risk_oran), grup_payi=D(k.grup_payi),
                stop_kayma=D(motor._sk(s)), taker=D(motor._tk(s))))
    return g
