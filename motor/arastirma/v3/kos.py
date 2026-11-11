"""v3 eleme koşusu (ON_KAYIT_V3 bölüm 1, 1.2, 2, 3). Satır başına: eleme dönemi, maliyet ×1/×2 (×3 rapor), tek hesap yeniden
oynatma (SERT_LIMITLER), kapılar V1-V5 (tek grafik) / P1-P6 (portföy), rastgele-giriş / rastgele-ağırlık testi, rapor ekleri.

v2 modülleri ÇAĞRILIR, değiştirilmez: ham.islem_hazirla (TradFi funding), eleme.kasa_oynat / portfoy_metrikleri / _gecer / _kalan_toplam
(secim.yeniden_oyna), test.cakisma_suz / pf_gunluk_getiri / p_degeri, ham.varsayilan_pf / maliyet_pf / pf_fonlama_duzeltmesi.
Eşik sayıları YALNIZ sabit.py'de. Hata veren satır ELENMİŞ sayılır (`satir_calistir`); istisna kaydedilir, sessizce yutulmaz."""
from __future__ import annotations

import dataclasses
import math
import time
import traceback
from typing import Callable, Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet
from motor.arastirma import saglamlik_portfoy as sp
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_portfoy as wep
from motor.arastirma import wf_portfoy as wp
from motor.arastirma.v2 import eleme as v2e
from motor.arastirma.v2 import ham as hm
from motor.arastirma.v2 import test as v2test
from motor.arastirma.v3 import destek, rastgele, sabit
from motor.backtest.motor import backtest
from motor.strateji import funding, kayit

NAN = math.nan


class AltyapiHatasi(RuntimeError):
    """Hiçbir metrik üretilmeden önceki altyapı hatası (veri okuma, bellek): bölüm 3 'Hata' istisnası (bir kez yeniden koşulur)."""


class DestekHatasi(RuntimeError):
    """Rastgele-giriş testi bu satırın çıkışlarını desteklemiyor: satır 'hata' (p = 1 DEĞİL)."""


# ============================================================================ kapılar (saf; sabit.py eşikleri)
def kapi_tek(o1: dict, net_x2: float, p: float, min_islem: int) -> dict:
    """V1-V5. o1: ×1 özeti (net, pf, n_islem, kill, r_yil); net_x2: ×2 oynatmasının neti; p: rastgele-giriş p'si. NaN = geçmez."""
    ned = []
    v1a = v2e._gecer(net_x2, lambda v: v > 0)
    v1b = v2e._gecer(o1.get("pf"), lambda v: v >= sabit.V1_PF_MIN)
    if not v1a:
        ned.append(f"V1 net(x2) {net_x2} <= 0 ya da hesaplanamadı")
    if not v1b:
        ned.append(f"V1 PF(x1) {o1.get('pf')} < {sabit.V1_PF_MIN} ya da hesaplanamadı")
    v2 = v2e._gecer(o1.get("n_islem"), lambda v: v >= min_islem)
    if not v2:
        ned.append(f"V2 işlem {o1.get('n_islem')} < {min_islem}")
    kalan = v2e._kalan_toplam(o1.get("r_yil") or {})
    v3 = v2e._gecer(kalan, lambda v: v > 0)
    if not v3:
        ned.append("V3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı")
    v4 = v2e._gecer(p, lambda v: v <= sabit.V4_P_MAX)
    if not v4:
        ned.append(f"V4 rastgele-giriş p {p} > {sabit.V4_P_MAX} ya da hesaplanamadı")
    v5 = v2e._gecer(o1.get("kill"), lambda v: v <= sabit.V5_MAKS_KILL)
    if not v5:
        ned.append(f"V5 kill_olayi(x1) {o1.get('kill')}")
    d = {"v1": bool(v1a and v1b), "v2": bool(v2), "v3": bool(v3), "v4": bool(v4), "v5": bool(v5), "v3_kalan_r": kalan}
    d["gecti"] = all(d[k] for k in ("v1", "v2", "v3", "v4", "v5"))
    d["nedenler"] = "; ".join(ned)
    return d


def kapi_portfoy(m: dict, p_rastgele: Optional[float], kiyas_sharpe: Optional[float], rastgele_gerekli: bool, al_tut_gerekli: bool) -> dict:
    """P1-P6. m: net_x1, net_x2, sharpe_x1, gun, dengeleme, net_en_iyi_yil_haric, kill_x1. P4/P6 uygulanmayan satırda None (= yok, geçer)."""
    ned = []
    p1 = v2e._gecer(m.get("net_x2"), lambda v: v > 0) and v2e._gecer(m.get("sharpe_x1"), lambda v: v >= sabit.P1_SHARPE_MIN)
    if not p1:
        ned.append(f"P1 net(x2) {m.get('net_x2')} / Sharpe(x1) {m.get('sharpe_x1')} (> 0 ve >= {sabit.P1_SHARPE_MIN})")
    p2 = (v2e._gecer(m.get("gun"), lambda v: v >= sabit.P2_MIN_GUN)
          and v2e._gecer(m.get("dengeleme"), lambda v: v >= sabit.P2_MIN_DENGELEME))
    if not p2:
        ned.append(f"P2 gün {m.get('gun')} / yeniden dengeleme {m.get('dengeleme')} (>= {sabit.P2_MIN_GUN} ve >= {sabit.P2_MIN_DENGELEME})")
    p3 = v2e._gecer(m.get("net_en_iyi_yil_haric"), lambda v: v > 0)
    if not p3:
        ned.append("P3 en iyi yıl çıkarılınca net <= 0 ya da hesaplanamadı")
    p4 = None
    if rastgele_gerekli:
        p4 = bool(v2e._gecer(p_rastgele, lambda v: v <= sabit.P4_P_MAX))
        if not p4:
            ned.append(f"P4 rastgele-ağırlık p {p_rastgele} > {sabit.P4_P_MAX} ya da hesaplanamadı")
    p5 = v2e._gecer(m.get("kill_x1"), lambda v: v <= sabit.P5_MAKS_KILL)
    if not p5:
        ned.append(f"P5 kill_olayi(x1) {m.get('kill_x1')}")
    p6 = None
    if al_tut_gerekli:
        p6 = bool(v2e._gecer(m.get("sharpe_x1"), lambda s: v2e._gecer(kiyas_sharpe, lambda k: s > k)))
        if not p6:
            ned.append(f"P6 strateji Sharpe {m.get('sharpe_x1')} <= al-tut kıyası {kiyas_sharpe} ya da hesaplanamadı")
    d = {"p1": bool(p1), "p2": bool(p2), "p3": bool(p3), "p4": p4, "p5": bool(p5), "p6": p6}
    d["gecti"] = all(v for v in (d["p1"], d["p2"], d["p3"], d["p4"], d["p5"], d["p6"]) if v is not None)
    d["nedenler"] = "; ".join(ned)
    return d


# ============================================================================ tek grafik
def strateji_uret(ad: str, parametreler: Optional[dict] = None):
    """Sınıfın varsayilan_parametreler'iyle (kart ayarı dosyası DEĞİL; bölüm 1). parametreler: rapor koşuları (ATR×20)."""
    st = kayit.al(ad)()
    return st.yeni(**parametreler) if parametreler else st


def genis_stop_parametresi(st) -> dict:
    """1.2: stop çarpanı parametresini 20'ye ayarlar; strateji bu parametreye sahip değilse AÇIK hata (sessiz atlama yok)."""
    if sabit.STOP_PARAMETRESI not in st.parametreler:
        raise KeyError(f"{st.ad}: '{sabit.STOP_PARAMETRESI}' parametresi yok (geniş stop koşusu kurulamaz)")
    return {sabit.STOP_PARAMETRESI: sabit.GENIS_STOP_ATR}


def maliyet_ayari(sembol: str, carpan: float, tablo_yolu):
    kural = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
    return evren_maliyet.maliyet_ayarlari(sembol, kural, carpan, tablo_yolu)


def tek_ham(st, sembol: str, tf: str, carpan: float, veri_al: Callable, tablo_yolu) -> tuple:
    """Stratejiyi TÜM veride (ısınma dahil) koşar. -> (ham işlem df (v2 biçimi: funding dahil r), mumlar)."""
    mumlar, fund = veri_al(sembol, tf)
    if not len(mumlar):
        raise AltyapiHatasi(f"{sembol} {tf}: mum yok")
    hazir = funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf)
    res = backtest(hazir, st, maliyet_ayari(sembol, carpan, tablo_yolu), fund)
    ham, _ = hm.islem_hazirla(res.islemler, sembol, tf, carpan, mumlar, tablo_yolu)
    return ham, mumlar


def tek_ozet(m: Optional[dict], tablo) -> dict:
    """Kasa metriklerinden (v2e.kasa_oynat çıktısı) kapı/rapor özeti. Kabul edilen işlemler üzerinden; yıl = giriş (UTC)."""
    bos = {"net": NAN, "pf": NAN, "n_islem": 0, "n_ham": 0, "kill": NAN, "sharpe": NAN, "max_dusus": NAN, "r_yil": {}, "net_yil": {}}
    if m is None or not m.get("islem_sayisi"):
        return bos
    kabul = m["kabul"]
    yil = pd.DatetimeIndex(tablo["giris"])[kabul].year
    r = pd.Series(tablo["r"].to_numpy(dtype=float)[kabul]).groupby(yil).sum()
    pnl = pd.Series([m["pnl"].get(i, 0.0) for i in kabul]).groupby(yil).sum()
    return {"net": m.get("net_getiri", NAN), "pf": m.get("profit_factor", NAN), "n_islem": int(m["islem_sayisi"]),
            "n_ham": int(m["n_oos_ham"]), "kill": m.get("kill_olayi", NAN), "sharpe": m.get("sharpe", NAN),
            "max_dusus": m.get("max_dusus", NAN),
            "r_yil": {int(k): float(v) for k, v in r.items()}, "net_yil": {int(k): float(v) for k, v in pnl.items()}}


def tek_donem(ham: pd.DataFrame, sembol: str, bas, carpan: float, tablo_yolu) -> dict:
    """Ham işlemleri `bas`tan itibaren tek hesapta oynatır (giriş < bas olanlar sayılmaz)."""
    m, tablo = v2e.kasa_oynat({sembol: ham}, (sembol,), bas, sabit.VERI_SONU, carpan, tablo_yolu)
    return tek_ozet(m, tablo)


def tek_sembol(satir, sembol: str, st, veri_al, tablo_yolu, n_sim: int, bas_alt_sinir: bool, ek_rapor: bool) -> dict:
    """Tek (satır, sembol) için ×1/×2/×3 oynatma, rastgele-giriş p'si ve kapılar. ek_rapor: geniş stop + tam dönem (yalnız ana sembol)."""
    dk = destek.satir_destek_st(satir, st)
    if dk["ok"] is not True:
        raise DestekHatasi(f"{satir.strateji}: {dk['neden']}")
    ham = {}
    for c in (sabit.CARPAN_ANA, sabit.CARPAN_KAPI, sabit.CARPAN_RAPOR):
        ham[c], mumlar = tek_ham(st, sembol, satir.tf, c, veri_al, tablo_yolu)
    bas = satir.bas if satir.bas is not None else mumlar.index[0].floor("D")
    o = {c: tek_donem(ham[c], sembol, bas, c, tablo_yolu) for c in ham}
    islemler = v2test.cakisma_suz({sembol: ham[sabit.CARPAN_ANA]}, bas)
    gercek = v2test.toplam_r(islemler)
    tohum = sabit.satir_tohumu(satir.strateji, "k2")
    cikti = {"o": o, "gercek_t": gercek, "p": NAN, "sim_ort": NAN, "sim_std": NAN, "gecersiz_oran": NAN, "bas": bas}
    if islemler:
        def ayar_al(s):
            return mumlar, maliyet_ayari(s, sabit.CARPAN_ANA, tablo_yolu)
        sim = rastgele.simule(islemler, ayar_al, n_sim, tohum, alt_sinir=bas if bas_alt_sinir else None)
        s = sim["toplam_r"]
        cikti.update(p=rastgele.p_degeri(gercek, s), sim_ort=float(np.mean(s)), sim_std=float(np.std(s, ddof=1)) if len(s) > 1 else NAN,
                     gecersiz_oran=sim["n_gecersiz"] / max(1, sim["n_islem"]))
    cikti["kapi"] = kapi_tek(o[sabit.CARPAN_ANA], o[sabit.CARPAN_KAPI]["net"], cikti["p"], satir.min_islem)
    if ek_rapor:
        gp = genis_stop_parametresi(st)
        gh, _ = tek_ham(st.yeni(**gp), sembol, satir.tf, sabit.CARPAN_ANA, veri_al, tablo_yolu)
        cikti["genis"] = tek_donem(gh, sembol, bas, sabit.CARPAN_ANA, tablo_yolu)
        if satir.tam_donem_rapor:
            b0 = mumlar.index[0].floor("D")
            cikti["tam"] = {c: tek_donem(ham[c], sembol, b0, c, tablo_yolu) for c in (sabit.CARPAN_ANA, sabit.CARPAN_KAPI)}
    return cikti


# ============================================================================ portföy
def pf_ayar(evren_t: tuple, carpan: float, tablo_yolu):
    """v2 maliyet_pf + SERT_LIMITLER UYGULANIR (limit_modu='uygula'; v2 'olc' idi): kill/günlük limit gerçekten işlemi durdurur."""
    return dataclasses.replace(hm.maliyet_pf(evren_t, carpan, tablo_yolu), limit_modu="uygula")


def pf_sonuc(r, v: dict, tablo_yolu) -> tuple:
    """Portföy motoru sonucu -> (DataFrame(gun, getiri, dengeleme), kill sayısı, brüt maruziyet Series). ham.pf_gorev ile aynı adımlar."""
    ozs = r.gunluk_ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last().astype(float)
    getiri = ozs.pct_change().fillna(0.0)
    getiri, _ = hm.pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
    q = r.pozisyon_gecmisi
    degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
    deng = set(pd.DatetimeIndex(q.index[degisti.to_numpy()]).floor("D")) if len(q) else set()
    out = pd.DataFrame({"gun": pd.DatetimeIndex(getiri.index).as_unit("ns"), "getiri": getiri.to_numpy(dtype=float),
                        "dengeleme": [g in deng for g in getiri.index]})
    kill = sum(1 for o in r.limit_olaylari if o.get("tur") == "kill_switch")
    brut = r.maruziyet["brut"].copy()
    brut.index = pd.DatetimeIndex(brut.index)
    return out, int(kill), brut


def pf_kos(satir, carpan: float, pf_veri_al: Callable, tablo_yolu, parametreler: Optional[dict] = None) -> dict:
    v, f, dis = pf_veri_al(satir.evren)
    evren_t = tuple(v)
    st = hm.varsayilan_pf(satir.strateji, evren_t)
    if st is None:
        raise RuntimeError(f"{satir.strateji}: varsayılan ayar bu evrende uygun değil")
    if parametreler:
        st = st.yeni(**parametreler)
    r = wep._kos(st, v, f, evren_t, pf_ayar(evren_t, carpan, tablo_yolu), 0)
    g, kill, brut = pf_sonuc(r, v, tablo_yolu)
    return {"g": g, "kill": kill, "brut": brut, "st": st, "v": v, "f": f, "evren_t": evren_t, "disarida": list(dis),
            "veri_bas": {s: str(v[s].index[0]) for s in v}, "n_islem": int(len(r.islemler))}


def pf_pencere(k: dict, analiz_bas) -> pd.Series:
    x = k["g"][pd.DatetimeIndex(k["g"]["gun"]) >= analiz_bas]
    return pd.Series(x["getiri"].to_numpy(dtype=float), index=pd.DatetimeIndex(x["gun"]))


def yil_net(r: pd.Series) -> dict:
    return {int(y): float(np.prod(1.0 + x.to_numpy()) - 1.0) for y, x in r.groupby(r.index.year)}


def max_dusus(r: pd.Series) -> float:
    if not len(r):
        return NAN
    e = np.cumprod(1.0 + r.to_numpy())
    z = np.maximum.accumulate(np.r_[1.0, e])[1:]
    return float(((z - e) / z).max())


def al_tut_getiri(v: dict, evren_t: tuple, gunler: pd.DatetimeIndex, ort_brut: float) -> pd.Series:
    """P6 kıyası: aynı evrenin eşit ağırlıklı al-tut'u (her gün veri olan sembollerin günlük getirisinin ortalaması; günlük takvim
    izgarası, kapanış ileri doldurulur) x stratejinin ortalama brüt maruziyeti. `gunler` üzerinde hizalanır; veri olmayan gün 0."""
    kap = {}
    for s in evren_t:
        c = v[s]["kapanis"].copy()
        c.index = pd.DatetimeIndex(c.index).floor("D")
        kap[s] = c.groupby(level=0).last()
    t0 = min(c.index[0] for c in kap.values())
    izgara = pd.date_range(t0, max(max(c.index[-1] for c in kap.values()), gunler[-1]), freq="D", tz="UTC")
    p = pd.DataFrame({s: c.reindex(izgara) for s, c in kap.items()}).ffill()
    for s, c in kap.items():                                   # ilk veri gününden önce NaN kalır (ffill geriye doldurmaz)
        p.loc[p.index < c.index[0], s] = np.nan
    ew = p.pct_change(fill_method=None).mean(axis=1)           # NaN'ler (henüz listelenmemiş) ortalamaya girmez
    return (ew * ort_brut).reindex(gunler).fillna(0.0)


def rw_simulator(st, v: dict, f: dict, evren_t: tuple, ay, tablo_yolu, analiz_bas) -> Callable:
    """Rastgele-ağırlık simülatörü (ON_KAYIT_V2 5.2; v3'te gerçek koşuyla AYNI hazırlık: stratejiye_hazirla + aynı maliyet/limit ayarı).
    sim(b, tohum) -> günlük Sharpe (analiz başlangıcından). Sim b tohumu [tohum, b, 0]."""
    sec = wp.gerekli_semboller(st, evren_t)
    hazir = {s: funding.stratejiye_hazirla(st, v[s], f.get(s), s, "1d") for s in sec}
    ff = {s: f[s] for s in sec if s in f}
    hz = sp.RastgeleHazirlik(st, hazir)
    from motor.portfoy.motor import portfoy_backtest

    def sim(b: int, tohum: int) -> float:
        r = portfoy_backtest(hazir, sp.RastgeleAgirlik(st, hz, [tohum, b, 0]), ay, ff)
        return v2test.sharpe_gunluk(v2test.pf_gunluk_getiri(r, v, tablo_yolu, analiz_bas).to_numpy())
    return sim


_RW: dict = {}


def _rw_parca(aralik: tuple) -> list:
    b0, b1 = aralik
    return [_RW["sim"](b, _RW["tohum"]) for b in range(b0, b1)]


def rw_sharpe_dizisi(sim: Callable, n_sim: int, tohum: int, isci: int = 1) -> np.ndarray:
    """n_sim rastgele-ağırlık Sharpe'ı; işçi sayısından BAĞIMSIZ aynı sonuç (sim b yalnız [tohum, b] tohumuna bağlıdır)."""
    parcalar = [(b, min(b + sabit.RW_BLOK, n_sim)) for b in range(0, n_sim, sabit.RW_BLOK)]
    _RW.update(sim=sim, tohum=tohum)
    if isci <= 1:
        out = [x for p in parcalar for x in _rw_parca(p)]
    else:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(isci) as havuz:
            out = [x for parca in havuz.map(_rw_parca, parcalar, chunksize=1) for x in parca]
    return np.asarray(out, dtype=float)


def portfoy_satiri(satir, pf_veri_al: Callable, tablo_yolu, n_sim: int, isci: int, ek_rapor: bool = True) -> dict:
    k1 = pf_kos(satir, sabit.CARPAN_ANA, pf_veri_al, tablo_yolu)
    k2 = pf_kos(satir, sabit.CARPAN_KAPI, pf_veri_al, tablo_yolu)
    k3 = pf_kos(satir, sabit.CARPAN_RAPOR, pf_veri_al, tablo_yolu)
    vb = {s: pd.Timestamp(t) for s, t in k1["veri_bas"].items()}
    m1 = {"veri_bas_sembol": k1["veri_bas"], "kill_olayi": k1["kill"]}
    met = v2e.portfoy_metrikleri(k1["g"], m1, k2["g"])
    analiz_bas = we.analiz_bas_hesapla(vb)
    r1, r2, r3 = pf_pencere(k1, analiz_bas), pf_pencere(k2, analiz_bas), pf_pencere(k3, analiz_bas)
    ort_brut = float(k1["brut"][k1["brut"].index >= analiz_bas].mean()) if len(k1["brut"]) else NAN
    met.update(net_x3=float(np.prod(1.0 + r3.to_numpy()) - 1.0) if len(r3) else NAN, sharpe_x3=wp.sharpe_gunluk(r3.to_numpy()),
               sharpe_x2=wp.sharpe_gunluk(r2.to_numpy()), max_dusus_x1=max_dusus(r1), net_yil=yil_net(r1), ort_brut=ort_brut,
               kill_x3=k3["kill"], kill_x2=k2["kill"], n_islem=k1["n_islem"], disarida=",".join(k1["disarida"]))
    p_r = kiyas = NAN
    if satir.rastgele == "agirlik":
        tohum = sabit.satir_tohumu(satir.strateji, "rw")
        sim = rw_simulator(k1["st"], k1["v"], k1["f"], k1["evren_t"], pf_ayar(k1["evren_t"], sabit.CARPAN_ANA, tablo_yolu),
                           tablo_yolu, analiz_bas)
        s = rw_sharpe_dizisi(sim, n_sim, tohum, isci)
        p_r = v2test.p_degeri(met["sharpe_x1"], s)
        met.update(sim_ort=float(np.nanmean(s)), sim_std=float(np.nanstd(s, ddof=1)) if np.isfinite(s).sum() > 1 else NAN)
    if satir.al_tut:
        kg = al_tut_getiri(k1["v"], k1["evren_t"], pd.DatetimeIndex(r1.index), ort_brut)
        kiyas = wp.sharpe_gunluk(kg.to_numpy())
    met.update(p_rastgele=p_r, kiyas_sharpe=kiyas)
    kapi = kapi_portfoy(met, p_r, kiyas, satir.rastgele == "agirlik", satir.al_tut)
    out = {"met": met, "kapi": kapi}
    if ek_rapor:
        kg_ = pf_kos(satir, sabit.CARPAN_ANA, pf_veri_al, tablo_yolu, genis_stop_parametresi(k1["st"]))
        rg = pf_pencere(kg_, analiz_bas)
        out["genis"] = {"net": float(np.prod(1.0 + rg.to_numpy()) - 1.0) if len(rg) else NAN, "sharpe": wp.sharpe_gunluk(rg.to_numpy()),
                        "max_dusus": max_dusus(rg), "kill": kg_["kill"]}
    return out


# ============================================================================ satır
def duz(on: str, d: dict) -> dict:
    return {f"{on}_{k}": v for k, v in d.items()}


def _json(d) -> str:
    import json
    return json.dumps({str(k): v for k, v in d.items()}, sort_keys=True)


def tek_satir_sonucu(satir, veri_al, tablo_yolu, n_sim: int) -> dict:
    st = strateji_uret(satir.strateji)
    sembol = satir.evren[0]
    k = tek_sembol(satir, sembol, st, veri_al, tablo_yolu, n_sim, bas_alt_sinir=satir.bas is not None, ek_rapor=True)
    o1 = k["o"][sabit.CARPAN_ANA]
    out = {"gecti": k["kapi"]["gecti"], "nedenler": k["kapi"]["nedenler"], "analiz_bas": str(k["bas"]),
           "v1": k["kapi"]["v1"], "v2": k["kapi"]["v2"], "v3": k["kapi"]["v3"], "v4": k["kapi"]["v4"], "v5": k["kapi"]["v5"],
           "v3_kalan_r": k["kapi"]["v3_kalan_r"],
           "net_x1": o1["net"], "net_x2": k["o"][sabit.CARPAN_KAPI]["net"], "net_x3": k["o"][sabit.CARPAN_RAPOR]["net"],
           "pf_x1": o1["pf"], "pf_x2": k["o"][sabit.CARPAN_KAPI]["pf"], "pf_x3": k["o"][sabit.CARPAN_RAPOR]["pf"],
           "n_islem": o1["n_islem"], "n_ham": o1["n_ham"], "kill_x1": o1["kill"], "sharpe_x1": o1["sharpe"],
           "max_dusus_x1": o1["max_dusus"], "r_yil": _json(o1["r_yil"]), "net_yil": _json(o1["net_yil"]),
           "p_rastgele": k["p"], "gercek_t": k["gercek_t"], "sim_ort": k["sim_ort"], "sim_std": k["sim_std"],
           "gecersiz_oran": k["gecersiz_oran"], "B": n_sim, "tohum_k2": sabit.satir_tohumu(satir.strateji, "k2")}
    out.update(duz("genis", {a: k["genis"][b] for a, b in (("net", "net"), ("pf", "pf"), ("n_islem", "n_islem"), ("sharpe", "sharpe"),
                                                           ("max_dusus", "max_dusus"), ("kill", "kill"))}))
    if "tam" in k:
        for c, on in ((sabit.CARPAN_ANA, "tam_x1"), (sabit.CARPAN_KAPI, "tam_x2")):
            t = k["tam"][c]
            out.update(duz(on, {"net": t["net"], "pf": t["pf"], "n_islem": t["n_islem"], "sharpe": t["sharpe"], "kill": t["kill"]}))
    for rs in satir.rapor_evren:                                 # satır 9: BTCUSDT yalnız rapor (kapı değil)
        kb = tek_sembol(satir, rs, st, veri_al, tablo_yolu, n_sim, bas_alt_sinir=satir.bas is not None, ek_rapor=False)
        b1 = kb["o"][sabit.CARPAN_ANA]
        out.update(duz("rapor_" + rs.lower(), {"net_x1": b1["net"], "net_x2": kb["o"][sabit.CARPAN_KAPI]["net"], "pf_x1": b1["pf"],
                                               "n_islem": b1["n_islem"], "kill_x1": b1["kill"], "sharpe_x1": b1["sharpe"],
                                               "p_rastgele": kb["p"], "gecti": kb["kapi"]["gecti"]}))
    return out


def portfoy_satir_sonucu(satir, pf_veri_al, tablo_yolu, n_sim: int, isci: int) -> dict:
    p = portfoy_satiri(satir, pf_veri_al, tablo_yolu, n_sim, isci)
    met, kapi = p["met"], p["kapi"]
    out = {"gecti": kapi["gecti"], "nedenler": kapi["nedenler"], "analiz_bas": met["analiz_bas"],
           "p1": kapi["p1"], "p2": kapi["p2"], "p3": kapi["p3"], "p4": kapi["p4"], "p5": kapi["p5"], "p6": kapi["p6"],
           "net_x1": met["net_x1"], "net_x2": met["net_x2"], "net_x3": met["net_x3"], "sharpe_x1": met["sharpe_x1"],
           "sharpe_x2": met["sharpe_x2"], "sharpe_x3": met["sharpe_x3"], "gun": met["gun"], "dengeleme": met["dengeleme"],
           "net_en_iyi_yil_haric": met["net_en_iyi_yil_haric"], "kill_x1": met["kill_x1"], "kill_x2": met["kill_x2"],
           "kill_x3": met["kill_x3"], "max_dusus_x1": met["max_dusus_x1"], "net_yil": _json(met["net_yil"]),
           "ort_brut": met["ort_brut"], "kiyas_sharpe": met["kiyas_sharpe"], "p_rastgele": met["p_rastgele"],
           "sim_ort": met.get("sim_ort", NAN), "sim_std": met.get("sim_std", NAN), "n_islem": met["n_islem"],
           "disarida": met["disarida"], "B": n_sim if satir.rastgele == "agirlik" else 0}
    if satir.rastgele == "agirlik":
        out["tohum_rw"] = sabit.satir_tohumu(satir.strateji, "rw")
    out.update(duz("genis", p["genis"]))
    return out


def satir_kos(satir, veri_al: Callable, pf_veri_al: Callable, tablo_yolu, n_sim: Optional[int] = None, isci: int = 1) -> dict:
    """Satırı koşar; istisna YUKARI çıkar (`satir_calistir` kaydeder)."""
    n_sim = sabit.B if n_sim is None else n_sim
    if satir.tur == "portfoy":
        return portfoy_satir_sonucu(satir, pf_veri_al, tablo_yolu, n_sim, isci)
    return tek_satir_sonucu(satir, veri_al, tablo_yolu, n_sim)


def _hata_turu(e: BaseException) -> str:
    return "altyapi" if isinstance(e, (AltyapiHatasi, FileNotFoundError, MemoryError)) else "hesap"


def satir_calistir(satir, veri_al: Callable, pf_veri_al: Callable, tablo_yolu, n_sim: Optional[int] = None, isci: int = 1) -> dict:
    """Bölüm 3 'Hata': satır istisna verirse ELENMİŞ sayılır (gecti=False, durum='hata'); istisna türü ve iz kaydedilir. Hiçbir metrik
    üretilmeden önceki altyapı hatası `hata_turu='altyapi'` ile işaretlenir (bir kez yeniden koşulabilir). Sessiz yutma yok."""
    t0 = time.perf_counter()
    taban = {"no": satir.no, "kart": satir.kart, "strateji": satir.strateji, "tur": satir.tur, "tf": satir.tf,
             "evren": ",".join(satir.evren), "bas": "" if satir.bas is None else str(satir.bas.date()),
             "veri_sonu": str(sabit.VERI_SONU), "surum": sabit.SURUM}
    try:
        out = satir_kos(satir, veri_al, pf_veri_al, tablo_yolu, n_sim, isci)
        out.update(durum="gecti" if out["gecti"] else "elendi", hata="", hata_turu="")
    except Exception as e:  # noqa: BLE001  (kaydedilir: durum 'hata' = elendi; sessiz yutma değil)
        iz = "".join(traceback.format_exception(type(e), e, e.__traceback__))[-1500:]
        out = {"gecti": False, "durum": "hata", "hata": f"{type(e).__name__}: {e}"[:400], "hata_turu": _hata_turu(e), "hata_iz": iz,
               "nedenler": f"hata: {type(e).__name__}: {e}"[:400]}
    out.update(taban)
    out["sure_sn"] = round(time.perf_counter() - t0, 1)
    return out
