"""Paper motoru için strateji tanımları ve bar-kapanışı sinyalleri.

Sinyal mantığı backtesttekiyle AYNI strateji sınıflarıdır (`motor.strateji` / `motor.portfoy.stratejiler`); yeniden yazılmadı.
Fark yalnız girdidir: backtest tüm seriyi bir kerede verir, paper her bar kapanışında YALNIZ o ana kadarki mumları verir
(`gecmis[:t]`) ve son satırı alır. Böylece lookahead yapısal olarak imkânsızdır; gelecekten bilgi kullanan (repaint eden) bir
strateji varsa tekrar-modu testi backtest ile farkı gösterir.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import final_set
from motor.arastirma import wf_portfoy as wfp
from motor.arastirma import wf_tarama as wf
from motor.backtest.motor import CikisYokHatasi, MESAJ_CIKIS_YOK
from motor.canli import giris_izi as gi
from motor.canli.paper_motor import Birim, PKol
from motor.strateji import funding as fnd
from motor.strateji import gostergeler as gst
from motor.strateji.temel import SINYAL_SUTUNLARI
from motor.veri.depo import aralik_suresi

KOK = Path(__file__).resolve().parents[2]
GUNCEL_AYAR_CSV = KOK / "sonuclar" / "final" / "guncel_ayarlar.csv"


@dataclass
class StratejiTanim:
    kimlik: str
    ajan: str
    kol: str                       # tek_grafik | portfoy
    strateji_ad: str
    sembol: str
    tf: str
    ayar: str                      # etiket (örn. 'izgara:{...}', 'csv:4', 'varsayilan')
    nesne: object                  # Strateji | PortfoyStratejisi
    grup: str
    grup_payi: Decimal
    evren: tuple = ()              # portföy: veri sembolleri (gerekli_semboller)
    sonraki_yenileme: Optional[str] = None
    veri_yok: str = ""             # doluysa: neden (strateji çalıştırılmaz)
    ayar_dosyasi: str = ""         # ayarın geldiği dosya (işlem kaydında `ayar_surumu.set_dosyasi`)

    @property
    def veri_semboller(self) -> list:
        return [self.sembol] if self.kol == "tek_grafik" else list(self.evren)


def ayar_nesnesi(s: dict, ayar: str):
    """final_set satırı + ayar etiketi -> strateji nesnesi (etiket, araştırma katmanının aday listesinde aranır)."""
    if s["kol"] == "portfoy":
        adaylar, _ = wfp.aday_listesi(s["strateji"], tuple(s["evren_semboller"]), True)
        d = dict(adaylar)
        if ayar not in d:
            raise KeyError(f"{s['kimlik']}: ayar aday listesinde yok: {ayar}")
        return d[ayar], tuple(wfp.gerekli_semboller(d[ayar], tuple(s["evren_semboller"])))
    adaylar, _ = wf.aday_listesi(s["strateji"], True)
    d = dict(adaylar)
    if ayar not in d:
        raise KeyError(f"{s['kimlik']}: ayar aday listesinde yok: {ayar}")
    return d[ayar], ()


def tanimlari_yukle(set_: Optional[dict] = None, ayar_kaynagi: str = "guncel", csv_yolu: Path = GUNCEL_AYAR_CSV) -> list:
    """final_set.json + ayar. ayar_kaynagi: 'guncel' (sonuclar/final/guncel_ayarlar.csv) | 'kilit' (kilit testindeki ayar)."""
    set_ = set_ or final_set.yukle()
    csv = pd.read_csv(csv_yolu).set_index("kimlik") if ayar_kaynagi == "guncel" else None
    kol_payi = set_["risk"]["kol_paylari"]
    out = []
    for s in set_["stratejiler"]:
        if ayar_kaynagi == "guncel":
            if csv.loc[s["kimlik"], "ayar"] != csv.loc[s["kimlik"], "ayar"] or not str(csv.loc[s["kimlik"], "ayar"]):
                raise ValueError(f"{s['kimlik']}: guncel_ayarlar.csv'de ayar boş (hata: {csv.loc[s['kimlik'], 'hata']})")
            ayar = str(csv.loc[s["kimlik"], "ayar"])
            yen = str(csv.loc[s["kimlik"], "sonraki_yenileme"])
        else:
            ayar, yen = s["kilit_testi_ayari"], None
        nesne, evren = ayar_nesnesi(s, ayar)
        if s["kol"] == "tek_grafik":
            grup, gp = "tek_grafik", Decimal(repr(kol_payi["tek_grafik"]))
        else:
            grup = s["kimlik"]
            gp = Decimal(repr(kol_payi["portfoy"])) / Decimal(sum(1 for x in set_["stratejiler"] if x["kol"] == "portfoy"))
        out.append(StratejiTanim(s["kimlik"], s["ajan"], s["kol"], s["strateji"], s["sembol"], s["tf"], ayar, nesne,
                                 grup, gp, evren, yen, ayar_dosyasi=("guncel_ayarlar.csv" if ayar_kaynagi == "guncel" else "final_set.json (kilit_testi_ayari)")))
    return out


# ---------------------------------------------------------------------------- birim kurma
def tek_kol(t: StratejiTanim) -> PKol:
    st = t.nesne
    ca = st.cikis_ayarlari
    if not (st.cikis_var_mi() or ca.atr_iz_suren_k or ca.zaman_cikisi_mum or ca.sabit_r_hedefi):
        raise CikisYokHatasi(f"{st.ad}/{t.sembol}: {MESAJ_CIKIS_YOK}")
    return PKol(kimlik=t.kimlik, sembol=t.sembol, mod="sinyal", strateji_ad=st.ad, cikis_ayarlari=ca,
                grup=t.grup, grup_payi=t.grup_payi, sk=t.kimlik)


def birim_kur(t: StratejiTanim, pf_sutunlar: Optional[list] = None) -> Birim:
    aralik = aralik_suresi(t.tf)
    if t.kol == "tek_grafik":
        return Birim(t.kimlik, t.tf, aralik, [tek_kol(t)], [t.sembol])
    kollar = [PKol(kimlik=f"{t.kimlik}#{s}", sembol=s, mod="agirlik", strateji_ad=t.strateji_ad,
                   grup=t.grup, grup_payi=t.grup_payi, sk=t.kimlik) for s in pf_sutunlar]
    return Birim(t.kimlik, t.tf, aralik, kollar, list(t.evren))


# ---------------------------------------------------------------------------- bar kapanışı kararları
def tek_karar(t: StratejiTanim, mumlar: pd.DataFrame, fund: Optional[pd.DataFrame]) -> dict:
    """mumlar: <= t. -> {kol_kimligi: karar}. Backtest `backtest()` ile aynı sinyal sütunları/yönlü çıkış/ATR."""
    st = t.nesne
    girdi = fnd.stratejiye_hazirla(st, mumlar, fund, t.sembol, t.tf)
    sig = st.sinyaller(girdi)
    if not sig.index.equals(mumlar.index):
        raise ValueError("sinyaller() mumlarla aynı indeksi dönmeli")
    eksik = [c for c in SINYAL_SUTUNLARI if c not in sig.columns]
    if eksik:
        raise ValueError(f"Sinyal sütunları eksik: {eksik}")
    r = sig.iloc[-1]
    yon = int(r["yon"])
    if yon != 0 and pd.isna(r["stop"]):
        raise ValueError("Giriş sinyali olan her satırda stop zorunlu")
    cikis = bool(r["cikis"])
    cl = cikis or (bool(r["cikis_long"]) if "cikis_long" in sig.columns and not pd.isna(r["cikis_long"]) else False)
    cs = cikis or (bool(r["cikis_short"]) if "cikis_short" in sig.columns and not pd.isna(r["cikis_short"]) else False)
    zc = float(r["zaman_cikisi_mum"]) if "zaman_cikisi_mum" in sig.columns else float("nan")
    ca = st.cikis_ayarlari
    atr = (float(gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], ca.atr_periyot).iloc[-1])
           if ca.atr_iz_suren_k else float("nan"))
    karar = {"yon": yon, "stop": float(r["stop"]), "hedef": float(r["hedef"]), "cikis_l": cl, "cikis_s": cs, "zc": zc, "atr": atr}
    if yon != 0:       # sürüm izi + giriş gerekçesi: yalnız karar anındaki (mumlar <= t) değerlerden; motor bunları pozisyona bağlar
        karar["ayar_surumu"] = gi.ayar_surumu(t.strateji_ad, t.ayar, t.ayar_dosyasi)
        karar["gerekce"] = gi.gerekce_tek(t, mumlar, sig, yon, r["stop"], r["hedef"])
    return {t.kimlik: karar}


def pf_karar(t: StratejiTanim, veriler: dict) -> tuple:
    """veriler: {sembol: mumlar<=t}. -> (kararlar {kol_kimligi: {w, stop}}, sutunlar). Eksenin SON satırı alınır."""
    h, s = t.nesne.sinyaller(veriler)
    son = h.index[-1]
    k = {}
    for sembol in h.columns:
        w = float(h[sembol].iloc[-1])
        sp = float(s[sembol].iloc[-1]) if sembol in s.columns else float("nan")
        k[f"{t.kimlik}#{sembol}"] = {"w": w, "stop": sp}
        if w != 0 and w == w:
            k[f"{t.kimlik}#{sembol}"]["ayar_surumu"] = gi.ayar_surumu(t.strateji_ad, t.ayar, t.ayar_dosyasi)
            k[f"{t.kimlik}#{sembol}"]["gerekce"] = gi.gerekce_agirlik(t, sembol, son, veriler[sembol]["kapanis"].iloc[-1], w, sp)
    return k, list(h.columns), son
