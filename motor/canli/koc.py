"""Koç — pano öncelik 6b. Kapanan işlemlerden KURALLI tespitler (metin şablonu; LLM yok, lookahead yok: yalnız kapanmış işlemler). Hesap BURADA; pano yalnız biçimler.

İLKELER (kullanıcı/proje kuralları)
  - Koç ASLA risk artırma, pozisyon büyütme, kayıp sonrası ekleme, Kelly ile büyütme ya da benzeri bir şey önermez (martingale/DCA yasak). Öneri metinleri sabit şablondur ve
    yalnız üç düzeydedir: "beklenti_disi", "incele", "izle". Geriye dönük strateji/ayar seçimi önermez; değişiklik yalnız walk-forward + kullanıcı onayıyla (karar 4).
  - Her tespitte dayanak sayılar ve istatistik (test, ham p, çoklu-test düzeltmeli p) bulunur. Örnek azsa kural ÇALIŞMAZ ve `atlanan[]`'a nedeniyle yazılır.
  - Bulgular bilgidir, karar değildir. Eşikler: asgari 30 işlem (Dersler onaylı), alfa 0.05 (Dersler onaylı); MIN_KOVA ve MIN_GRUP_TUTMA koça özgü örnek sınırlarıdır (kullanıcıya sorulur).

SEVİYE (referans = backtestte karşılaştırma tabanı var mı?)
  referans VAR  (stop sıklığı, çıkış nedeni payı, kayıp serisi, Dersler "altında"): düzeltilmiş p < alfa -> "beklenti_disi"; yalnız ham p < alfa -> "incele".
  referans YOK  (saat/gün/sembol kayıp yoğunluğu, tutma süresi): backtestte bu dağılımlar kayıtlı değil, grup farkı backtestte de olabilir ->
                düzeltilmiş p < alfa -> "incele"; yalnız ham p < alfa -> "izle". Bu kurallar "beklenti_disi" üretemez.
ÇOKLU TEST: aynı kural ailesi ve aynı kapsam (set ya da bir strateji) içindeki test sayısı kadar Bonferroni (p_duzeltilmis = min(1, p x m)). Kapsamlar/kurallar arası
  düzeltme YOKTUR (keşif amaçlı bilgi); `test_sayisi` her bulguda yazılıdır.

KURALLAR
  stop_sikligi        referans: beklenti_islem_referansi.csv çıkış payları (Dersler çıkış nedeni sapmaları). "stop" içeren nedenlerin toplam payı, backtest payından anlamlı yüksekse
                      (kesin iki yönlü binom). Strateji başına.
  cikis_nedeni        Stop dışı çıkış nedenlerinden payı backtestten anlamlı sapanlar (her iki yön; backtestte hiç görülmeyen neden dahil). m = o stratejide test edilen neden sayısı.
  kayip_serisi        En uzun ardışık "kazanmayan" (R <= 0) işlem serisi, backtest isabetiyle (q = 1 - isabet) n işlemde şansla görülme olasılığı
                      P(en uzun seri >= L) (kesin dinamik program). Strateji ve set (set: işlem karışımına göre havuzlanmış q). Çıkış sırası zamanla sıralanır.
  tutma_suresi        Kaybeden (R <= 0) işlemler kazananlardan (R > 0) anlamlı UZUN tutulmuş mu (Mann-Whitney U, normal yaklaşım, bağ düzeltmeli, iki yönlü). Yalnız strateji
                      başına (farklı zaman dilimleri havuzlanmaz). Backtestte tutma süresi referansı yok.
  kayip_yogunlugu     Giriş saati (TSİ, 4 saatlik blok), giriş günü (TSİ haftanın günü) ve sembol bazında "kazanmayan işlem payı" kovanın dışındakinden anlamlı yüksek ve kovanın
                      toplam R'si negatifse (Fisher kesin testi). Set ve strateji (>= 30 işlem) kapsamında. m = o ailede testlenen kova sayısı.
  beklenti_alti       Dersler durumu "altında" olan strateji; set 8 hf beklenti penceresi alarmı. Testler Dersler'dendir (ham p, düzeltme yok: Dersler onaylı kuralı).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

from motor.canli import dersler as ders
from motor.canli import durum as d
from motor.canli import durum_ek as ek

MIN_ISLEM = ders.MIN_ISLEM_DERS           # 30 (kullanıcı onaylı 2026-11-08)
ALFA = ders.ALFA                          # 0.05 (kullanıcı onaylı 2026-11-08)
MIN_KOVA = 5                              # saat/gün/sembol kovasında ve karşılaştırma kümesinde asgari işlem (koça özgü; kullanıcıya sorulur)
MIN_GRUP_TUTMA = 10                       # tutma süresi karşılaştırmasında her grupta asgari işlem (Mann-Whitney normal yaklaşımı; kullanıcıya sorulur)
SAAT_BLOK = 4                             # TSİ saat bloğu genişliği
GUN_ADI = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")
SEVIYE_SIRA = {"beklenti_disi": 0, "incele": 1, "izle": 2}
SEVIYE_ETIKET = {"beklenti_disi": "beklenti dışı", "incele": "incele", "izle": "izle"}
# Sabit öneri şablonları: yalnız gözlem / inceleme düzeyi. Risk artırma, büyütme, ekleme, Kelly YOK (test bunu tarar).
ONERI = {
    "beklenti_disi": ("Beklenti dışı: nedenini incele (veri, maliyet ve kayma, kod, piyasa koşulu). Bu bir strateji ya da ayar seçimi önerisi değildir; "
                      "değişiklik yalnız walk-forward testi ve kullanıcı onayıyla yapılır."),
    "incele": ("İncele: bulgu istatistiksel olarak kesin değil (çoklu test düzeltmesi ya da backtestte karşılaştırma tabanı yok). İşlem kayıtlarına bak, "
               "karar için örnek birikmesini bekle."),
    "izle": "İzle: yalnız düzeltmesiz testte anlamlı; tek başına bir şey söylemez. Örnek büyüdükçe tekrar edip etmediğine bak.",
}
KURALLAR = (
    {"id": "stop_sikligi", "ad": "Stoplar beklenenden sık", "referans": "backtest", "kaynak": "beklenti_islem_referansi.csv çıkış payları; kesin binom"},
    {"id": "cikis_nedeni", "ad": "Çıkış nedeni payı beklentiden saptı", "referans": "backtest", "kaynak": "beklenti_islem_referansi.csv çıkış payları; kesin binom; Bonferroni"},
    {"id": "kayip_serisi", "ad": "Ardışık kayıp serisi beklenti dışı", "referans": "backtest", "kaynak": "backtest isabeti; en uzun seri olasılığı (kesin)"},
    {"id": "tutma_suresi", "ad": "Kaybedenler kazananlardan uzun tutulmuş", "referans": "yok", "kaynak": "Mann-Whitney U (kayıt içi karşılaştırma)"},
    {"id": "kayip_yogunlugu", "ad": "Saat / gün / sembolde yoğun kayıp", "referans": "yok", "kaynak": "Fisher kesin testi; Bonferroni"},
    {"id": "beklenti_alti", "ad": "Beklentinin altında", "referans": "backtest", "kaynak": "Dersler durumu; set 8 hf beklenti alarmı"},
)


# ---------------------------------------------------------------------------- istatistik yardımcıları (scipy yok)
def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_p(a: int, b: int, c: int, dd: int) -> float:
    """2x2 [[a, b], [c, d]] kesin iki yönlü Fisher p-değeri (olasılığı gözlenenden büyük olmayan tüm tabloların toplamı)."""
    n1, n2, k = a + b, c + dd, a + c
    n = n1 + n2
    lo, hi = max(0, k - n2), min(n1, k)
    lp = lambda x: _log_comb(k, x) + _log_comb(n - k, n1 - x) - _log_comb(n, n1)          # noqa: E731
    gozlenen = lp(a) + 1e-7
    return min(1.0, sum(math.exp(lp(x)) for x in range(lo, hi + 1) if lp(x) <= gozlenen))


def mann_whitney(x: list, y: list) -> Optional[dict]:
    """İki yönlü Mann-Whitney U (normal yaklaşım, süreklilik ve bağ düzeltmeli). -> {u, z, p} | None (varyans sıfır)."""
    n1, n2 = len(x), len(y)
    tum = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    N = n1 + n2
    sira = [0.0] * N
    bag = 0.0
    i = 0
    while i < N:
        j = i
        while j + 1 < N and tum[j + 1][0] == tum[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            sira[t] = r
        bag += (j - i + 1) ** 3 - (j - i + 1)
        i = j + 1
    r1 = sum(s for s, (_, g) in zip(sira, tum) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    var = n1 * n2 / 12.0 * ((N + 1) - bag / (N * (N - 1)))
    if var <= 0:
        return None
    z = (abs(u1 - mu) - 0.5) / math.sqrt(var)
    z = max(z, 0.0) * (1 if u1 >= mu else -1)
    return {"u": u1, "z": z, "p": min(1.0, math.erfc(abs(z) / math.sqrt(2.0)))}


def en_uzun_seri_p(n: int, q: float, L: int) -> float:
    """n bağımsız denemede 'kazanmayan' olasılığı q iken en uzun ardışık kazanmayan seri >= L olma olasılığı (kesin)."""
    if L <= 0:
        return 1.0
    if L > n:
        return 0.0
    # durum: şu anki seri uzunluğu (0..L-1); L'ye ulaşan yol emilir
    dagilim = [1.0] + [0.0] * (L - 1)
    for _ in range(n):
        yeni = [0.0] * L
        for s, pr in enumerate(dagilim):
            if pr == 0.0:
                continue
            yeni[0] += pr * (1.0 - q)                       # kazanç: seri sıfırlanır
            if s + 1 < L:
                yeni[s + 1] += pr * q                       # kazanmayan: seri uzar (L'ye ulaşan emilir)
        dagilim = yeni
    return max(0.0, min(1.0, 1.0 - sum(dagilim)))


def _bonf(p: float, m: int) -> float:
    return min(1.0, p * max(1, m))


def _p_metni(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def _seviye(p_ham: float, p_duz: float, referans: bool) -> Optional[str]:
    if referans:
        return "beklenti_disi" if p_duz < ALFA else ("incele" if p_ham < ALFA else None)
    return "incele" if p_duz < ALFA else ("izle" if p_ham < ALFA else None)


def _bulgu(kural: str, kapsam: str, seviye: str, baslik: str, metin: str, dayanak: dict, test: str, p_ham: float, m: int, referans: bool) -> dict:
    p_duz = _bonf(p_ham, m)
    return {"id": f"{kural}:{kapsam}:{dayanak.get('kova', '')}".rstrip(":"), "kural": kural, "kapsam": kapsam, "seviye": seviye, "seviye_etiket": SEVIYE_ETIKET[seviye],
            "baslik": baslik, "metin": metin, "dayanak": dayanak,
            "istatistik": {"test": test, "p_ham": d.sayi(p_ham), "test_sayisi": m, "p_duzeltilmis": d.sayi(p_duz), "duzeltme": "Bonferroni (aynı kural ailesi ve kapsam)" if m > 1 else "yok (tek test)",
                           "anlamli_ham": p_ham < ALFA, "anlamli_duzeltilmis": p_duz < ALFA, "alfa": ALFA},
            "referans": "backtest" if referans else "yok", "oneri": ONERI[seviye]}


# ---------------------------------------------------------------------------- yardımcılar
def _kazanmadi(s: dict) -> Optional[bool]:
    """Kazanmayan = R <= 0 (isabet R > 0 tanımının tamamlayıcısı; Dersler ile aynı). R yoksa None."""
    return None if s.get("r") is None else float(s["r"]) <= 0.0


def _tsi_giris(s: dict):
    return d.zaman_oku(s["giris_zamani"]).astimezone(ek.TSI)


def _tutma_saat(s: dict) -> float:
    return (d.zaman_oku(s["cikis_zamani"]) - d.zaman_oku(s["giris_zamani"])).total_seconds() / 3600.0


def _kisa(kimlik: str) -> str:
    return kimlik.replace("|", " · ")


# ---------------------------------------------------------------------------- kurallar
def kural_stop_ve_cikis(x: dict, kapsam: str) -> list:
    """x: dersler.json strateji kaydı (cikis_nedeni_sapmalari dolu olmalı)."""
    sap = x.get("cikis_nedeni_sapmalari") or []
    n = x["islem"]
    out = []
    stop = [s for s in sap if "stop" in s["neden"]]
    if stop:
        k = sum(s["islem"] for s in stop)
        q = sum(s["beklenen_pay"] for s in stop)
        p = ders.binom_p(k, n, min(1.0, q))
        if k / n > q:
            sev = _seviye(p, p, True)
            if sev:
                out.append(_bulgu("stop_sikligi", kapsam, sev, "Stoplar beklenenden sık",
                                  f"{_kisa(kapsam)}: {n} işlemin {k} tanesi ({k / n * 100:.0f}%) stop ailesiyle kapandı; backtestte bu pay {q * 100:.0f}%. "
                                  f"Kesin binom {_p_metni(p)}. Neden: kayma/boşluk, veri ya da piyasa koşulu farkı olabilir; kök neden bu testle bilinmez.",
                                  {"islem": n, "stop_islem": k, "pay": k / n, "beklenen_pay": q, "nedenler": sorted(s["neden"] for s in stop)},
                                  "kesin iki yönlü binom", p, 1, True))
    digerleri = [s for s in sap if "stop" not in s["neden"]]
    m = len(digerleri)
    for s in digerleri:
        p = s["p_deger"]
        sev = _seviye(p, _bonf(p, m), True)
        if sev:
            yon = "sık" if s["pay"] > s["beklenen_pay"] else "seyrek"
            gorulmemis = s["beklenen_pay"] == 0.0
            out.append(_bulgu("cikis_nedeni", kapsam, sev, f"'{s['neden']}' çıkışı beklenenden {yon}",
                              f"{_kisa(kapsam)}: '{s['neden']}' çıkışı {n} işlemin {s['islem']} tanesinde ({s['pay'] * 100:.0f}%); backtestte "
                              + ("hiç görülmemişti" if gorulmemis else f"{s['beklenen_pay'] * 100:.0f}%") + f". Kesin binom {_p_metni(p)}, {m} nedenden biri.",
                              {"islem": n, "neden_islem": s["islem"], "pay": s["pay"], "beklenen_pay": s["beklenen_pay"], "kova": s["neden"]},
                              "kesin iki yönlü binom", p, m, True))
    return out


def _seri_bilgi(ls: list) -> Optional[tuple]:
    """Zaman sırasıyla (n, en uzun kazanmayan seri, şu anki seri). R'si olmayanlar dışarıda."""
    sirali = sorted((s for s in ls if _kazanmadi(s) is not None), key=lambda s: s["zaman"])
    if not sirali:
        return None
    en, simdi = 0, 0
    for s in sirali:
        simdi = simdi + 1 if _kazanmadi(s) else 0
        en = max(en, simdi)
    return len(sirali), en, simdi


def kural_kayip_serisi(ls: list, q: Optional[float], kapsam: str, q_kaynak: str) -> Optional[dict]:
    b = _seri_bilgi(ls)
    if b is None or q is None:
        return None
    n, L, simdi = b
    if n < MIN_ISLEM or L == 0 or not 0.0 < q < 1.0:
        return None
    p = en_uzun_seri_p(n, q, L)
    sev = _seviye(p, p, True)
    if not sev:
        return None
    return _bulgu("kayip_serisi", kapsam, sev, "Ardışık kayıp serisi beklenti dışı",
                  f"{_kisa(kapsam)}: {n} işlemde en uzun ardışık kazanmayan (R ≤ 0) seri {L}; backtest isabetiyle kazanmayan olasılığı {q * 100:.0f}% iken bu uzunlukta bir serinin "
                  f"şansla görülme olasılığı {_p_metni(p)}. Şu anki seri: {simdi}.",
                  {"islem": n, "en_uzun_seri": L, "su_anki_seri": simdi, "kazanmayan_olasiligi": q, "olasilik_kaynagi": q_kaynak}, "en uzun seri olasılığı (kesin dinamik program)", p, 1, True)


def kural_tutma(ls: list, kapsam: str) -> tuple:
    """-> (bulgu | None, atlanan neden | None)."""
    kay = [_tutma_saat(s) for s in ls if _kazanmadi(s) is True]
    kaz = [_tutma_saat(s) for s in ls if _kazanmadi(s) is False]
    if len(kay) < MIN_GRUP_TUTMA or len(kaz) < MIN_GRUP_TUTMA:
        return None, f"tutma süresi: kaybeden {len(kay)} / kazanan {len(kaz)} işlem, her grupta en az {MIN_GRUP_TUTMA} gerekir"
    mw = mann_whitney(kay, kaz)
    if mw is None:
        return None, "tutma süresi: varyans sıfır, test hesaplanamadı"
    med = lambda v: sorted(v)[len(v) // 2] if len(v) % 2 else (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2.0          # noqa: E731
    if med(kay) <= med(kaz):
        return None, None
    sev = _seviye(mw["p"], mw["p"], False)
    if not sev:
        return None, None
    return _bulgu("tutma_suresi", kapsam, sev, "Kaybedenler kazananlardan uzun tutulmuş",
                  f"{_kisa(kapsam)}: kaybeden {len(kay)} işlemin medyan tutma süresi {med(kay):.1f} saat, kazanan {len(kaz)} işlemin {med(kaz):.1f} saat. "
                  f"Mann-Whitney {_p_metni(mw['p'])}. Backtestte tutma süresi referansı yok: bu kayıt içi bir karşılaştırmadır.",
                  {"kaybeden_islem": len(kay), "kazanan_islem": len(kaz), "kaybeden_medyan_saat": med(kay), "kazanan_medyan_saat": med(kaz)},
                  "Mann-Whitney U (normal yaklaşım, iki yönlü)", mw["p"], 1, False), None


def _kova_anahtari(boyut: str, s: dict) -> str:
    if boyut == "saat":
        h = _tsi_giris(s).hour // SAAT_BLOK * SAAT_BLOK
        return f"{h:02d}:00–{h + SAAT_BLOK:02d}:00"
    if boyut == "gun":
        return GUN_ADI[_tsi_giris(s).weekday()]
    return s["sembol"]


BOYUT_ADI = {"saat": "giriş saati (TSİ)", "gun": "giriş günü (TSİ)", "sembol": "sembol"}


def kural_yogunluk(ls: list, kapsam: str) -> list:
    ls = [s for s in ls if _kazanmadi(s) is not None]
    out = []
    n = len(ls)
    for boyut in ("saat", "gun", "sembol"):
        kovalar = defaultdict(list)
        for s in ls:
            kovalar[_kova_anahtari(boyut, s)].append(s)
        uygun = {k: v for k, v in kovalar.items() if len(v) >= MIN_KOVA and n - len(v) >= MIN_KOVA}
        m = len(uygun)
        toplam_kaybeden = sum(1 for s in ls if _kazanmadi(s))
        for kova, v in sorted(uygun.items()):
            a = sum(1 for s in v if _kazanmadi(s))
            b = len(v) - a
            c = toplam_kaybeden - a
            dd = (n - len(v)) - c
            r_toplam = sum(float(s["r"]) for s in v)
            if a / len(v) <= c / (n - len(v)) or r_toplam >= 0:
                continue
            p = fisher_p(a, b, c, dd)
            sev = _seviye(p, _bonf(p, m), False)
            if sev:
                out.append(_bulgu("kayip_yogunlugu", kapsam, sev, f"Yoğun kayıp: {BOYUT_ADI[boyut]} {kova}",
                                  f"{_kisa(kapsam)}: {BOYUT_ADI[boyut]} {kova} kovasında {len(v)} işlemin {a} tanesi kazanmadı ({a / len(v) * 100:.0f}%); kalan {n - len(v)} işlemde "
                                  f"{c / (n - len(v)) * 100:.0f}%. Kovanın toplam R'si {r_toplam:+.1f}. Fisher {_p_metni(p)}, {m} kovadan biri. "
                                  f"Backtestte bu dağılımın referansı yok.",
                                  {"boyut": boyut, "kova": f"{boyut}:{kova}", "kova_islem": len(v), "kova_kazanmayan": a, "kalan_islem": n - len(v), "kalan_kazanmayan": c, "kova_toplam_r": r_toplam},
                                  "Fisher kesin testi (iki yönlü)", p, m, False))
    return out


def kural_beklenti_alti(x: dict, kapsam: str) -> Optional[dict]:
    if x.get("durum") != "altinda":
        return None
    it, rt = x.get("isabet_testi"), x.get("ort_r_testi")
    ps = [t["p_deger"] for t in (it, rt) if t and t.get("p_deger") is not None]
    return _bulgu("beklenti_alti", kapsam, "beklenti_disi", "Dersler: beklentinin altında",
                  f"{_kisa(kapsam)}: Dersler durumu 'beklentinin altında' ({x.get('durum_neden')}). " + " ".join(x.get("aciklamalar") or []),
                  {"islem": x["islem"], "isabet": x.get("isabet"), "ort_r": x.get("ort_r"), "backtest_isabet": (x.get("beklenti") or {}).get("isabet"),
                   "backtest_ort_r": (x.get("beklenti") or {}).get("ort_r"), "isabet_p": it.get("p_deger") if it else None, "ort_r_p": rt.get("p_deger") if rt else None},
                  "Dersler: kesin binom + Welch t (düzeltme yok, onaylı kural)", min(ps) if ps else 0.0, 1, True)


def kural_set_alarm(set_konum: Optional[dict]) -> Optional[dict]:
    b = (set_konum or {}).get("8")
    if not b:
        return None
    bozuk = [(ad, m) for ad, m in (("net getiri", b["net_getiri"]), ("düşüş", b["max_dusus"])) if m["alarm"]]
    if not bozuk:
        return None
    return _bulgu("beklenti_alti", "SET", "beklenti_disi", "Set 8 haftalık beklenti alarmı",
                  "SET: 8 haftalık pencerede " + "; ".join(f"{ad} {m['deger'] * 100:+.2f}% ({m['bant']})" for ad, m in bozuk) + " — backtest alarm eşiğinin dışında.",
                  {"net_getiri": b["net_getiri"]["deger"], "net_bant": b["net_getiri"]["bant"], "max_dusus": b["max_dusus"]["deger"], "dusus_bant": b["max_dusus"]["bant"]},
                  "beklenti aralığı alarm eşiği (%5 / %95 yüzdeliği)", 0.0, 1, True)


# ---------------------------------------------------------------------------- dosya
def olustur(kaynak: str, zaman: str, kimlikler: list, satirlar: list, dersler: Optional[dict], set_konum: Optional[dict] = None) -> dict:
    ders_of = {x["kimlik"]: x for x in (dersler or {}).get("stratejiler", [])}
    bulgular, atlanan = [], []
    for kim in kimlikler:
        ls = [s for s in satirlar if s["kimlik"] == kim]
        x = ders_of.get(kim)
        if len(ls) < MIN_ISLEM:
            atlanan.append({"kural": "tümü", "kapsam": kim, "neden": f"örnek az: {len(ls)} kapanan işlem < {MIN_ISLEM}; stop sıklığı, çıkış nedeni, kayıp serisi, tutma süresi ve yoğunluk testleri çalışmadı"})
            continue
        if x is None or x.get("beklenti") is None:
            atlanan.append({"kural": "stop_sikligi, cikis_nedeni, kayip_serisi, beklenti_alti", "kapsam": kim, "neden": "backtest referansı yok: referans gerektiren kurallar çalışmadı"})
        else:
            bulgular += kural_stop_ve_cikis(x, kim)
            q = 1.0 - x["beklenti"]["isabet"]
            kb = kural_kayip_serisi(ls, q, kim, "backtest isabeti (strateji)")
            if kb:
                bulgular.append(kb)
            ba = kural_beklenti_alti(x, kim)
            if ba:
                bulgular.append(ba)
        tb, tn = kural_tutma(ls, kim)
        if tb:
            bulgular.append(tb)
        if tn:
            atlanan.append({"kural": "tutma_suresi", "kapsam": kim, "neden": tn})
        bulgular += kural_yogunluk(ls, kim)
    # --- set
    if len(satirlar) < MIN_ISLEM:
        atlanan.append({"kural": "tümü", "kapsam": "SET", "neden": f"örnek az: set toplamında {len(satirlar)} kapanan işlem < {MIN_ISLEM}; set kapsamlı testler çalışmadı"})
    else:
        kay = [x for x in (dersler or {}).get("stratejiler", []) if x.get("beklenti") is not None and (x.get("r_olculen") or 0) > 0]
        N = sum(x["r_olculen"] for x in kay)
        q = (1.0 - sum(x["beklenti"]["isabet"] * x["r_olculen"] for x in kay) / N) if N else None
        kb = kural_kayip_serisi([s for s in satirlar if s["kimlik"] in {x["kimlik"] for x in kay}], q, "SET", "işlem karışımına göre havuzlanmış backtest isabeti")
        if kb:
            bulgular.append(kb)
        bulgular += kural_yogunluk(satirlar, "SET")
    ka = kural_set_alarm(set_konum)
    if ka:
        bulgular.append(ka)
    bulgular.sort(key=lambda b: (SEVIYE_SIRA[b["seviye"]], b["istatistik"]["p_duzeltilmis"] if b["istatistik"]["p_duzeltilmis"] is not None else 1.0, b["kapsam"]))
    sayim = {s: sum(1 for b in bulgular if b["seviye"] == s) for s in SEVIYE_SIRA}
    return {**d._zarf("koc", kaynak, zaman), "min_islem": MIN_ISLEM, "alfa": ALFA, "min_kova": MIN_KOVA, "min_grup_tutma": MIN_GRUP_TUTMA,
            "kurallar": [dict(k) for k in KURALLAR], "bulgular": bulgular, "atlanan": atlanan, "sayim": sayim,
            "yontem": ("Kurallı tespit (metin şablonu, LLM yok). Yalnız kapanmış işlemler; zaman dilimi TSİ. Her bulguda dayanak sayılar, ham p ve çoklu-test düzeltmeli p. "
                       "Örnek azsa kural çalışmaz ve `atlanan`'a yazılır. Bulgular BİLGİDİR, karar değildir."),
            "uyari": ("Koç risk artırma, pozisyon büyütme, kayıp sonrası ekleme ya da Kelly ile büyütme ÖNERMEZ (martingale/DCA yasak) ve geriye dönük strateji/ayar seçimi önermez; "
                      "öneriler yalnız 'incele / izle / beklenti dışı' düzeyindedir. Değişiklik: walk-forward + kullanıcı onayı (karar 4)."),
            "kaynak_not": ("backtest kaynağı: referans kilitli dönemi de içerir; bu bağımsız bir sınav değildir (bağımsız sınav paper'dır)." if kaynak == "backtest" else None)}
