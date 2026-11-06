"""Kağıt al-sat botu: KGT v3 (%50) + KMN (%50), 10.000$ sanal bakiye, 2 ay.

Her çalıştırmada (GitHub Actions, saatlik) durum dizininden durumu yükler, son işlenen saatten itibaren kapanmış
tüm 1S mumlarını sırayla işler (kaçırılan çalıştırmalar telafi edilir), durumu ve kayıtları yazar.

  python3 -m canli.kagit --durum kagit_durum                 # canlı (Binance spot verisi)
  python3 -m canli.kagit --durum /tmp/d --yerel 2025-03-01 --saat 240   # yerel veriyle yeniden oynatma (test)

Dosyalar (durum dizini): durum.json, islemler.csv, ozsermaye.csv, kmn_dengeleme.csv, ozet.md (son durum),
gunluk_rapor.md (bir UTC günü tamamlanınca; iş akışı bunu GitHub issue'ya yazıp siler).
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backtest import kripto_final as KF, strateji as st, kripto_strateji as ks, gostergeler as g   # noqa: E402
from backtest.kripto_evren import HARIC                                                        # noqa: E402
from backtest.momentum_sinyal import hedef_agirlik, AYAR as KMN_AYAR                           # noqa: E402
from canli.motor import KGTAltPortfoy, KMNDefter                                               # noqa: E402
from canli import veri                                                                         # noqa: E402

SERMAYE = 10000.0
PAY = dict(kgt=0.5, kmn=0.5)
SURE_GUN = 61
KGT_P = dict(KF.KGT)
FON_SAAT = (0, 8, 16)
TELAFI_MAKS_SAAT = 24 * 7


# ---------------------------------------------------------------- KGT sinyalleri (backtest ile aynı fonksiyonlar)
def kgt_diziler(df):
    """df: 1S mumları (eksik saatler ileri doldurulmuş). Döndürür: {gun_bas: (sinyal, stop)}, h4 trend dizisi."""
    out = {}
    bos = (df.high.values == df.low.values)
    for gb in KF.GUN_BASLARI:
        p = dict(KF.GIRIS, gun_bas=float(gb))
        st._IND.clear()
        s, stp, _, _, _ = st.gunluk_kirilim(df, p)
        _, _, gun, _ = st.gunluk_seviyeler(df, p["tz"], p["gun_bas"])
        gs = pd.Series(bos.astype(int), index=gun).groupby(level=0).sum()
        onceki = gs.shift(1).reindex(gun).fillna(0).to_numpy() >= 2
        s = np.where(bos | onceki, 0.0, s)
        out[gb] = (s, np.where(s > 0, stp, np.nan))
    h4 = ks._htf(df, "4h"); hc = h4.close.to_numpy()
    ef, es = g.ema(hc, KF.TREND["h4_f"]), g.ema(hc, KF.TREND["h4_s"])
    hy = np.where((ef > es) & (hc > ef), 1.0, np.where((ef < es) & (hc < ef), -1.0, 0.0))
    return out, g.htf_hizala(df.index, h4, {"hy": hy})["hy"]


def _tam_saat(df):
    """Eksik saatleri ileri doldur (backtest coin_df ile aynı: düz mum)."""
    if df is None or df.empty:
        return df
    z = pd.date_range(df.index[0], df.index[-1], freq="1h")
    d = df.reindex(z)
    c = d.close.ffill()
    for k in ("open", "high", "low"):
        d[k] = d[k].fillna(c)
    d["close"] = c
    d["volume"] = 1.0
    return d


# ---------------------------------------------------------------- durum
def yukle(dizin):
    f = dizin / "durum.json"
    return json.loads(f.read_text()) if f.exists() else None


def kaydet(dizin, d):
    (dizin / "durum.json").write_text(json.dumps(d, indent=1, default=float))


def ekle_csv(f, satirlar):
    if not satirlar:
        return
    df = pd.DataFrame(satirlar)
    if f.exists():
        eski = pd.read_csv(f, nrows=0).columns.tolist()
        if set(df.columns) - set(eski):          # yeni sütun: dosyayı birleşik sütunlarla yeniden yaz
            pd.concat([pd.read_csv(f), df], ignore_index=True).to_csv(f, index=False, float_format="%.8g")
            return
        df = df.reindex(columns=eski)
    df.to_csv(f, mode="a", header=not f.exists(), index=False, float_format="%.8g")


# ---------------------------------------------------------------- ana döngü
def calistir(dizin, simdi=None, kaynak=None, geri=0):
    """kaynak: test için veri sağlayıcı (mumlar, gunluk, evren, fonlama, dakika); None ise canlı (veri modülü)."""
    dizin.mkdir(parents=True, exist_ok=True)
    simdi = pd.Timestamp.utcnow().tz_localize(None) if simdi is None else pd.Timestamp(simdi)
    son_kapali = simdi.floor("h") - pd.Timedelta(hours=1)          # kapanmış son 1S mumunun açılışı
    K = kaynak or CanliKaynak()
    d = yukle(dizin)
    if d is None:
        bas = son_kapali.floor("D")
        d = dict(baslangic=str(simdi), bitis=str(simdi + pd.Timedelta(days=SURE_GUN)),
                 son_saat=str(son_kapali - pd.Timedelta(hours=geri)),                 # geri: yalnız deneme için
                 kmn_gun0=str(bas.date()), evren={}, kgt={}, kmn={}, bitti=False, gun_ozeti=None)
        print("Yeni kağıt hesap:", d["baslangic"], "->", d["bitis"])
        kaydet(dizin, d)
    if d.get("bitti"):
        print("Süre doldu; işlem yok."); return d
    bitis = pd.Timestamp(d["bitis"])
    kgt = {str(gb): KGTAltPortfoy(f"KGT-G{gb:02d}", SERMAYE * PAY["kgt"] / len(KF.GUN_BASLARI), KGT_P,
                                  d["kgt"].get(str(gb))) for gb in KF.GUN_BASLARI}
    kmn = {k: KMNDefter(f"KMN-{k}", SERMAYE * PAY["kmn"] / 2, 0.0007, d["kmn"].get(k)) for k in ("A", "B")}

    saatler = pd.date_range(pd.Timestamp(d["son_saat"]) + pd.Timedelta(hours=1), min(son_kapali, bitis), freq="1h")
    saatler = saatler[-TELAFI_MAKS_SAAT:]
    if len(saatler) == 0:
        print("Yeni kapanmış mum yok."); return d
    # evren: her saat kendi ayının evrenini kullanır (backtest ile aynı). Ay başında arşiv henüz yayımlanmadıysa
    # bir önceki ayın evreni o ay için kullanılır (sonradan değiştirilmez).
    for ay in sorted({str(z.to_period("M").to_timestamp().date()) for z in saatler}):
        if ay not in d["evren"]:
            e = K.evren(ay)
            if not e:
                onceki = sorted(a for a in d["evren"] if a < ay)
                if not onceki:
                    raise RuntimeError("evren alınamadı")
                e = d["evren"][onceki[-1]]
            d["evren"][ay] = e
    d["evren"] = {a: d["evren"][a] for a in sorted(d["evren"])[-3:]}
    ay_ev = lambda z: d["evren"][str(z.to_period("M").to_timestamp().date())]                     # noqa: E731
    aylar = {str(z.to_period("M").to_timestamp().date()) for z in saatler}
    kgt_ev = sorted({s for a in aylar for s in d["evren"][a][:KGT_P["evren_n"]] if K.spot(s)})
    # gerekli mumlar
    kgt_acik = set().union(*[set(p.poz) | set(p.bekleyen) for p in kgt.values()])
    kgt_tum = set(kgt_ev) | kgt_acik             # evrenden çıkan coinlerdeki açık pozisyonlar da çıkış sinyali alır
    gerek = sorted(kgt_tum | set().union(*[set(b.maruz) for b in kmn.values()]))
    df = {}
    for s in gerek:
        sp = K.spot(s)
        x = K.mumlar(sp, "1h", 150 if s in kgt_tum else 5, simdi) if sp else None
        if x is not None and len(x):
            df[s] = _tam_saat(x)
    diz = {s: kgt_diziler(df[s]) for s in kgt_tum if s in df and len(df[s]) > 24 * 60}
    kgt_ev_ay = {a: {s for s in d["evren"][a][:KGT_P["evren_n"]]} for a in aylar}
    fon_onbellek = {}

    def fon(s, z):
        if (s, z) not in fon_onbellek:
            fon_onbellek[(s, z)] = K.fonlama(s, z)
        return fon_onbellek[(s, z)]

    islemler, egri, deng = [], [], []
    for z in saatler:
        evren = ay_ev(z); oncelik = {s: i for i, s in enumerate(evren)}
        kgt_ev_k = kgt_ev_ay[str(z.to_period("M").to_timestamp().date())]
        mum = {s: tuple(df[s].loc[z, ["open", "high", "low", "close"]]) for s in df if z in df[s].index}
        fiyat = {s: m[3] for s, m in mum.items()}
        fon_saat = z.hour in FON_SAAT
        for gb, P in kgt.items():
            sg, ck = {}, {}
            for s, (sd, hy) in diz.items():
                i = df[s].index.get_loc(z) if z in df[s].index else None
                if i is None:
                    continue
                stp = sd[int(gb)][1][i]
                if s in kgt_ev_k and sd[int(gb)][0][i] > 0 and stp == stp:   # yeni giriş yalnız evrendekilere
                    sg[s] = float(stp)
                if hy[i] == -1:
                    ck[s] = -1
            fonl = {s: fon(s, z) for s in P.poz} if fon_saat else {}
            be = (lambda s, gir, tp, z=z: K.dakika(K.spot(s), z, gir, tp))
            islemler += P.bar(str(z), mum, sg, ck, oncelik, fonl, be)
        for k, B in kmn.items():
            B.fiyatla({s: fiyat[s] for s in B.maruz if s in fiyat})
            if fon_saat and B.maruz:
                B.fonla({s: fon(s, z) for s in B.maruz})
        if z.hour == 23:                                      # gün kapandı: KMN dengeleme günü mü?
            gun = (z.floor("D") - pd.Timestamp(d["kmn_gun0"])).days
            for k, kay in (("A", 0), ("B", 7)):
                if gun % 14 == kay:
                    W, kapanis = kmn_hedef(K, evren, z.floor("D"), simdi)
                    if len(W):
                        dv, ms = kmn[k].dengele(W.to_dict(), kapanis.to_dict())
                        deng.append(dict(zaman=str(z + pd.Timedelta(hours=1)), defter=k, devir=dv, masraf=ms,
                                         hedef=json.dumps({s: round(float(w), 4) for s, w in W.items()})))
        kd = sum(P.deger(fiyat) for P in kgt.values()); md = sum(B.deger_ for B in kmn.values())
        egri.append(dict(zaman=str(z), kgt=kd, kmn=md, toplam=kd + md,
                         kgt_poz=sum(len(P.poz) for P in kgt.values()), kmn_poz=sum(len(B.maruz) for B in kmn.values())))
        d["son_saat"] = str(z)
        if z.hour == 23:
            gunluk_rapor(dizin, d, egri, z)
    d["kgt"] = {gb: P.durum() for gb, P in kgt.items()}
    d["kmn"] = {k: B.durum() for k, B in kmn.items()}
    ekle_csv(dizin / "islemler.csv", islemler)
    ekle_csv(dizin / "ozsermaye.csv", egri)
    ekle_csv(dizin / "kmn_dengeleme.csv", deng)
    if pd.Timestamp(d["son_saat"]) >= bitis - pd.Timedelta(hours=1):
        d["bitti"] = True
        gunluk_rapor(dizin, d, egri, pd.Timestamp(d["son_saat"]), son=True)
    ozet(dizin, d, egri[-1] if egri else None)
    kaydet(dizin, d)
    print(f"{len(saatler)} saat işlendi ({saatler[0]} -> {saatler[-1]}), {sum(x['tur'] == 'kapanis' for x in islemler)} KGT işlemi kapandı, "
          f"{len(deng)} KMN dengelemesi. Toplam: {egri[-1]['toplam']:.2f}$")
    return d


def kmn_hedef(K, evren, gun, simdi):
    """Gün kapanışında (gun = günün başı) KMN hedef ağırlıkları ve kapanış fiyatları (spot günlük mumlar)."""
    aday = [s for s in evren[:KMN_AYAR["N"]] if K.spot(s)]
    kap = {}
    for s in aday:
        x = K.gunluk(K.spot(s), simdi)
        if x is not None:
            x = x[x.index <= gun]
            if len(x) and x.index[-1] == gun:
                kap[s] = x.close
    if not kap:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    C = pd.DataFrame(kap).sort_index()
    son = C.iloc[-KMN_AYAR["gecmis_gun"]:]
    uygun = [s for s in C.columns if len(C) >= KMN_AYAR["gecmis_gun"] and son[s].notna().all()]
    return hedef_agirlik(C, uygun), C.iloc[-1]


class CanliKaynak:
    def spot(self, s):
        return veri.spot_karsilik(s)

    def mumlar(self, sp, aralik, gun, simdi):
        return veri.mumlar(sp, aralik, gun)

    def gunluk(self, sp, simdi):
        return veri.mumlar(sp, "1d", 150)

    def evren(self, ay):
        return veri.aylik_evren(ay, HARIC)

    def fonlama(self, s, z):
        return veri.fonlama(s, z)

    def dakika(self, sp, z, giris, tp1):
        return veri.dakika_cozum(sp, z, giris, tp1)


class YerelKaynak:
    """Test: yerel backtest verisiyle 'canlı' çalıştırmayı taklit eder (ağ yok)."""
    def __init__(self):
        self.ev = pd.read_pickle(ks.KOK / "evren.pkl"); self._c = {}

    def _d(self, s):
        if s not in self._c:
            self._c[s] = pd.read_pickle(ks.KOK / "1h" / f"{s}.pkl")
        return self._c[s]

    def spot(self, s):
        return s if (ks.KOK / "1h" / f"{s}.pkl").exists() else None

    def mumlar(self, sp, aralik, gun, simdi):
        x = self._d(sp); x = x[(x.index < pd.Timestamp(simdi).floor("h")) & (x.index >= pd.Timestamp(simdi) - pd.Timedelta(days=gun))]
        return x[["open", "high", "low", "close", "quote_volume"]]

    def gunluk(self, sp, simdi):
        x = self.mumlar(sp, "1h", 160, pd.Timestamp(simdi).floor("D"))
        return x.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

    def evren(self, ay):
        return list(self.ev.get(pd.Timestamp(ay), []))

    def fonlama(self, s, z):
        f = self._d(s).funding
        return float(np.nan_to_num(f.get(pd.Timestamp(z), 0.0)))

    def dakika(self, sp, z, giris, tp1):
        return None


# ---------------------------------------------------------------- raporlar
def _tablo(d, egri_son):
    t = egri_son or {}
    bas = SERMAYE
    sat = [f"| Strateji | Değer ($) | Getiri |", "|---|---|---|"]
    for ad, k, pay in (("KGT v3", "kgt", PAY["kgt"]), ("KMN", "kmn", PAY["kmn"]), ("**Toplam**", "toplam", 1.0)):
        v = t.get(k, bas * pay)
        sat.append(f"| {ad} | {v:,.2f} | {100 * (v / (bas * pay) - 1):+.2f}% |")
    return "\n".join(sat)


def ozet(dizin, d, egri_son):
    poz = []
    for gb, P in d["kgt"].items():
        for s, x in P["poz"].items():
            poz.append(f"- KGT-G{int(gb):02d} {s}: giriş {x['giris']:.6g}, stop {x['stop']:.6g}, kısmi {'✓' if x['tp1_yapildi'] else '–'}")
    for k, B in d["kmn"].items():
        uz = ", ".join(f"{s} {v:+.0f}$" for s, v in sorted(B["maruz"].items(), key=lambda kv: -kv[1]))
        poz.append(f"- KMN-{k} ({B['deger']:.0f}$): {uz or 'pozisyon yok'}")
    (dizin / "ozet.md").write_text(f"# Kağıt al-sat — son durum ({d['son_saat']} UTC)\n\nBaşlangıç {d['baslangic'][:16]}, "
                                   f"bitiş {d['bitis'][:16]}\n\n{_tablo(d, egri_son)}\n\n## Açık pozisyonlar\n" + "\n".join(poz) + "\n")


def gunluk_rapor(dizin, d, egri, z, son=False):
    f = dizin / "ozsermaye.csv"
    gecmis = pd.read_csv(f) if f.exists() else pd.DataFrame()
    tum = pd.concat([gecmis, pd.DataFrame(egri)], ignore_index=True)
    tum["zaman"] = pd.to_datetime(tum.zaman); tum = tum.drop_duplicates("zaman").set_index("zaman")
    gun = tum[tum.index >= z.floor("D")]
    dd = 100 * (1 - tum.toplam / tum.toplam.cummax()).max()
    fi = dizin / "islemler.csv"
    isl = pd.read_csv(fi) if fi.exists() else pd.DataFrame()
    if len(isl) and "tur" in isl:                 # kısmi satış satırları işlem sayısına/kazanma oranına girmez
        isl = isl[isl.tur.fillna("kapanis") == "kapanis"]
    bugun = isl[pd.to_datetime(isl.cikis_zaman) >= z.floor("D")] if len(isl) else isl
    kaz = f"%{100 * (isl.R > 0).mean():.0f}" if len(isl) else "—"
    baslik = "SON RAPOR (2 ay tamamlandı)" if son else f"Günlük rapor — {z.date()}"
    metin = (f"## {baslik}\n\n{_tablo(d, tum.iloc[-1].to_dict())}\n\n"
             f"- Bugün: toplam {100 * (gun.toplam.iloc[-1] / gun.toplam.iloc[0] - 1) if len(gun) > 1 else 0:+.2f}%, "
             f"kapanan KGT işlemi {len(bugun)}\n"
             f"- Başlangıçtan beri: KGT işlem {len(isl)}, kazanma {kaz}, maks. düşüş %{dd:.1f}\n"
             f"- Açık: KGT {int(tum.kgt_poz.iloc[-1])} pozisyon, KMN {int(tum.kmn_poz.iloc[-1])} pozisyon\n\n"
             f"Backtest beklentisi (yıllık): toplam %35–45, maks. düşüş %15–20. Kağıt üzerinde, gerçek para yok.\n\n"
             f"---\n_Generated by [Claude Code](https://claude.ai/code)_\n")
    (dizin / "gunluk_rapor.md").write_text(metin)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", default="kagit_durum")
    ap.add_argument("--yerel", help="yerel veriyle test: başlangıç zamanı")
    ap.add_argument("--saat", type=int, default=48, help="yerel test: kaç saat ilerletilecek")
    ap.add_argument("--adim", type=int, default=1, help="yerel test: her çalıştırmada ilerlenen saat")
    ap.add_argument("--geri", type=int, default=0, help="deneme: yeni hesabı kaç saat geriden başlat")
    a = ap.parse_args()
    dz = Path(a.durum)
    if a.yerel:
        Y = YerelKaynak(); t = pd.Timestamp(a.yerel)
        for _ in range(0, a.saat, a.adim):
            t += pd.Timedelta(hours=a.adim)
            calistir(dz, simdi=t + pd.Timedelta(minutes=7), kaynak=Y)
    else:
        calistir(dz, geri=a.geri)
