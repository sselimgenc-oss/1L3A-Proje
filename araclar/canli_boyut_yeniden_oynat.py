"""Canlı boyutlandırma yeniden oynatması (GEÇMİŞ; gelecek tahmini DEĞİL). Kullanıcı kararı 2026-11-11 (CANLI_LIMITLER).

paper_v2 setindeki tek-grafik stratejilerin v2 GELİŞTİRME dönemi (<= 2025-11-07, holdout OKUNMAZ) işlem listesi mevcut backtest makinesiyle
(`motor.arastirma.v2.ham` ile aynı: varsayılan ayar, v2 maliyet tablosu ×1, funding dahil) yeniden üretilir; her işlemin R'si (net K/Z / stopa
fiyat riski) korunur ve 165 USD'lik bir strateji hesabı için CANLI_LIMITLER boyutuyla yeniden oynatılır. Yeni yazılmış strateji/araştırma YOKTUR.

Kullanım:  python araclar/canli_boyut_yeniden_oynat.py --onbellek DIZIN [--sadece-oyna]
Çıktı: sonuclar/canli/boyut_yeniden_oynatma.csv (rapor metni BOYUT_RAPORU.md ayrıca yazılır).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import math
import sys
from decimal import Decimal as D
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from motor.canli.borsa import canli_limitler as cl          # noqa: E402
from motor.risk.limitler import SERT_LIMITLER               # noqa: E402

HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")          # sabit.HOLDOUT_BAS ile aynı: bu tarih ve sonrası okunmaz
KASA_USD = 165.0
MIN_TUTAR = {"BTCUSDT": 100.0, "ETHUSDT": 20.0}              # VARSAYIM (tutucu tablo): diğer semboller 5 USDT; adım (stepSize) yuvarlaması modellenmedi
MIN_TUTAR_DIGER = 5.0
TABLO = KOK / "sonuclar" / "evren" / "v2" / "maliyet_tablosu_v2.csv"
SET_YOLU = KOK / "stratejiler" / "paper_v2_seti.json"
CIKTI = KOK / "sonuclar" / "canli"


# ------------------------------------------------------------------------------------------------ 1) işlem listesi (backtest, yalnız geliştirme)
def _kur():
    from motor.arastirma import wf_evren as we
    from motor.arastirma.v2 import sabit
    we.veri_ayarla(None, sabit.DONEM)


def _gorev(a):
    ad, tf, sembol, yol = a
    from motor.arastirma import evren_maliyet
    from motor.arastirma import wf_evren as we
    from motor.arastirma.v2 import ham as hm
    from motor.backtest.motor import backtest
    from motor.strateji import funding
    yol = Path(yol)
    try:
        mumlar, fund = hm.veri_oku(sembol, tf)               # HoldoutSizintisi: >= 2025-11-08 veri varsa kesin hata
    except (FileNotFoundError, ValueError) as e:
        return (ad, sembol, "veri_yok", str(e)[:100])
    if not len(mumlar):
        return (ad, sembol, "veri_yok", "bos")
    etiket, st = hm.varsayilan_strateji(ad)
    kurallar = we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
    ay = evren_maliyet.maliyet_ayarlari(sembol, kurallar, 1.0, TABLO)
    hazir = funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf)
    res = backtest(hazir, st, ay, fund)
    isl = res.islemler
    if not len(isl):
        return (ad, sembol, "tamam", 0)
    ham, mtm = hm.islem_hazirla(isl, sembol, tf, 1.0, mumlar, TABLO)
    d = isl.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
    net, r0, miktar = d["net_pnl"].to_numpy(float), d["r"].to_numpy(float), d["miktar"].to_numpy(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        risk = np.where(r0 != 0, net / r0, np.nan)             # stopa fiyat riski (USD) = miktar x |giriş - stop|
    sd = np.where(np.isfinite(risk) & (risk > 0), risk / miktar, np.nan)
    sd = pd.Series(sd).where(lambda x: x.notna(), pd.Series(ham["sf"].to_numpy(float) * d["giris_fiyati"].to_numpy(float))).to_numpy()  # r==0: komşu stop oranı
    out = pd.DataFrame({"strateji": ad, "sembol": sembol, "islem_no": np.arange(len(d)), "yon": d["yon"].to_numpy(int),
                        "giris_zamani": pd.DatetimeIndex(d["giris_zamani"]), "cikis_zamani": pd.DatetimeIndex(d["cikis_zamani"]),
                        "giris_fiyati": d["giris_fiyati"].to_numpy(float), "stop_mesafe": sd, "r": ham["r"].to_numpy(float)})
    if out["cikis_zamani"].max() > HOLDOUT_BAS or out["giris_zamani"].max() >= HOLDOUT_BAS:   # veri_sonu kapanışı = son geliştirme barının kapanış anı (= HOLDOUT_BAS) izinli
        raise RuntimeError(f"{ad} {sembol}: holdout sızıntısı")
    out.to_parquet(yol / f"{ad}--{sembol}--islem.parquet", index=False)
    m = mtm.copy()
    m.insert(0, "strateji", ad)
    m.insert(1, "sembol", sembol)
    m.to_parquet(yol / f"{ad}--{sembol}--mtm.parquet", index=False)
    return (ad, sembol, "tamam", int(len(out)))


def topla(onbellek: Path, surec: int) -> None:
    from motor.arastirma.v2 import sabit
    s = json.loads(SET_YOLU.read_text(encoding="utf-8"))
    gorevler = []
    for k in s["stratejiler"]:
        if k["tur"] != "tek":
            continue
        for sm in sabit.evren_listesi(k["evren"]):
            gorevler.append((k["strateji"], k["tf"], sm, str(onbellek)))
    onbellek.mkdir(parents=True, exist_ok=True)
    with cf.ProcessPoolExecutor(surec, initializer=_kur) as ex:
        for r in ex.map(_gorev, gorevler, chunksize=1):
            print(r, flush=True)


# ------------------------------------------------------------------------------------------------ 2) yeniden oynatma
def min_tutar(sembol: str) -> D:
    return D(str(MIN_TUTAR.get(sembol, MIN_TUTAR_DIGER)))


def maliyet_oranlari(sembol: str) -> tuple:
    from motor.arastirma import evren_maliyet
    taker, _, _, stop_bps = evren_maliyet.sembol_maliyeti(sembol, 1.0, TABLO)
    return D(str(stop_bps / 1e4)), D(str(taker / 100.0))


def boyut_yeni(kasa, giris, stop, yon, sembol, diger_brut, diger_risk):
    sk, tk = maliyet_oranlari(sembol)
    s = cl.miktar_hesapla(kasa=kasa, yon=yon, giris=giris, stop=stop, stop_kayma=sk, taker=tk, adim=D("1e-8"), min_tutar=min_tutar(sembol),
                          diger_brut=diger_brut, diger_stop_riski=diger_risk)
    return s.qty, s.neden, s.baglayan


def boyut_yuzde1(kasa, giris, stop, yon, sembol, diger_brut, diger_risk):
    """ESKİ kural (karşılaştırma): SERT_LIMITLER - işlem başı %1 maliyet dahil, toplam stop riski %5, brüt 3x (yürütücünün önceki formülü)."""
    sk, tk = maliyet_oranlari(sembol)
    if (yon == 1 and stop >= giris) or (yon == -1 and stop <= giris) or abs(giris - stop) / giris > D("0.25"):
        return D(0), "gecersiz", ""
    L = SERT_LIMITLER
    birim = abs(giris - stop) + cl.birim_maliyet(giris, stop, sk, tk)
    aday = {"kayip": D(str(L.islem_basi_max_risk_yuzde)) / 100 * kasa / birim,
            "toplam_risk": (D(str(L.portfoy_toplam_risk_yuzde)) / 100 * kasa - diger_risk) / abs(giris - stop),
            "brut": (D(str(L.max_kaldirac)) * kasa - diger_brut) / giris}
    b = min(aday, key=lambda k: aday[k])
    q = aday[b]
    if q <= 0:
        return D(0), "butce_dolu", b
    q = cl.asagi(q, D("1e-8"))
    if q * giris < min_tutar(sembol):
        return D(0), "min_tutar_alti", b
    return q, None, b


def oyna(tr: pd.DataFrame, mtm: pd.DataFrame, mod: str, baslangic=None, bitis=None) -> dict:
    """Gün gün yeniden oynatma (tek strateji hesabı). mod: 'canli' (CANLI_LIMITLER) | 'yuzde1' (SERT_LIMITLER eski boyut, karşılaştırma).

    Tanımlar / yaklaşıklıklar (rapora da yazılır):
      - her işlemin K/Z'si = r x qty x |giriş-stop| (r: backtest R'si, funding ve maliyet dahil; maliyet notional ile orantılı ölçeklenir)
      - kasa = min(özsermaye, 165): kâr kasayı büyütmez, kayıp küçültür (yürütücüyle aynı); özsermaye = gerçekleşmiş + açıkların gün sonu MTM'si
      - günlük blok: gün içinde (gün başı MTM özsermayesine göre) -%6 ya da altına inilmişse (gerçekleşen K/Z + açıkların önceki gün sonu MTM'si)
        o gün YENİ GİRİŞ yok (canlı yürütücü de açık pozisyonları KAPATMAZ: aynı davranış)
      - kill: GÜN SONU kasası zirve kasadan -%30 olursa o gün sonu MTM'siyle hepsi kapanır, sonrası işlem yok (gün içi tetik yakalanamaz)
      - açık pozisyonların stop riski girişteki stopla ölçülür (stop yükseltme riski azaltır; tutucu), diğer pozisyonların nominali giriş fiyatıyla
      - adım (stepSize) yuvarlaması modellenmedi; min tutar tablosu MIN_TUTAR (tutucu varsayım)
    """
    if mod == "canli":
        gunluk_oran, kill_oran, boyutla = cl.CANLI_LIMITLER.gunluk_max_kayip_oran, cl.CANLI_LIMITLER.strateji_kill_oran, boyut_yeni
    else:
        gunluk_oran, kill_oran, boyutla = SERT_LIMITLER.gunluk_max_kayip_yuzde / 100, SERT_LIMITLER.kill_switch_dusus_yuzde / 100, boyut_yuzde1
    tr = tr.sort_values(["giris_zamani", "sembol"], kind="stable").reset_index(drop=True)
    mtmd = {k: g.set_index("gun")["kum_r"].astype(float).to_dict() for k, g in mtm.groupby(["sembol", "islem_no"])}
    g0 = (baslangic if baslangic is not None else tr["giris_zamani"].min()).floor("D")
    g1 = (bitis if bitis is not None else tr["cikis_zamani"].max()).floor("D")
    giris_gun = {g: x for g, x in tr.groupby(tr["giris_zamani"].dt.floor("D"))}
    gerc, acik = KASA_USD, []
    sayac = dict(islem=0, min_tutar=0, gunluk_blok=0, kill_sonrasi=0, diger_red=0, nominal_bagli=0, risk_bagli=0, mtm_eksik=0)
    red = {}
    zirve, kill_gun, onceki_ozs = KASA_USD, None, KASA_USD
    egri, kapanan = {}, []

    def mtm_toplam(gun):
        return sum(p["qty"] * p["sd"] * p["mt"].get(gun, p["son"]) for p in acik)

    def kapat(t):
        nonlocal gerc
        for p in [p for p in acik if p["cikis"] <= t]:
            acik.remove(p)
            gerc += p["pnl"]
            kapanan.append((p["cikis"], p["pnl"]))
    for gun in pd.date_range(g0, g1, freq="D"):
        onceki_gun = gun - pd.Timedelta(days=1)
        for p in acik:                                              # önceki gün sonu MTM değerini 'son' olarak tut (gün içi tahmini)
            p["son"] = p["mt"].get(onceki_gun, p["son"])
        gun_basi = onceki_ozs
        if kill_gun is None and gun in giris_gun:
            for _, x in giris_gun[gun].iterrows():
                t = x["giris_zamani"]
                kapat(t)
                simdi = gerc + mtm_toplam(onceki_gun)
                if gun_basi > 0 and (gun_basi - simdi) / gun_basi >= gunluk_oran - 1e-12:
                    sayac["gunluk_blok"] += 1
                    continue
                kasa = min(simdi, KASA_USD)
                if kasa <= 0:
                    sayac["diger_red"] += 1
                    continue
                giris, sd, yon = D(repr(float(x["giris_fiyati"]))), D(repr(float(x["stop_mesafe"]))), int(x["yon"])
                diger_brut = sum((D(repr(p["qty"])) * D(repr(p["giris"])) for p in acik), D(0))
                diger_risk = sum((D(repr(p["qty"])) * D(repr(p["sd"])) for p in acik), D(0))
                qty, neden, bagl = boyutla(D(repr(kasa)), giris, giris - yon * sd, yon, x["sembol"], diger_brut, diger_risk)
                if neden == "min_tutar_alti":
                    sayac["min_tutar"] += 1
                    continue
                if neden is not None or qty <= 0:
                    sayac["diger_red"] += 1
                    red[neden] = red.get(neden, 0) + 1
                    continue
                q = float(qty)
                sayac["islem"] += 1
                sayac["nominal_bagli" if bagl in ("nominal", "marj", "brut") else "risk_bagli"] += 1
                m = mtmd.get((x["sembol"], int(x["islem_no"])), {})
                if not m and x["cikis_zamani"].floor("D") > gun:
                    sayac["mtm_eksik"] += 1
                acik.append(dict(cikis=x["cikis_zamani"], qty=q, sd=float(sd), giris=float(giris), pnl=float(x["r"]) * q * float(sd), mt=m, son=0.0))
        elif kill_gun is not None:
            sayac["kill_sonrasi"] += int(len(giris_gun.get(gun, ())))
        kapat(gun + pd.Timedelta(days=1) - pd.Timedelta(1, "ns"))            # gün içinde biten her işlem gün sonuna kadar gerçekleşir
        ozs = gerc + mtm_toplam(gun)
        if kill_gun is None:
            kasa = min(ozs, KASA_USD)
            zirve = max(zirve, kasa)
            if kasa <= (1 - kill_oran) * zirve + 1e-12:
                kill_gun = gun
                gerc, acik = ozs, []                                          # gün sonu MTM'siyle hepsi kapanır
        egri[gun] = gerc + mtm_toplam(gun)
        onceki_ozs = egri[gun]
    e = pd.Series(egri)
    gunluk = e.pct_change().fillna(e.iloc[0] / KASA_USD - 1)
    yil = max((g1 - g0).days / 365.25, 1 / 365.25)
    sonuc = e.iloc[-1]
    dd = float(((e.cummax() - e) / e.cummax()).max()) if len(e) else 0.0
    seri = en = 0
    for _, pnl in sorted(kapanan):
        seri = seri + 1 if pnl < 0 else 0
        en = max(en, seri)
    cagr = (sonuc / KASA_USD) ** (1 / yil) - 1 if sonuc > 0 else -1.0
    return dict(sayac, kill_tarihi=str(kill_gun.date()) if kill_gun is not None else "", son_ozsermaye=float(sonuc), cagr=float(cagr), maks_dusus=dd,
                en_kotu_gun=float(gunluk.min()), en_uzun_kayip_serisi=int(en), yil=yil, e=e, red=red)


ALANLAR = ["strateji", "boyut", "islem", "min_tutar_atlanan", "gunluk_blok_atlanan", "diger_red", "kill_sonrasi_atlanan", "son_ozsermaye_usd", "cagr",
           "maks_dusus", "en_kotu_gun", "en_uzun_kayip_serisi", "kill_30_tetiklendi", "kill_tarihi", "nominal_tavan_bagli_yuzde", "risk_tavan_bagli_yuzde",
           "ilk_islem", "son_islem", "not"]


def tum(onbellek: Path) -> pd.DataFrame:
    s = json.loads(SET_YOLU.read_text(encoding="utf-8"))
    satirlar = []
    for k in s["stratejiler"]:
        ad = k["strateji"]
        if k["tur"] != "tek":
            satirlar.append({"strateji": ad, "boyut": "-", "not": "UYGULANAMAZ: portföy (hedef-ağırlık) stratejisi; işlem başına stop yok, canlıda desteklenmiyor (onkontrol reddeder)"})
            continue
        dosyalar = sorted(onbellek.glob(f"{ad}--*--islem.parquet"))
        if not dosyalar:
            satirlar.append({"strateji": ad, "boyut": "-", "not": "işlem yok / veri yok"})
            continue
        tr = pd.concat([pd.read_parquet(f) for f in dosyalar], ignore_index=True)
        mt = pd.concat([pd.read_parquet(f) for f in sorted(onbellek.glob(f"{ad}--*--mtm.parquet"))], ignore_index=True)
        for mod, etiket in (("canli", "CANLI_LIMITLER"), ("yuzde1", "yuzde1_eski_SERT")):
            r = oyna(tr, mt, mod)
            n = max(r["islem"], 1)
            satirlar.append({"strateji": ad, "boyut": etiket, "islem": r["islem"], "min_tutar_atlanan": r["min_tutar"], "gunluk_blok_atlanan": r["gunluk_blok"],
                             "diger_red": r["diger_red"], "kill_sonrasi_atlanan": r["kill_sonrasi"], "son_ozsermaye_usd": round(r["son_ozsermaye"], 2),
                             "cagr": round(r["cagr"], 4), "maks_dusus": round(r["maks_dusus"], 4), "en_kotu_gun": round(r["en_kotu_gun"], 4),
                             "en_uzun_kayip_serisi": r["en_uzun_kayip_serisi"], "kill_30_tetiklendi": "evet" if r["kill_tarihi"] else "hayir",
                             "kill_tarihi": r["kill_tarihi"], "nominal_tavan_bagli_yuzde": round(100 * r["nominal_bagli"] / n, 1),
                             "risk_tavan_bagli_yuzde": round(100 * r["risk_bagli"] / n, 1), "ilk_islem": str(tr["giris_zamani"].min().date()),
                             "son_islem": str(tr["cikis_zamani"].max().date()),
                             "not": f"ham_islem={len(tr)}; mtm_eksik={r['mtm_eksik']}; red={r['red']}; kill eşiği: " + ("%30" if mod == "canli" else "%20") + "; günlük: " + ("-%6" if mod == "canli" else "-%3")})
    return pd.DataFrame(satirlar).reindex(columns=ALANLAR)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", required=True)
    ap.add_argument("--sadece-oyna", action="store_true")
    ap.add_argument("--surec", type=int, default=4)
    a = ap.parse_args(argv)
    ob = Path(a.onbellek)
    if not a.sadece_oyna:
        topla(ob, a.surec)
    df = tum(ob)
    CIKTI.mkdir(parents=True, exist_ok=True)
    df.to_csv(CIKTI / "boyut_yeniden_oynatma.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
