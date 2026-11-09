"""Kağıt hesaplar paneli için veri üretir (claude.ai panelinin veritabanına yazılacak JSON dosyaları).

Beş botun durum dallarını yerel git kopyalarından okur, ortak biçime çevirir:
  hesaplar/<id>  : özet metrikler, sermaye eğrisi, alt kollar, strateji kırılımı, bot sağlığı
  islemler/<id>  : kapanan işlemler (en yeni 400), açık pozisyonlar, bekleyen emirler
  meta/ozet      : güncelleme zamanı, beş hesabın eşit ağırlıklı toplamı

  python -m karsilastirma.panel_veri --cikis <dizin>
"""
import argparse
import io
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[2]  # /home/user
SAHIP = "sselimgenc-oss"
MAKS_ISLEM = 1000

# Kullanıcıya gösterilen strateji adları (botların içindeki kodlar değişmez; kod küçük etiket olarak kalır)
ISIM = {
    "S1": "Trend Molası", "S2": "Sıkışma Patlaması", "S3": "Dipten Sekme", "S4": "Gizli Güç",
    "BTC trend": "BTC Pusulası", "ABD trend portföyü": "ABD Güçlüler Sepeti", "Emtia ETF düşük vol.": "Sakin Emtialar",
    "KGT": "Seviye Kırılımı", "KMN": "Güçlü–Zayıf Sepeti",
    "A1": "Trend Avcısı (4 saatlik)", "A2": "Trend Avcısı (günlük)", "A": "Trend Avcısı", "B": "Panik Dönüşü",
    "S10": "Akşam Momentumu", "S13": "Tuzak Kırılım", "S15": "Trend Günü Molası",
}


def kismi_birlestir(kap):
    """Kısmi kâr satırlarını (algo "partial", strateji "tp1") ana işleme ekler: bir işlem tek satır, toplam K/Z ve R.
    Ana işlem henüz açıksa kısmi satır `kismi=True` işaretiyle kalır (kârı toplama girer, işlem sayısına girmez)."""
    kis = lambda x: any(w in str(x.get("n") or "").lower() for w in ("partial", "tp1", "kısmi"))
    ana = {}
    for x in kap:
        if not kis(x):
            ana.setdefault((x.get("s"), x.get("alt"), x.get("v"), x.get("gt")), x)
    out = []
    for x in kap:
        if not kis(x):
            out.append(x)
            continue
        a = ana.get((x.get("s"), x.get("alt"), x.get("v"), x.get("gt")))
        if a is None:
            out.append(dict(x, kismi=True))
            continue
        for c in ("k", "R"):
            if x.get(c) is not None:
                a[c] = round((a.get(c) or 0) + x[c], 3)
        a["n"] = (a.get("n") or "") + " + kısmi kâr"
    return out


def adlandir(liste):
    """s alanını kullanıcı dostu ada çevirir; eski kodu `kod` alanında saklar."""
    for x in liste:
        kod = str(x.get("s") or "")
        x["kod"] = kod
        x["s"] = ISIM.get(kod, kod)
    return liste

HESAPLAR = [
    dict(id="strateji", ad="Strateji", alt_ad="Seviye Kırılımı + Güçlü–Zayıf Sepeti", repo="strateji-sg", dal="kagit-durum",
         zaman="zaman", deger="toplam", alt=["kgt", "kmn"], beklenti=0.40, sharpe=1.99, dd_bek=-0.20, beklenti_metin="yıllık %35–45, düşüş %15–20",
         baslangic="2026-10-09", bitis="2026-12-09", siklik_saat=1,
         enstruman="Hacimce ilk 30 kripto"),
    dict(id="algo", ad="Algo", alt_ad="Trend Avcısı + Panik Dönüşü", repo="algo-sg", dal="kagit-durum",
         zaman="saat", deger="TOPLAM", alt=["A", "B"], beklenti=0.21, sharpe=1.45, dd_bek=-0.15, beklenti_metin="yıllık ~%21, düşüş ~%15",
         baslangic="2026-10-10", bitis="2026-12-09", siklik_saat=2, enstruman="İlk 25 kripto"),
    dict(id="daytrade", ad="Day trade", alt_ad="Akşam Momentumu + Tuzak Kırılım + Trend Günü Molası", repo="day-trade-sg", dal="kagit-durum",
         zaman="zaman", deger="deger", alt=[], beklenti=0.16, sharpe=1.5, dd_bek=-0.05, beklenti_metin="60 günde +%2–4, düşüş ~%5",
         baslangic="2026-10-11", bitis="2026-12-10", siklik_saat=12, enstruman="İlk 25 kripto"),
    dict(id="swing", ad="Swing", alt_ad="Trend Molası + Sıkışma Patlaması + Dipten Sekme", repo="swing-sg", dal="kagit-durum",
         zaman="tarih", deger="deger", alt=[], beklenti=0.25, sharpe=1.45, dd_bek=-0.13, beklenti_metin="60 günde +%3–4, düşüş ~%13",
         baslangic="2026-10-11", bitis="2026-12-09", siklik_saat=12,
         enstruman="25 kripto, Mag7, BIST10, altın, petrol"),
    dict(id="trend", ad="Trend kolları", alt_ad="BTC Pusulası + ABD Güçlüler Sepeti + Sakin Emtialar", repo="swing-sg", dal="kagit-trend-durum",
         zaman="tarih", deger="deger", alt=[], beklenti=0.23, sharpe=1.79, dd_bek=-0.07, beklenti_metin="60 günde +%3–4, düşüş ~%7",
         baslangic="2026-10-12", bitis="2026-12-10", siklik_saat=24,
         enstruman="BTC; 50 ABD hissesinden 12 ay getirisi pozitif olanlar (şu an 32); 18 emtia ETF'inden en sakin %20 (şu an 4)"),
]


def git(repo, *args, kontrol=True):
    r = subprocess.run(["git", "-C", str(KOK / repo), *args], capture_output=True, text=True)
    if kontrol and r.returncode:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def hazirla(repo, dal):
    d = KOK / repo
    if not d.exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/{SAHIP}/{repo}", str(d)], check=True)
    r = subprocess.run(["git", "-C", str(d), "fetch", "-q", "--depth", "50", "origin",
                        f"+refs/heads/{dal}:refs/remotes/origin/{dal}"], capture_output=True, text=True)
    if r.returncode == 0:
        return True
    # fetch geçici olarak başarısızsa (GitHub 5xx) eldeki son referansla devam: hesap sıfırlanmasın
    return subprocess.run(["git", "-C", str(d), "rev-parse", "-q", "--verify", f"origin/{dal}"], capture_output=True).returncode == 0


def oku(repo, dal, dosya):
    r = subprocess.run(["git", "-C", str(KOK / repo), "show", f"origin/{dal}:{dosya}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def csv(repo, dal, dosya):
    t = oku(repo, dal, dosya)
    if not t or not t.strip():
        return pd.DataFrame()
    try:
        return pd.read_csv(io.StringIO(t))
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def f(x, nd=6):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(x):
        return None
    if nd == 6 and 0 < abs(x) < 1:  # PEPE gibi 1e-5 altı fiyatlar: 6 anlamlı basamak
        return float(f"{x:.6g}")
    return round(x, nd)


def zaman(x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or str(x).strip() in ("", "nan"):
        return ""
    t = pd.Timestamp(str(x))
    if t.tzinfo is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    saatli = (t.hour or t.minute) or bool(re.search(r"[ T]\d{1,2}:\d{2}", str(x)))
    return t.strftime("%Y-%m-%d %H:%M") if saatli else t.strftime("%Y-%m-%d")


def gun_son(s):
    """Günlük kapanış değerleri İstanbul gününe göre (UTC+3); tarih-only veride gün değişmez."""
    return s.set_axis(s.index + pd.Timedelta(hours=3)).resample("1D").last().dropna()


def yon(x):
    x = str(x).upper()
    return "AL" if x in ("LONG", "AL", "1", "BUY") else ("SAT" if x in ("SHORT", "SAT", "-1", "SELL") else "")


def md_tablo(md, baslik):
    """ozet.md içinde `baslik` geçen bölümdeki ilk markdown tablosunu sözlük listesi olarak döndürür."""
    if not md or baslik not in md:
        return []
    parca = md.split(baslik, 1)[1]
    satirlar = []
    for s in parca.splitlines()[1:]:
        s = s.strip()
        if s.startswith("#"):
            break
        if s.startswith("|"):
            satirlar.append([h.strip() for h in s.strip("|").split("|")])
        elif satirlar:
            break
    if len(satirlar) < 3:
        return []
    bas = satirlar[0]
    return [dict(zip(bas, r)) for r in satirlar[2:]]


# ---------------------------------------------------------------- hesap bazında okuyucular
def islemler_oku(h):
    r, d = h["repo"], h["dal"]
    t = csv(r, d, "islemler.csv")
    out = []
    if t.empty:
        return out
    for _, x in t.iterrows():
        if h["id"] == "strateji":
            p = str(x.get("portfoy", ""))
            out.append(dict(s=p.split("-")[0] or p, alt=p, v=x.get("sembol"), y=yon(x.get("yon")) if pd.notna(x.get("yon")) else "AL",
                            gt=zaman(x.get("giris_zaman")),
                            gf=f(x.get("giris")), ct=zaman(x.get("cikis_zaman")), cf=f(x.get("cikis")),
                            R=f(x.get("R"), 3), k=f(x.get("pnl"), 2), n=str(x.get("sebep", ""))))
        elif h["id"] == "algo":
            n = x.get("reason")
            out.append(dict(s=str(x.get("module") or x.get("sleeve")), alt=str(x.get("sleeve")), v=x.get("sym"),
                            y=yon(x.get("yon")), gt=zaman(x.get("entry_time")), gf=f(x.get("entry")),
                            ct=zaman(x.get("exit_time")), cf=f(x.get("exit_px")), R=f(x.get("R"), 3),
                            k=f(x.get("pnl_usd"), 2), n="" if isinstance(n, (int, float)) else str(n)))
        elif h["id"] == "daytrade":
            out.append(dict(s=x.get("strateji"), alt="", v=x.get("sembol"), y=yon(x.get("yon")),
                            gt=zaman(x.get("giris_zamani")), gf=f(x.get("giris")), ct=zaman(x.get("cikis_zamani")),
                            cf=f(x.get("cikis")), R=f(x.get("R"), 3), k=f(x.get("kar_usd"), 2),
                            n=str(x.get("neden", ""))))
        elif h["id"] == "swing":
            out.append(dict(s=x.get("strateji"), alt="", v=x.get("varlik"), y="AL", gt=zaman(x.get("giris_tarih")),
                            gf=f(x.get("giris")), ct=zaman(x.get("cikis_tarih")), cf=f(x.get("cikis")),
                            R=f(x.get("R"), 3), k=f(x.get("kar_usd"), 2), n=str(x.get("neden", ""))))
        elif h["id"] == "trend":  # dengeleme kayıtları: kâr/zarar yok, ağırlık değişimi var
            eski, yeni = f(x.get("eski")) or 0, f(x.get("yeni")) or 0
            out.append(dict(s=x.get("kol"), alt="dengeleme", v=x.get("varlik"), y="AL" if yeni > eski else "SAT",
                            gt=zaman(x.get("uygulama")) or str(x.get("uygulama")), gf=f(x.get("fiyat")), ct="", cf=None,
                            R=None, k=None, n=f"ağırlık %{eski * 100:.0f} → %{yeni * 100:.0f}"))
    return out


def pozisyonlar_oku(h):
    r, d = h["repo"], h["dal"]
    out = []
    if h["id"] == "strateji":
        dj = json.loads(oku(r, d, "durum.json") or "{}")
        for alt, kp in (dj.get("kgt") or {}).items():
            for sym, p in (kp.get("poz") or {}).items():
                out.append(dict(s="KGT", alt=f"KGT-{alt}", v=sym, y="AL", gt=zaman(p.get("giris_zaman")),
                                gf=f(p.get("giris")), stop=f(p.get("stop")),
                                tutar=f((p.get("giris") or 0) * (p.get("miktar") or 0), 2), k=None, R=f(p.get("r_toplam"), 3),
                                n="1R kâr alındı" if p.get("tp1_yapildi") else ""))
        for alt, kp in (dj.get("kmn") or {}).items():
            for sym, m in (kp.get("maruz") or {}).items():
                out.append(dict(s="KMN", alt=f"KMN-{alt}", v=sym, y="AL" if m > 0 else "SAT", gt="", gf=None, stop=None,
                                tutar=f(abs(m), 2), k=None, R=None, n="piyasa nötr sepet"))
        return out
    t = csv(r, d, "pozisyonlar.csv")
    if t.empty:
        return out
    for _, x in t.iterrows():
        if h["id"] == "algo":
            out.append(dict(s=str(x.get("module")), alt=str(x.get("sleeve")), v=x.get("sym"), y=yon(x.get("yon")),
                            gt=zaman(x.get("entry_time")), gf=f(x.get("entry")), stop=f(x.get("stop")),
                            tutar=f(x.get("pozisyon_usd"), 2), k=f(x.get("pnl_usd"), 2), R=f(x.get("R"), 3),
                            n="" if f(x.get("remaining")) in (None, 1.0) else f"kalan %{f(x.get('remaining')) * 100:.0f}"))
        elif h["id"] == "daytrade":
            out.append(dict(s=x.get("strateji"), alt="", v=x.get("sembol"), y=yon(x.get("yon")),
                            gt=zaman(x.get("giris_zamani")), gf=f(x.get("giris")), stop=f(x.get("stop")),
                            tutar=f(x.get("tutar_usd"), 2), k=f(x.get("kar_usd"), 2), R=f(x.get("R"), 3),
                            n=str(x.get("neden", ""))))
        elif h["id"] == "swing":
            out.append(dict(s=x.get("strateji"), alt="", v=x.get("varlik"), y="AL", gt=zaman(x.get("giris_tarih")),
                            gf=f(x.get("giris")), stop=f(x.get("stop")), tutar=f(x.get("tutar"), 2),
                            k=f(x.get("kar_usd"), 2), R=f(x.get("R"), 3), n=str(x.get("neden", ""))))
        elif h["id"] == "trend":
            out.append(dict(s=x.get("kol"), alt="", v=x.get("varliklar"), y="AL", gt="", gf=None, stop=None,
                            tutar=None, k=None, R=None, n=f"ağırlık {x.get('toplam_agirlik')} · {x.get('adet')} varlık"))
    return out


def bekleyen_oku(h):
    md = oku(h["repo"], h["dal"], "ozet.md")
    out = []
    for x in md_tablo(md, "Bekleyen"):
        out.append(dict(s=x.get("strateji", ""), v=x.get("varlik") or x.get("sembol", ""),
                        sinyal=x.get("sinyal_tarihi", ""), emir=x.get("emir", ""), stop=x.get("stop", ""),
                        mesafe=x.get("stop_mesafe", "")))
    return out


def egri_oku(h):
    t = csv(h["repo"], h["dal"], "ozsermaye.csv")
    if t.empty or h["zaman"] not in t or h["deger"] not in t:
        return pd.DataFrame()
    idx = pd.to_datetime(t[h["zaman"]], utc=True).dt.tz_localize(None)
    e = pd.DataFrame({"deger": t[h["deger"]].astype(float).values}, index=idx)
    for a in h["alt"]:
        if a in t:
            e[a] = t[a].astype(float).values
    return e[~e.index.duplicated(keep="last")].sort_index()


def ek_metrikler(e, kap, sermaye):
    """Su altı (düşüş süresi), olasılıklı Sharpe (PSR) ve çıkış nedeni dağılımı."""
    from math import erf, sqrt
    out = dict(dd_sure_gun=None, dd_simdi_gun=None, psr=None, psr_gun=0, cikis=None, su_alti=[])
    if len(e):
        g = gun_son(e["deger"])
        g = pd.concat([pd.Series([sermaye], index=[g.index[0] - pd.Timedelta(days=1)]), g])
        s = e["deger"]
        dd_s = s / s.cummax().clip(lower=sermaye) - 1  # kartdaki maks. düşüşle aynı tanım
        dd = dd_s.set_axis(dd_s.index + pd.Timedelta(hours=3)).resample("1D").min().dropna()
        dd = pd.concat([pd.Series([0.0], index=[dd.index[0] - pd.Timedelta(days=1)]), dd])
        out["su_alti"] = [[str(d.date()), round(float(v), 5)] for d, v in dd.items()]
        en, say = 0, 0
        for v in dd_s.set_axis(dd_s.index + pd.Timedelta(hours=3)).resample("1D").last().dropna().values:
            say = say + 1 if v < -1e-9 else 0
            en = max(en, say)
        out["dd_sure_gun"], out["dd_simdi_gun"] = en, say
        r = g.pct_change().dropna()
        out["psr_gun"] = int(len(r))
        if len(r) >= 10 and r.std() > 0:
            sr = r.mean() / r.std()
            g3, g4 = float(r.skew()), float(r.kurt()) + 3
            pay = sqrt(max(1e-9, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
            z = sr * sqrt(len(r) - 1) / pay
            out["psr"] = round(0.5 * (1 + erf(z / sqrt(2))), 3)
    neden = {}
    for t in kap:
        if t.get("k") is None or t.get("kismi"):
            continue
        n = str(t.get("n") or "").lower()
        ad = ("başabaş stop" if ("be_stop" in n or "başabaş" in n) else "iz stop" if ("trail" in n or "iz süren" in n) else
              "stop" if "stop" in n else "hedef" if ("hedef" in n or "tp" in n) else "süre" if ("sure" in n or "süre" in n or "zaman" in n or "time" in n)
              else "iz stop" if "iz" in n else "çıkış sinyali" if ("sinyal" in n or "signal" in n or "trend" in n or "exit" in n) else
              "gün sonu" if ("gun" in n or "gün" in n or "eod" in n) else "bilinmiyor")
        o = neden.setdefault(ad, dict(n=0, k=0.0))
        o["n"] += 1
        o["k"] = round(o["k"] + t["k"], 2)
    out["cikis"] = neden or None
    return out


def metrikler(e, kap, sermaye):
    m = dict(deger=sermaye, getiri=0.0, max_dusus=0.0, kapanan=0, kazanma=None, pf=None, ort_R=None,
             kar_toplam=0.0, son_gun=None, son_hafta=None)
    if len(e):
        s = e["deger"]
        m["deger"] = round(float(s.iloc[-1]), 2)
        m["getiri"] = round(float(s.iloc[-1] / sermaye - 1), 5)
        m["max_dusus"] = round(float((s / s.cummax().clip(lower=sermaye) - 1).min()), 5)
        g = gun_son(s)
        g = pd.concat([pd.Series([sermaye], index=[g.index[0] - pd.Timedelta(days=1)]), g])
        m["son_gun"] = round(float(g.iloc[-1] / g.iloc[-2] - 1), 5) if len(g) > 1 else None
        m["son_hafta"] = round(float(g.iloc[-1] / g.iloc[max(0, len(g) - 8)] - 1), 5) if len(g) > 1 else None
    k = [x["k"] for x in kap if x.get("k") is not None and not x.get("kismi")]
    m["kar_toplam"] = round(sum(x["k"] for x in kap if x.get("k") is not None), 2)
    if k:
        kaz = [x for x in k if x > 0]
        zar = [x for x in k if x < 0]
        m["kapanan"] = len(k)
        m["kazanma"] = round(len(kaz) / len(k), 4)
        m["pf"] = round(sum(kaz) / -sum(zar), 3) if zar else None
        Rs = [x["R"] for x in kap if x.get("R") is not None]
        m["ort_R"] = round(float(np.mean(Rs)), 3) if Rs else None
    return m


def strateji_kirilim(kap, acik):
    out = {}
    for x in kap:
        if x.get("k") is None:
            continue
        o = out.setdefault(str(x["s"]), dict(islem=0, kazanan=0, kar=0.0, R=[], acik=0))
        o["kar"] += x["k"]  # açık işlemin kısmi kârı toplama girer, işlem sayısına girmez
        if x.get("kismi"):
            continue
        o["islem"] += 1
        o["kazanan"] += x["k"] > 0
        if x.get("R") is not None:
            o["R"].append(x["R"])
    for x in acik:
        out.setdefault(str(x["s"]), dict(islem=0, kazanan=0, kar=0.0, R=[], acik=0))["acik"] += 1
    return {s: dict(islem=o["islem"], kazanma=round(o["kazanan"] / o["islem"], 4) if o["islem"] else None,
                    kar=round(o["kar"], 2), ort_R=round(float(np.mean(o["R"])), 3) if o["R"] else None, acik=o["acik"])
            for s, o in out.items()}


def egri_listesi(e, sermaye, baslangic):
    """Grafik için seyreltilmiş eğri: saatlik veri en fazla 4 saatte bir nokta, başlangıç noktası eklenir."""
    if not len(e):
        return [], {}
    s = e.copy()
    if len(s) > 400:
        s = s.resample("4h").last().dropna(how="all")
    bas = pd.Timestamp(baslangic)
    ilk = pd.DataFrame({c: [sermaye if c == "deger" else float(e[c].iloc[0])] for c in e.columns},
                       index=[min(bas, s.index[0] - pd.Timedelta(hours=1))])  # botun ilk satırı ezmesin
    s = pd.concat([ilk, s])
    s = s[~s.index.duplicated(keep="last")]
    t = [x.strftime("%Y-%m-%d %H:%M") for x in s.index]
    return [[a, round(float(b), 2)] for a, b in zip(t, s["deger"])], \
        {c: [round(float(v), 2) for v in s[c]] for c in e.columns if c != "deger"}


def gunluk(e, sermaye, baslangic):
    if not len(e):
        return []
    g = gun_son(e["deger"])
    return [[str(d.date()), round(float(v), 2)] for d, v in g.items()]


Z_DIKKAT, Z_ALARM = -1.65, -2.33  # normal aralık: beklentinin %90'lık bandı
YOGUN_TUTAR = 5000.0  # tek varlıkta toplam sermayenin (50.000 $) %10'u


KONI = None


def koni_yukle():
    global KONI
    if KONI is None:
        try:
            KONI = json.loads((Path(__file__).with_name("koni.json")).read_text())
        except (OSError, ValueError):
            KONI = {}
    return KONI


def bolge_koni(h, m, gun):
    """Monte Carlo konisine göre rota: yeşil (≥ %25'lik dilim), sarı (%5–%25), kırmızı (< %5). Konisi yoksa None."""
    k = koni_yukle().get(h["id"])
    if not k:
        return None
    g = int(min(max(round(gun), 0), len(k["koni"]) - 1))
    _, p5, p25, p50, p75, p95 = k["koni"][g]
    r = m["getiri"]
    ad = "normal" if r >= p25 else ("dikkat" if r >= p5 else "alarm")
    if m["max_dusus"] <= h["dd_bek"]:
        ad = "alarm"
    return dict(ad=ad, alt=p5, ust=p95, p25=p25, p50=p50, p75=p75, kaynak="koni", gun=g,
                yuzdelik="%95 üstü" if r > p95 else "%75–95" if r > p75 else "%25–75" if r >= p25 else "%5–25" if r >= p5 else "%5 altı")


def bolge(h, m, gun):
    """Getiriyi backtest beklentisinin normal aralığıyla karşılaştırır: normal / dikkat / alarm."""
    r, sh = h["beklenti"], h["sharpe"]
    t = max(gun, 3) / 365
    ort = (1 + r) ** (max(gun, 0) / 365) - 1
    sigma = r / sh * t ** 0.5
    z = (m["getiri"] - ort) / sigma if sigma else 0.0
    dd = m["max_dusus"]
    ad = "normal"
    if z < Z_DIKKAT or dd <= 0.75 * h["dd_bek"]:
        ad = "dikkat"
    if z < Z_ALARM or dd <= h["dd_bek"]:
        ad = "alarm"
    return dict(ad=ad, z=round(z, 2), alt=round(ort + Z_DIKKAT * sigma, 4), ust=round(ort - Z_DIKKAT * sigma, 4),
                ort=round(ort, 4), vol=round(r / sh, 4), sharpe=sh, dd_bek=h["dd_bek"])


def sembol(v):
    v = str(v or "").upper()
    for son in ("USDT", "-USD", ".IS"):
        if v.endswith(son):
            v = v[: -len(son)]
    return v.replace("1000", "") if v.startswith("1000") else v


def yeni_mi(z, simdi, saat=24):
    if not z:
        return False
    t = pd.Timestamp(z)
    return t >= simdi - pd.Timedelta(hours=saat)  # yalnız tarih: o günün açılışı (00:00 UTC) sayılır


def olaylar(hepsi, simdi):
    out = []
    for h, kap, acik in hepsi:
        for t in kap:
            if t.get("k") is not None and yeni_mi(t.get("ct"), simdi):
                out.append(dict(h=h["id"], ad=h["ad"], tip="kapandı", s=t["s"], v=t["v"], k=t["k"],
                                R=t.get("R"), z=t["ct"]))
        for t in kap + acik:
            if t.get("gt") and yeni_mi(t.get("gt"), simdi) and t.get("alt") != "dengeleme":
                out.append(dict(h=h["id"], ad=h["ad"], tip="açıldı", s=t["s"], v=t["v"], y=t.get("y"),
                                z=t["gt"]))
            elif t.get("alt") == "dengeleme" and yeni_mi(t.get("gt"), simdi):
                out.append(dict(h=h["id"], ad=h["ad"], tip="dengeleme", s=t["s"], v=t["v"], y=t.get("y"), z=t["gt"]))
    tek, gor = [], set()
    for x in out:  # Seviye Kırılımı'nın alt hesapları aynı varlığı birkaç kez açar: tek olay say
        a = (x["h"], x["tip"], x["s"], x["v"], x.get("y")) if x["tip"] != "kapandı" else id(x)
        if a not in gor:
            gor.add(a)
            tek.append(x)
    out = sorted(tek, key=lambda x: x["z"], reverse=True)
    kap = [x for x in out if x["tip"] == "kapandı"]
    acl = [x for x in out if x["tip"] == "açıldı"]
    cumle = []
    if not out:
        cumle.append("Son 24 saatte yeni işlem açılmadı veya kapanmadı.")
    else:
        if acl:
            cumle.append(f"Son 24 saatte {len(acl)} pozisyon açıldı")
        if kap:
            top = sum(x["k"] for x in kap)
            cumle.append(f"{len(kap)} işlem kapandı (toplam {'+' if top >= 0 else '−'}{abs(top):,.0f} $)".replace(",", "."))
        den = sum(1 for x in out if x["tip"] == "dengeleme")
        if not cumle and den:
            cumle.append(f"Son 24 saatte yeni işlem yok; trend kollarında {den} ağırlık değişikliği oldu")
        cumle = [", ".join(cumle) + "."]
        if kap:
            en_iyi, en_kotu = max(kap, key=lambda x: x["k"]), min(kap, key=lambda x: x["k"])
            if en_iyi["k"] > 0:
                cumle.append(f"En iyisi {en_iyi['ad']} {sembol(en_iyi['v'])} (+{en_iyi['k']:,.0f} $).".replace(",", "."))
            if en_kotu["k"] < 0:
                cumle.append(f"En kötüsü {en_kotu['ad']} {sembol(en_kotu['v'])} (−{abs(en_kotu['k']):,.0f} $).".replace(",", "."))
    return dict(cumle=" ".join(cumle), liste=out[:40])


def maruziyet(hepsi, beks):
    toplam = {}
    for h, _, acik in hepsi:
        for p in acik:
            if h["id"] == "trend":  # kol satırları varlık listesi; tutar yok
                for v in str(p.get("v") or "").split(","):
                    v = sembol(v.strip())
                    if v and v != "NAKIT":
                        toplam.setdefault(v, dict(v=v, hesaplar=set(), tutar=0.0, net=0.0, bekleyen=set()))["hesaplar"].add(h["ad"])
                continue
            v = sembol(p.get("v"))
            o = toplam.setdefault(v, dict(v=v, hesaplar=set(), tutar=0.0, net=0.0, bekleyen=set()))
            o["hesaplar"].add(h["ad"])
            t = p.get("tutar") or 0.0
            o["tutar"] += t
            o["net"] += t if p.get("y") != "SAT" else -t
    for h, bek in beks:
        for b in bek:
            v = sembol(b.get("v"))
            toplam.setdefault(v, dict(v=v, hesaplar=set(), tutar=0.0, net=0.0, bekleyen=set()))["bekleyen"].add(h["ad"])
    out = []
    for o in toplam.values():
        n = len(o["hesaplar"] | o["bekleyen"])
        uyari = n >= 3 or o["tutar"] >= YOGUN_TUTAR
        out.append(dict(v=o["v"], hesaplar=sorted(o["hesaplar"]), bekleyen=sorted(o["bekleyen"] - o["hesaplar"]),
                        tutar=round(o["tutar"], 2), net=round(o["net"], 2), hesap_sayisi=n, uyari=uyari))
    out.sort(key=lambda x: (-x["hesap_sayisi"], -x["tutar"]))
    return out[:60]


# Backtest (örneklem-dışı) beklentileri: kazanma oranı ve ortalama R. Ders motoru canlı sonucu bunlarla karşılaştırır.
STRATEJI_BEKLENTI = {
    "Trend Molası": (0.50, 0.25), "Sıkışma Patlaması": (0.47, 0.41), "Dipten Sekme": (0.70, 0.19),
    "Seviye Kırılımı": (0.455, None), "Trend Avcısı (4 saatlik)": (0.485, 0.25), "Trend Avcısı (günlük)": (0.485, 0.25),
    "Panik Dönüşü": (0.70, None), "Akşam Momentumu": (0.49, None), "Tuzak Kırılım": (0.49, None),
    "Trend Günü Molası": (0.49, None),
}
MIN_ISLEM = 8  # bundan az işlemle ders çıkarılmaz


def _binom_cdf(k, n, p):
    from math import comb
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def dersler(hepsi):
    """Canlı (kağıt) işlemlerden otomatik bulgular: beklentiden sapma, kayıp serisi, saat kümelenmesi, çıkış nedenleri."""
    out, bekleyen = [], []
    for h, kap, _ in hepsi:
        gruplar = {}
        for t in kap:
            if t.get("k") is not None and not t.get("kismi"):
                gruplar.setdefault(t["s"], []).append(t)
        for st, ts in gruplar.items():
            n = len(ts)
            kaz = sum(1 for t in ts if t["k"] > 0)
            bek = STRATEJI_BEKLENTI.get(st)
            if not bek:
                continue
            if n < MIN_ISLEM:
                bekleyen.append(f"{st} ({n}/{MIN_ISLEM})")
                continue
            p0, r0 = bek
            alt = _binom_cdf(kaz, n, p0)
            ust = 1 - _binom_cdf(kaz - 1, n, p0) if kaz else 1.0
            ko = kaz / n
            if alt < 0.05:
                out.append(dict(seviye="dikkat", h=h["id"], baslik=f"{st}: kazanma oranı beklentinin belirgin altında",
                                metin=f"{n} işlemde kazanma %{ko*100:.0f}; backtest %{p0*100:.0f}. Bu fark şansla açıklanamayacak kadar büyük "
                                      f"(olasılık %{alt*100:.1f}). Piyasa koşulu değişmiş olabilir; Aralık'ta bu stratejinin yeri sorgulanmalı."))
            elif ust < 0.05:
                out.append(dict(seviye="iyi", h=h["id"], baslik=f"{st}: beklentinin belirgin üstünde",
                                metin=f"{n} işlemde kazanma %{ko*100:.0f}; backtest %{p0*100:.0f}. İyi giden piyasa koşulunun etkisi olabilir, kalıcı sayılmamalı."))
            Rs = [t["R"] for t in ts if t.get("R") is not None]
            if r0 is not None and len(Rs) >= MIN_ISLEM:
                ort = float(np.mean(Rs))
                se = float(np.std(Rs, ddof=1)) / len(Rs) ** 0.5 if len(Rs) > 1 else 0
                if se and (ort - r0) / se < -2:
                    out.append(dict(seviye="dikkat", h=h["id"], baslik=f"{st}: işlem başına kazanç düşük",
                                    metin=f"Ortalama {ort:+.2f}R, backtest {r0:+.2f}R (fark istatistiksel olarak anlamlı)."))
            # kayıp serisi: beklenen olasılığa göre şaşırtıcı mı?
            sira = sorted(ts, key=lambda t: t.get("ct") or "")
            seri = en = 0
            for t in sira:
                seri = seri + 1 if t["k"] < 0 else 0
                en = max(en, seri)
            q = 1 - p0
            if en >= 4 and (q ** en) * n < 0.05:
                out.append(dict(seviye="dikkat", h=h["id"], baslik=f"{st}: art arda {en} kayıp",
                                metin=f"Backtest kazanma oranıyla bu uzunlukta bir seri {n} işlemde nadir görülür. Tek başına alarm değil, izlenmeli."))
            # çıkış nedenleri
            stop = sum(1 for t in ts if str(t.get("n", "")).startswith("stop"))
            if n >= MIN_ISLEM and stop / n > 0.6:
                out.append(dict(seviye="bilgi", h=h["id"], baslik=f"{st}: işlemlerin çoğu stopla kapanıyor",
                                metin=f"{n} işlemden {stop} tanesi (%{stop/n*100:.0f}) stopla kapandı. Stop mesafesi ve giriş zamanlaması incelenecek."))
        # saat kümelenmesi (saatli işlemler)
        saatli = [t for t in kap if t.get("k") is not None and " " in (t.get("gt") or "")]
        if len(saatli) >= 20:
            kume = {}
            for t in saatli:
                saat = (pd.Timestamp(t["gt"]) + pd.Timedelta(hours=3)).hour // 4 * 4
                kume.setdefault(saat, []).append(t)
            genel = sum(t["k"] > 0 for t in saatli) / len(saatli)
            for saat, ts in kume.items():
                if len(ts) >= 6:
                    ko = sum(t["k"] > 0 for t in ts) / len(ts)
                    if _binom_cdf(int(ko * len(ts)), len(ts), genel) < 0.05:
                        out.append(dict(seviye="bilgi", h=h["id"], baslik=f"{h['ad']}: {saat:02d}:00–{saat+4:02d}:00 arası zayıf",
                                        metin=f"Bu saatlerde açılan {len(ts)} işlemde kazanma %{ko*100:.0f}, hesabın genelinde %{genel*100:.0f}. "
                                              "Yeterli veri birikirse saat filtresi Aralık'ta değerlendirilir."))
    return dict(liste=out, veri_bekleyen=bekleyen, min_islem=MIN_ISLEM)


def usdtry():
    """TL karşılığı için son USD/TRY kuru (swing-sg veri dosyasından; tarihiyle birlikte gösterilir)."""
    try:
        u = pd.read_csv(KOK / "swing-sg" / "data" / "yardimci" / "USDTRY.csv", index_col=0, parse_dates=True)["Close"].dropna()
        u = u[u > 0]
        return dict(kur=round(float(u.iloc[-1]), 4), tarih=str(u.index[-1].date()))
    except Exception:
        return None


def korelasyon(gunlukler):
    seri = {k: pd.Series({pd.Timestamp(d): v for d, v in g}).pct_change().dropna() for k, g in gunlukler.items() if len(g) > 1}
    if len(seri) < 2:
        return None
    T = pd.DataFrame(seri).dropna()
    if len(T) < 10:
        return dict(gun=len(T), hazir=False)
    C = T.corr().round(2)
    return dict(gun=len(T), hazir=True, hesaplar=list(C.columns), matris=C.values.tolist())


def alarmlar(docs, isl, maruz, simdi):
    out = []
    for d in docs:
        if d["saglik"] == "gecikmede" and d.get("son_calisma"):
            sa = (simdi - pd.Timestamp(d["son_calisma"])).total_seconds() / 3600
            out.append(dict(id=f"bot-{d['id']}", seviye="alarm" if sa > 24 else "dikkat",
                            metin=f"{d['ad']} botu {sa:.0f} saattir kayıt yazmadı (beklenen sıklığın 2,5 katını aştı)."))
        elif d["saglik"] == "veri yok":
            out.append(dict(id=f"bot-{d['id']}", seviye="alarm", metin=f"{d['ad']} botunun kayıtlarına ulaşılamadı."))
        b = d.get("bolge") or {}
        # koni rotasında sarı (%5–25 dilimi) sağlıklı bir hesapta da sık görülür: yalnız kartta gösterilir, uyarı değildir
        if b.get("ad") == "alarm" or (b.get("ad") == "dikkat" and b.get("kaynak") != "koni"):
            out.append(dict(id=f"bant-{d['id']}-{b['ad']}", seviye=b["ad"],
                            metin=f"{d['ad']} beklenen aralığın {'altına indi' if b['ad'] == 'alarm' else 'alt sınırına yaklaştı'}: "
                                  f"getiri %{d['getiri'] * 100:+.1f}, maks. düşüş %{d['max_dusus'] * 100:.1f}."))
    for hid, x in isl.items():
        for t in x["kapanan"]:
            if t.get("R") is not None and t["R"] <= -2 and yeni_mi(t.get("ct"), simdi):
                out.append(dict(id=f"kayip-{hid}-{t['v']}-{t['ct']}", seviye="dikkat",
                                metin=f"{hid}: {sembol(t['v'])} işlemi {t['R']:.1f}R ile kapandı (planlanan riskin {abs(t['R']):.1f} katı)."))
    for m in maruz:
        if m["uyari"]:
            out.append(dict(id=f"yogun-{m['v']}", seviye="dikkat",
                            metin=f"{m['v']}: {m['hesap_sayisi']} hesapta pozisyon veya emir var"
                                  + (", toplam " + f"{m['tutar']:,.0f}".replace(",", ".") + " $" if m["tutar"] else "") + "."))
    return out


KIYAS_AD = {"BTC": "Bitcoin", "SPX": "S&P 500", "NDX": "Nasdaq 100", "XU100": "BIST 100"}


def kiyas(baslangic="2026-10-09"):
    """Karşılaştırma endekslerinin test başından bugüne yüzde getirisi (swing-sg kiyas-durum dalı, GitHub Actions yazar)."""
    try:
        if not hazirla("swing-sg", "kiyas-durum"):
            return None
        t = oku("swing-sg", "kiyas-durum", "kiyas.csv")
        if not t:
            return None
        T = pd.read_csv(io.StringIO(t), index_col=0, parse_dates=True).sort_index()
        out = {}
        for c in T.columns:
            s = T[c].dropna()
            once = s[s.index <= pd.Timestamp(baslangic)]
            if once.empty:
                continue
            taban = float(once.iloc[-1])
            s = s[s.index >= once.index[-1]]
            out[c] = dict(ad=KIYAS_AD.get(c, c), seri=[[str(d.date()), round(float(v) / taban - 1, 5)] for d, v in s.items()])
        return out or None
    except Exception as e:
        print("kıyas okunamadı:", e)
        return None


def poz_gunsonu(hepsi, simdi, eski):
    """Açık pozisyonların kâr/zararının İstanbul günü bazında anlık görüntüsü.
    Her çalışmada bugünün kaydı üzerine yazılır (son çalışma ≈ gün sonu); önceki günler önceki meta'dan taşınır.
    Panel iki günün farkından pozisyon başına günlük değişimi gösterir."""
    gun = (simdi + pd.Timedelta(hours=3)).strftime("%Y-%m-%d")
    bugun = {}
    for h, _, acik in hepsi:
        for p in acik:
            if p.get("k") is None:
                continue
            a = "|".join(str(p.get(x) or "") for x in ("s", "alt", "v", "y"))
            bugun[f"{h['id']}|{a}"] = round(bugun.get(f"{h['id']}|{a}", 0.0) + float(p["k"]), 2)
    out = {k: v for k, v in (eski or {}).items() if isinstance(v, dict)}
    out[gun] = bugun
    return {k: out[k] for k in sorted(out)[-75:]}


def calistir(cikis, onceki_dosya=None):
    cikis = Path(cikis)
    cikis.mkdir(parents=True, exist_ok=True)
    simdi = pd.Timestamp.now(tz="UTC").tz_localize(None)
    toplam, hepsi, beks, docs, isls = [], [], [], [], {}
    for h in HESAPLAR:
        var = hazirla(h["repo"], h["dal"])
        sermaye = 10000.0
        e = egri_oku(h) if var else pd.DataFrame()
        kap = adlandir(kismi_birlestir(islemler_oku(h))) if var else []
        acik = adlandir(pozisyonlar_oku(h)) if var else []
        bek = adlandir(bekleyen_oku(h)) if var else []
        son_commit = git(h["repo"], "log", "-1", "--format=%cI", f"origin/{h['dal']}", kontrol=False).strip() if var else ""
        if son_commit:
            sc = pd.Timestamp(son_commit).tz_convert("UTC").tz_localize(None)
            gecikme = (simdi - sc).total_seconds() / 3600
            esik = max(6.0, h["siklik_saat"] * 2.5)  # GitHub zamanlayıcısı saatlerce gecikebiliyor
            saglik = "gecikmede" if gecikme > esik else "çalışıyor"
            son_calisma = sc.strftime("%Y-%m-%d %H:%M")
        else:
            saglik, son_calisma = ("başlamadı" if simdi < pd.Timestamp(h["baslangic"]) + pd.Timedelta(days=1) else "veri yok"), ""
        kap_sirali = sorted(kap, key=lambda x: (x.get("ct") or x.get("gt") or ""), reverse=True)
        egri, alt = egri_listesi(e, sermaye, h["baslangic"])
        doc = dict(id=h["id"], ad=h["ad"], alt_ad=h["alt_ad"], enstruman=h["enstruman"], sermaye=sermaye,
                   baslangic=h["baslangic"], bitis=h["bitis"], beklenti_yillik=h["beklenti"],
                   beklenti_metin=h["beklenti_metin"], saglik=saglik, son_calisma=son_calisma,
                   son_veri=egri[-1][0] if egri else "", acik=len({(p.get("s"), p.get("v"), p.get("y")) for p in acik}), bekleyen=len(bek),
                   **metrikler(e, kap, sermaye), egri=egri, alt=alt, gunluk=gunluk(e, sermaye, h["baslangic"]),
                   strateji=strateji_kirilim(kap, acik), sira=HESAPLAR.index(h))
        gun = (simdi - pd.Timestamp(h["baslangic"])).total_seconds() / 86400
        doc["bolge"] = (bolge_koni(h, doc, gun) or bolge(h, doc, gun)) if egri else None
        kn = koni_yukle().get(h["id"])
        doc["koni"] = kn["koni"] if kn else None
        doc["ruin"] = kn["ruin"] if kn else None
        doc["koni_kaynak"] = f"{kn['baslangic']} → {kn['bitis']} backtest, yıllık %{kn['yillik']*100:.0f}" if kn else None
        doc.update(ek_metrikler(e, kap, sermaye))
        doc["gecikme_saat"] = round((simdi - pd.Timestamp(son_calisma)).total_seconds() / 3600, 1) if son_calisma else None
        hepsi.append((h, kap, acik))
        beks.append((h, bek))
        docs.append(doc)
        isl = dict(id=h["id"], toplam_kapanan=len(kap), kapanan=kap_sirali[:MAKS_ISLEM], acik=acik, bekleyen=bek)
        (cikis / f"hesaplar__{h['id']}.json").write_text(json.dumps(doc, ensure_ascii=False, default=str))
        (cikis / f"islemler__{h['id']}.json").write_text(json.dumps(isl, ensure_ascii=False, default=str))
        isls[h["id"]] = isl
        if len(e):
            toplam.append(gun_son(e["deger"]).rename(h["id"]))
        print(f"{h['id']:9s} {saglik:10s} değer={doc['deger']:>9,.2f} getiri={doc['getiri']:+.2%} "
              f"kapanan={len(kap)} açık={len(acik)} bekleyen={len(bek)} eğri={len(egri)}")
    birlesik = []
    if toplam:
        T = pd.concat(toplam, axis=1).sort_index().ffill().fillna(10000.0)
        eksik = len(HESAPLAR) - T.shape[1]  # verisi olmayan hesaplar başlangıç sermayesinde sayılır
        s = (T.sum(axis=1) + eksik * 10000.0) / (len(HESAPLAR) * 10000.0) * 100
        birlesik = [[str(d.date()), round(float(v), 3)] for d, v in s.items()]
    onceki_meta = {}
    if onceki_dosya and Path(onceki_dosya).exists():
        try:
            d = json.loads(Path(onceki_dosya).read_text())
            onceki_meta = d.get("data", d) if isinstance(d, dict) else {}
        except ValueError:
            pass
    maruz = maruziyet(hepsi, beks)
    al = alarmlar(docs, isls, maruz, simdi)
    meta = dict(guncelleme=simdi.strftime("%Y-%m-%d %H:%M"), hesap_sayisi=len(HESAPLAR), birlesik_endeks=birlesik,
                bugun=olaylar(hepsi, simdi), maruziyet=maruz, alarmlar=al, dersler=dersler(hepsi), usdtry=usdtry(),
                korelasyon=korelasyon({d["id"]: d["gunluk"] for d in docs}))
    meta["kiyas"] = kiyas()
    meta["poz_gunsonu"] = poz_gunsonu(hepsi, simdi, onceki_meta.get("poz_gunsonu"))
    (cikis / "meta__ozet.json").write_text(json.dumps(meta, ensure_ascii=False))
    print("meta", meta["guncelleme"], "|", meta["bugun"]["cumle"])
    onceki = {a["id"] for a in (onceki_meta.get("alarmlar") or []) if isinstance(a, dict) and "id" in a}
    for a in al:
        print(("YENI_ALARM" if a["id"] not in onceki else "suren_alarm") + f" [{a['seviye']}] {a['metin']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikis", required=True)
    ap.add_argument("--onceki", help="paneldeki önceki meta/ozet belgesi (yeni alarmları ayırmak için)")
    a = ap.parse_args()
    calistir(a.cikis, a.onceki)
