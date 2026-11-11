"""BİRLEŞİK HESAP OYNATMASI (GEÇMİŞ; gelecek tahmini DEĞİL). Ön kayıt: sonuclar/canli/BIRLESIK_ON_KAYIT.md (koşudan önce commit, tek koşu).

Her strateji AYRI alt hesap (kasası ayrı; tahsis = 250 ya da 60 USD) mevcut yeniden oynatma makinesiyle oynatılır:
`canli_boyut_yeniden_oynat.oyna` (CANLI_LIMITLER: işlem başı %1,5 [canli_olcum_250_15.RISK], toplam açık stop riski <= %6, brüt <= 1,5x,
günlük -%6 yeni giriş yok, strateji -%30 kalıcı kill, asgari emir tutarı -> atla) IMPORT edilir, kopyalanmaz. Bu araç yalnız (a) v2 ham işlem
listesinden (ham/x1|x2 + günlük MTM kum_r) oyna'nın girdisini kurar, (b) alt hesap eğrilerini birleştirir, (c) ölçüleri hesaplar.

BİRLEŞİK SERİ (günlük, UTC gün sonu; açık pozisyonlar günlük MTM ile dahil):
  K (kasa serisi)  = Σ min(alt hesap özsermayesi, tahsis)   -> canlı hesap kill'in ölçtüğü seri (CANLI_LIMITLER.hesap_kill_guncelle: kasa=min(özsermaye,tahsis));
                      zirve = Σ tahsis (K onu aşamaz). Hesap kill: (zirve-K)/zirve >= %20 -> o gün sonu hepsi kapanır, sonrası DONUK (K ve H sabit).
  H (gerçek hesap) = Σ özsermaye (kâr hesapta kalır, yeniden boyutlanmaz; boyut kasa=min(özsermaye,tahsis) ile sınırlı: oyna'nın dünyası). Net %, H düşüşü bununla.
  Brake/-%15/-%20 oranları K üzerinden (kill ölçüsü), H düşüşü ayrıca raporlanır.
Pencereler: her pencere BAŞTAN başlar (tüm alt hesaplar tahsisle sıfırdan; pencere öncesi giriş yok, pencere sonunda açık işlemler MTM ile değerlenir).
Dönem: <= 2025-11-07 (SERT: HOLDOUT_BAS ve sonrası veri görülürse RuntimeError).
Kullanım:  python araclar/canli_birlesik_oynatma.py [--surec 4] [--sadece-dogrula]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import functools
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import canli_boyut_yeniden_oynat as oy                      # noqa: E402
import canli_olcum_250_15 as olcum                          # noqa: E402
from motor.canli.borsa import canli_limitler as cl          # noqa: E402

HAM_DIZIN = KOK / "sonuclar" / "evren" / "v2" / "ham"
MTM_DIZIN = KOK / "sonuclar" / "evren" / "v2" / "mtm"
CIKTI = KOK / "sonuclar" / "canli"

HOLDOUT_BAS = oy.HOLDOUT_BAS                                # 2025-11-08 UTC: bu tarih ve sonrası okunmaz
SON_GUN = HOLDOUT_BAS - pd.Timedelta(days=1)                # 2025-11-07
BASLANGIC = pd.Timestamp("2018-01-01", tz="UTC")            # ortak başlangıç (kripto verisi 2017-08'den; 2017 yarım yıl -> dışarıda)
HESAP_KILL = cl.CANLI_LIMITLER.hesap_kill_oran              # 0.20
FREN, ASMA15 = 0.10, 0.15
YATAY = (-0.10, 0.10)
EPS = 1e-12
RISK = olcum.RISK                                           # 0.015 (15m ve swing; CANLI_PLAN başlangıç)

K_E0, K_EWO, K_HMA, K_LUBE = "dis__e0v1en", "dis__ewo-ema-ofset", "dis__hma-atr-rider", "dis__lube"
SENARYOLAR = {
    "S1": dict(ad="v2 plani", tahsis={K_EWO: 250.0, K_E0: 60.0}),
    "S2": dict(ad="v2 + trend", tahsis={K_EWO: 250.0, K_E0: 60.0, K_HMA: 250.0, K_LUBE: 250.0}),
    "S3": dict(ad="eski plan", tahsis={K_E0: 250.0, K_EWO: 250.0, K_HMA: 250.0, K_LUBE: 250.0}),
}
MALIYETLER = ("x2", "x1")                                   # x2 ana, x1 ek
DENETIM = dict(senaryo="S2", pencere="Y2022", maliyet="x2")


# =============================================================================================== yardımcılar (saf)
def betik_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def holdout_kontrol(tr: pd.DataFrame, mt: pd.DataFrame, ad: str = "") -> None:
    """HOLDOUT_BAS ve sonrası görünürse KESİN HATA (sessiz kırpma yok)."""
    if len(tr) and tr["giris_zamani"].max() >= HOLDOUT_BAS:
        raise RuntimeError(f"{ad}: holdout sızıntısı (giriş >= {HOLDOUT_BAS})")
    if len(tr) and tr["cikis_zamani"].max() > HOLDOUT_BAS:       # veri_sonu kapanışı = HOLDOUT_BAS anı izinli (oy._gorev ile aynı)
        raise RuntimeError(f"{ad}: holdout sızıntısı (çıkış > {HOLDOUT_BAS})")
    if len(mt) and mt["gun"].max() > HOLDOUT_BAS:                # MTM'nin son günü = veri_sonu kapanışının çıkış günü (HOLDOUT_BAS) izinli; pencereler 11-07'de biter
        raise RuntimeError(f"{ad}: holdout sızıntısı (MTM günü > {HOLDOUT_BAS})")


def pencere_kontrol(bas: pd.Timestamp, bit: pd.Timestamp) -> None:
    if bit >= HOLDOUT_BAS or bit < bas:
        raise RuntimeError(f"pencere geçersiz/holdout: {bas} .. {bit}")


def pencereler() -> list:
    """[(anahtar, tur, bas, bit)] ; bit dahil. TUM, Y12 (yıl başı, tam yıllar), YK (2025 kısmi; istatistik dışı), R6 ve R12 (ayda bir kaydır)."""
    out = [("TUM", "tum", BASLANGIC, SON_GUN)]
    for ay_say, tur in ((6, "R6"), (12, "R12")):
        b = BASLANGIC
        while True:
            bit = b + pd.DateOffset(months=ay_say) - pd.Timedelta(days=1)
            if bit > SON_GUN:
                break
            out.append((f"{tur}_{b.date()}", tur, b, bit))
            if tur == "R12" and b.month == 1:
                out.append((f"Y{b.year}", "Y12", b, bit))
            b = b + pd.DateOffset(months=1)
    out.append(("Y2025K", "YK", pd.Timestamp("2025-01-01", tz="UTC"), SON_GUN))
    for _, _, b, e in out:
        pencere_kontrol(b, e)
    return out


def birlestir(egriler: dict, tahsis: dict, kill_oran: float = HESAP_KILL) -> dict:
    """egriler: {ad: günlük özsermaye dizisi (aynı uzunluk)}, tahsis: {ad: USD}. -> dict(K, H, kill_idx[-1: yok], zirve).
    K = Σ min(e, tahsis); H = Σ e. Hesap kill: (Σtahsis ile ortak zirve) K düşüşü >= kill_oran -> o günden sonra K ve H DONUK."""
    adlar = sorted(egriler)
    n = {len(np.asarray(egriler[a])) for a in adlar}
    if len(n) != 1:
        raise ValueError(f"eğri uzunlukları farklı: {n}")
    K = sum(np.minimum(np.asarray(egriler[a], float), tahsis[a]) for a in adlar)
    H = sum(np.asarray(egriler[a], float) for a in adlar)
    toplam = float(sum(tahsis[a] for a in adlar))
    zirve, kill_idx = toplam, -1
    for i, v in enumerate(K):
        zirve = max(zirve, v)
        if (zirve - v) / zirve >= kill_oran - EPS:
            kill_idx = i
            break
    if kill_idx >= 0:
        K = K.copy()
        H = H.copy()
        K[kill_idx:] = K[kill_idx]
        H[kill_idx:] = H[kill_idx]
    return dict(K=K, H=H, kill_idx=kill_idx, toplam=toplam)


def maks_dusus(seri: np.ndarray, baslangic: float) -> float:
    """Zirveden (başlangıç dahil) en büyük düşüş oranı (pozitif sayı)."""
    zirve, dd = baslangic, 0.0
    for v in seri:
        zirve = max(zirve, v)
        dd = max(dd, (zirve - v) / zirve)
    return float(dd)


def olcu(b: dict) -> dict:
    """Bir birleşik serinin pencere ölçüleri."""
    t = b["toplam"]
    return dict(net=float(b["H"][-1] / t - 1), dd_k=maks_dusus(b["K"], t), dd_h=maks_dusus(b["H"], t),
                kill=bool(b["kill_idx"] >= 0), kill_gun=int(b["kill_idx"]), son_k=float(b["K"][-1]), son_h=float(b["H"][-1]))


def oranlar(rows: list) -> dict:
    """Pencere ölçü listesi -> eşik oranları. fren/asma/kill K düşüşü üzerinden (ve H için ayrıca); yatay/üst/alt H net sonucu."""
    n = len(rows)
    if n == 0:
        return dict(n=0)
    f = lambda c: sum(1 for r in rows if c(r)) / n
    return dict(n=n,
                fren10_k=f(lambda r: r["dd_k"] >= FREN - EPS), asma15_k=f(lambda r: r["dd_k"] > ASMA15 + EPS), kill20=f(lambda r: r["kill"]),
                fren10_h=f(lambda r: r["dd_h"] >= FREN - EPS), asma15_h=f(lambda r: r["dd_h"] > ASMA15 + EPS),
                yatay=f(lambda r: YATAY[0] - EPS <= r["net"] <= YATAY[1] + EPS), ust=f(lambda r: r["net"] > YATAY[1] + EPS),
                alt=f(lambda r: r["net"] < YATAY[0] - EPS),
                en_kotu_net=float(min(r["net"] for r in rows)), medyan_net=float(np.median([r["net"] for r in rows])),
                en_kotu_dd_k=float(max(r["dd_k"] for r in rows)))


def korelasyon(egriler: dict, tahsis: dict) -> dict:
    """Alt hesapların günlük getirisi (Δözsermaye / tahsis) Pearson korelasyonu: tüm günler ve 'ikisi de hareketli' günler."""
    adlar = sorted(egriler)
    g = {a: np.diff(np.concatenate([[tahsis[a]], np.asarray(egriler[a], float)])) / tahsis[a] for a in adlar}
    out = {}
    for i, a in enumerate(adlar):
        for b in adlar[i + 1:]:
            x, y = g[a], g[b]
            hz = (x != 0) & (y != 0)
            tum = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None
            hr = float(np.corrcoef(x[hz], y[hz])[0, 1]) if hz.sum() > 2 and x[hz].std() > 0 and y[hz].std() > 0 else None
            out[f"{a}|{b}"] = dict(tum_gunler=tum, ikisi_hareketli=hr, hareketli_gun=int(hz.sum()), gun=int(len(x)))
    return out


def denetim_yeniden(egriler: list, tahsisler: list, kill_oran: float = HESAP_KILL) -> dict:
    """AYRI KISA KOD (numpy/pandas'sız, saf Python döngü): birleşik seriyi sıfırdan yeniden hesaplar; birlestir/olcu ile karşılaştırılır."""
    gun_say = len(egriler[0])
    toplam = sum(tahsisler)
    zirve_k = zirve_h = toplam
    dd_k = dd_h = 0.0
    kill, son_k, son_h = False, None, None
    for g in range(gun_say):
        if kill:
            break
        k = sum(min(egriler[i][g], tahsisler[i]) for i in range(len(egriler)))
        h = sum(egriler[i][g] for i in range(len(egriler)))
        zirve_k, zirve_h = max(zirve_k, k), max(zirve_h, h)
        dd_k, dd_h = max(dd_k, 1 - k / zirve_k), max(dd_h, 1 - h / zirve_h)
        son_k, son_h = k, h
        if 1 - k / zirve_k >= kill_oran - EPS:
            kill = True
    return dict(net=son_h / toplam - 1, dd_k=dd_k, dd_h=dd_h, kill=kill, son_k=son_k, son_h=son_h)


# =============================================================================================== veri (ham x1|x2 + MTM)
def kasa_ve_strateji_tf(ad: str) -> tuple:
    st = json.loads(oy.SET_YOLU.read_text(encoding="utf-8"))
    for k in st["stratejiler"]:
        if k["strateji"] == ad:
            if k["tur"] != "tek":
                raise ValueError(f"{ad}: tek-grafik değil")
            return k["tf"], k["evren"]
    raise KeyError(ad)


def yukle(ad: str, maliyet: str, ham_dizin: Path = HAM_DIZIN, mtm_dizin: Path = MTM_DIZIN) -> tuple:
    """v2 ham işlem listesi (+ günlük MTM kum_r) -> oyna girdisi. giris_fiyati = stop_mesafe / sf (sf = risk/nominal, taban 1e-4 -> bağlayıcı değil);
    islem_no = ham satır sırası (mtm.islem_no ile aynı). Yan dosya (.json, 'bitti' işareti) ve veri_yok/hata KONTROL edilir; eksik = hata."""
    from motor.arastirma.v2 import sabit
    tf, evren = kasa_ve_strateji_tf(ad)
    trl, mtl = [], []
    for sm in sabit.evren_listesi(evren):
        p = ham_dizin / maliyet / f"{ad}--{tf}--{sm}.parquet"
        j = ham_dizin / maliyet / f"{ad}--{tf}--{sm}.json"
        if not j.exists() or not p.exists():
            raise FileNotFoundError(f"ham dosya/yan dosya yok: {p}")
        meta = json.loads(j.read_text(encoding="utf-8"))
        if meta.get("hata") or meta.get("veri_yok"):
            raise RuntimeError(f"{p.name}: yan dosya hata/veri_yok: {meta.get('hata')!r} veri_yok={meta.get('veri_yok')}")
        h = pd.read_parquet(p)
        if not len(h):
            continue
        if not (np.isfinite(h["stop_mesafe"]).all() and (h["stop_mesafe"] > 0).all() and (h["sf"] > 0).all()):
            raise ValueError(f"{p.name}: stop_mesafe/sf geçersiz")
        if not h["giris_zamani"].is_monotonic_increasing:
            raise ValueError(f"{p.name}: giris_zamani sıralı değil (islem_no eşlemesi bozulur)")
        trl.append(pd.DataFrame({
            "strateji": ad, "sembol": sm, "islem_no": np.arange(len(h)), "yon": h["yon"].to_numpy(int),
            "giris_zamani": pd.DatetimeIndex(h["giris_zamani"]), "cikis_zamani": pd.DatetimeIndex(h["cikis_zamani"]),
            "giris_fiyati": h["stop_mesafe"].to_numpy(float) / h["sf"].to_numpy(float),
            "stop_mesafe": h["stop_mesafe"].to_numpy(float), "r": h["r"].to_numpy(float)}))
        m = pd.read_parquet(mtm_dizin / maliyet / f"{ad}--{tf}--{sm}.parquet")
        m.insert(0, "sembol", sm)
        mtl.append(m[["sembol", "islem_no", "gun", "kum_r"]])
    tr = pd.concat(trl, ignore_index=True)
    mt = pd.concat(mtl, ignore_index=True)
    holdout_kontrol(tr, mt, ad)
    return tr, mt


@functools.lru_cache(maxsize=None)
def _maliyet_orani(sembol: str, carpan: float) -> tuple:
    from decimal import Decimal as D
    from motor.arastirma import evren_maliyet
    taker, _, _, stop_bps = evren_maliyet.sembol_maliyeti(sembol, carpan, oy.TABLO)
    return D(str(stop_bps / 1e4)), D(str(taker / 100.0))


def maliyet_ayarla(maliyet: str) -> None:
    """oyna'nın boyutlandırmada kullandığı stop kayması + taker oranını, işlem R'lerinin üretildiği maliyet çarpanıyla (x1 | x2) tutarlı yapar
    (oy.maliyet_oranlari yalnız çarpan argümanıyla değiştirilir; mantık aynı). x1 = oy'nin kendi davranışı."""
    c = float(maliyet[1:])
    oy.maliyet_oranlari = lambda sembol, _c=c: _maliyet_orani(sembol, _c)


def alt_hesap_oyna(tr, mt, tahsis: float, bas, bit) -> dict:
    oy.KASA_USD = float(tahsis)
    lim = dataclasses.replace(cl.CANLI_LIMITLER, islem_basi_max_kayip_oran=RISK)
    r = oy.oyna(tr, mt, "canli", baslangic=bas, bitis=bit, boyut_ek=dict(limitler=lim))
    e = r["e"]
    beklenen = pd.date_range(bas.floor("D"), bit.floor("D"), freq="D")
    if not e.index.equals(beklenen):
        raise RuntimeError(f"alt hesap eğrisi gün dizisi pencereyle uyuşmuyor ({len(e)} vs {len(beklenen)})")
    return dict(e=e.to_numpy(float), kill=r["kill_tarihi"], islem=int(r["islem"]), mtm_eksik=int(r["mtm_eksik"]), min_tutar=int(r["min_tutar"]))


def gorev(a) -> tuple:
    ad, tahsis, maliyet, pens = a
    maliyet_ayarla(maliyet)
    tr, mt = yukle(ad, maliyet)
    return (ad, tahsis, maliyet), {k: alt_hesap_oyna(tr, mt, tahsis, b, e) for k, _, b, e in pens}


# =============================================================================================== senaryo birleştirme + rapor
def senaryo_hesapla(alt: dict, pens: list) -> dict:
    out = {}
    for sk, sv in SENARYOLAR.items():
        for mal in MALIYETLER:
            rows = {}
            for pk, tur, b, e in pens:
                eg = {ad: alt[(ad, t, mal)][pk]["e"] for ad, t in sv["tahsis"].items()}
                bi = birlestir(eg, sv["tahsis"])
                o = olcu(bi)
                o["tur"] = tur
                o["strateji_kill"] = {ad: alt[(ad, t, mal)][pk]["kill"] for ad, t in sv["tahsis"].items()}
                o["islem"] = {ad: alt[(ad, t, mal)][pk]["islem"] for ad, t in sv["tahsis"].items()}
                o["mtm_eksik"] = int(sum(alt[(ad, t, mal)][pk]["mtm_eksik"] for ad, t in sv["tahsis"].items()))
                rows[pk] = o
            tum_eg = {ad: alt[(ad, t, mal)]["TUM"]["e"] for ad, t in sv["tahsis"].items()}
            sets = {}
            for tur in ("Y12", "R6", "R12"):
                lst = [r for r in rows.values() if r["tur"] == tur]
                s = oranlar(lst)
                s["strateji_kill_say"] = {ad: sum(1 for r in lst if r["strateji_kill"][ad]) for ad in sv["tahsis"]}
                sets[tur] = s
            out[(sk, mal)] = dict(pencere=rows, set=sets, korelasyon=korelasyon(tum_eg, sv["tahsis"]),
                                  tum_alt={ad: dict(kill=alt[(ad, t, mal)]["TUM"]["kill"], islem=alt[(ad, t, mal)]["TUM"]["islem"],
                                                    min_tutar=alt[(ad, t, mal)]["TUM"]["min_tutar"], son=float(alt[(ad, t, mal)]["TUM"]["e"][-1]))
                                           for ad, t in sv["tahsis"].items()})
    return out


def denetim_calistir(alt: dict, sonuc: dict, pens: list) -> dict:
    sk, pk, mal = DENETIM["senaryo"], DENETIM["pencere"], DENETIM["maliyet"]
    sv = SENARYOLAR[sk]
    adlar = sorted(sv["tahsis"])
    eg = [list(map(float, alt[(ad, sv["tahsis"][ad], mal)][pk]["e"])) for ad in adlar]
    d = denetim_yeniden(eg, [sv["tahsis"][ad] for ad in adlar])
    a = sonuc[(sk, mal)]["pencere"][pk]
    fark = {k: abs(float(d[k]) - float(a[k])) for k in ("net", "dd_k", "dd_h", "son_k", "son_h")}
    return dict(**DENETIM, ana={k: a[k] for k in ("net", "dd_k", "dd_h", "kill", "son_k", "son_h")}, yeniden=d, maks_fark=max(fark.values()),
                kill_uyumlu=bool(a["kill"] == d["kill"]), uyumlu=bool(max(fark.values()) < 1e-9 and a["kill"] == d["kill"]))


def pct(x, d=1):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.{d}f}%"


def md_tablo(basliklar: list, satirlar: list) -> str:
    L = ["| " + " | ".join(basliklar) + " |", "|" + "|".join("---" for _ in basliklar) + "|"]
    L += ["| " + " | ".join(str(c) for c in s) + " |" for s in satirlar]
    return "\n".join(L)


def rapor_md(sonuc: dict, den: dict, dog: list, sha: str) -> str:
    L = ["# Birleşik hesap yeniden oynatması (S1 / S2 / S3)", "",
         "> **GEÇMİŞ SİMÜLASYON, GELECEK TAHMİNİ DEĞİL. ÜST SINIR UYARISI:** bu stratejiler tam da bu dönemde (v2 geliştirme, en geç 2025-11-07; holdout okunmadı) "
         "seçildi; sonuçlar bu yüzden iyimser bir üst sınırdır. Ön kayıt: `BIRLESIK_ON_KAYIT.md`; betik: `araclar/canli_birlesik_oynatma.py` "
         f"(sha256 `{sha[:16]}…`); ham sayılar: `birlesik_oynatma.json`.", "",
         "## Ne yapıldı (sade)",
         "- Her strateji kendi küçük hesabında, mevcut canlı kuralla (işlem başı %1,5, toplam açık stop riski %6, günlük -%6 yeni giriş yok, strateji -%30 kalıcı kill, "
         "asgari emir tutarı altı atlanır) ayrı ayrı oynatıldı; sonra günlük olarak toplandı.",
         "- **Açık pozisyonlar dahil:** her gün sonu açık işlemler günlük MTM (piyasa değeri) ile değerlendi (v2 `mtm` dosyaları, `kum_r`); yalnız kapanan işlemler değil.",
         "- İki birleşik seri: **K (kasa)** = Σ min(alt hesap özsermayesi, tahsis) (canlı hesap kill'in ölçtüğü seri; en çok tahsis toplamı kadar olabilir); "
         "**H (gerçek hesap)** = Σ özsermaye (kâr hesapta kalır). Net sonuç ve H düşüşü H'den; büyüme freni (-%10), -%15 aşma ve -%20 hesap kill K'dan.",
         "- Hesap kill: K, tahsis toplamından -%20 olursa o gün sonu hepsi kapanır, sonrası donuk. Pencereler her seferinde sıfırdan başlar (başlangıç noktası etkisi).",
         "- Ortak başlangıç 2018-01-01 (kripto 2017-08'de başlıyor; 2017 yarım yıl dışarıda), bitiş 2025-11-07. Yıl pencereleri 2018-2024 (7 tam yıl; 2025 yarım olduğu için yalnız ayrı satırda). "
         "6 ay ve 12 ay pencereleri ayda bir kaydırıldı.",
         "- Senaryolar: **S1** ewo 250 + e0v1en 60 USD; **S2** S1 + hma-atr-rider 250 + lube 250; **S3** eski plan: e0v1en, ewo, hma, lube 4 x 250 USD. "
         "Maliyet x2 ana, x1 ek. Boyutlandırmadaki kayma/komisyon da aynı çarpanla (x2'de x2).", ""]
    for mal, bas in (("x2", "ANA: maliyet x2"), ("x1", "EK: maliyet x1")):
        L += [f"## {bas}", "", "### Tüm dönem (2018-01-01 .. 2025-11-07, tek başlangıç)", ""]
        sat = []
        for sk in SENARYOLAR:
            r = sonuc[(sk, mal)]["pencere"]["TUM"]
            ta = sonuc[(sk, mal)]["tum_alt"]
            sat.append([sk, SENARYOLAR[sk]["ad"], f"{sum(SENARYOLAR[sk]['tahsis'].values()):.0f}", pct(r["net"]), pct(r["dd_h"]), pct(r["dd_k"]),
                        "EVET (gün %d)" % r["kill_gun"] if r["kill"] else "hayır",
                        ", ".join(f"{a.replace('dis__', '')}:{'KILL ' + v['kill'] if v['kill'] else 'ok'}" for a, v in ta.items())])
        L += [md_tablo(["Senaryo", "Ad", "Toplam USD", "Net sonuç (H)", "Maks düşüş H", "Maks düşüş K", "Hesap kill -%20", "Strateji kill (tüm dönem)"], sat), ""]
        L += ["### Pencere oranları (her pencere sıfırdan)", ""]
        sat = []
        for sk in SENARYOLAR:
            for tur, etiket in (("Y12", "12 ay, yıl başı"), ("R6", "6 ay kayan"), ("R12", "12 ay kayan")):
                s = sonuc[(sk, mal)]["set"][tur]
                sat.append([sk, etiket, s["n"], pct(s["fren10_k"], 0), pct(s["asma15_k"], 0), pct(s["kill20"], 0), pct(s["fren10_h"], 0), pct(s["asma15_h"], 0),
                            pct(s["en_kotu_net"]), pct(s["medyan_net"]), ", ".join(f"{a.replace('dis__', '')[:6]}={v}" for a, v in s["strateji_kill_say"].items())])
        L += [md_tablo(["Sen.", "Pencere", "n", "-%10 değme (K)", "-%15 aşma (K)", "Hesap kill -%20", "-%10 değme (H)", "-%15 aşma (H)", "En kötü net", "Medyan net",
                        "Strateji kill sayısı (pencere)"], sat), ""]
        L += ["### Yatay bandı (-%10 .. +%10, net sonuç H) ve en kötü dönemler", ""]
        sat = []
        for sk in SENARYOLAR:
            for tur, etiket in (("Y12", "12 ay, yıl başı"), ("R12", "12 ay kayan"), ("R6", "6 ay kayan")):
                s = sonuc[(sk, mal)]["set"][tur]
                sat.append([sk, etiket, s["n"], pct(s["yatay"], 0), pct(s["ust"], 0), pct(s["alt"], 0), pct(s["en_kotu_net"])])
        L += [md_tablo(["Sen.", "Pencere", "n", "Yatay bandında", "Bandın üstünde", "Bandın altında", "En kötü net"], sat), ""]
        L += ["En kötü 6 ay = 6 ay kayan pencerelerin en düşük neti; en kötü 12 ay = 12 ay kayan pencerelerin en düşük neti (yukarıdaki 'En kötü net').", ""]
        L += ["### Yıl yıl net sonuç (H) / maks düşüş K (12 ay yıl başı + 2025 kısmi)", ""]
        sat = []
        for pk in ["Y2018", "Y2019", "Y2020", "Y2021", "Y2022", "Y2023", "Y2024", "Y2025K"]:
            sat.append([pk + (" (yarım)" if pk == "Y2025K" else "")] + [f"{pct(sonuc[(sk, mal)]['pencere'][pk]['net'])} / {pct(sonuc[(sk, mal)]['pencere'][pk]['dd_k'])}" +
                                                                         (" KILL" if sonuc[(sk, mal)]['pencere'][pk]['kill'] else "") for sk in SENARYOLAR])
        L += [md_tablo(["Yıl"] + list(SENARYOLAR), sat), ""]
        L += ["### Stratejiler arası günlük getiri korelasyonu (tüm dönem; Δözsermaye / tahsis)", ""]
        sat = []
        for sk in SENARYOLAR:
            for kk, v in sonuc[(sk, mal)]["korelasyon"].items():
                a, b = (x.replace("dis__", "") for x in kk.split("|"))
                sat.append([sk, f"{a} / {b}", "-" if v["tum_gunler"] is None else f"{v['tum_gunler']:.2f}",
                            "-" if v["ikisi_hareketli"] is None else f"{v['ikisi_hareketli']:.2f}", v["hareketli_gun"]])
        L += [md_tablo(["Sen.", "Çift", "Tüm günler", "İkisi de hareketli günler", "Hareketli gün sayısı"], sat), ""]
    L += ["## Denetim (birleşik seriyi ayrı kısa kodla yeniden hesaplama)", "",
          f"Senaryo **{den['senaryo']}**, pencere **{den['pencere']}**, maliyet **{den['maliyet']}**. Ana yol (`birlestir`/`olcu`, numpy) ile saf Python döngüyle yazılmış ayrı kod (`denetim_yeniden`) karşılaştırıldı.", "",
          md_tablo(["Ölçü", "Ana yol", "Ayrı kod"], [[k, f"{den['ana'][k]:.6f}", f"{den['yeniden'][k]:.6f}"] for k in ("net", "dd_k", "dd_h", "son_k", "son_h")] +
                   [["hesap kill", str(den["ana"]["kill"]), str(den["yeniden"]["kill"])]]),
          "", f"Sonuç: **{'UYUMLU' if den['uyumlu'] else 'UYUMSUZ'}** (en büyük mutlak fark {den['maks_fark']:.2e}).", "",
          "## Veri hattı doğrulaması (ham/x1 -> oyna, tüm dönem, tek başına) — ölçüm raporuyla uyum", "",
          "Aynı 250 USD / %1,5 / x1 kurulumu, `OLCUM_250_15.md` (işlem listesi backtest'ten yeniden üretilmişti) ile karşılaştırıldı; giriş fiyatı ham dosyadan türetildiği için küçük fark olabilir.", "",
          md_tablo(["Strateji", "Bu araç (son özsermaye USD)", "OLCUM_250_15.csv", "Fark"], [[d["ad"].replace("dis__", ""), f"{d['bu']:.2f}", f"{d['olcum']:.2f}", f"{d['bu'] - d['olcum']:+.2f}"] for d in dog]), ""]
    return "\n".join(L)


def olcum_karsilastir(ham_dizin=HAM_DIZIN) -> list:
    """Veri hattı doğrulaması: ham/x1'den kurulan girdiyle tek strateji, 250 USD, tüm dönem (baslangic=None) -> olcum_250_15.csv'deki son özsermaye."""
    csv = pd.read_csv(CIKTI / "olcum_250_15.csv")
    out = []
    maliyet_ayarla("x1")
    for ad in (K_EWO, K_E0, K_HMA, K_LUBE):
        tr, mt = yukle(ad, "x1", ham_dizin)
        oy.KASA_USD = 250.0
        lim = dataclasses.replace(cl.CANLI_LIMITLER, islem_basi_max_kayip_oran=RISK)
        r = oy.oyna(tr, mt, "canli", boyut_ek=dict(limitler=lim))
        out.append(dict(ad=ad, bu=float(r["son_ozsermaye"]), olcum=float(csv.loc[csv["strateji"] == ad, "son_ozsermaye_usd"].iloc[0]),
                        kill=r["kill_tarihi"], mtm_eksik=int(r["mtm_eksik"])))
    return out


def json_hazirla(sonuc, den, dog, sha, pens) -> dict:
    j = dict(betik_sha256=sha, baslangic=str(BASLANGIC.date()), son_gun=str(SON_GUN.date()), risk_islem_basi=RISK, hesap_kill=HESAP_KILL, fren=FREN, asma=ASMA15, yatay=list(YATAY),
             senaryolar={k: dict(ad=v["ad"], tahsis=v["tahsis"]) for k, v in SENARYOLAR.items()}, denetim=den, veri_hatti_dogrulama=dog, sonuc={})
    for (sk, mal), v in sonuc.items():
        j["sonuc"].setdefault(sk, {})[mal] = dict(
            set=v["set"], korelasyon=v["korelasyon"], tum_alt=v["tum_alt"],
            pencere={k: {a: b for a, b in r.items() if a not in ("son_k",)} for k, r in v["pencere"].items()})
    return j


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--sadece-dogrula", action="store_true", help="yalnız veri hattı doğrulaması (senaryo koşusu YOK)")
    a = ap.parse_args(argv)
    sha = betik_sha256()
    if a.sadece_dogrula:
        for d in olcum_karsilastir():
            print(d)
        return
    pens = pencereler()
    gorevler = sorted({(ad, t, mal) for sv in SENARYOLAR.values() for ad, t in sv["tahsis"].items() for mal in MALIYETLER})
    alt = {}
    with cf.ProcessPoolExecutor(a.surec) as ex:
        for anahtar, v in ex.map(gorev, [(ad, t, mal, pens) for ad, t, mal in gorevler], chunksize=1):
            alt[anahtar] = v
            print("alt hesap bitti:", anahtar, flush=True)
    sonuc = senaryo_hesapla(alt, pens)
    den = denetim_calistir(alt, sonuc, pens)
    dog = olcum_karsilastir()
    CIKTI.mkdir(parents=True, exist_ok=True)
    (CIKTI / "birlesik_oynatma.json").write_text(json.dumps(json_hazirla(sonuc, den, dog, sha, pens), indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    (CIKTI / "BIRLESIK_OYNATMA.md").write_text(rapor_md(sonuc, den, dog, sha), encoding="utf-8")
    print("denetim:", "UYUMLU" if den["uyumlu"] else "UYUMSUZ", den["maks_fark"])


if __name__ == "__main__":
    main()
