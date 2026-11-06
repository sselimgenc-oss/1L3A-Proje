"""TradingView'den geçen stratejilerin kağıt botu (gerçek para yok). Her strateji sabit 3.333,33 $ ile kendi başlangıç tarihinden başlar;
başlamamış strateji sabit 3.333,33 $ sayılır, toplam = strateji özsermayelerinin toplamı. tv/gecenler.json: ["ad", ...] veya [{"ad":..., "bas":"YYYY-MM-DD"}].

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
SERMAYE_S = 3333.33          # strateji başına sabit sanal bakiye
BASLANGIC = "2026-10-14"        # geçişten sonraki ilk gün 00:00 UTC
SURE_GUN = 57                   # bitiş: 10 Aralık 2026 00:00 UTC
GRUPLAR = dict(kripto=veri.KRIPTO, bist=veri.BIST, abd=veri.ABD, emtia=list(veri.EMTIA), endeks=list(veri.ENDEKS))
NEDEN_CIKIS = {1: "ters yönde giriş sinyali geldiği için pozisyon çevrildi", 2: "stratejinin çıkış koşulu oluştu",
               11: "stop seviyesi vuruldu", 12: "hedef seviyesi vuruldu", 13: "azami tutma süresi doldu"}
def birim(tf):
    m = re.fullmatch(r"(\d+)([mhd])", tf); n = int(m.group(1))
    return pd.Timedelta(n, dict(m="min", h="h", d="D")[m.group(2)])


# ------------------------------------------------------------------ veri
_SATIR = {"5m": 12000, "15m": 8000, "1h": 4000, "1d": 1500}
def _kripto_canli(sym, iv, n):
    sure = {"5m": 300, "15m": 900, "1h": 3600, "1d": 86400}[iv]*1000; out = []; son = int(pd.Timestamp.now('UTC').timestamp()*1000)
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
    per = {"1d": "11y", "1h": "729d", "15m": "59d"}[iv]
    d = yf.Ticker(sym).history(auto_adjust=True, interval=iv, period=per)
    d = d[["Open", "High", "Low", "Close", "Volume"]]; d.columns = ["o", "h", "l", "c", "v"]
    if d.index.tz is not None: d.index = d.index.tz_convert("UTC").tz_localize(None)
    return d[~d.index.duplicated()]

def canli_yama():
    """veri.kripto / veri.yahoo'yu canlı indirmeye çevirir; türetilmiş zaman dilimleri, yardımcı seriler (VIX, US10Y...) veri.al üzerinden aynen çalışır."""
    veri.kripto = lambda sym, iv, bas=None: _kripto_canli(sym, iv, _SATIR[iv])
    veri.yahoo = lambda sym, iv, **kw: _yahoo_canli(sym, iv)

_ON = {}
def al(ad, tf, simdi):
    """Kapanmış mumlar (simdi'ye göre)."""
    k = (ad, tf)
    if k not in _ON: _ON[k] = veri.al(ad, tf)
    d = _ON[k]
    if d is None: return None
    return d[d.index + birim(tf) <= simdi]


# ------------------------------------------------------------------ yardımcı
def gecenler(liste="gecenler"):
    """[(ad, başlangıç Timestamp)] — gecenler.json girişi ad (metin) ya da {"ad","bas"}."""
    f = K/f"{liste}.json"
    if not f.exists(): return []
    return [((x, pd.Timestamp(BASLANGIC)) if isinstance(x, str) else (x["ad"], pd.Timestamp(x.get("bas", BASLANGIC)))) for x in json.loads(f.read_text())]

def ilk_cumle(mod):
    s = (mod.__doc__ or "").strip().split("\n")[0]
    m = re.search(r"\):\s*(.*)", s); s = m.group(1) if m else s
    return (s.split(". ")[0])[:170].rstrip(".")

def _kes(v, i0):
    return v[i0:] if hasattr(v, "__len__") and not isinstance(v, (str, dict, list)) else v

def _bacaklar(S, i0):
    out = []
    for B in (S["bacaklar"] if "bacaklar" in S else [S]):
        out.append({k: _kes(v, i0) for k, v in B.items()})
    return out

def calistir(dizin, simdi=None, yerel=False, bas_zorla=None, liste_adi="gecenler"):
    dizin.mkdir(parents=True, exist_ok=True)
    simdi = pd.Timestamp.now('UTC').tz_localize(None) if simdi is None else pd.Timestamp(simdi)
    liste = gecenler(liste_adi)
    if not liste: print("Listede strateji yok."); return
    if bas_zorla: liste = [(a, pd.Timestamp(bas_zorla)) for a, _ in liste]
    if not yerel: canli_yama()
    bas0 = min(b for _, b in liste); bitis = bas0 + pd.Timedelta(days=SURE_GUN)
    simdi_e = min(simdi, bitis)
    izgara = pd.date_range(bas0, max(simdi_e.floor("h"), bas0), freq="1h")
    islemler, egri, acik, sutun, baslangic = [], pd.DataFrame(index=izgara), {}, {}, {}
    for ad, bas in liste:
        baslangic[ad] = bas
        mod = importlib.import_module(f"tv.stratejiler.{ad}")
        motor.SERMAYE = SERMAYE_S
        eksen = pd.Series(0.0, index=izgara); acik[ad] = []
        if simdi_e < bas: sutun[ad] = SERMAYE_S + eksen; continue      # henüz başlamadı: sabit bakiye
        sem_l = getattr(mod, "SEMBOL", None)
        ev = [(veri.grup(x), x) for x in sem_l] if sem_l else [(g, x) for g in mod.EVREN for x in GRUPLAR[g]]
        N = len(ev); b = birim(mod.TF)
        for g, sem in ev:
            try: d = al(sem, mod.TF, simdi_e)
            except Exception as e: print("veri alınamadı", sem, repr(e)[:80]); continue
            if d is None or len(d) < 250: continue
            S = mod.sinyal(d, **mod.PARAM)
            i0 = int(d.index.searchsorted(bas))          # başlangıçtan önceki mumlar yalnız ısınma
            if i0 >= len(d): continue
            i0 = max(i0-1, 0); dd = d.iloc[i0:]
            for B in _bacaklar(S, i0):
                r = motor.calistir(dd, B, g, sem, 1.0, getattr(mod, "YON", 0), N)
                tab = motor.islem_tablosu(r)
                for _, t in tab.iterrows():
                    if t.neden == 20:
                        acik[ad].append(dict(sembol=sem, yon=int(t.yon), giris_zaman=str(t.giris), giris=float(t.gfiyat), son_fiyat=float(t.cfiyat),
                                             miktar=float(t.adet), anlik_kar=float(t.kar))); continue
                    islemler.append(dict(strateji=ad, sembol=sem, yon="long" if t.yon > 0 else "short", giris_zaman=str(t.giris), cikis_zaman=str(t.cikis),
                        giris=float(t.gfiyat), cikis=float(t.cfiyat), miktar=float(t.adet), R=(float(t.kar/t.risk) if t.risk > 0 else None), kar_usd=float(t.kar),
                        sebep_giris=f"{mod.ISIM}: {'long' if t.yon > 0 else 'short'} sinyali — {ilk_cumle(mod)}",
                        sebep_cikis=NEDEN_CIKIS.get(int(t.neden), "çıkış")))
                s = pd.Series(r.mtm, index=dd.index + b)   # mum kapanışında değerle
                s = s[~s.index.duplicated(keep="last")]
                eksen = eksen + s.reindex(izgara.union(s.index)).ffill().fillna(0.0).reindex(izgara)
        sutun[ad] = SERMAYE_S + eksen
    for ad, s in sutun.items(): egri[ad] = s
    egri["toplam"] = sum(sutun.values())
    _yaz(dizin, bas0, bitis, simdi, liste, islemler, egri, acik, baslangic, simdi >= bitis)

def _yaz(dizin, bas, bitis, simdi, liste, islemler, egri, acik, baslangic, bitti):
    adlar = [a for a, _ in liste]
    cols = ["strateji", "sembol", "yon", "giris_zaman", "cikis_zaman", "giris", "cikis", "miktar", "R", "kar_usd", "sebep_giris", "sebep_cikis"]
    pd.DataFrame(islemler, columns=cols).sort_values("cikis_zaman").to_csv(dizin/"islemler.csv", index=False, float_format="%.8g")
    e = egri.copy(); e.index.name = "zaman"; e.to_csv(dizin/"ozsermaye.csv", float_format="%.4f")
    toplam0 = SERMAYE_S*len(liste); son = float(egri["toplam"].iloc[-1]) if len(egri) else toplam0
    durum = dict(baslangic=str(bas), bitis=str(bitis), son_guncelleme=str(simdi), bitti=bool(bitti), strateji_basi_sermaye=SERMAYE_S, sermaye=toplam0,
                 strateji_sayisi=len(liste), toplam=son, islem_sayisi=len(islemler),
                 stratejiler={a: dict(baslangic=str(baslangic[a]), basladi=bool(simdi >= baslangic[a]), ozsermaye=float(egri[a].iloc[-1]) if a in egri and len(egri) else SERMAYE_S,
                                      acik_pozisyon=acik.get(a, [])) for a in adlar})
    poz = [dict(strateji=a, sembol=x["sembol"], yon="long" if x["yon"] > 0 else "short", giris_zaman=x["giris_zaman"], giris=x["giris"],
                son_fiyat=x["son_fiyat"], tutar_usd=x["giris"]*x["miktar"], kar_usd=x["anlik_kar"]) for a in adlar for x in acik.get(a, [])]
    pd.DataFrame(poz, columns=["strateji", "sembol", "yon", "giris_zaman", "giris", "son_fiyat", "tutar_usd", "kar_usd"]).to_csv(
        dizin/"pozisyonlar.csv", index=False, float_format="%.8g")
    (dizin/"durum.json").write_text(json.dumps(durum, indent=1, ensure_ascii=False))
    L = [f"# TV kağıt test — {len(liste)} strateji, strateji başına {SERMAYE_S:,.2f} $ sanal", f"İlk başlangıç {bas.date()}, bitiş {bitis.date()}, güncelleme {simdi}.",
         f"Toplam özsermaye: {son:,.2f} $ ({(son/toplam0-1)*100:+.2f}%), kapanan işlem: {len(islemler)}", ""]
    for a in adlar:
        d = durum['stratejiler'][a]
        L.append(f"- {a} (başlangıç {baslangic[a].date()}{'' if d['basladi'] else ', henüz başlamadı'}): {d['ozsermaye']:,.2f} $, açık {len(acik.get(a, []))} pozisyon")
    (dizin/"ozet.md").write_text("\n".join(L)+"\n")
    print(f"Toplam {son:,.2f} $; {len(islemler)} kapanan işlem; {sum(len(v) for v in acik.values())} açık pozisyon.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", required=True); ap.add_argument("--bas", default=None, help="tüm stratejiler için başlangıcı zorla (deneme)"); ap.add_argument("--simdi", default=None)
    ap.add_argument("--liste", default="gecenler", help="tv/<liste>.json: gecenler (varsayılan) | izleme")
    ap.add_argument("--yerel", action="store_true", help="canlı yerine önbellek verisi (deneme)")
    a = ap.parse_args(); calistir(Path(a.durum), a.simdi, a.yerel, a.bas, a.liste)
