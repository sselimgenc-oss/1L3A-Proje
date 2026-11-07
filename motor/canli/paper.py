"""Paper trading (Aşama 4): final set (7 strateji) canlı Binance herkese açık verisiyle, SANAL emirlerle.

Gerçek emir YOK, API anahtarı YOK (yalnız herkese açık REST/WS). Limitler UYGULANIR: işlem başı %1 (grup özsermayesinde),
toplam stop riski %5, 3x, günlük -%3 (o gün yeni işlem yok + açıklar kapanır), kill %20 (her şey durur). İki kol (tek-grafik +
portföy) TEK hesapta ortak limit kontrolünden geçer (bkz. paper_motor.py).

Bu dosya: orkestrasyon (`Paper`), tekrar modu, CLI. Canlı veri: paper_canli.py. Durum yazımı: paper_durum.py.

CLI
  python -m motor.canli.paper --canli [--durum durum] [--ayar-guncelle]     # servis (systemd)
  python -m motor.canli.paper --tekrar BAS [BIT] [--ayar kilit|guncel]     # geçmişi canlıymış gibi besler (yerel veri)
  python -m motor.canli.paper --tek-sefer                                    # bir tur çalış, durum yaz, çık
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import SembolKurallari
from motor.canli import paper_sinyal as psg
from motor.canli.paper_kaynak import TekrarKaynagi
from motor.canli.paper_motor import Birim, PaperMotor, _dec, _enc
from motor.portfoy.motor import PortfoyAyarlari

log = logging.getLogger("paper")


def d_zaman(t) -> str:
    from motor.canli.durum import zaman_str
    return zaman_str(pd.Timestamp(t))
KOK = Path(__file__).resolve().parents[2]
SURUM = 1
BASLANGIC_SERMAYE = 10000.0
PENCERE = {"5m": 4000, "15m": 3000, "30m": 6000, "1h": 3000, "4h": 3000, "1d": 1500}      # canlıda son N bar (tekrar: None)


def paper_ayarlari(baslangic_sermaye: float = BASLANGIC_SERMAYE) -> PortfoyAyarlari:
    """Backtest maliyet modeli (varsayılanlar: taker %0.05, maker %0.02, kayma 2 bps, stop kayması 5 bps) + limitler UYGULANIR."""
    return PortfoyAyarlari(baslangic_sermaye=baslangic_sermaye, limit_modu="uygula")


class Paper:
    def __init__(self, tanimlar: list, kaynak: TekrarKaynagi, kurallar: dict, ayarlar: Optional[PortfoyAyarlari] = None,
                 durum_yolu: Optional[Path] = None, her_satir_kaydet: bool = False, islem_baslangic=None,
                 pf_sutunlar: Optional[dict] = None):
        self.tanimlar = [t for t in tanimlar if not t.veri_yok]
        self.veri_yok = [t for t in tanimlar if t.veri_yok]
        self.kaynak = kaynak
        self.ayarlar = ayarlar or paper_ayarlari()
        self.motor = PaperMotor(self.ayarlar, kurallar)
        self.durum_yolu = Path(durum_yolu) if durum_yolu else None
        self.her_satir_kaydet = her_satir_kaydet
        self.pf_sutunlar = dict(pf_sutunlar or {})
        self.tanim_ad = {t.kimlik: t for t in self.tanimlar}
        self.birimler: list[Birim] = []
        self.baslatildi = False
        self.satir_sayisi = 0
        self.uyarilar: list = []                 # veri/motor uyarıları (saglik.json'a gider)
        self.olaylar: list = []                  # {zaman, tur, mesaj}; son 50'si olaylar.jsonl'e yazılır
        self.strateji_gun: dict = {}             # {kimlik: {"YYYY-MM-DD": gün sonu kümülatif net K/Z (Decimal)}}
        self.bildirim = None                     # callback(tur, mesaj) (Telegram vb.); None: yok
        self._limit_gorulen = 0
        for s in {x for t in self.tanimlar for x in t.veri_semboller}:
            if s not in kurallar:
                raise KeyError(f"{s}: sembol kuralı (tick/step/minNotional) yok")
            self.motor.sembol_ekle(s, kurallar[s])
        self._birimleri_kur()

    # ------------------------------------------------------------------ kurulum
    def _birimleri_kur(self):
        for t in self.tanimlar:
            if t.kol == "portfoy" and t.kimlik not in self.pf_sutunlar:
                continue                         # sütunlar ilk kararda (baslat) keşfedilir
            self._birim_ekle(t)

    def _birim_ekle(self, t):
        b = psg.birim_kur(t, self.pf_sutunlar.get(t.kimlik))
        self.motor.birim_ekle(b)
        self.birimler.append(b)

    def _mumlar_t(self, b: Birim, t) -> dict:
        return {s: self.kaynak.gecmis(s, b.tf, t) for s in b.semboller}

    def _motor_besle(self, b: Birim):
        for s in b.semboller:
            self.motor.fiyat_serisi(s, *self.kaynak.fiyat_dizisi(s))
            self.motor.funding_serisi(s, *self.kaynak.funding_dizisi(s))

    def _karar(self, b: Birim, t) -> dict:
        td = self.tanim_ad[b.ad]
        if td.kol == "tek_grafik":
            m = self.kaynak.gecmis(td.sembol, td.tf, t)
            return psg.tek_karar(td, m, self.kaynak.funding_df(td.sembol))
        k, _, son = psg.pf_karar(td, self._mumlar_t(b, t))
        if son != t:
            raise RuntimeError(f"{b.ad}: portföy ekseni son satırı {son} != işlenen satır {t}")
        return k

    def baslat(self, simdi):
        """İlk çalıştırma: her birim için kapanmış son barın kararları (bekleyen emirler) kurulur; dolum yok."""
        simdi = pd.Timestamp(simdi)
        for t in self.tanimlar:
            if t.kol == "portfoy" and t.kimlik not in self.pf_sutunlar:
                sr = self.kaynak.son_satir(Birim(t.kimlik, t.tf, pd.Timedelta(t.tf.replace("d", "D")) if t.tf.endswith("d")
                                                 else pd.Timedelta(t.tf), [], list(t.evren)), simdi)
                if sr is None:
                    raise RuntimeError(f"{t.kimlik}: başlangıç için kapanmış mum yok")
                _, sutun, _ = psg.pf_karar(t, self._mumlar_t(Birim(t.kimlik, t.tf, pd.Timedelta(0), [], list(t.evren)), sr[0]))
                self.pf_sutunlar[t.kimlik] = sutun
                self._birim_ekle(t)
        for b in self.birimler:
            sr = self.kaynak.son_satir(b, simdi)
            if sr is None:
                raise RuntimeError(f"{b.ad}: başlangıç için kapanmış mum yok")
            t, mumlar = sr
            self._motor_besle(b)
            self.motor.ilk_karar(b, t, mumlar, self._karar(b, t))
            b.son_t = t
        self.baslatildi = True

    # ------------------------------------------------------------------ işleme
    def isle(self, b: Birim, t, mumlar: dict, son_satir: bool = False):
        self._motor_besle(b)
        self.motor.acilis_fazi(b, t, mumlar)
        self.motor.kapanis_fazi(b, t, lambda: self._karar(b, t), son_satir)
        b.son_t = t
        self.satir_sayisi += 1
        self._satir_sonrasi(b, t)
        if self.her_satir_kaydet and self.durum_yolu:
            self.kaydet()

    def olay_ekle(self, tur: str, mesaj: str, zaman=None, bildir: bool = True):
        z = d_zaman(zaman if zaman is not None else self.motor.son_zaman or pd.Timestamp.now(tz="UTC"))
        self.olaylar.append({"zaman": z, "tur": tur, "mesaj": mesaj})
        self.olaylar = self.olaylar[-200:]
        log.info("olay %s: %s", tur, mesaj)
        if bildir and self.bildirim:
            self.bildirim(tur, mesaj)

    def _satir_sonrasi(self, b: Birim, t):
        from motor.canli.paper_durum import strateji_pnl
        m = self.motor
        gun = str(m.gun)
        for td in self.tanimlar:
            self.strateji_gun.setdefault(td.kimlik, {})[gun] = strateji_pnl(self, td.kimlik)["toplam"]
        for o in m.limit_olaylari[self._limit_gorulen:]:
            if o["tur"] == "kill_switch":
                self.olay_ekle("kill_switch", f"KILL SWITCH: zirveden düşüş %{o['dusus_yuzde']:.2f}; tüm işlemler durdu", o["zaman"])
            else:
                self.olay_ekle("gunluk_limit", f"Günlük kayıp limiti: gün başından %{o['dusus_yuzde']:.2f} kayıp; açıklar kapanıyor, "
                                              f"bugün yeni işlem yok", o["zaman"])
        self._limit_gorulen = len(m.limit_olaylari)

    def bekleyen(self, simdi) -> list:
        """İşlenecek (kapanış, birim sırası, t, mumlar) satırları, kapanış zamanına göre."""
        rows = []
        for bi, b in enumerate(self.birimler):
            for t, mumlar in self.kaynak.satirlar(b, b.son_t, simdi):
                rows.append((t + b.aralik, bi, t, mumlar))
        rows.sort(key=lambda r: (r[0], r[1]))
        return rows

    def adim(self, simdi, son_satir_bayragi: bool = False) -> int:
        """Kapanmış tüm bekleyen satırları kronolojik işler. -> işlenen satır sayısı."""
        if not self.baslatildi:
            raise RuntimeError("önce baslat(simdi) ya da yukle()")
        rows = self.bekleyen(simdi)
        for k, (kap, bi, t, mumlar) in enumerate(rows):
            b = self.birimler[bi]
            son = son_satir_bayragi and not any(r[1] == bi for r in rows[k + 1:])
            self.isle(b, t, mumlar, son_satir=son)
        return len(rows)

    # ------------------------------------------------------------------ kalıcılık
    def durum_sozlugu(self) -> dict:
        return {"surum": SURUM, "baslangic_sermaye": self.ayarlar.baslangic_sermaye,
                "ayarlar": {t.kimlik: t.ayar for t in self.tanimlar}, "pf_sutunlar": self.pf_sutunlar,
                "satir_sayisi": self.satir_sayisi, "uyarilar": self.uyarilar, "olaylar": self.olaylar,
                "strateji_gun": self.strateji_gun, "motor": self.motor.durum_al()}

    def kaydet(self, yol: Optional[Path] = None):
        from motor.canli.durum import atomik_yaz_json
        yol = Path(yol or self.durum_yolu)
        atomik_yaz_json(yol, _enc(self.durum_sozlugu()))

    def yukle(self, yol: Optional[Path] = None, ayar_guncelle: bool = False) -> bool:
        """Kayıtlı durumu yükler (varsa). Ayar etiketleri kayıtla uyuşmuyorsa AÇIK HATA (sessizce yeni ayara geçilmez)."""
        yol = Path(yol or self.durum_yolu)
        if not yol.exists():
            return False
        d = _dec(json.loads(yol.read_text(encoding="utf-8")))
        if d["surum"] != SURUM:
            raise RuntimeError(f"durum dosyası sürümü uyumsuz: {d['surum']}")
        fark = {k: (d["ayarlar"].get(k), t.ayar) for k, t in self.tanim_ad.items() if d["ayarlar"].get(k) != t.ayar}
        if fark and not ayar_guncelle:
            raise RuntimeError(f"kayıtlı durumun ayarları guncel_ayarlar.csv ile farklı: {fark}. Açık pozisyonlar eski ayarla "
                               f"yönetilir; yeni ayara geçmek için kullanıcı onayıyla --ayar-guncelle verin.")
        for t in self.tanimlar:
            if t.kol == "portfoy" and t.kimlik not in self.pf_sutunlar:
                self.pf_sutunlar[t.kimlik] = d["pf_sutunlar"][t.kimlik]
                self._birim_ekle(t)
        self.satir_sayisi = d["satir_sayisi"]
        self.uyarilar = list(d.get("uyarilar", []))
        self.olaylar = list(d.get("olaylar", []))
        self.strateji_gun = {k: dict(v) for k, v in d.get("strateji_gun", {}).items()}
        self.motor.durum_yukle(d["motor"])
        self._limit_gorulen = len(self.motor.limit_olaylari)
        for b in self.birimler:
            if b.son_t is None:
                raise RuntimeError(f"{b.ad}: kayıtlı durumda son işlenen satır yok")
            self._motor_besle(b)
        self.baslatildi = True
        return True


# ---------------------------------------------------------------------------- tekrar modu
def tekrar_veri_yukle(tanimlar: list, bas, bit=None, veri_dizini=None, kilit_ac: bool = False, gerekce: Optional[str] = None):
    """Yerel parquet'ten (araştırma katmanıyla AYNI yükleyiciler) çerçeveler. -> (mumlar {(s,tf)}, fundingler {s})."""
    from motor.portfoy import veri as pveri
    from motor.veri import depo
    mumlar, fund = {}, {}
    for t in tanimlar:
        for s in t.veri_semboller:
            if (s, t.tf) not in mumlar:
                df = pveri.mum_yukle(s, t.tf, None, bit, veri_dizini, kilit_ac=kilit_ac, gerekce=gerekce)
                mumlar[(s, t.tf)] = df.drop(columns="eksik") if "eksik" in df.columns else df
            if s not in fund and depo.funding_yolu(s, veri_dizini).exists():
                fund[s] = depo.funding_oku(s, None, bit, dizin=veri_dizini, kilit_ac=kilit_ac, gerekce=gerekce)
    return mumlar, fund


def tekrar_calistir(tanimlar: list, mumlar: dict, fundingler: dict, kurallar: dict, bas, bit=None,
                    ayarlar: Optional[PortfoyAyarlari] = None, pencere: Optional[dict] = None,
                    kapat: bool = True) -> Paper:
    """Geçmiş mumları SIRAYLA 'canlıymış gibi' besler: önce `bas` anına kadar olan kapanmış mumlarla başlangıç kararı,
    sonra bas..bit arasındaki mumlar kapanış sırasıyla işlenir. kapat=True: sonda açık pozisyonlar 'veri_sonu' ile kapanır
    (backtest ile aynı). Canlı yolla AYNI kod (Paper.baslat / Paper.adim)."""
    bas = pd.Timestamp(bas)
    bas = bas.tz_localize("UTC") if bas.tzinfo is None else bas.tz_convert("UTC")
    kaynak = TekrarKaynagi(mumlar, fundingler, pencere)
    p = Paper(tanimlar, kaynak, kurallar, ayarlar)
    p.baslat(bas)
    if bit is None:
        from motor.veri.depo import aralik_suresi
        bit = max(df.index[-1] + aralik_suresi(k[1]) for k, df in mumlar.items())      # son barın KAPANIŞI
    p.adim(pd.Timestamp(bit), son_satir_bayragi=kapat)
    return p


# ---------------------------------------------------------------------------- servis
def _tanimlara_veri_yok_isle(tanimlar: list, esl: dict) -> None:
    """Eşlemesi bulunamayan/TRADING olmayan sembol gerektiren stratejiler 'veri yok' işaretlenir (uydurma yok)."""
    for t in tanimlar:
        eksik = [f"{s}: {esl[s][1]}" for s in t.veri_semboller if esl.get(s, (None, "eşleme tablosunda yok"))[0] is None]
        if eksik:
            t.veri_yok = "; ".join(eksik)


def _durum_yaz(p: "Paper", kaynak, dizin: Path, simdi, servis=None, kaynak_adi="paper"):
    from motor.canli import paper_durum as pdr
    p.uyarilar = p.uyarilar[-50:]
    sag = kaynak.saglik_veri() if hasattr(kaynak, "saglik_veri") else [
        {"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1]} for (s, tf), df in kaynak.mumlar.items()]
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=p.olaylar, uyarilar=p.uyarilar, servis=servis, kaynak=kaynak_adi,
                    veri_yok_notlari=[f"VERİ YOK: {t.kimlik} — {t.veri_yok}" for t in p.veri_yok])
    from motor.canli import durum as d
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"],
                gecmis=o["gecmis"], ekstra=o["ekstra"])
    return o


def canli_calistir(durum_dizini: Path, tohum_dizin: Optional[Path] = None, ayar_guncelle: bool = False,
                   tek_sefer: bool = False) -> int:
    import asyncio
    import signal
    from motor.canli import paper_canli as pc, paper_veri as pv, telegram as tg
    durum_dizini = Path(durum_dizini)
    durum_dizini.mkdir(parents=True, exist_ok=True)
    ist = pv.FapiIstemci()
    simdi = ist.sunucu_zamani()
    bilgi = ist.exchange_info()
    tanimlar = psg.tanimlari_yukle(ayar_kaynagi="guncel")
    semboller = sorted({s for t in tanimlar for s in t.veri_semboller})
    esl = pv.esleme_dogrula(bilgi, semboller)
    _tanimlara_veri_yok_isle(tanimlar, esl)
    kurallar_b = pv.kurallar_cikar(bilgi)
    kurallar = {s: kurallar_b[b] for s, (b, _) in esl.items() if b is not None}
    olaylar_onbellek: list = []

    def olay(tur, mesaj):
        olaylar_onbellek.append((tur, mesaj))
        log.info("olay %s: %s", tur, mesaj)
    aktif = [t for t in tanimlar if not t.veri_yok]
    kaynak = pc.CanliKaynak(ist, aktif, PENCERE, tohum_dizin, olay)
    kaynak.baslat(simdi)
    p = Paper(tanimlar, kaynak, kurallar, durum_yolu=durum_dizini / "paper_state.json", her_satir_kaydet=True)
    p.bildirim = lambda tur, mesaj: tg.gonder(tg.olay_metni(tur, mesaj))
    if not p.yukle(ayar_guncelle=ayar_guncelle):
        p.baslat(simdi)
        p.olay_ekle("baslangic", f"Paper başlatıldı, başlangıç sermayesi {p.ayarlar.baslangic_sermaye}", simdi)
    else:
        p.olay_ekle("yeniden_baslatma", f"Durum diskten yüklendi; kaçan mumlar REST'ten tamamlanacak", simdi)
    for t in p.veri_yok:
        p.olay_ekle("veri_yok", f"{t.kimlik}: {t.veri_yok}", simdi)
    bildirilen = [len(p.motor.islemler)]
    son_ozet = [None]

    def tur() -> None:
        simdi = ist.sunucu_zamani()
        while olaylar_onbellek:
            t_, m_ = olaylar_onbellek.pop(0)
            p.olay_ekle(t_, m_, simdi)
        kaynak.guncelle(simdi)
        n = p.adim(simdi)
        for x in p.motor.islemler[bildirilen[0]:]:
            from motor.canli import paper_durum as pdr
            tg.gonder(tg.islem_metni(pdr._islem_satiri(p, x)))
        bildirilen[0] = len(p.motor.islemler)
        o = _durum_yaz(p, kaynak, durum_dizini, simdi)
        if n:
            p.kaydet()
        gun = str(simdi.date())
        if simdi.hour >= 0 and simdi.minute >= 10 and son_ozet[0] != gun:
            tg.gonder(tg.ozet_metni(o))
            son_ozet[0] = gun

    if tek_sefer:
        tur()
        p.kaydet()
        return 0

    async def ana():
        durdur = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, durdur.set)
        tetik = asyncio.Event()

        def mesaj(m):
            k = m.get("data", {}).get("k")
            if k and k.get("x"):
                tetik.set()
        ws = asyncio.create_task(pc.ws_dongu(pc.ws_url(pc.akislar(kaynak)), mesaj,
                                             lambda t_, m_: olaylar_onbellek.append((t_, m_)), durdur))
        while not durdur.is_set():
            try:
                await loop.run_in_executor(None, tur)
            except pv.BinanceHata as e:
                p.olay_ekle("binance_hata", str(e)[:300])
                log.error("tur başarısız: %s", e)
            try:
                await asyncio.wait_for(tetik.wait(), timeout=pc.YOKLAMA_SN)
            except asyncio.TimeoutError:
                pass
            tetik.clear()
            await asyncio.sleep(pc.GRACE_SN)
        ws.cancel()
        p.kaydet()
    asyncio.run(ana())
    return 0


def tekrar_cli(bas, bit, ayar: str, durum_dizini: Path, veri_dizini=None) -> int:
    """Geçmişi canlıymış gibi besler (7 strateji TEK hesapta, kol payları ve ortak limitlerle) ve durum/ dosyalarını yazar."""
    from motor.arastirma import tarama
    from motor.portfoy.motor import sembol_kurali
    tanimlar = psg.tanimlari_yukle(ayar_kaynagi=ayar)
    bas = pd.Timestamp(bas, tz="UTC") if pd.Timestamp(bas).tzinfo is None else pd.Timestamp(bas)
    bit_ts = pd.Timestamp(bit, tz="UTC") if bit else None
    mumlar, fund = tekrar_veri_yukle(tanimlar, bas, bit_ts, veri_dizini, kilit_ac=True,
                                     gerekce="Aşama 4: paper tekrar modu (kilit kullanılmış sayılır)")
    kurallar = {s: tarama.SEMBOL_KURALLARI.get(s, tarama.VARSAYILAN_KURAL) for t in tanimlar for s in t.veri_semboller}
    p = tekrar_calistir(tanimlar, mumlar, fund, kurallar, bas, bit_ts, pencere={tf: PENCERE.get(tf, 1500) for tf in ("30m", "4h", "1d")},
                        kapat=False)
    simdi = bit_ts or max(df.index[-1] for df in mumlar.values())
    from motor.canli.paper_kaynak import TekrarKaynagi
    _durum_yaz(p, p.kaynak, durum_dizini, simdi, kaynak_adi="backtest")
    print(f"[tekrar] {p.satir_sayisi} satır işlendi; kapanan işlem {len(p.motor.islemler)}; özsermaye {p.motor.ozsermaye():.2f}")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="1L3A paper trading (gerçek emir yok)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--canli", action="store_true", help="servis: canlı Binance verisiyle paper")
    g.add_argument("--tek-sefer", action="store_true", help="bir tur çalış, durum yaz, çık")
    g.add_argument("--tekrar", nargs="+", metavar=("BAS", "BIT"), help="geçmiş tekrarı: BAS [BIT] (UTC tarih)")
    ap.add_argument("--durum", default=str(KOK / "durum"))
    ap.add_argument("--tohum", default=None, help="yerel tohum veri dizini (veri/mumlar); yoksa yalnız REST")
    ap.add_argument("--ayar", default=None, choices=["guncel", "kilit"], help="tekrar modu ayar kaynağı (varsayılan: guncel)")
    ap.add_argument("--ayar-guncelle", action="store_true", help="kayıtlı durumdaki ayarlar csv'den farklıysa KULLANICI ONAYIYLA yeni ayara geç")
    ap.add_argument("--log", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if a.tekrar:
        return tekrar_cli(a.tekrar[0], a.tekrar[1] if len(a.tekrar) > 1 else None, a.ayar or "guncel", Path(a.durum))
    return canli_calistir(Path(a.durum), Path(a.tohum) if a.tohum else None, a.ayar_guncelle, a.tek_sefer)


if __name__ == "__main__":
    raise SystemExit(main())
