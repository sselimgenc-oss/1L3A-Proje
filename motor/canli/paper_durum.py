"""Paper motoru -> durum/ dosyaları (DURUM_SOZLESMESI.md). Pano hesap yapmaz: TÜM sayılar burada hesaplanır.

Aynı sayı birden çok dosyada geçiyorsa (özsermaye, katkı, maliyet, işlem sayısı) tek kaynaktan (aynı değişken) yazılır;
`icgoruler` cümleleri de aynı değişkenlerden üretilir (sayılar diğer alanlarla birebir aynıdır).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import beklenti as bek
from motor.backtest.motor import D
from motor.canli import durum as d
from motor.canli import aylik_rapor as ar
from motor.canli import dersler as ders
from motor.canli import durum_ek as ek
from motor.canli import guven as gv
from motor.canli import paper_takvim as tk
from motor.canli.backtest_durum import beklenti_konumlari
from motor.risk.limitler import SERT_LIMITLER

KOK = Path(__file__).resolve().parents[2]
BEKLENTI_CSV = KOK / "sonuclar" / "final" / "beklenti_araliklari.csv"
SERI_GUN = 60
DOSYA_ESIK_DK = 15
OLAY_SON = 50
SURUM_ADI = "paper/1"


def _z(t) -> str:
    return d.zaman_str(pd.Timestamp(t))


def _gun_sirali(gun_kapanis: dict) -> list:
    return sorted(gun_kapanis.items())


def _yuzde(x, isaretli=True) -> str:
    return f"{x * 100:+.2f}%" if isaretli else f"{x * 100:.2f}%"


def _usd(x) -> str:
    return f"{Decimal(d.para(x)):+,.2f} USD"


# ---------------------------------------------------------------------------- strateji bazında hesaplar
def _acik_pnl(m, pos) -> Decimal:
    """Açık pozisyonun anlık net K/Z'si: mark fiyatla K/Z - giriş/çıkış komisyonu - funding + önceki kısmi çıkışların brüt toplamı."""
    return (D(m.son_kap[pos.sembol]) - pos.giris) * pos.miktar * pos.yon - pos.giris_kom - pos.cikis_kom - pos.funding + pos.brut_toplam


def strateji_pnl(p, sk: str) -> dict:
    """Stratejinin net K/Z'si: kapanan işlemler (net_pnl) + açık pozisyonların anlık K/Z'si (mark) - giriş komisyonu - funding."""
    m = p.motor
    kapanan = sum((D(x["net_pnl"]) for x in m.islemler if m_kol_sk(m, x["kol"]) == sk), Decimal(0))
    acik = sum((_acik_pnl(m, pos) for pos in m.acik.values() if pos.kol.sk == sk), Decimal(0))
    return {"kapanan": kapanan, "acik": acik, "toplam": kapanan + acik}


def katki_hucreleri(p) -> dict:
    """{(strateji kimliği, sembol): Decimal} net K/Z katkısı (kapanan + açık). Σ hücre = Σ strateji_pnl()["toplam"] (aynı formül)."""
    m = p.motor
    h: dict = {}
    for x in m.islemler:
        k = (m_kol_sk(m, x["kol"]), x["sembol"])
        h[k] = h.get(k, Decimal(0)) + D(x["net_pnl"])
    for pos in m.acik.values():
        k = (pos.kol.sk, pos.sembol)
        h[k] = h.get(k, Decimal(0)) + _acik_pnl(m, pos)
    return h


def m_kol_sk(m, kol_kimlik: str) -> str:
    return _SK_ONBELLEK.setdefault((id(m), kol_kimlik), next(k.sk for k in m.tum_kollar if k.kimlik == kol_kimlik))


_SK_ONBELLEK: dict = {}


def performans(islemler: list) -> dict:
    """islemler: motor işlem dict'leri. -> {islem, kazanma_orani, ort_kar, ort_zarar, net, pf}. Para: metin; zarar negatif."""
    n = len(islemler)
    if n == 0:
        return {"islem": 0, "kazanma_orani": None, "ort_kar": None, "ort_zarar": None, "net": d.para(0), "pf": None}
    net = [D(x["net_pnl"]) for x in islemler]
    kar = [x for x in net if x > 0]
    zr = [x for x in net if x < 0]
    pf = (float(sum(kar, Decimal(0)) / -sum(zr, Decimal(0))) if zr else (None if not kar else None))
    return {"islem": n, "kazanma_orani": d.sayi(len(kar) / n),
            "ort_kar": d.para(sum(kar, Decimal(0)) / len(kar)) if kar else None,
            "ort_zarar": d.para(sum(zr, Decimal(0)) / len(zr)) if zr else None,
            "net": d.para(sum(net, Decimal(0))), "pf": d.sayi(pf)}


def _islem_satiri(p, x: dict) -> dict:
    m = p.motor
    sk = m_kol_sk(m, x["kol"])
    return {"zaman": _z(x["cikis_zamani"]), "kimlik": sk, "sembol": x["sembol"], "yon": "long" if x["yon"] == 1 else "short",
            "giris_zamani": _z(x["giris_zamani"]), "giris_fiyati": repr(x["giris_fiyati"]),
            "cikis_zamani": _z(x["cikis_zamani"]), "cikis_fiyati": repr(x["cikis_fiyati"]), "miktar": repr(x["miktar"]),
            "r": d.sayi(x["r"]), "net_pnl_yerel": d.para(x["net_pnl"]), "set_katki_usd": d.para(x["net_pnl"]),
            "cikis_nedeni": x["cikis_nedeni"], "gun": ek.tsi_gun(x["cikis_zamani"]),
            # sürüm izi + giriş gerekçesi (giris_izi.py); bu özellikten önceki kayıtlarda null
            "ayar_surumu": x.get("ayar_surumu"), "giris_gerekcesi": x.get("giris_gerekcesi")}


def acik_pozisyonlar(p, sk: Optional[str] = None) -> list:
    out = []
    m = p.motor
    E = m.ozsermaye()
    for pos in m.acik.values():
        if sk is not None and pos.kol.sk != sk:
            continue
        mark = D(m.son_kap[pos.sembol])
        kz = (mark - pos.giris) * pos.miktar * pos.yon
        nom = mark * pos.miktar
        out.append({"kimlik": pos.kol.sk, "sembol": pos.sembol, "yon": "long" if pos.yon == 1 else "short",
                    "miktar": str(pos.miktar), "giris_fiyati": str(pos.giris), "mark_fiyat": str(mark),
                    "giris_zamani": _z(pos.zaman), "stop": str(pos.stop), "kz": d.para(kz),
                    "kz_oran": d.sayi(kz / (pos.giris * pos.miktar)) if pos.miktar else None,
                    "nominal": d.para(nom), "kasaya_orani": d.sayi(nom / E) if E > 0 else None,
                    "stop_riski": d.para(max((mark - pos.stop) * pos.miktar * pos.yon, Decimal(0)))})
    return out


# ---------------------------------------------------------------------------- günlük seriler
def gunluk_seriler(p, simdi) -> dict:
    """gun_kapanis_tsi -> noktalar, gunluk_kz, dusus_serisi (gün kesimi TSİ; kullanıcı kararı 2026-11-08). Başlangıç noktası (ilk günden
    bir önceki gün) = başlangıç sermayesi. `kapanislar_utc`/`ilk_gun` UTC günü serisidir: beklenti aralığı tabanı (backtestle aynı
    UTC ızgarası) ve risk limiti günü için korunur."""
    m = p.motor
    bas = D(p.ayarlar.baslangic_sermaye)
    gunler = _gun_sirali(m.gun_kapanis_tsi)
    utc = _gun_sirali(m.gun_kapanis)
    ilk_utc = pd.Timestamp(utc[0][0], tz="UTC") if utc else None
    kap_utc = {g: D(e) for g, e in utc}
    if not gunler:
        return {"noktalar": [], "gunluk_kz": [], "dusus_serisi": [], "max_dusus": 0.0, "ilk_gun": ilk_utc, "ilk_gun_tsi": None,
                "kapanislar": {}, "kapanislar_utc": kap_utc, "gunluk_tam": []}
    ilk = pd.Timestamp(gunler[0][0], tz="UTC")
    noktalar = [{"gun": str((ilk - pd.Timedelta(days=1)).date()), "ozsermaye": d.para(bas)}]
    kz, dus = [], []
    onceki, zirve, maxd = bas, bas, 0.0
    for g, e in gunler:
        e = D(e)
        noktalar.append({"gun": g, "ozsermaye": d.para(e)})
        kz.append({"gun": g, "pnl": d.para(e - onceki), "getiri": d.sayi((e - onceki) / onceki)})
        zirve = max(zirve, e)
        dd = float((zirve - e) / zirve)
        maxd = max(maxd, dd)
        dus.append({"gun": g, "dusus": d.sayi(dd)})
        onceki = e
    return {"noktalar": noktalar, "gunluk_kz": kz[-SERI_GUN:], "dusus_serisi": dus[-SERI_GUN:], "max_dusus": maxd,
            "ilk_gun": ilk_utc, "ilk_gun_tsi": ilk, "kapanislar": {g: D(e) for g, e in gunler}, "kapanislar_utc": kap_utc, "gunluk_tam": kz}


def _getiri_serisi(seri: dict, bas: Decimal) -> pd.Series:
    """{gun: özsermaye} -> günlük getiri (bitişik olmayan günler 0 sayılmaz; yalnız mevcut günler, takvim günlerine genişletilir)."""
    if not seri:
        return pd.Series(dtype=float)
    ix = pd.DatetimeIndex(sorted(pd.Timestamp(g, tz="UTC") for g in seri))
    degerler = [float(seri[str(x.date())]) for x in ix]
    s = pd.Series(degerler, index=ix)
    tam = pd.date_range(ix[0], ix[-1], freq="D")
    s = s.reindex(tam).ffill()
    onc = pd.concat([pd.Series([float(bas)]), s.iloc[:-1].reset_index(drop=True)]).reset_index(drop=True)
    return pd.Series((s.to_numpy() / onc.to_numpy()) - 1.0, index=s.index)


# ---------------------------------------------------------------------------- ana oluşturucu
def olustur(p, simdi, kaynak_saglik: Optional[list] = None, olaylar: Optional[list] = None, uyarilar: Optional[list] = None,
            servis: Optional[dict] = None, beklenti_csv: Path = BEKLENTI_CSV, kaynak: str = "paper",
            veri_yok_notlari: Optional[list] = None, veri_dizini: Optional[Path] = None) -> dict:
    """-> {'ozet','stratejiler','islemler','saglik','gecmis','ekstra'} (yaz_hepsi'ye verilir). simdi: UTC Timestamp.
    kaynak_saglik satırları isteğe bağlı `mum_indeksi` (DatetimeIndex) taşıyabilir: veri_guveni.json eksik mum ölçümü için (yoksa null + neden)."""
    simdi = pd.Timestamp(simdi)
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    m = p.motor
    L = SERT_LIMITLER
    bas = D(p.ayarlar.baslangic_sermaye)
    E = m.ozsermaye()
    S = gunluk_seriler(p, simdi)
    zirve = max(m.zirve, E)
    yeni_gun = m.gun is not None and simdi.date() > m.gun                     # UTC günü: yalnız risk limiti (motor.gun) için
    # günlük K/Z: TSİ günü (önceki TSİ gününün son özsermayesine göre)
    bugun = str(simdi.tz_convert(ek.TSI).date())
    onceki_gunler = [g for g in m.gun_kapanis_tsi if g < bugun]
    tsi_gun_basi = D(m.gun_kapanis_tsi[max(onceki_gunler)]) if onceki_gunler else bas
    gun_pnl = E - tsi_gun_basi
    gun_getiri = float(gun_pnl / tsi_gun_basi) if tsi_gun_basi > 0 else 0.0
    # hafta K/Z: 7 gün dolmadıysa null
    hafta_pnl, hafta_neden = None, None
    ilk = S["ilk_gun_tsi"]
    if ilk is None or (date.fromisoformat(bugun) - ilk.date()).days < 7:
        hafta_neden = "7 günlük geçmiş dolmadı"
    else:
        ref = str(date.fromisoformat(bugun) - timedelta(days=7))
        adaylar = [g for g in S["kapanislar"] if g <= ref]
        e0 = S["kapanislar"][max(adaylar)] if adaylar else bas
        hafta_pnl = E - e0
    dusus = float((zirve - E) / zirve) if zirve > 0 else 0.0
    max_dd = max(S["max_dusus"], dusus)
    kal = m.brut_kaldirac()
    stop_riski = m.acik_stop_riski()
    gunluk_kayip = 0.0 if yeni_gun else max(0.0, float(-(E - m.gun_basi) / m.gun_basi))
    risk = d.risk_blogu(gunluk_kayip=gunluk_kayip, gunluk_limit=L.gunluk_max_kayip_yuzde / 100,
                        kaldirac=kal, kaldirac_limit=L.max_kaldirac, zirveden_dusus=dusus,
                        kill_limit=L.kill_switch_dusus_yuzde / 100, acik_stop_riski=stop_riski,
                        stop_risk_limit=L.portfoy_toplam_risk_yuzde / 100,
                        kaldirac_not="brüt nominal / özsermaye (son bilinen fiyatlarla)",
                        gunluk_limit_tetiklendi=bool(m.gunluk_blok and not yeni_gun))
    risk["kill_switch"]["tetiklendi"] = bool(m.kill)
    giris_red = [x for x in m.reddedilenler]
    sayac = {"acik_pozisyon": len(m.acik), "kapanan_islem": len(m.islemler), "reddedilen_giris": len(giris_red),
             "kirpilan_giris": len(m.kirpmalar), "gunluk_limit_olayi": m.gunluk_limit_sayisi,
             "kill_olayi": sum(1 for o in m.limit_olaylari if o["tur"] == "kill_switch")}

    # --- stratejiler
    bek_csv = d.beklenti_oku(beklenti_csv)
    set_getiri = _getiri_serisi(S["kapanislar_utc"], bas)         # beklenti tabanı: UTC günü (backtestle aynı ızgara)
    uyari_listesi = list(uyarilar or [])
    strat_json, katkilar, perf_tum, alarmlar = [], {}, {}, []
    hafta_katki, strat_kon = {}, {}
    for t in p.tanimlar:
        sk = t.kimlik
        pn = strateji_pnl(p, sk)
        katkilar[sk] = pn["toplam"]
        isl = [x for x in m.islemler if m_kol_sk(m, x["kol"]) == sk]
        perf = performans(isl)
        perf_tum[sk] = perf
        satirlar = [_islem_satiri(p, x) for x in isl]
        if t.kol == "tek_grafik":
            df = pd.DataFrame({"cikis_zamani": [pd.Timestamp(x["cikis_zamani"]) for x in isl], "r": [x["r"] for x in isl]})
            gunler = pd.date_range(S["ilk_gun"], pd.Timestamp(simdi.date(), tz="UTC"), freq="D") if S["ilk_gun"] is not None else pd.DatetimeIndex([], tz="UTC")
            seri = bek.gunluk_tablo_islem(df, gunler)["ret"] if len(gunler) else pd.Series(dtype=float)
        else:
            seri = p_strateji_gunluk(p, sk)
        kon = beklenti_konumlari(seri, bek_csv[sk]) if len(seri) else {}
        strat_kon[sk] = kon
        for hf, b in kon.items():
            for metrik in ("net_getiri", "max_dusus"):
                if b[metrik]["alarm"]:
                    alarmlar.append((sk, hf, metrik, b[metrik]["deger"]))
        ap = acik_pozisyonlar(p, sk)
        kazanan = sum(1 for x in isl if D(x["net_pnl"]) > 0)
        strat_json.append({
            "kimlik": sk, "ajan": t.ajan, "kol": t.kol, "kol_payi": float(t.grup_payi) if t.kol == "tek_grafik" else float(t.grup_payi) * 3,
            "ozsermaye_katkisi": d.para(pn["toplam"]), "katki_getiri": d.sayi(pn["toplam"] / bas),
            "acik_pozisyonlar": ap, "son_islem": (satirlar[-1] if satirlar else None), "islem_sayisi": len(isl),
            "kazanma_orani": d.sayi(kazanan / len(isl)) if isl else None, "beklenti": kon, "performans": perf,
            "ayar": t.ayar, "sonraki_yenileme": t.sonraki_yenileme, "durum": "calisiyor"})
    for t in p.veri_yok:
        strat_json.append({"kimlik": t.kimlik, "ajan": t.ajan, "kol": t.kol, "kol_payi": float(t.grup_payi),
                           "ozsermaye_katkisi": d.para(0), "katki_getiri": 0.0, "acik_pozisyonlar": [], "son_islem": None,
                           "islem_sayisi": 0, "kazanma_orani": None, "beklenti": {},
                           "performans": performans([]), "ayar": t.ayar, "sonraki_yenileme": t.sonraki_yenileme,
                           "durum": f"veri yok: {t.veri_yok}"})
        uyari_listesi.append(f"VERİ YOK: {t.kimlik} çalıştırılmıyor ({t.veri_yok})")
    set_kon = beklenti_konumlari(set_getiri, bek_csv["set"]) if len(set_getiri) else {}
    for hf, b in set_kon.items():
        for metrik in ("net_getiri", "max_dusus"):
            if b[metrik]["alarm"]:
                alarmlar.append(("SET", hf, metrik, b[metrik]["deger"]))
    for sk, hf, metrik, v in alarmlar:
        uyari_listesi.append(f"BEKLENTİ ALARMI: {sk} {hf} hafta {metrik.replace('_', ' ')} {_yuzde(v)}")
    # yenileme uyarısı
    for t in p.tanimlar:
        if t.sonraki_yenileme and simdi.date() >= pd.Timestamp(t.sonraki_yenileme).date():
            uyari_listesi.append(f"AYAR YENİLEME ZAMANI: {t.kimlik} ({t.sonraki_yenileme}) — "
                                 f"`python -m motor.arastirma.guncel_ayar` sonucunu inceleyip kullanıcı onayıyla uygulayın (otomatik değil)")

    # --- olaylar
    olay_liste = list(olaylar or [])[-OLAY_SON:]

    # --- maliyet
    esik24 = simdi - pd.Timedelta(hours=24)

    def topla(filtre):
        r = {"ucret": Decimal(0), "kayma": Decimal(0), "funding": Decimal(0)}
        for x in m.maliyet_log:
            if filtre(x):
                r[x["tur"]] += x["tutar"]
        return r

    def blok(r):
        return {k: d.para(v) for k, v in r.items()} | {"toplam": d.para(sum(r.values(), Decimal(0)))}
    mal_tum, mal_24 = topla(lambda x: True), topla(lambda x: pd.Timestamp(x["zaman"]) >= esik24)
    maliyet = {**d._zarf("maliyet", kaynak, _z(simdi)),
               "toplam": {"son24s": blok(mal_24), "tum": blok(mal_tum)},
               "stratejiler": {t.kimlik: {"son24s": blok(topla(lambda x, k=t.kimlik: x["sk"] == k and pd.Timestamp(x["zaman"]) >= esik24)),
                                          "tum": blok(topla(lambda x, k=t.kimlik: x["sk"] == k))} for t in p.tanimlar},
               "not": "ücret = taker komisyonu; kayma = dolum fiyatı ile referans (açılış/stop seviyesi) farkı x miktar; "
                      "funding = ödenen (negatif: tahsil edilen). Hepsi pozitif sayı = maliyet."}

    # --- reddedilen / kırpılan
    def kayit(x, tur_):
        neden = x["neden"] if tur_ == "reddedildi" else x["tur"]
        sk = m_kol_sk(m, x["kol"]) if x["kol"] in {k.kimlik for k in m.tum_kollar} else x["kol"]
        return {"zaman": _z(x["zaman"]), "tur": tur_, "neden": neden, "kimlik": sk, "sembol": x["sembol"]}
    kayitlar = [kayit(x, "reddedildi") for x in m.reddedilenler] + [kayit(x, "kirpildi") for x in m.kirpmalar]
    kayitlar.sort(key=lambda r: r["zaman"])

    def sayi_neden(ls):
        return dict(Counter(f"{r['tur']}:{r['neden']}" for r in ls))
    son24 = [r for r in kayitlar if pd.Timestamp(r["zaman"]) >= esik24]
    reddedilen = {**d._zarf("reddedilen", kaynak, _z(simdi)), "son24s": sayi_neden(son24), "tum": sayi_neden(kayitlar),
                  "son": kayitlar[-20:], "not": "reddedildi = giriş yapılmadı; kirpildi = miktar küçültüldü (risk/kaldıraç/toplam stop riski)"}

    # --- maruziyet
    ap_hepsi = acik_pozisyonlar(p)
    sem = {}
    for a in ap_hepsi:
        s = sem.setdefault(a["sembol"], {"net": Decimal(0), "brut": Decimal(0)})
        nom = Decimal(a["nominal"])
        s["net"] += nom if a["yon"] == "long" else -nom
        s["brut"] += nom
    brut_toplam = sum((v["brut"] for v in sem.values()), Decimal(0))
    net_toplam = sum((v["net"] for v in sem.values()), Decimal(0))
    stop_risk_para = sum((Decimal(a["stop_riski"]) for a in ap_hepsi), Decimal(0))
    maruziyet = {**d._zarf("maruziyet", kaynak, _z(simdi)),
                 "semboller": [{"sembol": k, "net_nominal": d.para(v["net"]), "brut_nominal": d.para(v["brut"]),
                                "net_oran": d.sayi(v["net"] / E) if E > 0 else None, "brut_oran": d.sayi(v["brut"] / E) if E > 0 else None}
                               for k, v in sorted(sem.items())],
                 "toplam_brut_nominal": d.para(brut_toplam), "toplam_net_nominal": d.para(net_toplam),
                 "kaldirac": d.sayi(kal), "kullanilan_teminat": d.para(brut_toplam / D(L.max_kaldirac)),
                 "teminat_notu": f"brüt nominal / {L.max_kaldirac:g}x (sert kaldıraç tavanı); borsa teminatı değildir",
                 "acik_stop_riski": {"deger": d.para(stop_risk_para), "oran": d.sayi(stop_riski), "limit": L.portfoy_toplam_risk_yuzde / 100},
                 "pozisyonlar": ap_hepsi, "bekleyen_emirler": ek.bekleyen_emirler(m)}

    # --- iç görüler (sayılar yukarıdaki değişkenlerden)
    ic = icgoruler(p, simdi, E, bas, katkilar, perf_tum, ap_hepsi, mal_24, S, hafta_pnl, alarmlar, bek_csv, kon_tum=None)

    islemler = [_islem_satiri(p, x) for x in m.islemler]
    islemler.sort(key=lambda s: s["zaman"])
    # --- motor yazıcı paketi: istatistik, çıkış nedenleri, dönemsel getiri, stil/enstrüman kırılımları (pano yalnız biçimler)
    ajan_of = {t.kimlik: t.ajan for t in p.tanimlar}
    gun_tsi = sorted(m.gun_kapanis_tsi)
    donem = ek.gunluk_kz_ajan(p.strateji_gun_tsi, ajan_of, gun_tsi, bas, {g: D(e) for g, e in m.gun_kapanis_tsi.items()}) if gun_tsi else \
        {"gunluk": [], "haftalik": [], "aylik": []}
    cn, cn_not = ek.cikis_nedenleri(islemler)
    kirilim = ek.kirilimlar(strat_json, islemler, katki_hucreleri(p), bas, ap_hepsi, "net")
    ozet_ekstra = {"hafta_pnl": d.para(hafta_pnl) if hafta_pnl is not None else None, "hafta_pnl_neden": hafta_neden,
                   "gunluk_kz": S["gunluk_kz"], "dusus_serisi": S["dusus_serisi"], "gun_kesimi": ek.GUN_KESIMI_TSI,
                   "gunluk_kz_ajan": donem["gunluk"], "haftalik_kz_ajan": donem["haftalik"], "aylik_kz_ajan": donem["aylik"],
                   "istatistik": ek.istatistik(islemler, S["gunluk_tam"]), "cikis_nedenleri": cn, "cikis_nedenleri_not": cn_not}
    tsi_notu = ["Gün kesimi TSİ (00:00 Europe/Istanbul). Bu sürümden önceki günler UTC günü serisinden aktarıldı (en çok 3 saat kayma)."] \
        if m.tsi_aktarildi else []
    ozet = d.ozet_olustur(
        kaynak=kaynak, zaman=_z(simdi), yazim_zamani=_z(datetime.now(timezone.utc)),
        donem={"bas": _z(S["ilk_gun"]) if S["ilk_gun"] is not None else _z(simdi), "bit": _z(simdi)},
        baslangic_ozsermaye=bas, ozsermaye=E, gun_pnl=gun_pnl, gun_getiri=gun_getiri, zirve_ozsermaye=zirve, max_dusus=max_dd,
        risk=risk, sayaclar=sayac,
        notlar=list(veri_yok_notlari or []) + tsi_notu + [f"Paper: gerçek emir yok, canlı herkese açık Binance verisi. Başlangıç {d.para(bas)} USD."],
        ekstra=ozet_ekstra)
    strat = {**d._zarf("stratejiler", kaynak, _z(simdi)), "yazim_zamani": _z(datetime.now(timezone.utc)),
             "beklenti_penceresi_hafta": list(bek.PENCERE_HAFTA), "stratejiler": strat_json, "set": {"beklenti": set_kon}, **kirilim}
    gecmis = {**d._zarf("gecmis", kaynak, _z(simdi)), "noktalar": S["noktalar"]}
    saglik = saglik_olustur(p, simdi, kaynak_saglik or [], uyari_listesi, servis, kaynak)
    # --- Dersler (backtest beklentisiyle karşılaştırma) + aylık rapor / paper kabul listesi (motor hesaplar, pano biçimler)
    ds = ders.olustur(kaynak, _z(simdi), [t.kimlik for t in p.tanimlar], islemler, strat_kon)
    limit_ev = [{"tur": o["tur"], "zaman": o["zaman"]} for o in m.limit_olaylari]
    rapor = ar.olustur(kaynak=kaynak, zaman=_z(simdi), simdi=simdi, donem_bas=S["ilk_gun"], aylik_kz_ajan=donem["aylik"], gunluk_tam=S["gunluk_tam"],
                       satirlar=islemler, risk=risk, sayaclar=sayac, set_konum=set_kon, strat_konum=strat_kon, dersler=ds,
                       saglik_durum=saglik["durum"], olaylar=list(olaylar or []), limit_olaylari=limit_ev, kazanma_olcutu="net")
    # --- veri güveni (sembol başına son mum, bayatlık, eksik mum, kaynak) + backtest bütünlüğü (sha256 ↔ kayıt, kod sürümü)
    indeksler = {(x["sembol"], x["tf"]): x["mum_indeksi"] for x in (kaynak_saglik or []) if x.get("mum_indeksi") is not None}
    guven = gv.veri_guveni(saglik["veri"], indeksler or None, simdi, kaynak, _z(simdi), veri_dizini=veri_dizini or gv.VERI_DIZINI)
    butun = gv.butunluk(kaynak, _z(simdi), p.ayarlar)
    ekstra = {"dersler": ds, "aylik_rapor": rapor, "maruziyet": maruziyet, "maliyet": maliyet, "reddedilen": reddedilen, "olaylar": olay_liste,
              "icgoruler": {**d._zarf("icgoruler", kaynak, _z(simdi)), "cumleler": ic}, "veri_guveni": guven, "butunluk": butun}
    return {"ozet": ozet, "stratejiler": strat, "islemler": islemler, "saglik": saglik, "gecmis": gecmis, "ekstra": ekstra,
            "alarmlar": alarmlar}


def p_strateji_gunluk(p, sk: str) -> pd.Series:
    """Portföy stratejisinin kendi payı üzerinden günlük getirisi: Δ(katkı K/Z) / (önceki gün hesap özsermayesi x grup payı)."""
    snap = p.strateji_gun.get(sk, {})
    if not snap:
        return pd.Series(dtype=float)
    t = next(x for x in p.tanimlar if x.kimlik == sk)
    ix = pd.DatetimeIndex(sorted(pd.Timestamp(g, tz="UTC") for g in snap))
    tam = pd.date_range(ix[0], ix[-1], freq="D")
    kum = pd.Series([float(snap[str(x.date())]) for x in ix], index=ix).reindex(tam).ffill()
    E = p.motor.gun_kapanis
    out, onc_k, onc_e = [], 0.0, float(p.ayarlar.baslangic_sermaye)
    for g, k in kum.items():
        out.append((k - onc_k) / (onc_e * float(t.grup_payi)))
        onc_k = k
        if str(g.date()) in E:
            onc_e = float(E[str(g.date())])
    return pd.Series(out, index=tam)


def saglik_olustur(p, simdi, kaynak_saglik: list, uyarilar: list, servis: Optional[dict], kaynak: str = "paper") -> dict:
    """kaynak_saglik: [{sembol, tf, son_mum_acilis}] (veri kaynağından). Bayatlık seans takvimiyle."""
    veri = []
    bayat_var = False
    for x in kaynak_saglik:
        esik = d.bayat_esigi_dk(x["tf"])
        dk, bayat = tk.bayatlik(x["sembol"], x["tf"], x["son_mum_acilis"], simdi, esik)
        bayat_var |= bayat
        veri.append({"sembol": x["sembol"], "tf": x["tf"], "son_mum_zamani": _z(x["son_mum_acilis"]), "bayatlik_dk": dk,
                     "esik_dk": esik, "bayat": bool(bayat), "seans": tk.tur(x["sembol"])})
    durum = "ok"
    if p.motor.kill:
        durum = "kill_switch"
    elif bayat_var:
        durum = "veri_bayat"
    canli = kaynak != "backtest"
    return {**d._zarf("saglik", kaynak, _z(simdi)), "son_calisma": _z(datetime.now(timezone.utc)), "durum": durum,
            "bayat_denetimi": canli, "dosya_esik_dk": DOSYA_ESIK_DK if canli else None, "veri": veri,
            "servis": servis or ({"calisiyor": True, "surum": SURUM_ADI, "not": ""} if canli else
                                 {"calisiyor": None, "surum": SURUM_ADI, "not": "tekrar modu; canlı servis yok"}),
            "kalp_atisi": p.kalp_bilgisi() if canli else None,
            "uyarilar": list(uyarilar)}


def icgoruler(p, simdi, E, bas, katkilar, perf, ap_hepsi, mal24, S, hafta_pnl, alarmlar, bek_csv, kon_tum=None) -> list:
    """Kısa Türkçe cümleler. Sayılar durum dosyalarındakilerle aynı değişkenlerden (katkı, maliyet, açık K/Z)."""
    c = []
    if katkilar:
        sirali = sorted(katkilar.items(), key=lambda kv: kv[1])
        en_k, en_i = sirali[0], sirali[-1]
        etiket = "bu hafta" if hafta_pnl is not None else "başlangıçtan beri"
        if p.motor.islemler or any(v != 0 for v in katkilar.values()):
            c.append(f"En iyi strateji ({etiket}, katkı): {en_i[0]} {_usd(en_i[1])}.")
            if en_k[0] != en_i[0]:
                c.append(f"En kötü strateji ({etiket}, katkı): {en_k[0]} {_usd(en_k[1])}.")
    if ap_hepsi:
        karda = sum(1 for a in ap_hepsi if Decimal(a["kz"]) > 0)
        c.append(f"Açık {len(ap_hepsi)} pozisyonun {karda} tanesi kârda.")
    else:
        c.append("Açık pozisyon yok.")
    # beklenti alarmına en yakın strateji (8 hafta penceresi dolduysa)
    en_yakin = None
    for t in p.tanimlar:
        seri = (bek.gunluk_tablo_islem(pd.DataFrame({"cikis_zamani": [pd.Timestamp(x["cikis_zamani"]) for x in p.motor.islemler
                                                                     if m_kol_sk(p.motor, x["kol"]) == t.kimlik],
                                                     "r": [x["r"] for x in p.motor.islemler if m_kol_sk(p.motor, x["kol"]) == t.kimlik]}),
                                       pd.date_range(S["ilk_gun"], pd.Timestamp(simdi.date(), tz="UTC"), freq="D"))["ret"]
                if (t.kol == "tek_grafik" and S["ilk_gun"] is not None) else p_strateji_gunluk(p, t.kimlik))
        if len(seri) < 56:
            continue
        kon = beklenti_konumlari(seri, bek_csv[t.kimlik]).get("8")
        if not kon:
            continue
        nb = kon["net_getiri"]
        q = bek_csv[t.kimlik][(8, "net_getiri")]
        marj = (nb["deger"] - q["alarm_esigi"]) / max(q["p95"] - q["p05"], 1e-12) if q["alarm_esigi"] is not None else None
        if marj is not None and (en_yakin is None or marj < en_yakin[1]):
            en_yakin = (t.kimlik, marj, nb["deger"], q["alarm_esigi"])
    if en_yakin:
        c.append(f"Beklenti alarmına en yakın strateji: {en_yakin[0]} (8 hf net {_yuzde(en_yakin[2])}, alarm eşiği {_yuzde(en_yakin[3])}).")
    else:
        c.append("8 haftalık beklenti penceresi henüz dolmadı; alarm yok.")
    c.append(f"Son 24 saatte toplam maliyet {Decimal(d.para(sum(mal24.values(), Decimal(0)))):,.2f} USD "
             f"(ücret {d.para(mal24['ucret'])}, kayma {d.para(mal24['kayma'])}, funding {d.para(mal24['funding'])}).")
    if p.motor.kill:
        c.append("KILL SWITCH tetiklendi: tüm işlemler durdu.")
    elif p.motor.gunluk_blok and p.motor.gun == simdi.date():
        c.append("Günlük kayıp limiti tetiklendi: bugün yeni işlem yok.")
    return c


def yaz(p, dizin, simdi, **kw) -> Path:
    """durum/ dosyalarını atomik yazar."""
    o = olustur(p, simdi, **kw)
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"],
                gecmis=o["gecmis"], ekstra=o["ekstra"])
    return Path(dizin)
