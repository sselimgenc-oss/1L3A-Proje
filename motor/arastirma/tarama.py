"""Geniş tarama (Aşama 2, Katman 2): strateji x sembol x TF x ayar -> metrik tablosu. ELEME DEĞİL, SIRALAMA.

Karar 19: hepsi test edilir; bu modül hiçbir şeyi silmez. `umutsuz_mu` yalnız "apaçık umutsuz" bayrağı koyar.
Karar 20: veri `depo.mum_oku` / `depo.funding_oku` ile OKUNUR, `kilit_ac` ASLA kullanılmaz; kilitli dönem
(2025-11-01 sonrası) taramaya girmez.

Akış
  - Veri: 5m parquet -> `yeniden_ornekle(eksikleri_at=True)` ile hedef TF; funding dahil.
  - Her görev = (strateji, sembol, tf, ayar). Ayar kaynakları: "varsayilan", "kart" (her kart ayarı), "dis" (dış ayarlar: stratejiler/dis_ayarlari), "izgara"
    (parametre_izgarasi tam çarpımı; yalnız izgara=True ile).
  - Stil -> TF: scalp 15m/30m, daytrade 30m/1h, swing 4h/1d (`STIL_TF`; parametreyle değişir).
  - Motor: MotorAyarlari(limit_modu="olc") (araştırma modu: günlük limit ve kill switch durdurmaz, kaydedilir).
  - Paralel: multiprocessing, işçi başına (sembol, tf) veri önbelleği. Hata (CikisYokHatasi dahil) satıra `hata`
    olarak yazılır, tarama durmaz.
  - Çıktı: sonuclar/tarama/<etiket>.parquet (+ .csv aynı satırlar, _ozet.csv özet). Aynı etiketle tekrar
    çalıştırınca biten görevler atlanır (kaldığı yerden devam).
  - Deneme kaydı: tarama sonunda strateji başına bu çağrıda YAPILAN koşu sayısı deneme_kaydi'na yazılır.

SEMBOL_KURALLARI Binance USDT-M için bilinen/yaklaşık değerlerdir; exchangeInfo ile doğrulanacak (Aşama 6).

CLI: python -m motor.arastirma.tarama --etiket katman2_v1 [--stratejiler a b] [--semboller BTCUSDT] [--izgara]
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import multiprocessing as mp
import time
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from motor.backtest import deneme_kaydi
from motor.backtest import metrikler as mtr
from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.strateji import kayit
from motor.strateji.cikislar import CikisAyarlari
from motor.veri import depo
from motor.veri.yeniden_ornekle import yeniden_ornekle

KOK = Path(__file__).resolve().parents[2]
CIKTI_DIZINI = KOK / "sonuclar" / "tarama"
DIS_AYAR_DIZINI = KOK / "stratejiler" / "dis_ayarlari"

VARSAYILAN_SEMBOLLER = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
STIL_TF = {"scalp": ("15m", "30m"), "daytrade": ("30m", "1h"), "swing": ("4h", "1d")}

# Stil tablosuna uymayan stratejiler için TF geçersiz kılma (ad -> TF'ler). KGT: günlük/4s üst TF değerlerini
# kullanır, bu yüzden çalışma TF'si 4s'den KÜÇÜK olmalı (karar 21: swing orijinali ve gün-sonu varyantı 1h).
STRATEJI_TF = {"onceki__kgt": ("30m", "1h"), "onceki__kgt-gun": ("30m", "1h")}

# Binance USDT-M bilinen/yaklaşık filtreler; exchangeInfo ile doğrulanacak.
SEMBOL_KURALLARI = {
    "BTCUSDT": SembolKurallari(tick_size=0.1, step_size=0.001, min_qty=0.001, min_notional=5.0),
    "ETHUSDT": SembolKurallari(tick_size=0.01, step_size=0.001, min_qty=0.001, min_notional=5.0),
    "SOLUSDT": SembolKurallari(tick_size=0.01, step_size=0.1, min_qty=0.1, min_notional=5.0),
}
VARSAYILAN_KURAL = SembolKurallari(tick_size=0.01, step_size=0.001, min_qty=0.001, min_notional=5.0)

METRIK_ALANLARI = ["net_getiri", "cagr", "max_dusus", "sharpe", "sortino", "gunluk_mtm_max_dusus", "islem_sayisi",
                   "profit_factor", "kazanma_orani", "ortalama_r", "beklenen_deger", "en_iyi_yuzde5_haric_net",
                   "en_iyi_yuzde5_haric_pf", "toplam_komisyon", "toplam_funding", "ortalama_tutma_saat"]
KIMLIK_ALANLARI = ["strateji", "stil", "sembol", "tf", "ayar_kaynagi", "parametreler", "cikis_ayarlari"]
SUTUNLAR = KIMLIK_ALANLARI + METRIK_ALANLARI + ["sure_sn", "hata"]
KAYDET_ARALIGI = 400      # bu kadar yeni satırda bir parquet'e ara kayıt


def _json(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------- görev üretimi
def dis_ayarlari(ad: str, dizin: Optional[Path] = None) -> list:
    """stratejiler/dis_ayarlari/<aile>.json içeriği (dış kaynaklı ayarlar); dosya yoksa boş liste."""
    yol = Path(dizin if dizin is not None else DIS_AYAR_DIZINI) / f"{ad}.json"
    if not yol.exists():
        return []
    return json.loads(yol.read_text(encoding="utf-8"))


def dis_ayarli_strateji(ad: str, dis_id: str, dizin: Optional[Path] = None):
    """Dış ayarı (dis_id) ile kurulmuş strateji. Bilinmeyen parametre ValueError, bilinmeyen dis_id KeyError verir."""
    sinif = kayit.al(ad)
    for k in dis_ayarlari(ad, dizin):
        if k["dis_id"] == dis_id:
            par = dict(k.get("parametreler") or {})
            bilinmeyen = set(par) - set(sinif.varsayilan_parametreler)
            if bilinmeyen:
                raise ValueError(f"{ad}/{dis_id}: sınıfta olmayan parametre: {sorted(bilinmeyen)}")
            cikis = k.get("cikis_ayarlari")
            if cikis is not None:
                cikis = dict(cikis)
                if "kismi" in cikis:
                    cikis["kismi"] = tuple(tuple(x) for x in cikis["kismi"])
                cikis = CikisAyarlari(**cikis)
            return sinif(cikis_ayarlari=cikis, **par)
    raise KeyError(f"{ad}: dış ayar yok: {dis_id!r}")


def _ayar_listesi(ad: str, izgara: bool) -> list[tuple]:
    """[(ayar_kaynagi, arguman)]: varsayilan -> None; kart -> kart_id; dis -> dis_id; izgara -> parametre sözlüğü."""
    sinif = kayit.al(ad)
    liste = [("varsayilan", None)]
    liste += [("kart", k["kart_id"]) for k in kayit.kart_ayarlari(ad)]
    liste += [("dis", k["dis_id"]) for k in dis_ayarlari(ad)]
    if izgara and sinif.parametre_izgarasi:
        adlar = list(sinif.parametre_izgarasi)
        for deger in itertools.product(*sinif.parametre_izgarasi.values()):
            liste.append(("izgara", dict(zip(adlar, deger))))
    return liste


def _strateji_kur(ad: str, tur: str, arg):
    sinif = kayit.al(ad)
    if tur == "varsayilan":
        return sinif()
    if tur == "kart":
        return kayit.kart_ayarli_strateji(ad, arg)
    if tur == "dis":
        return dis_ayarli_strateji(ad, arg)
    return sinif(**arg)


def _etiket_ayar(tur: str, arg) -> str:
    return f"{tur}:{arg}" if tur in ("kart", "dis") else tur


def anahtar(strateji, sembol, tf, ayar_kaynagi, parametreler_json) -> tuple:
    return (strateji, sembol, tf, ayar_kaynagi, parametreler_json)


def gorevler_uret(stratejiler: Iterable[str], semboller: Iterable[str], tf_tablosu: dict, izgara: bool = False) -> list:
    """Görev listesi: sözlükler {strateji, stil, sembol, tf, tur, arg, ayar_kaynagi, parametreler, cikis_ayarlari,
    anahtar}. (sembol, tf) gruplu sıralıdır (işçi önbelleği için)."""
    gorevler = []
    for ad in stratejiler:
        sinif = kayit.al(ad)
        for tf in STRATEJI_TF.get(ad) or tf_tablosu.get(sinif.stil, ()):
            for sembol in semboller:
                for tur, arg in _ayar_listesi(ad, izgara):
                    try:
                        s = _strateji_kur(ad, tur, arg)
                        par, cks = _json(s.parametreler), _json(dataclasses.asdict(s.cikis_ayarlari))
                        hata = ""
                    except Exception as e:  # noqa: BLE001  (kurulamayan ayar yine satır olur)
                        par, cks, hata = _json(arg if isinstance(arg, dict) else {}), "{}", f"{type(e).__name__}: {e}"
                    etiket = _etiket_ayar(tur, arg)
                    gorevler.append({"strateji": ad, "stil": sinif.stil, "sembol": sembol, "tf": tf, "tur": tur,
                                     "arg": arg, "ayar_kaynagi": etiket, "parametreler": par, "cikis_ayarlari": cks,
                                     "kurma_hatasi": hata,
                                     "anahtar": anahtar(ad, sembol, tf, etiket, par)})
    gorevler.sort(key=lambda g: (g["sembol"], g["tf"]))
    return gorevler


# ---------------------------------------------------------------------------- işçi
_AYAR: dict = {}
_ONBELLEK: dict = {}


def _isci_baslat(veri_dizini, baslangic, bitis):
    _AYAR.update(dizin=veri_dizini, baslangic=baslangic, bitis=bitis)
    _ONBELLEK.clear()


def _veri(sembol: str, tf: str):
    k = (sembol, tf)
    if k not in _ONBELLEK:
        if len(_ONBELLEK) >= 4:
            _ONBELLEK.clear()
        d = _AYAR["dizin"]
        # kilit_ac YOK: kilitli dönem depo tarafından kesilir (karar 20).
        m5 = depo.mum_oku(sembol, "5m", _AYAR["baslangic"], _AYAR["bitis"], dizin=d)
        mumlar = yeniden_ornekle(m5, tf, kaynak="5m", eksikleri_at=True)
        try:
            fund = depo.funding_oku(sembol, _AYAR["baslangic"], _AYAR["bitis"], dizin=d)
        except FileNotFoundError:
            fund = None
        _ONBELLEK[k] = (mumlar, fund)
    return _ONBELLEK[k]


def _calistir(g: dict) -> dict:
    satir = {a: g[a] for a in ("strateji", "stil", "sembol", "tf", "ayar_kaynagi", "parametreler", "cikis_ayarlari")}
    t0 = time.perf_counter()
    hata = g["kurma_hatasi"]
    metrik = {}
    try:
        if hata:
            raise ValueError(hata)
        s = _strateji_kur(g["strateji"], g["tur"], g["arg"])
        mumlar, fund = _veri(g["sembol"], g["tf"])
        ay = MotorAyarlari(limit_modu="olc", kurallar=SEMBOL_KURALLARI.get(g["sembol"], VARSAYILAN_KURAL))
        r = backtest(mumlar, s, ay, fund)
        metrik = mtr.hesapla(r.islemler, r.ozsermaye, r.baslangic_sermaye)
        hata = ""
    except Exception as e:  # noqa: BLE001  (CikisYokHatasi dahil: satıra yazılır, tarama durmaz)
        hata = f"{type(e).__name__}: {e}"
    satir.update({a: metrik.get(a, np.nan) for a in METRIK_ALANLARI})
    satir["sure_sn"] = time.perf_counter() - t0
    satir["hata"] = hata
    return satir


# ---------------------------------------------------------------------------- yardımcılar
def _df(satirlar: list) -> pd.DataFrame:
    df = pd.DataFrame(satirlar, columns=SUTUNLAR)
    for a in METRIK_ALANLARI + ["sure_sn"]:
        df[a] = pd.to_numeric(df[a], errors="coerce").astype("float64")
    for a in KIMLIK_ALANLARI + ["hata"]:
        df[a] = df[a].astype(str)
    return df


def _satir_anahtari(df: pd.DataFrame) -> list:
    return list(zip(df["strateji"], df["sembol"], df["tf"], df["ayar_kaynagi"], df["parametreler"]))


def _yaz(df: pd.DataFrame, yol_pq: Path) -> None:
    gecici = yol_pq.with_suffix(".parquet.tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol_pq)


# ---------------------------------------------------------------------------- ana akış
def tara(etiket: str, stratejiler: Optional[Iterable[str]] = None, semboller: Iterable[str] = VARSAYILAN_SEMBOLLER,
         tf_tablosu: Optional[dict] = None, izgara: bool = False, surec: int = 4,
         cikti_dizini: Optional[Path] = None, veri_dizini: Optional[Path] = None,
         baslangic=None, bitis=None, hatalari_yeniden: bool = False, deneme_kaydi_yolu=None,
         ilerleme: bool = True) -> pd.DataFrame:
    """Taramayı koşar, tüm sonuç satırlarını (önceki + yeni) döner. surec=1: ana süreçte (test/ayıklama)."""
    stratejiler = list(stratejiler) if stratejiler is not None else list(kayit.tum_stratejiler())
    semboller = list(semboller)
    tf_tablosu = tf_tablosu or STIL_TF
    cikti_dizini = Path(cikti_dizini) if cikti_dizini is not None else CIKTI_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    yol_pq = cikti_dizini / f"{etiket}.parquet"

    onceki = pd.read_parquet(yol_pq) if yol_pq.exists() else _df([])
    if hatalari_yeniden:
        onceki = onceki[onceki["hata"] == ""]
    bitmis = set(_satir_anahtari(onceki))
    tum = gorevler_uret(stratejiler, semboller, tf_tablosu, izgara)
    kalan = [g for g in tum if g["anahtar"] not in bitmis]
    if ilerleme:
        print(f"[tarama] {etiket}: toplam {len(tum)} görev, bitmiş {len(tum) - len(kalan)}, kalan {len(kalan)}", flush=True)

    yeni: list = []
    t0 = time.perf_counter()

    def ekle(satir):
        yeni.append(satir)
        if len(yeni) % KAYDET_ARALIGI == 0:
            _yaz(pd.concat([onceki, _df(yeni)], ignore_index=True), yol_pq)
        if ilerleme and len(yeni) % 200 == 0:
            gecen = time.perf_counter() - t0
            print(f"[tarama] {len(yeni)}/{len(kalan)}  {gecen:.0f} sn", flush=True)

    if kalan:
        if surec <= 1:
            _isci_baslat(veri_dizini, baslangic, bitis)
            for g in kalan:
                ekle(_calistir(g))
        else:
            with mp.get_context("fork").Pool(surec, _isci_baslat, (veri_dizini, baslangic, bitis)) as havuz:
                for satir in havuz.imap_unordered(_calistir, kalan, chunksize=8):
                    ekle(satir)
    sonuc = pd.concat([onceki, _df(yeni)], ignore_index=True)
    _yaz(sonuc, yol_pq)
    sonuc.to_csv(cikti_dizini / f"{etiket}.csv", index=False)
    ozet(sonuc).to_csv(cikti_dizini / f"{etiket}_ozet.csv", index=False)

    # Deneme kaydı: bu çağrıda gerçekten koşulan (hatasız) backtest sayısı, strateji başına.
    if yeni:
        y = _df(yeni)
        for ad, grup in y.groupby("strateji"):
            kosu = int((grup["hata"] == "").sum())
            if kosu:
                komb = int(grup[["ayar_kaynagi", "parametreler"]].drop_duplicates().shape[0])
                deneme_kaydi.kaydet(ad, ",".join(sorted(grup["sembol"].unique())), ",".join(sorted(grup["tf"].unique())),
                                    komb, 0, kosu, deneme_kaydi_yolu)
    if ilerleme:
        print(f"[tarama] bitti: {len(yeni)} yeni satır, {time.perf_counter() - t0:.1f} sn -> {yol_pq}", flush=True)
    return sonuc


# ---------------------------------------------------------------------------- yorum: işaretleme, özet
def _gecerli(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["hata"] == ""] if "hata" in df.columns else df


def umutsuz_mu(sonuc_df: pd.DataFrame, pf_esik: float = 0.8) -> pd.Series:
    """Strateji -> bool. True: stratejinin TÜM geçerli (hatasız) satırlarında (sembol x TF x ayar) PF < pf_esik
    veya işlem yok. Hatalı satırlar kanıt sayılmaz; hiç geçerli satırı olmayan strateji False döner.
    Hiçbir şey silinmez; yalnız işaretler (karar 19)."""
    cikti = {}
    for ad, grup in sonuc_df.groupby("strateji"):
        g = _gecerli(grup)
        if len(g) == 0:
            cikti[ad] = False
            continue
        pf = g["profit_factor"]
        kotu = (g["islem_sayisi"].fillna(0) == 0) | pf.isna() | (pf < pf_esik)
        cikti[ad] = bool(kotu.all())
    return pd.Series(cikti, name="umutsuz", dtype=bool)


def ozet(sonuc_df: pd.DataFrame, pf_esik: float = 0.8, min_islem: int = 10) -> pd.DataFrame:
    """Strateji başına: en iyi satır (en yüksek PF; önce >= min_islem işlemli satırlar, yoksa işlemi olanlar),
    medyan PF (işlemi olan geçerli satırlar), umutsuz bayrağı. Sonuç en iyi PF'ye göre azalan sıralıdır."""
    sat = []
    umut = umutsuz_mu(sonuc_df, pf_esik) if len(sonuc_df) else pd.Series(dtype=bool)
    for ad, grup in sonuc_df.groupby("strateji"):
        g = _gecerli(grup)
        islemli = g[g["islem_sayisi"].fillna(0) > 0]
        aday = islemli[islemli["islem_sayisi"] >= min_islem]
        if len(aday) == 0:
            aday = islemli
        r = {"strateji": ad, "stil": grup["stil"].iloc[0], "satir_sayisi": len(grup),
             "hata_sayisi": int((grup["hata"] != "").sum()),
             "medyan_pf": float(islemli["profit_factor"].replace(np.inf, np.nan).median()) if len(islemli) else np.nan,
             "umutsuz": bool(umut.get(ad, False))}
        if len(aday):
            e = aday.loc[aday["profit_factor"].fillna(-np.inf).idxmax()]
            r.update({"en_iyi_sembol": e["sembol"], "en_iyi_tf": e["tf"], "en_iyi_ayar": e["ayar_kaynagi"],
                      "en_iyi_pf": e["profit_factor"], "en_iyi_islem": e["islem_sayisi"],
                      "en_iyi_net_getiri": e["net_getiri"], "en_iyi_max_dusus": e["max_dusus"]})
        sat.append(r)
    cikti = pd.DataFrame(sat)
    if len(cikti) and "en_iyi_pf" in cikti.columns:
        cikti = cikti.sort_values("en_iyi_pf", ascending=False, na_position="last").reset_index(drop=True)
    return cikti


# ---------------------------------------------------------------------------- CLI
def _tf_ayristir(metinler: Optional[list]) -> dict:
    tablo = dict(STIL_TF)
    for m in metinler or []:                       # "swing=4h,1d"
        stil, tflar = m.split("=")
        tablo[stil] = tuple(tflar.split(","))
    return tablo


def main(argv=None):
    ap = argparse.ArgumentParser(description="Geniş tarama (Aşama 2 Katman 2): sıralama, eleme değil")
    ap.add_argument("--etiket", required=True)
    ap.add_argument("--stratejiler", nargs="*", default=None)
    ap.add_argument("--semboller", nargs="*", default=list(VARSAYILAN_SEMBOLLER))
    ap.add_argument("--izgara", action="store_true", help="tam parametre ızgarasını da tara")
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--tf", nargs="*", help="stil=tf1,tf2 (ör. swing=4h,1d)")
    ap.add_argument("--hatalari-yeniden", action="store_true")
    a = ap.parse_args(argv)
    sonuc = tara(a.etiket, a.stratejiler, a.semboller, _tf_ayristir(a.tf), a.izgara, a.surec,
                 hatalari_yeniden=a.hatalari_yeniden)
    o = ozet(sonuc)
    print(o.head(25).to_string())
    print(f"umutsuz: {int(o['umutsuz'].sum())}/{len(o)}")


if __name__ == "__main__":
    main()
