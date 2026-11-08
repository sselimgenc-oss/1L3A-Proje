"""Günlük S&P 500 (DK_SPX, Dukascopy USA500IDXUSD) 1h mum güncelleyici: kıyas serisi (motor/canli/kiyas.py) için SUNUCU veri dizinini taze tutar.

Neden: kıyas DK_SPX kapanışlarını yerel mum arşivinden okur (1h öncelikli); 5 günden bayat ise S&P çizgisi null olur. Sunucuda arşiv
`${STATE_DIRECTORY}/veri/mumlar` (paper `--tohum` ile AYNI dizin; paper bunu kıyas/güven okumasına da verir) ve kimse güncellemezse bayatlar.

Artımlı: mevcut parquet'in son mumunun bulunduğu aydan BİR ay öncesinden `--bitis` (hariç, varsayılan yarın UTC) tarihine kadar aylık saatlik
dosyalar geçici dizine indirilir; yeni parça mevcut geçmişle birleştirilir (örtüşmede yeni kazanır), eski geçmiş yeniden yazılmaz/indirilmez.
Sessiz hata yok: indirilemeyen ay, bayat sonuç ya da bilinmeyen/yasak dizin -> SystemExit (kod != 0) ve stderr'e neden.
Kilit: araştırma dizini (`veri/mumlar` depo içi) REDDEDİLİR; bu araç yalnız paper/kıyas verisi içindir, 2025-11-01 sonrası araştırma verisi yazmaz.
CLI: python -m motor.canli.spx_guncelle --veri /var/lib/1l3a-paper/veri/mumlar [--baslangic YYYY-MM] [--bitis YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from motor.veri import depo
from motor.veri import dukascopy as dk
from motor.veri.indir import _yaz

SEMBOL = "DK_SPX"
MAKS_BAYAT_GUN = 5                    # kiyas.MAKS_BOSLUK_GUN ile aynı anlam: sonuç bundan eskiyse hata


class GuncellemeHatasi(RuntimeError):
    pass


def bitis_hesapla(bugun: date) -> str:
    """bitis (hariç) = bugün + 1 gün (UTC): bugünün tamamlanmış saatleri dahil olur."""
    return (bugun + timedelta(days=1)).isoformat()


def baslangic_hesapla(mevcut_son: Optional[pd.Timestamp], baslangic_arg: Optional[str], geri_ay: int = 1) -> str:
    """'YYYY-MM'. Mevcut veri varsa son mumun ayından `geri_ay` önceki ay (güvenlik payı: o ayın kısmi/geç düzeltilmiş verisi yenilenir).
    Mevcut veri yoksa `--baslangic` ZORUNLU (ilk kurulumda tüm geçmişi sessizce indirmeye kalkılmaz)."""
    if mevcut_son is None:
        if not baslangic_arg:
            raise GuncellemeHatasi(f"{SEMBOL} arşivi yok: ilk kurulumda --baslangic YYYY-MM verin ya da tohumu kopyalayın (deploy/KURULUM.md)")
        return baslangic_arg
    ay = pd.Period(mevcut_son.strftime("%Y-%m"), freq="M") - geri_ay
    return str(ay)


def birlestir(mevcut: Optional[pd.DataFrame], yeni: pd.DataFrame) -> pd.DataFrame:
    """Yeni parçanın ilk mumundan ÖNCEKİ mevcut geçmiş + yeni parça (örtüşmede yeni kazanır)."""
    if yeni is None or not len(yeni):
        raise GuncellemeHatasi("yeni veri boş: indirme hiç mum getirmedi")
    if mevcut is None or not len(mevcut):
        return yeni.sort_index()
    eski = mevcut[mevcut.index < yeni.index.min()]
    sonuc = pd.concat([eski, yeni])
    sonuc = sonuc[~sonuc.index.duplicated(keep="last")].sort_index()
    return sonuc


def guncelle(veri: Path, bugun: date, baslangic: Optional[str] = None, bitis: Optional[str] = None,
             indir: Callable = dk.saatlik_indir, log: Callable = print) -> dict:
    veri = Path(veri)
    if veri.resolve() == depo.MUM_DIZINI.resolve():
        raise GuncellemeHatasi(f"{veri}: depo içi araştırma dizini reddedildi (kilit kuralı); sunucu paper veri dizinini verin")
    yol = depo.mum_yolu(SEMBOL, "1h", veri)
    mevcut = pd.read_parquet(yol) if yol.exists() else None
    mevcut_son = mevcut.index.max() if mevcut is not None and len(mevcut) else None
    bas = baslangic_hesapla(mevcut_son, baslangic)
    bit = bitis or bitis_hesapla(bugun)
    if date.fromisoformat(bit) <= date.fromisoformat(bas + "-01"):
        raise GuncellemeHatasi(f"bitis ({bit}) başlangıçtan ({bas}) sonra olmalı")
    with tempfile.TemporaryDirectory(prefix="spx_guncelle_") as gecici:
        r = indir(SEMBOL, bas, bit, dizin=Path(gecici), bugun=bugun, log=log)
        if r.get("basarisiz"):
            raise GuncellemeHatasi(f"indirilemeyen aylar: {r['basarisiz']} (yol yazılmadı)")
        yeni = pd.read_parquet(depo.mum_yolu(SEMBOL, "1h", Path(gecici))) if depo.mum_yolu(SEMBOL, "1h", Path(gecici)).exists() else None
    sonuc = birlestir(mevcut, yeni)
    son = sonuc.index.max()
    son_utc = son.tz_localize("UTC") if son.tzinfo is None else son.tz_convert("UTC")
    if son_utc < pd.Timestamp(bugun, tz="UTC") - pd.Timedelta(days=MAKS_BAYAT_GUN):
        raise GuncellemeHatasi(f"sonuç bayat: son mum {son_utc} (bugün {bugun}, sınır {MAKS_BAYAT_GUN} gün); yazılmadı")
    _yaz(sonuc, yol)
    ozet = {"sembol": SEMBOL, "yol": str(yol), "baslangic": bas, "bitis": bit, "onceki_son": None if mevcut_son is None else str(mevcut_son),
            "son": str(son), "mum_sayisi": len(sonuc), "eklenen": len(sonuc) - (0 if mevcut is None else len(mevcut))}
    log(f"{SEMBOL}: {ozet['onceki_son']} -> {ozet['son']}, {ozet['mum_sayisi']} mum (+{ozet['eklenen']})")
    return ozet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DK_SPX 1h mumlarını günlük artımlı güncelle (kıyas için)")
    ap.add_argument("--veri", required=True, help="mum arşivi kökü (sunucu: /var/lib/1l3a-paper/veri/mumlar)")
    ap.add_argument("--baslangic", help="YYYY-MM; yalnız arşiv yokken zorunlu (ilk kurulum)")
    ap.add_argument("--bitis", help="YYYY-MM-DD (hariç); varsayılan yarın UTC")
    a = ap.parse_args(argv)
    try:
        guncelle(Path(a.veri), datetime.now(timezone.utc).date(), a.baslangic, a.bitis)
    except GuncellemeHatasi as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
