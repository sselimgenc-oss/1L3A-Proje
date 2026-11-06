"""Kullanım: python3 -m tv.calistir [strateji_adi ...]  → tv/sonuclar/<ad>.json + ozet.csv
Her strateji modülü: ISIM, PINE_ID, PARAM, TF, EVREN (grup listesi), NEDEN, sinyal(df, **P) -> sözlük."""
import sys, json, importlib, pkgutil, time, numpy as np, pandas as pd, pathlib, traceback
from . import motor, veri, analiz
K = pathlib.Path(__file__).parent
SON = K/"sonuclar"
GRUPLAR = dict(kripto=veri.KRIPTO, bist=veri.BIST, abd=veri.ABD, emtia=list(veri.EMTIA), endeks=list(veri.ENDEKS))
_VERI = {}

def getir(ad, tf):
    k = (ad, tf)
    if k not in _VERI:
        d = veri.al(ad, tf)
        _VERI[k] = None if d is None or len(d) < 250 else d.dropna()
    return _VERI[k]

def evren(mod):
    out = []
    if hasattr(mod, "SEMBOL"):   # açık sembol listesi (ör. yalnız 5dk verisi indirilmiş semboller)
        for ad in mod.SEMBOL:
            d = getir(ad, mod.TF)
            if d is not None: out.append((veri.grup(ad), ad, d))
        return out
    for g in mod.EVREN:
        for ad in GRUPLAR[g]:
            d = getir(ad, mod.TF)
            if d is not None: out.append((g, ad, d))
    return out

def kos(mod, ev, P, carpan=1.0):
    res = []
    for g, ad, d in ev:
        try:
            S = mod.sinyal(d, **P)
            # bacaklar: kısmi çıkışlı Pine stratejileri, her biri kendi çıkış kurallı ve pay (olcek) toplamı 1 olan ayrı bacaklar olarak koşulur
            for B in (S["bacaklar"] if "bacaklar" in S else [S]):
                res.append(motor.calistir(d, B, g, ad, carpan, getattr(mod, "YON", 0), len(ev)))
        except Exception as e:
            print("   hata", mod.ISIM, ad, repr(e)[:120], file=sys.stderr); raise
    return res

def degerlendir(mod):
    ev = evren(mod)
    kripto_mi = all(g == "kripto" for g, _, _ in ev)
    bas = min(d.index[0] for _, _, d in ev); son = max(d.index[-1] for _, _, d in ev)
    kesim = bas + (son-bas)*0.7
    P = dict(mod.PARAM)
    res = kos(mod, ev, P)
    m, tab, egri = analiz.olc(res, None, kripto_mi, kesim)
    # tür: gün içi / swing
    gun = m.get("tutma_gun", 99) < 1.0
    m["tur"] = "gun" if gun else "swing"
    # maliyet x2
    m2, _, _ = analiz.olc(kos(mod, ev, P, 2.0), None, kripto_mi)
    m["pf_maliyet2x"] = m2.get("pf", np.nan)
    # komşular
    rng = np.random.default_rng(7)
    nb = analiz.komsular(P, rng)
    if len(nb) > 24: nb = [nb[i] for i in rng.choice(len(nb), 24, replace=False)]
    karda = 0
    for Q in nb:
        try:
            mq, _, _ = analiz.olc(kos(mod, ev, Q), None, kripto_mi)
            karda += int(mq.get("kar", 0) > 0)
        except Exception: pass
    m["komsu_n"] = len(nb); m["komsu_karda"] = karda/len(nb) if nb else np.nan
    # enstrüman bazında kâr
    pes = {}
    for r in res: pes[r.sembol] = pes.get(r.sembol, 0.0) + float(r.mtm[-1])   # bacaklar enstrüman başına toplanır
    pe = [v for k, v in pes.items() if any(len(r.ts) for r in res if r.sembol == k)]
    m["enstr_n"] = len(pes); m["enstr_karda"] = float(np.mean([x > 0 for x in pe])) if pe else 0.0
    # korelasyon (mevcut stratejiler)
    try:
        mev = pd.read_csv(K.parent/"ortak/backtest_gunluk_getiri.csv", index_col=0, parse_dates=True)
        r = egri.pct_change().dropna(); r.index = r.index.normalize()
        j = pd.concat([r.rename("x"), mev], axis=1, join="inner").dropna()
        m["maks_kor"] = float(j.corr()["x"].drop("x").abs().max()) if len(j) > 60 else np.nan
    except Exception: m["maks_kor"] = np.nan
    return m, tab, ev

def kurallar(m):
    n_esik = 300 if m["tur"] == "gun" else 100
    t = lambda x: bool(x) if x == x else False
    k = {
     "1_islem_sayisi": m["n"] >= n_esik,
     "2_maks_dusus<=20": t(m.get("maxdd", 1) <= 0.20),
     "3_beklenti>=0.15R": t(m.get("beklenti_R", -1) >= 0.15),
     "4a_kf>=1.3": t(m.get("pf", 0) >= 1.3), "4b_sharpe>=1": t(m.get("sharpe", -9) >= 1.0),
     "5_oos": t(m.get("sharpe_oos", -9) >= 0.5*m.get("sharpe_egitim", 9) and m.get("oos_kar", -1) > 0),
     "6_maliyet2x_kf>=1.1": t(m.get("pf_maliyet2x", 0) >= 1.1),
     "7_komsu>=70": t(m.get("komsu_karda", 0) >= 0.7),
     "8_enstr>=60": t(m.get("enstr_karda", 0) >= 0.6),
    }
    return k

def calistir_modul(ad):
    mod = importlib.import_module(f"tv.stratejiler.{ad}")
    t0 = time.time()
    m, tab, ev = degerlendir(mod)
    k = kurallar(m)
    m = {kk: (None if (isinstance(v, float) and (v != v)) else v) for kk, v in m.items()}
    cikti = dict(ad=ad, pine_id=mod.PINE_ID, tf=mod.TF, evren=mod.EVREN, neden=mod.NEDEN, olcut=m, kurallar=k, gecti=all(k.values()))
    (SON/f"{ad}.json").write_text(json.dumps(cikti, ensure_ascii=False, indent=1, default=float))
    print(f"{ad:28s} n={m['n']:5d} PF={m.get('pf') or 0:.2f} Sh={m.get('sharpe') or 0:.2f} DD={m.get('maxdd') or 0:.2f} "
          f"E={m.get('beklenti_R') or 0:.2f}R OOS={m.get('sharpe_oos') or 0:.2f}/{m.get('sharpe_egitim') or 0:.2f} "
          f"k={m.get('komsu_karda') or 0:.2f} e={m.get('enstr_karda') or 0:.2f} {'GEÇTİ' if cikti['gecti'] else 'kaldı'} ({time.time()-t0:.0f}sn)", flush=True)
    return cikti

def hepsi():
    return sorted(x.name for x in pkgutil.iter_modules([str(K/"stratejiler")]) if not x.name.startswith("_"))

if __name__ == "__main__":
    for ad in (sys.argv[1:] or hepsi()):
        try: calistir_modul(ad)
        except Exception: traceback.print_exc(); print("HATA", ad)
