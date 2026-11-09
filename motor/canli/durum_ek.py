"""Pano için motorun YAZDIĞI türetilmiş alanlar (DURUM_SOZLESMESI.md "Genişletme (motor yazıcı paketi)").

İlke: pano hesap yapmaz; istatistik, çıkış nedenleri, dönemsel getiri, stil/enstrüman kırılımları ve bekleyen emirler burada
(motor tarafında) hesaplanır. Paper (`paper_durum.py`) ve backtest (`backtest_durum.py`) AYNI fonksiyonları çağırır.

Gün kesimi (kullanıcı kararı 2026-11-08): günlük K/Z, dönemsel (hafta/ay) gruplama TSİ'ye (Europe/Istanbul, 00:00) göredir.
Zaman damgaları dosyada UTC kalır. Backtest kaynağında günlük seri araştırma çıktısının (kilit set.csv) UTC ızgarasıdır;
gün içi özsermaye olmadığı için TSİ'ye çevrilemez ve `gun_kesimi` alanı bunu açıkça söyler.

Eşikler: aşağıdaki MIN_* sabitleri yalnız "istatistik yeterli örnekle hesaplandı mı" sınırıdır (envanter F11); kabul/geçme ölçütü
değildir (geçme ölçütleri sonuclar/evren/ON_KAYIT.md'dedir, bu dosyada eşik/alarm yok).
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from motor.canli import durum as d

TSI = ZoneInfo("Europe/Istanbul")
GUN_KESIMI_TSI = "Europe/Istanbul"
GUN_KESIMI_UTC_IZGARA = "UTC (araştırma ızgarası)"
MIN_ISLEM = 30                      # SQN / Kelly için en az kapanan işlem
MIN_GUN = 30                        # Sharpe / Sortino için en az günlük gözlem
YILLIK = 365                        # secim.sharpe_gunluk ile aynı (7/24 piyasa)
KELLY_CARPAN = 0.25                 # çeyrek Kelly (yalnız bilgi; pozisyon büyütme önerisi değildir)
DONEM_SON = 12                      # haftalık/aylık listede son N dönem
SERI_GUN = 60


# ---------------------------------------------------------------------------- TSİ gün yardımcıları
def _utc(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def tsi_gun(t) -> str:
    """UTC an -> o anın TSİ takvim günü ('YYYY-MM-DD')."""
    return str(_utc(t).tz_convert(TSI).date())


def kapanis_gunu(kapanis) -> str:
    """Bir mumun KAPANIŞ anındaki özsermayenin ait olduğu TSİ günü: tam gece yarısı (00:00 TSİ) kapanışı önceki güne yazılır."""
    return tsi_gun(_utc(kapanis) - pd.Timedelta(nanoseconds=1))


# ---------------------------------------------------------------------------- dönemsel (hafta/ay) gruplama
def hafta_anahtari(gun: str) -> str:
    y, w, _ = date.fromisoformat(gun).isocalendar()
    return f"{y}-W{w:02d}"


def ay_anahtari(gun: str) -> str:
    return gun[:7]


def gunluk_kz_ajan(strateji_kumulatif: dict, ajan_of: dict, gunler: list, bas: Decimal, ozs_gun: dict) -> dict:
    """Stil (ajan) başına günlük K/Z ve dönemsel (hafta/ay) toplamlar.

    strateji_kumulatif: {kimlik: {gun: gün sonu kümülatif net K/Z (Decimal)}}; gunler: sıralı gün metinleri (mevcut kesimde);
    ajan_of: {kimlik: ajan}; ozs_gun: {gun: gün sonu özsermaye (Decimal)} (set toplamı için); bas: başlangıç özsermaye.
    getiri (ajan) = pnl / başlangıç özsermaye (set başlangıcına oran, toplamsal); toplam.getiri = özsermaye getirisi.
    -> {'gunluk': [...son 60], 'haftalik': [...], 'aylik': [...]}; dönem kayıtları son 12; bitmemiş dönem `tamamlandi=false`.
    """
    ajanlar = sorted({a for a in ajan_of.values()})
    onceki = {k: Decimal(0) for k in strateji_kumulatif}
    gun_ajan = {}
    for g in gunler:
        satir = defaultdict(lambda: Decimal(0))
        for k, seri in strateji_kumulatif.items():
            if g in seri:
                satir[ajan_of[k]] += seri[g] - onceki[k]
                onceki[k] = seri[g]
        gun_ajan[g] = {a: satir.get(a, Decimal(0)) for a in ajanlar}
    onc_e, ozs_onceki = bas, {}
    for g in gunler:
        ozs_onceki[g] = onc_e
        if g in ozs_gun:
            onc_e = ozs_gun[g]

    def kayit(pnls: dict, toplam_pnl: Decimal, e_bas: Decimal) -> dict:
        return {"ajanlar": {a: {"pnl": d.para(p), "getiri": d.sayi(p / bas)} for a, p in pnls.items()},
                "toplam": {"pnl": d.para(toplam_pnl), "getiri": d.sayi(toplam_pnl / e_bas) if e_bas > 0 else None}}
    gunluk = []
    for g in gunler:
        pnl_set = ozs_gun[g] - ozs_onceki[g] if g in ozs_gun else Decimal(0)
        gunluk.append({"gun": g, **kayit(gun_ajan[g], pnl_set, ozs_onceki[g])})
    out = {"gunluk": gunluk[-SERI_GUN:]}
    for ad, anahtar in (("haftalik", hafta_anahtari), ("aylik", ay_anahtari)):
        gruplar: dict = {}
        for g in gunler:
            gruplar.setdefault(anahtar(g), []).append(g)
        liste = []
        for donem, gs in gruplar.items():
            pn = {a: sum((gun_ajan[g][a] for g in gs), Decimal(0)) for a in ajanlar}
            e_bas = ozs_onceki[gs[0]]
            # set K/Z: gün K/Z'lerinin toplamı (= dönem sonu özsermaye - dönem başı özsermaye)
            pnl_set = sum((ozs_gun[g] - ozs_onceki[g] for g in gs if g in ozs_gun), Decimal(0))
            liste.append({"donem": donem, "bas_gun": gs[0], "bit_gun": gs[-1], "gun_sayisi": len(gs),
                          "tamamlandi": _donem_bitti(ad, donem, gunler[-1]), **kayit(pn, pnl_set, e_bas)})
        out[ad] = liste[-DONEM_SON:]
    return out


def _donem_bitti(ad: str, donem: str, son_gun: str) -> bool:
    """Dönemin son takvim günü verideki son günden önceyse dönem tamamdır."""
    if ad == "aylik":
        y, m = int(donem[:4]), int(donem[5:7])
        sonraki = date(y + (m == 12), m % 12 + 1, 1)
        return date.fromisoformat(son_gun) >= sonraki
    y, w = int(donem[:4]), int(donem[6:])
    pazar = date.fromisocalendar(y, w, 7)
    return date.fromisoformat(son_gun) > pazar


# ---------------------------------------------------------------------------- istatistik{}
def _ort(x: list) -> Optional[float]:
    return sum(x) / len(x) if x else None


def _std(x: list) -> Optional[float]:
    if len(x) < 2:
        return None
    m = sum(x) / len(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def _seri_uzunlugu(isaretler: list, hedef: int) -> int:
    en, simdi = 0, 0
    for s in isaretler:
        simdi = simdi + 1 if s == hedef else 0
        en = max(en, simdi)
    return en


def istatistik(satirlar: list, gunluk: list) -> dict:
    """islemler.jsonl satırları + TAM günlük seri ({gun, pnl (para metni), getiri}) -> ozet.istatistik{}.

    SQN, çeyrek Kelly: R çarpanlarından, n < MIN_ISLEM ise null + neden. Sharpe/Sortino: günlük getiriden (yıllık, √365),
    gün < MIN_GUN ise null + neden. Para tutarı (beklenti_islem_basi) yalnız `set_katki_usd` olan satırlardan.
    """
    nedenler = []
    n = len(satirlar)
    r = [float(s["r"]) for s in satirlar if s.get("r") is not None]
    kazanc = [x for x in r if x > 0]
    kayip = [x for x in r if x < 0]
    kk = (_ort(kazanc) / -_ort(kayip)) if (kazanc and kayip) else None
    sqn = kelly = None
    if n < MIN_ISLEM:
        nedenler.append(f"SQN ve Kelly ölçülmedi: kapanan işlem {n} < {MIN_ISLEM}")
    else:
        sd = _std(r) if len(r) > 1 else None
        if len(r) < n:
            nedenler.append(f"SQN ölçülmedi: {n - len(r)}/{n} işlemde R yok (R'siz satır varken SQN tüm işlemleri temsil etmez)")
        elif not sd or sd <= 0:
            nedenler.append("SQN ölçülemedi: R çarpanlarının standart sapması sıfır")
        else:
            sqn = d.sayi(math.sqrt(n) * _ort(r) / sd)
        w = len(kazanc) / len(r) if r else 0.0
        if kk is not None and kk > 0:
            kelly = d.sayi(KELLY_CARPAN * max(0.0, w - (1 - w) / kk))
        else:
            nedenler.append("Kelly ölçülemedi: kazanç ya da kayıp işlemi yok")
    para_satir = [Decimal(s["set_katki_usd"]) for s in satirlar if s.get("set_katki_usd") is not None]
    if satirlar and len(para_satir) < n:
        nedenler.append(f"Para tutarları (işlem başı beklenti) {len(para_satir)}/{n} işlem için ölçüldü "
                        f"(kalanında set katkısı yok); oran ve R tabanlı alanlar tüm işlemlerden")
    g_ret = [float(x["getiri"]) for x in gunluk if x.get("getiri") is not None]
    sharpe = sortino = None
    if len(g_ret) < MIN_GUN:
        nedenler.append(f"Sharpe ve Sortino ölçülmedi: gün sayısı {len(g_ret)} < {MIN_GUN}")
    else:
        sd, mu = _std(g_ret), _ort(g_ret)
        sharpe = d.sayi(mu / sd * math.sqrt(YILLIK)) if sd and sd > 0 else None
        asagi = math.sqrt(sum(min(v, 0.0) ** 2 for v in g_ret) / len(g_ret))
        sortino = d.sayi(mu / asagi * math.sqrt(YILLIK)) if asagi > 0 else None
        if sortino is None:
            nedenler.append("Sortino ölçülemedi: hiç zarar günü yok")
    sirali = sorted(satirlar, key=lambda s: s["zaman"])
    isaret = [(1 if Decimal(s["net_pnl_yerel"]) > 0 else (-1 if Decimal(s["net_pnl_yerel"]) < 0 else 0)) for s in sirali]
    tutma = [(d.zaman_oku(s["cikis_zamani"]) - d.zaman_oku(s["giris_zamani"])).total_seconds() / 3600 for s in satirlar]
    gunler_pnl = [(x["gun"], Decimal(x["pnl"])) for x in gunluk if x.get("pnl") is not None]
    iyi = max(gunler_pnl, key=lambda x: x[1]) if gunler_pnl else None
    kotu = min(gunler_pnl, key=lambda x: x[1]) if gunler_pnl else None
    return {
        "islem_sayisi": n, "gun_sayisi": len(g_ret),
        "beklenti_islem_basi": d.para(sum(para_satir, Decimal(0)) / len(para_satir)) if para_satir else None,
        "kazanc_kayip_orani": d.sayi(kk), "sqn": sqn, "sharpe": sharpe, "sortino": sortino, "kelly_ceyrek": kelly,
        "yesil_gun_orani": d.sayi(sum(1 for _, p in gunler_pnl if p > 0) / len(gunler_pnl)) if gunler_pnl else None,
        "en_uzun_kazanc_serisi": _seri_uzunlugu(isaret, 1) if n else None,
        "en_uzun_kayip_serisi": _seri_uzunlugu(isaret, -1) if n else None,
        "ort_tutma_saat": d.sayi(_ort(tutma)),
        "en_iyi_gun": {"gun": iyi[0], "pnl": d.para(iyi[1])} if iyi else None,
        "en_kotu_gun": {"gun": kotu[0], "pnl": d.para(kotu[1])} if kotu else None,
        "istatistik_neden": "; ".join(nedenler) if nedenler else None,
    }


# ---------------------------------------------------------------------------- cikis_nedenleri[]
def cikis_nedenleri(satirlar: list) -> tuple:
    """-> (liste [{neden, islem, pay, net_pnl}], not|None). net_pnl = set katkısı toplamı; grubun herhangi bir satırında set_katki_usd
    yoksa o grupta net_pnl null (karışık hesap birimleri toplanmaz)."""
    n = len(satirlar)
    gr = defaultdict(list)
    for s in satirlar:
        gr[s["cikis_nedeni"] or "bilinmiyor"].append(s)
    liste, eksik = [], False
    for neden, ls in sorted(gr.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        tam = all(s.get("set_katki_usd") is not None for s in ls)
        eksik |= not tam
        liste.append({"neden": neden, "islem": len(ls), "pay": d.sayi(len(ls) / n),
                      "net_pnl": d.para(sum((Decimal(s["set_katki_usd"]) for s in ls), Decimal(0))) if tam else None})
    return liste, ("net_pnl null olan nedenlerde işlemlerin bir kısmının set katkısı ölçülmedi (portföy kolu)" if eksik else None)


def r_kiyas(s: dict):
    """Backtest beklentisiyle KIYAS R'si (Dersler, Karne, Koç): TradFi funding HARİÇ (kullanıcı kararı 2026-11-09; paper satırında `r_kiyas`).
    Alanı olmayan satır TradFi funding ayrımı gerektirmeyen kaynaktandır (backtest durumu: araştırmada TradFi funding yok) -> r."""
    return s["r_kiyas"] if "r_kiyas" in s else s.get("r")


# ---------------------------------------------------------------------------- ajanlar[] / enstrumanlar[] / strateji_enstruman[]
def _kazandi(s: dict, olcut: str) -> bool:
    if olcut == "r":
        return s.get("r") is not None and s["r"] > 0
    return Decimal(s["net_pnl_yerel"]) > 0


def _pf(satirlar: list) -> Optional[float]:
    """Profit factor = kârların toplamı / zararların toplamı (set katkısı üzerinden); katkısı ölçülmeyen satır varsa null."""
    if not satirlar or any(s.get("set_katki_usd") is None for s in satirlar):
        return None
    v = [Decimal(s["set_katki_usd"]) for s in satirlar]
    kar, zr = sum((x for x in v if x > 0), Decimal(0)), sum((x for x in v if x < 0), Decimal(0))
    return d.sayi(kar / -zr) if zr < 0 else None


def kirilimlar(stratejiler: list, satirlar: list, hucre_katki: dict, bas: Decimal, acik_pozisyonlar: Optional[list] = None,
               kazanma_olcutu: str = "net") -> dict:
    """stratejiler: stratejiler.json satırları (kimlik, ajan, ozsermaye_katkisi). satirlar: islemler.jsonl satırları.
    hucre_katki: {(kimlik, sembol): Decimal|None} (None = bu hücrenin katkısı ölçülmedi). acik_pozisyonlar: maruziyet pozisyon nesneleri.
    kazanma_olcutu: 'net' (net_pnl_yerel > 0) | 'r' (r > 0) — stratejilerin kendi kazanma_orani tanımıyla aynı olmalı.
    -> {'ajanlar','enstrumanlar','strateji_enstruman'}; toplamlar stratejiler.json katkılarıyla birebir tutar."""
    acik = acik_pozisyonlar or []
    # --- ajanlar
    ajanlar = []
    for a in dict.fromkeys(s["ajan"] for s in stratejiler):
        sts = [s for s in stratejiler if s["ajan"] == a]
        ids = {s["kimlik"] for s in sts}
        ls = [x for x in satirlar if x["kimlik"] in ids]
        kat = sum((Decimal(s["ozsermaye_katkisi"]) for s in sts), Decimal(0))
        ajanlar.append({"ajan": a, "strateji_sayisi": len(sts), "ozsermaye_katkisi": d.para(kat), "katki_getiri": d.sayi(kat / bas),
                        "islem_sayisi": len(ls),
                        "kazanma_orani": d.sayi(sum(1 for x in ls if _kazandi(x, kazanma_olcutu)) / len(ls)) if ls else None,
                        "pf": _pf(ls), "acik_pozisyon": sum(1 for p in acik if p["kimlik"] in ids)})
    # --- enstrümanlar ve strateji x enstrüman
    semboller = sorted({k[1] for k in hucre_katki} | {x["sembol"] for x in satirlar} | {p["sembol"] for p in acik})
    enst, matris = [], []
    for sm in semboller:
        ls = [x for x in satirlar if x["sembol"] == sm]
        ap = [p for p in acik if p["sembol"] == sm]
        h = {k: v for k, v in hucre_katki.items() if k[1] == sm}
        tam = all(v is not None for v in h.values()) and bool(h) and {x["kimlik"] for x in ls} <= {k[0] for k in h}
        kat = sum((v for v in h.values()), Decimal(0)) if tam else None
        kim = {x["kimlik"] for x in ls} | {p["kimlik"] for p in ap} | {k[0] for k in h}
        enst.append({"sembol": sm, "strateji_sayisi": len(kim), "ozsermaye_katkisi": d.para(kat) if kat is not None else None,
                     "katki_getiri": d.sayi(kat / bas) if kat is not None else None, "islem_sayisi": len(ls),
                     "kazanma_orani": d.sayi(sum(1 for x in ls if _kazandi(x, kazanma_olcutu)) / len(ls)) if ls else None,
                     "acik_pozisyon": len(ap), **({} if tam else {"katki_neden": "bu enstrümandaki katkı en az bir stratejide ölçülmedi"})})
    gruplar = defaultdict(lambda: {"kat": Decimal(0), "tam": True, "islem": 0, "acik": 0, "var": False})
    for (kim, sm), v in hucre_katki.items():
        g = gruplar[(kim.split("|")[0], sm)]
        g["var"] = True
        if v is None:
            g["tam"] = False
        else:
            g["kat"] += v
    for x in satirlar:
        gruplar[(x["kimlik"].split("|")[0], x["sembol"])]["islem"] += 1
    for p in acik:
        gruplar[(p["kimlik"].split("|")[0], p["sembol"])]["acik"] += 1
    for (ad, sm), g in sorted(gruplar.items()):
        matris.append({"strateji": ad, "sembol": sm, "ozsermaye_katkisi": d.para(g["kat"]) if g["tam"] and g["var"] else None,
                       "islem_sayisi": g["islem"], "acik_pozisyon": g["acik"],
                       **({} if g["tam"] and g["var"] else {"katki_neden": "bu hücrenin katkısı ölçülmedi"})})
    return {"ajanlar": ajanlar, "enstrumanlar": enst, "strateji_enstruman": matris}


# ---------------------------------------------------------------------------- bekleyen_emirler[]
def bekleyen_emirler(motor) -> list:
    """Paper motorunun henüz yürütülmemiş emirleri (bir sonraki mumun açılışında): giriş (sinyal modu), hedef ağırlık (portföy),
    kapanış (çıkış nedeni) ve küçültme. `sinyal_zamani` = kararın verildiği mum KAPANIŞI (birimin son işlenen mumu)."""
    out = []
    for kol in motor.tum_kollar:
        b = motor.birimler.get(kol.birim)
        sz = d.zaman_str(_utc(b.son_t) + b.aralik) if b is not None and b.son_t is not None else None
        acik = motor.acik.get(kol.kimlik)
        ek = {"kimlik": kol.kimlik, "sembol": kol.sembol, "sinyal_zamani": sz}

        def f(v):
            return None if v is None or (isinstance(v, float) and v != v) else str(v)
        if kol.giris_emri is not None and acik is None:
            yon, stop, hedef, _zc = kol.giris_emri
            out.append({**ek, "tur": "giris", "yon": "long" if yon == 1 else "short", "emir": "piyasa (sonraki mum açılışı)",
                        "stop": f(stop), "hedef": f(hedef)})
        if kol.hedef_emri is not None:
            yon, w_abs, stop = kol.hedef_emri
            out.append({**ek, "tur": "hedef_agirlik", "yon": "long" if yon == 1 else ("short" if yon == -1 else "kapat"),
                        "emir": f"hedef ağırlık {w_abs}" if yon != 0 else "pozisyonu kapat (hedef 0)", "stop": f(stop), "hedef": None})
        if kol.cikis_emri and acik is not None:
            out.append({**ek, "tur": "cikis", "yon": "kapat", "emir": f"çıkış: {kol.cikis_emri}", "stop": f(acik.stop), "hedef": None})
        if kol.kucult_emri is not None and acik is not None:
            out.append({**ek, "tur": "kucultme", "yon": "küçült", "emir": f"küçült x{kol.kucult_emri:.4f}", "stop": f(acik.stop), "hedef": None})
    out.sort(key=lambda x: (x["sinyal_zamani"] or "", x["kimlik"]))
    return out
