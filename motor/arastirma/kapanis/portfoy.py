"""Kapanış turunun portföy (pf__) araştırma hesabı.

Ön kayıt (ON_KAYIT_KAPANIS "Veri ve maliyet"): her strateji kendi 10.000 USDT sanal hesabında, işlem başı başlangıç stop
riski %1,5, zirveden -%30 kalıcı kill, maliyet x1 ve x2 (funding çarpılmaz), dönem sonu <= 2025-11-07 23:59:59 UTC.

Mevcut portföy motoru (`motor/portfoy/motor.py`) DEĞİŞTİRİLMEZ; sert limitler (`SERT_LIMITLER`: işlem %1, portföy toplam
stop riski %5, kill -%20, günlük -%3, kaldıraç 3x) olduğu gibi kalır (motor.py'nin içeriği v2 damgasına girer; dokunmak
v2 çıktılarını bayatlatır). Araştırma limitleri, koşu süresince yalnızca `motor.portfoy.motor.SERT_LIMITLER` modül
adının GEÇİCİ olarak başka bir `SertLimitler` nesnesine bağlanmasıyla uygulanır (`arastirma_limitleri` bağlam yöneticisi;
çıkışta mutlaka geri yüklenir; `motor.risk.limitler.SERT_LIMITLER` nesnesi hiç değişmez; mevcut testler de aynı yolla
motor limitlerini değiştirir). Tek iş parçacığı varsayımı: koşular kilitle sıralanır.

%1,5 işlem riskinin portföye eşlenmesi (LİDER KARARI GEREKİR; burada varsayılan seçenek A uygulanır):
  Portföy (ağırlık) kollarında "işlem başı %1" yoktur; motor tek bir TOPLAM stop riski bütçesi kullanır:
  açık pozisyonların stopa kadar toplam riski <= `portfoy_toplam_risk_yuzde` x özsermaye (sert %5; tek pozisyon da en
  fazla bu kadar). v2 portföy elemesi de bu motoru aynen kullanır (yalnız `limit_modu='olc'`, yani limit olaylarını
  ölçer, durdurmaz). Sert değerler arasındaki oran: portföy toplamı %5 = 5 x işlem başı %1.
  A) (uygulanan) Aynı oran korunur: %1,5 x 5 = %7,5 toplam stop riski (`TOPLAM_RISK_YUZDE`).
  B) Toplam tavan %5 kalır, yalnız kill -%30 olur (işlem riski ağırlık kollarında zaten uygulanmaz).
  C) Tavan %1,5 (tek işlem bütçesi = tüm portföy bütçesi) olur; portföy sınıfları için çok kısıtlayıcı.
  Sinyal kollarında (birlesik) işlem başı risk doğrudan %1,5 olur (`ISLEM_RISK_YUZDE`); pf__ sınıfları ağırlık kolu
  kullandığından bu değer yalnız üst sınır olarak sinyal kollarına etki eder.
Diğer limitler sert değerlerde kalır: günlük -%3 (yeni giriş o gün yok) ve brüt kaldıraç 3x (ön kayıt bunlara değinmez;
bunları değiştirmek lider kararıdır).
Kill burada GERÇEK ve kalıcıdır (`limit_modu='uygula'`): zirveden -%30'da tüm pozisyonlar kapanır, bir daha işlem açılmaz.
Bu yüzden x2 neti kill sonrası düz kalır; x1/x2 kill sayısı `kill_olaylari` listesindedir.

Dönem: `v2.ham.sizinti_kontrol` (HOLDOUT_BAS = 2025-11-08 ve sonrası mum/funding -> `HoldoutSizintisi`, yutulmaz).
Metrikler v2'nin `eleme.portfoy_metrikleri` işleviyle aynı hesaplanır (E1 Sharpe x1 ve net x2, E2 gün/dengeleme, E3 en iyi yıl
çıkarılınca net, kill); kapanış ön kaydının 1-7 kapıları tek grafik ΣR için yazılmıştır, portföye uyarlama lider kararıdır.
"""
from __future__ import annotations

import dataclasses
import math
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma.v2 import eleme, ham as v2_ham, sabit
from motor.portfoy import motor as pmotor
from motor.risk.limitler import SERT_LIMITLER

BASLANGIC_SERMAYE = 10_000.0
ISLEM_RISK_YUZDE = 1.5                 # ön kayıt: işlem başı başlangıç stop riski
KILL_YUZDE = 30.0                      # ön kayıt: zirveden kalıcı kill
TOPLAM_RISK_YUZDE = SERT_LIMITLER.portfoy_toplam_risk_yuzde * ISLEM_RISK_YUZDE / SERT_LIMITLER.islem_basi_max_risk_yuzde  # 7,5
DONEM_SONU = pd.Timestamp("2025-11-07 23:59:59", tz="UTC")

_KILIT = threading.Lock()


@contextmanager
def arastirma_limitleri(islem_risk=ISLEM_RISK_YUZDE, kill=KILL_YUZDE, toplam_risk=TOPLAM_RISK_YUZDE):
    """Portföy motorunun görüş alanında SERT_LIMITLER'i geçici olarak araştırma değerleriyle değiştirir; çıkışta geri yükler."""
    arastirma = dataclasses.replace(SERT_LIMITLER, islem_basi_max_risk_yuzde=islem_risk,
                                    kill_switch_dusus_yuzde=kill, portfoy_toplam_risk_yuzde=toplam_risk)
    with _KILIT:
        eski = pmotor.SERT_LIMITLER
        pmotor.SERT_LIMITLER = arastirma
        try:
            yield arastirma
        finally:
            pmotor.SERT_LIMITLER = eski


@dataclass
class PortfoyHesap:
    """Tek maliyet çarpanında bir portföy koşusunun sonucu."""
    carpan: float
    ozsermaye: pd.Series                 # günlük (UTC gün sonu) MTM özsermaye, USDT
    getiri: pd.Series                    # günlük getiri (TradFi funding düzeltmeli; kripto evrende düzeltme 0)
    islemler: pd.DataFrame
    dengeleme: pd.Series                 # gün -> o gün pozisyon değişti mi (bool)
    kill_olaylari: list                  # limit_olaylari içindeki kill_switch kayıtları
    limit_olaylari: list
    kirpmalar: int
    uyarilar: list
    fonlama_toplam: float
    net_tum: float                       # son özsermaye / başlangıç - 1 (tüm dönem, funding düzeltmesi hariç)


@dataclass
class PortfoyKosu:
    strateji: str
    ayar: dict
    tf: str
    evren: tuple
    disarida: list                       # verisi bulunamayan/boş semboller (açıkça raporlanır)
    veri_bas_sembol: dict
    x1: PortfoyHesap
    x2: PortfoyHesap
    metrikler: dict = field(default_factory=dict)   # v2 portföy ölçütleri (+ sharpe_x2, kill_x2)


def _veri_topla(evren, tf, veri_al):
    v, f, dis = {}, {}, []
    for s in evren:
        try:
            mumlar, fonlama = veri_al(s, tf)
        except (FileNotFoundError, ValueError) as e:
            dis.append(f"{s}: {type(e).__name__}: {e}")
            continue
        if mumlar is None or not len(mumlar):
            dis.append(f"{s}: geliştirme döneminde mum yok")
            continue
        v2_ham.sizinti_kontrol(s, tf, mumlar, fonlama)      # HOLDOUT_BAS ve sonrası -> HoldoutSizintisi
        if pd.Timestamp(mumlar.index.max()) > DONEM_SONU:
            raise v2_ham.HoldoutSizintisi(f"{s}: mum {mumlar.index.max()} > {DONEM_SONU}")
        v[s] = mumlar.drop(columns="eksik") if "eksik" in mumlar.columns else mumlar
        if fonlama is not None and len(fonlama):
            f[s] = fonlama
    if not v:
        raise FileNotFoundError(f"evrende hiç veri yok: {dis}")
    return v, f, dis


def _hesap(st, v, f, evren_t, tf, carpan, tablo_yolu, limitler) -> PortfoyHesap:
    from motor.arastirma import wf_evren_portfoy as wep
    if carpan not in (1.0, 2.0):
        raise ValueError(f"kapanış maliyet çarpanı 1 veya 2 olmalı: {carpan}")
    ay = dataclasses.replace(v2_ham.maliyet_pf(evren_t, carpan, tablo_yolu), limit_modu="uygula",
                             baslangic_sermaye=BASLANGIC_SERMAYE, risk_yuzde=limitler["islem_risk"])
    with arastirma_limitleri(**limitler):
        r = wep._kos(st, v, f, evren_t, ay, 0, tf)
    ozs = r.gunluk_ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last().astype(float)
    getiri = ozs.pct_change().fillna(0.0)
    getiri, fon = v2_ham.pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
    q = r.pozisyon_gecmisi
    degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
    gun = pd.DatetimeIndex(q.index[degisti.to_numpy()]).floor("D") if len(q) else pd.DatetimeIndex([])
    deng = pd.Series([g in set(gun) for g in getiri.index], index=getiri.index)
    kill = [o for o in r.limit_olaylari if o.get("tur") == "kill_switch"]
    return PortfoyHesap(carpan, ozs, getiri, r.islemler, deng, kill, list(r.limit_olaylari), len(r.kirpmalar),
                        list(r.uyarilar), fon, float(ozs.iloc[-1] / BASLANGIC_SERMAYE - 1.0) if len(ozs) else math.nan)


def portfoy_kos(strateji_adi: str, ayar: dict | None, tf: str, evren, veri_al, tablo_yolu: Path,
                islem_risk: float = ISLEM_RISK_YUZDE, kill: float = KILL_YUZDE,
                toplam_risk: float = TOPLAM_RISK_YUZDE) -> PortfoyKosu:
    """Bir pf__ stratejisini x1 ve x2 maliyetle araştırma hesabında oynatır.
    ayar: sınıfın `varsayilan_parametreler` anahtarlarıyla parametre sözlüğü (None/{} = varsayılan).
    veri_al(sembol, tf) -> (mumlar, funding) (tek_grafik ile aynı arayüz). Holdout verisi `HoldoutSizintisi` (açık hata)."""
    from motor.arastirma import wf_portfoy as wp
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    sinif = tum_portfoy_stratejileri().get(strateji_adi)
    if sinif is None:
        raise KeyError(f"bilinmeyen portföy stratejisi: {strateji_adi}")
    ayar = dict(ayar or {})
    evren = tuple(evren)
    v, f, dis = _veri_topla(evren, tf, veri_al)
    evren_t = tuple(v)
    st = sinif(**ayar)
    etkin = st.etkin_semboller(evren_t)
    st = st.yeni(semboller=etkin) if etkin else st
    if not st.uygun_mu(evren_t):
        raise RuntimeError(f"{strateji_adi}: bu evrende uygun değil (yeterli sembol/çift yok)")
    lim = {"islem_risk": islem_risk, "kill": kill, "toplam_risk": toplam_risk}
    h1 = _hesap(st, v, f, evren_t, tf, 1.0, tablo_yolu, lim)
    h2 = _hesap(st, v, f, evren_t, tf, 2.0, tablo_yolu, lim)
    vb = {s: str(v[s].index[0]) for s in v}
    g = lambda h: pd.DataFrame({"gun": pd.DatetimeIndex(h.getiri.index).as_unit("ns"), "getiri": h.getiri.to_numpy(dtype=float),
                                "dengeleme": h.dengeleme.to_numpy(dtype=bool)})
    m = eleme.portfoy_metrikleri(g(h1), {"veri_bas_sembol": vb, "kill_olayi": len(h1.kill_olaylari)}, g(h2))
    analiz = pd.Timestamp(m["analiz_bas"])
    r2 = h2.getiri[pd.DatetimeIndex(h2.getiri.index) >= analiz].to_numpy(dtype=float)
    m.update(sharpe_x2=wp.sharpe_gunluk(r2) if len(r2) else math.nan, kill_x2=len(h2.kill_olaylari),
             net_en_iyi_yil_haric_x2=eleme._yil_haric_net(h2.getiri[pd.DatetimeIndex(h2.getiri.index) >= analiz]))
    return PortfoyKosu(strateji_adi, ayar, tf, evren_t, dis, vb, h1, h2, m)
