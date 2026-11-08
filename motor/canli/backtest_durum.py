"""Backtest besleyici (Aşama 3, "önce backtest sonuçlarıyla çalışır"): final seti kilitli dönem için MEVCUT yeniden oynatma
motoruyla koşar ve sonucu durum dosyalarına yazar (DURUM_SOZLESMESI.md). Yeni hesap yöntemi yoktur:
  - tek_grafik kolu: secim.yeniden_oyna (kilit_testi.set_testi ile AYNI çağrı ve sıra); portföy kolu: 3 stratejinin eşit
    ağırlıklı günlük ortalaması; set: secim.harmanla 50/50 -> sayılar sonuclar/kilit/set.csv ile BİREBİR aynıdır.
  - Katkılar toplamsaldır (set özsermayesindeki artışa tam bölünür): tek-grafik stratejisi için S[t-1] x kol_payı x pnl/E_kol[t-1],
    portföy stratejisi için S[t-1] x kol_payı x g/n_t (n_t: o gün verisi olan portföy stratejisi sayısı; S: set özsermayesi, E_kol: tek-grafik kolu hesabı).
  - Beklenti konumu (4 ve 8 hafta): dönemin SON 28/56 günü, sonuclar/final/beklenti_araliklari.csv ile aynı tabanda
    (strateji: kendi hesabında işlem başı %1 / portföy günlüğü; set: harman serisi). Hesap burada (motor), pano yalnız gösterir.
Ölçülmeyenler (kaldıraç, açık stop riski: yeniden oynatma günlük MTM tutmaz) None yazılır; açık pozisyon yoktur
(backtest işlemleri veri sonunda kapalıdır).

CLI: python -m motor.canli.backtest_durum [--cikti durum] [--baslangic 10000]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import beklenti as bek
from motor.arastirma import final_set
from motor.arastirma import secim as sec
from motor.canli import aylik_rapor as ar
from motor.canli import dersler as ders
from motor.canli import durum as d
from motor.canli import durum_ek as ek
from motor.canli import giris_izi as gi
from motor.canli import guven as gv
from motor.canli import karne as kr_
from motor.canli import koc as kc
from motor.canli import koni as kn
from motor.canli import kiyas as ky
from motor.canli import korelasyon as kr
from motor.canli import yogunlasma as yg
from motor.risk.limitler import SERT_LIMITLER

KOK = Path(__file__).resolve().parents[2]
KILIT = pd.Timestamp("2025-11-01", tz="UTC")
BEKLENTI_CSV = KOK / "sonuclar" / "final" / "beklenti_araliklari.csv"
BASLANGIC = Decimal("10000")
GUN = pd.Timedelta(days=1)


def _kid(kimlik: str) -> str:
    return kimlik.replace("|", "--")


def _yon(v) -> str:
    return "long" if int(v) == 1 else "short"


def _utc_index(s: pd.Series) -> pd.Series:
    s = s.copy()
    ix = pd.DatetimeIndex(s.index)
    s.index = ix.tz_convert("UTC") if ix.tz is not None else ix.tz_localize("UTC")
    return s


def set_serileri(kok: Path = KOK) -> dict:
    """kilit_testi.set_testi ile aynı çağrılar (aynı sıra: sonuc.csv'deki A satırları). -> ham sonuçlar."""
    sonuc = pd.read_csv(kok / "sonuclar" / "kilit" / "sonuc.csv")
    A = sonuc[sonuc["A"].astype(bool)]
    tek, port = A[A["tur"] == "tek"], A[A["tur"] == "portfoy"]
    parcalar, atlanan = {}, []
    for r in tek.itertuples():
        yol = kok / "sonuclar" / "kilit" / "islemler" / f"{_kid(r.kimlik)}.parquet"
        if yol.exists():
            parcalar[r.kimlik] = (pd.read_parquet(yol), r.sembol)
        else:
            atlanan.append(r.kimlik)
    if not parcalar:
        raise RuntimeError("kilit işlem dosyaları yok (sonuclar/kilit/islemler)")
    bit = max(pd.Timestamp(v) for v in tek["veri_son"].dropna())
    tablo = sec.islem_tablosu_hazirla(parcalar)
    oy = sec.yeniden_oyna(tablo, sec.OynatmaAyari(), bas=KILIT, bit=bit)
    gunluk = {}
    for r in port.itertuples():
        yol = kok / "sonuclar" / "kilit" / "gunluk" / f"{_kid(r.kimlik)}.parquet"
        if not yol.exists():
            raise RuntimeError(f"portföy günlük dosyası yok: {yol.name}")
        gunluk[r.kimlik] = pd.read_parquet(yol)["oos_getiri"].astype(float).rename(r.kimlik)
    g = pd.concat(list(gunluk.values()), axis=1)
    g = g.loc[g.dropna().index.min():g.dropna().index.max()] if g.dropna().shape[0] else g
    port_getiri = g.mean(axis=1)
    h = sec.harmanla(_utc_index(oy["getiri"]), _utc_index(port_getiri), 0.5)
    return {"sonuc": sonuc, "parcalar": parcalar, "tablo": tablo, "oy": oy, "gunluk": g, "port_getiri": port_getiri,
            "harman": h, "atlanan": atlanan, "bit": bit}


def _pencere_metrik(ret: np.ndarray) -> tuple:
    eg = np.cumprod(1.0 + ret)
    zirve = np.maximum.accumulate(np.r_[1.0, eg])[1:]
    return float(eg[-1] - 1.0), float(((zirve - eg) / zirve).max())


def beklenti_konumlari(seri: pd.Series, satirlar: dict) -> dict:
    """seri: günlük getiri (ardışık günler). -> {'4': {net_getiri, max_dusus}, '8': {...}}; seri pencereden kısaysa o pencere yok."""
    out = {}
    for hafta in bek.PENCERE_HAFTA:
        w = hafta * 7
        if len(seri) < w:
            continue
        net, dd = _pencere_metrik(seri.to_numpy(dtype=float)[-w:])
        out[str(hafta)] = {"net_getiri": d.konum("net_getiri", net, satirlar[(hafta, "net_getiri")], hafta),
                           "max_dusus": d.konum("max_dusus", dd, satirlar[(hafta, "max_dusus")], hafta)}
    return out


SERI_GUN = 60
MFE_YOK = {"mfe_fiyat": None, "mae_fiyat": None, "mfe_r": None, "mae_r": None,
           "mfe_mae_neden": "backtest yeniden oynatması işlem boyunca en iyi/en kötü fiyatı tutmaz; paper motoru yazar"}
OLCULMEDI = "backtest yeniden oynatması günlük pozisyon/maliyet kaydı tutmaz; paper motoru yazar"


def _genisletme(gunler, ozs, bas: Decimal, zaman: str) -> tuple:
    """-> (ozet ek alanları, ek dosyalar, tam günlük K/Z listesi). Günler yeniden oynatmanın UTC ızgarasıdır (gun_kesimi alanı söyler)."""
    """Pano genişletme alanları (backtestte ölçülebilenler dolu, ölçülemeyenler null + neden)."""
    kz, dus, onceki, zirve = [], [], bas, bas
    for t, e in zip(gunler, ozs):
        kz.append({"gun": str(t.date()), "pnl": d.para(e - onceki), "getiri": d.sayi((e - onceki) / onceki)})
        zirve = max(zirve, e)
        dus.append({"gun": str(t.date()), "dusus": d.sayi((zirve - e) / zirve)})
        onceki = e
    hafta = d.para(ozs[-1] - ozs[-8]) if len(ozs) >= 8 else None
    ekstra_ozet = {"hafta_pnl": hafta, "hafta_pnl_neden": None if hafta is not None else "7 günlük geçmiş dolmadı",
                   "gunluk_kz": kz[-SERI_GUN:], "dusus_serisi": dus[-SERI_GUN:], "gun_kesimi": ek.GUN_KESIMI_UTC_IZGARA}
    bos = lambda ad, **kw: {**d._zarf(ad, "backtest", zaman), "olculmedi_neden": OLCULMEDI, **kw}      # noqa: E731
    dosyalar = {
        "maruziyet": bos("maruziyet", semboller=None, toplam_brut_nominal=None, toplam_net_nominal=None, kaldirac=None,
                         kullanilan_teminat=None, acik_stop_riski=None, pozisyonlar=[], bekleyen_emirler=None),
        "maliyet": bos("maliyet", toplam=None, stratejiler=None),
        "reddedilen": bos("reddedilen", son24s=None, tum=None, son=[]),
        "olaylar": [],
        "icgoruler": {**d._zarf("icgoruler", "backtest", zaman), "cumleler": [
            f"Backtest dönemi son 7 gün K/Z: {hafta if hafta is not None else '—'} USD.",
            "Maliyet, maruziyet ve reddedilen sinyal dökümü backtest kaynağında ölçülmez (null)."]}}
    return ekstra_ozet, dosyalar, kz


def olustur(kok: Path = KOK, baslangic=BASLANGIC, yazim_zamani=None, beklenti_csv: Path = BEKLENTI_CSV) -> dict:
    """Durum dosyalarının içeriği (diske yazmaz). -> {'ozet','stratejiler','islemler','saglik','gecmis', 'seriler'}."""
    set_ = final_set.yukle(kok / "stratejiler" / "final_set.json")
    S = set_serileri(kok)
    sonuc, oy, tablo, h = S["sonuc"], S["oy"], S["tablo"], S["harman"]
    ids = {x["kimlik"] for x in set_["stratejiler"]}
    A = set(sonuc[sonuc["A"].astype(bool)]["kimlik"])
    if ids != A or S["atlanan"]:
        raise RuntimeError(f"final_set.json ile sonuc.csv A grubu uyuşmuyor ya da işlem dosyası eksik: {sorted(ids ^ A)} {S['atlanan']}")
    bekle = d.beklenti_oku(beklenti_csv)
    bas = Decimal(baslangic)
    pay = set_["risk"]["kol_paylari"]
    getiri = h["getiri"].astype(float)
    gunler = getiri.index
    # --- özsermaye serisi (set): S[t] = bas x Π(1+h)
    carpan = np.cumprod(1.0 + getiri.to_numpy())
    S_once = np.r_[1.0, carpan[:-1]]                                   # S[t-1] (başlangıç 1.0)
    ozs = [bas * Decimal(repr(float(c))) for c in carpan]
    yazim = yazim_zamani or datetime.now(timezone.utc)
    # --- katkı: tek-grafik (kabul edilen işlemler; pnl, yeniden oynatma motorundan)
    ozs_kol = oy["gunluk"]                                             # E_kol[t] (gece yarısı, gerçekleşmiş)
    sicil = {x["kimlik"]: {"katki": 0.0, "satirlar": []} for x in set_["stratejiler"]}
    # sürüm izi: kilit testindeki ayar (paper ile aynı hash fonksiyonu); giriş gerekçesi backtest yeniden oynatmasında tutulmaz -> null
    ayar_of = {x["kimlik"]: gi.ayar_surumu(x["strateji"], x["kilit_testi_ayari"], "final_set.json (kilit_testi_ayari)") for x in set_["stratejiler"]}
    gun_katki = {x["kimlik"]: np.zeros(len(gunler)) for x in set_["stratejiler"]}       # set başlangıcına oran, gün gün
    ofset, bitis_kol = {}, 0
    for k, (df, _) in S["parcalar"].items():
        ofset[k] = (bitis_kol, df.sort_values("giris_zamani", kind="stable").reset_index(drop=True))
        bitis_kol += len(df)
    son_etiket = ozs_kol.index[-1]
    gun_ix = {t: i for i, t in enumerate(gunler)}
    for i, (t_ns, pnl) in sorted(oy["islem_pnl"].items(), key=lambda kv: kv[1][0]):
        etiket = pd.Timestamp(t_ns, tz="UTC").floor("D") + GUN            # getiri etiketi = gerçekleşmeyi izleyen gece yarısı
        if etiket > son_etiket or etiket not in gun_ix:
            continue
        kol = tablo.iloc[i]["kol"]
        e_once = float(ozs_kol.loc[etiket - GUN])
        katki_set = S_once[gun_ix[etiket]] * pay["tek_grafik"] * pnl / e_once        # set başlangıç özsermayesine oran
        sicil[kol]["katki"] += katki_set
        gun_katki[kol][gun_ix[etiket]] += katki_set
        o0, df_k = ofset[kol]
        tr = df_k.iloc[i - o0]
        sicil[kol]["satirlar"].append({
            "zaman": d.zaman_str(pd.Timestamp(tr["cikis_zamani"])), "kimlik": kol, "sembol": tablo.iloc[i]["sembol"],
            "yon": _yon(tr["yon"]), "giris_zamani": d.zaman_str(pd.Timestamp(tr["giris_zamani"])),
            "giris_fiyati": repr(float(tr["giris_fiyati"])), "cikis_zamani": d.zaman_str(pd.Timestamp(tr["cikis_zamani"])),
            "cikis_fiyati": repr(float(tr["cikis_fiyati"])), "miktar": repr(float(tr["miktar"])), "r": d.sayi(tr["r"]),
            "net_pnl_yerel": d.para(tr["net_pnl"]), "set_katki_usd": d.para(bas * Decimal(repr(float(katki_set)))),
            "cikis_nedeni": str(tr.get("cikis_nedeni", "")), "ayar_surumu": ayar_of[kol], "giris_gerekcesi": None, **MFE_YOK})
    # --- katkı: portföy stratejileri (günlük getiri / 3 x kol payı x S[t-1]); işlemler kendi hesaplarında
    # kol getirisi = DataFrame.mean(axis=1) (set_testi ile aynı): o gün verisi olan stratejiler arasında eşit pay (hafta sonu
    # DK_ verisi olmayan strateji satırda yoktur -> payda ona göre küçülür); katkı aynı payla dağıtılır ki toplam birebir tutsun
    adet = S["gunluk"].notna().sum(axis=1).reindex(gunler).to_numpy(dtype=float)
    for x in set_["stratejiler"]:
        if x["kol"] != "portfoy":
            continue
        gj = _utc_index(S["gunluk"][x["kimlik"]]).reindex(gunler).fillna(0.0).to_numpy()
        gun_katki[x["kimlik"]] = S_once * pay["portfoy"] * gj / adet
        sicil[x["kimlik"]]["katki"] = float(gun_katki[x["kimlik"]].sum())
        tr_df = pd.read_parquet(kok / "sonuclar" / "kilit" / "islemler" / f"{_kid(x['kimlik'])}.parquet")
        for _, tr in tr_df.iterrows():
            if pd.Timestamp(tr["cikis_zamani"]).floor("D") > gunler[-1]:
                continue
            sicil[x["kimlik"]]["satirlar"].append({
                "zaman": d.zaman_str(pd.Timestamp(tr["cikis_zamani"])), "kimlik": x["kimlik"], "sembol": tr["sembol"],
                "yon": _yon(tr["yon"]), "giris_zamani": d.zaman_str(pd.Timestamp(tr["giris_zamani"])),
                "giris_fiyati": repr(float(tr["giris_fiyati"])), "cikis_zamani": d.zaman_str(pd.Timestamp(tr["cikis_zamani"])),
                "cikis_fiyati": repr(float(tr["cikis_fiyati"])), "miktar": repr(float(tr["miktar"])), "r": d.sayi(tr["r"]),
                "net_pnl_yerel": d.para(tr["net_pnl"]), "set_katki_usd": None, "cikis_nedeni": str(tr.get("cikis_nedeni", "")),
                "ayar_surumu": ayar_of[x["kimlik"]], "giris_gerekcesi": None, **MFE_YOK})
    # --- strateji kayıtları + beklenti konumu (stratejinin kendi serisi, dönemin son günleri)
    kilit_gunleri = pd.date_range(KILIT, gunler[-1], freq="D", tz="UTC").as_unit(gunler.unit)
    stratejiler, tum_islemler = [], []
    for x in set_["stratejiler"]:
        k = x["kimlik"]
        satirlar = sorted(sicil[k]["satirlar"], key=lambda s: s["zaman"])
        tum_islemler += satirlar
        if x["kol"] == "tek_grafik":
            isl = S["parcalar"][k][0]
            seri = bek.gunluk_tablo_islem(isl, kilit_gunleri)["ret"]
        else:
            seri = _utc_index(S["gunluk"][k]).reindex(kilit_gunleri).fillna(0.0)
        kazanan = sum(1 for s in satirlar if s["r"] is not None and s["r"] > 0)
        stratejiler.append({
            "kimlik": k, "ajan": x["ajan"], "kol": x["kol"], "kol_payi": x["kol_payi"],
            "ozsermaye_katkisi": d.para(bas * Decimal(repr(float(sicil[k]["katki"])))), "katki_getiri": d.sayi(sicil[k]["katki"]),
            "acik_pozisyonlar": [], "son_islem": (satirlar[-1] if satirlar else None), "islem_sayisi": len(satirlar),
            "kazanma_orani": d.sayi(kazanan / len(satirlar)) if satirlar else None,
            "beklenti": beklenti_konumlari(seri, bekle[k])})
    tum_islemler.sort(key=lambda s: s["zaman"])
    for s_ in tum_islemler:                     # takvim günü (motor yazar): backtest ızgarası UTC günüdür (ozet.gun_kesimi ile aynı kesim)
        s_["gun"] = str(d.zaman_oku(s_["zaman"]).astimezone(timezone.utc).date())
    # --- özet
    ozet_ham = h["ozet"]                                                # sec.seri_ozeti: getiri, sharpe, max_dusus, gun
    zirve = max([bas] + ozs)
    gun_pnl = ozs[-1] - (ozs[-2] if len(ozs) > 1 else bas)
    zirveden = float((Decimal(d.para(zirve)) - Decimal(d.para(ozs[-1]))) / Decimal(d.para(zirve)))     # ozet.zirveden_dusus ile aynı (2 haneli tutarlardan)
    sayac = oy["sayac"]
    risk = d.risk_blogu(gunluk_kayip=max(0.0, -float(getiri.iloc[-1])), gunluk_limit=SERT_LIMITLER.gunluk_max_kayip_yuzde / 100,
                        kaldirac=None, kaldirac_limit=SERT_LIMITLER.max_kaldirac, zirveden_dusus=zirveden,
                        kill_limit=SERT_LIMITLER.kill_switch_dusus_yuzde / 100, acik_stop_riski=None,
                        stop_risk_limit=SERT_LIMITLER.portfoy_toplam_risk_yuzde / 100,
                        kaldirac_not="backtest: yeniden oynatma günlük kaldıraç/açık risk tutmaz; paper motoru yazar",
                        gunluk_limit_tetiklendi=sayac["gunluk_limit_olayi"] > 0)
    zaman = d.zaman_str(gunler[-1])
    ekstra_ozet, ekstra_dosyalar, kz_tam = _genisletme(gunler, ozs, bas, zaman)
    # --- motor yazıcı paketi (paper ile aynı fonksiyonlar; durum_ek.py). Portföy kolunda sembol dağılımı ölçülmez -> hücre katkısı null.
    ajan_of = {x["kimlik"]: x["ajan"] for x in set_["stratejiler"]}
    gun_s = [str(t.date()) for t in gunler]
    kum = {k: {g: bas * Decimal(repr(float(c))) for g, c in zip(gun_s, np.cumsum(v))} for k, v in gun_katki.items()}
    donem = ek.gunluk_kz_ajan(kum, ajan_of, gun_s, bas, dict(zip(gun_s, ozs)))
    hucre, katki_usd = {}, {s["kimlik"]: Decimal(s["ozsermaye_katkisi"]) for s in stratejiler}
    for x in set_["stratejiler"]:
        k = x["kimlik"]
        if x["kol"] == "tek_grafik":
            hucre[(k, S["parcalar"][k][1])] = katki_usd[k]
        else:
            for sm in {s["sembol"] for s in sicil[k]["satirlar"]}:
                hucre[(k, sm)] = None
    kirilim = ek.kirilimlar(stratejiler, tum_islemler, hucre, bas, [], "r")
    cn, cn_not = ek.cikis_nedenleri(tum_islemler)
    ekstra_ozet.update({"gunluk_kz_ajan": donem["gunluk"], "haftalik_kz_ajan": donem["haftalik"], "aylik_kz_ajan": donem["aylik"],
                        "istatistik": ek.istatistik(tum_islemler, kz_tam), "cikis_nedenleri": cn, "cikis_nedenleri_not": cn_not})
    ozet = d.ozet_olustur(
        kaynak="backtest", zaman=zaman, yazim_zamani=d.zaman_str(yazim), donem={"bas": d.zaman_str(gunler[0]), "bit": zaman},
        baslangic_ozsermaye=bas, ozsermaye=ozs[-1], gun_pnl=gun_pnl, gun_getiri=float(getiri.iloc[-1]), zirve_ozsermaye=zirve,
        max_dusus=ozet_ham["max_dusus"], risk=risk,
        sayaclar={"acik_pozisyon": 0, "kapanan_islem": len(tum_islemler), "reddedilen_giris": sayac["reddedilen"],
                  "kirpilan_giris": sayac["kirpilan"], "gunluk_limit_olayi": sayac["gunluk_limit_olayi"], "kill_olayi": sayac["kill_olayi"]},
        notlar=["BACKTEST: kilitli dönem (2025-11-01 sonrası) yeniden oynatması; canlı/paper verisi değildir.",
                "Set sayıları sonuclar/kilit/set.csv ile aynıdır (tek_grafik oynatma + portföy ortalaması, 50/50 günlük dengeli).",
                f"Sharpe (yıllık, günlük getiriden): {d.sayi(ozet_ham['sharpe']):.2f}; gün sayısı: {ozet_ham['gun']}."],
        ekstra=ekstra_ozet)
    set_bek = beklenti_konumlari(getiri, bekle["set"])
    stratejiler_json = {**d._zarf("stratejiler", "backtest", zaman), "yazim_zamani": d.zaman_str(yazim),
                        "beklenti_penceresi_hafta": list(bek.PENCERE_HAFTA), "stratejiler": stratejiler, "set": {"beklenti": set_bek}, **kirilim}
    saglik = {**d._zarf("saglik", "backtest", zaman), "son_calisma": d.zaman_str(yazim), "durum": "ok", "bayat_denetimi": False,
              "dosya_esik_dk": None,
              "veri": [{"sembol": x["sembol"], "tf": x["tf"], "son_mum_zamani": d.zaman_str(pd.Timestamp(
                  sonuc.set_index("kimlik").loc[x["kimlik"], "veri_son"]).tz_convert("UTC")),
                  "bayatlik_dk": d.veri_yasi_dk(pd.Timestamp(sonuc.set_index("kimlik").loc[x["kimlik"], "veri_son"]).tz_convert("UTC"),
                                                x["tf"], gunler[-1]),
                  "esik_dk": d.bayat_esigi_dk(x["tf"]), "bayat": False} for x in set_["stratejiler"]],
              "servis": {"calisiyor": None, "surum": "backtest_durum/1", "not": "backtest besleyici; canlı servis yok"},
              "uyarilar": ["Bayatlık denetimi backtest kaynağında kapalı (veri bilerek statik)."]}
    ds = ders.olustur("backtest", zaman, [x["kimlik"] for x in set_["stratejiler"]], tum_islemler, {s["kimlik"]: s["beklenti"] for s in stratejiler})
    ekstra_dosyalar["dersler"] = ds
    # --- koni / kıyas / korelasyon / yoğunlaşma. Koni havuzu backtest döneminin İÇİNDEKİ günleri dışlar (baz gün = dönemden önceki gün); gün kesimi UTC ızgarası.
    baz_gun = str((gunler[0] - GUN).date())
    gercek = [{"gun": str(t.date()), "getiri": float(e / bas - 1)} for t, e in zip(gunler, ozs)]
    ekstra_dosyalar["koni"] = kn.olustur("backtest", zaman, baz_gun, gercek)
    ekstra_dosyalar["kiyas"] = ky.olustur("backtest", zaman, gunler[-1] + GUN, baz_gun, [x["gun"] for x in gercek], {x["gun"]: x["getiri"] for x in gercek},
                                          "UTC", ek.GUN_KESIMI_UTC_IZGARA)
    ekstra_dosyalar["korelasyon"] = kr.hesapla({k: pd.Series(v / S_once, index=gun_s) for k, v in gun_katki.items()}, "backtest", zaman, ek.GUN_KESIMI_UTC_IZGARA)
    ekstra_dosyalar["yogunlasma"] = yg.olustur("backtest", zaman, None, bas, OLCULMEDI)
    ekstra_dosyalar["veri_guveni"] = gv.veri_guveni(saglik["veri"], None, gunler[-1], "backtest", zaman)
    ekstra_dosyalar["butunluk"] = gv.butunluk("backtest", zaman, None, kok=kok, kayit_yolu=kok / "sonuclar" / "final" / "butunluk_kayit.json")
    ekstra_dosyalar["karne"] = kr_.olustur("backtest", zaman, [{"kimlik": s["kimlik"], "ajan": s["ajan"], "beklenti": s["beklenti"]} for s in stratejiler], set_bek, tum_islemler, ds,
                                           None, None, "backtest yeniden oynatması: çalışma sağlığı ölçülmez (bayatlık denetimi kapalı, servis yok)")
    ekstra_dosyalar["koc"] = kc.olustur("backtest", zaman, [s["kimlik"] for s in stratejiler], tum_islemler, ds, set_bek)
    ekstra_dosyalar["aylik_rapor"] = ar.olustur(
        kaynak="backtest", zaman=zaman, simdi=gunler[-1], donem_bas=gunler[0], aylik_kz_ajan=donem["aylik"], gunluk_tam=kz_tam, satirlar=tum_islemler,
        risk=risk, sayaclar=ozet["sayaclar"], set_konum=set_bek, strat_konum={s["kimlik"]: s["beklenti"] for s in stratejiler}, dersler=ds,
        saglik_durum=saglik["durum"], olaylar=None, limit_olaylari=None, kazanma_olcutu="r", gun_kesimi=ek.GUN_KESIMI_UTC_IZGARA)
    gecmis = {**d._zarf("gecmis", "backtest", zaman),
              "noktalar": [{"gun": str(t.date()), "ozsermaye": d.para(v)} for t, v in zip(gunler, ozs)]}
    return {"ozet": ozet, "stratejiler": stratejiler_json, "islemler": tum_islemler, "saglik": saglik, "gecmis": gecmis,
            "ekstra": ekstra_dosyalar,
            "seriler": {"set_getiri": getiri, "ozs": ozs, "katki_toplam": sum(sicil[k]["katki"] for k in sicil)}}


def yaz(cikti=None, **kw) -> Path:
    p = olustur(**kw)
    dizin = Path(cikti) if cikti else d.DURUM_DIZINI
    d.yaz_hepsi(dizin, ozet=p["ozet"], stratejiler=p["stratejiler"], islemler=p["islemler"], saglik=p["saglik"], gecmis=p["gecmis"],
                ekstra=p["ekstra"])
    return dizin


def main(argv=None):
    ap = argparse.ArgumentParser(description="Final seti kilitli dönem için yeniden oynatıp durum dosyalarını yazar")
    ap.add_argument("--cikti", default=None, help=f"varsayılan: {d.DURUM_DIZINI}")
    ap.add_argument("--baslangic", default=str(BASLANGIC), help="başlangıç özsermayesi (USD)")
    a = ap.parse_args(argv)
    dizin = yaz(a.cikti, baslangic=Decimal(a.baslangic))
    o = d.oku_ozet(dizin)
    print(f"[backtest_durum] {dizin}: özsermaye {o['ozsermaye']} (toplam {o['toplam_getiri'] * 100:+.2f}%), "
          f"max düşüş {o['max_dusus'] * 100:.2f}%, kapanan işlem {o['sayaclar']['kapanan_islem']}")


if __name__ == "__main__":
    main()
