"""v2 Aşama 5 — set kurma + boyut + mühür (ON_KAYIT_V2 6.2, 6.3; P1-5). Yalnız SAĞLAM KEŞİFLERDEN (saglamlik.csv liste=saglam_kesif).

1. Korelasyon kümesi: sağlam keşiflerin haftalık MTM getirisi (Pazar kapanışlı UTC; tek kasa, x1; satırın ilk aktif gününden itibaren);
   ortalama bağlantı, uzaklık 1-ρ, kesim KUME_UZAKLIK_KESIM (ρ > 0.5 aynı küme; `secim.kumeler`). Ortak hafta < KUME_MIN_ORTAK_HAFTA
   ya da ölçülemeyen çift ρ = 0 (uzaklık 1) sayılır = ayrı küme eğilimli.
2. Sıra: nihai K2 p küçük önce; eşitlikte maliyet x2 PF(R) büyük (portföy satırında x2 günlük Sharpe); sonra alfabetik (strateji, tf).
3. Açgözlü, STİL başına: aday alınır eğer (a) stilde < STIL_BASINA_MAKS seçili, (b) aynı korelasyon kümesinden seçili yok (küme küresel:
   stiller arası da), (c) aynı stilde aynı ana etiketten seçili yok.
4. Ağırlık: eşit risk (işlem başı s x %1), tek kasa, sert limitler aynen. 5. Boyut s: S_IZGARA'nın, s=1 tek kasa günlük MTM getirisinin
   s ile çarpımı + durağan blok bootstrap (blok BOOT_BLOK_GUN, BOOT_CEKIM çekim, tohum `boot`) %95'lik maks düşüşü <= DD_MAKS olan EN BÜYÜĞÜ;
   hiçbiri uymazsa set kurulmaz (sonuç 0). Yukarı ölçek yok. 6. Sağlam keşfi olmayan stil boş; hiç yoksa sonuç "0 strateji" (holdout açılmaz).
Portföy (pf__) satırı sete girerse günlük getirisi ayrı kol olarak eklenir (toplamsal; s ile doğrusal ölçeklenir).
Çıktı: set.csv, set_ozet.json, set_muhru.json (holdout.muhur_yaz). Mühür varsa aşama çalışmaz.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import ham as hm, kasa, sabit, spa


# ============================================================================ saf parçalar
def haftalik_seri(gunluk: pd.Series) -> pd.Series:
    """Günlük MTM getirisi -> Pazar kapanışlı haftalık bileşik getiri; satırın ilk aktif (sıfır olmayan) gününden önceki günler atılır."""
    nz = np.flatnonzero(gunluk.to_numpy(dtype=float) != 0.0)
    if not len(nz):
        return pd.Series(dtype=float)
    return kasa.haftalik(gunluk.iloc[nz[0]:])


def korelasyon_matrisi(haftalik: dict) -> pd.DataFrame:
    """Çiftli korelasyon (ortak hafta üzerinden). Ortak hafta < KUME_MIN_ORTAK_HAFTA ya da sabit seri -> NaN (ölçülemedi)."""
    k = sorted(haftalik)
    M = pd.DataFrame(np.nan, index=k, columns=k)
    for i, a in enumerate(k):
        M.loc[a, a] = 1.0
        for b in k[i + 1:]:
            ort = haftalik[a].index.intersection(haftalik[b].index)
            if len(ort) < sabit.KUME_MIN_ORTAK_HAFTA:
                continue
            x, y = haftalik[a].reindex(ort).to_numpy(dtype=float), haftalik[b].reindex(ort).to_numpy(dtype=float)
            if x.std() == 0 or y.std() == 0:
                continue
            M.loc[a, b] = M.loc[b, a] = float(np.corrcoef(x, y)[0, 1])
    return M


def kumeler(haftalik: dict) -> dict:
    """{anahtar: küme_no}. Ortalama bağlantı: kümeler arası ortalama ρ > 1 - KUME_UZAKLIK_KESIM ise birleşir; NaN ρ = 0."""
    if not haftalik:
        return {}
    return secim.kumeler(korelasyon_matrisi(haftalik), 1.0 - sabit.KUME_UZAKLIK_KESIM)


def sira_anahtari(a: dict) -> tuple:
    pf = a.get("pf_x2")
    pf = -math.inf if pf is None or (isinstance(pf, float) and math.isnan(pf)) else float(pf)
    return (float(a["p"]), -pf, a["strateji"], a["tf"])


def acgozlu_sec(adaylar: list, kume: dict) -> tuple:
    """adaylar: [{strateji, tf, stil_v2, etiket, p, pf_x2}]. kume: {'strateji|tf': küme_no}. -> (secilen, atlanan{'anahtar': neden})."""
    secilen, atlanan = [], {}
    kume_dolu, etiket_dolu, say = set(), set(), {}
    for a in sorted(adaylar, key=sira_anahtari):
        k = f"{a['strateji']}|{a['tf']}"
        stil, kn = a["stil_v2"], kume.get(k)
        if say.get(stil, 0) >= sabit.STIL_BASINA_MAKS:
            atlanan[k] = "stilde dolu"
        elif kn is not None and kn in kume_dolu:
            atlanan[k] = f"küme {kn} zaten seçili"
        elif (stil, a["etiket"]) in etiket_dolu:
            atlanan[k] = f"aynı stilde etiket '{a['etiket']}' zaten seçili"
        else:
            secilen.append(a)
            say[stil] = say.get(stil, 0) + 1
            kume_dolu.add(kn)
            etiket_dolu.add((stil, a["etiket"]))
    return secilen, atlanan


def maks_dusus_dagilimi(getiri: np.ndarray, olcekler, tohum: int, ort_blok: float = sabit.BOOT_BLOK_GUN,
                        n_cekim: int = sabit.BOOT_CEKIM) -> dict:
    """{s: maks düşüş dizisi (n_cekim,)}: aynı bootstrap indeksleriyle her ölçek için s x getiri bileşik özsermayesinin maks düşüşü."""
    x = np.asarray(getiri, dtype=float)
    n = len(x)
    rng = np.random.default_rng(tohum)
    sonuc = {s: [] for s in olcekler}
    for idx in spa.durgan_indeks(n, ort_blok, n_cekim, rng, parca=sabit.BOOT_PARCA):
        ornek = x[idx]
        for s in olcekler:
            ozs = np.cumprod(1.0 + s * ornek, axis=1)
            zirve = np.maximum(np.maximum.accumulate(ozs, axis=1), 1.0)
            sonuc[s].append(((zirve - ozs) / zirve).max(axis=1))
    return {s: np.concatenate(v) for s, v in sonuc.items()}


def boyut_sec(getiri: np.ndarray, tohum: int, olcekler=sabit.S_IZGARA) -> dict:
    """-> {'s': en büyük uygun ölçek | None, 'tablo': {s: %95 maks düşüş}}. Koşul: percentile <= DD_MAKS (sınır dahil)."""
    dagilim = maks_dusus_dagilimi(getiri, olcekler, tohum)
    tablo = {s: float(np.percentile(v, sabit.DD_YUZDELIK)) for s, v in dagilim.items()}
    uygun = [s for s in olcekler if tablo[s] <= sabit.DD_MAKS]
    return {"s": (max(uygun) if uygun else None), "tablo": tablo}


# ============================================================================ set günlük getirisi (s = 1)
def set_gunluk_getiri(cikti: Path, secilen: list, tablo_yolu, tablo_hash: str) -> pd.Series:
    """Setin s = 1 tek kasa oynatmasının günlük MTM getirisi (tek-grafik stratejiler tek kasada; portföy kolları toplamsal)."""
    cikti = Path(cikti)
    tek = [a for a in secilen if a["stil_v2"] != "portfoy"]
    pf = [a for a in secilen if a["stil_v2"] == "portfoy"]
    ham, sira, tf_of, bilgiler = {}, {}, {}, []
    for a in tek:
        evren_t = sabit.evren_listesi(a["evren"])
        h, b = hm.ham_yukle(cikti, 1.0, a["strateji"], a["tf"], evren_t, tablo_hash)
        if b["hatali"] or not h:
            raise RuntimeError(f"{a['strateji']}: ham sonuç kullanılamaz")
        ham[a["strateji"]], sira[a["strateji"]], tf_of[a["strateji"]] = h, evren_t, a["tf"]
        bilgiler.append(b)
    parcalar = []
    if tek:
        analiz = [kasa.donem_sinirlari(b) for b in bilgiler]
        bas, bit = max(x[0] for x in analiz), max(x[1] for x in analiz)         # ortak pencere: hepsinin etkin olduğu dönem
        oos = kasa.oos_birlestir(ham, sira, bas, 1.0, tablo_yolu)
        if not len(oos):
            raise RuntimeError("sette analiz döneminde işlem yok")
        tablo, res = kasa.oynat(oos, bas, bit)
        parcalar.append(kasa.gunluk_mtm_getiri(oos, tablo, res, kasa.MtmOnbellek(cikti, tf_of), bas, bit))
    for a in pf:
        parcalar.append(kasa.satir_gunluk(cikti, a, tablo_yolu, tablo_hash))
    gun = parcalar[0].index
    for p in parcalar[1:]:
        gun = gun.intersection(p.index)
    toplam = sum(p.reindex(gun).fillna(0.0) for p in parcalar)
    return pd.Series(toplam, index=gun)


# ============================================================================ aşama
def saglamlik_oku(cikti: Path) -> pd.DataFrame:
    cikti = Path(cikti)
    yol, oz = cikti / "saglamlik.csv", cikti / "saglamlik_ozet.json"
    if not yol.exists() or not oz.exists():
        raise RuntimeError(f"saglamlik.csv / saglamlik_ozet.json yok: önce saglamlik aşaması ({cikti})")
    if json.loads(oz.read_text()).get("saglamlik_csv_sha256") != kasa.sha256(yol):
        raise RuntimeError("saglamlik.csv saglamlik_ozet.json'daki sha256 ile uyuşmuyor")
    return pd.read_csv(yol)


def set_asamasi(cikti: Path = None, butce_sn: Optional[float] = None, havuz_yolu=None, muhur_yolu=None, ilerleme: bool = True) -> dict:
    import time
    from motor.arastirma.v2 import holdout, maliyet
    cikti = Path(cikti or sabit.CIKTI)
    kasa.yazma_engeli(cikti)
    hm.havuz_muhru_dogrula(havuz_yolu, muhur_yolu)
    sg = saglamlik_oku(cikti)
    tablo = maliyet.tablo_yolu(cikti)
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    saglam = sg[sg["liste"] == "saglam_kesif"]
    el = pd.read_csv(cikti / "eleme.csv").set_index(["strateji", "tf"])
    adaylar = [{**{k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.items()},
                "ayar": ("varsayilan" if r["stil_v2"] == "portfoy" else str(el.loc[(r["strateji"], r["tf"]), "ayar"]))}
               for r in saglam.to_dict("records")]
    ozet = {"saglam_kesif": len(adaylar), "kume": {}, "secilen": [], "atlanan": {}, "s": None, "s_tablo": {}, "sonuc": "0 strateji"}
    son = time.time() + butce_sn if butce_sn else None
    if adaylar:
        haftalik = {}
        for a in adaylar:
            if son is not None and time.time() > son:
                o = {"bekleyen": 1, "neden": "bütçe doldu (günlük MTM serisi hesaplanıyor)"}
                if ilerleme:
                    print(f"[v2 set] TAMAMLANMADI: {o}", flush=True)
                return o
            haftalik[f"{a['strateji']}|{a['tf']}"] = haftalik_seri(kasa.satir_gunluk(cikti, a, tablo, tablo_hash))
        kume = kumeler(haftalik)
        secilen, atlanan = acgozlu_sec(adaylar, kume)
        ozet.update(kume={k: int(v) for k, v in kume.items()}, atlanan=atlanan)
        if secilen:
            g = set_gunluk_getiri(cikti, secilen, tablo, tablo_hash)
            b = boyut_sec(g.to_numpy(dtype=float), sabit.satir_tohumu("set", "1d", "boot"))
            ozet.update(s=b["s"], s_tablo={str(k): v for k, v in b["tablo"].items()})
            if b["s"] is not None:
                for i, a in enumerate(secilen):
                    a["kume"] = int(kume[f"{a['strateji']}|{a['tf']}"])
                    a["sira"] = i + 1
                ozet.update(secilen=secilen, sonuc=f"{len(secilen)} strateji")
        else:
            ozet["neden"] = "açgözlü seçim boş"
    cols = ["strateji", "tf", "stil_v2", "evren", "ayar", "etiket", "alt_etiket", "kilit_gorulmus", "p", "pf_x2", "kume", "sira"]
    df = pd.DataFrame(ozet["secilen"], columns=cols) if ozet["secilen"] else pd.DataFrame(columns=cols)
    yol = cikti / "set.csv"
    gecici = yol.with_suffix(".tmp")
    df.to_csv(gecici, index=False)
    gecici.replace(yol)
    ozet["set_csv_sha256"] = kasa.sha256(yol)
    kasa.atomik_yaz_json(cikti / "set_ozet.json", ozet)
    muhur = holdout.muhur_yaz(cikti, havuz_yolu, ozet)
    ozet["muhur"] = str(cikti / sabit.SET_MUHRU)
    if ilerleme:
        print(f"[v2 set] sonuç: {ozet['sonuc']}; s={ozet['s']}; mühür yazıldı ({len(muhur['dosyalar'])} dosya hash'i)", flush=True)
    return ozet
