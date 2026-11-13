#!/usr/bin/env python3
"""G0_SONUC: kodlanmış her stratejinin (kod_kaydi.csv) tüm test aşamalarındaki akıbeti.

SALT OKUR: sonuç dosyalarını okur, strateji KOŞMAZ, mevcut dosyaları DEĞİŞTİRMEZ. Tekrar çalıştırılabilir.
Çıktılar (yalnız şuraya yazar):
  sonuclar/hesap_defteri/ara/G0_kod_akibet.csv   (521 satır, kod_kaydi.csv ile birebir)
  sonuclar/hesap_defteri/ara/G0_ayarlar.csv      (kart_ayarlari + dis_ayarlari + d11j/d12b ek ayarlar; 1 kayıt = 1 satır)
  sonuclar/hesap_defteri/ara/G0_NOTLAR.md        (istatistikler + öz kontrol; sabit anlatım bölümleri aşağıda NOTLAR_SABIT)
Kullanım:  python sonuclar/hesap_defteri/betikler/g0_kod_akibet.py
Not: G0_ayarlar için motor/arastirma/wf_tarama.aday_listesi YALNIZ aday kümesini kurmak için çağrılır (backtest yok).
"""
from __future__ import annotations

import csv
import json
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[3]
ARA = KOK / "sonuclar" / "hesap_defteri" / "ara"
HAIKU = Path(os.environ.get(
    "HAIKU_KOPYA",
    "/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/scratchpad/ref_haiku_arge/sonuclar/haiku_arge"))
HAIKU_DAL = "dal:claude/haiku-arge-5-enstruman:sonuclar/haiku_arge"
csv.field_size_limit(sys.maxsize)

KANIT: dict[str, list[str]] = defaultdict(list)      # ad -> kanıt parçaları
KOSTU: dict[str, set] = defaultdict(set)             # ad -> sonuç dosyaları (hic_kosuldu)
ASAMA: dict[str, list] = defaultdict(list)           # ad -> [(rank, asama, sonuc, kapi_metni)]


# ------------------------------------------------------------------------------------------ yardımcılar
def fx(v, nd=3):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "NA"
        if isinstance(v, (bool, np.bool_)):
            return str(bool(v))
        if isinstance(v, str):
            return v
        v = float(v)
        if np.isinf(v):
            return "inf"
        if abs(v - round(v)) < 1e-12 and abs(v) < 1e9:
            return str(int(round(v)))
        return f"{v:.{nd}f}"
    except Exception:
        return str(v)


def bayrak(v):
    """CSV'den gelen True/False/NaN -> True/False/None."""
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, str):
        return {"true": True, "false": False}.get(v.strip().lower())
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return bool(v)


def satir_baslangiclari(yol: Path) -> list[int]:
    """Her veri kaydının dosyadaki FİZİKSEL başlangıç satırı (başlık = 1; tırnaklı çok satırlı alanlar doğru sayılır)."""
    bas = []
    with open(yol, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        next(r)
        prev = r.line_num
        for row in r:
            if row:
                bas.append(prev + 1)
            prev = r.line_num
    return bas


def oku(rel: str | Path, usecols=None, mutlak=False) -> pd.DataFrame:
    yol = Path(rel) if mutlak else KOK / rel
    df = pd.read_csv(yol, usecols=usecols, low_memory=False)
    bas = satir_baslangiclari(yol)
    if len(bas) != len(df):
        raise RuntimeError(f"{rel}: satır sayısı tutmuyor ({len(bas)} != {len(df)})")
    df["_satir"] = bas
    return df


def kanit_ekle(ad, yol, satirlar):
    if isinstance(satirlar, (int, np.integer)):
        satirlar = [int(satirlar)]
    satirlar = sorted(set(int(s) for s in satirlar))
    if not satirlar:
        return
    g = ",".join(map(str, satirlar[:4])) + (f",…(+{len(satirlar) - 4})" if len(satirlar) > 4 else "")
    KANIT[ad].append(f"{yol}:{g}")


def gruplar(df: pd.DataFrame, kol="strateji") -> dict[str, pd.DataFrame]:
    return {k: g for k, g in df.groupby(kol, sort=False)}


def kisa_sembol(s: str) -> str:
    return str(s).replace("USDT", "").replace("DK_", "")


TF_SIRA = {"5m": 0, "15m": 1, "30m": 2, "1h": 3, "4h": 4, "1d": 5}


def tf_sirala(tfler):
    return sorted(set(tfler), key=lambda t: TF_SIRA.get(t, 9))


NEDEN_KISALT = [
    (r"en iyi %5 hariç PF ([\-\d\.]+) < ([\d\.]+)", r"pf5=\1<\2"),
    (r"net ([\-\d\.]+) <= 0", r"net=\1<=0"),
    (r"PF ([\-\d\.]+) < ([\d\.]+)", r"PF=\1<\2"),
    (r"işlem (\d+) < (\d+)", r"islem=\1<\2"),
    (r"Sharpe ([\-\d\.]+) < ([\d\.]+)", r"Sharpe=\1<\2"),
    (r"düşüş ([\d\.]+) > ([\d\.]+)", r"DD=\1>\2"),
    (r"kârlı enstrüman oranı ([\d\.]+) < ([\d\.]+)", r"karli_enstr=\1<\2"),
    (r"tek enstrüman payı ([\d\.]+) > ([\d\.]+)", r"tek_enstr_pay=\1>\2"),
    (r"kârlı sınıf (\d+) < (\d+)", r"karli_sinif=\1<\2"),
    (r"tek_enstruman hesaplanamadı", "tek_enstr=NA"),
    (r"(\w+) hesaplanamadı", r"\1=NA"),
]


def neden_kisalt(metin) -> str:
    if not isinstance(metin, str) or not metin.strip():
        return ""
    out = []
    for seg in metin.split(";"):
        seg = seg.strip()
        for kalip, yer in NEDEN_KISALT:
            if re.fullmatch(kalip, seg):
                seg = re.sub(kalip, yer, seg)
                break
        out.append(seg)
    return ",".join(out)


# ------------------------------------------------------------------------------------------ kod kaydı
KOD = pd.read_csv(ARA / "kod_kaydi.csv")
ADLAR = KOD.ad.tolist()
KOD_BILGI = {r.ad: r for r in KOD.itertuples()}


# ------------------------------------------------------------------------------------------ ERKEN KATMANLAR
def erken_katmanlar():
    """k2_k3 özeti + k3/sağlamlık/kilit/final aşama kayıtları. Döner: ad -> ['parça', ...]"""
    ozet: dict[str, list[str]] = defaultdict(list)
    ana = {}
    # K2 özetleri
    for dosya, etiket in (("sonuclar/tarama/k2_ana_ozet.csv", "k2ana"), ("sonuclar/tarama/k2_izgara_ozet.csv", "k2izg")):
        d = oku(dosya)
        for r in d.itertuples():
            ozet[r.strateji].append(f"{etiket}(n={fx(r.satir_sayisi)},medPF={fx(r.medyan_pf, 2)},umutsuz={'E' if bayrak(r.umutsuz) else 'H'})")
            kanit_ekle(r.strateji, dosya, r._satir)
            KOSTU[r.strateji].add(dosya)
    # K3 WF + sağlamlık
    wf_dosyalar = ["k3_kripto", "k3_dk", "k3_dk_v2", "k3_hisse_kisa", "son1ay_k3_kripto"]
    wf_gecen = defaultdict(int)
    wf_toplam = defaultdict(int)
    wf_en_iyi = {}
    for et in wf_dosyalar:
        yol = f"sonuclar/wf/{et}.csv"
        d = oku(yol, usecols=["strateji", "sembol", "tf", "hata", "islem_sayisi", "profit_factor", "gecti", "nedenler"])
        for ad, g in gruplar(d).items():
            gec = g[g.gecti.map(bayrak) == True]  # noqa: E712
            sem = sorted({kisa_sembol(s) for s in g.sembol})
            tfs = tf_sirala(g.tf)
            sem_s = ("|".join(sem) if len(sem) <= 3 else f"{len(sem)}sembol")
            gec_s = ",".join(f"{kisa_sembol(r.sembol)}/{r.tf}" for r in gec.itertuples()) if len(gec) else "-"
            ozet[ad].append(f"{et}[{sem_s};{','.join(tfs)}]:n={len(g)},gecen={len(gec)}({gec_s})" + (f",hata={int(g.hata.notna().sum())}" if g.hata.notna().any() else ""))
            kanit_ekle(ad, yol, g._satir.tolist())
            KOSTU[ad].add(yol)
            wf_gecen[ad] += len(gec)
            wf_toplam[ad] += len(g)
            pf = pd.to_numeric(g.profit_factor, errors="coerce")
            if pf.notna().any():
                i = pf.idxmax()
                if ad not in wf_en_iyi or pf[i] > wf_en_iyi[ad][0]:
                    wf_en_iyi[ad] = (float(pf[i]), f"{kisa_sembol(g.sembol[i])}/{g.tf[i]}", et)
    for ad in wf_toplam:
        ASAMA[ad].append((10, "k3_wf", "gecti" if wf_gecen[ad] else "elendi",
                          f"K3 WF (karar 13): {wf_toplam[ad]} görev, geçen {wf_gecen[ad]}"
                          + (f"; en iyi PF={fx(wf_en_iyi[ad][0], 2)} ({wf_en_iyi[ad][1]}, {wf_en_iyi[ad][2]})" if ad in wf_en_iyi else "")))
    sag_ok = defaultdict(list)
    for et in wf_dosyalar:
        yol = f"sonuclar/saglamlik/{et}.csv"
        d = oku(yol, usecols=["strateji", "sembol", "tf", "saglam_mi", "kapi_basarisiz"])
        for ad, g in gruplar(d).items():
            parca = []
            for r in g.itertuples():
                ok = bayrak(r.saglam_mi)
                sag_ok[ad].append((ok, f"{kisa_sembol(r.sembol)}/{r.tf}", r.kapi_basarisiz))
                parca.append(f"{kisa_sembol(r.sembol)}/{r.tf}={'saglam' if ok else 'kaldi[' + str(r.kapi_basarisiz) + ']'}")
            ozet[ad].append(f"sag_{et}:" + ";".join(parca))
            kanit_ekle(ad, yol, g._satir.tolist())
            KOSTU[ad].add(yol)
    for ad, L in sag_ok.items():
        gec = [x for x in L if x[0]]
        ASAMA[ad].append((11, "k3_saglamlik", "gecti" if gec else "elendi",
                          f"K3b sağlamlık: {len(L)} satır, saglam {len(gec)}; kapılar: " + "; ".join(f"{a}:{c}" for ok, a, c in L if not ok)[:200]))
    # final aday havuzu, secim adaylar / oneri
    d = oku("sonuclar/final_aday_havuzu_tek_grafik.csv")
    for ad, g in gruplar(d).items():
        ozet[ad].append("final_aday_havuzu:" + ",".join(f"{kisa_sembol(r.sembol)}/{r.tf}" for r in g.itertuples()))
        kanit_ekle(ad, "sonuclar/final_aday_havuzu_tek_grafik.csv", g._satir.tolist())
        KOSTU[ad].add("final_aday_havuzu")
    d = oku("sonuclar/secim/adaylar.csv")
    for ad, g in gruplar(d).items():
        ozet[ad].append("secim_adaylar:" + ",".join(f"{kisa_sembol(r.sembol)}/{r.tf}(kume{fx(r.kume)})" for r in g.itertuples()))
        kanit_ekle(ad, "sonuclar/secim/adaylar.csv", g._satir.tolist())
        KOSTU[ad].add("secim_adaylar")
    d = oku("sonuclar/secim/oneri.csv")
    for ad, g in gruplar(d).items():
        ozet[ad].append("secim_oneri:" + ",".join(f"{r.ajan}/{r.rol}#{fx(r.sira)}" for r in g.itertuples()))
        kanit_ekle(ad, "sonuclar/secim/oneri.csv", g._satir.tolist())
        KOSTU[ad].add("secim_oneri")
    # portföy WF + sağlamlık
    pf_wf = defaultdict(list)
    import glob
    for yol in sorted(glob.glob(str(KOK / "sonuclar/wf_portfoy/*.csv"))):
        rel = os.path.relpath(yol, KOK)
        d = oku(rel, usecols=["strateji", "evren", "tf", "atlandi", "gecti", "sharpe", "net_getiri", "islem_sayisi", "nedenler"])
        et = Path(yol).stem
        for ad, g in gruplar(d).items():
            for r in g.itertuples():
                if bayrak(r.atlandi):
                    pf_wf[ad].append((None, f"{et}:{r.evren}=atlandi"))
                else:
                    pf_wf[ad].append((bayrak(r.gecti), f"{et}:{r.evren}={'gecti' if bayrak(r.gecti) else 'elendi'}(sh={fx(r.sharpe, 2)})"))
            kanit_ekle(ad, rel, g._satir.tolist())
            KOSTU[ad].add(rel)
    for ad, L in pf_wf.items():
        ozet[ad].append("wf_portfoy[" + ";".join(x[1] for x in L)[:300] + "]")
        gec = any(x[0] for x in L)
        ASAMA[ad].append((10, "k3_wf", "gecti" if gec else "elendi", f"portföy WF: {len(L)} koşu, geçen {sum(1 for x in L if x[0])}"))
    for yol in sorted(glob.glob(str(KOK / "sonuclar/saglamlik_portfoy/*.csv"))):
        rel = os.path.relpath(yol, KOK)
        d = oku(rel, usecols=["strateji", "evren", "tf", "saglam_mi", "saglam_nedenler"])
        et = Path(yol).stem
        for ad, g in gruplar(d).items():
            ozet[ad].append(f"sag_{et}:" + ";".join(f"{r.evren}={'saglam' if bayrak(r.saglam_mi) else 'kaldi[' + str(r.saglam_nedenler)[:60] + ']'}" for r in g.itertuples()))
            kanit_ekle(ad, rel, g._satir.tolist())
            KOSTU[ad].add(rel)
            ASAMA[ad].append((11, "k3_saglamlik", "gecti" if any(bayrak(x) for x in g.saglam_mi) else "elendi", f"portföy sağlamlık ({et}): " + "; ".join(str(x)[:80] for x in g.saglam_nedenler if isinstance(x, str))))
    return ozet


def kilit_ve_final():
    kilit = {}
    d = oku("sonuclar/kilit/sonuc.csv", usecols=["strateji", "sembol", "tf", "gruplar", "gecti", "neden", "kilit_islem", "kilit_pf", "kilit_net", "hata"])
    for ad, g in gruplar(d).items():
        parca = []
        for r in g.itertuples():
            parca.append(f"{kisa_sembol(r.sembol)}/{r.tf}:{r.gruplar}:{'gecti' if bayrak(r.gecti) else 'kaldi'},n={fx(r.kilit_islem)},pf={fx(r.kilit_pf, 2)},net={fx(r.kilit_net, 3)}")
        kilit[ad] = ";".join(parca)
        kanit_ekle(ad, "sonuclar/kilit/sonuc.csv", g._satir.tolist())
        KOSTU[ad].add("sonuclar/kilit/sonuc.csv")
        gec = [r for r in g.itertuples() if bayrak(r.gecti)]
        ASAMA[ad].append((13, "kilit_k4", "gecti" if gec else "elendi",
                          f"Katman 4 kilitli dönem: {len(g)} satır, geçen {len(gec)}; " + "; ".join(f"{kisa_sembol(r.sembol)}/{r.tf}:{str(r.neden)[:70]}" for r in g.itertuples() if not bayrak(r.gecti))[:220]))
    final = {}
    fs = json.load(open(KOK / "stratejiler/final_set.json", encoding="utf-8"))
    for i, s in enumerate(fs["stratejiler"]):
        ad = s["strateji"]
        final[ad] = f"evet ({s['sembol']}/{s['tf']}; kimlik {s['kimlik']}); karar 27 ile paper'dan kaldırıldı (DURUM.md satır 371)"
        KANIT[ad].append(f"stratejiler/final_set.json#{s['kimlik']}")
        KOSTU[ad].add("final_set.json")
        ASAMA[ad].append((12, "v1_final", "gecti", "v1 final set (7) üyesi; kilit setinde tek tek 3/7 geçti"))
    return kilit, final


# ------------------------------------------------------------------------------------------ V1 EVREN ZİNCİRİ
V1 = {}


def v1_zinciri():
    yol = "sonuclar/evren/2017_gelistirme/wf_evren.csv"
    d = oku(yol, usecols=["strateji", "stil", "tf", "n_enstruman_evren", "n_enstruman", "kisa_gecmis", "n_aday", "en_sik_ayar",
                          "islem_sayisi", "profit_factor", "net_getiri", "g1", "g2", "gecti", "nedenler", "hata", "yakin_wf", "secimler"])
    out = {}
    for ad, g in gruplar(d).items():
        g = g.copy()
        g["_t"] = g.tf.map(lambda t: TF_SIRA.get(t, 9))
        g = g.sort_values("_t")
        parca, tfs, kap = [], [], []
        gec_any = False
        for r in g.itertuples():
            tfs.append(r.tf)
            if isinstance(r.hata, str) and r.hata:
                parca.append(f"{r.tf}:hata[{r.hata[:50]}]")
                continue
            gec = bayrak(r.gecti)
            gec_any |= bool(gec)
            if gec:
                parca.append(f"{r.tf}:gecti n={fx(r.islem_sayisi)} pf={fx(r.profit_factor, 2)}")
            else:
                k = neden_kisalt(r.nedenler)
                parca.append(f"{r.tf}:elendi[{k[:110]}] n={fx(r.islem_sayisi)} pf={fx(r.profit_factor, 2)}")
                kap.append(f"{r.tf}: {k[:140]}")
        out[ad] = dict(tf=",".join(tf_sirala(tfs)), sonuc=" | ".join(parca), gecti=gec_any, kap="; ".join(kap), g=g,
                       n_enstruman=fx(g.n_enstruman.iloc[0]), n_aday=g.n_aday.iloc[0], satirlar=g._satir.tolist())
        kanit_ekle(ad, yol, g._satir.tolist())
        KOSTU[ad].add(yol)
        ASAMA[ad].append((20, "v1_wf", "gecti" if gec_any else "elendi", "v1 evren WF (35 enstrüman): " + "; ".join(kap)))
    # sağlamlık
    yol = "sonuclar/evren/2017_gelistirme/saglamlik.csv"
    s = oku(yol, usecols=["strateji", "tf", "saglam_mi", "kapi_basarisiz", "rnd_p", "m2_pf", "pf_boot_alt", "par_oran", "dsr_deneme", "wf_islem", "wf_pf"])
    for ad, g in gruplar(s).items():
        parca, kap, ok_any = [], [], False
        for r in g.itertuples():
            ok = bayrak(r.saglam_mi)
            ok_any |= bool(ok)
            parca.append(f"{r.tf}:saglam={ok}" + ("" if ok else f"[{r.kapi_basarisiz}; rnd_p={fx(r.rnd_p, 3)} m2_pf={fx(r.m2_pf, 2)} boot_alt={fx(r.pf_boot_alt, 2)} par={fx(r.par_oran, 2)} dsr={fx(r.dsr_deneme, 3)}]"))
            if not ok:
                kap.append(f"{r.tf}: {r.kapi_basarisiz} (rnd_p={fx(r.rnd_p, 3)}, m2_pf={fx(r.m2_pf, 2)}, boot_alt={fx(r.pf_boot_alt, 2)}, par_oran={fx(r.par_oran, 2)}, dsr={fx(r.dsr_deneme, 3)})")
        if ad in out:
            out[ad]["sag"] = " | ".join(parca)
        else:
            out[ad] = dict(tf="", sonuc="", sag=" | ".join(parca), gecti=False, kap="", g=None)
        kanit_ekle(ad, yol, g._satir.tolist())
        KOSTU[ad].add(yol)
        ASAMA[ad].append((21, "v1_saglamlik", "gecti" if ok_any else "elendi", "v1 sağlamlık: " + "; ".join(kap)))
    # secim / iyi listeler (boş) + arşivler
    for rel in ("secim.csv", "iyi_liste.csv", "iyiye_yakin_liste.csv"):
        p = KOK / "sonuclar/evren/2017_gelistirme" / rel
        try:
            n = len(pd.read_csv(p))
        except Exception:
            n = 0
        V1.setdefault("bos_dosyalar", {})[rel] = n
    arsiv = {}
    for rel, et in (("sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv", "arsiv_g7_oncesi"),
                    ("sonuclar/evren/2017_gelistirme/arsiv_scalp4/wf_scalp4.csv", "arsiv_scalp4")):
        d = oku(rel, usecols=["strateji", "tf", "gecti", "islem_sayisi", "profit_factor"])
        for ad, g in gruplar(d).items():
            arsiv.setdefault(ad, []).append(f"{et}:" + ",".join(f"{r.tf}={'gecti' if bayrak(r.gecti) else 'elendi'}" for r in g.itertuples()))
            kanit_ekle(ad, rel, g._satir.tolist())
            KOSTU[ad].add(rel)
    return out, arsiv


# ------------------------------------------------------------------------------------------ V2
def v2_havuz_disi(ad, havuz, kume_uye, temsilci_of):
    """(neden, kanit) ; havuzdaysa ('', '')."""
    if ad in havuz.index:
        return "", ""
    b = KOD_BILGI[ad]
    stil = b.stil
    pre, _, govde = ad.partition("__")
    if ad.startswith("pf__v3-") or ad.startswith("v3__"):
        return ("havuz mühürlendikten sonra kodlandı (v3 adayı, 2026-11-09 mührü: ON_KAYIT_V2 2.8 'mühürlendikten sonra ekleme yok')",
                "stratejiler/v3_adaylar/kodlama_v3.csv; sonuclar/evren/v2/havuz_muhru.json")
    if b.tur == "portfoy":
        return ("BELIRSIZ: pf stratejisi havuzda yok; havuz_v2_olustur.py tum_portfoy_stratejileri()'nin hepsini alır, sınıf mühürden sonra eklenmiş olabilir",
                "araclar/havuz_v2_olustur.py:aday_satirlari")
    if stil != "swing":
        ek = ""
        if pre in ("daytrade", "scalp"):
            tw = f"swing__{govde}"
            if tw in havuz.index:
                ek = f"; swing karşılığı {tw} havuzda (2.3 klon kuralı)"
            elif tw in KOD_BILGI:
                if tw in temsilci_of:
                    ek = f"; swing karşılığı {tw} küme temsilcisi değil (temsilci {temsilci_of[tw]})"
                else:
                    ek = f"; swing karşılığı {tw} kodlu ama havuzda yok"
            else:
                ek = "; swing__ karşılığı yok (2.3: havuza girmez)"
        return (f"stil v2 dışı: {stil} (ON_KAYIT_V2 2.2: daytrade/scalp v2 resmi ailesine girmez; yalnız 7'li gün-içi kripto hipotezi 2.5){ek}",
                "sonuclar/evren/ON_KAYIT_V2.md:2.2,2.3,2.5; araclar/havuz_v2_olustur.py:aday_satirlari")
    if ad in temsilci_of:
        t = temsilci_of[ad]
        h = havuz.loc[t]
        return (f"küme temsilcisi değil (ON_KAYIT_V2 2.7): temsilci={t} (etiket={h.etiket}/{h.alt_etiket}, kume_no={h.kume_no}, {h['not'].split(';')[0]}); "
                f"aynı etiket+alt_etiket ve v1 WF-OOS haftalık korelasyon ≥0.7 (ya da klon) kümesi; en az sayısal parametreli temsilci seçilir (korelasyon serisi oos/*.parquet repoda yok: değer doğrulanamadı)",
                f"stratejiler/havuz_v2.csv:{int(h['_satir'])}")
    return ("BELIRSIZ: swing stilinde ama havuzda da küme üyeleri listesinde de yok", "stratejiler/havuz_v2.csv")


def v2_kapi_metni(r) -> str:
    """eleme satırından kapı ve değerler (düşen her kapı)."""
    out = []
    tur_pf = r.stil_v2 == "portfoy"
    e = {k: bayrak(getattr(r, k)) for k in ("e1", "e2", "e3", "e4", "e5")}
    ned = r.nedenler if isinstance(r.nedenler, str) else ""
    if e["e1"] is not True:
        if tur_pf:
            out.append(f"E1 kârlılık: net(x2)={fx(r.net_x2)}, Sharpe(x1)={fx(r.sharpe_x1, 2)} (net>0 ve Sharpe≥0.5)")
        else:
            out.append(f"E1 kârlılık: net(x2)={fx(r.net_x2)}, PF(x1)={fx(r.pf_x1, 2)} (net>0 ve PF≥1.2)")
    if e["e2"] is not True:
        if tur_pf:
            out.append(f"E2 örnek: gün={fx(r.gun)}, dengeleme={fx(r.dengeleme)} (≥1095 gün, ≥20)")
        else:
            mine = 6 if r.evren == "kripto" else 10
            out.append(f"E2 örnek: n_islem={fx(r.n_islem_x1)}<200 ya da işlemli enstrüman={fx(r.n_enstruman_x1)}<{mine}")
    if e["e3"] is not True:
        parca = []
        if "en iyi enstrüman" in ned:
            parca.append("en iyi enstrüman çıkarılınca ΣR≤0")
        if "en iyi yıl" in ned:
            parca.append("en iyi yıl çıkarılınca ΣR≤0")
        out.append("E3 yoğunlaşma: " + (" ve ".join(parca) or "BELIRSIZ") + (f" (net_en_iyi_yil_haric={fx(r.net_en_iyi_yil_haric)})" if tur_pf else ""))
    if e["e4"] is not True and not tur_pf:
        try:
            rs = json.loads(r.r_sinif) if isinstance(r.r_sinif, str) else {}
            tot = sum(rs.values())
            if tot > 0:
                pay = ", ".join(f"{k} %{100 * v / tot:.0f}" for k, v in sorted(rs.items(), key=lambda kv: -kv[1]))
                sayi = sum(1 for v in rs.values() if v / tot >= 0.15)
                out.append(f"E4 genişlik: ΣR payları {pay} (≥%15 sınıf {sayi}<2)")
            else:
                out.append(f"E4 genişlik: toplam ΣR≤0 (sınıf ΣR: {', '.join(f'{k} {v:.1f}' for k, v in rs.items())})")
        except Exception:
            out.append("E4 genişlik: " + ned[:80])
    if e["e5"] is not True:
        out.append(f"E5 hayatta kalma: kill_olayi(x1)={fx(r.kill_x1)}")
    return "; ".join(out)


def v2_okuma():
    S = {}
    havuz = oku("stratejiler/havuz_v2.csv").set_index("strateji", drop=False)
    kume_uye, temsilci_of = {}, {}
    for r in havuz.itertuples():
        m = re.search(r"kume_uyeleri_havuz_disi=([^;]+)", str(r.not_)) if hasattr(r, "not_") else None
    for ad, row in havuz.iterrows():
        m = re.search(r"kume_uyeleri_havuz_disi=([^;]+)", str(row["not"]))
        if m:
            uyeler = m.group(1).split("/")
            kume_uye[ad] = uyeler
            for u in uyeler:
                temsilci_of[u] = ad
    S["havuz"], S["kume_uye"], S["temsilci_of"] = havuz, kume_uye, temsilci_of
    S["eleme"] = oku("sonuclar/evren/v2/eleme.csv").set_index("strateji", drop=False)
    S["test"] = oku("sonuclar/evren/v2/test.csv").set_index("strateji", drop=False)
    S["sag"] = oku("sonuclar/evren/v2/saglamlik.csv").set_index("strateji", drop=False)
    S["set"] = oku("sonuclar/evren/v2/set.csv").set_index("strateji", drop=False)
    S["set_ozet"] = json.load(open(KOK / "sonuclar/evren/v2/set_ozet.json", encoding="utf-8"))
    S["hk"] = oku("sonuclar/evren/v2/holdout_kesif/holdout_kesif.csv").set_index("strateji", drop=False)
    S["ho"] = oku("sonuclar/evren/v2/holdout/holdout.csv").set_index("strateji", drop=False)
    S["paper"] = json.load(open(KOK / "stratejiler/paper_v2_seti.json", encoding="utf-8"))
    return S


def v2_alanlari(ad, S, bos):
    """v2 sütunları + aşama kayıtları."""
    o = dict(bos)
    havuz, eleme, test, sag, sset, hk, ho = S["havuz"], S["eleme"], S["test"], S["sag"], S["set"], S["hk"], S["ho"]
    neden, kn = v2_havuz_disi(ad, havuz, S["kume_uye"], S["temsilci_of"])
    if ad in havuz.index:
        o["v2_havuzda"] = "evet"
        kanit_ekle(ad, "stratejiler/havuz_v2.csv", int(havuz.loc[ad, "_satir"]))
        KOSTU[ad].add("stratejiler/havuz_v2.csv")
    else:
        o["v2_havuzda"] = "hayir"
        o["v2_havuz_disi_neden"] = neden + (f" [kanıt: {kn}]" if kn else "")
    if ad in eleme.index:
        r = eleme.loc[ad]
        rt = r.to_frame().T.itertuples().__next__()
        o["v2_tf"], o["v2_evren"] = r.tf, r.evren
        o["v2_ayar"] = r.ayar
        o["v2_ayar_kaynagi"] = "varsayilan" if r.ayar == "varsayilan" else (r.ayar.split(":")[0] if ":" in str(r.ayar) else "izgara")
        o["v2_eleme"] = r.durum
        for k in ("e1", "e2", "e3", "e4", "e5"):
            o[f"v2_{k}"] = fx(bayrak(r[k]))
        o["v2_nedenler"] = (r.nedenler if isinstance(r.nedenler, str) else "") if r.durum != "hata" else str(r.hata)
        o["v2_n_islem_x1"], o["v2_pf_x1"], o["v2_net_x1"], o["v2_net_x2"], o["v2_kill_x1"] = (
            fx(r.n_islem_x1), fx(r.pf_x1, 3), fx(r.net_x1, 4), fx(r.net_x2, 4), fx(r.kill_x1))
        kanit_ekle(ad, "sonuclar/evren/v2/eleme.csv", int(r._satir))
        KOSTU[ad].add("sonuclar/evren/v2/eleme.csv")
        if r.durum == "hata":
            ASAMA[ad].append((30, "v2_eleme_hata", "hata", f"v2 eleme KOŞU HATASI (gerçek test yok): {str(r.hata)[:150]}"))
        else:
            ASAMA[ad].append((30, "v2_eleme", "gecti" if r.durum == "gecti" else "elendi", v2_kapi_metni(rt) if r.durum != "gecti" else "v2 eleme geçti (E1-E5)"))
    # test
    if ad in test.index:
        t = test.loc[ad]
        kanit_ekle(ad, "sonuclar/evren/v2/test.csv", int(t._satir))
        KOSTU[ad].add("sonuclar/evren/v2/test.csv")
        if t.eleme_durum == "gecti":
            o["v2_test"] = (f"{t.test_durum} p={fx(t.p, 5)} (aşama {fx(t.asama)}, B1={fx(t.B1)}) BH sıra={fx(t.bh_sira)} eşik={fx(t.bh_esik, 6)} kesif={fx(bayrak(t.kesif))}"
                            + (f" rnd_desteklenmeyen={t.rnd_desteklenmeyen}" if isinstance(t.rnd_desteklenmeyen, str) else ""))
            kes = bool(bayrak(t.kesif))
            if t.test_durum == "rnd_desteklenmeyen":
                m = f"K2 rastgele-giriş testi desteklenmeyen çıkış modülü ('{t.rnd_desteklenmeyen}') yüzünden uygulanamadı: p=1 (ON_KAYIT_V2 5.1); BH sıra={fx(t.bh_sira)}"
            else:
                m = f"K2 rastgele-giriş p={fx(t.p, 4)} > BH eşiği {fx(t.bh_esik, 5)} (sıra {fx(t.bh_sira)}/{len(test)}; keşif değil)"
            ASAMA[ad].append((31, "v2_test", "gecti" if kes else "elendi", "v2 test: keşif (BH q=0.10)" if kes else m))
        else:
            o["v2_test"] = f"elendi(eleme {t.eleme_durum}) -> p=1 (ON_KAYIT_V2 5.3: eleme geçemeyen p=1)"
    # sağlamlık
    if ad in sag.index:
        s = sag.loc[ad]
        kanit_ekle(ad, "sonuclar/evren/v2/saglamlik.csv", int(s._satir))
        KOSTU[ad].add("sonuclar/evren/v2/saglamlik.csv")
        ok = bool(bayrak(s.saglam))
        o["v2_saglamlik"] = (f"{s.liste} saglam={ok} S1(gecikme PF)={fx(bayrak(s.s1))}/{fx(s.s1_pf, 2)} S2(komşu ayar)={fx(bayrak(s.s2))}(medyan {fx(s.s2_medyan, 2)}, min {fx(s.s2_en_dusuk, 2)}, n={fx(s.s2_n_gecerli)}) "
                             f"S3(komşu tf)={fx(bayrak(s.s3))}/{fx(s.s3_pf, 2)} S4(ayı rejimi)={fx(bayrak(s.s4))}")
        kap = []
        if not bayrak(s.s1):
            kap.append(f"S1 gecikme PF={fx(s.s1_pf, 2)}<1.0")
        if not bayrak(s.s2):
            kap.append(f"S2 komşu ayar medyan PF={fx(s.s2_medyan, 2)} (≥1.1) / en düşük={fx(s.s2_en_dusuk, 2)} (≥0.9)")
        if not bayrak(s.s3):
            kap.append(f"S3 komşu TF PF={fx(s.s3_pf, 2)}<1.0")
        if not bayrak(s.s4):
            kap.append(f"S4 ayı rejimi: ayı ΣR={fx(s.s4_r_ayi, 1)} < -0.20×toplam({fx(s.s4_r_toplam, 1)})")
        ASAMA[ad].append((32, "v2_saglamlik", "gecti" if ok else "elendi", "v2 sağlamlık (izleme listesi): " + "; ".join(kap) if not ok else "v2 sağlamlık 4/4 geçti (saglam_kesif)"))
    # set
    sset_ad = ad in sset.index
    if ad in sag.index and bool(bayrak(sag.loc[ad].saglam)):
        if sset_ad:
            o["v2_set"] = "evet"
            kanit_ekle(ad, "sonuclar/evren/v2/set.csv", int(sset.loc[ad]._satir))
            ASAMA[ad].append((33, "v2_set", "gecti", f"v2 sete girdi (kume {fx(sset.loc[ad].kume)}, sira {fx(sset.loc[ad].sira)})"))
        else:
            anahtar = f"{ad}|{o['v2_tf']}"
            sebep = S["set_ozet"]["atlanan"].get(anahtar, "BELIRSIZ")
            o["v2_set"] = f"hayir (set seçiminde atlandı: {sebep})"
            kanit_ekle(ad, "sonuclar/evren/v2/set_ozet.json", 1)
            ASAMA[ad].append((33, "v2_set_secimi", "elendi", f"set seçiminde atlandı: {sebep} (küme/etiket kuralı; sağlamlık 4/4 geçmişti)"))
    else:
        o["v2_set"] = "hayir"
    # holdout resmi
    if ad in ho.index:
        h = ho.loc[ad]
        o["holdout_resmi"] = f"{h.durum}: net={fx(h.net, 4)} pf_r={fx(h.pf_r, 2)} n={fx(h.n_islem)} k2_p={fx(h.k2_p, 4)}"
        kanit_ekle(ad, "sonuclar/evren/v2/holdout/holdout.csv", int(h._satir))
        KOSTU[ad].add("sonuclar/evren/v2/holdout/holdout.csv")
        ASAMA[ad].append((34, "v2_holdout", "gecti" if h.durum == "kaldi" else "elendi", "resmi holdout (2025-11-08→2026-11-06): " + o["holdout_resmi"]))
    if ad in hk.index:
        h = hk.loc[ad]
        o["holdout_kesif"] = f"{h.grup}: net={fx(h.net, 4)} pf_r={fx(h.pf_r, 2)} n={fx(h.n_islem)} k2_p={fx(h.k2_p, 4)} (sonuç sonrası keşif — kanıt değil)"
        kanit_ekle(ad, "sonuclar/evren/v2/holdout_kesif/holdout_kesif.csv", int(h._satir))
        KOSTU[ad].add("sonuclar/evren/v2/holdout_kesif/holdout_kesif.csv")
    # paper + canlı
    pap = {s["strateji"]: s for s in S["paper"]["stratejiler"]}
    if ad in pap:
        o["paper_v2"] = "evet"
        o["_paper_etiket"] = pap[ad]["etiket"]
        KANIT[ad].append(f"stratejiler/paper_v2_seti.json#{ad}")
        KOSTU[ad].add("paper_v2_seti.json")
        ASAMA[ad].append((40, "paper_v2", "gecti", f"paper v2 seti ({pap[ad]['etiket']})"))
    else:
        o["paper_v2"] = "hayir"
    return o


def canli_kadro(ad):
    if ad in ("dis__ewo-ema-ofset", "dis__e0v1en"):
        KANIT[ad].append("stratejiler/canli_ayar.ornek.json#" + ad)
        KANIT[ad].append("sonuclar/canli/CANLI_PLAN_V2.md:18-19")
        ASAMA[ad].append((41, "canli_kadro", "gecti", "canlı kadro (60 USD duman; CANLI_PLAN_V2 §2)"))
        return "canli"
    if ad in ("dis__hma-atr-rider", "dis__lube"):
        KANIT[ad].append("sonuclar/canli/CANLI_PLAN_V2.md:20")
        return "paper"
    return "hayir"


# ------------------------------------------------------------------------------------------ V2 SONRASI + V3 + HAIKU
def v2_sonrasi():
    s = defaultdict(list)
    # meta_test
    d = oku("sonuclar/evren/meta_test/secilenler.csv", usecols=["kesim", "strateji", "kapi_gecti", "S", "N1"])
    for ad, g in gruplar(d).items():
        s[ad].append(f"meta_test:{len(g)}kesim,kapi_gecen={int(g.kapi_gecti.map(bayrak).sum())},S(secildi)={int(g.S.map(bayrak).sum())}")
        kanit_ekle(ad, "sonuclar/evren/meta_test/secilenler.csv", g._satir.tolist())
        KOSTU[ad].add("meta_test")
    # yeni sembol
    d = oku("sonuclar/evren/yeni_sembol/sonuc_strateji.csv", usecols=["evren", "strateji", "tf", "n_sembol", "n_x2", "pf_x2", "sum_r_x2", "yorum_x2"])
    for ad, g in gruplar(d).items():
        s[ad].append("yeni_sembol:" + "; ".join(f"{r.evren}({fx(r.n_sembol)}sembol,n={fx(r.n_x2)},PFx2={fx(r.pf_x2, 2)},ΣR={fx(r.sum_r_x2, 1)}{',' + r.yorum_x2 if isinstance(r.yorum_x2, str) else ''})" for r in g.itertuples()))
        kanit_ekle(ad, "sonuclar/evren/yeni_sembol/sonuc_strateji.csv", g._satir.tolist())
        KOSTU[ad].add("yeni_sembol")
    # teşhis
    d = oku("sonuclar/teshis/stop_cikis/sonuc.csv", usecols=["strateji", "tf", "n_islem", "tip", "beklenti_r"])
    for ad, g in gruplar(d).items():
        r = g.iloc[0]
        s[ad].append(f"teshis_stop_cikis:n={fx(r.n_islem)},beklenti_R={fx(r.beklenti_r, 3)},tip={r.tip}")
        kanit_ekle(ad, "sonuclar/teshis/stop_cikis/sonuc.csv", g._satir.tolist())
        KOSTU[ad].add("teshis")
    d = oku("sonuclar/teshis/duzenlilik/sonuc.csv", usecols=["strateji", "n_islem", "etiket", "tutmayan"])
    for ad, g in gruplar(d).items():
        r = g.iloc[0]
        s[ad].append(f"teshis_duzenlilik:n={fx(r.n_islem)},etiket={r.etiket},tutmayan={fx(r.tutmayan)}")
        kanit_ekle(ad, "sonuclar/teshis/duzenlilik/sonuc.csv", g._satir.tolist())
        KOSTU[ad].add("teshis")
    return s


def v3_okuma():
    out = {}
    e = oku("sonuclar/v3/eleme.csv", usecols=["no", "strateji", "tur", "tf", "evren", "durum", "nedenler", "n_islem", "net_x1", "net_x2", "sharpe_x1", "pf_x1", "p_rastgele"])
    for r in e.itertuples():
        ned = r.nedenler if isinstance(r.nedenler, str) else ""
        kisa = re.sub(r"\s+", " ", ned)[:230]
        out[r.strateji] = dict(durum=r.durum, nedenler=kisa, tf=r.tf, evren=str(r.evren)[:40], n_islem=r.n_islem)
        kanit_ekle(r.strateji, "sonuclar/v3/eleme.csv", r._satir)
        KOSTU[r.strateji].add("sonuclar/v3/eleme.csv")
        ASAMA[r.strateji].append((50, "v3_eleme", "gecti" if r.durum == "gecti" else "elendi", f"v3 eleme: {kisa}"))
    k = oku("stratejiler/v3_adaylar/kodlama_v3.csv")
    kod = {}
    for r in k.itertuples():
        if isinstance(r.strateji_ad, str):
            kod.setdefault(r.strateji_ad, []).append(r)
            if r.strateji_ad in KOD_BILGI:
                kanit_ekle(r.strateji_ad, "stratejiler/v3_adaylar/kodlama_v3.csv", r._satir)
    return out, kod


def haiku_okuma():
    out = defaultdict(list)
    if not HAIKU.exists():
        return out, False
    for et, alt in (("wf/haiku_elenen_swing", "swing"), ("wf/haiku_elenen_daytrade", "daytrade"), ("wf/haiku_elenen_scalp", "scalp")):
        d = oku(HAIKU / f"{et}.csv", usecols=["strateji", "sembol", "tf", "gecti"], mutlak=True)
        for ad, g in gruplar(d).items():
            gec = g[g.gecti.map(bayrak) == True]  # noqa: E712
            out[ad].append(f"wf[{alt}]:n={len(g)},gecen={len(gec)}" + (f"({','.join(kisa_sembol(r.sembol) + '/' + r.tf for r in gec.itertuples())})" if len(gec) else ""))
            KANIT[ad].append(f"{HAIKU_DAL}/{et}.csv:{','.join(map(str, g._satir.tolist()[:3]))}…")
            KOSTU[ad].add("haiku_arge")
    for et in ("haiku_elenen_swing", "haiku_elenen_daytrade"):
        d = oku(HAIKU / f"saglamlik/{et}.csv", usecols=["strateji", "sembol", "tf", "saglam_mi", "kapi_basarisiz"], mutlak=True)
        for ad, g in gruplar(d).items():
            out[ad].append("sag:" + ";".join(f"{kisa_sembol(r.sembol)}/{r.tf}={'saglam' if bayrak(r.saglam_mi) else 'kaldi[' + str(r.kapi_basarisiz) + ']'}" for r in g.itertuples()))
            KANIT[ad].append(f"{HAIKU_DAL}/saglamlik/{et}.csv:{','.join(map(str, g._satir.tolist()))}")
    return out, True


# ------------------------------------------------------------------------------------------ ANA
def tf_evren_ozeti(ad, v1, S, v3, k3_tfsem):
    p = []
    if ad in k3_tfsem:
        p.append(k3_tfsem[ad])
    if ad in v1 and v1[ad].get("tf"):
        p.append(f"v1_evren:{v1[ad]['tf']}|{v1[ad].get('n_enstruman', '?')}enstrüman")
    if ad in S["eleme"].index:
        r = S["eleme"].loc[ad]
        p.append(f"v2:{r.tf}|{r.evren}")
    if ad in v3:
        p.append(f"v3:{v3[ad]['tf']}|{v3[ad]['evren']}")
    return "; ".join(p)


def main():
    erken = erken_katmanlar()
    kilit, final = kilit_ve_final()
    v1, arsiv = v1_zinciri()
    S = v2_okuma()
    sonrasi = v2_sonrasi()
    v3, v3kod = v3_okuma()
    haiku, haiku_var = haiku_okuma()

    # K3 tf/sembol özeti (tf_evren için)
    k3_tfsem = {}
    for et in ["k3_kripto", "k3_dk_v2", "k3_hisse_kisa"]:
        d = pd.read_csv(KOK / f"sonuclar/wf/{et}.csv", usecols=["strateji", "sembol", "tf"])
        for ad, g in gruplar(d).items():
            k3_tfsem[ad] = (k3_tfsem.get(ad, "") + ("; " if ad in k3_tfsem else "") + f"{et}:{','.join(tf_sirala(g.tf))}|{g.sembol.nunique()}sembol")

    bos_alan = {k: "" for k in ("v2_havuz_disi_neden", "v2_tf", "v2_evren", "v2_ayar", "v2_ayar_kaynagi", "v2_eleme", "v2_e1", "v2_e2", "v2_e3", "v2_e4", "v2_e5",
                                "v2_nedenler", "v2_n_islem_x1", "v2_pf_x1", "v2_net_x1", "v2_net_x2", "v2_kill_x1", "v2_test", "v2_saglamlik", "v2_set",
                                "holdout_kesif", "holdout_resmi", "paper_v2", "v2_havuzda")}
    satirlar = []
    for ad in ADLAR:
        b = KOD_BILGI[ad]
        o = v2_alanlari(ad, S, bos_alan)
        kadro = canli_kadro(ad)
        # --- erken
        k2k3 = " | ".join(erken.get(ad, []))
        # --- v1
        V = v1.get(ad, {})
        v1_tf, v1_sonuc, v1_sag = V.get("tf", ""), V.get("sonuc", ""), V.get("sag", "")
        # --- v3 / haiku / sonrası
        v3s = ""
        if ad in v3:
            v3s = f"{v3[ad]['durum']}: {v3[ad]['nedenler']}"
        haiku_s = (" | ".join(haiku.get(ad, [])))
        sonr = " | ".join(sonrasi.get(ad, []))
        if ad in arsiv:
            KOSTU[ad].add("v1_arsiv")
        hic = "evet" if KOSTU.get(ad) else "hayir"

        # --- durum / aşama
        st = sorted(ASAMA.get(ad, []), key=lambda x: x[0])
        durum = asama = kapi = ""
        not_ = []
        if not st:
            # C
            durum = "C_KODLANDI_KOSULMADI"
            asama = "kosulmadi"
            if ad in v3kod:
                r = v3kod[ad][0]
                if r.durum == "altyapi_yok":
                    kapi = f"koşulamadı: altyapı yok — {r.not_}"
                elif r.durum == "veri_yok":
                    kapi = f"koşulamadı: veri yok — {r.not_}"
                elif ad == "v3__saatlik-asiri-tepki":
                    kapi = ("aile temsilcisi değil + birincil metin okunana dek bekletildi (ON_KAYIT_V3 0.4: 'saatlik-asiri-tepki birincil metin okunamadığı için bu turda yok'; "
                            "DURUM.md 2026-11-11 'saatlik-aşırı-tepki birincil metin okunana dek bekletilir')")
                elif r.durum == "kodlandi":
                    kapi = ("aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz "
                            "(ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcisi'); kodlama notu: " + str(r.not_)[:120])
                else:
                    kapi = f"kodlama_v3 durum={r.durum}: {r.not_}"
            else:
                kapi = "neden yazılı değil"
        else:
            son = st[-1]
            rank, asama, sonuc, kapi = son
            kesif_yolu = (o.get("_paper_etiket") == "iyi_gorundu")
            if rank >= 40 or (rank == 34 and sonuc == "gecti"):
                durum = "A_TEST_EDILDI_GECTI"
                if kesif_yolu:
                    not_.append("keşif yolu (kanıt değil): resmi v2'de elendi/izlemede; paper'a sonuç-sonrası holdout keşfi (kullanıcı onayı 2026-11-10) ile alındı")
                    kapi = ""
            elif sonuc == "gecti":
                durum = "A_TEST_EDILDI_GECTI"
            else:
                durum = "B_TEST_EDILDI_ELENDI"
            if durum.startswith("A"):
                # A için aşama adı: spec sıralaması
                if rank >= 41:
                    asama = "canli_kadro"
                elif rank >= 40:
                    asama = "paper_v2"
                elif asama == "v2_test":
                    asama = "v2_test_kesif"
                kapi = kapi if durum.startswith("B") else ""
            if asama == "v2_eleme_hata":
                not_.append("v2 koşu hatası: strateji v2'de gerçekten sınanmadı (teknik hata); gerçek test sonucu v1 aşamalarında")
        # --- yapisal_kapi
        yap = ""
        if ad in S["eleme"].index and o["v2_eleme"] != "hata":
            e = {k: o[f"v2_{k}"] == "True" for k in ("e1", "e2", "e3", "e4", "e5")}
            yap = "evet" if (e["e1"] and e["e3"] and not (e["e2"] and e["e4"] and e["e5"])) else "hayir"
            if o["v2_eleme"] == "gecti":
                yap = "hayir"
        # --- adil test
        adil, gerekce = "", ""
        if durum.startswith("B"):
            tag, gz = [], []
            veri_v1 = V.get("g")
            # tf sayısı / ayar özeti
            tf_sayisi = len(tf_sirala(list(veri_v1.tf))) if veri_v1 is not None else 0
            if ad in S["eleme"].index:
                r2 = S["eleme"].loc[ad]
                gz.append(f"v2: 1 TF ({r2.tf}), evren {r2.evren}, ayar {r2.ayar}, n_işlem(x1)={fx(r2.n_islem_x1)}")
            if veri_v1 is not None:
                gz.append(f"v1 evren: {tf_sayisi} TF denendi ({v1_tf}), aday ayar sayısı n_aday={fx(V.get('n_aday'))} (WF ızgara dahil)")
            # yapisal
            if yap == "evet":
                tag.append("yapisal_kapi")
                gz.append("E1 ve E3 geçti; yalnız " + "/".join(k.upper() for k in ("e2", "e4", "e5") if o[f"v2_{k}"] != "True") + " düştü")
            # zayıf temsilci
            temsilci = S["temsilci_of"].get(ad)
            if temsilci is not None or ad in S["kume_uye"]:
                rep = temsilci or ad
                uyeler = S["kume_uye"].get(rep, [])
                rep_el = S["eleme"].loc[rep].durum if rep in S["eleme"].index else "?"
                if rep_el != "gecti":
                    tag.append("zayif_temsilci")
                    gz.append(f"küme {rep}+{len(uyeler)} üye; temsilci v2 eleme={rep_el}; temsilci en az parametreliye göre seçildi (performansa göre değil), diğer {len(uyeler)} üye v2'de hiç koşulmadı")
            # tek TF
            if ad in S["eleme"].index and veri_v1 is not None:
                r2 = S["eleme"].loc[ad]
                diger = veri_v1[veri_v1.tf != r2.tf]
                kullan = veri_v1[veri_v1.tf == r2.tf]
                if len(diger):
                    d0 = diger.iloc[0]
                    pf_d = pd.to_numeric(d0.profit_factor, errors="coerce")
                    pf_k = pd.to_numeric(kullan.profit_factor.iloc[0], errors="coerce") if len(kullan) else np.nan
                    if bayrak(d0.gecti) or (pd.notna(pf_d) and pf_d >= 1.2) or (pd.notna(pf_d) and pd.notna(pf_k) and pf_d > pf_k + 0.1):
                        tag.append("yalniz_tek_TF")
                        gz.append(f"v2 yalnız {r2.tf}; v1'de {d0.tf} satırı PF={fx(pf_d, 2)} gecti={fx(bayrak(d0.gecti))} (v2'deki TF PF={fx(pf_k, 2)})")
            # varsayılan ayar
            if ad in S["eleme"].index and veri_v1 is not None and V.get("n_aday") and V["n_aday"] > 1:
                r2 = S["eleme"].loc[ad]
                kullan = veri_v1[veri_v1.tf == r2.tf]
                if len(kullan):
                    es = str(kullan.en_sik_ayar.iloc[0])
                    if es and es != "nan" and es != str(r2.ayar):
                        tag.append("yalniz_varsayilan_ayar")
                        gz.append(f"v2 ayar={r2.ayar}; v1 WF en sık seçilen ayar={es[:70]}")
            # kısa veri
            ns = None
            if ad in S["eleme"].index and o["v2_n_islem_x1"] not in ("", "NA"):
                ns = float(o["v2_n_islem_x1"])
            if asama == "v3_eleme":
                if ad in ("v3__btc-gecelik-max10-hafta-sonu", "v3__cuma-15-est-tutma"):
                    tag.append("kisa_veri")
                    gz.append("v3 eleme dönemi kısa (btc-gecelik 2024-10-15→, cuma-15 2022-01-01→; ON_KAYIT_V3 §1)")
            elif ns is not None and ns < 100 and o["v2_e1"] == "True":
                tag.append("kisa_veri")
                gz.append(f"kârlılık (E1) geçti ama işlem sayısı {fx(ns)} < 100: örnek yetersiz")
            # evet: tek kapıdan düşen / yakın
            if ad in S["eleme"].index and o["v2_eleme"] == "elendi":
                sayi_dusen = sum(1 for k in ("e1", "e2", "e3", "e4", "e5") if o[f"v2_{k}"] != "True")
                if sayi_dusen == 1:
                    tag.append("evet")
                    gz.append("v2 elemede tek kapıdan düştü")
            if asama in ("v2_test", "v2_saglamlik", "v2_set_secimi"):
                tag.append("evet")
                gz.append("v2 elemeyi geçti; test/sağlamlık/set aşamasında düştü")
            if asama == "v2_eleme_hata":
                tag.append("evet")
                gz.append("v2 koşusu teknik hatayla bitti (gerçek ret yok)")
            if asama in ("v3_eleme",):
                gz.append(f"v3: tek ayar, {v3[ad]['tf']}, {v3[ad]['evren']}")
            if asama == "k3_wf" or asama == "k3_saglamlik" or asama == "kilit_k4":
                gz.append("yalnız erken katman (kripto/DK, 3-10 sembol, tek tek) test edildi")
            # sırayı sabitle, tekrarı at
            sira = ["evet", "zayif_temsilci", "yalniz_tek_TF", "yalniz_varsayilan_ayar", "yapisal_kapi", "kisa_veri"]
            adil = ";".join(t for t in sira if t in tag)
            gerekce = " | ".join(gz)[:600]
        # --- islem sayısı (en son test aşamasında)
        isl = ""
        if ad in S["ho"].index:
            isl = f"holdout:{fx(S['ho'].loc[ad].n_islem)}"
        elif ad in S["hk"].index and durum.startswith("A"):
            isl = f"holdout_kesif:{fx(S['hk'].loc[ad].n_islem)}"
        elif ad in v3:
            isl = f"v3:{fx(v3[ad]['n_islem'])}"
        elif ad in S["eleme"].index and o["v2_eleme"] != "hata":
            isl = f"v2_x1:{o['v2_n_islem_x1']}"
        elif V.get("g") is not None:
            isl = "v1:" + ",".join(f"{r.tf}={fx(r.islem_sayisi)}" for r in V["g"].itertuples())
        # --- kanıt
        kn = " ; ".join(KANIT.get(ad, []))
        if arsiv.get(ad):
            v1_arsiv = " | ".join(arsiv[ad])
        else:
            v1_arsiv = ""
        not_s = " ; ".join(not_)
        satirlar.append(dict(
            kod_id=ad, tur=b.tur, stil=b.stil, kod_dosyasi=f"{b.dosya}:{b.sinif}:{b.satir}",
            k2_k3=k2k3, kilit_k4=kilit.get(ad, ""), final_v1=final.get(ad, "hayir"),
            v1_tf=v1_tf, v1_sonuc=v1_sonuc, v1_saglamlik=v1_sag, v1_secim=("yok (2017_gelistirme/secim.csv ve iyi_liste.csv boş: 0 satır)" if V.get("g") is not None and V.get("gecti") else ""), v1_arsiv=v1_arsiv,
            v2_havuzda=o["v2_havuzda"], v2_havuz_disi_neden=o["v2_havuz_disi_neden"], v2_tf=o["v2_tf"], v2_evren=o["v2_evren"], v2_ayar=o["v2_ayar"], v2_ayar_kaynagi=o["v2_ayar_kaynagi"],
            v2_eleme=o["v2_eleme"], v2_e1=o["v2_e1"], v2_e2=o["v2_e2"], v2_e3=o["v2_e3"], v2_e4=o["v2_e4"], v2_e5=o["v2_e5"], v2_nedenler=o["v2_nedenler"],
            v2_n_islem_x1=o["v2_n_islem_x1"], v2_pf_x1=o["v2_pf_x1"], v2_net_x1=o["v2_net_x1"], v2_net_x2=o["v2_net_x2"], v2_kill_x1=o["v2_kill_x1"],
            v2_test=o["v2_test"], v2_saglamlik=o["v2_saglamlik"], v2_set=o["v2_set"], holdout_kesif=o["holdout_kesif"], holdout_resmi=o["holdout_resmi"],
            paper_v2=o["paper_v2"], canli_kadro=kadro, v3_eleme=v3s, haiku_arge=haiku_s, sonrasi_testler=sonr,
            hic_kosuldu=hic, durum_onerisi=durum, asama=asama, kapi_ve_deger=kapi if (durum.startswith("B") or durum.startswith("C")) else "",
            yapisal_kapi=yap, adil_test_onerisi=adil, adil_test_gerekce=gerekce,
            tf_evren=tf_evren_ozeti(ad, v1, S, v3, k3_tfsem), islem_sayisi=isl, kanit=kn, **{"not": not_s}))
    cikti = pd.DataFrame(satirlar)
    assert len(cikti) == len(KOD) and cikti.kod_id.is_unique
    cikti.to_csv(ARA / "G0_kod_akibet.csv", index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n", encoding="utf-8")
    print("G0_kod_akibet.csv:", len(cikti))
    print(cikti.durum_onerisi.value_counts().to_string())
    return cikti, dict(S=S, v1=v1, v3=v3, v3kod=v3kod, haiku_var=haiku_var, kilit=kilit, final=final)


# ------------------------------------------------------------------------------------------ AYARLAR
def ayarlar(cikti, ctx):
    import glob
    sys.path.insert(0, str(KOK))
    try:
        from motor.arastirma import wf_tarama
        motor_var = True
    except Exception as e:  # noqa: BLE001
        print("motor import edilemedi:", e)
        motor_var = False
    kayitlar = []
    for yol in sorted(glob.glob(str(KOK / "stratejiler/kart_ayarlari/*.json"))):
        ad = Path(yol).stem
        for i, r in enumerate(json.load(open(yol, encoding="utf-8"))):
            kayitlar.append(dict(grup="kart", ad=ad, id=f"kart:{r['kart_id']}", ham=r["kart_id"], dosya=f"stratejiler/kart_ayarlari/{ad}.json#{i + 1}",
                                 kaynak=f"kart_id={r['kart_id']}", parametre=r.get("parametreler"), cikis=r.get("cikis_ayarlari"), nt=r.get("not", ""), ilk=(i == 0)))
    for yol in sorted(glob.glob(str(KOK / "stratejiler/dis_ayarlari/*.json"))):
        ad = Path(yol).stem
        for i, r in enumerate(json.load(open(yol, encoding="utf-8"))):
            kayitlar.append(dict(grup="dis", ad=ad, id=f"dis:{r['dis_id']}", ham=r["dis_id"], dosya=f"stratejiler/dis_ayarlari/{ad}.json#{i + 1}",
                                 kaynak=str(r.get("kaynak_dosya", ""))[:110], parametre=r.get("parametreler"), cikis=r.get("cikis_ayarlari"), nt=r.get("not", ""), ilk=False))
    for dos, et in (("ayarlar_d11j_ek.json", "d11j"), ("ayarlar_d12b_ek.json", "d12b")):
        for i, r in enumerate(json.load(open(KOK / "stratejiler" / dos, encoding="utf-8"))):
            kayitlar.append(dict(grup=et, ad=r["hedef"], id=r["ayar_id"], ham=r["ayar_id"], dosya=f"stratejiler/{dos}#{i + 1}",
                                 kaynak=str(r.get("kaynak_dosya", ""))[:110], parametre=r.get("parametreler"), cikis=r.get("cikis_ayarlari"), nt=r.get("not", ""), ilk=False))
    # v1 aday havuzu (wf_tarama.aday_listesi; v1 evren n_aday ile doğrulanmış)
    havuz_etiket, hatalar = {}, {}
    if motor_var:
        for ad in sorted({k["ad"] for k in kayitlar if k["grup"] in ("kart", "dis") and k["ad"] in KOD_BILGI and KOD_BILGI[k["ad"]].tur == "tek_grafik"}):
            try:
                c, h = wf_tarama.aday_listesi(ad, True)
                havuz_etiket[ad] = ([e for e, _ in c], len(c))
                hatalar[ad] = {e: m for e, m in h}
            except Exception as ex:  # noqa: BLE001
                havuz_etiket[ad] = (None, None)
                hatalar[ad] = {"_": str(ex)[:80]}
    # v1 en sık ayar + pencerede seçilme sayıları
    en_sik = defaultdict(lambda: defaultdict(set))   # ad -> etiket -> {dosya}
    pencere = defaultdict(lambda: defaultdict(int))
    d = pd.read_csv(KOK / "sonuclar/evren/2017_gelistirme/wf_evren.csv", usecols=["strateji", "tf", "en_sik_ayar", "secimler", "n_aday"])
    v1_naday = {}
    for r in d.itertuples():
        if isinstance(r.en_sik_ayar, str) and r.en_sik_ayar:
            en_sik[r.strateji][r.en_sik_ayar].add(f"wf_evren {r.tf}")
        v1_naday[r.strateji] = r.n_aday
        try:
            for s in json.loads(r.secimler):
                if s.get("ayar"):
                    pencere[r.strateji][s["ayar"]] += 1
        except Exception:
            pass
    for et in ("k3_kripto", "k3_dk", "k3_dk_v2", "k3_hisse_kisa", "son1ay_k3_kripto"):
        d = pd.read_csv(KOK / f"sonuclar/wf/{et}.csv", usecols=["strateji", "tf", "en_sik_ayar"])
        for r in d.itertuples():
            if isinstance(r.en_sik_ayar, str) and r.en_sik_ayar:
                en_sik[r.strateji][r.en_sik_ayar].add(f"{et} {r.tf}")
    d = pd.read_csv(KOK / "sonuclar/evren/2017_gelistirme/saglamlik.csv", usecols=["strateji", "tf", "en_sik_ayar"])
    for r in d.itertuples():
        if isinstance(r.en_sik_ayar, str):
            en_sik[r.strateji][r.en_sik_ayar].add(f"v1_saglamlik {r.tf}")
    d = pd.read_csv(KOK / "sonuclar/kilit/secilen_ayarlar.csv", usecols=["strateji", "tf", "secilen_ayar"])
    for r in d.itertuples():
        if isinstance(r.secilen_ayar, str):
            en_sik[r.strateji][r.secilen_ayar].add(f"kilit_secilen {r.tf}")
    eleme = ctx["S"]["eleme"]
    wf_var = {a for a in v1_naday}
    satirlar = []
    for k in kayitlar:
        ad, et = k["ad"], k["id"]
        var = ad in KOD_BILGI
        not_ = []
        if not var:
            not_.append("hedef strateji kod_kaydi.csv'de yok")
        # v1 havuz
        if k["grup"] in ("d11j", "d12b"):
            hv = "hayir"
            not_.append("ayarlar_d11j/d12b_ek.json'u okuyan araştırma kodu YOK (motor/ ve araclar/ taraması: yalnız testler/test_d11j_modlar.py ve testler/test_d12b_151.py okur); "
                        "tarama._ayar_listesi yalnız kart_ayarlari + dis_ayarlari + izgara; pf__ için wf_portfoy.aday_listesi yalnız BAGLAMA csv + varsayilan + izgara")
        elif var and KOD_BILGI[ad].tur == "portfoy":
            hv = "hayir"
            not_.append("pf__ stratejisi: wf_portfoy.aday_listesi kart/dis ayarı okumaz")
        elif ad in havuz_etiket and havuz_etiket[ad][0] is not None:
            etk = havuz_etiket[ad][0]
            if et in etk:
                hv = "evet"
            elif et in hatalar.get(ad, {}):
                hv = "hayir"
                not_.append(f"ayar kurulamadı: {hatalar[ad][et]}")
            else:
                hv = "evet_esdeger"
                not_.append("etkin parametre+çıkış başka adayla aynı olduğu için aday_listesi'nde tekilleştirildi (aynı ayar başka etiketle koşuldu)")
            if ad in v1_naday:
                if int(v1_naday[ad]) == int(havuz_etiket[ad][1]):
                    not_.append(f"v1 evren WF n_aday={int(v1_naday[ad])} = güncel aday sayısı (doğrulandı)")
                else:
                    not_.append(f"UYARI: v1 evren n_aday={fx(v1_naday[ad])} != güncel {havuz_etiket[ad][1]}")
        else:
            hv = "hayir"
            not_.append("aday listesi kurulamadı / hedef bulunamadı")
        # en sık
        es = en_sik.get(ad, {}).get(et)
        p = pencere.get(ad, {}).get(et, 0)
        if es:
            es_s = "evet"
            not_.append("en_sik_ayar: " + ",".join(sorted(es))[:100])
        else:
            es_s = "hayir"
        if p:
            not_.append(f"v1 evren WF pencerelerinde {p} kez seçildi")
        # v2
        v2s = "hayir"
        if ad in eleme.index and str(eleme.loc[ad].ayar) == et:
            v2s = "evet"
            not_.append("v2 eleme.csv ayar alanı bu ayar")
        # koşuldu
        if es or p or v2s == "evet":
            kos = "evet_secildi"
        elif hv in ("evet", "evet_esdeger") and ad in wf_var:
            kos = "evet_aday"
            not_.append("WF aday kümesinde koşuldu, hiç seçilmedi")
        elif hv in ("evet", "evet_esdeger"):
            kos = "BELIRSIZ"
            not_.append("havuzda ama strateji v1 evren WF'de satırı yok (yalnız erken katman olabilir)")
        else:
            kos = "hayir"
        if k["ilk"] and ad in eleme.index:
            not_.append("kart ayarı dosyasının İLK kaydı (ON_KAYIT_V2 1.1: v2 varsayılanı olur)" + ("" if v2s == "evet" else "; ama v2 eleme.csv ayar alanı farklı"))
        satirlar.append({"ayar_id": et, "hedef_kod_id": ad, "ayar_dosyasi": k["dosya"], "ayar_kaynagi": k["kaynak"], "v1_aday_havuzunda": hv,
                         "v1_en_sik_ayar_mi": es_s, "v2_secilen_ayar_mi": v2s, "kosuldu_mu": kos, "not": " ; ".join(not_)})
    df = pd.DataFrame(satirlar)
    df.to_csv(ARA / "G0_ayarlar.csv", index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n", encoding="utf-8")
    print("G0_ayarlar.csv:", len(df))
    print(df.groupby(["v1_aday_havuzunda", "kosuldu_mu"]).size().to_string())
    return df


# ------------------------------------------------------------------------------------------ NOTLAR
def ornek_izle(cikti, n=10, tohum=20261113):
    """Rastgele n satır: kanıt kolonundaki 'yol:satır' parçalarını dosyaya geri izle (satır, strateji id ile başlıyor/içeriyor mu)."""
    rnd = random.Random(tohum)
    secilen = rnd.sample(list(cikti.kod_id), n)
    out = []
    for ad in secilen:
        r = cikti[cikti.kod_id == ad].iloc[0]
        kontrol = []
        for parca in str(r.kanit).split(" ; "):
            m = re.match(r"^([^#]+\.csv):([\d,]+)", parca)
            if not m or parca.startswith("dal:"):
                continue
            yol = KOK / m.group(1)
            if not yol.exists():
                kontrol.append(f"{m.group(1)}: dosya yok")
                continue
            satir_no = [int(x) for x in m.group(2).split(",") if x.isdigit()]
            with open(yol, encoding="utf-8-sig", newline="") as f:
                satirlar = f.read().split("\n")
            ok = sum(1 for s in satir_no if s - 1 < len(satirlar) and ad.split("|")[0] in satirlar[s - 1][:400])
            kontrol.append(f"{m.group(1)}:{ok}/{len(satir_no)} satırda id görüldü")
        out.append((ad, r.durum_onerisi, r.asama, kontrol))
    return out


NOTLAR_SABIT = open(Path(__file__).with_name("g0_notlar_sabit.md"), encoding="utf-8").read() if (Path(__file__).with_name("g0_notlar_sabit.md")).exists() else ""


def notlar(cikti, ay, ctx):
    L = []
    L.append("# G0_SONUC notları (kod akıbeti defteri)\n")
    L.append("Üretici: `sonuclar/hesap_defteri/betikler/g0_kod_akibet.py` (salt okur; tekrar çalıştırılabilir). Çıktılar: `G0_kod_akibet.csv` (521), `G0_ayarlar.csv`.\n")
    L.append("## 1. Sayılar\n")
    vc = cikti.durum_onerisi.value_counts()
    L.append("### durum_onerisi dağılımı\n")
    for k, v in vc.items():
        L.append(f"- {k}: {v}")
    L.append("\n### asama dağılımı (A ve B ayrı)\n")
    for dur in ("A_TEST_EDILDI_GECTI", "B_TEST_EDILDI_ELENDI", "C_KODLANDI_KOSULMADI"):
        vv = cikti[cikti.durum_onerisi == dur].asama.value_counts()
        L.append(f"- {dur}: " + ", ".join(f"{k}={v}" for k, v in vv.items()))
    yap = cikti[cikti.yapisal_kapi == "evet"]
    L.append(f"\n### yapisal_kapi=evet: **{len(yap)}** (beklenen 73)\n")
    L.append("Tanım: v2 eleme.csv'de E1 ve E3 True, E2/E4/E5'ten en az biri False (durum=elendi). 'hata' (6) ve 'gecti' (18) satırları sayılmaz. "
             f"Kırılım: E4 düşen {int((yap.v2_e4 == 'False').sum())}, E2 düşen {int((yap.v2_e2 == 'False').sum())}, E5 düşen {int((yap.v2_e5 == 'False').sum())}.\n")
    c = cikti[cikti.durum_onerisi.str.startswith("C")]
    L.append(f"### hiç koşulmayanlar (C): **{len(c)}** (beklenen 26); hic_kosuldu=hayir: {int((cikti.hic_kosuldu == 'hayir').sum())}\n")
    for r in c.itertuples():
        L.append(f"- `{r.kod_id}` ({r.tur}/{r.stil}) — {r.kapi_ve_deger[:200]}")
    L.append("")
    # v1'de olup v2'de olmayan neden dağılımı
    v1var = cikti[(cikti.v1_tf != "") | (cikti.v1_saglamlik != "")]
    dis = v1var[v1var.v2_havuzda == "hayir"]
    L.append(f"### v1 evren zincirinde olup v2 havuzunda olmayan: {len(dis)} / v1'de olan {len(v1var)} (v2 havuzu {int((cikti.v2_havuzda == 'evet').sum())})\n")

    def sinif(x):
        if x.startswith("stil v2 dışı"):
            return "stil v2 dışı (daytrade/scalp)" + (" + swing__ klonu havuzda" if "klon kuralı" in x else (" + swing__ karşılığı yok" if "karşılığı yok" in x else ""))
        if x.startswith("küme temsilcisi değil"):
            return "küme temsilcisi değil (2.7)"
        if x.startswith("havuz mühürlendikten"):
            return "havuz sonrası eklendi"
        return x[:60]
    dd = dis.v2_havuz_disi_neden.map(sinif).value_counts()
    for k, v in dd.items():
        L.append(f"- {k}: {v}")
    L.append("\nv1 WF'de (g1/g2) kalma, v2 havuzuna girişin ÖLÇÜTÜ DEĞİLDİR: `araclar/havuz_v2_olustur.py::aday_satirlari` yalnız stil, klon kuralı, kümeleme ve etiketlere bakar. "
             "v1 sonuçları yalnız 2.7(b) kümelemesinde haftalık OOS serisi olarak kullanılır.\n")
    L.append("### havuzda olmayıp kod_kaydi'nda olan (v1'de olmayanlar dahil) toplam\n")
    d2 = cikti[cikti.v2_havuzda == "hayir"].v2_havuz_disi_neden.map(sinif).value_counts()
    for k, v in d2.items():
        L.append(f"- {k}: {v}")
    L.append("")
    L.append("### v2 aşamaları (kod_kaydi'ndaki strateji sayısı)\n")
    L.append(f"- v2 eleme: gecti {int((cikti.v2_eleme == 'gecti').sum())}, elendi {int((cikti.v2_eleme == 'elendi').sum())}, hata {int((cikti.v2_eleme == 'hata').sum())}")
    L.append(f"- v2 keşif (BH): {int(cikti.v2_test.str.contains('kesif=True', na=False).sum())}; sağlamlık satırı: {int((cikti.v2_saglamlik != '').sum())} "
             f"(saglam=True {int(cikti.v2_saglamlik.str.contains('saglam=True', na=False).sum())}); sete girdi: {int((cikti.v2_set == 'evet').sum())}; "
             f"paper_v2: {int((cikti.paper_v2 == 'evet').sum())}; canlı: {int((cikti.canli_kadro == 'canli').sum())}; paper(hma/lube dahil): {int((cikti.canli_kadro == 'paper').sum())}")
    adil = cikti[cikti.durum_onerisi.str.startswith("B")].adil_test_onerisi
    L.append("\n### adil_test_onerisi etiket sayıları (B satırlarında; bir satır birden çok etiket taşıyabilir)\n")
    for t in ("evet", "zayif_temsilci", "yalniz_tek_TF", "yalniz_varsayilan_ayar", "yapisal_kapi", "kisa_veri"):
        L.append(f"- {t}: {int(adil.map(lambda s: t in str(s).split(';')).sum())}")
    L.append(f"- hiç etiket almayan B: {int((adil == '').sum())}")
    L.append("\n## 2. Ayarlar (G0_ayarlar.csv)\n")
    L.append(f"- Satır: {len(ay)} (kart {int(ay.ayar_id.str.startswith('kart:').sum())}, dis {int(ay.ayar_id.str.startswith('dis:').sum())}, d11j {int(ay.ayar_id.str.startswith('d11j:').sum())}, d12b {int(ay.ayar_id.str.startswith('d12b:').sum())})")
    for (a, b), n in ay.groupby(["v1_aday_havuzunda", "kosuldu_mu"]).size().items():
        L.append(f"- v1_aday_havuzunda={a}, kosuldu_mu={b}: {n}")
    L.append(f"- v1_en_sik_ayar_mi=evet: {int((ay.v1_en_sik_ayar_mi == 'evet').sum())}; v2_secilen_ayar_mi=evet: {int((ay.v2_secilen_ayar_mi == 'evet').sum())}")
    L.append("")
    L.append("## 3. Öz kontrol: rastgele 10 satırın kaynağa geri izlenmesi (tohum 20261113)\n")
    for ad, dur, asm, kont in ornek_izle(cikti):
        L.append(f"- `{ad}` → {dur}/{asm}: " + "; ".join(kont))
    L.append("")
    sabit_yol = Path(__file__).with_name("g0_notlar_sabit.md")
    if sabit_yol.exists():
        L.append(sabit_yol.read_text(encoding="utf-8"))
    (ARA / "G0_NOTLAR.md").write_text("\n".join(L), encoding="utf-8")
    print("G0_NOTLAR.md yazıldı")


if __name__ == "__main__":
    cikti, ctx = main()
    ay = ayarlar(cikti, ctx)
    notlar(cikti, ay, ctx)
