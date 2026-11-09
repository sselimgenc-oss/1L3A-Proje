"""v2 Aşama 4 — sağlamlık (ON_KAYIT_V2 6.1; P1-4). YALNIZ keşiflere (test.csv `kesif`); dördü de şart.

  S1 gecikme   : sinyal 1 mum gecikmeli (`wf_evren.GecikmeliStrateji`), maliyet x1, tek kasa oynatması: PF(R) >= S1_PF_MIN
  S2 komşu ayar: `saglamlik.komsu_parametreler(varsayılan)` komşuları, geliştirme dönemi, aynı evren, x1, PF(R) = evren toplamı
                 (oynatma öncesi): medyan >= S2_MEDYAN_MIN VE en düşük >= S2_EN_DUSUK_MIN. Geçerli komşu < S2_MIN_KOMSU ise KALIR
  S3 komşu tf  : swing: diğer tf'de (1d<->4h) varsayılan ayar, PF(R) (oynatma öncesi) >= S3_PF_MIN; gunici_kripto/portfoy: yok
  S4 ayı rejimi: ayı günlerinde GİRİLEN (kabul edilen) işlemlerin ΣR >= -S4_KAYIP_ORANI x tüm dönem ΣR (rejim.py). Ayı günlerinde
                 kabul < S4_MIN_ISLEM ise "ölçülemedi = geçti" ve s4_az_ornek=evet. Portföy: R yerine günlük getiri toplamı.
Dördünü geçen = sağlam keşif; birini kaçıran = izleme listesi (sete girmez). S2/S3 analiz dönemi = satırın analiz başlangıcı -> veri sonu.
Çıktı: saglamlik.csv (+ saglamlik_ozet.json). Kalıcılık: saglamlik_satir/*.json (kapı kapı), saglamlik_kismi/*.json (S2 komşu
başına). Bütçe dolunca yeni kapı/komşu başlatılmaz; tamamlanmamışsa csv yazılmaz.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, saglamlik, wf_tarama
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import eleme, ham as hm, kasa, rejim, sabit
from motor.backtest.motor import backtest
from motor.strateji import funding


# ============================================================================ saf kapı kararları
def pf_r(r) -> float:
    r = np.asarray(r, dtype=float)
    return float(wf_tarama.pf_hesapla(r)) if len(r) else math.nan


def s1_karar(pf: float) -> bool:
    return bool(math.isfinite(pf) and pf >= sabit.S1_PF_MIN)


def s2_karar(pfler) -> dict:
    """Geçerli (sonlu) komşu PF'leri. < S2_MIN_KOMSU geçerli komşu = kalır."""
    a = np.array([x for x in pfler if x is not None and math.isfinite(x)], dtype=float)
    if len(a) < sabit.S2_MIN_KOMSU:
        return {"gecti": False, "n_gecerli": int(len(a)), "medyan": math.nan, "en_dusuk": math.nan}
    med, mn = float(np.median(a)), float(a.min())
    return {"gecti": bool(med >= sabit.S2_MEDYAN_MIN and mn >= sabit.S2_EN_DUSUK_MIN), "n_gecerli": int(len(a)), "medyan": med,
            "en_dusuk": mn}


def s3_karar(pf: float) -> bool:
    return bool(math.isfinite(pf) and pf >= sabit.S3_PF_MIN)


def s4_karar(r_ayi: float, r_toplam: float, n_ayi: int) -> dict:
    """n_ayi < S4_MIN_ISLEM: ölçülemedi = geçti (+ s4_az_ornek). Aksi halde r_ayi >= -S4_KAYIP_ORANI x r_toplam."""
    if n_ayi < sabit.S4_MIN_ISLEM:
        return {"gecti": True, "az_ornek": True}
    return {"gecti": bool(math.isfinite(r_ayi) and math.isfinite(r_toplam) and r_ayi >= -sabit.S4_KAYIP_ORANI * r_toplam),
            "az_ornek": False}


# ============================================================================ koşucular
def strateji_ham(st, tf: str, evren_t: tuple, tablo_yolu, gecikme: int = 0, carpan: float = 1.0) -> tuple:
    """Verilen strateji nesnesini evrenin her enstrümanında geliştirme döneminde koşar (ham.ham_gorev ile AYNI yol: hazırla ->
    backtest -> islem_hazirla). -> ({sembol: ham df}, bilgi{veri_bas, veri_bit, disarida, hatali, hata_ornegi}).
    Verisi olmayan enstrüman 'disarida'; diğer her istisna 'hatali' (sayılır, çağıran satırı 'hata' yapar). HoldoutSizintisi yutulmaz."""
    ham, bilgi = {}, {"veri_bas": {}, "veri_bit": {}, "disarida": [], "hatali": [], "hata_ornegi": ""}
    run = we.GecikmeliStrateji(st, gecikme) if gecikme else st
    for s in evren_t:
        try:
            mumlar, fund = hm.veri_oku(s, tf)
        except hm.HoldoutSizintisi:
            raise
        except (FileNotFoundError, ValueError):
            bilgi["disarida"].append(s)
            continue
        if not len(mumlar):
            bilgi["disarida"].append(s)
            continue
        try:
            kural = we.tarama.SEMBOL_KURALLARI.get(s, we.tarama.VARSAYILAN_KURAL)
            ay = evren_maliyet.maliyet_ayarlari(s, kural, carpan, tablo_yolu)
            hazir = funding.stratejiye_hazirla(st, mumlar, fund, s, tf)
            res = backtest(hazir, run, ay, fund)
            h, _ = hm.islem_hazirla(res.islemler, s, tf, carpan, mumlar, tablo_yolu)
        except Exception as e:  # noqa: BLE001  (sayılır: bilgi['hatali']; çağıran satırı 'hata' yapar)
            bilgi["hatali"].append(s)
            bilgi["hata_ornegi"] = bilgi["hata_ornegi"] or f"{s}: {type(e).__name__}: {e}"[:200]
            continue
        ham[s] = h
        bilgi["veri_bas"][s] = hm.zaman_utc(mumlar.index[0])
        bilgi["veri_bit"][s] = hm.zaman_utc(mumlar.index[-1])
    return ham, bilgi


def evren_pf(ham: dict, analiz_bas) -> float:
    """Oynatma ÖNCESİ evren toplamı PF(R): analiz başlangıcından sonra girilen tüm işlemlerin R'si."""
    rs = [d["r"].to_numpy(dtype=float)[(pd.DatetimeIndex(d["giris_zamani"]) >= analiz_bas)] for d in ham.values() if len(d)]
    return pf_r(np.concatenate(rs)) if rs else math.nan


def kasa_pf(ham: dict, bilgi: dict, evren_t: tuple, analiz_bas, tablo_yolu) -> float:
    oos_bit = max(bilgi["veri_bit"].values()) + pd.Timedelta(1, "ns")
    m, _ = eleme.kasa_oynat(ham, evren_t, analiz_bas, oos_bit, 1.0, tablo_yolu)
    return math.nan if m is None else float(m.get("profit_factor", math.nan))


def komsu_listesi(st) -> list:
    return saglamlik.komsu_parametreler(st.parametreler, st.parametre_izgarasi or {})


def kapanis_serileri(evren_t: tuple) -> dict:
    """S4 endeksi için üyelerin 1d kapanışları (geliştirme dönemi, ham gün serisi — doldurma rejim.endeks_kur'da)."""
    out = {}
    for s in evren_t:
        try:
            mumlar, _ = hm.veri_oku(s, "1d")
        except hm.HoldoutSizintisi:
            raise
        except (FileNotFoundError, ValueError):
            continue
        if len(mumlar):
            out[s] = pd.Series(mumlar["kapanis"].to_numpy(dtype=float), index=pd.DatetimeIndex(mumlar.index).floor("D"))
    return out


# ============================================================================ satır
def satir_yolu(cikti: Path, ad: str, tf: str) -> Path:
    return Path(cikti) / "saglamlik_satir" / f"{ad}--{tf}.json"


def _kismi_yolu(cikti: Path, ad: str, tf: str) -> Path:
    return Path(cikti) / "saglamlik_kismi" / f"{ad}--{tf}--s2.json"


def saglamlik_satiri(row: dict, cikti: Path, tablo_yolu, tablo_hash: str, son: Optional[float] = None) -> dict:
    """Bir keşif satırı için S1..S4. Kapı bitince satır dosyasına yazılır; biten kapı yeniden koşulmaz. son: bütçe zaman damgası."""
    cikti = Path(cikti)
    ad, tf, evren, stil = row["strateji"], row["tf"], row["evren"], row["stil_v2"]
    yol = satir_yolu(cikti, ad, tf)
    s = json.loads(yol.read_text()) if yol.exists() else {"strateji": ad, "tf": tf, "evren": evren, "stil_v2": stil, "durum": "bekliyor"}
    if s.get("durum") == "tamam":
        return s

    def doldu():
        return son is not None and time.time() > son

    def kaydet():
        kasa.atomik_yaz_json(yol, s)
    evren_t = sabit.evren_listesi(evren)
    try:
        _, st = hm.varsayilan_strateji(ad) if stil != "portfoy" else (None, None)
        if stil == "portfoy":
            return _pf_satiri(row, s, cikti, tablo_yolu, tablo_hash, doldu, kaydet, evren_t)
        ham1, b1 = hm.ham_yukle(cikti, 1.0, ad, tf, evren_t, tablo_hash)
        if b1["hatali"] or not ham1:
            raise RuntimeError(f"x1 ham sonuç kullanılamaz (hatalı {len(b1['hatali'])}, veri {len(ham1)})")
        analiz_bas, _ = kasa.donem_sinirlari(b1)
        # ---- ×2 PF (set sıralaması için; kapı değil)
        if "pf_x2" not in s:
            ham2, b2 = hm.ham_yukle(cikti, 2.0, ad, tf, evren_t, tablo_hash)
            s["pf_x2"] = kasa_pf(ham2, b2, evren_t, analiz_bas, tablo_yolu) if ham2 else math.nan
            kaydet()
        # ---- S1
        if "s1" not in s:
            if doldu():
                return {"ertelendi": True, "strateji": ad, "tf": tf}
            hg, bg = strateji_ham(st, tf, evren_t, tablo_yolu, gecikme=sabit.S1_GECIKME_MUM)
            if bg["hatali"] or not hg:
                s.update(s1=False, s1_pf=math.nan, s1_hata=bg["hata_ornegi"] or "veri yok")
            else:
                pf = kasa_pf(hg, bg, evren_t, analiz_bas, tablo_yolu)
                s.update(s1=s1_karar(pf), s1_pf=pf, s1_hata="")
            kaydet()
        # ---- S2
        if "s2" not in s:
            if _s2(s, st, tf, evren_t, analiz_bas, tablo_yolu, cikti, ad, doldu) is None:
                return {"ertelendi": True, "strateji": ad, "tf": tf}
            kaydet()
        # ---- S3
        if "s3" not in s:
            if stil in sabit.STIL_TF_YOK:
                s.update(s3=True, s3_pf=math.nan, s3_uygulanir=False, s3_hata="")
            else:
                if doldu():
                    return {"ertelendi": True, "strateji": ad, "tf": tf}
                diger = sabit.S3_DIGER_TF[tf]
                hd, bd = strateji_ham(st, diger, evren_t, tablo_yolu)
                if bd["hatali"] or not hd:
                    s.update(s3=False, s3_pf=math.nan, s3_uygulanir=True, s3_hata=bd["hata_ornegi"] or "diğer tf'de veri yok")
                else:
                    pf = evren_pf(hd, analiz_bas)
                    s.update(s3=s3_karar(pf), s3_pf=pf, s3_uygulanir=True, s3_hata="")
            kaydet()
        # ---- S4
        if "s4" not in s:
            o = kasa.satir_oynat(cikti, row, tablo_yolu, tablo_hash)
            ayi = rejim.ayi_gunleri(rejim.endeks_kur(kapanis_serileri(evren_t)))
            tab, kabul = o["tablo"], list(o["res"]["kabul"])
            r = tab["r"].to_numpy(dtype=float)[kabul]
            a = rejim.giris_ayi_mi(ayi, pd.DatetimeIndex(tab["giris"])[kabul])
            k = s4_karar(float(r[a].sum()), float(r.sum()), int(a.sum()))
            s.update(s4=k["gecti"], s4_az_ornek="evet" if k["az_ornek"] else "hayir", s4_r_ayi=float(r[a].sum()),
                     s4_r_toplam=float(r.sum()), s4_n_ayi=int(a.sum()))
            kaydet()
    except hm.HoldoutSizintisi:
        raise
    except (FileNotFoundError, ValueError, RuntimeError, KeyError) as e:
        if isinstance(e, RuntimeError) and "bitmemiş" in str(e):
            return {"ertelendi": True, "neden": str(e), "strateji": ad, "tf": tf}
        s.update(hata=f"{type(e).__name__}: {e}"[:300])
    return _bitir(s, yol)


def _s2(s: dict, st, tf, evren_t, analiz_bas, tablo_yolu, cikti, ad, doldu):
    """S2 komşu ayarlar; komşu başına kısmi sonuç. Bütçe dolarsa None (satır ertelenir)."""
    ky = _kismi_yolu(cikti, ad, tf)
    kismi = json.loads(ky.read_text()) if ky.exists() else {}
    komsular = komsu_listesi(st)
    for p, yon, v in komsular:
        anahtar = f"{p}{'+' if yon > 0 else '-'}={v}"
        if anahtar in kismi:
            continue
        if doldu():
            return None
        try:
            ns = st.yeni(**{p: v})
        except (ValueError, TypeError) as e:
            kismi[anahtar] = {"pf": None, "hata": f"kurulamadı: {e}"[:100]}
            kasa.atomik_yaz_json(ky, kismi)
            continue
        h, b = strateji_ham(ns, tf, evren_t, tablo_yolu)
        if b["hatali"]:
            kismi[anahtar] = {"pf": None, "hata": b["hata_ornegi"]}
        elif not h:
            kismi[anahtar] = {"pf": None, "hata": "veri yok"}
        else:
            pf = evren_pf(h, analiz_bas)
            kismi[anahtar] = {"pf": pf if math.isfinite(pf) else None, "hata": ""}
        kasa.atomik_yaz_json(ky, kismi)
    k = s2_karar([v["pf"] for v in kismi.values()])
    hatali = [a for a, v in kismi.items() if v.get("hata") and "kurulamadı" not in v["hata"]]
    s.update(s2=k["gecti"] and not hatali, s2_n_komsu=len(komsular), s2_n_gecerli=k["n_gecerli"], s2_medyan=k["medyan"],
             s2_en_dusuk=k["en_dusuk"], s2_hata=(kismi[hatali[0]]["hata"] if hatali else ""))
    return True


def _pf_satiri(row, s, cikti, tablo_yolu, tablo_hash, doldu, kaydet, evren_t) -> dict:
    """Portföy satırı: S1 = 1 bar gecikmeli ağırlık tablosu (GecikmePf), PF(R) = portföy işlemlerinin R'si; S2 = varsayılan ayarın
    sayısal parametre komşuları, PF(R); S3 yok; S4 = ayı günlerinde günlük getiri toplamı (yeniden dengeleme günü < S4_MIN_ISLEM ise
    ölçülemedi). Çalıştırıcılar `_pf_kos` ile enjekte edilebilir (test)."""
    ad, tf = row["strateji"], row["tf"]
    yol = satir_yolu(cikti, ad, tf)
    try:
        g1, m1 = hm.pf_yukle(cikti, 1.0, ad, tablo_hash)
        g2, _ = hm.pf_yukle(cikti, 2.0, ad, tablo_hash)
        if g1 is None or g2 is None:
            raise RuntimeError("portföy x1/x2 koşusu hata")
        analiz_bas = we.analiz_bas_hesapla({k: pd.Timestamp(t) for k, t in m1["veri_bas_sembol"].items()})
        if "pf_x2" not in s:
            from motor.arastirma import wf_portfoy as wp
            x = g2[pd.DatetimeIndex(g2["gun"]) >= analiz_bas]["getiri"].to_numpy(dtype=float)
            s["pf_x2"] = float(wp.sharpe_gunluk(x))               # portföy satırında sıralama ölçüsü: x2 günlük Sharpe
            kaydet()
        if "s1" not in s:
            if doldu():
                return {"ertelendi": True, "strateji": ad, "tf": tf}
            pf = _pf_kos(ad, evren_t, analiz_bas, gecikme=sabit.S1_GECIKME_MUM)
            s.update(s1=s1_karar(pf), s1_pf=pf, s1_hata="")
            kaydet()
        if "s2" not in s:
            if doldu():
                return {"ertelendi": True, "strateji": ad, "tf": tf}
            pfler, n_komsu = _pf_komsular(ad, evren_t, analiz_bas)
            k = s2_karar(pfler)
            s.update(s2=k["gecti"], s2_n_komsu=n_komsu, s2_n_gecerli=k["n_gecerli"], s2_medyan=k["medyan"],
                     s2_en_dusuk=k["en_dusuk"], s2_hata="")
            kaydet()
        s.update(s3=True, s3_pf=math.nan, s3_uygulanir=False, s3_hata="")
        if "s4" not in s:
            ayi = rejim.ayi_gunleri(rejim.endeks_kur(kapanis_serileri(evren_t)))
            x = g1[pd.DatetimeIndex(g1["gun"]) >= analiz_bas]
            a = rejim.giris_ayi_mi(ayi, pd.DatetimeIndex(x["gun"]))
            getiri = x["getiri"].to_numpy(dtype=float)
            n_ayi = int((a & x["dengeleme"].to_numpy(dtype=bool)).sum())
            k = s4_karar(float(getiri[a].sum()), float(getiri.sum()), n_ayi)
            s.update(s4=k["gecti"], s4_az_ornek="evet" if k["az_ornek"] else "hayir", s4_r_ayi=float(getiri[a].sum()),
                     s4_r_toplam=float(getiri.sum()), s4_n_ayi=n_ayi)
            kaydet()
    except hm.HoldoutSizintisi:
        raise
    except (FileNotFoundError, ValueError, RuntimeError, KeyError) as e:
        if isinstance(e, RuntimeError) and "bitmemiş" in str(e):
            return {"ertelendi": True, "neden": str(e), "strateji": ad, "tf": tf}
        s.update(hata=f"{type(e).__name__}: {e}"[:300])
    return _bitir(s, yol)


def _pf_kos(ad: str, evren_t: tuple, analiz_bas, gecikme: int = 0, **ayar) -> float:
    """Portföy varsayılan ayarını (ya da `ayar` ile değiştirilmiş) gecikmeli/gecikmesiz koşar; PF(R) (analiz başlangıcından sonra
    girilen portföy işlemleri)."""
    from motor.arastirma import wf_evren_portfoy as wep
    v, f, _ = wep.veri_yukle(evren_t, "1d")
    for s_, df in v.items():
        hm.sizinti_kontrol(s_, "1d", df, f.get(s_))
    ev = tuple(v)
    st = hm.varsayilan_pf(ad, ev)
    if st is None:
        raise RuntimeError("varsayılan ayar bu evrende uygun değil")
    if ayar:
        st = st.yeni(**ayar)
    r = wep._kos(st, v, f, ev, hm.maliyet_pf(ev, 1.0, _tablo_yolu_pf()), gecikme)
    t = r.islemler
    if not len(t):
        return math.nan
    t = t[pd.DatetimeIndex(t["giris_zamani"]) >= analiz_bas]
    return pf_r(np.nan_to_num(t["r"].to_numpy(dtype=float), nan=0.0))


_TABLO = {"yol": None}


def _tablo_yolu_pf():
    return _TABLO["yol"]


def _pf_komsular(ad: str, evren_t: tuple, analiz_bas) -> tuple:
    from motor.arastirma import wf_evren_portfoy as wep
    v, f, _ = wep.veri_yukle(evren_t, "1d")
    ev = tuple(v)
    st = hm.varsayilan_pf(ad, ev)
    if st is None:
        raise RuntimeError("varsayılan ayar bu evrende uygun değil")
    komsular = saglamlik.komsu_parametreler(st.parametreler, getattr(st, "parametre_izgarasi", None) or {})
    pfler = []
    for p, _, val in komsular:
        try:
            pfler.append(_pf_kos(ad, evren_t, analiz_bas, **{p: val}))
        except (ValueError, TypeError, RuntimeError):
            pfler.append(math.nan)                                 # geçersiz komşu: s2_n_gecerli'de sayılmaz
    return pfler, len(komsular)


def _bitir(s: dict, yol: Path) -> dict:
    hata = bool(s.get("hata"))
    kapilar = [bool(s.get(k, False)) for k in ("s1", "s2", "s3", "s4")]
    s.update(durum="hata" if hata else "tamam", saglam=bool(all(kapilar)) and not hata)
    kasa.atomik_yaz_json(yol, s)
    return s


# ============================================================================ aşama
_AYAR: dict = {}


def _baslat(ayar: dict):
    we.veri_ayarla(ayar.get("veri_dizini"), sabit.DONEM)
    _AYAR.clear()
    _AYAR.update(ayar)
    _TABLO["yol"] = ayar["tablo_yolu"]


def _isci(g: dict):
    return saglamlik_satiri(g["row"], Path(_AYAR["cikti"]), _AYAR["tablo_yolu"], _AYAR["tablo_hash"], _AYAR.get("son"))


def test_oku(cikti: Path) -> pd.DataFrame:
    cikti = Path(cikti)
    yol, oz = cikti / "test.csv", cikti / "test_ozet.json"
    if not yol.exists() or not oz.exists():
        raise RuntimeError(f"test.csv / test_ozet.json yok: önce test aşaması ({cikti})")
    if json.loads(oz.read_text()).get("test_csv_sha256") != kasa.sha256(yol):
        raise RuntimeError("test.csv test_ozet.json'daki sha256 ile uyuşmuyor")
    return pd.read_csv(yol)


def saglamlik_asamasi(cikti: Path = None, surec: int = sabit.SUREC_VARSAYILAN, butce_sn: Optional[float] = None, ilerleme: bool = True) -> dict:
    cikti = Path(cikti or sabit.CIKTI)
    kasa.yazma_engeli(cikti)
    t = test_oku(cikti)
    kes = t[t["kesif"].astype(bool)]
    from motor.arastirma.v2 import maliyet
    tablo = maliyet.tablo_yolu(cikti)
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    gorev = []
    for _, row in kes.iterrows():
        y = satir_yolu(cikti, row["strateji"], row["tf"])
        if y.exists() and json.loads(y.read_text()).get("durum") in ("tamam", "hata"):
            continue
        gorev.append({"row": {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}})
    if ilerleme:
        print(f"[v2 saglamlik] keşif {len(kes)}, bekleyen {len(gorev)}", flush=True)
    ayar = {"cikti": str(cikti), "tablo_yolu": str(tablo), "tablo_hash": tablo_hash}
    sonuc = we.havuz_calistir(_isci, gorev, surec, _baslat, ayar, butce_sn, ilerleme, "v2 saglamlik")
    bekleyen = sum(1 for x in sonuc if x.get("ertelendi"))
    if bekleyen:
        ozet = {"kesif": len(kes), "bekleyen": bekleyen, "neden": next((x.get("neden") for x in sonuc if x.get("neden")), "bütçe doldu")}
        if ilerleme:
            print(f"[v2 saglamlik] TAMAMLANMADI: {ozet}", flush=True)
        return ozet
    satirlar = []
    for _, row in kes.iterrows():
        s = json.loads(satir_yolu(cikti, row["strateji"], row["tf"]).read_text())
        for c in ("etiket", "alt_etiket", "kume_no", "kilit_gorulmus", "p"):
            s[c] = row.get(c)
        s["liste"] = "saglam_kesif" if s.get("saglam") else ("izleme" if s.get("durum") == "tamam" else "hata")
        satirlar.append(s)
    kolon = ["strateji", "stil_v2", "tf", "evren", "etiket", "alt_etiket", "kume_no", "kilit_gorulmus", "p", "liste", "saglam", "pf_x2",
             "s1", "s1_pf", "s2", "s2_n_komsu", "s2_n_gecerli", "s2_medyan", "s2_en_dusuk", "s3", "s3_uygulanir", "s3_pf", "s4",
             "s4_az_ornek", "s4_n_ayi", "s4_r_ayi", "s4_r_toplam", "hata"]
    df = pd.DataFrame(satirlar, columns=kolon) if satirlar else pd.DataFrame(columns=kolon)
    yol = cikti / "saglamlik.csv"
    gecici = yol.with_suffix(".tmp")
    df.to_csv(gecici, index=False)
    gecici.replace(yol)
    ozet = {"kesif": int(len(df)), "saglam_kesif": int((df["liste"] == "saglam_kesif").sum()) if len(df) else 0,
            "izleme": int((df["liste"] == "izleme").sum()) if len(df) else 0, "hata": int((df["liste"] == "hata").sum()) if len(df) else 0,
            "saglamlik_csv_sha256": kasa.sha256(yol), "test_csv_sha256": kasa.sha256(cikti / "test.csv"),
            "maliyet_tablosu_sha256": tablo_hash}
    kasa.atomik_yaz_json(cikti / "saglamlik_ozet.json", ozet)
    if ilerleme:
        print(f"[v2 saglamlik] {ozet}", flush=True)
    return ozet
