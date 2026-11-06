"""TradingView'den geçen stratejilerin kağıt botu (gerçek para yok). 10.000 $ sanal bakiye, geçenler arasında eşit.

Her çalıştırmada başlangıç tarihinden bugüne kadar olan tarihçeyi YENİDEN OYNATIR (kaçırılan saat işlem kaybettirmez).

  python3 -m tv.kagit --durum kagit_tv_durum                     # canlı veri (Binance spot + Yahoo)
  python3 -m tv.kagit --durum /tmp/d --bas 2026-09-01 --simdi "2026-10-13 12:00" --yerel   # önbellek verisiyle deneme

Dosyalar (durum dizini): durum.json, islemler.csv, ozsermaye.csv, ozet.md
"""
import argparse, json, sys, importlib, re
from pathlib import Path
import numpy as np, pandas as pd, requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tv import motor, veri                                                       # noqa: E402

K = Path(__file__).resolve().parent
SERMAYE = 10000.0
BASLANGIC = "2026-10-14"        # geçişten sonraki ilk gün 00:00 UTC
SURE_GUN = 57                   # bitiş: 10 Aralık 2026 00:00 UTC
GRUPLAR = dict(kripto=veri.KRIPTO, bist=veri.BIST, abd=veri.ABD, emtia=list(veri.EMTIA))
NEDEN_CIKIS = {1: "ters yönde giriş sinyali geldiği için pozisyon çevrildi", 2: "stratejinin çıkış koşulu oluştu",
               11: "stop seviyesi vuruldu", 12: "hedef seviyesi vuruldu", 13: "azami tutma süresi doldu"}
GUN_BIRIM = {"1d": pd.Timedelta(days=1), "4h": pd.Timedelta(hours=4), "1h": pd.Timedelta(hours=1)}


# ------------------------------------------------------------------ veri
def _kripto_canli(sym, iv, n):
    sure = {"1h": 3600, "1d": 86400}[iv]*1000; out = []; son = int(pd.Timestamp.now('UTC').timestamp()*1000)
    bas = son - n*sure
    while bas < son:
        r = requests.get("https://data-api.binance.vision/api/v3/klines", params=dict(symbol=sym+"USDT", interval=iv, startTime=bas, limit=1000), timeout=30)
        r.raise_for_status(); d = r.json()
        if not d: break
        out += d; bas = d[-1][0] + sure
        if len(d) < 1000: break
    df = pd.DataFrame(out).iloc[:, :6]; df.columns = ["t", "o", "h", "l", "c", "v"]
    df.index = pd.to_datetime(df.pop("t"), unit="ms"); return df.astype(float)

def _yahoo_canli(sym, iv):
    import yfinance as yf
    d = yf.Ticker(sym).history(auto_adjust=True, interval=iv, period="6y" if iv == "1d" else "729d")
    d = d[["Open", "High", "Low", "Close", "Volume"]]; d.columns = ["o", "h", "l", "c", "v"]
    if d.index.tz is not None: d.index = d.index.tz_convert("UTC").tz_localize(None)
    return d[~d.index.duplicated()]

def al(ad, tf, yerel, simdi):
    """Kapanmış mumlar (simdi'ye göre). yerel=True ise önbellekteki arşiv verisi."""
    if yerel: d = veri.al(ad, tf)
    else:
        if ad in veri.KRIPTO:
            h = _kripto_canli(ad, "1d", 1500) if tf == "1d" else _kripto_canli(ad, "1h", 4000)
        else:
            s = ad + ".IS" if ad in veri.BIST else veri.EMTIA.get(ad, ad)
            h = _yahoo_canli(s, "1d" if tf == "1d" else "1h")
        d = h if tf in ("1d", "1h") else h.resample("4h").agg(dict(o="first", h="max", l="min", c="last", v="sum")).dropna()
    if d is None: return None
    birim = GUN_BIRIM[tf]
    return d[d.index + birim <= simdi]


# ------------------------------------------------------------------ yardımcı
def gecenler():
    f = K/"gecenler.json"
    return json.loads(f.read_text()) if f.exists() else []

def ilk_cumle(mod):
    s = (mod.__doc__ or "").strip().split("\n")[0]
    m = re.search(r"\):\s*(.*)", s); s = m.group(1) if m else s
    return (s.split(". ")[0])[:170].rstrip(".")

def calistir(dizin, simdi=None, bas=BASLANGIC, yerel=False):
    dizin.mkdir(parents=True, exist_ok=True)
    simdi = pd.Timestamp.now('UTC').tz_localize(None) if simdi is None else pd.Timestamp(simdi)
    bas = pd.Timestamp(bas); bitis = bas + pd.Timedelta(days=SURE_GUN)
    simdi_e = min(simdi, bitis)
    liste = gecenler()
    if not liste: print("Geçen strateji yok."); return
    sermaye_i = SERMAYE/len(liste)
    izgara = pd.date_range(bas, simdi_e.floor("h"), freq="1h")
    islemler, egri, acik, sutun = [], pd.DataFrame(index=izgara), {}, {}
    if len(izgara) == 0: print("Başlangıç henüz gelmedi."); _yaz(dizin, bas, bitis, simdi, liste, [], egri, {}, sermaye_i, False); return
    for ad in liste:
        mod = importlib.import_module(f"tv.stratejiler.{ad}")
        motor.SERMAYE = sermaye_i
        eksen = pd.Series(0.0, index=izgara); acik[ad] = []
        for g in mod.EVREN:
            for sem in GRUPLAR[g]:
                try: d = al(sem, mod.TF, yerel, simdi_e)
                except Exception as e: print("veri alınamadı", sem, repr(e)[:80]); continue
                if d is None or len(d) < 250: continue
                S = mod.sinyal(d, **mod.PARAM)
                i0 = int(d.index.searchsorted(bas))          # başlangıçtan önceki mumlar yalnız ısınma
                if i0 >= len(d): continue
                i0 = max(i0-1, 0); dd = d.iloc[i0:]
                S2 = {k: (v[i0:] if hasattr(v, "__len__") and not isinstance(v, str) else v) for k, v in S.items()}
                r = motor.calistir(dd, S2, g, sem, 1.0, getattr(mod, "YON", 0), sum(len(GRUPLAR[x]) for x in mod.EVREN))
                tab = motor.islem_tablosu(r)
                for _, t in tab.iterrows():
                    if t.neden == 20:
                        acik[ad].append(dict(sembol=sem, yon=int(t.yon), giris_zaman=str(t.giris), giris=float(t.gfiyat), son_fiyat=float(t.cfiyat),
                                             miktar=float(t.adet), anlik_kar=float(t.kar))); continue
                    islemler.append(dict(strateji=ad, sembol=sem, yon="long" if t.yon > 0 else "short", giris_zaman=str(t.giris), cikis_zaman=str(t.cikis),
                        giris=float(t.gfiyat), cikis=float(t.cfiyat), miktar=float(t.adet), R=(float(t.kar/t.risk) if t.risk > 0 else None), kar_usd=float(t.kar),
                        sebep_giris=f"{mod.ISIM}: {'long' if t.yon > 0 else 'short'} sinyali — {ilk_cumle(mod)}",
                        sebep_cikis=NEDEN_CIKIS.get(int(t.neden), "çıkış")))
                s = pd.Series(r.mtm, index=dd.index + GUN_BIRIM[mod.TF])   # mum kapanışında değerle
                s = s[~s.index.duplicated(keep="last")]
                eksen = eksen + s.reindex(izgara.union(s.index)).ffill().fillna(0.0).reindex(izgara)
        sutun[ad] = sermaye_i + eksen
    for ad, s in sutun.items(): egri[ad] = s
    egri["toplam"] = sum(sutun.values())
    _yaz(dizin, bas, bitis, simdi, liste, islemler, egri, acik, sermaye_i, simdi >= bitis)

def _yaz(dizin, bas, bitis, simdi, liste, islemler, egri, acik, sermaye_i, bitti):
    cols = ["strateji", "sembol", "yon", "giris_zaman", "cikis_zaman", "giris", "cikis", "miktar", "R", "kar_usd", "sebep_giris", "sebep_cikis"]
    pd.DataFrame(islemler, columns=cols).sort_values("cikis_zaman").to_csv(dizin/"islemler.csv", index=False, float_format="%.8g")
    e = egri.copy(); e.index.name = "zaman"; e.to_csv(dizin/"ozsermaye.csv", float_format="%.4f")
    son = float(egri["toplam"].iloc[-1]) if len(egri) else SERMAYE
    durum = dict(baslangic=str(bas), bitis=str(bitis), son_guncelleme=str(simdi), bitti=bool(bitti), sermaye=SERMAYE, strateji_sayisi=len(liste),
                 strateji_basi_sermaye=sermaye_i, toplam=son, islem_sayisi=len(islemler),
                 stratejiler={a: dict(ozsermaye=float(egri[a].iloc[-1]) if a in egri and len(egri) else sermaye_i, acik_pozisyon=acik.get(a, [])) for a in liste})
    poz = [dict(strateji=a, sembol=x["sembol"], yon="long" if x["yon"] > 0 else "short", giris_zaman=x["giris_zaman"], giris=x["giris"],
                son_fiyat=x["son_fiyat"], tutar_usd=x["giris"]*x["miktar"], kar_usd=x["anlik_kar"]) for a in liste for x in acik.get(a, [])]
    pd.DataFrame(poz, columns=["strateji", "sembol", "yon", "giris_zaman", "giris", "son_fiyat", "tutar_usd", "kar_usd"]).to_csv(
        dizin/"pozisyonlar.csv", index=False, float_format="%.8g")
    (dizin/"durum.json").write_text(json.dumps(durum, indent=1, ensure_ascii=False))
    L = [f"# TV kağıt test — {len(liste)} strateji, 10.000 $ sanal", f"Başlangıç {bas.date()}, bitiş {bitis.date()}, güncelleme {simdi}.", f"Toplam özsermaye: {son:,.2f} $ ({(son/SERMAYE-1)*100:+.2f}%), kapanan işlem: {len(islemler)}", ""]
    for a in liste:
        L.append(f"- {a}: {durum['stratejiler'][a]['ozsermaye']:,.2f} $, açık {len(acik.get(a, []))} pozisyon")
    (dizin/"ozet.md").write_text("\n".join(L)+"\n")
    print(f"Toplam {son:,.2f} $; {len(islemler)} kapanan işlem; {sum(len(v) for v in acik.values())} açık pozisyon.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", required=True); ap.add_argument("--bas", default=BASLANGIC); ap.add_argument("--simdi", default=None)
    ap.add_argument("--yerel", action="store_true", help="canlı yerine önbellek verisi (deneme)")
    a = ap.parse_args(); calistir(Path(a.durum), a.simdi, a.bas, a.yerel)
