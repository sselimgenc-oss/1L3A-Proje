"""Beklenti aralıkları (Aşama 2 kapanışı): paper trading sonucunu karşılaştırmak için.

KAYNAK (yalnız örneklem-DIŞI veriler; yeni backtest koşulmaz, dosyalar okunur):
  tek-grafik stratejiler: sonuclar/wf/islemler/<k3_kripto|k3_dk_v2>/<strateji>--<sembol>--<tf>.parquet (WF OOS işlemleri; pencere
      sınırları sonuclar/wf/<etiket>.csv oos_bas/oos_bit) + sonuclar/kilit/islemler/<kimlik>.parquet (kilitli dönem işlemleri).
  portföy stratejileri: sonuclar/wf_portfoy/gunluk/<etiket>/...parquet (OOS günlük getiri) + sonuclar/wf_portfoy/islemler/<etiket>/...
      (OOS işlemler) + sonuclar/kilit/gunluk ve islemler (kilitli dönem).
  OOS günleri = WF test pencereleri + kilitli dönem. WF'nin son TAM penceresinden sonrası ile kilit başlangıcı arasındaki
  günler (kısmi pencere) HİÇBİR örneklemde yoktur (boşluk; bloklar boşluğu aşmaz).

GÜNLÜK TABLO (her varlık için): ret (günlük getiri), n (o gün kapanan işlem), kazanan (o gün kapanan r>0 işlem).
  tek-grafik strateji: ret = Σ r x %1 (işlem başı %1 risk; wf_tarama OOS modeliyle aynı), çıkış gününe yazılır (bileşik toplanır).
  portföy stratejisi: ret = motorun günlük OOS getirisi (oos_getiri); işlem = pozisyon bacağı (yeniden dengeleme işlemi).
  tek_grafik kolu: dört tek-grafik stratejinin işlemleri TEK hesapta secim.yeniden_oyna ile (kilit testi set_testi ile aynı ayar:
      %1/işlem, toplam stop riski <= %5, 3x, günlük %3, kill %20); kabul edilen işlemler sayılır. Segment başına ayrı oynatma.
  portfoy kolu: üç portföy stratejisinin eşit ağırlıklı günlük ortalaması. set: kollar günlük 50/50 (secim.harmanla mantığı).
  Kol ve set yalnız TÜM 7 stratejinin OOS günlerinin KESİŞİMİNDE hesaplanır (kesişim kesintili olabilir -> segmentler).

BLOK BOOTSTRAP: hareketli blok (blok_gun = 14 gün; duyarlılık 7 ve 28), 10 000 örnek, tohum 42. Her örnek, havuzdaki gün
  bloklarını (blok bir segment içinde kalır) arka arkaya ekleyip pencere uzunluğuna (28 / 56 gün) keser. Pencere metrikleri:
  net getiri (bileşik), kapanan işlem sayısı, max düşüş (pencere içi zirveden), kazanma oranı (kapanan işlemlerde; işlemsiz pencere
  hariç, `oran_hesaplanabilir` sütunu kaç pencerede hesaplanabildiğini verir). Yüzdelikler: %5/%25/%50/%75/%95.
ALARM: 8 haftalık net getiri < %5 yüzdeliği VEYA 8 haftalık max düşüş > %95 yüzdeliği (alarm_esigi sütunu).

DÜRÜSTLÜK: set, WF OOS sonuçlarına bakılarak seçildi (oneri.csv) -> aralıklar iyimser yanlıdır; zaman içinde sabitlik (durağanlık)
varsayılır; kilitli dönem tek yıl; portföy kolunun işlem sayısı bacak sayısıdır.

CLI: python -m motor.arastirma.beklenti   -> sonuclar/final/beklenti_araliklari.csv + OZET.md
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import final_set
from motor.arastirma import secim as sec

KOK = Path(__file__).resolve().parents[2]
CIKTI = KOK / "sonuclar" / "final"
KILIT = pd.Timestamp("2025-11-01", tz="UTC")
RISK = 0.01
BLOK_GUN = 14
BLOK_DUYARLILIK = (7, 28)
N_ORNEK = 10_000
TOHUM = 42
PENCERE_HAFTA = (4, 8)
YUZDELIKLER = (5, 25, 50, 75, 95)
METRIKLER = ("net_getiri", "islem_sayisi", "max_dusus", "kazanma_orani")


# ============================================================================ günlük tablolar
def gunluk_tablo_islem(islemler: pd.DataFrame, gunler: pd.DatetimeIndex, risk: float = RISK) -> pd.DataFrame:
    """İşlem listesinden günlük (ret, n, kazanan). Çıkış günü `gunler` aralığına kırpılır (aralık sonrası kapananlar son güne yazılır)."""
    t = pd.DataFrame(0.0, index=gunler, columns=["ret", "n", "kazanan"])
    if len(islemler) == 0 or len(gunler) == 0:
        return t
    c = pd.DatetimeIndex(islemler["cikis_zamani"]).floor("D")
    c = c.where(c <= gunler[-1], gunler[-1]).where(c >= gunler[0], gunler[0])
    r = np.nan_to_num(islemler["r"].to_numpy(dtype=float))
    d = pd.DataFrame({"gun": c, "ret": r * risk, "n": 1.0, "kazanan": (r > 0).astype(float)}).groupby("gun").sum()
    d.index = pd.DatetimeIndex(d.index).as_unit(t.index.unit) if hasattr(t.index, "unit") else d.index
    t.loc[d.index, ["ret", "n", "kazanan"]] = d[["ret", "n", "kazanan"]].to_numpy()
    return t


def gunluk_tablo_portfoy(getiri: pd.Series, islemler: pd.DataFrame) -> pd.DataFrame:
    g = getiri.astype(float)
    if len(g):                       # veri olmayan takvim günleri (hafta sonu vb.) = düz gün: getiri 0 (wf_portfoy.secim_ve_oos ile aynı)
        g = g.reindex(pd.date_range(g.index[0], g.index[-1], freq="D", tz="UTC").as_unit(g.index.unit)).fillna(0.0)
    t = pd.DataFrame({"ret": g.to_numpy(), "n": 0.0, "kazanan": 0.0}, index=g.index)
    if len(islemler):
        c = pd.DatetimeIndex(islemler["cikis_zamani"]).floor("D")
        r = np.nan_to_num(islemler["r"].to_numpy(dtype=float))
        d = pd.DataFrame({"gun": c, "n": 1.0, "kazanan": (r > 0).astype(float)}).groupby("gun").sum()
        d = d[(d.index >= t.index[0]) & (d.index <= t.index[-1])]
        d.index = pd.DatetimeIndex(d.index).as_unit(t.index.unit)
        t.loc[d.index, ["n", "kazanan"]] = d[["n", "kazanan"]].to_numpy()
    return t


def _gun_araligi(bas, bit_dahil) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(bas).floor("D"), pd.Timestamp(bit_dahil).floor("D"), freq="D", tz="UTC")


# ============================================================================ veri toplama
def _wf_tek_aralik(wf_dosya: str, strateji: str, sembol: str, tf: str, kok: Path) -> tuple:
    d = pd.read_csv(kok / "sonuclar" / "wf" / f"{wf_dosya}.csv")
    r = d[(d.strateji == strateji) & (d.sembol == sembol) & (d.tf == tf)].iloc[-1]
    # test_bit hariç -> son OOS günü = bit - 1 gün
    return pd.Timestamp(r.oos_bas).floor("D"), pd.Timestamp(r.oos_bit).floor("D") - pd.Timedelta(days=1)


def _kid(kimlik: str) -> str:
    return kimlik.replace("|", "--")


def varliklar_yukle(set_: dict, kok: Path = KOK) -> dict:
    """-> {kimlik: {'tur','tablo','gun_set','islem' (tek: tüm OOS işlemleri), 'kaynak'}}. Dosya yoksa FileNotFoundError (açık)."""
    sonuc = pd.read_csv(kok / "sonuclar" / "kilit" / "sonuc.csv").set_index("kimlik")
    out = {}
    for s in set_["stratejiler"]:
        k, ad = s["kimlik"], f"{s['strateji']}--{s['sembol']}--{s['tf']}.parquet"
        wf_d = s["wf_dosya"]
        if s["kol"] == "tek_grafik":
            wf_i = pd.read_parquet(kok / "sonuclar" / "wf" / "islemler" / wf_d / ad)
            kl_i = pd.read_parquet(kok / "sonuclar" / "kilit" / "islemler" / f"{_kid(k)}.parquet")
            w0, w1 = _wf_tek_aralik(wf_d, s["strateji"], s["sembol"], s["tf"], kok)
            k1 = pd.Timestamp(sonuc.loc[k, "veri_son"]).floor("D")
            gunler = _gun_araligi(w0, w1).append(_gun_araligi(KILIT, k1))
            isl = pd.concat([wf_i, kl_i], ignore_index=True)
            # WF işlemleri WF segmentine, kilit işlemleri kilit segmentine kırpılır (boşluğa taşan çıkış segment sonuna yazılır)
            t1 = gunluk_tablo_islem(wf_i, _gun_araligi(w0, w1))
            t2 = gunluk_tablo_islem(kl_i, _gun_araligi(KILIT, k1))
            out[k] = {"tur": "tek", "tablo": pd.concat([t1, t2]), "islem": isl, "wf_islem": wf_i, "kilit_islem": kl_i, "sembol": s["sembol"],
                      "kaynak": f"wf_oos:{wf_d}+kilit", "wf_aralik": (w0, w1), "kilit_aralik": (KILIT, k1)}
        else:
            g1 = pd.read_parquet(kok / "sonuclar" / "wf_portfoy" / "gunluk" / wf_d / ad)["oos_getiri"].astype(float)
            g2 = pd.read_parquet(kok / "sonuclar" / "kilit" / "gunluk" / f"{_kid(k)}.parquet")["oos_getiri"].astype(float)
            i1 = pd.read_parquet(kok / "sonuclar" / "wf_portfoy" / "islemler" / wf_d / ad)
            i2 = pd.read_parquet(kok / "sonuclar" / "kilit" / "islemler" / f"{_kid(k)}.parquet")
            for g in (g1, g2):
                g.index = pd.DatetimeIndex(g.index).floor("D")
            t1, t2 = gunluk_tablo_portfoy(g1, i1), gunluk_tablo_portfoy(g2, i2)
            out[k] = {"tur": "portfoy", "tablo": pd.concat([t1, t2]), "islem": pd.concat([i1, i2], ignore_index=True),
                      "kaynak": f"wf_portfoy_oos:{wf_d}+kilit"}
    return out


def kesisim_gunleri(varliklar: dict) -> pd.DatetimeIndex:
    ks = None
    for v in varliklar.values():
        ix = v["tablo"].index
        ks = ix if ks is None else ks.intersection(ix)
    return ks.sort_values()


def segmentler(gunler: pd.DatetimeIndex) -> np.ndarray:
    """Ardışık olmayan günlerde yeni segment: her gün için segment numarası."""
    if len(gunler) == 0:
        return np.array([], dtype=int)
    kes = np.r_[0, (np.diff(gunler.asi8) != 86_400_000_000_000 // _birim_ns(gunler)).astype(int)]
    return np.cumsum(kes)


def _birim_ns(ix: pd.DatetimeIndex) -> int:
    return {"ns": 1, "us": 1000, "ms": 1_000_000, "s": 1_000_000_000}[ix.unit]


def kol_ve_set(set_: dict, varliklar: dict, kesisim: pd.DatetimeIndex) -> dict:
    """Kesişim günlerinde tek_grafik kolu (yeniden oynatma), portföy kolu (eşit ağırlık) ve set (50/50) tabloları."""
    seg = segmentler(kesisim)
    tek_idler = [s["kimlik"] for s in set_["stratejiler"] if s["kol"] == "tek_grafik"]
    pf_idler = [s["kimlik"] for s in set_["stratejiler"] if s["kol"] == "portfoy"]
    pay = set_["risk"]["kol_paylari"]
    tek_parcalar, tek_tablo_listesi = [], []
    for sg in np.unique(seg):
        gn = kesisim[seg == sg]
        bas, bit = gn[0], gn[-1]
        parcalar = {}
        for k in tek_idler:
            isl = varliklar[k]["islem"]
            gz = pd.DatetimeIndex(isl["giris_zamani"])
            sel = isl[(gz >= bas) & (gz < bit + pd.Timedelta(days=1))]
            if len(sel):
                parcalar[k] = (sel, varliklar[k]["sembol"])
        t = pd.DataFrame(0.0, index=gn, columns=["ret", "n", "kazanan"])
        if parcalar:
            tablo = sec.islem_tablosu_hazirla(parcalar, sec.VARSAYILAN_MALIYET)
            oy = sec.yeniden_oyna(tablo, sec.OynatmaAyari(), bas=bas, bit=bit)
            g = oy["getiri"].copy()
            g.index = pd.DatetimeIndex(g.index).as_unit(gn.unit) - pd.Timedelta(days=1)       # etiket = getirinin kazanıldığı gün
            g = g.reindex(gn).fillna(0.0)
            t["ret"] = g.to_numpy()
            kab = tablo.iloc[oy["kabul"]]
            c = pd.DatetimeIndex(kab["cikis"]).floor("D")
            c = c.where(c <= bit, bit)
            d = pd.DataFrame({"gun": c, "n": 1.0, "kazanan": (kab["r"].to_numpy() > 0).astype(float)}).groupby("gun").sum()
            d.index = pd.DatetimeIndex(d.index).as_unit(gn.unit)
            t.loc[d.index.intersection(gn), ["n", "kazanan"]] = d.loc[d.index.intersection(gn), ["n", "kazanan"]].to_numpy()
        tek_tablo_listesi.append(t)
    tek = pd.concat(tek_tablo_listesi)
    pf = sum(varliklar[k]["tablo"].loc[kesisim, ["ret", "n", "kazanan"]] for k in pf_idler)
    pf["ret"] = pf["ret"] / len(pf_idler)                        # eşit ağırlıklı günlük ortalama (n, kazanan toplanır)
    st = pd.DataFrame({"ret": pay["tek_grafik"] * tek["ret"] + pay["portfoy"] * pf["ret"],
                       "n": tek["n"] + pf["n"], "kazanan": tek["kazanan"] + pf["kazanan"]})
    return {"tek_grafik": tek, "portfoy": pf, "set": st}


# ============================================================================ bootstrap
def blok_bootstrap(tablo: pd.DataFrame, pencere_gun: int, blok_gun: int = BLOK_GUN, n: int = N_ORNEK, tohum: int = TOHUM) -> dict:
    """Hareketli blok bootstrap. Blok bir segment (ardışık gün) içinde kalır. -> {metrik: dizi[n]}, 'havuz_baslangic' sayısı."""
    seg = segmentler(tablo.index)
    ret = tablo["ret"].to_numpy(dtype=float)
    nn = tablo["n"].to_numpy(dtype=float)
    kz = tablo["kazanan"].to_numpy(dtype=float)
    L = len(ret)
    gecerli = np.array([i for i in range(L - blok_gun + 1) if seg[i] == seg[i + blok_gun - 1]], dtype=int)
    if len(gecerli) == 0:
        raise ValueError(f"bootstrap: {blok_gun} günlük blok için yeterince uzun segment yok")
    rng = np.random.default_rng(tohum)
    nb = math.ceil(pencere_gun / blok_gun)
    bas = gecerli[rng.integers(len(gecerli), size=(n, nb))]
    idx = (bas[:, :, None] + np.arange(blok_gun)[None, None, :]).reshape(n, nb * blok_gun)[:, :pencere_gun]
    r = ret[idx]
    eg = np.cumprod(1.0 + r, axis=1)
    zirve = np.maximum.accumulate(np.concatenate([np.ones((n, 1)), eg], axis=1), axis=1)[:, 1:]
    dd = ((zirve - eg) / zirve).max(axis=1)
    ni = nn[idx].sum(axis=1)
    kazanan = kz[idx].sum(axis=1)
    oran = np.where(ni > 0, kazanan / np.where(ni > 0, ni, 1.0), np.nan)
    return {"net_getiri": eg[:, -1] - 1.0, "islem_sayisi": ni, "max_dusus": dd, "kazanma_orani": oran,
            "n_baslangic": len(gecerli)}


def aralik_satirlari(kimlik: str, tur: str, tablo: pd.DataFrame, kaynak: str, kol: str = "", blok_gun: int = BLOK_GUN,
                     n: int = N_ORNEK, tohum: int = TOHUM) -> list:
    satirlar = []
    seg = segmentler(tablo.index)
    for hafta in PENCERE_HAFTA:
        b = blok_bootstrap(tablo, hafta * 7, blok_gun, n, tohum)
        for m in METRIKLER:
            x = b[m]
            gecerli = x[np.isfinite(x)]
            q = np.percentile(gecerli, YUZDELIKLER) if len(gecerli) else [np.nan] * len(YUZDELIKLER)
            satir = {"kimlik": kimlik, "tur": tur, "kol": kol, "pencere_hafta": hafta, "metrik": m,
                     "p05": q[0], "p25": q[1], "p50": q[2], "p75": q[3], "p95": q[4],
                     "alarm_yonu": "", "alarm_esigi": np.nan,
                     "oran_hesaplanabilir": float(len(gecerli) / len(x)),
                     "havuz_gun": int(len(tablo)), "n_segment": int(len(np.unique(seg))), "blok_gun": blok_gun, "n_orneklem": n,
                     "kaynak": kaynak}
            if hafta == 8 and m == "net_getiri":
                satir.update({"alarm_yonu": "alt", "alarm_esigi": q[0]})          # net < p05 -> uyarı
            if hafta == 8 and m == "max_dusus":
                satir.update({"alarm_yonu": "ust", "alarm_esigi": q[4]})          # düşüş > p95 -> uyarı
            satirlar.append(satir)
    return satirlar


def tum_tablo(set_: dict, varliklar: dict, kolset: dict, kesisim: pd.DatetimeIndex, **kw) -> pd.DataFrame:
    satirlar = []
    for s in set_["stratejiler"]:
        v = varliklar[s["kimlik"]]
        satirlar += aralik_satirlari(s["kimlik"], "strateji", v["tablo"], v["kaynak"], s["kol"], **kw)
    satirlar += aralik_satirlari("tek_grafik", "kol", kolset["tek_grafik"], "wf_oos+kilit (4 strateji yeniden oynatma, kesişim günleri)", "tek_grafik", **kw)
    satirlar += aralik_satirlari("portfoy", "kol", kolset["portfoy"], "wf_portfoy_oos+kilit (3 strateji eşit ağırlık, kesişim günleri)", "portfoy", **kw)
    satirlar += aralik_satirlari("set", "set", kolset["set"], "kollar 50/50 (kesişim günleri)", "", **kw)
    return pd.DataFrame(satirlar)


# ============================================================================ özet
def _p(x, d=1):
    return "-" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%"


def _al(df, kimlik, hafta, metrik):
    return df[(df.kimlik == kimlik) & (df.pencere_hafta == hafta) & (df.metrik == metrik)].iloc[0]


def kilit_kayan_pencere_orani(tablo: pd.DataFrame, esik_net: float, esik_dd: float, pencere_gun: int = 56) -> dict:
    """Kilitli yılda 8 haftalık kayan pencerelerin kaçı alarm eşiğini aşmış (tutarlılık kontrolü)."""
    t = tablo[tablo.index >= KILIT]
    seg = segmentler(t.index)
    ret = t["ret"].to_numpy()
    n_p, n_net, n_dd = 0, 0, 0
    for i in range(len(ret) - pencere_gun + 1):
        if seg[i] != seg[i + pencere_gun - 1]:
            continue
        eg = np.cumprod(1.0 + ret[i:i + pencere_gun])
        zirve = np.maximum.accumulate(np.r_[1.0, eg])[1:]
        n_p += 1
        n_net += int(eg[-1] - 1.0 < esik_net)
        n_dd += int(((zirve - eg) / zirve).max() > esik_dd)
    return {"n_pencere": n_p, "net_alti": n_net, "dusus_ustu": n_dd}


def ozet_yaz(df: pd.DataFrame, set_: dict, kolset: dict, kesisim: pd.DatetimeIndex, duyarlilik: dict, kilit_kayan: dict,
             yol: Path) -> str:
    sg = _al(df, "set", 8, "net_getiri")
    L = []
    L.append("# Beklenti aralıkları (paper trading ile karşılaştırma için)\n")
    L.append("Bu dosya, final setin (7 strateji) geçmiş **örneklem-dışı** sonuçlarından 'normal bir 4 ve 8 haftada ne görürüz?' "
             "aralığını çıkarır. Paper trading sonucu bu aralıkta kalıyorsa sistem beklendiği gibi çalışıyor demektir; aralığın "
             "dışına çıkması alarm nedenidir. Sayılar tahmindir, söz değildir.\n")
    L.append("## Set (tüm 7 strateji, kollar 50/50) — 4 ve 8 haftalık pencere\n")
    L.append("| ölçü | %5 | %25 | %50 | %75 | %95 |\n|---|---|---|---|---|---|")
    for h in (4, 8):
        for m, ad, bicim in (("net_getiri", "net getiri", "p"), ("max_dusus", "max düşüş", "p"), ("islem_sayisi", "işlem sayısı", "n"),
                             ("kazanma_orani", "kazanma oranı", "p")):
            r = _al(df, "set", h, m)
            f = (lambda x: _p(x)) if bicim == "p" else (lambda x: f"{x:.0f}")
            L.append(f"| {h} hafta {ad} | {f(r.p05)} | {f(r.p25)} | {f(r.p50)} | {f(r.p75)} | {f(r.p95)} |")
    dd = _al(df, "set", 8, "max_dusus")
    L.append("")
    L.append(f"**Alarm eşiği (set, 8 hafta):** net getiri {_p(sg.alarm_esigi)} altında VEYA düşüş {_p(dd.alarm_esigi)} üstünde ise uyarı.\n")
    L.append("## Strateji bazında (8 hafta, net getiri ve düşüş)\n")
    L.append("| strateji | net %5 | net %50 | net %95 | düşüş %50 | düşüş %95 (alarm: bunun üstü) | alarm: net bunun altı |\n|---|---|---|---|---|---|---|")
    for s in set_["stratejiler"]:
        a, b = _al(df, s["kimlik"], 8, "net_getiri"), _al(df, s["kimlik"], 8, "max_dusus")
        L.append(f"| {s['kimlik'].replace('|', ' / ')} | {_p(a.p05)} | {_p(a.p50)} | {_p(a.p95)} | {_p(b.p50)} | {_p(b.p95)} | {_p(a.alarm_esigi)} |")
    for kol in ("tek_grafik", "portfoy"):
        a, b = _al(df, kol, 8, "net_getiri"), _al(df, kol, 8, "max_dusus")
        L.append(f"| **kol: {kol}** | {_p(a.p05)} | {_p(a.p50)} | {_p(a.p95)} | {_p(b.p50)} | {_p(b.p95)} | {_p(a.alarm_esigi)} |")
    L.append("")
    L.append("Tüm sayılar (4 ve 8 hafta; net, işlem sayısı, max düşüş, kazanma oranı; %5/%25/%50/%75/%95): `beklenti_araliklari.csv`.\n")
    L.append("## Nasıl hesaplandı\n")
    L.append("- **Veri (yalnız örneklem-dışı):** tek-grafik stratejilerde walk-forward test pencerelerinin işlemleri + kilitli dönem (2025-11-01 sonrası) işlemleri; "
             "portföy stratejilerinde walk-forward OOS günlük getirileri + kilitli dönem günlükleri. Yeni backtest koşulmadı, mevcut dosyalar okundu: "
             "`sonuclar/wf`, `sonuclar/wf_portfoy`, `sonuclar/kilit`.")
    L.append(f"- **Set / kol hesabı:** yalnız 7 stratejinin de OOS'ta olduğu günlerde ({len(kesisim)} gün, {kesisim[0].date()} → {kesisim[-1].date()}; "
             "walk-forward'ın son tam penceresi ile kilit başlangıcı arasında boşluk var). Tek-grafik kolu tek hesapta, kilit testindeki limitlerle "
             "(işlem başı %1, toplam stop riski %5, 3x, günlük %3, kill %20) yeniden oynatıldı; portföy kolu 3 stratejinin eşit ortalaması; kollar 50/50.")
    L.append(f"- **Yöntem:** blok bootstrap — geçmiş günler {BLOK_GUN} günlük bloklar halinde yeniden karıştırılıp 28/56 günlük sahte pencereler "
             f"üretildi ({N_ORNEK} adet, tohum {TOHUM}); bloklar, ardışık günlerin birbirine bağlı olmasını korur.")
    L.append(f"- **Blok uzunluğu duyarlılığı (set, 8 hafta net %5 / %50 / %95):** "
             + "; ".join(f"blok {b}: {_p(v[0])} / {_p(v[1])} / {_p(v[2])}" for b, v in sorted({BLOK_GUN: duyarlilik[BLOK_GUN], **duyarlilik}.items())) + ".")
    L.append(f"- **Tutarlılık kontrolü:** kilitli yıldaki 8 haftalık kayan {kilit_kayan['n_pencere']} pencerenin {kilit_kayan['net_alti']} tanesi net alarm eşiğinin altında, "
             f"{kilit_kayan['dusus_ustu']} tanesi düşüş eşiğinin üstünde (bağımsız değil, kayan pencereler çakışır).\n")
    L.append("## Dürüst uyarılar\n")
    L.append("- Set, walk-forward OOS sonuçlarına bakılarak seçildi; bu yüzden aralıklar **iyimser** olabilir. Kilit testinde seçim yönteminin öngörü gücü zayıf çıktı (`sonuclar/kilit/RAPOR.md`).")
    L.append("- Geçmişin yeniden karıştırılması 'gelecek de buna benzer' varsayar. Piyasa rejimi değişirse aralık yanıltır; set için geçmiş yalnız birkaç yıl (çoğu kripto boğa/ayı karışımı).")
    L.append("- Kazanma oranı yalnız işlem kapanan pencerelerde hesaplanır (`oran_hesaplanabilir` sütunu). Portföy kolunun 'işlem'i pozisyon bacağıdır.")
    L.append("- Paper'da ilk 4 hafta çok kısa bir sınavdır; tek başına karar için kullanılmaz.")
    L.append("")
    Path(yol).write_text("\n".join(L), encoding="utf-8")
    return "\n".join(L)


def calistir(kok: Path = KOK, cikti: Path = CIKTI, n: int = N_ORNEK) -> pd.DataFrame:
    set_ = final_set.yukle(kok / "stratejiler" / "final_set.json")
    varliklar = varliklar_yukle(set_, kok)
    kesisim = kesisim_gunleri(varliklar)
    kolset = kol_ve_set(set_, varliklar, kesisim)
    df = tum_tablo(set_, varliklar, kolset, kesisim, n=n)
    cikti.mkdir(parents=True, exist_ok=True)
    df.to_csv(cikti / "beklenti_araliklari.csv", index=False)
    duy = {}
    for b in (BLOK_GUN, *BLOK_DUYARLILIK):
        x = blok_bootstrap(kolset["set"], 56, b, n)["net_getiri"]
        duy[b] = tuple(np.percentile(x, [5, 50, 95]))
    sg, dd = _al(df, "set", 8, "net_getiri"), _al(df, "set", 8, "max_dusus")
    kayan = kilit_kayan_pencere_orani(kolset["set"], sg.alarm_esigi, dd.alarm_esigi)
    ozet_yaz(df, set_, kolset, kesisim, duy, kayan, cikti / "OZET.md")
    return df


if __name__ == "__main__":
    d = calistir()
    print(d[(d.kimlik == "set")][["pencere_hafta", "metrik", "p05", "p25", "p50", "p75", "p95", "alarm_esigi"]].to_string())
