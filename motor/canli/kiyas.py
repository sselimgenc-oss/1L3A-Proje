"""Kıyas serileri (pano öncelik 5b): aynı dönemde paper getirisi ↔ BTC al-tut, S&P 500 al-tut (DK_SPX), mevduat. Hesap BURADA (motor tarafı).

Hepsi AYNI tabana normalize birikimli getiridir: gün 0 = `baz_gun` (özsermaye geçmişinin başlangıç noktası) kesim anı = 1.0.
Fiyat kaynağı: yerel mum arşivi (`veri/mumlar/<sembol>/1h|5m.parquet`, kilit koruması BURADA geçerli değildir: paper dönemi araştırma verisi değildir).
Gün değeri = o günün kesim anına (gün sonu, yerel gün kesimi; bitmemiş gün için `simdi`) kadar KAPANMIŞ son mumun kapanışı (mum kapanışı = açılış + süre;
kapanmamış mum kullanılmaz: lookahead yok). Seans dışı günlerde (hafta sonu/tatil) son kapanış taşınır; son mum kesimden `MAKS_BOSLUK_GUN` günden eskiyse
o gün için değer null + neden (bayat veriyle sahte düz çizgi çizilmez).
TABAN NOTU: özsermaye geçmişinin başlangıç noktası ilk günden bir önceki gündür (başlangıç sermayesi); kıyaslar da aynı gün sonuna normalize edilir. Paper'ın gerçek
başlangıç saati ilk günün içindedir: ilk günün kıyas getirisi başlangıçtan önceki saatlerin hareketini de içerebilir (kaba karşılaştırma).
MEVDUAT: oran projede tanımlı DEĞİL. `stratejiler/kiyas_ayar.json` -> `mevduat_yillik_oran` (kesir: 0.40 = yıllık %40, bileşik) null ise seri çizilmez
ve `kullanici_girmeli: true` yazılır; oran uydurulmaz.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from motor.canli import durum as d
from motor.veri.depo import aralik_suresi, mum_yolu

KOK = Path(__file__).resolve().parents[2]
VERI_DIZINI = KOK / "veri" / "mumlar"
AYAR_YOLU = KOK / "stratejiler" / "kiyas_ayar.json"
TF_ONCELIK = ("1h", "5m")
MAKS_BOSLUK_GUN = 5                          # hafta sonu + tatil payı; fazlası "veri güncel değil"
SERILER = (("btc", "BTC al-tut", "BTCUSDT"), ("spx", "S&P 500 al-tut", "DK_SPX"))
MEVDUAT_NEDEN = ("mevduat yıllık oranı projede tanımlı değil: kullanıcı oranı girmeli (stratejiler/kiyas_ayar.json -> mevduat_yillik_oran, "
                 "kesir: 0.40 = yıllık %40); girilene kadar seri çizilmez")


def ayar_oku(yol: Path = AYAR_YOLU) -> dict:
    """-> {'mevduat_yillik_oran': float|None}. Dosya yoksa oran None (varsayılan); bozuk/geçersiz değer ValueError (sessiz yutulmaz)."""
    if not Path(yol).exists():
        return {"mevduat_yillik_oran": None}
    ham = json.loads(Path(yol).read_text(encoding="utf-8"))
    oran = ham.get("mevduat_yillik_oran")
    if oran is not None and (isinstance(oran, bool) or not isinstance(oran, (int, float)) or not math.isfinite(oran) or oran <= -1):
        raise ValueError(f"{Path(yol).name}: mevduat_yillik_oran sonlu bir kesir olmalı (> -1) ya da null: {oran!r}")
    return {"mevduat_yillik_oran": None if oran is None else float(oran)}


def kapanislar(sembol: str, veri_dizini: Path = VERI_DIZINI) -> tuple:
    """-> (Series kapanış, indeks = mum KAPANIŞ zamanı UTC, 'tf') | (None, neden)."""
    for tf in TF_ONCELIK:
        yol = mum_yolu(sembol, tf, veri_dizini)
        if yol.exists():
            df = pd.read_parquet(yol, columns=["kapanis"])
            ix = pd.DatetimeIndex(df.index)
            ix = ix.tz_localize("UTC") if ix.tz is None else ix.tz_convert("UTC")
            return pd.Series(df["kapanis"].to_numpy(dtype=float), index=ix + aralik_suresi(tf)).sort_index(), tf
    return None, f"mum arşivi yok: {sembol} ({' / '.join(TF_ONCELIK)}); kaynak makinede indirilmeli"


def gun_sonu_utc(gun: str, tz: str) -> pd.Timestamp:
    """Yerel gün sonu (ertesi gün 00:00 yerel) -> UTC."""
    t = pd.Timestamp(date.fromisoformat(gun) + timedelta(days=1)).tz_localize(ZoneInfo(tz))
    return t.tz_convert("UTC")


def _son_kapanis(seri: pd.Series, kesim: pd.Timestamp):
    """kesim anına kadar kapanmış son mum -> (zaman, fiyat) | (None, None)."""
    i = seri.index.searchsorted(kesim, side="right") - 1
    return (seri.index[i], float(seri.iloc[i])) if i >= 0 else (None, None)


def fiyat_serisi(sembol: str, etiket: str, kesimler: list, gunler: list, veri_dizini: Path = VERI_DIZINI) -> dict:
    """kesimler[0] baz; gunler[i] kesimler[i] ile hizalı. -> kıyas seri kaydı."""
    kayit = {"kimlik": None, "etiket": etiket, "sembol": sembol, "kaynak": "yerel mum arşivi", "noktalar": [], "son_getiri": None, "neden": None}
    seri, tf = kapanislar(sembol, veri_dizini)
    if seri is None:
        kayit["neden"] = tf
        return kayit
    kayit["kaynak"] = f"yerel mum arşivi {sembol} {tf}"
    z0, p0 = _son_kapanis(seri, kesimler[0])
    if p0 is None or (kesimler[0] - z0) > pd.Timedelta(days=MAKS_BOSLUK_GUN):
        kayit["neden"] = (f"baz anında ({kesimler[0]:%Y-%m-%d %H:%M} UTC) güncel fiyat yok" + (f" (son mum {z0:%Y-%m-%d %H:%M} UTC)" if z0 is not None else ""))
        return kayit
    bayat, nok = [], []
    for g, k in zip(gunler, kesimler):
        z, p = _son_kapanis(seri, k)
        if p is None or (k - z) > pd.Timedelta(days=MAKS_BOSLUK_GUN):
            nok.append({"gun": g, "getiri": None})
            bayat.append(g)
        else:
            nok.append({"gun": g, "getiri": d.sayi(p / p0 - 1.0)})
    kayit["noktalar"] = nok
    kayit["son_getiri"] = next((x["getiri"] for x in reversed(nok) if x["getiri"] is not None), None)
    if bayat:
        kayit["neden"] = (f"{len(bayat)} gün için güncel fiyat yok (son mum {seri.index[-1]:%Y-%m-%d %H:%M} UTC; >{MAKS_BOSLUK_GUN} gün eski): "
                          f"{bayat[0]}" + (f" … {bayat[-1]}" if len(bayat) > 1 else "") + " null")
    return kayit


def mevduat_serisi(oran: Optional[float], kesimler: list, gunler: list) -> dict:
    kayit = {"kimlik": "mevduat", "etiket": "Mevduat", "sembol": None, "kaynak": "yapılandırma (stratejiler/kiyas_ayar.json)",
             "yillik_oran": oran, "kullanici_girmeli": oran is None, "noktalar": [], "son_getiri": None, "neden": None}
    if oran is None:
        kayit["neden"] = MEVDUAT_NEDEN
        return kayit
    nok = [{"gun": g, "getiri": d.sayi((1.0 + oran) ** ((k - kesimler[0]) / pd.Timedelta(days=365)) - 1.0)} for g, k in zip(gunler, kesimler)]
    kayit["noktalar"], kayit["son_getiri"] = nok, nok[-1]["getiri"]
    return kayit


def olustur(kaynak: str, zaman: str, simdi, baz_gun: str, gunler: list, paper_getiri: dict, gun_kesimi_tz: str, gun_kesimi_adi: str,
            veri_dizini: Path = VERI_DIZINI, ayar_yolu: Path = AYAR_YOLU) -> dict:
    """kiyas.json içeriği.
    baz_gun: gün 0; gunler: baz sonrası gün metinleri (sıralı); paper_getiri: {gun: birikimli net getiri} (baz gün 0.0 olarak eklenir);
    gun_kesimi_tz: 'Europe/Istanbul' | 'UTC'; simdi: bitmemiş gün için kesim üst sınırı."""
    simdi = pd.Timestamp(simdi)
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    tum = [baz_gun] + [g for g in gunler if g != baz_gun]
    kesimler = [min(gun_sonu_utc(g, gun_kesimi_tz), simdi) for g in tum]
    kesimler[0] = gun_sonu_utc(baz_gun, gun_kesimi_tz)
    paper = {"kimlik": "paper", "etiket": "Paper (set)", "sembol": None, "kaynak": "ozsermaye_gecmisi.json",
             "noktalar": [{"gun": g, "getiri": d.sayi(0.0 if g == baz_gun else paper_getiri.get(g))} for g in tum], "neden": None}
    paper["son_getiri"] = next((x["getiri"] for x in reversed(paper["noktalar"]) if x["getiri"] is not None), None)
    seriler = [paper]
    for kimlik, etiket, sembol in SERILER:
        s = fiyat_serisi(sembol, etiket, kesimler, tum, veri_dizini)
        s["kimlik"] = kimlik
        seriler.append(s)
    seriler.append(mevduat_serisi(ayar_oku(ayar_yolu)["mevduat_yillik_oran"], kesimler, tum))
    return {**d._zarf("kiyas", kaynak, zaman), "baz_gun": baz_gun, "gun_kesimi": gun_kesimi_adi,
            "gunler": tum, "seriler": seriler,
            "taban_notu": "Hepsi baz günün sonuna normalize birikimli getiridir; paper'ın gerçek başlangıç saati ilk gündedir, ilk günün kıyas getirisi "
                          "başlangıçtan önceki saatlerin hareketini de içerebilir.",
            "notlar": ["Kıyas fiyatları kapanmış mumlardan alınır (kapanmamış mum yok); seans dışı günlerde son kapanış taşınır.",
                       "Mevduat oranı projede tanımlı değil; kullanıcı girene kadar seri yoktur."]}
