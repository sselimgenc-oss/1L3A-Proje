"""Dersler: paper/canlı sonuçlarının backtest beklentisiyle karşılaştırması (pano öncelik 2). Hesap BURADA (motor tarafı); pano yalnız biçimler.

Karşılaştırma tabanı: `sonuclar/final/beklenti_islem_referansi.csv` (üretici: `python -m motor.canli.dersler_referans`). Bu dosya
`beklenti_araliklari.csv` ile AYNI örneklem-dışı işlemlerden (walk-forward OOS + kilitli dönem; `motor.arastirma.beklenti.varliklar_yukle`)
strateji başına isabet, ortalama R, PF (R tabanlı), R sapması ve çıkış nedeni dağılımını verir; beklenti_araliklari.csv ise yalnız pencere
(4/8 hafta) yüzdeliklerini içerir ve ortalama R / PF beklentisi taşımaz.

YÖNTEM (kurallı; LLM yok, lookahead yok: yalnız kapanmış işlemler)
  - R = `r_kiyas` (TradFi funding HARİÇ r; kullanıcı kararı 2026-11-09: araştırmada TradFi funding yok; kripto funding dahil kalır).
  - isabet = r > 0 olan işlem payı (r'si olan işlemler üzerinden). Binom testi: kesin, iki yönlü, H0: p = backtest isabeti.
  - ortalama R: Welch t testi (paper n, ort, std ↔ referans n, ort, std), iki yönlü. PF (R tabanlı) = Σ(r>0) / -Σ(r<0): betimleyici, test yok.
  - çıkış nedeni payı: neden başına kesin binom testi (H0: pay = backtest payı), n >= MIN_ISLEM_DERS iken. Backtest payı 0 (ya da 1) olan nedende test
    YAPILMAZ (H0 pay=0 iken tek gözlem p=0 verirdi): p_deger null + test_neden "backtestte gözlenmedi (üst sınır ~3/n)"; Koç bunu en fazla "izle" sayar.
  - durum: "ornek_az" (n < MIN_ISLEM_DERS; testler null + neden) | "ustunde" | "altinda" | "icinde". Ortalama R testi anlamlıysa (p < ALFA) yönü
    belirler; değilse isabet testi; ikisi de anlamlı değilse "icinde". Ortalama R ile isabet ters yönde anlamlıysa R kararı verir ve açıklamaya yazılır.
    8 haftalık beklenti penceresinde alarm varsa (stratejiler.json beklenti) ve n yeterliyse durum "altinda"dır.
EŞİKLER (KULLANICI ONAYLI, 2026-11-08; DURUM.md lider günlüğü): MIN_ISLEM_DERS = 30 (yeterli örnek sınırı), ALFA = 0.05 (çoklu test düzeltmesi YOK).
  Karar sonucu: "altinda" kabulü bozmaz ama strateji canlıya geçmez; "ornek_az" da canlıya uygun sayılmaz (bkz. aylik_rapor.canliya_uygunluk).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Optional

from motor.canli import durum as d
from motor.canli import durum_ek as ek

KOK = Path(__file__).resolve().parents[2]
REFERANS_CSV = KOK / "sonuclar" / "final" / "beklenti_islem_referansi.csv"
MIN_ISLEM_DERS = 30                      # kullanıcı onaylı 2026-11-08 (durum_ek.MIN_ISLEM'den bağımsız)
ALFA = 0.05
DURUM_ETIKET = {"icinde": "beklenti içinde", "altinda": "beklentinin altında", "ustunde": "beklentinin üstünde", "ornek_az": "örnek az"}
ONAYLI_ESIKLER = [
    {"ad": "dersler_asgari_islem", "deger": MIN_ISLEM_DERS, "onay": "kullanıcı onaylı 2026-11-08",
     "aciklama": f"Bir stratejinin 'beklenti içinde/altında/üstünde' diye sınıflanması için en az {MIN_ISLEM_DERS} kapanan işlem; altı 'örnek az'."},
    {"ad": "dersler_alfa", "deger": ALFA, "onay": "kullanıcı onaylı 2026-11-08",
     "aciklama": f"İstatistiksel testlerde anlamlılık düzeyi p < {ALFA}; çoklu test düzeltmesi yok."},
]


# ---------------------------------------------------------------------------- istatistik yardımcıları (scipy yok)
def _log_pmf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) + k * math.log(p) + (n - k) * math.log1p(-p)


def binom_p(k: int, n: int, p: float) -> float:
    """Kesin iki yönlü binom testi p-değeri (olasılığı gözlenenden büyük olmayan tüm sonuçların toplamı)."""
    if n <= 0 or not (0 <= k <= n):
        raise ValueError(f"binom_p: geçersiz k={k}, n={n}")
    lg = _log_pmf(k, n, p)
    esik = lg + 1e-7
    toplam = sum(math.exp(_log_pmf(i, n, p)) for i in range(n + 1) if _log_pmf(i, n, p) <= esik)
    return min(1.0, toplam)


def _betacf(a: float, b: float, x: float) -> float:
    tiny, eps = 1e-300, 3e-14
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    dd = 1.0 - qab * x / qap
    dd = 1.0 / (dd if abs(dd) > tiny else tiny)
    h = dd
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= dd * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = dd * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    raise ArithmeticError("tamamlanmamış beta (kesirli açılım yakınsamadı)")


def betainc(a: float, b: float, x: float) -> float:
    """Düzenlenmiş eksik beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_p_iki_yonlu(t: float, df: float) -> float:
    return betainc(df / 2.0, 0.5, df / (df + t * t)) if t != 0 else 1.0


def welch(m1: float, s1: float, n1: int, m2: float, s2: float, n2: int) -> Optional[dict]:
    """Welch t testi (iki yönlü). Varyans sıfırsa None."""
    v1, v2 = s1 * s1 / n1, s2 * s2 / n2
    se2 = v1 + v2
    if se2 <= 0:
        return None
    t = (m1 - m2) / math.sqrt(se2)
    df = se2 * se2 / ((v1 * v1 / (n1 - 1) if n1 > 1 else 0.0) + (v2 * v2 / (n2 - 1) if n2 > 1 else 0.0))
    return {"t": t, "df": df, "p": t_p_iki_yonlu(t, df)}


# ---------------------------------------------------------------------------- referans
def referans_oku(yol=REFERANS_CSV) -> Optional[dict]:
    """-> {kimlik: {n, isabet, ort_r, std_r, pf_r, cikis_paylari {neden: pay}}}; dosya yoksa None (çağıran nedeni yazar)."""
    yol = Path(yol)
    if not yol.exists():
        return None
    out = {}
    with open(yol, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[r["kimlik"]] = {"n": int(r["n"]), "isabet": float(r["isabet"]), "ort_r": float(r["ort_r"]), "std_r": float(r["std_r"]),
                                "pf_r": float(r["pf_r"]) if r["pf_r"] not in ("", None) else None,
                                "cikis_paylari": json.loads(r["cikis_paylari"]), "kaynak": r["kaynak"]}
    return out


def r_ozet(r: list) -> dict:
    """R listesi -> {n, isabet, ort_r, std_r, pf_r}. Boş liste: n=0, kalanı None."""
    n = len(r)
    if n == 0:
        return {"n": 0, "isabet": None, "ort_r": None, "std_r": None, "pf_r": None}
    kar, zr = sum(x for x in r if x > 0), sum(x for x in r if x < 0)
    return {"n": n, "isabet": sum(1 for x in r if x > 0) / n, "ort_r": sum(r) / n, "std_r": ek._std(r) if n > 1 else None,
            "pf_r": kar / -zr if zr < 0 else None}


# ---------------------------------------------------------------------------- strateji değerlendirmesi
def _yon(deger: float, beklenen: float) -> str:
    return "altinda" if deger < beklenen else ("ustunde" if deger > beklenen else "esit")


def _pct(x: float) -> str:
    return f"%{x * 100:.0f}"


def _p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def degerlendir(kimlik: str, satirlar: list, ref: Optional[dict], konum: Optional[dict] = None) -> dict:
    """Bir strateji için ders kaydı. satirlar: yalnız bu stratejinin kapanan işlemleri (islemler.jsonl satırı). konum: stratejiler.json `beklenti`."""
    ls = [s for s in satirlar if s["kimlik"] == kimlik]
    r = [float(ek.r_kiyas(s)) for s in ls if ek.r_kiyas(s) is not None]      # TradFi funding HARİÇ (2026-11-09)
    g = r_ozet(r)
    n = len(ls)
    out = {"kimlik": kimlik, "islem": n, "r_olculen": len(r), "isabet": g["isabet"], "ort_r": g["ort_r"], "std_r": g["std_r"], "pf_r": g["pf_r"],
           "beklenti": None, "isabet_testi": None, "ort_r_testi": None, "test_neden": None, "durum": None, "durum_etiket": None,
           "durum_neden": None, "beklenti_penceresi": None, "aciklamalar": [], "cikis_nedeni_sapmalari": []}
    if ref is None:
        out["durum_neden"] = "backtest referansı yok (beklenti_islem_referansi.csv'de bu kimlik yok ya da dosya yok)"
        return out
    out["beklenti"] = {k: ref[k] for k in ("n", "isabet", "ort_r", "std_r", "pf_r")}
    # beklenti penceresi konumu (8 hf öncelikli): yalnız stratejiler.json'daki alanlar
    alarm = False
    if konum:
        hf = "8" if "8" in konum else ("4" if "4" in konum else None)
        if hf:
            nb, dd = konum[hf]["net_getiri"], konum[hf]["max_dusus"]
            out["beklenti_penceresi"] = {"hafta": int(hf), "net_bant": nb["bant"], "net_getiri": nb["deger"], "dusus_bant": dd["bant"],
                                         "max_dusus": dd["deger"], "alarm": nb["alarm"] if hf == "8" else None}
            alarm = bool(hf == "8" and (nb["alarm"] or dd["alarm"]))
    if n < MIN_ISLEM_DERS or len(r) < MIN_ISLEM_DERS:
        out["durum"], out["durum_etiket"] = "ornek_az", DURUM_ETIKET["ornek_az"]
        out["test_neden"] = f"kapanan işlem {n} (R ölçülen {len(r)}) < {MIN_ISLEM_DERS}: binom ve t testi hesaplanmadı"
        out["durum_neden"] = out["test_neden"]
        if alarm:
            out["aciklamalar"].append("8 haftalık beklenti penceresinde alarm var (net getiri ya da düşüş); işlem örneği az olduğu için durum bu alarmdan bağımsız 'örnek az'.")
        return out
    k = sum(1 for x in r if x > 0)
    pb = binom_p(k, len(r), ref["isabet"])
    yi = _yon(k / len(r), ref["isabet"])
    out["isabet_testi"] = {"test": "binom (kesin, iki yönlü)", "p_deger": pb, "yon": yi, "anlamli": pb < ALFA}
    wt = welch(g["ort_r"], g["std_r"] or 0.0, len(r), ref["ort_r"], ref["std_r"], ref["n"]) if g["std_r"] is not None else None
    if wt is None:
        out["test_neden"] = "ortalama R t testi hesaplanamadı: varyans sıfır"
        out["ort_r_testi"] = None
    else:
        yr = _yon(g["ort_r"], ref["ort_r"])
        out["ort_r_testi"] = {"test": "Welch t (iki yönlü)", "t": wt["t"], "df": wt["df"], "p_deger": wt["p"], "yon": yr, "anlamli": wt["p"] < ALFA}
    # durum
    r_an = out["ort_r_testi"]["anlamli"] if out["ort_r_testi"] else False
    i_an = out["isabet_testi"]["anlamli"]
    if r_an:
        yon, neden = out["ort_r_testi"]["yon"], "ortalama R testi anlamlı"
        if i_an and out["isabet_testi"]["yon"] != yon:
            out["aciklamalar"].append("İsabet ve ortalama R ters yönde anlamlı sapıyor; durum ortalama R'ye göre verildi.")
    elif i_an:
        yon, neden = out["isabet_testi"]["yon"], "isabet testi anlamlı"
    else:
        yon, neden = "icinde", "isabet ve ortalama R testleri anlamlı sapma göstermiyor"
    if yon in ("altinda", "ustunde"):
        out["durum"] = yon
    else:
        out["durum"] = "icinde"
    if alarm and out["durum"] != "altinda":
        out["durum"], neden = "altinda", "8 haftalık beklenti penceresinde alarm"
    out["durum_etiket"] = DURUM_ETIKET[out["durum"]]
    out["durum_neden"] = neden
    # metin şablonları
    A = out["aciklamalar"]
    A.append(f"İsabet {_pct(g['isabet'])} (backtest {_pct(ref['isabet'])}, {len(r)} işlem, binom {_p(pb)}).")
    if out["ort_r_testi"]:
        A.append(f"Ortalama R {g['ort_r']:+.2f} (backtest {ref['ort_r']:+.2f}, Welch t {_p(wt['p'])}).")
    if g["pf_r"] is not None and ref["pf_r"] is not None:
        A.append(f"PF (R) {g['pf_r']:.2f} (backtest {ref['pf_r']:.2f}).")
    elif g["pf_r"] is None:
        A.append("PF (R) hesaplanamadı: zarar eden işlem yok.")
    if alarm:
        pw = out["beklenti_penceresi"]
        A.append(f"8 hafta beklenti penceresinde alarm: net getiri {pw['net_bant']}, düşüş {pw['dusus_bant']}.")
    # çıkış nedeni sapmaları
    cnt: dict = {}
    for s in ls:
        cnt[s.get("cikis_nedeni") or "bilinmiyor"] = cnt.get(s.get("cikis_nedeni") or "bilinmiyor", 0) + 1
    for neden_ in sorted(set(cnt) | set(ref["cikis_paylari"])):
        kk, q = cnt.get(neden_, 0), ref["cikis_paylari"].get(neden_, 0.0)
        if q <= 0.0:
            # Backtestte 0 gözlem: H0 pay=0 altında k>0'ın olasılığı tam 0 olur (binom p=0) -> anlamsız "beklenti dışı". Test YAPILMAZ;
            # yalnız bilgi: referans n işlemde 0 gözlemin %95 üst güven sınırı ~3/n ("üçler kuralı").
            ust = gozlenmeyen_ust_sinir(ref.get("n"))
            neden_t = ("backtestte gözlenmedi (referans " + (f"{ref['n']} işlemde 0; %95 üst sınır ~3/n = {_pct(ust)}" if ust is not None else "işlem sayısı bilinmiyor")
                       + "); binom testi yapılmadı")
            out["cikis_nedeni_sapmalari"].append({"neden": neden_, "islem": kk, "pay": kk / n, "beklenen_pay": q, "p_deger": None, "anlamli": False,
                                                  "gozlenmedi": True, "ust_sinir": ust, "test_neden": neden_t})
            if kk > 0:
                A.append(f"'{neden_}' çıkışı backtestte gözlenmedi (üst sınır ~3/n" + (f" = {_pct(ust)}" if ust is not None else "")
                         + f"); paperda {kk}/{n} işlemde var. Test yapılmadı: tek başına beklenti dışı sayılmaz.")
            continue
        if q >= 1.0:
            # Backtestte TÜM çıkışlar bu nedenle: diğer nedenlerin payı 0 (yukarıdaki kural) -> aynı nedenle test yapılmaz (p=0 olurdu).
            ust = gozlenmeyen_ust_sinir(ref.get("n"))
            out["cikis_nedeni_sapmalari"].append({"neden": neden_, "islem": kk, "pay": kk / n, "beklenen_pay": q, "p_deger": None, "anlamli": False,
                                                  "gozlenmedi": False, "ust_sinir": None,
                                                  "test_neden": "backtestte tüm çıkışlar bu nedenle (diğer nedenler gözlenmedi"
                                                                + (f"; alt sınır ~1-3/n = {_pct(1 - ust)}" if ust is not None else "") + "); binom testi yapılmadı"})
            continue
        p_ = binom_p(kk, n, q)
        sapma = {"neden": neden_, "islem": kk, "pay": kk / n, "beklenen_pay": q, "p_deger": p_, "anlamli": p_ < ALFA,
                 "gozlenmedi": False, "ust_sinir": None, "test_neden": None}
        out["cikis_nedeni_sapmalari"].append(sapma)
        if p_ < ALFA:
            A.append(f"'{neden_}' çıkışları {_pct(kk / n)} (backtest {_pct(q)}): beklenenden {'çok' if kk / n > q else 'az'} ({_p(p_)}).")
    return out


def gozlenmeyen_ust_sinir(n_ref) -> Optional[float]:
    """Backtestte n_ref işlemde 0 gözlenen olayın payı için yaklaşık %95 üst güven sınırı (üçler kuralı, 3/n). n bilinmiyorsa None."""
    try:
        n_ref = int(n_ref)
    except (TypeError, ValueError):
        return None
    return min(1.0, 3.0 / n_ref) if n_ref > 0 else None


# ---------------------------------------------------------------------------- dosya
def olustur(kaynak: str, zaman: str, kimlikler: list, satirlar: list, konumlar: Optional[dict] = None, referans_csv=REFERANS_CSV,
            referans: Optional[dict] = None) -> dict:
    """-> dersler.json içeriği. kimlikler: strateji kimlikleri (stratejiler.json sırası); konumlar: {kimlik: stratejiler.json beklenti}."""
    ref = referans if referans is not None else referans_oku(referans_csv)
    kayitlar = [degerlendir(k, satirlar, (ref or {}).get(k), (konumlar or {}).get(k)) for k in kimlikler]
    sayim = {x: sum(1 for k in kayitlar if k["durum"] == x) for x in ("icinde", "altinda", "ustunde", "ornek_az")}
    sayim["olculmedi"] = sum(1 for k in kayitlar if k["durum"] is None)
    return {**d._zarf("dersler", kaynak, zaman), "min_islem": MIN_ISLEM_DERS, "alfa": ALFA,
            "referans_neden": None if ref is not None else "sonuclar/final/beklenti_islem_referansi.csv yok (python -m motor.canli.dersler_referans)",
            "yontem": ("İsabet: kesin iki yönlü binom; ortalama R: Welch t; PF: R tabanlı, test yok; çıkış nedeni payı: neden başına binom. "
                       "Referans = beklenti_araliklari.csv'nin kaynağı olan örneklem-dışı işlemler. Çoklu test düzeltmesi yok; "
                       "backtest referansının kendi belirsizliği yalnız Welch testinde hesaba katılır."),
            "kaynak_not": ("backtest kaynağı: referans kilitli dönem işlemlerini de içerir; bu karşılaştırma bağımsız bir sınav değildir (bağımsız sınav paper'dır)."
                           if kaynak == "backtest" else None),
            "onayli_esikler": ONAYLI_ESIKLER, "tanimsiz_esikler": [], "sayim": sayim, "stratejiler": kayitlar}
