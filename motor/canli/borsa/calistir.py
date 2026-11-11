"""Canlı servis girişi: `python -m motor.canli.borsa.calistir --durum DIZIN --tohum DIZIN [--ayar DOSYA]`.

Paper servisinin AYNI döngüsünü (`motor.canli.paper.canli_calistir`) çalıştırır; yalnız seçili stratejileri kurar ve her turdan sonra
paper motorunun niyetlerini yürütücüye verir. Durum dizini paper'dan AYRI olmalıdır (kendi paper durumu + `canli/` yürütücü durumu).
`canli` modu CANLI_ONAY=evet olmadan BAŞLAMAZ. Anahtarlar yalnız ortam değişkeninden okunur.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from pathlib import Path

from motor.canli.borsa import canli_ayar as ca
from motor.canli.borsa.canli_yurutucu import Ayar, Yurutucu
from motor.canli.borsa.motor_kopru import CanliDesteklemiyorHatasi, gorunum, uygunluk_kontrol

log = logging.getLogger("canli")


def _durum_dosyasi(dizin: Path, sid: str) -> Path:
    return dizin / "canli" / f"yurutucu_{hashlib.sha1(sid.encode()).hexdigest()[:12]}.json"


def onkontrol(ayar: ca.CanliAyar) -> None:
    """Başlamadan: strateji kimlikleri sette var mı, canlıda taklit edilebilir mi (portföy/kısmi çıkış yok)."""
    from motor.canli import paper_v2 as v2
    tanimlar = {t.kimlik: t for t in v2.tanimlari_yukle()}
    for s in ayar.stratejiler:
        t = tanimlar.get(s.id)
        if t is None:
            raise ca.CanliAyarHatasi(f"{s.id}: paper_v2 setinde yok")
        if t.kol == "portfoy":
            raise CanliDesteklemiyorHatasi(f"{s.id}: portföy (ağırlık) stratejisi canlıda henüz desteklenmiyor")
        if t.nesne.cikis_ayarlari.kismi:
            raise CanliDesteklemiyorHatasi(f"{s.id}: kısmi çıkış canlıda desteklenmiyor")


def borsa_kur(ayar: ca.CanliAyar, s: ca.StratejiAyar, env=None):
    """(borsa, exchangeInfo). kuru: gerçek hiçbir istek imzalanmaz; herkese açık mark fiyat + exchangeInfo kullanılır."""
    from decimal import Decimal
    from motor.canli import paper_veri as pv
    if ayar.mod == "kuru":
        from motor.canli.borsa.kuru import KuruBorsa
        ist = pv.FapiIstemci()
        return KuruBorsa(lambda b: Decimal(str(ist.get("/fapi/v1/premiumIndex", {"symbol": b})["markPrice"])), s.tahsis_usd), ist.exchange_info()
    from motor.canli.borsa.binance_futures import BinanceFutures
    anahtar, gizli = ca.anahtarlar(s, env)
    b = BinanceFutures(ayar.mod, anahtar, gizli, kosullu_modu=ayar.kosullu_modu)
    b.zaman_esitle()
    return b, b.exchange_info()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="1L3A canlı yürütücü")
    ap.add_argument("--ayar", default=None)
    ap.add_argument("--durum", default="durum_canli")
    ap.add_argument("--tohum", default=None)
    ap.add_argument("--tek-sefer", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        ayar = ca.yukle(a.ayar)
        onkontrol(ayar)
    except (ca.CanliAyarHatasi, CanliDesteklemiyorHatasi) as e:
        log.error("canlı yürütücü BAŞLAMADI: %s", e)
        return 2
    from motor.canli import paper as pp, telegram as tg
    dizin = Path(a.durum)
    yurutuculer, tutucu, kontrol_edildi = {}, {}, set()

    def olay(tur, mesaj):
        p = tutucu.get("p")
        if p is not None:
            p.olay_ekle(tur, mesaj, bildir=False)

    for s in ayar.stratejiler:
        try:
            borsa, bilgi = borsa_kur(ayar, s)
            b = borsa.bakiye()                                 # anahtar/izin doğrulaması: başarısızsa servis başlamaz
        except Exception as e:  # noqa: BLE001  (başlatma hatası: açık, mesajda gizli yok; BorsaHata metni zaten temizlenmiş)
            log.error("%s: borsa bağlantısı kurulamadı (%s): %s", s.id, type(e).__name__, e)
            return 3
        log.info("%s: %s hesabı hazır, özsermaye %s, tahsis %s", s.id, ayar.mod, b["ozsermaye"], s.tahsis_usd)
        yurutuculer[s.id] = Yurutucu(s.id, borsa, bilgi, Ayar(ayar.mod, s.tahsis_usd, ayar.working_type, ayar.giris_gecikme_max_sn, ayar.hedef_emri),
                                     durum_yolu=_durum_dosyasi(dizin, s.id), olay=olay, bildir=tg.gonder)

    def kanca(p, simdi) -> None:
        tutucu["p"] = p
        def son_mum(sembol, tf, t):
            df = p.kaynak.gecmis(sembol, tf, t)
            return df.index[-1] if len(df) else None
        for sid, y in yurutuculer.items():
            h = p.hesaplar[sid]
            if sid not in kontrol_edildi:
                uygunluk_kontrol(h.motor, h.birimler)             # fail-closed: desteklenmeyen kol varsa ilk turda açık hata, emir yok
                kontrol_edildi.add(sid)
            y.adim(gorunum(h.motor, h.birimler, son_mum))

    return pp.canli_calistir(dizin, Path(a.tohum) if a.tohum else None, tek_sefer=a.tek_sefer, tur_kancasi=kanca,
                             strateji_filtre=[s.id for s in ayar.stratejiler], telegram_sessiz=True)


if __name__ == "__main__":
    sys.exit(main())
