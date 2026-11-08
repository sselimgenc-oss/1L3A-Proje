"""Karne (radar) — pano öncelik 6a. Hesap BURADA (motor tarafı); pano yalnız çizer/biçimler.

Strateji ve set başına 6 eksen, her biri 0-100 puan. EŞİKLER eski panonunkiler (%10 düşüş, PSR>%95) DEĞİL; projenin kendi kurallarındandır
(kullanıcı kararı 2026-11-08). Her eksenin formülü ve eşik kaynağı `eksen_tanimlari` içinde (json) yazılıdır.

  getiri       Son 8 (yoksa 4) haftalık net getirinin backtest beklenti aralığındaki yüzdelik konumu (sonuclar/final/beklenti_araliklari.csv;
               aralık stratejiler.json `beklenti`'de). Puan = %5/%25/%50/%75/%95 noktaları arasında doğrusal yüzdelik; %5 altı 0'a, %95 üstü 100'e iner.
               Eşik: 8 hf alarm eşiği (= %5 yüzdeliği; OZET.md "Alarm eşiği"): alarm yoksa "gecti".
  risk         Aynı pencerenin en büyük düşüşü, beklenti aralığındaki yüzdelik konumu TERSİNE: puan = 100 - yüzdelik (düşüş küçüldükçe puan artar).
               Eşik: 8 hf düşüş alarm eşiği (= %95 yüzdeliği).
  kalite       PF (R tabanlı) = Σ(R>0) / -Σ(R<0). Puan = clamp(250 x (PF - 1), 0, 100): PF 1.0 -> 0, 1.2 -> 50, 1.4 -> 100. Eşik: PF >= 1.2
               (sonuclar/evren/ON_KAYIT.md "Geçme ölçütleri" 1). Örnek: >= 30 kapanan işlem (Dersler onaylı asgari, 2026-11-08).
  isabet       Gözlenen isabet (R>0 payı) ↔ backtest isabeti (beklenti_islem_referansi.csv): z = (gözlenen - beklenen) / sqrt(p(1-p)/n);
               puan = clamp(50 + 50 x z / 1.96, 0, 100). 1.96 = Dersler alfa 0.05 (iki yönlü): z <= -1.96 -> 0 ("kaldi"), z >= +1.96 -> 100.
               Dersler'in kesin binom p-değeri `ayrinti`'dedir (strateji). Set: işlem karışımına göre havuzlanmış beklenti.
  uyum         Beklentiye uyum: ortalama R'nin backtest ortalama R'sine göre Welch t'si (Dersler ile aynı test). Puan = clamp(100 x (1 - max(0, -t)/1.96), 0, 100):
               beklentiyi tutturan ya da aşan 100; anlamlı biçimde altında (t <= -1.96) 0. Tek yönlü ceza: beklentinin ÜSTÜ cezalanmaz.
               Set: havuzlanmış beklenti, backtest std'siyle z.
  saglik       Veri/çalışma sağlığı: geçen kontrol / ölçülen kontrol x 100. Strateji: çalışıyor mu (durum), veri akışı bayat mı. Set: motor durumu,
               veri bayatlığı, backtest bütünlüğü (sha256 ↔ kayıt), kesinti <= 24 saat (kullanıcı kararı 2026-11-08), sert limit ihlali yok (kabul listesi).
               Backtest kaynağında ölçülmez (null + neden).

Örnek azsa (kapanan işlem < 30 ya da beklenti penceresi dolmadıysa) ilgili eksen `puan: null` + `neden`. Eksik eksenler ortalamaya GİRMEZ ve
tek bir "genel puan" YOKTUR (genel_puan: null): envanterdeki risk notları (veri azken puan şişmesi, Goodhart) ve karar 13/24 kapıları nedeniyle karne
YALNIZ BİLGİDİR; strateji seçme/eleme ölçütü olarak kullanılmaz.
"""
from __future__ import annotations

import math
from typing import Optional

from motor.canli import dersler as ders
from motor.canli import durum as d

MIN_ISLEM = ders.MIN_ISLEM_DERS          # 30, kullanıcı onaylı 2026-11-08
ALFA = ders.ALFA                         # 0.05
Z_KRIT = 1.959964                        # iki yönlü normal, alfa 0.05
PF_ESIK = 1.2                            # sonuclar/evren/ON_KAYIT.md geçme ölçütü 1
KESINTI_LIMIT_SAAT = 24.0                # kullanıcı kararı 2026-11-08 (aylik_rapor.KESINTI_LIMIT_SAAT)

EKSENLER = (
    {"id": "getiri", "ad": "Getiri",
     "formul": "net getirinin (8 hf, yoksa 4 hf) backtest beklenti aralığındaki yüzdelik konumu; %5/%25/%50/%75/%95 arası doğrusal, %5 altı 0'a ve %95 üstü 100'e iner",
     "esik": "8 hf net getiri alarm eşiği (= %5 yüzdeliği)", "esik_kaynagi": "sonuclar/final/beklenti_araliklari.csv; sonuclar/final/OZET.md (alarm eşiği)",
     "min_ornek": "beklenti penceresi dolu (8 hf = 56 gün; yoksa 4 hf = 28 gün)"},
    {"id": "risk", "ad": "Risk / düşüş",
     "formul": "aynı pencerenin en büyük düşüşünün beklenti aralığındaki yüzdeliği TERSİNE: puan = 100 - yüzdelik",
     "esik": "8 hf düşüş alarm eşiği (= %95 yüzdeliği)", "esik_kaynagi": "sonuclar/final/beklenti_araliklari.csv; sonuclar/final/OZET.md (alarm eşiği)",
     "min_ornek": "beklenti penceresi dolu (8 hf; yoksa 4 hf)"},
    {"id": "kalite", "ad": "Kâr kalitesi (PF)",
     "formul": f"PF(R) = Σ(R>0) / -Σ(R<0); puan = clamp(250 x (PF - 1), 0, 100)  [PF 1.0 -> 0, {PF_ESIK} -> 50, 1.4 -> 100]",
     "esik": f"PF >= {PF_ESIK}", "esik_kaynagi": "sonuclar/evren/ON_KAYIT.md Geçme ölçütleri 1 (net > 0, PF >= 1.2)",
     "min_ornek": f"{MIN_ISLEM} kapanan işlem (R ölçülen) ve en az bir zarar eden işlem"},
    {"id": "isabet", "ad": "İsabet",
     "formul": "z = (gözlenen isabet - backtest isabeti) / sqrt(p(1-p)/n); puan = clamp(50 + 50 x z / 1.96, 0, 100)",
     "esik": "z > -1.96 (iki yönlü alfa 0.05 altında anlamlı düşüş yok)", "esik_kaynagi": f"Dersler alfa {ALFA} (kullanıcı onaylı 2026-11-08); sonuclar/final/beklenti_islem_referansi.csv",
     "min_ornek": f"{MIN_ISLEM} kapanan işlem (R ölçülen)"},
    {"id": "uyum", "ad": "Beklentiye uyum (ort. R)",
     "formul": "t = ortalama R'nin backtest ortalama R'sine göre Welch t'si; puan = clamp(100 x (1 - max(0, -t)/1.96), 0, 100) (tek yönlü ceza)",
     "esik": "t > -1.96 (ortalama R beklentinin anlamlı altında değil)", "esik_kaynagi": f"Dersler Welch t + alfa {ALFA} (kullanıcı onaylı 2026-11-08); beklenti_islem_referansi.csv",
     "min_ornek": f"{MIN_ISLEM} kapanan işlem (R ölçülen)"},
    {"id": "saglik", "ad": "Veri / çalışma sağlığı",
     "formul": "geçen kontrol / ölçülen kontrol x 100 (kontroller eksenin `kontroller` listesinde)",
     "esik": "tüm ölçülen kontroller geçer", "esik_kaynagi": "saglik.json bayatlık eşiği (2 x mum + 10 dk); butunluk.json; kullanıcı kararı 2026-11-08 (kesinti <= 24 saat, sert limit)",
     "min_ornek": "en az bir ölçülen kontrol; backtest kaynağında ölçülmez"},
)
EKSEN = {e["id"]: e for e in EKSENLER}


# ---------------------------------------------------------------------------- puan fonksiyonları
def kis(x: float) -> float:
    return max(0.0, min(100.0, x))


def yuzdelik_puan(v: float, q: dict) -> float:
    """Değerin beklenti aralığındaki yüzdelik konumu (0-100). q: {p05,p25,p50,p75,p95}. %5 altı 0'a, %95 üstü 100'e doğrusal iner (bir segment genişliğinde)."""
    xs = [q[k] for k in ("p05", "p25", "p50", "p75", "p95")]
    ys = [5.0, 25.0, 50.0, 75.0, 95.0]
    if v <= xs[0]:
        if v == xs[0]:
            return 5.0
        gen = xs[1] - xs[0]
        return 0.0 if gen <= 0 else max(0.0, 5.0 - 5.0 * (xs[0] - v) / gen)
    if v >= xs[4]:
        if v == xs[4]:
            return 95.0
        gen = xs[4] - xs[3]
        return 100.0 if gen <= 0 else min(100.0, 95.0 + 5.0 * (v - xs[4]) / gen)
    for i in range(4):
        if v <= xs[i + 1]:
            if xs[i + 1] == xs[i]:
                return ys[i + 1]
            return ys[i] + (v - xs[i]) / (xs[i + 1] - xs[i]) * (ys[i + 1] - ys[i])
    raise AssertionError("yuzdelik_puan: erişilemez")


def _eksen(id_: str, puan: Optional[float], ozet: Optional[str], *, deger: Optional[float] = None, esik: Optional[str] = None,
           neden: Optional[str] = None, ayrinti: Optional[dict] = None, kontroller: Optional[list] = None) -> dict:
    """esik: 'gecti' | 'kaldi' | 'esik_yok' | None (ölçülmedi)."""
    out = {"id": id_, "ad": EKSEN[id_]["ad"], "puan": None if puan is None else d.sayi(round(puan, 1)), "deger": d.sayi(deger), "ozet": ozet,
           "esik_durumu": esik, "neden": neden, "ayrinti": ayrinti or {}}
    if kontroller is not None:
        out["kontroller"] = kontroller
    return out


def _yok(id_: str, neden: str) -> dict:
    return _eksen(id_, None, None, neden=neden)


# ---------------------------------------------------------------------------- getiri / risk
def _pencere(konum: Optional[dict]) -> Optional[str]:
    if not konum:
        return None
    return "8" if "8" in konum else ("4" if "4" in konum else None)


def getiri_risk(konum: Optional[dict]) -> tuple:
    """konum: stratejiler.json `beklenti` ({'4':{net_getiri,max_dusus},'8':{...}}). -> (getiri ekseni, risk ekseni)."""
    hf = _pencere(konum)
    if hf is None:
        neden = "beklenti penceresi dolmadı (en az 28 günlük seri gerekir; 8 hafta = 56 gün)"
        return _yok("getiri", neden), _yok("risk", neden)
    n, dd = konum[hf]["net_getiri"], konum[hf]["max_dusus"]
    yz_n = yuzdelik_puan(n["deger"], n)
    yz_d = yuzdelik_puan(dd["deger"], dd)
    es = lambda b: "esik_yok" if b["alarm"] is None else ("kaldi" if b["alarm"] else "gecti")           # noqa: E731
    ek_not = "" if hf == "8" else " (4 haftalık pencerede alarm eşiği tanımlı değil)"
    g = _eksen("getiri", yz_n, f"{hf} hf net getiri {n['deger'] * 100:+.2f}% (backtest %5-%95: {n['p05'] * 100:+.1f}% … {n['p95'] * 100:+.1f}%; yüzdelik ≈ {yz_n:.0f}){ek_not}",
               deger=n["deger"], esik=es(n), ayrinti={"pencere_hafta": int(hf), "bant": n["bant"], "yuzdelik": d.sayi(round(yz_n, 1)), "p05": n["p05"], "p50": n["p50"], "p95": n["p95"]})
    r = _eksen("risk", 100.0 - yz_d, f"{hf} hf en büyük düşüş {dd['deger'] * 100:.2f}% (backtest %5-%95: {dd['p05'] * 100:.1f}% … {dd['p95'] * 100:.1f}%; yüzdelik ≈ {yz_d:.0f}){ek_not}",
               deger=dd["deger"], esik=es(dd), ayrinti={"pencere_hafta": int(hf), "bant": dd["bant"], "yuzdelik": d.sayi(round(yz_d, 1)), "p05": dd["p05"], "p50": dd["p50"], "p95": dd["p95"]})
    return g, r


# ---------------------------------------------------------------------------- kalite
def kalite(satirlar: list) -> dict:
    r = [float(s["r"]) for s in satirlar if s.get("r") is not None]
    if len(r) < MIN_ISLEM:
        return _yok("kalite", f"örnek az: R ölçülen işlem {len(r)} < {MIN_ISLEM}")
    kar, zr = sum(x for x in r if x > 0), sum(x for x in r if x < 0)
    if zr >= 0:
        return _yok("kalite", "PF hesaplanamadı: zarar eden işlem yok")
    pf = kar / -zr
    return _eksen("kalite", kis(250.0 * (pf - 1.0)), f"PF(R) {pf:.2f} ({len(r)} işlem; eşik ≥ {PF_ESIK})", deger=pf, esik="gecti" if pf >= PF_ESIK else "kaldi",
                  ayrinti={"n": len(r), "pf_r": d.sayi(pf), "esik_pf": PF_ESIK})


# ---------------------------------------------------------------------------- isabet / uyum
def _normal_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def isabet_uyum_strateji(x: Optional[dict]) -> tuple:
    """x: dersler.json strateji kaydı (ya da None). -> (isabet ekseni, uyum ekseni)."""
    if x is None:
        n = "Dersler kaydı yok"
        return _yok("isabet", n), _yok("uyum", n)
    ref = x.get("beklenti")
    if ref is None:
        n = x.get("durum_neden") or "backtest referansı yok"
        return _yok("isabet", n), _yok("uyum", n)
    n_r = x.get("r_olculen") or 0
    if n_r < MIN_ISLEM or x.get("isabet") is None:
        n = f"örnek az: R ölçülen işlem {n_r} < {MIN_ISLEM}"
        return _yok("isabet", n), _yok("uyum", n)
    p0 = ref["isabet"]
    if not 0.0 < p0 < 1.0:
        isa = _yok("isabet", f"backtest isabeti {p0:.2f}: varyans sıfır, z hesaplanamadı")
    else:
        z = (x["isabet"] - p0) / math.sqrt(p0 * (1 - p0) / n_r)
        t = x.get("isabet_testi") or {}
        isa = _eksen("isabet", kis(50.0 + 50.0 * z / Z_KRIT), f"isabet {x['isabet'] * 100:.0f}% (backtest {p0 * 100:.0f}%, {n_r} işlem, z {z:+.2f})", deger=x["isabet"],
                     esik="kaldi" if z <= -Z_KRIT else "gecti", ayrinti={"n": n_r, "z": d.sayi(round(z, 3)), "backtest_isabet": p0, "binom_p": t.get("p_deger"), "binom_yon": t.get("yon")})
    tt = x.get("ort_r_testi")
    if tt is None:
        uy = _yok("uyum", x.get("test_neden") or "ortalama R testi hesaplanamadı")
    else:
        t_ = tt["t"]
        uy = _eksen("uyum", kis(100.0 * (1.0 - max(0.0, -t_) / Z_KRIT)),
                    f"ort. R {x['ort_r']:+.2f} (backtest {ref['ort_r']:+.2f}, t {t_:+.2f}); Dersler: {x.get('durum_etiket') or '—'}", deger=x["ort_r"],
                    esik="kaldi" if t_ <= -Z_KRIT else "gecti", ayrinti={"n": n_r, "t": d.sayi(round(t_, 3)), "welch_p": tt.get("p_deger"), "backtest_ort_r": ref["ort_r"],
                                                                         "dersler_durumu": x.get("durum")})
    return isa, uy


def isabet_uyum_set(dersler: Optional[dict]) -> tuple:
    """Set: stratejilerin beklentileri GERÇEKLEŞEN işlem karışımına göre havuzlanır (Σ n_i x beklenti_i)."""
    kay = [x for x in (dersler or {}).get("stratejiler", []) if x.get("beklenti") is not None and (x.get("r_olculen") or 0) > 0 and x.get("isabet") is not None]
    N = sum(x["r_olculen"] for x in kay)
    if N < MIN_ISLEM:
        n = f"örnek az: set toplamında R ölçülen işlem {N} < {MIN_ISLEM}"
        return _yok("isabet", n), _yok("uyum", n)
    k = sum(x["isabet"] * x["r_olculen"] for x in kay)
    E = sum(x["beklenti"]["isabet"] * x["r_olculen"] for x in kay)
    V = sum(x["r_olculen"] * x["beklenti"]["isabet"] * (1 - x["beklenti"]["isabet"]) for x in kay)
    if V <= 0:
        isa = _yok("isabet", "havuzlanmış varyans sıfır")
    else:
        z = (k - E) / math.sqrt(V)
        isa = _eksen("isabet", kis(50.0 + 50.0 * z / Z_KRIT), f"isabet {k / N * 100:.0f}% (işlem karışımına göre beklenen {E / N * 100:.0f}%, {N} işlem, z {z:+.2f})",
                     deger=k / N, esik="kaldi" if z <= -Z_KRIT else "gecti",
                     ayrinti={"n": N, "z": d.sayi(round(z, 3)), "beklenen_isabet": d.sayi(E / N), "normal_p": d.sayi(_normal_p(z)), "yontem": "havuzlanmış binom (normal yaklaşım)"})
    se2 = sum(x["r_olculen"] * (x["beklenti"].get("std_r") or 0.0) ** 2 for x in kay)
    gozlenen = sum((x["ort_r"] or 0.0) * x["r_olculen"] for x in kay) / N
    beklenen = sum(x["beklenti"]["ort_r"] * x["r_olculen"] for x in kay) / N
    if se2 <= 0:
        uy = _yok("uyum", "havuzlanmış backtest std'si sıfır")
    else:
        t_ = (gozlenen - beklenen) / (math.sqrt(se2) / N)
        uy = _eksen("uyum", kis(100.0 * (1.0 - max(0.0, -t_) / Z_KRIT)), f"ort. R {gozlenen:+.2f} (işlem karışımına göre beklenen {beklenen:+.2f}, {N} işlem, z {t_:+.2f})",
                    deger=gozlenen, esik="kaldi" if t_ <= -Z_KRIT else "gecti",
                    ayrinti={"n": N, "z": d.sayi(round(t_, 3)), "beklenen_ort_r": d.sayi(beklenen), "normal_p": d.sayi(_normal_p(t_)),
                             "yontem": "havuzlanmış ortalama R, backtest std'siyle z (normal yaklaşım)"})
    return isa, uy


# ---------------------------------------------------------------------------- sağlık
def kontrol(id_: str, ad: str, gecti: Optional[bool], deger: Optional[str], kaynak: str, neden: Optional[str] = None) -> dict:
    return {"id": id_, "ad": ad, "gecti": gecti, "deger": deger, "kaynak": kaynak, "neden": neden}


def saglik_strateji_kontrolleri(durum: str, veri_satirlari: list) -> list:
    """durum: stratejiler.json `durum` ('calisiyor' | 'veri yok: ...'); veri_satirlari: saglik.json veri[] içinde bu stratejinin sembol/tf eşleşmeleri."""
    k = [kontrol("calisiyor", "Strateji çalışıyor", durum == "calisiyor", durum, "stratejiler.json durum")]
    if not veri_satirlari:
        k.append(kontrol("veri_taze", "Veri akışı taze", None, None, "saglik.json veri[] (bayat)", "bu stratejinin veri satırı saglik.json'da eşlenemedi"))
    else:
        bayat = [f"{v['sembol']} {v['tf']}" for v in veri_satirlari if v["bayat"]]
        k.append(kontrol("veri_taze", "Veri akışı taze", not bayat, f"{len(veri_satirlari)} seri" + (f"; bayat: {', '.join(bayat)}" if bayat else ""), "saglik.json veri[] (bayat)"))
    return k


def saglik_set_kontrolleri(saglik: dict, butunluk: Optional[dict], kabul: Optional[dict]) -> list:
    k = [kontrol("motor_durumu", "Motor durumu ok", saglik["durum"] == "ok", saglik["durum"], "saglik.json durum")]
    bayat = [f"{v['sembol']} {v['tf']}" for v in saglik["veri"] if v["bayat"]]
    k.append(kontrol("veri_taze", "Hiçbir veri serisi bayat değil", (not bayat) if saglik["veri"] else None, f"{len(saglik['veri'])} seri" + (f"; bayat: {', '.join(bayat)}" if bayat else ""),
                     "saglik.json veri[] (bayat)", None if saglik["veri"] else "veri serisi kaydı yok"))
    if butunluk is None:
        k.append(kontrol("butunluk", "Backtest bütünlüğü eşleşiyor", None, None, "butunluk.json", "butunluk.json yok"))
    else:
        g = butunluk.get("genel_durum")
        k.append(kontrol("butunluk", "Backtest bütünlüğü eşleşiyor", {"eslesti": True, "uyusmuyor": False}.get(g), g, "butunluk.json genel_durum",
                         None if g in ("eslesti", "uyusmuyor") else f"genel_durum {g!r}: ölçülemedi"))
    if kabul is None:
        k.append(kontrol("kesinti", f"Toplam kesinti <= {KESINTI_LIMIT_SAAT:.0f} saat", None, None, "aylik_rapor.kabul_listesi.kesinti", "kabul listesi yok"))
        k.append(kontrol("sert_limit", "Sert limit ihlali yok", None, None, "aylik_rapor.kabul_listesi (sert_limit)", "kabul listesi yok"))
        return k
    ks = kabul["kesinti"]
    if ks["saat"] is not None:
        k.append(kontrol("kesinti", f"Toplam kesinti <= {KESINTI_LIMIT_SAAT:.0f} saat", ks["saat"] <= KESINTI_LIMIT_SAAT, f"{ks['saat']:.1f} saat",
                         "aylik_rapor.kabul_listesi.kesinti; kullanıcı kararı 2026-11-08"))
    elif ks["alt_sinir_saat"] > KESINTI_LIMIT_SAAT:
        k.append(kontrol("kesinti", f"Toplam kesinti <= {KESINTI_LIMIT_SAAT:.0f} saat", False, f"≥ {ks['alt_sinir_saat']:.1f} saat (alt sınır)", "aylik_rapor.kabul_listesi.kesinti", ks["neden"]))
    else:
        k.append(kontrol("kesinti", f"Toplam kesinti <= {KESINTI_LIMIT_SAAT:.0f} saat", None, f"≥ {ks['alt_sinir_saat']:.1f} saat (alt sınır)", "aylik_rapor.kabul_listesi.kesinti",
                         ks["neden"] or "ölçülemedi"))
    sl = next((x for x in kabul["kalemler"] if x["id"] == "sert_limit"), None)
    k.append(kontrol("sert_limit", "Sert limit ihlali yok", None if sl is None else sl["durum"] == "gecti", None if sl is None else sl["deger"], "aylik_rapor.kabul_listesi (sert_limit)",
                     "kalem yok" if sl is None else None))
    return k


def saglik_ekseni(kontroller: Optional[list], neden: Optional[str]) -> dict:
    if kontroller is None:
        return _yok("saglik", neden or "sağlık ölçülmedi")
    olculen = [c for c in kontroller if c["gecti"] is not None]
    if not olculen:
        return _yok("saglik", "ölçülen kontrol yok: " + "; ".join(f"{c['id']}: {c['neden']}" for c in kontroller if c.get("neden")))
    gecen = sum(1 for c in olculen if c["gecti"])
    return _eksen("saglik", 100.0 * gecen / len(olculen), f"{gecen}/{len(olculen)} ölçülen kontrol geçti" + (f" ({len(kontroller) - len(olculen)} ölçülemedi)" if len(olculen) < len(kontroller) else ""),
                  deger=gecen / len(olculen), esik="gecti" if gecen == len(olculen) else "kaldi", kontroller=kontroller)


# ---------------------------------------------------------------------------- dosya
def _kayit(kimlik: str, tur: str, ajan: Optional[str], n_islem: int, eksenler: list) -> dict:
    return {"kimlik": kimlik, "tur": tur, "ajan": ajan, "islem": n_islem, "eksenler": eksenler, "olculen_eksen": sum(1 for e in eksenler if e["puan"] is not None)}


def olustur(kaynak: str, zaman: str, stratejiler: list, set_konum: Optional[dict], satirlar: list, dersler: Optional[dict],
            saglik_strateji: Optional[dict] = None, saglik_set: Optional[list] = None, saglik_neden: Optional[str] = None) -> dict:
    """stratejiler: [{kimlik, ajan, beklenti}] (stratejiler.json); satirlar: islemler.jsonl satırları; dersler: dersler.json içeriği.
    saglik_strateji: {kimlik: kontrol listesi} | None; saglik_set: kontrol listesi | None; saglik_neden: ölçülmediyse nedeni."""
    ders_of = {x["kimlik"]: x for x in (dersler or {}).get("stratejiler", [])}
    kayitlar = []
    for s in stratejiler:
        kim = s["kimlik"]
        ls = [x for x in satirlar if x["kimlik"] == kim]
        g, r = getiri_risk(s.get("beklenti"))
        isa, uy = isabet_uyum_strateji(ders_of.get(kim))
        sg = saglik_ekseni(None if saglik_strateji is None else saglik_strateji.get(kim), saglik_neden)
        kayitlar.append(_kayit(kim, "strateji", s.get("ajan"), len(ls), [g, r, kalite(ls), isa, uy, sg]))
    g, r = getiri_risk(set_konum)
    isa, uy = isabet_uyum_set(dersler)
    sg = saglik_ekseni(saglik_set, saglik_neden)
    set_k = _kayit("SET", "set", None, len(satirlar), [g, r, kalite(satirlar), isa, uy, sg])
    return {**d._zarf("karne", kaynak, zaman), "puan_olcegi": "0-100 (eksen başına; tek genel puan yok)", "genel_puan": None,
            "genel_puan_neden": "Bilerek yok: eksik eksenler ortalamayı şişirir ve tek sayı Goodhart riskidir; karne seçim/eleme ölçütü değildir (karar 13/24 kapıları ayrı).",
            "min_islem": MIN_ISLEM, "alfa": ALFA,
            "eksen_tanimlari": [dict(e) for e in EKSENLER],
            "eksen_sirasi": [e["id"] for e in EKSENLER],
            "yontem": ("Eşikler projenin kendi kurallarındandır (ON_KAYIT geçme ölçütleri, beklenti aralıkları, Dersler testleri, paper kabul kararları); eski pano eşikleri "
                       "(%10 düşüş, PSR>%95) kullanılmaz. Örnek azsa eksen null + neden. Karne YALNIZ BİLGİDİR."),
            "kaynak_not": ("backtest kaynağı: referans kilitli dönemi de içerir; isabet/uyum bağımsız sınav değildir. Sağlık ekseni backtestte ölçülmez."
                           if kaynak == "backtest" else None),
            "set": set_k, "stratejiler": kayitlar}
