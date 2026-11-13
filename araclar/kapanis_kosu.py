"""Kapanış turu AŞAMA 1 koşucusu (ON_KAYIT_KAPANIS + ekler 1-4). Dondurulmuş listeyi (kosu_listesi_asama1.csv) koşar.

Kullanım:
  python araclar/kapanis_kosu.py --kuru                 # yalnız liste/sınıf/TF/veri dosyası çözümlemesi (backtest YOK, mum okunmaz)
  python araclar/kapanis_kosu.py --sinir 3 --isci 2     # ilk 3 kimlik (deneme)
  python araclar/kapanis_kosu.py --isci 4               # tüm liste; biten kimlikler atlanır (kontrol noktası)
  python araclar/kapanis_kosu.py --birlestir            # JSON'ları topla + kapı 7 (BH) + ikinci kapı + özet

Tek grafik kimliği: evrendeki her sembol x maliyet x1/x2 `tek_ham_kos`, sonra `kendi_hesabi_oynat` (risk %1,5, kill -%30).
Kapılar (ana karar x2): K1 net>0 ve PF(R)>=1,2; K2 kabul>=200; K3 en iyi sembol ve en iyi yıl çıkarılınca ΣR>0; K4 kill yok;
K5 long-only ise eşit ağırlıklı al-tut Sharpe'ını (x2 maliyet, aynı kapsam) aşar; K6 rastgele giriş (v2 `test.k2_simule`, B=100.000,
tohum 20261113+crc32(kimlik), takvim çeyreği, genişletilmiş evren_k2) p<=0,05; desteklenmeyen çıkış -> HATA, p=1; K7 BH q=0,10.
Portföy (pf__) kimlikleri ek 2'deki portföy kapılarıyla (portfoy.py). Dönem <= 2025-11-07; holdout okunmaz (HoldoutSizintisi asla yutulmaz).
Bir kimlikte hata: JSON'a durum=HATA + mesaj, diğerleri sürer (HoldoutSizintisi hariç: tüm koşu durur).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
import shutil
import sys
import time
import traceback
import zlib
from dataclasses import dataclass, field
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from araclar import kapanis_kosu_listesi as kl  # noqa: E402
from motor.arastirma import evren_k2, evren_maliyet  # noqa: E402
from motor.arastirma import wf_evren as we  # noqa: E402
from motor.arastirma import wf_portfoy as wp  # noqa: E402
from motor.arastirma.kapanis import portfoy as kpf  # noqa: E402
from motor.arastirma.kapanis.tek_grafik import kendi_hesabi_oynat, tek_ham_kos  # noqa: E402
from motor.arastirma.v2 import eleme as v2_eleme  # noqa: E402
from motor.arastirma.v2 import ham as hm  # noqa: E402
from motor.arastirma.v2 import sabit  # noqa: E402
from motor.arastirma.v2 import test as v2_test  # noqa: E402
from motor.strateji import funding  # noqa: E402
from motor.veri import depo  # noqa: E402

KAPANIS = KOK / "sonuclar" / "kapanis"
LISTE = KAPANIS / "kosu_listesi_asama1.csv"
CIKTI = KAPANIS / "kosu_asama1"
SONUC_CSV = KAPANIS / "sonuc_asama1.csv"
OZET_MD = KAPANIS / "ozet_asama1.md"
TABLO = KOK / "sonuclar" / "evren" / "v2" / "maliyet_tablosu_v2.csv"
YENI_DIZIN = KOK / "sonuclar" / "evren" / "yeni_sembol"
TABLO_40 = YENI_DIZIN / "maliyet_tablosu_yeni_sembol.csv"
SEMBOLLER_40 = YENI_DIZIN / "semboller.csv"

# ---- ön kayıtlı sabitler (ON_KAYIT_KAPANIS + ekler)
ESIK = {"min_islem": 200, "pf_min": 1.2, "p_esik": 0.05, "b": 100_000, "tohum": 20261113, "bh_q": 0.10,
        "pf_sharpe_min": 0.5, "pf_min_gun": 1095, "pf_min_dengeleme": 20}
DESTEKLENEN_SAKIN_TF = ("1w", "1M")        # motor aralik_suresi/gunluk_kapanis bu TF'leri tanımaz -> VERI_TF_YOK


@dataclass
class Baglam:
    tablo: Path = TABLO
    tablo_40: Path = TABLO_40
    veri_al: object = None            # (sembol, tf) -> (mumlar, funding); None: v2 `veri_oku` (geliştirme dönemi, holdout hariç)
    veri_al_40: object = None
    kurallar_40: dict = field(default_factory=dict)
    sembol_40: tuple = ()
    cikti: Path = CIKTI
    esik: dict = field(default_factory=lambda: dict(ESIK))
    k6_on_eleme_tf: tuple = ()        # ön kayıt eki 9: bu TF'lerde kapı 6 yalnız kapı 1–5'i geçenlere koşulur (geçmeyen p=1)


_CTX: Baglam | None = None


def baglam() -> Baglam:
    if _CTX is None:
        raise RuntimeError("bağlam kurulmadı (baglam_kur)")
    return _CTX


def baglam_kur(**kw) -> Baglam:
    global _CTX
    b = Baglam(**kw)
    if b.veri_al is None:
        we.veri_ayarla(None, sabit.DONEM)
        b.veri_al = hm.veri_oku
    if b.veri_al_40 is None:
        b.veri_al_40 = _veri_al_40
    if not b.sembol_40 and SEMBOLLER_40.exists():
        b.sembol_40, b.kurallar_40 = _semboller_40()
    _CTX = b
    return b


# ---------------------------------------------------------------- yardımcılar
def guvenli(kimlik: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9._#=-]", "_", kimlik)


def temiz(o):
    """JSON için: numpy -> yerel, NaN/inf -> None, Timestamp -> str."""
    if isinstance(o, dict):
        return {str(k): temiz(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [temiz(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return o


def atomik_yaz(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".tmp")
    gecici.write_text(json.dumps(temiz(veri), ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    gecici.replace(yol)


def liste_oku(yol: Path = LISTE) -> list:
    with open(yol, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tf_cozum(tf: str) -> tuple:
    """-> (tamam_mi, aciklama). 5m'nin katı tüm TF'ler motor `yeniden_ornekle` ile 5m'den kapanmış mumlarla üretilir (2h,3h,6h,8h...)."""
    if tf in DESTEKLENEN_SAKIN_TF:
        return False, f"VERI_TF_YOK: {tf} motorda yok (aralik_suresi/gunluk_kapanis m/h/d bilir)"
    try:
        sure = depo.aralik_suresi(tf)
    except ValueError as e:
        return False, f"VERI_TF_YOK: {e}"
    if sure < pd.Timedelta(5, "min") or sure % pd.Timedelta(5, "min") != pd.Timedelta(0):
        return False, f"VERI_TF_YOK: {tf} 5m'den üretilemez"
    return True, "5m" if sure == pd.Timedelta(5, "min") else f"5m -> {tf} yeniden örnekleme (yeniden_ornekle, eksik mumlar atılır)"


def _semboller_40() -> tuple:
    from motor.backtest.motor import SembolKurallari
    d = pd.read_csv(SEMBOLLER_40)
    kurallar = {r.sembol: SembolKurallari(tick_size=float(r.tick), step_size=float(r.step), min_qty=float(r.step), min_notional=5.0)
                for r in d.itertuples()}
    return tuple(d["sembol"]), kurallar


def _veri_al_40(sembol: str, tf: str):
    """İkinci kapı verisi: geliştirme dönemi (holdout okunmaz); delist sonrası sıfır hacimli düz mumlar son gerçek işlemde kesilir."""
    mumlar, fund = hm.veri_oku(sembol, tf)
    gercek = mumlar.index[(mumlar["quote_hacim"] > 0).to_numpy()] if len(mumlar) else mumlar.index
    if not len(gercek):
        raise FileNotFoundError(f"{sembol} {tf}: geliştirme döneminde hacimli mum yok")
    son = gercek.max()
    return mumlar[mumlar.index <= son], (fund[fund.index <= son] if fund is not None else None)


# ---------------------------------------------------------------- saf kapı işlevleri (testli)
def _gec(v, ok) -> bool:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return False
    try:
        return bool(ok(v))
    except TypeError:
        return False


def kalan_toplam(d: dict) -> float:
    """En yüksek toplamlı anahtar çıkarılınca kalan toplam (boş/NaN -> NaN; tek anahtar -> 0)."""
    return v2_eleme._kalan_toplam(d)


def kapilar_tek(m2: dict, sharpe2: float, bh_sharpe2: float, long_only: bool, esik: dict) -> dict:
    """Kapı 1-5 (ana karar x2). m2: kendi_hesabi_oynat(x2) metrikleri."""
    k = {}
    k["k1"] = _gec(m2.get("net_getiri"), lambda v: v > 0) and _gec(m2.get("profit_factor"), lambda v: v >= esik["pf_min"])
    k["k2"] = _gec(m2.get("islem_sayisi"), lambda v: v >= esik["min_islem"])
    k["k3a"] = _gec(kalan_toplam(m2.get("r_enstruman") or {}), lambda v: v > 0)
    k["k3b"] = _gec(kalan_toplam(m2.get("r_yil") or {}), lambda v: v > 0)
    k["k3"] = k["k3a"] and k["k3b"]
    k["k4"] = _gec(m2.get("kill_olayi"), lambda v: v == 0)
    k["k5"] = True if not long_only else (_gec(sharpe2, lambda v: True) and _gec(bh_sharpe2, lambda v: True) and sharpe2 > bh_sharpe2)
    return k


def kapilar_portfoy(m: dict, bh_sharpe2: float, long_only: bool, esik: dict) -> dict:
    """Portföy kapıları (ek 2): K1 net x2>0 ve Sharpe x2>=0,5; K2 dönem>=1095 gün ve >=20 yeniden dengeleme; K3 en iyi yıl çıkarılınca
    net x2>0 (sembol çıkarma tanımsız); K4 kill x2 yok; K5 long-only ise al-tut Sharpe'ını aşar."""
    k = {}
    k["k1"] = _gec(m.get("net_x2"), lambda v: v > 0) and _gec(m.get("sharpe_x2"), lambda v: v >= esik["pf_sharpe_min"])
    k["k2"] = _gec(m.get("gun"), lambda v: v >= esik["pf_min_gun"]) and _gec(m.get("dengeleme"), lambda v: v >= esik["pf_min_dengeleme"])
    k["k3a"] = True
    k["k3b"] = _gec(m.get("net_en_iyi_yil_haric_x2"), lambda v: v > 0)
    k["k3"] = k["k3b"]
    k["k4"] = _gec(m.get("kill_x2"), lambda v: v == 0)
    sh = m.get("sharpe_x2")
    k["k5"] = True if not long_only else (_gec(sh, lambda v: True) and _gec(bh_sharpe2, lambda v: True) and sh > bh_sharpe2)
    return k


def bh_net_getiri(veriler: dict, evren, bas, bit, carpan: float, tablo: Path) -> pd.Series:
    """Eşit ağırlıklı al-tut günlük getirisi (wf_portfoy.al_tut_getirisi) - x`carpan` gidiş-dönüş maliyeti (komisyon + kayma, sembol
    ortalaması; ilk günden giriş, son günden çıkış tarafı düşülür). Aynı tarih kapsamı: [bas, bit)."""
    g = wp.al_tut_getirisi(veriler, evren, pd.Timestamp(bas), pd.Timestamp(bit)).dropna()
    if len(g) < 2:
        return g
    yan = np.mean([evren_maliyet.sembol_maliyeti(s, carpan, tablo)[0] / 100.0 + evren_maliyet.sembol_maliyeti(s, carpan, tablo)[2] / 1e4
                   for s in evren if s in veriler])
    g = g.copy()
    g.iloc[0] -= yan
    g.iloc[-1] -= yan
    return g


def sharpe_x(getiri) -> float:
    return wp.sharpe_gunluk(np.asarray(getiri, dtype=float))


# ---------------------------------------------------------------- tek grafik koşusu
def _kur(satir: dict):
    par = json.loads(satir["parametreler"])
    st, pf = kl.strateji_kur(satir["sinif"], satir["modul"], par)
    return st, pf, par


def rastgele_giris_p(satir: dict, ham2: dict, analiz_bas, mumlar_s: dict, b: Baglam, tf: str, evren: tuple) -> dict:
    """Kapı 6: v2 `test.k2_simule` (rastgele giriş, takvim çeyreği, stratejinin çıkış kuralları + genişletilmiş evren_k2). x2 maliyet.
    -> {'p','T','n_islem','B','tohum','gecersiz_oran','desteklenmeyen'}. Desteklenmeyen çıkış: p=1, desteklenmeyen dolu (HATA)."""
    st0, _, _ = _kur(satir)
    destek_yok = evren_k2.desteklenmeyen(st0.cikis_ayarlari)
    if destek_yok:
        return {"p": 1.0, "desteklenmeyen": sorted(destek_yok)}
    gercek = v2_test.cakisma_suz(ham2, analiz_bas)
    if not gercek:
        return {"p": 1.0, "T": 0.0, "n_islem": 0, "desteklenmeyen": []}
    T = v2_test.toplam_r(gercek)
    B = int(b.esik["b"])
    tohum = int(b.esik["tohum"]) + zlib.crc32(satir["kimlik"].encode())

    def veri_al_k2(sembol):
        mumlar = mumlar_s[sembol]
        kural = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
        return mumlar, evren_maliyet.maliyet_ayarlari(sembol, kural, 2.0, b.tablo)

    def cikis_al(sembol):
        st, _, _ = _kur(satir)                       # sembol başına taze örnek (kanca dizileri sembole özgü)
        mumlar, fund = b.veri_al(sembol, tf)
        return evren_k2.cikis_bilgisi(st, funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf))

    kismi = b.cikti / "_kismi" / guvenli(satir["kimlik"])
    r = v2_test.k2_simule(gercek, veri_al_k2, cikis_al, B, tohum, kismi_dizin=kismi)
    shutil.rmtree(kismi, ignore_errors=True)
    s = r["toplam_r"]
    return {"p": v2_test.p_degeri(T, s), "T": T, "n_islem": int(sum(len(d) for d in gercek.values())), "B": B, "tohum": tohum,
            "gecersiz_oran": (r["n_gecersiz"] / max(1, r["n_islem"])), "desteklenmeyen": []}


def tek_grafik_kos(satir: dict, b: Baglam) -> dict:
    evren = kl.evren_coz(satir["evren"])
    tf = satir["tf"]
    ok, aciklama = tf_cozum(tf)
    if not ok:
        raise FileNotFoundError(aciklama)
    ham = {1.0: {}, 2.0: {}}
    mumlar_s: dict = {}
    for s in evren:
        for c in (1.0, 2.0):
            st, _, _ = _kur(satir)
            try:
                h, _, m = tek_ham_kos(st, s, tf, c, b.tablo, b.veri_al)
            except hm.HoldoutSizintisi:
                raise
            except Exception as e:  # noqa: BLE001 — sembol bağlamı eklenip yeniden fırlatılır (yutulmaz)
                raise RuntimeError(f"{s} x{c:g}: {type(e).__name__}: {e}") from e
            ham[c][s] = h
            mumlar_s[s] = m
    veri_bas = {s: pd.Timestamp(m.index[0]) for s, m in mumlar_s.items()}
    analiz_bas = we.analiz_bas_hesapla(veri_bas)
    analiz_bit = max(pd.Timestamp(m.index[-1]) for m in mumlar_s.values()) + pd.Timedelta(1, "ns")
    m1, _ = kendi_hesabi_oynat(ham[1.0], evren, analiz_bas, analiz_bit, 1.0, b.tablo)
    m2, _ = kendi_hesabi_oynat(ham[2.0], evren, analiz_bas, analiz_bit, 2.0, b.tablo)
    yonler = pd.concat([h["yon"] for h in ham[2.0].values() if len(h)], ignore_index=True) if any(len(h) for h in ham[2.0].values()) else pd.Series([], dtype=int)
    long_only = satir["yon"] == "long" or (satir["yon"] == "" and len(yonler) > 0 and bool((yonler == 1).all()))
    getiri = m2.get("getiri_serisi")
    sharpe2 = sharpe_x(getiri) if getiri is not None and len(getiri) else math.nan
    bh_sh = math.nan
    if long_only:
        bh = bh_net_getiri(mumlar_s, evren, analiz_bas, analiz_bit, 2.0, b.tablo)
        bh_sh = sharpe_x(bh) if len(bh) else math.nan
    k = kapilar_tek(m2, sharpe2, bh_sh, long_only, b.esik)
    out = {"tur": "tek", "n_islem_x2": m2.get("islem_sayisi", 0), "net_x2": m2.get("net_getiri"), "pf_x2": m2.get("profit_factor"),
           "n_islem_x1": m1.get("islem_sayisi", 0), "net_x1": m1.get("net_getiri"), "pf_x1": m1.get("profit_factor"),
           "kill_x2": m2.get("kill_olayi"), "kill_x1": m1.get("kill_olayi"), "sharpe_x2": sharpe2, "bh_sharpe_x2": bh_sh,
           "long_only": bool(long_only), "r_enstruman": m2.get("r_enstruman"), "r_yil": m2.get("r_yil"),
           "analiz_bas": str(analiz_bas), "tf_kaynak": aciklama, **k}
    if m2.get("islem_sayisi", 0) == 0:
        out.update(p=1.0, k6_durum="ISLEM_YOK")
        return out
    if tf in b.k6_on_eleme_tf and not all(k[x] for x in ("k1", "k2", "k3", "k4", "k5")):
        out.update(p=1.0, k6_durum="ATLANDI_K1_5")
        return out
    p6 = rastgele_giris_p(satir, ham[2.0], analiz_bas, mumlar_s, b, tf, evren)
    out["k6"] = p6
    out["p"] = p6["p"]
    if p6.get("desteklenmeyen"):
        out["k6_durum"] = "HATA"
        out["hata_k6"] = f"desteklenmeyen çıkış (rastgele giriş testi yok): {p6['desteklenmeyen']}"
    else:
        out["k6_durum"] = "TAMAM"
    return out


# ---------------------------------------------------------------- portföy koşusu
def portfoy_kos_satir(satir: dict, b: Baglam) -> dict:
    evren = kl.evren_coz(satir["evren"])
    tf = satir["tf"]
    ok, aciklama = tf_cozum(tf)
    if not ok:
        raise FileNotFoundError(aciklama)
    par = json.loads(satir["parametreler"])
    pk = kpf.portfoy_kos(satir["sinif"], par, tf, evren, b.veri_al, b.tablo)
    m = pk.metrikler
    long_only = satir["yon"] == "long"
    bh_sh = math.nan
    v, f, _ = kpf._veri_topla(evren, tf, b.veri_al)
    if long_only:
        bit = max(pd.Timestamp(x.index[-1]) for x in v.values()) + pd.Timedelta(1, "ns")
        bh = bh_net_getiri(v, tuple(v), m["analiz_bas"], bit, 2.0, b.tablo)
        bh_sh = sharpe_x(bh) if len(bh) else math.nan
    k = kapilar_portfoy(m, bh_sh, long_only, b.esik)
    out = {"tur": "pf", "net_x2": m.get("net_x2"), "net_x1": m.get("net_x1"), "sharpe_x2": m.get("sharpe_x2"), "sharpe_x1": m.get("sharpe_x1"),
           "gun": m.get("gun"), "dengeleme": m.get("dengeleme"), "net_en_iyi_yil_haric_x2": m.get("net_en_iyi_yil_haric_x2"),
           "kill_x2": m.get("kill_x2"), "kill_x1": m.get("kill_x1"), "bh_sharpe_x2": bh_sh, "long_only": long_only,
           "disarida": pk.disarida, "analiz_bas": m.get("analiz_bas"), "tf_kaynak": aciklama, **k}
    out["n_islem_x2"] = int(len(pk.x2.islemler))
    out["p"], out["k6_durum"] = 1.0, "PF_ATLANDI"
    if math.isfinite(m.get("sharpe_x2", math.nan)):
        out.update(pf_rastgele_p(satir, pk, v, f, b))
    return out


def pf_rastgele_p(satir: dict, pk, v: dict, f: dict, b: Baglam) -> dict:
    """Kapı 6 (portföy): v2 `pf_k2_simule` (RastgeleAgirlik, aynı yeniden dengeleme takvimi); aşama 1 B=K2_B1, p<=K2_GECIS_P ise aşama 2
    (v2 test ayarı korunur: B ek 2'ye göre). Gerçek büyüklük = x2 günlük Sharpe (aynı araştırma hesabı)."""
    from motor.arastirma import saglamlik_portfoy as sp
    from motor.portfoy.motor import portfoy_backtest
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    import dataclasses
    evren_t = tuple(v)
    sinif = tum_portfoy_stratejileri()[satir["sinif"]]
    st = sinif(**json.loads(satir["parametreler"]))
    etkin = st.etkin_semboller(evren_t)
    st = st.yeni(semboller=etkin) if etkin else st
    sec = wp.gerekli_semboller(st, evren_t)
    vv, ff = {s: v[s] for s in sec}, {s: f[s] for s in sec if s in f}
    ay = dataclasses.replace(hm.maliyet_pf(evren_t, 2.0, b.tablo), limit_modu="uygula", baslangic_sermaye=kpf.BASLANGIC_SERMAYE,
                             risk_yuzde=kpf.ISLEM_RISK_YUZDE)
    hz = sp.RastgeleHazirlik(st, vv)
    analiz_bas = pd.Timestamp(pk.metrikler["analiz_bas"])

    def sim(i, tohum):
        with kpf.arastirma_limitleri():
            r = portfoy_backtest(vv, sp.RastgeleAgirlik(st, hz, [tohum, i, 0]), ay, ff)
        return v2_test.sharpe_gunluk(v2_test.pf_gunluk_getiri(r, v, b.tablo, analiz_bas).to_numpy())
    gercek = float(pk.metrikler["sharpe_x2"])
    tohum = int(b.esik["tohum"]) + zlib.crc32(satir["kimlik"].encode())
    kismi = b.cikti / "_kismi" / guvenli(satir["kimlik"])
    sonuc = {}
    for ad, n in (("a1", sabit.K2_B1), ("a2", sabit.K2_B2.get(satir["tf"], sabit.K2_B2["1d"]))):
        s = v2_test.pf_k2_simule(satir["sinif"], "kripto", b.tablo, analiz_bas, n, tohum, kismi_dizin=kismi / ad, simulator=sim)
        p = v2_test.p_degeri(gercek, s)
        sonuc[ad] = {"B": n, "p": p}
        if ad == "a1" and not p <= sabit.K2_GECIS_P:
            break
    shutil.rmtree(kismi, ignore_errors=True)
    nihai = sonuc.get("a2", sonuc["a1"])["p"]
    return {"p": nihai, "k6_durum": "TAMAM", "k6": {**sonuc, "tohum": tohum, "yontem": "v2 pf_k2_simule (RastgeleAgirlik), x2"}}


# ---------------------------------------------------------------- kimlik işleyici
def kimlik_isle(satir: dict, b: Baglam | None = None) -> dict:
    """Bir kimliği koşar -> sonuç sözlüğü (durum TAMAM/HATA/COZULEMEDI). HoldoutSizintisi yeniden fırlatılır."""
    b = b or baglam()
    taban = {"kimlik": satir["kimlik"], "katman": satir["katman"], "sinif": satir["sinif"], "tf": satir["tf"], "evren": satir["evren"],
             "durum": "", "hata": "", "p": 1.0}
    if satir["durum"] != "KOSULACAK":
        return {**taban, "durum": "COZULEMEDI", "hata": satir["notlar"]}
    t0 = time.time()
    try:
        _, pf, _ = _kur(satir)
        sonuc = portfoy_kos_satir(satir, b) if pf else tek_grafik_kos(satir, b)
        out = {**taban, **sonuc, "durum": "TAMAM"}
        if sonuc.get("k6_durum") == "HATA":
            out.update(durum="HATA", hata=sonuc["hata_k6"], p=1.0)
        out["sure_sn"] = round(time.time() - t0, 1)
        return out
    except hm.HoldoutSizintisi:
        raise
    except Exception as e:  # noqa: BLE001 — kayıt altına alınır (durum=HATA); sessiz değil
        return {**taban, "durum": "HATA", "p": 1.0, "hata": f"{type(e).__name__}: {e}"[:600],
                "iz": traceback.format_exc()[-1500:], "sure_sn": round(time.time() - t0, 1)}


def json_yolu(kimlik: str, cikti: Path) -> Path:
    return cikti / f"{guvenli(kimlik)}.json"


def _isci_gorev(satir: dict) -> str:
    b = baglam()
    sonuc = kimlik_isle(satir, b)
    atomik_yaz(json_yolu(satir["kimlik"], b.cikti), sonuc)
    return f"{satir['kimlik']}: {sonuc['durum']} p={sonuc.get('p')}"


def kos(satirlar: list, isci: int = 4, sinir: int | None = None, b: Baglam | None = None, tf_haric: tuple = ()) -> dict:
    """Bekleyen kimlikleri koşar. isci<=1 ise aynı süreçte (enjekte bağlam); >1 ise fork'lu havuz (bağlam çocuklara miras kalır)."""
    b = b or baglam()
    kume = satirlar if sinir is None else satirlar[:sinir]
    bekleyen = [s for s in kume if not json_yolu(s["kimlik"], b.cikti).exists()]
    # Sıra sonucu değiştirmez (her kimlik bağımsız, tohum kimlikten); hızlı TF'ler önce biter.
    _hiz = {"1d": 0, "8h": 1, "6h": 2, "4h": 3, "3h": 4, "2h": 5, "1h": 6, "30m": 7, "15m": 8, "5m": 9}
    bekleyen.sort(key=lambda s: _hiz.get(s["tf"], 5))
    if tf_haric:                                         # ön kayıt eki 8: bu TF'ler koşulmaz, birleştirmede p=1 KOSULMADI
        bekleyen = [s for s in bekleyen if s["tf"] not in tf_haric]
    atlanan = len(kume) - len(bekleyen)
    print(f"[kos] liste {len(satirlar)} | hedef {len(kume)} | biten (atlanan) {atlanan} | koşulacak {len(bekleyen)} | işçi {isci}", flush=True)
    if isci <= 1 or len(bekleyen) <= 1:
        for s in bekleyen:
            print("[kos]", _isci_gorev(s), flush=True)
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(isci) as havuz:
            for mesaj in havuz.imap_unordered(_isci_gorev, bekleyen, chunksize=1):
                print("[kos]", mesaj, flush=True)
    return {"hedef": len(kume), "atlanan": atlanan, "kosulan": len(bekleyen)}


# ---------------------------------------------------------------- kuru mod
def kuru(satirlar: list, mum_dizini: Path | None = None, tablo: Path = TABLO) -> list:
    """Backtest yok, mum okunmaz: sınıf kurulumu, TF çözümü, evren sembolleri, veri dosyası varlığı/boyutu, maliyet tablosu satırı."""
    tab = evren_maliyet.yukle(tablo)
    rapor = []
    for s in satirlar:
        sorunlar, bilgi = [], []
        if s["durum"] != "KOSULACAK":
            rapor.append({"kimlik": s["kimlik"], "tf": s["tf"], "durum": s["durum"], "sorun": "COZULEMEDI: " + s["notlar"][-160:], "veri_mb": 0.0})
            continue
        try:
            st, pf, _ = _kur(s)
        except Exception as e:  # noqa: BLE001
            rapor.append({"kimlik": s["kimlik"], "tf": s["tf"], "durum": "SINIF_HATA", "sorun": f"{type(e).__name__}: {e}", "veri_mb": 0.0})
            continue
        ok, ac = tf_cozum(s["tf"])
        if not ok:
            sorunlar.append(ac)
        cls, _ = kl.sinif_coz(s["sinif"], s["modul"])
        try:
            evren = kl.evren_coz(s["evren"])
        except ValueError as e:
            evren = ()
            sorunlar.append(str(e))
        mb = 0.0
        for sym in evren:
            yol = depo.mum_yolu(sym, "5m", mum_dizini)
            if not yol.exists() or yol.stat().st_size == 0:
                sorunlar.append(f"VERI_YOK {sym}: 5m dosyası yok/boş")
            else:
                mb += yol.stat().st_size / 1e6
            if sym not in tab.index:
                sorunlar.append(f"MALIYET_YOK {sym}")
            if getattr(cls, "funding_gerekli", False):
                fy = depo.funding_yolu(sym, mum_dizini)
                if not fy.exists() or fy.stat().st_size == 0:
                    sorunlar.append(f"FUNDING_YOK {sym}")
        if not pf:
            try:
                dy = evren_k2.desteklenmeyen(st.cikis_ayarlari)
                if dy:
                    sorunlar.append(f"K6_DESTEKLENMEYEN {dy}")
            except Exception as e:  # noqa: BLE001
                sorunlar.append(f"cikis_ayarlari: {e}")
        rapor.append({"kimlik": s["kimlik"], "tf": s["tf"], "durum": "SORUNLU" if sorunlar else "TAMAM", "sorun": "; ".join(sorunlar),
                      "veri_mb": round(mb, 1), "tur": "pf" if pf else "tek", "tf_yol": ac, "semboller": ",".join(evren)})
    return rapor


# ---------------------------------------------------------------- birleştirme: BH + ikinci kapı + özet
def ikinci_kapi_tek(satir: dict, b: Baglam) -> dict:
    """40 sabit sembol, aynı kural, x2: ortalama işlem R > 0. Veri/maliyet yoksa geçmez, eksik sembol yazılır."""
    eksik, r_hepsi = [], []
    tf = satir["tf"]
    ok, ac = tf_cozum(tf)
    if not ok:
        return {"gecti": False, "eksik": [ac], "n": 0, "ort_r": None}
    for s in b.sembol_40:
        try:
            st, _, _ = _kur(satir)
            h, _, _ = tek_ham_kos(st, s, tf, 2.0, b.tablo_40, b.veri_al_40, kurallar=b.kurallar_40.get(s))
            r_hepsi.append(h["r"].to_numpy(dtype=float))
        except hm.HoldoutSizintisi:
            raise
        except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
            eksik.append(f"{s}: {type(e).__name__}: {str(e)[:120]}")
    r = np.concatenate(r_hepsi) if r_hepsi else np.array([])
    ort = float(r.mean()) if len(r) else math.nan
    return {"gecti": (not eksik) and len(r) > 0 and ort > 0, "eksik": eksik, "n": int(len(r)), "ort_r": ort}


def ikinci_kapi_pf(satir: dict, b: Baglam) -> dict:
    """Portföy karşılığı: 40 sembolde x2 net > 0 (ortalama işlem R portföyde tanımsız; belgelendi)."""
    try:
        pk = kpf.portfoy_kos(satir["sinif"], json.loads(satir["parametreler"]), satir["tf"], b.sembol_40, b.veri_al_40, b.tablo_40)
    except hm.HoldoutSizintisi:
        raise
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
        return {"gecti": False, "eksik": [f"{type(e).__name__}: {str(e)[:200]}"], "n": 0, "ort_r": None}
    net = pk.metrikler.get("net_x2")
    return {"gecti": (not pk.disarida) and _gec(net, lambda v: v > 0), "eksik": list(pk.disarida), "n": int(len(pk.x2.islemler)), "ort_r": net}


def birlestir(satirlar: list, b: Baglam | None = None, eksik_izin: bool = False, sonuc_csv: Path = SONUC_CSV, ozet_md: Path = OZET_MD) -> dict:
    b = b or baglam()
    sonuc, eksik = {}, []
    for s in satirlar:
        y = json_yolu(s["kimlik"], b.cikti)
        if y.exists():
            sonuc[s["kimlik"]] = json.loads(y.read_text(encoding="utf-8"))
        else:
            eksik.append(s["kimlik"])
    if eksik and not eksik_izin:
        raise RuntimeError(f"{len(eksik)} kimlik henüz bitmedi (örn. {eksik[:3]}); önce koşu bitmeli ya da --eksik-izin")
    m = len(satirlar)
    p = {}
    for s in satirlar:
        r = sonuc.get(s["kimlik"])
        v = None if r is None or r.get("durum") != "TAMAM" else r.get("p")
        p[s["kimlik"]] = float(v) if v is not None and math.isfinite(float(v)) else 1.0
    bh = v2_test.bh_kesif(p, m, b.esik["bh_q"])
    kesif = set(bh["kesif"])
    satir_by = {s["kimlik"]: s for s in satirlar}
    cikti = []
    for s in satirlar:
        k = s["kimlik"]
        r = sonuc.get(k, {"durum": "KOSULMADI", "hata": "JSON yok (--eksik-izin)"})
        k1_5 = all(r.get(x) is True for x in ("k1", "k2", "k3", "k4", "k5"))
        k6 = r.get("durum") == "TAMAM" and _gec(r.get("p"), lambda v: v <= b.esik["p_esik"])
        k7 = k in kesif
        birinci = bool(k1_5 and k6 and k7)
        ik = {"gecti": None, "eksik": [], "n": None, "ort_r": None}
        if birinci:
            yol = b.cikti / "_ikinci" / f"{guvenli(k)}.json"
            if yol.exists():
                ik = json.loads(yol.read_text(encoding="utf-8"))
            else:
                ik = ikinci_kapi_pf(s, b) if r.get("tur") == "pf" else ikinci_kapi_tek(s, b)
                atomik_yaz(yol, ik)
        cikti.append({
            "kimlik": k, "katman": s["katman"], "sinif": s["sinif"], "tf": s["tf"], "evren": s["evren"], "durum": r.get("durum"),
            "hata": r.get("hata", ""), "tur": r.get("tur", ""), "n_islem_x2": r.get("n_islem_x2"), "net_x2": r.get("net_x2"),
            "pf_x2": r.get("pf_x2"), "sharpe_x2": r.get("sharpe_x2"), "bh_sharpe_x2": r.get("bh_sharpe_x2"), "long_only": r.get("long_only"),
            "kill_x2": r.get("kill_x2"), "net_x1": r.get("net_x1"), "pf_x1": r.get("pf_x1"),
            "kapi1": r.get("k1"), "kapi2": r.get("k2"), "kapi3": r.get("k3"), "kapi4": r.get("k4"), "kapi5": r.get("k5"),
            "kapi6_p": p[k], "kapi6": bool(k6), "kapi7_bh": bool(k7), "bh_sira": bh["sira"][k], "bh_esik": bh["esik"][k],
            "birinci_kapi": birinci, "ikinci_kapi": ik["gecti"], "ikinci_n": ik["n"], "ikinci_ort": ik["ort_r"],
            "ikinci_eksik": "; ".join(ik["eksik"]), "paper_adayi": bool(birinci and ik["gecti"]),
            "yaklasik": s["yaklasik"], "emin_degil": s["emin_degil"], "notlar": s["notlar"][:200]})
    df = pd.DataFrame(cikti)
    df = df.assign(_sira=df["kapi6_p"]).sort_values(["_sira", "kimlik"], kind="stable").drop(columns="_sira")
    sonuc_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(sonuc_csv, index=False)
    ozet = ozet_uret(df, m, bh, b)
    ozet_md.write_text(ozet, encoding="utf-8")
    return {"aile": m, "bh_k_yildiz": bh["k_yildiz"], "birinci": int(df["birinci_kapi"].sum()), "paper": int(df["paper_adayi"].sum()),
            "hata": int((df["durum"] == "HATA").sum()), "cozulemedi": int((df["durum"] == "COZULEMEDI").sum()), "eksik": len(eksik)}


def ozet_uret(df: pd.DataFrame, m: int, bh: dict, b: Baglam) -> str:
    durum = df["durum"].value_counts().to_dict()
    gecen = df[df["paper_adayi"]]
    birinci = df[df["birinci_kapi"]]
    satirlar = ["# Kapanış aşama 1 sonuç özeti", "",
                f"- BH ailesi (dondurulmuş liste satır sayısı): {m}; q={b.esik['bh_q']}; k*={bh['k_yildiz']}",
                f"- Durumlar: {durum}",
                f"- Kapı 1-5 geçen: {int(df[['kapi1', 'kapi2', 'kapi3', 'kapi4', 'kapi5']].fillna(False).astype(bool).all(axis=1).sum())}",
                f"- Kapı 6 (p<={b.esik['p_esik']}) geçen: {int(df['kapi6'].sum())}",
                f"- Birinci kapı (1-7) geçen: {len(birinci)}",
                f"- İkinci kapıyı da geçen (yalnız paper adayı; 12 hafta ileri gözlem + ayrı kullanıcı onayı olmadan canlı yok): {len(gecen)}", ""]
    for r in birinci.itertuples():
        satirlar.append(f"  - {r.kimlik} ({r.katman}, {r.tf}) p={r.kapi6_p:.4g} ikinci_kapı={r.ikinci_kapi} eksik={r.ikinci_eksik or '-'}")
    satirlar += ["", "Not: elenen stratejiye yeni ayar/kapı denemesi yoktur; bu tablo sonuç kaydıdır (ön kayıt)."]
    return "\n".join(satirlar) + "\n"


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kapanış koşucusu (aşama 1 / aşama 2: ayrı dondurulmuş liste, ayrı BH ailesi)")
    ap.add_argument("--asama", type=int, choices=(1, 2), default=1)
    ap.add_argument("--liste", default=None)
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--isci", type=int, default=4)
    ap.add_argument("--sinir", type=int, default=None, help="ilk K kimlik (deneme)")
    ap.add_argument("--kuru", action="store_true", help="yalnız çözümleme; backtest/mum okuma yok")
    ap.add_argument("--birlestir", action="store_true")
    ap.add_argument("--tf-haric", default="", help="virgüllü TF listesi; koşulmaz (ek 8)")
    ap.add_argument("--k6-on-eleme-tf", default="", help="virgüllü TF listesi; kapı 6 yalnız kapı 1-5'i geçenlere (ek 9)")
    ap.add_argument("--eksik-izin", action="store_true", help="birleştirmede bitmemiş kimliklere izin (p=1, KOSULMADI)")
    a = ap.parse_args(argv)
    ek = f"asama{a.asama}"
    a.liste = a.liste or str(KAPANIS / f"kosu_listesi_{ek}.csv")
    a.cikti = a.cikti or str(KAPANIS / f"kosu_{ek}")
    kl.dogrula_dosya(Path(a.liste))                      # donmuş liste SHA'sı tutmuyorsa DUR
    satirlar = liste_oku(Path(a.liste))
    if a.kuru:
        rapor = kuru(satirlar if a.sinir is None else satirlar[:a.sinir])
        yol = KAPANIS / f"kosu_{ek}_kuru.csv"
        pd.DataFrame(rapor).to_csv(yol, index=False)
        df = pd.DataFrame(rapor)
        uniq = {x for r in df["semboller"].dropna() for x in r.split(",")}
        mb = sum(depo.mum_yolu(x, "5m").stat().st_size for x in uniq if depo.mum_yolu(x, "5m").exists()) / 1e6
        print(f"[kuru] {len(df)} kimlik; durum: {df['durum'].value_counts().to_dict()}; {len(uniq)} benzersiz sembol, 5m dosya toplamı ~{mb:.0f} MB; yazıldı: {yol}")
        for r in df[df["durum"] != "TAMAM"].itertuples():
            print("  ", r.kimlik, r.durum, "|", r.sorun)
        return 0
    b = baglam_kur(cikti=Path(a.cikti), k6_on_eleme_tf=tuple(x for x in a.k6_on_eleme_tf.split(",") if x))
    if a.birlestir:
        print(birlestir(satirlar, b, eksik_izin=a.eksik_izin, sonuc_csv=KAPANIS / f"sonuc_{ek}.csv", ozet_md=KAPANIS / f"ozet_{ek}.md"))
        return 0
    print(kos(satirlar, isci=a.isci, sinir=a.sinir, b=b, tf_haric=tuple(x for x in a.tf_haric.split(",") if x)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
