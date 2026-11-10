"""v2 Aşama 3 — resmi test (ON_KAYIT_V2 bölüm 5; P1-3). Tek çoklu-test adımı.

5.1 (tek-grafik) K2 rastgele giriş: her gerçek işlem için enstrüman, yön, stop/ATR14 katı ve stratejinin KENDİ çıkış kuralları
(`evren_k2.tek_islem_r`) korunur; giriş mumu, gerçek girişin bulunduğu TAKVİM ÇEYREĞİ (UTC) içinden o enstrümanın mumlarından
tekdüze çekilir. Sınama büyüklüğü T = ΣR (enstrüman başı çakışma süzgecinden sonra, tek kasa oynatmasından önce), maliyet x1.
Hız: çeyrek içindeki aday giriş mumu sayısı sınırlıdır; aynı (işlem, giriş mumu) sonucu bir kez hesaplanıp önbellekten okunur
(çekimler ve p-değeri naif döngüyle BİREBİR aynıdır, yalnız hızlıdır).
5.2 portföy: v1 rastgele-ağırlık testi (aynı takvim / ağırlık kümesi / rastgele semboller), büyüklük = günlük Sharpe.
5.3 iki aşama: B = K2_B1 (tohum k2a); p <= K2_GECIS_P ise YENİ tohumla (k2b) B = K2_B2[tf]; nihai p YALNIZ 2. aşamadan.
Elenen / hata / test koşulmayan / desteklenmeyen çıkış modüllü satır: p = 1.
5.4 BH (m havuz mührü; eşitlikte alfabetik), 5.5 BY ve Hansen SPA yalnız RAPOR.

Kalıcılık: sembol bazında kısmi sonuç (test_kismi/*.npy), aşama bazında satır dosyası (test_satir/*.json); süreç kesilirse kaldığı
yerden sürer. Bütçe (butce_sn) dolunca yeni görev/aşama BAŞLATILMAZ. Tüm satırlar tamsa test.csv + test_ozet.json yazılır.
"""
from __future__ import annotations

import json
import math
import time
import zlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_k2, evren_maliyet, saglamlik
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import eleme, ham as hm, kasa, sabit
from motor.strateji import funding
from motor.strateji import gostergeler as gst


# ============================================================================ saf istatistik
def p_degeri(gercek: float, sim) -> float:
    """1.3: p = (1 + #{sim >= gerçek}) / (B + 1). NaN simülasyon eşitsizliği sağlamaz (B'ye sayılır)."""
    s = np.asarray(sim, dtype=float)
    if not np.isfinite(gercek):
        return math.nan
    return float((1 + int((s >= gercek).sum())) / (len(s) + 1))


def bh_kesif(p: dict, m: int, q: float = sabit.BH_Q) -> dict:
    """5.4 Benjamini-Hochberg. p: {anahtar: p}. m hipotez (hipotez sayısı >= len(p); eksikler p=1 sayılır, reddedilemez).
    Sıralama: p artan, eşitlikte anahtar alfabetik. k* = max{k : p_(k) <= q k / m}; ilk k* anahtar keşif.
    -> {'k_yildiz', 'kesif': [anahtar...], 'sira': {anahtar: k}, 'esik': {anahtar: q k / m}}"""
    if m < len(p):
        raise ValueError(f"m ({m}) hipotez sayısından ({len(p)}) küçük olamaz")
    sirali = sorted(p, key=lambda a: (p[a], a))
    sira = {a: k + 1 for k, a in enumerate(sirali)}
    esik = {a: q * sira[a] / m for a in sirali}
    kyildiz = 0
    for a in sirali:
        if p[a] <= esik[a]:
            kyildiz = sira[a]
    return {"k_yildiz": kyildiz, "kesif": sirali[:kyildiz], "sira": sira, "esik": esik}


def by_kesif(p: dict, m: int, q: float = sabit.BH_Q) -> dict:
    """5.5 Benjamini-Yekutieli (rapor): eşik q k / (m Σ_{j<=m} 1/j)."""
    c = float(sum(1.0 / j for j in range(1, m + 1)))
    r = bh_kesif(p, m, q / c)
    return {"k_yildiz": r["k_yildiz"], "kesif": r["kesif"], "c_m": c}


# ============================================================================ 5.1 K2 çekirdeği
def ceyrek_sinirlari(giris_zamanlari, alt_sinir=None) -> tuple:
    """Her girişin takvim çeyreği (UTC) [başlangıç, bitiş). alt_sinir verilirse çeyrek başlangıcı bunun altına inmez
    (holdout: sınırı aşan çeyrek kesilir). -> (bas DatetimeIndex, bit DatetimeIndex) tz-aware UTC."""
    gi = pd.DatetimeIndex(giris_zamanlari).tz_convert("UTC")
    donem = gi.tz_localize(None).to_period("Q")
    bas = donem.start_time.tz_localize("UTC")
    bit = (donem + 1).start_time.tz_localize("UTC")
    if alt_sinir is not None:
        bas = pd.DatetimeIndex(np.maximum(bas.asi8, pd.Timestamp(alt_sinir).as_unit("ns").value)).tz_localize("UTC")
    return bas, bit


def cakisma_suz(ham: dict, analiz_bas) -> dict:
    """{sembol: ham df} -> {sembol: df}: analiz başlangıcından önce girilenler atılır, enstrüman başı çakışma süzgeci (v1)."""
    parca = []
    for s, df in ham.items():
        if df is None or not len(df):
            continue
        d = df[pd.DatetimeIndex(df["giris_zamani"]) >= analiz_bas].copy()
        if len(d):
            d["sembol"] = s
            parca.append(d)
    if not parca:
        return {}
    oos, _ = we.sembol_cakismasini_ele(pd.concat(parca, ignore_index=True))
    return {s: d.reset_index(drop=True) for s, d in oos.groupby("sembol", sort=True)}


def toplam_r(islemler: dict) -> float:
    return float(sum(float(d["r"].astype(float).sum()) for d in islemler.values()))


def _sembol_k2(d: pd.DataFrame, mumlar: pd.DataFrame, ay, ci: Optional[dict], n_sim: int, rng, alt_sinir=None) -> tuple:
    """Tek enstrüman: -> (toplam_r (n_sim,), geçersiz, işlem sayısı). Her işlem için B çekim; ilk geçerli çekim sayılır
    (en çok K2_YENIDEN_CEKIM çekim; hiçbiri geçerli değilse işlem atlanır = geçersiz)."""
    idx = mumlar.index
    o, h = mumlar["acilis"].to_numpy(float), mumlar["yuksek"].to_numpy(float)
    l, c = mumlar["dusuk"].to_numpy(float), mumlar["kapanis"].to_numpy(float)
    atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], saglamlik.ATR_PERIYOT).to_numpy(float)
    n = len(mumlar)
    gj = idx.get_indexer(pd.DatetimeIndex(d["giris_zamani"]))
    if (gj < 0).any():
        raise ValueError(f"giriş zamanı mum indeksinde yok ({int((gj < 0).sum())}/{len(gj)})")
    hm_ = saglamlik.tutma_mum(idx, d["giris_zamani"], d["cikis_zamani"])
    mesafe = d["stop_mesafe"].to_numpy(float)
    stop_med = float(np.nanmedian(mesafe)) if len(mesafe) else math.nan
    mesafe = np.where(np.isfinite(mesafe) & (mesafe > 0), mesafe, stop_med)
    with np.errstate(divide="ignore", invalid="ignore"):
        mult = mesafe / atr[np.maximum(gj - 1, 0)]
    gec = np.isfinite(mult) & (mult > 0)
    mult = np.where(gec, mult, np.median(mult[gec]) if gec.any() else 1.0)
    yon = d["yon"].to_numpy(int)
    qbas, qbit = ceyrek_sinirlari(d["giris_zamani"], alt_sinir)
    kayma, skayma, taker = ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4, ay.komisyon_taker_yuzde / 100
    iz_onb: dict = {}

    def iz_atr(per):
        if per not in iz_onb:
            iz_onb[per] = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], per).to_numpy(float)
        return iz_onb[per]
    toplam = np.zeros(n_sim)
    gecersiz = 0
    yc = sabit.K2_YENIDEN_CEKIM
    for k in range(len(d)):
        lo = max(1, int(idx.searchsorted(qbas[k], "left")))
        hi = min(int(idx.searchsorted(qbit[k], "left")), n - int(hm_[k]))
        if hi <= lo:                                        # çeyrekte yer yok: en geç olanı kullan (v1 kuralı)
            hi = lo + 1
        u = rng.random((n_sim, yc))
        j = np.clip((lo + u * (hi - lo)).astype(np.int64), 1, n - 2)
        onb: dict = {}

        def deger(jj: int) -> float:
            if jj in onb:
                return onb[jj]
            hk = min(int(hm_[k]), n - 1 - jj)
            if not np.isfinite(atr[jj - 1]):
                v = math.nan
            elif ci is None:
                r = saglamlik._tek_islem_r(o, h, l, c, atr, jj, int(yon[k]), hk, float(mult[k]), kayma, skayma, taker)
                v = math.nan if r is None else float(r)
            else:
                r = evren_k2.tek_islem_r(
                    o, h, l, c, atr, jj, int(yon[k]), hk, float(mult[k]), kayma, skayma, taker,
                    ex=ci["ex_long"] if yon[k] == 1 else ci["ex_short"], hedef_r=ci["hedef_r"], iz_k=ci["iz_k"],
                    iz_atr=iz_atr(ci["iz_periyot"]) if ci["iz_k"] else None, be_r=ci["be_r"])
                v = math.nan if r is None else float(r)
            onb[jj] = v
            return v
        sonuc = np.full(n_sim, np.nan)
        bekleyen = np.arange(n_sim)
        for e in range(yc):
            if not len(bekleyen):
                break
            jl = j[bekleyen, e]
            uj, ters = np.unique(jl, return_inverse=True)
            vals = np.array([deger(int(x)) for x in uj])[ters]
            ok = np.isfinite(vals)
            sonuc[bekleyen[ok]] = vals[ok]
            bekleyen = bekleyen[~ok]
        gecersiz += int(len(bekleyen))
        toplam += np.where(np.isfinite(sonuc), sonuc, 0.0)
    return toplam, gecersiz, int(len(d)) * n_sim


def k2_simule(islemler: dict, veri_al, cikis_al, n_sim: int, tohum: int, alt_sinir=None, kismi_dizin: Optional[Path] = None) -> dict:
    """islemler: {sembol: işlem df (giris_zamani, cikis_zamani, yon, r, stop_mesafe)}. veri_al(sembol) -> (mumlar, MotorAyarlari);
    cikis_al(sembol) -> evren_k2.cikis_bilgisi sözlüğü | None. Sembol başına RNG = default_rng([tohum, crc32(sembol)]) (kısmi sonuç
    ve devam için bağımsız). kismi_dizin verilirse biten sembol sonucu <sembol>.npy olarak yazılır / varsa okunur.
    -> {'toplam_r': (n_sim,), 'n_gecersiz', 'n_islem'}"""
    toplam = np.zeros(n_sim)
    gecersiz = n_islem = 0
    for sembol in sorted(islemler):
        kismi = Path(kismi_dizin) / f"{sembol}.npz" if kismi_dizin is not None else None
        if kismi is not None and kismi.exists():
            z = np.load(kismi)
            if len(z["toplam"]) != n_sim:
                raise RuntimeError(f"{kismi}: kısmi sonuç B ile uyuşmuyor (stale)")
            t, g, ni = z["toplam"], int(z["gecersiz"]), int(z["n_islem"])
        else:
            mumlar, ay = veri_al(sembol)
            rng = np.random.default_rng([tohum, zlib.crc32(sembol.encode())])
            t, g, ni = _sembol_k2(islemler[sembol], mumlar, ay, cikis_al(sembol), n_sim, rng, alt_sinir)
            if kismi is not None:
                kismi.parent.mkdir(parents=True, exist_ok=True)
                gecici = kismi.with_suffix(".tmp.npz")
                np.savez(gecici, toplam=t, gecersiz=g, n_islem=ni)
                gecici.replace(kismi)
        toplam += t
        gecersiz += g
        n_islem += ni
    return {"toplam_r": toplam, "n_gecersiz": gecersiz, "n_islem": n_islem}


def tek_satir_baglam(ad: str, tf: str, tablo_yolu):
    """Havuz satırı için (veri_al, cikis_al, desteklenmeyen). veri_ayarla(None, DONEM) kurulu olmalı. Varsayılan ayar (1.1)."""
    _, st = hm.varsayilan_strateji(ad)
    destek_yok = evren_k2.desteklenmeyen(st.cikis_ayarlari)
    onb_v, onb_c = {}, {}

    def veri_al(sembol):
        if sembol not in onb_v:
            mumlar, _ = hm.veri_oku(sembol, tf)
            kural = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
            onb_v[sembol] = (mumlar, evren_maliyet.maliyet_ayarlari(sembol, kural, 1.0, tablo_yolu))
        return onb_v[sembol]

    def cikis_al(sembol):
        if sembol not in onb_c:
            mumlar, fund = hm.veri_oku(sembol, tf)
            onb_c[sembol] = evren_k2.cikis_bilgisi(st, funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf))
        return onb_c[sembol]
    return veri_al, cikis_al, destek_yok


# ============================================================================ 5.2 portföy
def pf_gunluk_getiri(r, v: dict, tablo_yolu, analiz_bas) -> pd.Series:
    """Portföy motoru sonucundan günlük getiri (ham.pf_gorev ile AYNI adımlar: özsermaye -> getiri -> TradFi funding düzeltmesi),
    analiz başlangıcından itibaren."""
    ozs = r.gunluk_ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last().astype(float)
    getiri = ozs.pct_change().fillna(0.0)
    getiri, _ = hm.pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
    return getiri[pd.DatetimeIndex(getiri.index) >= analiz_bas]


def sharpe_gunluk(x) -> float:
    from motor.arastirma import wf_portfoy as wp
    return float(wp.sharpe_gunluk(np.asarray(x, dtype=float)))


def pf_k2_simule(ad: str, evren_adi: str, tablo_yolu, analiz_bas, n_sim: int, tohum: int, kismi_dizin: Optional[Path] = None,
                 simulator=None, holdout: bool = False) -> np.ndarray:
    """5.2: n_sim rastgele-ağırlık Sharpe'ı. Sim b tohumu [tohum, b] (bağımsız; devam edilebilir). Kısmi sonuç: bloklar halinde
    <kismi_dizin>/sharpe.npy (kaç sim bittiyse onu içerir). simulator(b, tohum) -> Sharpe | None ise gerçek motor kurulur."""
    kismi = Path(kismi_dizin) / "sharpe.npy" if kismi_dizin is not None else None
    sonuc = np.full(n_sim, np.nan)
    bitti = 0
    if kismi is not None and kismi.exists():
        onceki = np.load(kismi)
        if len(onceki) > n_sim:
            raise RuntimeError(f"{kismi}: kısmi sonuç B'den uzun (stale)")
        sonuc[:len(onceki)] = onceki
        bitti = len(onceki)
    if simulator is None:
        simulator = _pf_gercek_simulator(ad, evren_adi, tablo_yolu, analiz_bas, holdout)
    blok = sabit.PF_KAYIT_BLOK
    for b in range(bitti, n_sim):
        sonuc[b] = simulator(b, tohum)
        if kismi is not None and ((b + 1) % blok == 0 or b + 1 == n_sim):
            kismi.parent.mkdir(parents=True, exist_ok=True)
            gecici = kismi.with_suffix(".tmp.npy")
            np.save(gecici, sonuc[:b + 1])
            gecici.replace(kismi)
    return sonuc


def _pf_gercek_simulator(ad: str, evren_adi: str, tablo_yolu, analiz_bas, holdout: bool = False):
    from motor.arastirma import saglamlik_portfoy as sp
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.portfoy.motor import portfoy_backtest
    evren = sabit.evren_listesi(evren_adi)
    v, f, _ = wep.veri_yukle(evren, "1d")
    if not holdout:                                  # geliştirme aşamaları holdout verisi görürse DUR; holdout modülü bayrakla çağırır
        for s, df in v.items():
            hm.sizinti_kontrol(s, "1d", df, f.get(s))
    evren_t = tuple(v)
    st = hm.varsayilan_pf(ad, evren_t)
    if st is None:
        raise RuntimeError("varsayılan ayar bu evrende uygun değil")
    from motor.arastirma import wf_portfoy as wp
    sec = wp.gerekli_semboller(st, evren_t)
    vv, ff = {s: v[s] for s in sec}, {s: f[s] for s in sec if s in f}
    ay = hm.maliyet_pf(evren_t, 1.0, tablo_yolu)
    hz = sp.RastgeleHazirlik(st, vv)

    def sim(b, tohum):
        r = portfoy_backtest(vv, sp.RastgeleAgirlik(st, hz, [tohum, b, 0]), ay, ff)
        return sharpe_gunluk(pf_gunluk_getiri(r, v, tablo_yolu, analiz_bas).to_numpy())
    return sim


# ============================================================================ satır değerlendirme
def _asama(sim_toplam, gercek, n_sim, tohum, n_gecersiz=0, n_islem=0) -> dict:
    s = np.asarray(sim_toplam, dtype=float)
    return {"B": int(n_sim), "tohum": int(tohum), "p": p_degeri(gercek, s), "sim_ort": float(np.nanmean(s)),
            "sim_std": float(np.nanstd(s, ddof=1)) if np.isfinite(s).sum() > 1 else math.nan,
            "gecersiz_oran": (n_gecersiz / max(1, n_islem)) if n_islem else 0.0}


def b_ikinci(tf: str) -> int:
    return sabit.K2_B2[tf]


def satir_yolu(cikti: Path, ad: str, tf: str) -> Path:
    return Path(cikti) / "test_satir" / f"{ad}--{tf}.json"


def kismi_dizin(cikti: Path, ad: str, tf: str, asama: str) -> Path:
    return Path(cikti) / "test_kismi" / f"{ad}--{tf}--{asama}"


def satir_test(row: dict, cikti: Path, tablo_yolu, tablo_hash: str, son: Optional[float] = None, _ctx=None) -> dict:
    """Elemeyi geçen bir satırın iki aşamalı testi. Satır dosyası aşama bitince yazılır (devam). son: zaman damgası (bütçe):
    dolmuşsa yeni aşama başlatılmaz -> {'ertelendi': True}. _ctx: test için {'ham','gercek','veri_al','cikis_al','destek_yok'}."""
    cikti = Path(cikti)
    ad, tf, evren, stil = row["strateji"], row["tf"], row["evren"], row["stil_v2"]
    yol = satir_yolu(cikti, ad, tf)
    s = json.loads(yol.read_text()) if yol.exists() else None

    def taze():
        return {"strateji": ad, "tf": tf, "evren": evren, "stil_v2": stil, "durum": "bekliyor", "hata": "", "rnd_desteklenmeyen": ""}

    def bitir(**kw):
        s.update(kw)
        kasa.atomik_yaz_json(yol, s)
        return s

    def doldu():
        return son is not None and time.time() > son
    try:
        # B16b: önbellek kararı girdi damgasına bağlıdır (yalnız "dosya var / durum tamam" değil). _ctx (test enjeksiyonu) kimliksizdir.
        damga = "ctx" if _ctx is not None else kasa.girdi_damgasi(cikti, row, (1.0,), "motor/arastirma/v2/test.py")
        if s is not None and not kasa.onbellek_gecerli_mi(s, damga, kasa.SATIR_BITTI):
            kasa.temizle(*(kismi_dizin(cikti, ad, tf, a) for a in ("k2a", "k2b")))      # bayat kısmi sonuçlar yeni girdiyle birleşmesin
            s = None
        if s is None:
            s = taze()
        s[kasa.DAMGA_ANAHTARI] = damga
        if s.get("durum") in kasa.SATIR_BITTI:
            return s
        if stil == "portfoy":
            return _pf_satir_test(row, s, cikti, tablo_yolu, tablo_hash, bitir, doldu, _ctx)
        if _ctx is not None:
            gercek, veri_al, cikis_al, destek_yok = _ctx["gercek"], _ctx["veri_al"], _ctx["cikis_al"], _ctx.get("destek_yok", [])
        else:
            ham, bilgi = hm.ham_yukle(cikti, 1.0, ad, tf, sabit.evren_listesi(evren), tablo_hash, veri_al=hm.veri_oku)
            if bilgi["hatali"] or not ham:
                raise RuntimeError(f"ham sonuç kullanılamaz (hatalı sembol {len(bilgi['hatali'])}, veri {len(ham)})")
            gercek = cakisma_suz(ham, we.analiz_bas_hesapla(bilgi["veri_bas"]))
            veri_al, cikis_al, destek_yok = tek_satir_baglam(ad, tf, tablo_yolu)
        if destek_yok:
            return bitir(durum="rnd_desteklenmeyen", rnd_desteklenmeyen=",".join(sorted(destek_yok)), p=1.0, p1=math.nan, p2=math.nan,
                         asama=0, hata="")
        T = toplam_r(gercek)
        s.update(T=T, n_islem=int(sum(len(d) for d in gercek.values())), n_enstruman=len(gercek))
        for ad_asama, n_sim in (("k2a", sabit.K2_B1), ("k2b", b_ikinci(tf))):
            anahtar = "a1" if ad_asama == "k2a" else "a2"
            if anahtar in s:
                continue
            if ad_asama == "k2b" and not s["a1"]["p"] <= sabit.K2_GECIS_P:
                break
            if doldu():
                return {"ertelendi": True, "strateji": ad, "tf": tf}
            tohum = sabit.satir_tohumu(ad, tf, ad_asama)
            r = k2_simule(gercek, veri_al, cikis_al, n_sim, tohum, kismi_dizin=kismi_dizin(cikti, ad, tf, ad_asama))
            s[anahtar] = _asama(r["toplam_r"], T, n_sim, tohum, r["n_gecersiz"], r["n_islem"])
            s["p1"] = s["a1"]["p"]
            kasa.atomik_yaz_json(yol, s)
        return _final(s, bitir)
    except hm.HoldoutSizintisi:
        raise                                                # ASLA yutulmaz
    except hm.DamgaUyusmazligi as e:                         # bayat/damgasız girdi: KALICI hata satırı yazılmaz; girdi yenilenince yeniden denenir
        return {"ertelendi": True, "neden": str(e), "damga": True, "strateji": ad, "tf": tf}
    except (FileNotFoundError, ValueError, RuntimeError, KeyError) as e:   # satır "hata" olur ve sayılır (0.5)
        if isinstance(e, RuntimeError) and "bitmemiş" in str(e):
            return {"ertelendi": True, "neden": str(e), "strateji": ad, "tf": tf}
        return bitir(durum="hata", hata=f"{type(e).__name__}: {e}"[:300], p=1.0, asama=0)


def _final(s: dict, bitir) -> dict:
    """Nihai p: 2. aşama varsa yalnız ondan; yoksa 1. aşamadan (p > geçiş eşiği)."""
    son_p = s["a2"]["p"] if "a2" in s else s["a1"]["p"]
    if not math.isfinite(son_p):
        return bitir(durum="hata", hata="p hesaplanamadı (T sonlu değil)", p=1.0, asama=0)
    if "a2" in s:
        return bitir(durum="tamam", p=s["a2"]["p"], p1=s["a1"]["p"], p2=s["a2"]["p"], asama=2, hata="")
    return bitir(durum="tamam", p=s["a1"]["p"], p1=s["a1"]["p"], p2=math.nan, asama=1, hata="")


def _pf_satir_test(row, s, cikti, tablo_yolu, tablo_hash, bitir, doldu, ctx) -> dict:
    ad, tf, evren = row["strateji"], row["tf"], row["evren"]
    if ctx is not None:
        gercek_sharpe, analiz_bas, simulator = ctx["gercek_sharpe"], ctx.get("analiz_bas"), ctx.get("simulator")
    else:
        g1, m1 = hm.pf_yukle(cikti, 1.0, ad, tablo_hash, pf_veri_al=hm.pf_veri_oku, evren_adi=evren)
        if g1 is None:
            return bitir(durum="hata", hata=f"portföy koşusu hata: {m1.get('hata')}", p=1.0, asama=0)
        analiz_bas = we.analiz_bas_hesapla({k: pd.Timestamp(t) for k, t in m1["veri_bas_sembol"].items()})
        x = g1[pd.DatetimeIndex(g1["gun"]) >= analiz_bas]
        gercek_sharpe, simulator = sharpe_gunluk(x["getiri"].to_numpy(dtype=float)), None
    s.update(T=gercek_sharpe, n_islem=0, n_enstruman=0)
    for ad_asama, n_sim in (("k2a", sabit.K2_B1), ("k2b", b_ikinci(tf))):
        anahtar = "a1" if ad_asama == "k2a" else "a2"
        if anahtar in s:
            continue
        if ad_asama == "k2b" and not s["a1"]["p"] <= sabit.K2_GECIS_P:
            break
        if doldu():
            return {"ertelendi": True, "strateji": ad, "tf": tf}
        tohum = sabit.satir_tohumu(ad, tf, ad_asama)
        sims = pf_k2_simule(ad, evren, tablo_yolu, analiz_bas, n_sim, tohum, kismi_dizin(cikti, ad, tf, ad_asama), simulator)
        s[anahtar] = _asama(sims, gercek_sharpe, n_sim, tohum)
        kasa.atomik_yaz_json(satir_yolu(cikti, ad, tf), s)
    return _final(s, bitir)


# ============================================================================ aşama
_AYAR: dict = {}


def _baslat(ayar: dict):
    we.veri_ayarla(ayar.get("veri_dizini"), sabit.DONEM)
    _AYAR.clear()
    _AYAR.update(ayar)


def _isci(g: dict):
    return satir_test(g["row"], Path(_AYAR["cikti"]), _AYAR["tablo_yolu"], _AYAR["tablo_hash"], _AYAR.get("son"))


def eleme_oku(cikti: Path, havuz: pd.DataFrame) -> pd.DataFrame:
    """eleme.csv (ve özeti) önceki aşamanın çıktısıdır; yoksa/uyuşmuyorsa açık hata."""
    cikti = Path(cikti)
    yol, oz = cikti / "eleme.csv", cikti / "eleme_ozet.json"
    if not yol.exists() or not oz.exists():
        raise RuntimeError(f"eleme.csv / eleme_ozet.json yok: önce eleme aşaması ({cikti})")
    if json.loads(oz.read_text()).get("eleme_csv_sha256") != kasa.sha256(yol):
        raise RuntimeError("eleme.csv eleme_ozet.json'daki sha256 ile uyuşmuyor")
    d = pd.read_csv(yol)
    anahtar = set(zip(havuz["strateji"], havuz["tf"]))
    if set(zip(d["strateji"], d["tf"])) != anahtar or len(d) != len(havuz):
        raise RuntimeError("eleme.csv satırları havuzla uyuşmuyor")
    return d


def test_asamasi(cikti: Path = None, surec: int = sabit.SUREC_VARSAYILAN, butce_sn: Optional[float] = None, havuz_yolu=None,
                 muhur_yolu=None, ilerleme: bool = True, spa_hesapla: bool = True) -> dict:
    cikti = Path(cikti or sabit.CIKTI)
    kasa.yazma_engeli(cikti)
    muhur = hm.havuz_muhru_dogrula(havuz_yolu, muhur_yolu)
    havuz = hm.havuz_oku(havuz_yolu)
    el = eleme_oku(cikti, havuz).set_index(["strateji", "tf"])
    from motor.arastirma.v2 import maliyet
    tablo = maliyet.tablo_yolu(cikti)
    if not tablo.exists():
        raise RuntimeError(f"v2 maliyet tablosu yok: {tablo}")
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    we.veri_ayarla(None, sabit.DONEM)                             # planlama de veri özetini bu dönemden hesaplar (işçilerle aynı)
    gorev = []
    for _, row in havuz.iterrows():
        if el.loc[(row["strateji"], row["tf"]), "durum"] != "gecti":
            continue
        s = satir_yolu(cikti, row["strateji"], row["tf"])
        r = {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}
        if kasa.satir_bitti_mi(cikti, s, r, (1.0,), "motor/arastirma/v2/test.py", kasa.SATIR_BITTI):     # B16b: damga-duyarlı devam
            continue
        gorev.append({"row": r})
    if ilerleme:
        print(f"[v2 test] {len(havuz)} satır, elemeyi geçen testte {len(gorev)} bekliyor", flush=True)
    ayar = {"cikti": str(cikti), "tablo_yolu": str(tablo), "tablo_hash": tablo_hash}
    sonuc = we.havuz_calistir(_isci, gorev, surec, _baslat, ayar, butce_sn, ilerleme, "v2 test")
    bekleyen = sum(1 for x in sonuc if x.get("ertelendi"))
    if bekleyen:
        ozet = {"satir": len(havuz), "bekleyen": bekleyen, "neden": next((x.get("neden") for x in sonuc if x.get("neden")), "bütçe doldu")}
        if ilerleme:
            print(f"[v2 test] TAMAMLANMADI: {ozet}", flush=True)
        return ozet
    ozet = rapor_yaz(cikti, havuz, el, muhur, tablo_hash)
    if spa_hesapla:
        spa_ozet = spa_asamasi(cikti, havuz, tablo, tablo_hash, butce_sn, ilerleme)
        ozet["spa"] = spa_ozet
        o = json.loads((cikti / "test_ozet.json").read_text())
        o["spa"] = spa_ozet
        kasa.atomik_yaz_json(cikti / "test_ozet.json", o)
    if ilerleme:
        print(f"[v2 test] {ozet}", flush=True)
    return ozet


def rapor_yaz(cikti: Path, havuz: pd.DataFrame, el: pd.DataFrame, muhur: dict, tablo_hash: str) -> dict:
    """Tüm satır sonuçları tamsa: p'ler (elenen/hata/testsiz = 1), BH (m mühürden), BY (rapor) -> test.csv + test_ozet.json."""
    satirlar, p = [], {}
    for _, row in havuz.iterrows():
        ad, tf = row["strateji"], row["tf"]
        e = el.loc[(ad, tf)]
        r = {"strateji": ad, "stil_v2": row["stil_v2"], "tf": tf, "evren": row["evren"]}
        for c in ("etiket", "alt_etiket", "kume_no", "kilit_gorulmus"):
            r[c] = row.get(c)
        r["eleme_durum"] = e["durum"]
        if e["durum"] != "gecti":
            r.update(test_durum="elendi" if e["durum"] == "elendi" else "hata", p=1.0, p1=math.nan, p2=math.nan, asama=0,
                     hata=e.get("hata", "") if isinstance(e.get("hata", ""), str) else "")
        else:
            s = json.loads(satir_yolu(cikti, ad, tf).read_text())
            r.update(test_durum=s["durum"], p=s["p"], p1=s.get("p1", math.nan), p2=s.get("p2", math.nan), asama=s.get("asama", 0),
                     hata=s.get("hata", ""), T=s.get("T", math.nan), n_islem=s.get("n_islem", math.nan),
                     rnd_desteklenmeyen=s.get("rnd_desteklenmeyen", ""))
            if "a1" in s:
                r.update(B1=s["a1"]["B"], sim_ort=s["a1"]["sim_ort"], sim_std=s["a1"]["sim_std"], gecersiz_oran=s["a1"]["gecersiz_oran"])
            if "a2" in s:
                r.update(B2=s["a2"]["B"], sim_ort=s["a2"]["sim_ort"], sim_std=s["a2"]["sim_std"], gecersiz_oran=s["a2"]["gecersiz_oran"])
        satirlar.append(r)
        p[f"{ad}|{tf}"] = float(r["p"])
    m = int(muhur["m"])
    bh, by = bh_kesif(p, m), by_kesif(p, m)
    for r in satirlar:
        k = f"{r['strateji']}|{r['tf']}"
        r.update(bh_sira=bh["sira"][k], bh_esik=bh["esik"][k], kesif=k in set(bh["kesif"]), by_kesif=k in set(by["kesif"]))
    df = pd.DataFrame(satirlar)
    yol = Path(cikti) / "test.csv"
    gecici = yol.with_suffix(".tmp")
    df.to_csv(gecici, index=False)
    gecici.replace(yol)
    ozet = {"satir": len(df), "m": m, "k_yildiz": bh["k_yildiz"], "kesif": [k for k in bh["kesif"]], "by_k_yildiz": by["k_yildiz"],
            "test_edilen": int((df["test_durum"].isin(["tamam"])).sum()), "ikinci_asama": int((df["asama"] == 2).sum()),
            "hata": int((df["test_durum"] == "hata").sum()), "desteklenmeyen": int((df["test_durum"] == "rnd_desteklenmeyen").sum()),
            "test_csv_sha256": kasa.sha256(yol), "eleme_csv_sha256": kasa.sha256(Path(cikti) / "eleme.csv"),
            "havuz_csv_sha256": muhur["havuz_csv_sha256"], "maliyet_tablosu_sha256": tablo_hash}
    kasa.atomik_yaz_json(Path(cikti) / "test_ozet.json", ozet)
    return ozet


# ============================================================================ 5.5 SPA (yalnız rapor)
def spa_asamasi(cikti: Path, havuz: pd.DataFrame, tablo, tablo_hash: str, butce_sn: Optional[float], ilerleme: bool) -> dict:
    """Havuzun TÜM satırlarının günlük MTM getirisi (sıfıra karşı). Ham sonucu olmayan/hatalı satır hariç tutulur ve sayılır.
    Satır serisi gunluk/ önbelleğine yazılır (devam edilebilir); bütçe dolarsa {'durum': 'bekliyor'}."""
    from motor.arastirma.v2 import spa
    son = time.time() + butce_sn if butce_sn else None
    seriler, atlanan = {}, []
    for _, row in havuz.iterrows():
        if son is not None and time.time() > son:
            return {"durum": "bekliyor", "neden": "bütçe doldu"}
        try:
            seriler[f"{row['strateji']}|{row['tf']}"] = kasa.satir_gunluk(cikti, row.to_dict(), tablo, tablo_hash)
        except (RuntimeError, ValueError, KeyError, FileNotFoundError) as e:
            atlanan.append(f"{row['strateji']}|{row['tf']}: {str(e)[:80]}")
    if not seriler:
        return {"durum": "yok", "atlanan": len(atlanan)}
    r = spa.hansen_spa(seriler, tohum=sabit.satir_tohumu("havuz", "1d", "boot"))
    r.update(durum="tamam", atlanan=len(atlanan), atlanan_ornek=atlanan[:3])
    r["ilk_satir"] = sabit.SPA_RAPOR_METNI if r["p"] > sabit.SPA_RAPOR_ESIK_P else ""
    return r
