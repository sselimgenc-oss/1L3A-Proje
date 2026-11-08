"""Evren holdout aşaması (ON_KAYIT Güncelleme 5.1): son 12 ay (2025-11-08 -> veri sonu), BİR KEZ.

Akış: secim aşaması iyi/iyiye yakın listelerini yazar ve mühürler (`liste_muhru.json`: dosya sha256'ları + maliyet tablosu
hash'i). Holdout aşaması önce mührü doğrular (liste değişmişse HoldoutHatasi), sonra listedeki her stratejiyi WF'nin
geliştirme dönemindeki SON seçilen ayarıyla holdout'ta tek koşuda sınar. Kapı: evren net > 0 ve PF(R) >= 1.1 ->
"dogrulanmis", aksi "holdout_ta_kaldi". Holdout sonucuna göre ayar/eşik/liste DEĞİŞTİRİLMEZ.

Bir kerelik: `holdout/holdout_gunlugu.jsonl` (yalnız ekler). Herhangi bir "basladi" kaydı varsa yeniden koşu HoldoutTekrarHatasi
verir; zorla=True + boş olmayan gerekçe ile açılır ve günlüğe yazılır. Holdout verisi yalnız burada okunur (donem="holdout").
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from motor.arastirma import evren_maliyet, saglamlik, tarama
from motor.arastirma import wf_evren as we
from motor.backtest.motor import backtest
from motor.strateji import funding

MUHUR = "liste_muhru.json"
GUNLUK = "holdout/holdout_gunlugu.jsonl"
MUHUR_DOSYALARI = ("iyi_liste.csv", "iyiye_yakin_liste.csv", "secim.csv")


class HoldoutHatasi(RuntimeError):
    """Liste mührü bozuk / eksik: holdout reddedilir."""


class HoldoutTekrarHatasi(HoldoutHatasi):
    """Holdout daha önce başlatılmış (bir kerelik)."""


def _sha(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest() if Path(yol).exists() else ""


def gunluk_oku(cikti: Path) -> list:
    yol = Path(cikti) / GUNLUK
    if not yol.exists():
        return []
    return [json.loads(x) for x in yol.read_text(encoding="utf-8").splitlines() if x.strip()]


def holdout_baslamis_mi(cikti: Path) -> bool:
    return any(k.get("olay") == "basladi" for k in gunluk_oku(cikti))


def muhur_yaz(cikti: Path) -> dict:
    """secim aşaması çıktıları yazıldıktan sonra çağrılır. Holdout başlamışsa listeler artık değiştirilemez."""
    cikti = Path(cikti)
    if holdout_baslamis_mi(cikti):
        raise HoldoutHatasi("holdout daha önce başlatıldı: iyi/iyiye yakın listeleri ve mühür değiştirilemez")
    m = {"zaman": datetime.now(timezone.utc).isoformat(), "dosyalar": {f: _sha(cikti / f) for f in MUHUR_DOSYALARI},
         "maliyet_hash": evren_maliyet.tablo_hash()}
    (cikti / MUHUR).write_text(json.dumps(m, ensure_ascii=False, indent=1))
    return m


def muhur_kontrol(cikti: Path) -> dict:
    cikti = Path(cikti)
    yol = cikti / MUHUR
    if not yol.exists():
        raise HoldoutHatasi(f"{MUHUR} yok: önce secim aşaması listeleri yazıp mühürlemeli")
    m = json.loads(yol.read_text())
    for f, h in m["dosyalar"].items():
        if _sha(cikti / f) != h:
            raise HoldoutHatasi(f"liste değişmiş: {f} (mühürlü hash ile uyuşmuyor); holdout reddedildi")
    if m.get("maliyet_hash") != evren_maliyet.tablo_hash():
        raise HoldoutHatasi("maliyet tablosu mühürden sonra değişmiş; holdout reddedildi")
    return m


def son_secilen_ayar(secimler_json: str) -> Optional[str]:
    """WF'nin geliştirme dönemindeki SON seçilen ayarı (ayar seçilen son pencere)."""
    for s in reversed(json.loads(secimler_json)):
        if s.get("secilen") is not None and s.get("ayar"):
            return s["ayar"]
    return None


def holdout_kos(ad: str, tf: str, stil: str, etiket: str, dislanan=(), ayar=None) -> dict:
    """Tek strateji, tek ayar, evrende holdout (girişi >= HOLDOUT_BAS). veri_ayarla(..., 'holdout') kurulu olmalı."""
    evren = [s for s in we.evren_stil(stil) if s not in set(dislanan)]
    st = saglamlik.ayar_coz(ad, etiket)
    parcalar, n_veri = [], 0
    for sembol in evren:
        try:
            mumlar, fund = we._veri(sembol, tf)
        except (FileNotFoundError, ValueError):
            continue
        if not len(mumlar) or mumlar.index[-1] < we.HOLDOUT_BAS:
            continue
        n_veri += 1
        kural = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
        try:
            t = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st,
                         evren_maliyet.maliyet_ayarlari(sembol, kural, 1.0), fund).islemler
        except Exception:  # noqa: BLE001  (K-L)
            continue
        if not len(t):
            continue
        o = we.islem_ozet(t, 0)
        o = o[pd.DatetimeIndex(o["giris_zamani"]) >= we.HOLDOUT_BAS].copy()
        if len(o):
            o["sembol"] = sembol
            o["son_mum"] = mumlar.index[-1]
            parcalar.append(o)
    satir = {"n_enstruman_veri": n_veri}
    if not parcalar:
        satir.update(islem_sayisi=0, net_getiri=0.0, profit_factor=math.nan, nedenler="holdout'ta işlem yok")
        return satir
    oos = pd.concat(parcalar, ignore_index=True)
    bit = oos["son_mum"].max() + pd.Timedelta(1, "ns")
    oos, atilan = we.sembol_cakismasini_ele(oos.drop(columns="son_mum"))
    m = we.kasa_metrikleri(we.oynatma_tablosu(oos, tuple(evren)), we.HOLDOUT_BAS, bit, ayar)
    for kx in ("kabul", "pnl", "getiri_serisi", "sinif_net", "enstruman_net", "enstruman_adet"):
        m.pop(kx, None)
    satir.update(m)
    satir.update(holdout_bit=str(bit), cakisma_atilan=atilan)
    return satir


def kapi(m: dict) -> bool:
    pf = m.get("profit_factor")
    return (m.get("islem_sayisi", 0) or 0) > 0 and (m.get("net_getiri", 0.0) or 0.0) > 0 \
        and pf is not None and not (isinstance(pf, float) and math.isnan(pf)) and pf >= we.OLCUT["holdout_pf"]


def holdout_asamasi(cikti: Path, donem: str = "2017_gelistirme", veri_dizini=None, zorla: bool = False,
                    gerekce: str = "", ayar=None) -> pd.DataFrame:
    cikti = Path(cikti)
    muhur = muhur_kontrol(cikti)                                     # liste değişmişse HoldoutHatasi
    (cikti / "holdout").mkdir(parents=True, exist_ok=True)
    if holdout_baslamis_mi(cikti):
        if not zorla:
            raise HoldoutTekrarHatasi("holdout bir kerelik ve daha önce başlatıldı; tekrar için zorla=True ve gerekçe gerekir "
                                      "(günlüğe yazılır, yöntem ihlali olarak raporlanır)")
        if not isinstance(gerekce, str) or not gerekce.strip():
            raise HoldoutTekrarHatasi("zorla tekrar için boş olmayan gerekçe zorunlu")
    elif zorla:
        raise HoldoutTekrarHatasi("zorla bayrağı yalnız daha önce koşulmuş holdout için anlamlı; ilk koşuda kullanılmaz")

    def yaz(k):
        with open(cikti / GUNLUK, "a", encoding="utf-8") as f:
            f.write(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), **k}, ensure_ascii=False) + "\n")
    yaz({"olay": "basladi", "zorla": bool(zorla), "gerekce": gerekce, "muhur": muhur["dosyalar"], "donem": donem})
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    kayitlar = []
    for liste, dosya in (("iyi", "iyi_liste.csv"), ("iyiye_yakin", "iyiye_yakin_liste.csv")):
        f = cikti / dosya
        if f.exists() and f.stat().st_size > 5:
            for r in pd.read_csv(f).to_dict("records"):
                kayitlar.append((liste, r["strateji"], r["tf"], r["stil"]))
    we.veri_ayarla(veri_dizini, "holdout")
    satirlar = []
    for liste, ad, tf, stil in kayitlar:
        w = wf[(wf["strateji"] == ad) & (wf["tf"] == tf)].iloc[0]
        etiket = son_secilen_ayar(w["secimler"])
        satir = {"liste": liste, "strateji": ad, "tf": tf, "stil": stil, "ayar": etiket or "", "hata": "",
                 "gelistirme_pf": w.get("profit_factor"), "gelistirme_sharpe": w.get("sharpe")}
        if etiket is None:
            satir.update(durum="holdout_ta_kaldi", nedenler="WF'de seçilen ayar yok")
        else:
            dis = set(x for col in ("kisa_gecmis", "disarida", "hatali_sembol") for x in str(w.get(col) or "").split(",") if x)
            try:
                if stil == "portfoy":
                    from motor.arastirma import wf_evren_portfoy
                    satir.update(wf_evren_portfoy.holdout_kos(ad, etiket, tf, dis, ayar))
                else:
                    satir.update(holdout_kos(ad, tf, stil, etiket, dis, ayar))
                satir["durum"] = "dogrulanmis" if kapi(satir) else "holdout_ta_kaldi"
            except Exception as e:  # noqa: BLE001
                satir.update(hata=f"{type(e).__name__}: {e}"[:300], durum="holdout_ta_kaldi", nedenler="hata")
        satirlar.append(satir)
    df = pd.DataFrame(satirlar)
    df.to_csv(cikti / "holdout" / "holdout.csv", index=False)
    yaz({"olay": "bitti", "n": len(df), "dogrulanmis": int((df["durum"] == "dogrulanmis").sum()) if len(df) else 0})
    return df
