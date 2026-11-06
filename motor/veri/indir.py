"""data.binance.vision arşivinden mum ve funding verisi indirme.

Kullanım: python -m motor.veri.indir BTCUSDT XAUUSDT --aralik 5m 1h --funding
TLS doğrulaması her zaman açıktır (requests varsayılanı / ortam proxy CA'sı).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from motor.veri.depo import MUM_DIZINI, MUM_SUTUNLARI, _utc, funding_yolu, mum_yolu

ARSIV = "https://data.binance.vision"
S3_LISTE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
TABAN = "data/futures/um"
HAM_DIZIN = MUM_DIZINI / "_ham"

KLINE_SUTUNLARI = ["open_time", "open", "high", "low", "close", "volume", "close_time",
                   "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


# --------------------------------------------------------------- ayrıştırma
def _zaman_coz(seri: pd.Series) -> pd.DatetimeIndex:
    """Epoch sayısını UTC zamana çevirir; basamak sayısından ms/µs algılar."""
    sayi = pd.to_numeric(seri).astype("int64")
    ornek = int(sayi.iloc[0])
    birim = "us" if len(str(abs(ornek))) >= 16 else "ms"
    return pd.DatetimeIndex(pd.to_datetime(sayi, unit=birim, utc=True))


def _csv_oku(veri: bytes | str, sutunlar: list[str]) -> pd.DataFrame:
    """Başlıklı ya da başlıksız CSV'yi okur; başlık satırını ilk hücreden anlar."""
    metin = veri.decode() if isinstance(veri, bytes) else veri
    ilk = metin.lstrip().split("\n", 1)[0].split(",")[0].strip()
    baslik_var = not re.fullmatch(r"-?\d+", ilk)
    return pd.read_csv(io.StringIO(metin), header=0 if baslik_var else None,
                       names=None if baslik_var else sutunlar)


def mum_csv_ayristir(veri: bytes | str) -> pd.DataFrame:
    ham = _csv_oku(veri, KLINE_SUTUNLARI)
    if ham.empty:
        return _bos_mum()
    df = pd.DataFrame({
        "acilis": ham["open"].astype("float64"),
        "yuksek": ham["high"].astype("float64"),
        "dusuk": ham["low"].astype("float64"),
        "kapanis": ham["close"].astype("float64"),
        "hacim": ham["volume"].astype("float64"),
        "quote_hacim": ham["quote_volume"].astype("float64"),
        "islem_sayisi": ham["count"].astype("int64"),
    })
    df.index = _zaman_coz(ham["open_time"])
    df.index.name = "zaman"
    return df


def funding_csv_ayristir(veri: bytes | str) -> pd.DataFrame:
    ham = _csv_oku(veri, ["calc_time", "funding_interval_hours", "last_funding_rate"])
    if ham.empty:
        return _bos_funding()
    df = pd.DataFrame({"oran": ham["last_funding_rate"].astype("float64")})
    df.index = _zaman_coz(ham["calc_time"])
    df.index.name = "zaman"
    return df


def _bos_mum() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype="int64" if c == "islem_sayisi" else "float64")
                       for c in MUM_SUTUNLARI})
    df.index = pd.DatetimeIndex([], tz="UTC", name="zaman")
    return df


def _bos_funding() -> pd.DataFrame:
    df = pd.DataFrame({"oran": pd.Series(dtype="float64")})
    df.index = pd.DatetimeIndex([], tz="UTC", name="zaman")
    return df


def birlestir(parcalar: list[pd.DataFrame], bos) -> pd.DataFrame:
    """Sırala + tekrarları at (aynı zamanda sonraki parça kazanır)."""
    parcalar = [p for p in parcalar if len(p)]
    if not parcalar:
        return bos()
    df = pd.concat(parcalar)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "zaman"
    return df


def zip_icinden_csv(zip_bayt: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bayt)) as z:
        ad = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        return z.read(ad)


# --------------------------------------------------------------------- ağ
_oturum = requests.Session()


def _get(url: str, **kw) -> requests.Response:
    son = None
    for deneme in range(4):
        try:
            r = _oturum.get(url, timeout=60, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return r
            son = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            son = str(e)
        time.sleep(2 ** deneme)
    raise RuntimeError(f"İndirilemedi: {url} ({son})")


def s3_listele(onek: str) -> list[str]:
    """S3 öneki altındaki anahtarlar (sayfalı)."""
    anahtarlar, isaret = [], ""
    while True:
        params = {"delimiter": "/", "prefix": onek}
        if isaret:
            params["marker"] = isaret
        r = _get(S3_LISTE, params=params)
        r.raise_for_status()
        kok = ET.fromstring(r.content)
        ns = {"s": kok.tag.split("}")[0].strip("{")}
        yeni = [k.text for k in kok.findall("s:Contents/s:Key", ns)]
        anahtarlar += yeni
        if kok.findtext("s:IsTruncated", namespaces=ns) == "true" and yeni:
            isaret = yeni[-1]
        else:
            return anahtarlar


def zip_getir(anahtar: str, ham_dizin: Path | None = None) -> bytes:
    """Zip'i önbellekten ya da arşivden alır; sha256 CHECKSUM doğrulanır."""
    ham_dizin = ham_dizin or HAM_DIZIN
    yol = ham_dizin / anahtar.removeprefix(TABAN + "/")
    ck_yol = yol.with_name(yol.name + ".CHECKSUM")
    if yol.exists() and ck_yol.exists():
        bayt = yol.read_bytes()
        if _checksum_tamam(bayt, ck_yol.read_text()):
            return bayt
        yol.unlink()
        ck_yol.unlink()
    r = _get(f"{ARSIV}/{anahtar}")
    r.raise_for_status()
    rc = _get(f"{ARSIV}/{anahtar}.CHECKSUM")
    rc.raise_for_status()
    if not _checksum_tamam(r.content, rc.text):
        raise RuntimeError(f"Checksum uyuşmuyor: {anahtar}")
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(r.content)
    ck_yol.write_text(rc.text)
    return r.content


def _checksum_tamam(bayt: bytes, checksum_metni: str) -> bool:
    beklenen = checksum_metni.split()[0].lower()
    return hashlib.sha256(bayt).hexdigest() == beklenen


# --------------------------------------------------------------- yardımcı
def _ay(t) -> pd.Period:
    t = pd.Timestamp(t)
    if t.tzinfo is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t.to_period("M")


def _utc_simdi() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def _yaz(df: pd.DataFrame, yol: Path):
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".tmp")
    df.to_parquet(gecici)
    gecici.replace(yol)


def _mevcut(yol: Path, bos) -> pd.DataFrame:
    return pd.read_parquet(yol) if yol.exists() else bos()


def _baslangic_ayi(baslangic_ay, mevcut: pd.DataFrame, ilk_ay_varsayilan) -> pd.Period:
    if baslangic_ay is not None:
        return _ay(baslangic_ay)
    if len(mevcut):  # artımlı: parquet'teki son ayın başından devam
        return _ay(mevcut.index[-1])
    return ilk_ay_varsayilan


# ------------------------------------------------------------------ mum
def mum_indir(sembol: str, aralik: str, baslangic_ay=None, bitis=None,
              dizin: Path | None = None, sessiz: bool = False) -> pd.DataFrame:
    """Mumları indirip veri/mumlar/<SEMBOL>/<aralik>.parquet dosyasına birleştirir.

    baslangic_ay: 'YYYY-MM'. Verilmezse parquet varsa son ayından (artımlı),
    yoksa arşivdeki ilk aydan başlar. bitis: bu zamandan ÖNCEKİ mumlar alınır
    (varsayılan: şimdi).
    """
    dizin = dizin or MUM_DIZINI
    ham = dizin / "_ham"
    yol = mum_yolu(sembol, aralik, dizin)
    mevcut = _mevcut(yol, _bos_mum)
    bitis = _utc_simdi() if bitis is None else _utc(bitis)

    aylik = {re.search(r"(\d{4}-\d{2})\.zip$", k).group(1): k for k in
             s3_listele(f"{TABAN}/monthly/klines/{sembol}/{aralik}/{sembol}-{aralik}-") if k.endswith(".zip")}
    if not aylik:
        raise RuntimeError(f"Arşivde veri yok: {sembol} {aralik}")
    bas = _baslangic_ayi(baslangic_ay, mevcut, _ay(min(aylik) + "-01"))
    bit = _ay(bitis)

    parcalar = []
    ay = bas
    while ay <= bit:
        ad = str(ay)
        if ad in aylik:
            parcalar.append(mum_csv_ayristir(zip_icinden_csv(zip_getir(aylik[ad], ham))))
        else:  # aylık dosya henüz yok: günlük dosyalar
            gunluk = [k for k in s3_listele(f"{TABAN}/daily/klines/{sembol}/{aralik}/{sembol}-{aralik}-{ad}-")
                      if k.endswith(".zip")]
            for k in gunluk:
                parcalar.append(mum_csv_ayristir(zip_icinden_csv(zip_getir(k, ham))))
        if not sessiz:
            print(f"  {sembol} {aralik} {ad} tamam", flush=True)
        ay += 1

    yeni = birlestir(parcalar, _bos_mum)
    if baslangic_ay is not None and len(yeni):
        # açık başlangıç: bu aydan önceki mevcut veri korunur, sonrası yenilenir
        mevcut = mevcut[mevcut.index < yeni.index[0]]
    sonuc = birlestir([mevcut, yeni], _bos_mum)
    sonuc = sonuc[sonuc.index < bitis]
    sonuc = sonuc.astype({c: ("int64" if c == "islem_sayisi" else "float64") for c in MUM_SUTUNLARI})
    _yaz(sonuc, yol)
    return sonuc


# -------------------------------------------------------------- funding
def funding_indir(sembol: str, baslangic_ay=None, bitis=None,
                  dizin: Path | None = None, sessiz: bool = False) -> pd.DataFrame:
    dizin = dizin or MUM_DIZINI
    ham = dizin / "_ham"
    yol = funding_yolu(sembol, dizin)
    mevcut = _mevcut(yol, _bos_funding)
    bitis = _utc_simdi() if bitis is None else _utc(bitis)

    aylik = {re.search(r"(\d{4}-\d{2})\.zip$", k).group(1): k for k in
             s3_listele(f"{TABAN}/monthly/fundingRate/{sembol}/{sembol}-fundingRate-") if k.endswith(".zip")}
    if not aylik:
        raise RuntimeError(f"Arşivde funding yok: {sembol}")
    bas = _baslangic_ayi(baslangic_ay, mevcut, _ay(min(aylik) + "-01"))
    parcalar = []
    for ad, k in sorted(aylik.items()):
        if bas <= _ay(ad + "-01") <= _ay(bitis):
            parcalar.append(funding_csv_ayristir(zip_icinden_csv(zip_getir(k, ham))))
            if not sessiz:
                print(f"  {sembol} funding {ad} tamam", flush=True)
    # not: funding için günlük dosya yok; içinde bulunulan ay aylık dosya çıkana dek eksik kalır.
    yeni = birlestir(parcalar, _bos_funding)
    if baslangic_ay is not None and len(yeni):
        mevcut = mevcut[mevcut.index < yeni.index[0]]
    sonuc = birlestir([mevcut, yeni], _bos_funding)
    sonuc = sonuc[sonuc.index < bitis]
    _yaz(sonuc, yol)
    return sonuc


# ------------------------------------------------------------------ CLI
def main(argv=None):
    p = argparse.ArgumentParser(description="Binance Vision'dan USDT-M vadeli mum/funding indir")
    p.add_argument("semboller", nargs="+")
    p.add_argument("--aralik", nargs="+", default=["5m"])
    p.add_argument("--funding", action="store_true", help="funding oranlarını da indir")
    p.add_argument("--baslangic-ay", help="YYYY-MM (verilmezse artımlı / en baştan)")
    p.add_argument("--bitis", help="bu zamandan önceki mumlar (UTC)")
    a = p.parse_args(argv)
    for s in a.semboller:
        for ar in a.aralik:
            df = mum_indir(s, ar, a.baslangic_ay, a.bitis)
            print(f"{s} {ar}: {len(df)} satır, {df.index[0]} -> {df.index[-1]}" if len(df) else f"{s} {ar}: boş")
        if a.funding:
            df = funding_indir(s, a.baslangic_ay, a.bitis)
            print(f"{s} funding: {len(df)} satır" + (f", {df.index[0]} -> {df.index[-1]}" if len(df) else ""))


if __name__ == "__main__":
    sys.exit(main())
