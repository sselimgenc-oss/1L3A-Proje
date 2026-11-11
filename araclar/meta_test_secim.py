"""Seçim yöntemi meta-testi ("seçim rastgele mi?") — ON_KAYIT_META.md'nin birebir uygulaması.

Bu betik strateji SEÇMEZ; seçim vekilimizin (geriye bakış kapıları + t-istatistiği puanı) rastgeleden iyi olup olmadığını
11 örtüşmeyen 6 aylık pencerede ölçer. Tüm eşikler/kesimler/kural aşağıda sabit ve ön kayıtlıdır; koşudan sonra değişmez.
Tarihi >= 2025-11-08 olan hiçbir veri kullanılmaz (yüklemede süzülür, sonda sert doğrulanır). Tohum 20261111. Tek koşu.

Kullanım: python araclar/meta_test_secim.py   (çıktı: sonuclar/evren/meta_test/)
"""
from __future__ import annotations

import hashlib
import io
import itertools
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]

# ============================================================================ ön kayıtlı sabitler (ON_KAYIT_META.md)
TOHUM = 20261111
HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")     # bu tarih ve sonrası HİÇ kullanılmaz
ILK_KESIM = pd.Timestamp("2020-05-08", tz="UTC")
KESIM_SAYISI = 11
PENCERE_AY = 6
MIN_SERI_GUN = 730
G1_PF_MIN = 1.2
G2_YILLIK_ISLEM = 27.0
YIL_GUN = 365.25
ILK_N = 10
MIN_S = 3
KARAR_ESIK_PUAN = 5.0
KARAR_ESIK_P = 0.10
RASTGELE_CEKIM = 10000
GLOBAL_BAS = pd.Timestamp("2017-01-01", tz="UTC")     # yoğun günlük dizilerin başlangıcı (teknik)
EPS = 1e-9
# t dağılımı, tek yönlü 0.95 (= iki yönlü %90) kritik değerler, sd = df 1..10 (scipy yok; standart tablo)
T95 = {1: 6.313752, 2: 2.919986, 3: 2.353363, 4: 2.131847, 5: 2.015048,
       6: 1.943180, 7: 1.894579, 8: 1.859548, 9: 1.833113, 10: 1.812461}

VERI_ADAYLARI = (KOK / "sonuclar" / "evren" / "v2", Path("/home/user/1L3A-Proje/sonuclar/evren/v2"))
V1_OOS_ADAYLARI = (KOK / "sonuclar" / "evren" / "2017_gelistirme" / "oos",
                   Path("/home/user/1L3A-Proje/sonuclar/evren/2017_gelistirme/oos"))
CIKTI = KOK / "sonuclar" / "evren" / "meta_test"

_MAKS_TARIH = [None]     # kullanılan en büyük tarih (sert doğrulama için)


def _gor(ts) -> None:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    if _MAKS_TARIH[0] is None or ts > _MAKS_TARIH[0]:
        _MAKS_TARIH[0] = ts


def maks_tarih_dogrula() -> pd.Timestamp:
    assert _MAKS_TARIH[0] is not None, "hiç tarih kaydedilmedi"
    assert _MAKS_TARIH[0] < HOLDOUT_BAS, f"holdout verisi kullanıldı: {_MAKS_TARIH[0]}"
    return _MAKS_TARIH[0]


def _ns(x) -> np.ndarray:
    """tz'li datetime serisi/indeksi -> int64 ns (UTC)."""
    return pd.DatetimeIndex(x).tz_convert("UTC").tz_localize(None).as_unit("ns").asi8


def _ts_ns(t: pd.Timestamp) -> int:
    return int(t.tz_convert("UTC").tz_localize(None).as_unit("ns").value)


# ============================================================================ kesimler
def kesimleri_uret(ilk: pd.Timestamp = ILK_KESIM, adet: int = KESIM_SAYISI, adim_ay: int = PENCERE_AY,
                   kayma_ay: int = 0) -> list:
    """T_k = ilk + k·adim_ay ay (+ kayma_ay), 00:00 UTC."""
    return [ilk + pd.DateOffset(months=k * adim_ay + kayma_ay) for k in range(adet)]


def pencere_sonu(T: pd.Timestamp, ay: int = PENCERE_AY) -> pd.Timestamp:
    """Ölçüm penceresi [T, T + ay takvim ayı) -> hariç bitiş. Holdout'a taşamaz."""
    son = T + pd.DateOffset(months=ay)
    assert son <= HOLDOUT_BAS, f"pencere holdout'a taşıyor: {T} + {ay} ay = {son}"
    return son


# ============================================================================ strateji verisi
@dataclass
class SData:
    ad: str
    tf: str
    etiket: str
    analiz_bas: pd.Timestamp
    gunluk: np.ndarray          # GLOBAL_BAS'tan itibaren yoğun günlük R (x2, eksik gün = 0), uzunluk = HOLDOUT_BAS'a kadar gün
    g2: np.ndarray              # x2 işlemleri: giriş ns
    c2: np.ndarray              # çıkış ns
    r2: np.ndarray              # net R (x2)
    ins2: np.ndarray            # enstrüman kodu
    yil2: np.ndarray            # giriş yılı (UTC)
    g1: np.ndarray              # x1 işlemleri (PF için)
    c1: np.ndarray
    r1: np.ndarray

    @property
    def kimlik(self) -> str:
        return f"{self.ad}|{self.tf}"


def sdata_olustur(ad: str, tf: str, etiket: str, analiz_bas, gunluk: pd.Series, tr2: pd.DataFrame,
                  tr1: pd.DataFrame) -> SData:
    """gunluk: UTC gün indeksli günlük R artışları (x2). tr2: sembol, giris, cikis, r. tr1: giris, cikis, r.
    Tarihi >= HOLDOUT_BAS olan veri varsa AssertionError (yükleyici önceden süzer)."""
    analiz_bas = pd.Timestamp(analiz_bas)
    if analiz_bas.tzinfo is None:
        analiz_bas = analiz_bas.tz_localize("UTC")
    n = int((HOLDOUT_BAS - GLOBAL_BAS).days)
    arr = np.zeros(n, dtype=float)
    if len(gunluk):
        gi = pd.DatetimeIndex(gunluk.index)
        assert gi.max() < HOLDOUT_BAS, "günlük seride holdout tarihi"
        assert gi.min() >= GLOBAL_BAS, "günlük seri GLOBAL_BAS'tan önce"
        _gor(gi.max())
        idx = ((gi.tz_convert("UTC").tz_localize(None).normalize() - GLOBAL_BAS.tz_localize(None)).days).to_numpy()
        np.add.at(arr, idx, gunluk.to_numpy(dtype=float))
    for df in (tr2, tr1):
        if len(df):
            assert pd.DatetimeIndex(df["giris"]).max() < HOLDOUT_BAS and pd.DatetimeIndex(df["cikis"]).max() < HOLDOUT_BAS, \
                "işlem tarihinde holdout"
            _gor(pd.DatetimeIndex(df["cikis"]).max())
    if len(tr2):
        kod = pd.factorize(tr2["sembol"].to_numpy())[0].astype(np.int64)
        yil = pd.DatetimeIndex(tr2["giris"]).tz_convert("UTC").year.to_numpy().astype(np.int64)
        g2, c2 = _ns(tr2["giris"]), _ns(tr2["cikis"])
        r2 = tr2["r"].to_numpy(dtype=float)
    else:
        kod = yil = g2 = c2 = np.zeros(0, dtype=np.int64)
        r2 = np.zeros(0)
    if len(tr1):
        g1, c1, r1 = _ns(tr1["giris"]), _ns(tr1["cikis"]), tr1["r"].to_numpy(dtype=float)
    else:
        g1 = c1 = np.zeros(0, dtype=np.int64)
        r1 = np.zeros(0)
    return SData(ad, tf, etiket, analiz_bas, arr, g2, c2, r2, kod, yil, g1, c1, r1)


def _gun_ofset(t: pd.Timestamp) -> int:
    return int((t.tz_convert("UTC").tz_localize(None).normalize() - GLOBAL_BAS.tz_localize(None)).days)


def _kalan_toplam(kod: np.ndarray, w: np.ndarray) -> float:
    """En yüksek toplamlı grup çıkarılınca kalan toplam (tek grup -> 0; boş -> NaN)."""
    if len(w) == 0:
        return math.nan
    _, inv = np.unique(kod, return_inverse=True)
    s = np.bincount(inv, weights=w)
    return float(s.sum() - s.max())


# ============================================================================ geriye bakış: kapılar + puan
def geriye_bakis(sd: SData, T: pd.Timestamp, lb_bas: pd.Timestamp = None) -> dict:
    """T öncesi (T hariç) veriyle: kapılar G1-G3, puan (t-istatistiği), geriye bakış sd'si. Yalnızca T'den önce KAPANAN işlemler
    ve T'den önceki günlük MTM kullanılır. lb_bas None ise stratejinin analiz başlangıcı."""
    lb = sd.analiz_bas if lb_bas is None else max(lb_bas, sd.analiz_bas)
    out = {"uygun": False, "puan": math.nan, "sd": math.nan, "g1": False, "g2": False, "g3": False, "gecti": False,
           "sum_r": 0.0, "n_islem": 0, "pf": math.nan}
    if (T - sd.analiz_bas).days < MIN_SERI_GUN:
        return out
    o1, o2 = _gun_ofset(lb), _gun_ofset(T)
    a = sd.gunluk[o1:o2]
    n = len(a)
    if n < 2:
        return out
    sdv = float(a.std(ddof=1))
    if not sdv > 0:                       # hiç etkinlik yok: puan/ölçek tanımsız -> uygun sayılmaz
        return out
    out["sd"] = sdv
    out["puan"] = float(a.mean() / sdv * math.sqrt(n))
    out["uygun"] = True
    lb_ns, T_ns = _ts_ns(lb), _ts_ns(T)
    m2 = (sd.g2 >= lb_ns) & (sd.c2 < T_ns)
    m1 = (sd.g1 >= lb_ns) & (sd.c1 < T_ns)
    r2, r1 = sd.r2[m2], sd.r1[m1]
    toplam = float(r2.sum())
    out["sum_r"], out["n_islem"] = toplam, int(m2.sum())
    kazanc, kayip = float(r1[r1 > 0].sum()), float(-r1[r1 < 0].sum())
    if kayip > 0:
        pf = kazanc / kayip
    else:
        pf = math.inf if kazanc > 0 else math.nan
    out["pf"] = pf
    out["g1"] = bool(toplam > 0 and not math.isnan(pf) and pf >= G1_PF_MIN)
    yil_gun = (T - lb).days / YIL_GUN
    out["g2"] = bool(min(int(m1.sum()), int(m2.sum())) >= G2_YILLIK_ISLEM * yil_gun)
    k_ins = _kalan_toplam(sd.ins2[m2], r2)
    k_yil = _kalan_toplam(sd.yil2[m2], r2)
    out["g3"] = bool(not math.isnan(k_ins) and k_ins > 0 and not math.isnan(k_yil) and k_yil > 0)
    out["gecti"] = out["g1"] and out["g2"] and out["g3"]
    return out


def olcum(sd: SData, T: pd.Timestamp, son: pd.Timestamp, lb_sd: float) -> tuple:
    """Pencere [T, son): (ΣR, score). score = ΣR / (lb_sd · √pencere_gün). Veri/işlem yoksa 0."""
    a = sd.gunluk[_gun_ofset(T):_gun_ofset(son)]
    n = len(a)
    s = float(a.sum())
    return s, (s / (lb_sd * math.sqrt(n)) if n > 0 and s != 0.0 else 0.0)


# ============================================================================ istatistik yardımcıları
def yuzdelik_sira(x) -> np.ndarray:
    """0-100 yüzdelik sıra; eşitlikte ortalama sıra. n=1 -> 50."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 1:
        return np.array([50.0])
    r = pd.Series(x).rank(method="average").to_numpy()
    return (r - 1.0) / (n - 1.0) * 100.0


def spearman(a, b) -> float:
    ra = pd.Series(np.asarray(a, dtype=float)).rank(method="average").to_numpy()
    rb = pd.Series(np.asarray(b, dtype=float)).rank(method="average").to_numpy()
    if ra.std() == 0 or rb.std() == 0:
        return math.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def isaret_cevirme(d) -> dict:
    """Kesin işaret çevirme permütasyonu: 2^n desen. p_yukari = P(D̄* >= D̄), p_asagi = P(D̄* <= D̄). Gözlenen desen dahil."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    assert 1 <= n <= 20
    desen = np.arange(2 ** n)[:, None] >> np.arange(n)[None, :] & 1
    isaret = 1.0 - 2.0 * desen
    ort = isaret @ d / n
    gozlenen = float(d.mean())
    return {"dbar": gozlenen, "n": n, "p_yukari": float(np.mean(ort >= gozlenen - EPS)),
            "p_asagi": float(np.mean(ort <= gozlenen + EPS)), "desen": 2 ** n}


def guven_araligi_90(d) -> tuple:
    d = np.asarray(d, dtype=float)
    n = len(d)
    assert (n - 1) in T95, f"t tablosu df={n - 1} için yok"
    h = T95[n - 1] * float(d.std(ddof=1)) / math.sqrt(n)
    m = float(d.mean())
    return m - h, m + h


def karar_etiketi(dbar: float, p_yukari: float, p_asagi: float) -> str:
    if dbar >= KARAR_ESIK_PUAN and p_yukari <= KARAR_ESIK_P:
        return "SEÇİM ÇALIŞIYOR"
    if dbar <= -KARAR_ESIK_PUAN and p_asagi <= KARAR_ESIK_P:
        return "SEÇİM ZARARLI"
    return "RASTGELEDEN AYIRT EDİLEMİYOR"


def s_sec(kimlikler: list, puanlar: dict, gecenler: set, n1: set, ilk_n: int = ILK_N, min_s: int = MIN_S) -> list:
    """S_k: kapıyı geçenlerden puana göre ilk ilk_n; ilk_n'den az geçen varsa hepsi; min_s'ten azsa N1'den puan sırasıyla
    min_s'e tamamla. Eşit puanda kimlik sırası (deterministik)."""
    sirali = sorted(gecenler, key=lambda k: (-puanlar[k], k))
    s = sirali[:ilk_n]
    if len(s) < min_s:
        for k in sorted(n1 - set(s), key=lambda k: (-puanlar[k], k)):
            s.append(k)
            if len(s) >= min_s:
                break
    return s


# ============================================================================ bir kesim şeması
def sema_kos(havuz: list, kesimler: list, ufuk_ay: int = PENCERE_AY, geri_ay: int = None, ilk_n: int = ILK_N,
             rng: np.random.Generator = None) -> dict:
    """Kesimler üzerinde D_k'ları ve ikincilleri hesapla. geri_ay None = genişleyen geriye bakış, değilse kayan (ay)."""
    pencereler, satirlar = [], []
    for T in kesimler:
        son = pencere_sonu(T, ufuk_ay)
        lb_bas = None if geri_ay is None else T - pd.DateOffset(months=geri_ay)
        ucret = []
        for sd in havuz:
            g = geriye_bakis(sd, T, lb_bas)
            if g["uygun"]:
                s_r, sc = olcum(sd, T, son, g["sd"])
                ucret.append((sd, g, s_r, sc))
        assert ucret, f"{T}: uygun strateji yok"
        kim = [u[0].kimlik for u in ucret]
        puan = {u[0].kimlik: u[1]["puan"] for u in ucret}
        gec = {u[0].kimlik for u in ucret if u[1]["gecti"]}
        n1 = {u[0].kimlik for u in ucret if u[1]["sum_r"] > 0}
        score = np.array([u[3] for u in ucret])
        P = yuzdelik_sira(score)
        pmap = dict(zip(kim, P))
        sum_olcum = {u[0].kimlik: u[2] for u in ucret}
        etk = {u[0].kimlik: u[0].etiket for u in ucret}
        S = s_sec(kim, puan, gec, n1, ilk_n)
        assert len(S) > 0, f"{T}: S_k boş"
        assert set(S) <= n1 | gec
        ps = float(np.mean([pmap[k] for k in S]))
        n1l = sorted(n1)
        p_n1 = float(np.mean([pmap[k] for k in n1l]))
        p_n2 = float(P.mean())
        # N3: S'nin etiket dağılımına göre tabakalı N1
        n3 = 0.0
        for e in sorted({etk[k] for k in S}):
            pay = sum(etk[k] == e for k in S) / len(S)
            ev = [pmap[k] for k in n1l if etk[k] == e]
            assert ev, f"{T}: N1'de {e} etiketi yok"
            n3 += pay * float(np.mean(ev))
        ic = spearman([puan[k] for k in kim], score)
        # ölçüm ΣR özetleri (strateji başı)
        ort = lambda ks: float(np.mean([sum_olcum[k] for k in ks])) if len(ks) else math.nan   # noqa: E731
        n1_med = float(np.median([sum_olcum[k] for k in n1l]))
        kalan = [k for k in kim if k not in gec]
        w = {"kesim": str(T.date()), "pencere_son": str((son - pd.Timedelta(days=1)).date()), "n_uygun": len(kim),
             "n_kapi_gecen": len(gec), "n_N1": len(n1), "n_S": len(S), "S": ";".join(S),
             "P_S": ps, "P_N1": p_n1, "P_N2": p_n2, "P_N3": n3,
             "D_N1": ps - p_n1, "D_N2": ps - p_n2, "D_N3": ps - n3, "IC": ic,
             "sumR_S": ort(S), "sumR_N1": ort(n1l), "sumR_N2": ort(kim), "sumR_gecen": ort(sorted(gec)),
             "sumR_kalan": ort(kalan), "sumR_N1_medyan": n1_med, "isabet": bool(ort(S) > n1_med)}
        if rng is not None:
            m = len(S)
            pn = np.array([pmap[k] for k in n1l])
            cek = np.argsort(rng.random((RASTGELE_CEKIM, len(pn))), axis=1)[:, :m]
            ortc = pn[cek].mean(axis=1)
            w["rastgele_p_yukari"] = float((np.sum(ortc >= ps - EPS) + 1) / (RASTGELE_CEKIM + 1))
            w["rastgele_p_asagi"] = float((np.sum(ortc <= ps + EPS) + 1) / (RASTGELE_CEKIM + 1))
        pencereler.append(w)
        for sd, g, s_r, sc in ucret:
            k = sd.kimlik
            satirlar.append({"kesim": str(T.date()), "strateji": sd.ad, "tf": sd.tf, "etiket": sd.etiket, "puan": g["puan"],
                             "g1": g["g1"], "g2": g["g2"], "g3": g["g3"], "kapi_gecti": g["gecti"], "N1": k in n1,
                             "S": k in S, "P": pmap[k], "olcum_sumR": s_r, "olcum_score": sc})
    d1 = [w["D_N1"] for w in pencereler]
    res = {"pencereler": pencereler, "satirlar": satirlar, "D_N1": d1}
    for ad in ("N1", "N2", "N3"):
        d = [w[f"D_{ad}"] for w in pencereler]
        res[f"istatistik_{ad}"] = {**isaret_cevirme(d), "ga90": guven_araligi_90(d) if len(d) >= 2 else (math.nan, math.nan)}
    ic = [w["IC"] for w in pencereler]
    res["ic"] = {**isaret_cevirme(ic)}
    res["isabet"] = int(sum(w["isabet"] for w in pencereler))
    return res


# ============================================================================ veri yükleme (v2)
class DogrulamaHatasi(RuntimeError):
    pass


def veri_kok() -> Path:
    for p in VERI_ADAYLARI:
        if (p / "ham" / "x2").is_dir() and (p / "mtm" / "x2").is_dir():
            return p
    raise DogrulamaHatasi("v2 ham/mtm dizini bulunamadı")


def _oku_parquet(yol: Path, hash_listesi: list) -> pd.DataFrame:
    b = yol.read_bytes()
    hash_listesi.append((yol.name, hashlib.sha256(b).hexdigest()))
    return pd.read_parquet(io.BytesIO(b))


def _ham_suz(h: pd.DataFrame, bilgi: dict) -> pd.DataFrame:
    """Yüklemede süz: çıkışı veya girişi >= HOLDOUT_BAS olan işlemler atılır (orijinal satır sırası islem_no için korunur)."""
    h = h.copy()
    h["islem_no"] = np.arange(len(h), dtype=np.int64)
    kes = (pd.DatetimeIndex(h["cikis_zamani"]) >= HOLDOUT_BAS) | (pd.DatetimeIndex(h["giris_zamani"]) >= HOLDOUT_BAS)
    bilgi["atilan_islem"] += int(kes.sum())
    return h[~np.asarray(kes)]


def _strateji_yukle(ad: str, tf: str, etiket: str, analiz_bas: pd.Timestamp, kok: Path, idx: dict, bilgi: dict,
                    hashler: list) -> SData:
    ons = f"{ad}--{tf}--"
    f2, fm, f1 = (idx["ham2"].get(ons, []), idx["mtm2"].get(ons, []), idx["ham1"].get(ons, []))
    assert f2 and fm and f1, f"{ad}|{tf}: dosya eksik"
    gun_parcalari, t2, t1 = [], [], []
    for yol in f2:
        sembol = yol.stem[len(ons):]
        h = _ham_suz(_oku_parquet(yol, hashler), bilgi)
        myol = kok / "mtm" / "x2" / yol.name
        assert myol.exists(), f"mtm yok: {myol.name}"
        m = _oku_parquet(myol, hashler)
        bilgi["atilan_mtm_satiri"] += int((pd.DatetimeIndex(m["gun"]) >= HOLDOUT_BAS).sum())
        m = m[~np.asarray(pd.DatetimeIndex(m["gun"]) >= HOLDOUT_BAS)]
        if len(m):
            assert (pd.DatetimeIndex(m["gun"]).tz_convert("UTC") == pd.DatetimeIndex(m["gun"]).tz_convert("UTC").normalize()).all()
            _gor(pd.DatetimeIndex(m["gun"]).max())
        if len(h):
            _gor(pd.DatetimeIndex(h["cikis_zamani"]).max())
        # sadakat: her kapanan işlemin son kum_r'si net r'ye eşit (tolerans 1e-4)
        if len(h):
            son = m.sort_values(["islem_no", "gun"]).groupby("islem_no")["kum_r"].last().astype(float)
            son = son.reindex(h["islem_no"].to_numpy())
            fark = np.abs(son.to_numpy() - h["r"].to_numpy(dtype=float))
            if np.isnan(fark).any() or fark.max() > 1e-4:
                raise DogrulamaHatasi(f"kum_r != r: {yol.name} max fark {np.nanmax(fark) if not np.isnan(fark).all() else 'NaN'}"
                                      f" (NaN: {int(np.isnan(fark).sum())})")
            bilgi["kum_r_kontrol_islem"] += len(h)
            bilgi["kum_r_max_fark"] = max(bilgi["kum_r_max_fark"], float(fark.max()))
            fon = h["fonlama_r"].to_numpy(dtype=float) != 0
            bilgi["fonlama_sifir_degil"] += int(fon.sum())
            bilgi["fonlama_r_ayrica_eklenirse_uyumsuz"] += int(
                (np.abs(son.to_numpy() - (h["r"].to_numpy(dtype=float) + h["fonlama_r"].to_numpy(dtype=float)))[fon] > 1e-4).sum())
        # günlük artışlar: kum_r farkı (ilk gün = kum_r); yalnız analiz başlangıcından sonra girilen işlemler
        giris = pd.Series(pd.DatetimeIndex(h["giris_zamani"]), index=h["islem_no"].to_numpy())
        gecerli_no = giris.index[(giris >= analiz_bas).to_numpy()]
        mm = m[m["islem_no"].isin(gecerli_no)].sort_values(["islem_no", "gun"])
        if len(mm):
            kr = mm["kum_r"].to_numpy(dtype=float)
            once = mm.groupby("islem_no")["kum_r"].shift(1).to_numpy(dtype=float)
            inc = kr - np.where(np.isnan(once), 0.0, once)
            gun_parcalari.append(pd.Series(inc, index=pd.DatetimeIndex(mm["gun"]).tz_convert("UTC")))
        hh = h[(pd.DatetimeIndex(h["giris_zamani"]) >= analiz_bas)]
        t2.append(pd.DataFrame({"sembol": sembol, "giris": hh["giris_zamani"].to_numpy(), "cikis": hh["cikis_zamani"].to_numpy(),
                                "r": hh["r"].to_numpy(dtype=float)}))
    for yol in f1:
        h = _ham_suz(_oku_parquet(yol, hashler), bilgi)
        hh = h[(pd.DatetimeIndex(h["giris_zamani"]) >= analiz_bas)]
        t1.append(pd.DataFrame({"giris": hh["giris_zamani"].to_numpy(), "cikis": hh["cikis_zamani"].to_numpy(),
                                "r": hh["r"].to_numpy(dtype=float)}))
    gunluk = pd.concat(gun_parcalari) if gun_parcalari else pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    gunluk = gunluk.groupby(level=0).sum()
    tr2 = pd.concat(t2, ignore_index=True)
    tr1 = pd.concat(t1, ignore_index=True)
    for df in (tr2, tr1):
        for c in ("giris", "cikis"):
            df[c] = pd.to_datetime(df[c], utc=True)
    return sdata_olustur(ad, tf, etiket, analiz_bas, gunluk, tr2, tr1)


def v2_havuz_yukle() -> tuple:
    kok = veri_kok()
    eleme = pd.read_csv(kok / "eleme.csv")
    eleme_h = eleme[eleme["durum"] != "hata"].copy()
    idx = {"ham2": {}, "mtm2": {}, "ham1": {}}
    for anahtar, alt in (("ham2", "ham/x2"), ("mtm2", "mtm/x2"), ("ham1", "ham/x1")):
        for p in sorted((kok / alt).glob("*.parquet")):
            ad, tf, _ = p.stem.split("--", 2)
            idx[anahtar].setdefault(f"{ad}--{tf}--", []).append(p)
    bilgi = {"atilan_islem": 0, "atilan_mtm_satiri": 0, "kum_r_kontrol_islem": 0, "kum_r_max_fark": 0.0,
             "fonlama_sifir_degil": 0, "fonlama_r_ayrica_eklenirse_uyumsuz": 0, "veri_kok": str(kok)}
    hashler, havuz, dosyasiz = [], [], []
    for _, r in eleme_h.iterrows():
        ons = f"{r['strateji']}--{r['tf']}--"
        if not (idx["ham2"].get(ons) and idx["mtm2"].get(ons) and idx["ham1"].get(ons)):
            dosyasiz.append(f"{r['strateji']}|{r['tf']}")
            continue
        havuz.append(_strateji_yukle(r["strateji"], r["tf"], r["etiket"], pd.Timestamp(r["analiz_bas"]), kok, idx, bilgi, hashler))
    bilgi["eleme_satiri_hata_disi"] = int(len(eleme_h))
    bilgi["havuz_n"] = len(havuz)
    bilgi["dosyasiz_satir_n"] = len(dosyasiz)
    bilgi["dosyasiz_satirlar"] = dosyasiz
    bilgi["dosya_hash_ozeti"] = hashlib.sha256(json.dumps(sorted(hashler)).encode()).hexdigest()
    bilgi["okunan_dosya_n"] = len(hashler)
    return havuz, eleme, bilgi


# ============================================================================ veri yükleme (v1 havuzu, dayanıklılık)
def v1_oos_dizini() -> Path:
    for p in V1_OOS_ADAYLARI:
        if p.is_dir():
            return p
    raise DogrulamaHatasi("v1 oos dizini bulunamadı")


def v1_havuz_yukle() -> tuple:
    """Her `strateji--tf.parquet`: kabul == True işlemleri, pnl (hesap kesri; R yerine) üzerinden. Günlük seri: pnl'nin ÇIKIŞ gününe
    toplamı. Analiz başlangıcı = dosyadaki oos_bas. PF(x1) için aynı pnl kullanılır."""
    kok = v1_oos_dizini()
    havuz, hashler, atilan = [], [], 0
    for p in sorted(kok.glob("*.parquet")):
        d = _oku_parquet(p, hashler)
        d = d[d["kabul"].to_numpy(dtype=bool)]
        kes = (pd.DatetimeIndex(d["giris"]) >= HOLDOUT_BAS) | (pd.DatetimeIndex(d["cikis"]) >= HOLDOUT_BAS)
        atilan += int(kes.sum())
        d = d[~np.asarray(kes)]
        if not len(d):
            continue
        ad, tf = p.stem.rsplit("--", 1)
        bas = pd.Timestamp(d["oos_bas"].iloc[0])
        if bas.tzinfo is None:
            bas = bas.tz_localize("UTC")
        d = d[pd.DatetimeIndex(d["giris"]) >= bas]
        if not len(d):
            continue
        gun = pd.DatetimeIndex(d["cikis"]).tz_convert("UTC").normalize()
        gunluk = pd.Series(d["pnl"].to_numpy(dtype=float), index=gun).groupby(level=0).sum()
        tr2 = pd.DataFrame({"sembol": d["sembol"].to_numpy(), "giris": d["giris"].to_numpy(), "cikis": d["cikis"].to_numpy(),
                            "r": d["pnl"].to_numpy(dtype=float)})
        tr1 = tr2[["giris", "cikis", "r"]]
        for df in (tr2, tr1):
            for c in ("giris", "cikis"):
                df[c] = pd.to_datetime(df[c], utc=True)
        havuz.append(sdata_olustur(ad, tf, "v1", bas, gunluk, tr2, tr1))
    return havuz, {"v1_dizin": str(kok), "v1_havuz_n": len(havuz), "v1_atilan_islem": atilan,
                   "v1_dosya_hash_ozeti": hashlib.sha256(json.dumps(sorted(hashler)).encode()).hexdigest()}


# ============================================================================ sadakat kontrolü
def sadakat(havuz: list, eleme: pd.DataFrame, test: pd.DataFrame) -> dict:
    """T = 2025-11-08 (tam geliştirme verisi): G1-G3 geçenler vs gerçek 18 `gecti` satırı; Spearman(puan, -p)."""
    T = HOLDOUT_BAS
    gec, puan = {}, {}
    for sd in havuz:
        g = geriye_bakis(sd, T, None)
        if g["uygun"]:
            puan[sd.kimlik] = g["puan"]
            if g["gecti"]:
                gec[sd.kimlik] = g["puan"]
    gercek = set(f"{r.strateji}|{r.tf}" for r in eleme.itertuples() if r.durum == "gecti")
    pool_ids = {sd.kimlik for sd in havuz}
    kesisim = set(gec) & gercek
    out = {"vekil_gecen_n": len(gec), "gercek_gecti_n": len(gercek), "gercek_gecti_havuzda_n": len(gercek & pool_ids),
           "kesisim_n": len(kesisim), "yalniz_vekil": sorted(set(gec) - gercek), "yalniz_gercek": sorted(gercek - set(gec)),
           "jaccard": len(kesisim) / len(set(gec) | gercek) if (set(gec) | gercek) else math.nan}
    pm = {f"{r.strateji}|{r.tf}": r.p for r in test.itertuples() if not (isinstance(r.p, float) and math.isnan(r.p))}
    ks = [k for k in gec if k in pm]
    out["spearman_puan_eksi_p_n"] = len(ks)
    out["spearman_puan_eksi_p"] = spearman([gec[k] for k in ks], [-pm[k] for k in ks]) if len(ks) >= 3 else None
    ks2 = [k for k in kesisim if k in pm]
    out["spearman_kesisim_n"] = len(ks2)
    out["spearman_kesisim"] = spearman([gec[k] for k in ks2], [-pm[k] for k in ks2]) if len(ks2) >= 3 else None
    return out


# ============================================================================ çıktılar
def _sade(o):
    if isinstance(o, dict):
        return {str(k): _sade(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sade(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) or (isinstance(o, np.floating) and np.isnan(o)) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _sha(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(KOK), *args], check=True, capture_output=True, text=True).stdout.strip()


def _f(x, n=2):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


UYGULAMA_NOTLARI = [
    "ΣR(×2), PF(×1), kapanan işlem sayısı, en iyi enstrüman/yıl çıkarma: yalnız T_k'den ÖNCE KAPANAN (çıkış < T_k) işlemler, "
    "girişi analiz başlangıcından sonra olanlar (sıkı okuma, ileriye sızıntı yok). En iyi yıl = giriş yılı (UTC), eleme.py ile aynı.",
    "G2 sayacı: x1 ve x2 kapanan işlem sayısının küçüğü (sıkı okuma). Geriye bakış yılı = (T_k − geriye bakış başı) gün / 365,25.",
    "Günlük seri (puan, sd, pencere ΣR): mtm kum_r farkı, işlem+enstrüman toplamı, eksik gün = 0; analiz başlangıcından sonra "
    "girilen işlemler; T_k'den önce başlayıp sonra bitenlerin günlük artışları ilgili güne yazılır (takvim günü sayısıyla: "
    "geriye bakışta takvim günü, pencerede takvim günü). sd: ddof=1 (takvim günleri üzerinden).",
    "Geriye bakış günlük sd'si 0 olan (hiç etkinlik yok) strateji 'uygun' sayılmaz (puan/ölçek tanımsız); N2 bu uygunlar üzerindedir.",
    "P_i,k = (ortalama sıra − 1)/(n − 1) × 100 (0–100 aralığı; eşitlikte ortalama sıra). N2'ye karşı D_k bu yüzden = ort P(S_k) − 50.",
    "Havuz: eleme.csv'de durum != hata VE ham x1, ham x2 ve mtm x2 dosyası olan satırlar. Portföy (pf__) satırlarının mtm dosyası "
    "yoktur; MTM serisi kurulamadığı için dışarıda (sıkı okuma). Bu yüzden havuz beklenen ~212'den küçüktür (bkz. ozet.json).",
    "Yükleme süzgeci: çıkışı ≥ 2025-11-08 olan işlemler (veri sonunda zorla kapananlar) ve gün ≥ 2025-11-08 mtm satırları atılır; "
    "kum_r = r doğrulaması kalan (kapanan) işlemlerde yapılır. Atılan MTM satırlarının öncesindeki günlük artışlar pencerede kalır.",
    "kum_r doğrulaması: son kum_r = net r (tol 1e-4) tüm kapanan işlemlerde sağlandı; fonlama_r ayrıca EKLENMEZ (r'ye zaten dahil).",
    "N3: S_k etiket payları × o etiketin N1 ortalama P'si. N1 ve S_k'de aynı etiketler olduğundan boş tabaka olmaz (S_k ⊂ N1).",
    "Sadakat: Spearman(puan, −p) için test.csv'deki `p` (geliştirme dönemi resmi test p'si) kullanıldı; eleme.csv'de gecti satırlarında "
    "p_ust boş. Yalnız vekil geçenler içinde p'si olanlar üzerinde; ayrıca vekil ∩ gerçek kümesinde.",
    "Pencere içi rastgeleleştirme p: (sayı+1)/(10001) (sıkı); tek rng (tohum 20261111), kesim sırasıyla ana koşuda.",
    "Dayanıklılık: 12 ay ufku = 5 pencere (T_0, T_2, …, T_8 = 2020-05 … 2024-05; kesin işaret çevirme 2^5=32). +3 ay kaydırma = "
    "T_0…T_9 + 3 ay (10 pencere; T_10+3 ay holdout'a taşar, atıldı). 24 ay kayan: geriye bakış = [max(analiz_bas, T−24 ay), T). "
    "v1: kabul==True işlem pnl'i (hesap kesri, R değil); günlük seri pnl'nin çıkış gününe toplamı; PF ve G1–G3 aynı pnl "
    "üzerinden; analiz başlangıcı = oos_bas; etiket yok (yalnız N1'e karşı); 9 pencere (2021-05-08…2025-05-08); "
    "v1 oos verisi 2025-09 civarında biter (sonraki günler 0).",
    "secilenler.csv yalnız seçilenleri değil, her kesimde tüm uygun stratejileri (S bayrağıyla) içerir (kapılar/P/ölçüm için).",
]


def rapor_yaz(yol: Path, oz: dict, kes: list, bilgi: dict) -> None:
    a = oz["ana"]
    L = []
    L += [f"# Seçim meta-testi sonucu: {oz['karar']}", "",
          f"- Karar etiketi: **{oz['karar']}**",
          f"- D̄ (ort. fark, yüzdelik puan): **{_f(a['dbar'])}**",
          f"- p_yukarı: **{_f(a['p_yukari'], 4)}**   p_aşağı: **{_f(a['p_asagi'], 4)}**  (2^11 = 2048 işaret çevirme)",
          f"- %90 GA (t, sd=10): **[{_f(a['ga90'][0])} ; {_f(a['ga90'][1])}]**", "",
          "Kural (önceden yazıldı): D̄ ≥ +5 ve p_yukarı ≤ 0.10 → çalışıyor; D̄ ≤ −5 ve p_aşağı ≤ 0.10 → zararlı; aksi halde "
          "rastgeleden ayırt edilemiyor. Bu test strateji seçmez, seçim YÖNTEMİMİZİN rastgeleden iyi olup olmadığını ölçer.", "",
          "## Pencere başına (ana karşılaştırma: S_k − N1)", "",
          "| kesim | pencere sonu | uygun | kapı geçen | S_k n | P(S) | P(N1) | D_k | S ort ΣR | N1 ort ΣR |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for w in kes:
        L.append(f"| {w['kesim']} | {w['pencere_son']} | {w['n_uygun']} | {w['n_kapi_gecen']} | {w['n_S']} | {_f(w['P_S'])} | "
                 f"{_f(w['P_N1'])} | **{_f(w['D_N1'])}** | {_f(w['sumR_S'])} | {_f(w['sumR_N1'])} |")
    L += ["", f"D_k pozitif pencere sayısı: {sum(w['D_N1'] > 0 for w in kes)} / {len(kes)}.", "",
          "## Sadakat kontrolü (yalnız rapor)", "",
          "T = 2025-11-08'de tam geliştirme verisiyle vekilin kapıları, gerçek `gecti` (18) satırlarıyla karşılaştırıldı.", ""]
    s = oz["sadakat"]
    L += [f"- Vekil kapıyı geçen: {s['vekil_gecen_n']}; gerçek gecti: {s['gercek_gecti_n']} (havuzda {s['gercek_gecti_havuzda_n']}); "
          f"örtüşen: **{s['kesisim_n']}**; Jaccard {_f(s['jaccard'])}.",
          f"- Yalnız vekilde: {', '.join(s['yalniz_vekil']) or '—'}",
          f"- Yalnız gerçekte: {', '.join(s['yalniz_gercek']) or '—'}",
          f"- Spearman(puan, −p) vekil geçenler (n={s['spearman_puan_eksi_p_n']}): {_f(s['spearman_puan_eksi_p'])}; "
          f"kesişimde (n={s['spearman_kesisim_n']}): {_f(s['spearman_kesisim'])}", ""]
    L += ["## İkincil sonuçlar (ikincil, kararı değiştirmez)", ""]
    for ad in ("N2", "N3"):
        x = oz["ikincil"][f"istatistik_{ad}"]
        L.append(f"- D̄ vs {ad}: {_f(x['dbar'])}; p_yukarı {_f(x['p_yukari'], 4)}; p_aşağı {_f(x['p_asagi'], 4)}; "
                 f"%90 GA [{_f(x['ga90'][0])} ; {_f(x['ga90'][1])}]")
    x = oz["ikincil"]["ic"]
    L.append(f"- Sıra IC (geriye bakış puanı ↔ ölçüm puanı), ortalama {_f(x['dbar'], 3)}; p_yukarı {_f(x['p_yukari'], 4)}; "
             f"p_aşağı {_f(x['p_asagi'], 4)}")
    L.append(f"- İsabet (S ort ΣR > N1 medyanı): {oz['ikincil']['isabet']} / {len(kes)}")
    sr = oz["ikincil"]["ort_sumR"]
    L.append(f"- Strateji başı ort. ölçüm ΣR(×2) (pencereler ortalaması): S {_f(sr['S'])}; N1 {_f(sr['N1'])}; N2 {_f(sr['N2'])}; "
             f"kapıyı geçen {_f(sr['gecen'])}; kalan {_f(sr['kalan'])}")
    rp = [w.get("rastgele_p_yukari") for w in kes]
    L += ["", "Pencere içi rastgeleleştirme p_yukarı (N1'den aynı boyutta 10.000 çekiliş): " +
          ", ".join(f"{w['kesim']}: {_f(w['rastgele_p_yukari'], 3)}" for w in kes), "",
          "## Dayanıklılık koşulları (ikincil, kararı değiştirmez; ek örnek sayılmaz)", "",
          "| koşul | pencere | D̄ | p_yukarı | p_aşağı | %90 GA | (kural etiketi, bilgi) |", "|---|---|---|---|---|---|---|"]
    for ad, r in oz["dayaniklilik"].items():
        L.append(f"| {ad} | {r['n']} | {_f(r['dbar'])} | {_f(r['p_yukari'], 4)} | {_f(r['p_asagi'], 4)} | "
                 f"[{_f(r['ga90'][0])} ; {_f(r['ga90'][1])}] | {r['etiket']} |")
    L += ["", "## Yanlılık uyarıları (ön kayıttan)", "",
          "- Evren 2026'da seçildi (hayatta kalan/seçilmiş strateji havuzu): sonradan bakıldığında zaten iyi görünenler var → "
          "yanlılık \"seçim çalışıyor\" yönünde.",
          "- Kapılar (G1–G3 ve eşikleri) geliştirme verisi görüldükten SONRA tasarlandı → yine \"çalışıyor\" yönünde yanlılık.",
          "- Yalnız 11 pencere var, güç düşük: \"ayırt edilemiyor\" kanıt eksikliğidir, \"seçim işe yaramaz\" kanıtı değildir. "
          "Olumsuz bulgu güvenilir, olumlu bulgu indirimle okunur.",
          "- Stratejiler birbirine bağımlı; çıkarım birimi pencere (11 sayı). Strateji başı ya da pencere içi p karara girmez.", "",
          "## Veri ve doğrulama", "",
          f"- Veri kökü: {bilgi['veri_kok']}; havuz: {bilgi['havuz_n']} strateji (eleme.csv hata dışı satır {bilgi['eleme_satiri_hata_disi']}, "
          f"dosyasız {bilgi['dosyasiz_satir_n']}).",
          f"- kum_r = r doğrulaması: {bilgi['kum_r_kontrol_islem']} kapanan işlem, en büyük fark {bilgi['kum_r_max_fark']:.2e} "
          f"(fonlama_r ≠ 0 olan {bilgi['fonlama_sifir_degil']} işlemde r'ye eklenirse uyuşmayan {bilgi['fonlama_r_ayrica_eklenirse_uyumsuz']}: "
          "yani fonlama r'ye dahil).",
          f"- Kullanılan en büyük tarih: {oz['maks_tarih']} (< 2025-11-08 doğrulandı). Süzülen: {bilgi['atilan_islem']} işlem "
          f"(çıkış ≥ 2025-11-08), {bilgi['atilan_mtm_satiri']} mtm satırı.",
          f"- Betik sha256: {oz['girdi_hash']['betik']}; commit: {oz['commit']}.", "",
          "## Uygulama notları", ""]
    L += [f"{i}. {n}" for i, n in enumerate(oz["uygulama_notlari"], 1)]
    yol.write_text("\n".join(L) + "\n", encoding="utf-8")


# ============================================================================ ana akış
def main() -> int:
    CIKTI.mkdir(parents=True, exist_ok=True)
    havuz, eleme, bilgi = v2_havuz_yukle()
    test = pd.read_csv(veri_kok() / "test.csv")
    rng = np.random.default_rng(TOHUM)
    kesimler = kesimleri_uret()
    assert len(kesimler) == 11 and str(kesimler[0].date()) == "2020-05-08" and str(kesimler[-1].date()) == "2025-05-08"
    assert pencere_sonu(kesimler[-1]) == HOLDOUT_BAS
    ana = sema_kos(havuz, kesimler, rng=rng)
    st = ana["istatistik_N1"]
    karar = karar_etiketi(st["dbar"], st["p_yukari"], st["p_asagi"])
    sad = sadakat(havuz, eleme, test)

    dayan = {}

    def kaydet(ad, res, ufuk_not=""):
        s = res["istatistik_N1"]
        dayan[ad] = {"n": s["n"], "dbar": s["dbar"], "p_yukari": s["p_yukari"], "p_asagi": s["p_asagi"], "ga90": s["ga90"],
                     "etiket": karar_etiketi(s["dbar"], s["p_yukari"], s["p_asagi"]), "D": res["D_N1"],
                     "kesimler": [w["kesim"] for w in res["pencereler"]]}
    kaydet("12 aylık ufuk (5 pencere)", sema_kos(havuz, kesimleri_uret(adet=5, adim_ay=12), ufuk_ay=12))
    kaydet("24 aylık kayan geriye bakış", sema_kos(havuz, kesimler, geri_ay=24))
    kaydet("+3 ay kaydırılmış kesimler (10 pencere)", sema_kos(havuz, kesimleri_uret(adet=10, kayma_ay=3)))
    kaydet("ilk 5", sema_kos(havuz, kesimler, ilk_n=5))
    kaydet("ilk 20", sema_kos(havuz, kesimler, ilk_n=20))
    v1, v1b = v1_havuz_yukle()
    kaydet("v1 havuzu (9 pencere, 2021-05-08'den)", sema_kos(v1, kesimleri_uret(ilk=pd.Timestamp("2021-05-08", tz="UTC"), adet=9)))

    maks = maks_tarih_dogrula()
    pw = ana["pencereler"]

    def ort_sumr(anahtar):
        return float(np.nanmean([w[anahtar] for w in pw]))
    oz = {
        "karar": karar,
        "ana": {"dbar": st["dbar"], "p_yukari": st["p_yukari"], "p_asagi": st["p_asagi"], "ga90": st["ga90"],
                "D_k": ana["D_N1"], "n_pencere": st["n"], "permutasyon_sayisi": st["desen"]},
        "ikincil": {"istatistik_N2": ana["istatistik_N2"], "istatistik_N3": ana["istatistik_N3"], "ic": ana["ic"],
                    "isabet": ana["isabet"],
                    "ort_sumR": {"S": ort_sumr("sumR_S"), "N1": ort_sumr("sumR_N1"), "N2": ort_sumr("sumR_N2"),
                                 "gecen": ort_sumr("sumR_gecen"), "kalan": ort_sumr("sumR_kalan")},
                    "rastgele_p_yukari": [w["rastgele_p_yukari"] for w in pw]},
        "dayaniklilik": dayan, "sadakat": sad,
        "maks_tarih": str(maks), "tohum": TOHUM,
        "girdi_hash": {"betik": _sha(Path(__file__)), "eleme_csv": _sha(veri_kok() / "eleme.csv"),
                       "test_csv": _sha(veri_kok() / "test.csv"), "on_kayit_meta": _sha(CIKTI / "ON_KAYIT_META.md"),
                       "v2_dosyalar": bilgi["dosya_hash_ozeti"], "v1_dosyalar": v1b["v1_dosya_hash_ozeti"]},
        "commit": _git("rev-parse", "HEAD"), "veri": {**bilgi, **v1b}, "uygulama_notlari": UYGULAMA_NOTLARI,
    }
    (CIKTI / "ozet.json").write_text(json.dumps(_sade(oz), ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(pw).to_csv(CIKTI / "kesimler.csv", index=False)
    pd.DataFrame(ana["satirlar"]).to_csv(CIKTI / "secilenler.csv", index=False)
    rapor_yaz(CIKTI / "rapor.md", _sade(oz), pw, bilgi)
    print(karar, st["dbar"], st["p_yukari"], st["p_asagi"], st["ga90"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
