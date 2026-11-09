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
import traceback
from decimal import Decimal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import SembolKurallari
from motor.canli import kalp_atisi as kh
from motor.canli import paper_sinyal as psg
from motor.canli.durum_ek import kapanis_gunu as tsi_kapanis_gunu
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
                 pf_sutunlar: Optional[dict] = None, tetikleyen_hemen_kapat: bool = True):
        self.tanimlar = [t for t in tanimlar if not t.veri_yok]
        self.veri_yok = [t for t in tanimlar if t.veri_yok]
        self.kaynak = kaynak
        self.ayarlar = ayarlar or paper_ayarlari()
        self.motor = PaperMotor(self.ayarlar, kurallar, tetikleyen_hemen_kapat)
        self.durum_yolu = Path(durum_yolu) if durum_yolu else None
        self.her_satir_kaydet = her_satir_kaydet
        self.pf_sutunlar = dict(pf_sutunlar or {})
        self.tanim_ad = {t.kimlik: t for t in self.tanimlar}
        self.birimler: list[Birim] = []
        self.baslatildi = False
        self.satir_sayisi = 0
        self.uyarilar: list = []                 # veri/motor uyarıları (saglik.json'a gider)
        self.olaylar: list = []                  # {zaman, tur, mesaj}; son 50'si olaylar.jsonl'e yazılır
        self.strateji_gun: dict = {}             # {kimlik: {"YYYY-MM-DD" (UTC günü): gün sonu kümülatif net K/Z (Decimal)}} (beklenti tabanı)
        self.strateji_gun_tsi: dict = {}         # aynısı TSİ günü kesimiyle (pano dönemsel getiri)
        self.bildirim = None                     # callback(tur, mesaj) (Telegram vb.); None: yok
        self._limit_gorulen = 0
        # kalp atışı (kalp_atisi.py): düzenli zaman damgası; yeniden başlatmadaki kesinti süresi bundan ölçülür
        self.kalp_atisi: Optional[str] = None     # son kalp atışı (UTC ISO); paper_state.json'a da yazılır
        self.baslangic_zamani: Optional[str] = None
        self.onceki_kalp: Optional[str] = None    # bu süreç başlarken bulunan önceki kalp atışı
        self.son_kesinti: Optional[dict] = None   # bu süreç başlarken ölçülen kesinti (kalp_atisi.kesinti)
        self._kalp_yazilan = None
        self._askida_kayit: dict = {"ayarlar": {}, "pf_sutunlar": {}}   # kayıtta olup şimdi çalışmayan stratejilerin ayar/sütunları (geri yazılır)
        self.son_ozet: Optional[str] = None       # günlük Telegram özeti gönderilen son TSİ günü ("YYYY-MM-DD"; paper_state'e yazılır)
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

    # ------------------------------------------------------------------ kalp atışı
    def kalp_at(self, simdi, dizin: Optional[Path] = None, zorla: bool = False, durdu: bool = False) -> None:
        """Kalp atışını günceller (bellek + paper_state) ve en çok `kh.KALP_SN`'de bir `kalp_atisi.json`'a yazar. `simdi`: sunucu zamanı (UTC)."""
        simdi = pd.Timestamp(simdi)
        self.kalp_atisi = d_zaman(simdi)
        if dizin is not None and (zorla or durdu or self._kalp_yazilan is None
                                  or (simdi - self._kalp_yazilan).total_seconds() >= kh.KALP_SN):
            kh.yaz(dizin, simdi, self.baslangic_zamani or self.kalp_atisi, self.onceki_kalp, durdu)
            self._kalp_yazilan = simdi

    def surec_basla(self, simdi, dizin: Path, yuklendi: bool) -> None:
        """Servis başlangıcı: ÖNCEKİ kalp atışını (dosya ve paper_state'in yenisi) okur; yeniden başlatmaysa "son kalp atışı -> başlangıç"
        kesintisini süresiyle `yeniden_baslatma` olayına yazar; sonra yeni kalp atışını yazar. İlk çalışmada kesinti yoktur."""
        from motor.canli import durum as dr
        self.baslangic_zamani = d_zaman(simdi)
        if yuklendi:
            try:
                kd, hata = kh.oku(dizin), None
            except dr.DurumHatasi as e:
                kd, hata = None, str(e).replace("(", "[").replace(")", "]")
            k = kh.kesinti(kh.en_yeni(self.kalp_atisi, kd["zaman"] if kd else None), simdi)
            self.son_kesinti, self.onceki_kalp = k, k["onceki"]
            self.olay_ekle("yeniden_baslatma", kh.olay_mesaji(k) + (f"; kalp atışı dosyası okunamadı: {hata}" if hata else ""), simdi)
        self.kalp_at(simdi, dizin, zorla=True)

    def kalp_bilgisi(self) -> Optional[dict]:
        """saglik.json `kalp_atisi` bloğu (pano yalnız biçimler). Kalp atışı hiç atılmadıysa (tekrar modu) None."""
        if self.kalp_atisi is None:
            return None
        k = self.son_kesinti
        return {"son": self.kalp_atisi, "baslangic": self.baslangic_zamani, "aralik_sn": kh.KALP_SN,
                "onceki_kalp_atisi": self.onceki_kalp, "son_kesinti_sn": (k or {}).get("sn"),
                "son_kesinti_neden": (k or {}).get("neden") if k else "bu süreç ilk çalışmada başladı (yeniden başlatma yok)"}

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
        tsi_gun = tsi_kapanis_gunu(t + b.aralik)
        for td in self.tanimlar:
            toplam = strateji_pnl(self, td.kimlik)["toplam"]
            self.strateji_gun.setdefault(td.kimlik, {})[gun] = toplam
            self.strateji_gun_tsi.setdefault(td.kimlik, {})[tsi_gun] = toplam
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
                "ayarlar": {**self._askida_kayit["ayarlar"], **{t.kimlik: t.ayar for t in self.tanimlar}},
                "pf_sutunlar": {**self._askida_kayit["pf_sutunlar"], **self.pf_sutunlar},
                "satir_sayisi": self.satir_sayisi, "uyarilar": self.uyarilar, "olaylar": self.olaylar, "kalp_atisi": self.kalp_atisi,
                "strateji_gun": self.strateji_gun, "strateji_gun_tsi": self.strateji_gun_tsi, "son_ozet": self.son_ozet,
                "motor": self.motor.durum_al()}

    def kaydet(self, yol: Optional[Path] = None):
        from motor.canli.durum import atomik_yaz_json
        yol = Path(yol or self.durum_yolu)
        atomik_yaz_json(yol, _enc(self.durum_sozlugu()))

    def _pf_sutun_guncelle(self, t, eski: list, d: dict) -> tuple:
        """--ayar-guncelle: portföy sütunları YENİ ayar nesnesinden (baslat'taki keşifle aynı yol; kayıtlı son satıra kadarki veriyle)
        yeniden türetilir. -> (sütunlar, atılan kol kimlikleri, uyarı metni | None). Çıkan sembolde AÇIK POZİSYON varsa AÇIK HATA
        (sessizce eski kümeyle devam edilmez, pozisyon da sahipsiz bırakılmaz)."""
        son_t = d["motor"]["birimler"].get(t.kimlik)
        if son_t is None:
            raise RuntimeError(f"{t.kimlik}: kayıtlı durumda son işlenen satır yok; portföy sütunları yeni ayardan türetilemez")
        _, yeni, _ = psg.pf_karar(t, self._mumlar_t(Birim(t.kimlik, t.tf, pd.Timedelta(0), [], list(t.evren)), son_t))
        if list(yeni) == list(eski):
            return list(eski), set(), None
        cikan, eklenen = [x for x in eski if x not in yeni], [x for x in yeni if x not in eski]
        acik_kollar = {q["kol"] for q in d["motor"]["acik"].values()}
        acik_cikan = [x for x in cikan if f"{t.kimlik}#{x}" in acik_kollar]
        if acik_cikan:
            raise RuntimeError(f"{t.kimlik}: yeni ayar şu sembolleri evrenden çıkarıyor ama bu sembollerde AÇIK POZİSYON var: {acik_cikan}. "
                               f"Yeni ayara bu pozisyonlar kapandıktan sonra geçin (ya da kullanıcı kararıyla elle karar verin).")
        msg = (f"{t.kimlik}: --ayar-guncelle ile portföy sembol kümesi değişti; eklenen {eklenen or '-'}, çıkan {cikan or '-'} "
               f"(çıkanlarda açık pozisyon yoktu)")
        log.warning(msg)
        return list(yeni), {f"{t.kimlik}#{x}" for x in cikan}, msg

    def yukle(self, yol: Optional[Path] = None, ayar_guncelle: bool = False, olay_yaz: bool = True) -> bool:
        """Kayıtlı durumu yükler (varsa). Ayar etiketleri kayıtla uyuşmuyorsa AÇIK HATA (sessizce yeni ayara geçilmez).
        Kayıtta olup şimdi 'veri yok' olan strateji yüklemeyi düşürmez: 'askıda' taşınır, uyarı + `askida` olayı yazılır.
        olay_yaz=False: hata sonrası geri yükleme (aynı uyarılar tekrar yazılmaz)."""
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
        atilan, notlar = set(), []
        self._askida_kayit = {"ayarlar": {k: v for k, v in d["ayarlar"].items() if k not in self.tanim_ad},
                              "pf_sutunlar": {k: v for k, v in d["pf_sutunlar"].items() if k not in self.tanim_ad}}
        for t in self.tanimlar:
            if t.kol == "portfoy" and t.kimlik not in self.pf_sutunlar:
                sutun = list(d["pf_sutunlar"][t.kimlik])
                if ayar_guncelle and t.kimlik in fark:
                    sutun, at, msg = self._pf_sutun_guncelle(t, sutun, d)
                    atilan |= at
                    notlar += [msg] if msg else []
                self.pf_sutunlar[t.kimlik] = sutun
                self._birim_ekle(t)
        self.satir_sayisi = d["satir_sayisi"]
        self.uyarilar = list(d.get("uyarilar", []))
        self.olaylar = list(d.get("olaylar", []))
        self.kalp_atisi = d.get("kalp_atisi")                       # eski durum dosyasında yok (None)
        self.strateji_gun = {k: dict(v) for k, v in d.get("strateji_gun", {}).items()}
        # eski durum dosyasında TSİ serisi yok: UTC günü serisi devralınır (en çok 3 saat kayma; motor.tsi_aktarildi notu)
        self.strateji_gun_tsi = {k: dict(v) for k, v in d.get("strateji_gun_tsi", d.get("strateji_gun", {})).items()}
        self.son_ozet = d.get("son_ozet")                           # eski durum dosyasında yok (None)
        self.motor.durum_yukle(d["motor"], atilan_kollar=frozenset(atilan))
        self._limit_gorulen = len(self.motor.limit_olaylari)
        if olay_yaz:
            for msg in notlar:
                self.uyarilar.append(msg)
                self.olay_ekle("ayar_guncelle", msg, self.motor.son_zaman, bildir=False)
            for a in self.motor.askida_ozeti():
                acik = "; ".join(f"{k} {s} {'long' if y == 1 else 'short'} {m}" for k, s, y, m in a["acik"])
                msg = (f"{a['birim']} ASKIDA: kayıtlı durumda var ama şu an çalıştırılamıyor (veri yok); durumu korunuyor, emir verilmiyor"
                       + (f"; açık pozisyon son bilinen fiyatla donduruldu: {acik}" if acik else "; açık pozisyon yok"))
                log.warning(msg)
                self.uyarilar.append(msg)
                self.olay_ekle("askida", msg, self.motor.son_zaman)
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
                    kapat: bool = True, tetikleyen_hemen_kapat: bool = True) -> Paper:
    """Geçmiş mumları SIRAYLA 'canlıymış gibi' besler: önce `bas` anına kadar olan kapanmış mumlarla başlangıç kararı,
    sonra bas..bit arasındaki mumlar kapanış sırasıyla işlenir. kapat=True: sonda açık pozisyonlar 'veri_sonu' ile kapanır
    (backtest ile aynı). Canlı yolla AYNI kod (Paper.baslat / Paper.adim)."""
    bas = pd.Timestamp(bas)
    bas = bas.tz_localize("UTC") if bas.tzinfo is None else bas.tz_convert("UTC")
    kaynak = TekrarKaynagi(mumlar, fundingler, pencere)
    p = Paper(tanimlar, kaynak, kurallar, ayarlar, tetikleyen_hemen_kapat=tetikleyen_hemen_kapat)
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


def _durum_yaz(p: "Paper", kaynak, dizin: Path, simdi, servis=None, kaynak_adi="paper", veri_dizini: Optional[Path] = None):
    from motor.canli import paper_durum as pdr
    p.uyarilar = p.uyarilar[-50:]
    sag = kaynak.saglik_veri() if hasattr(kaynak, "saglik_veri") else [
        {"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1], "mum_indeksi": df.index} for (s, tf), df in kaynak.mumlar.items()]
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=p.olaylar, uyarilar=p.uyarilar, servis=servis, kaynak=kaynak_adi,
                    veri_yok_notlari=[f"VERİ YOK: {t.kimlik} — {t.veri_yok}" for t in p.veri_yok], veri_dizini=veri_dizini)
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
    bld = tg.Bildirimci()
    p.bildirim = bld.olay                      # teknik olaylar gönderilmez; sorun sürerse tek uyarı; sel koruması
    yuklendi = p.yukle(ayar_guncelle=ayar_guncelle)
    p.surec_basla(simdi, durum_dizini, yuklendi)         # kalp atışı + yeniden başlatma kesintisi (süresiyle `yeniden_baslatma` olayı)
    if not yuklendi:
        p.baslat(simdi)
        p.olay_ekle("baslangic", f"Paper başlatıldı, başlangıç sermayesi {p.ayarlar.baslangic_sermaye}", simdi)
    for t in p.veri_yok:
        p.olay_ekle("veri_yok", f"{t.kimlik}: {t.veri_yok}", simdi)
    for u in pv.tradfi_sinif_uyusmazliklari(bilgi, semboller):     # TradFi funding ayrımı (2026-11-09) sınıflamaya dayanır
        p.olay_ekle("tradfi_sinif", u, simdi)
    from motor.canli import paper_durum as pdr
    tg.gonder(tg.baslangic_metni(len(aktif), p.motor.ozsermaye()))
    bildirilen = [len(p.motor.islemler)]
    gorulen_acik = {(a["kimlik"], a["sembol"], a["giris_zamani"]) for a in pdr.acik_pozisyonlar(p)}
    if not yuklendi:
        p.son_ozet = dun_tsi(simdi)            # ilk çalışma: paper'dan önceki gün özetlenmez
        p.kaydet()                             # hata sonrası geri yükleme için her zaman tutarlı bir kayıt bulunsun
    kiyas_son = [None]

    def tur() -> None:
        simdi = ist.sunucu_zamani()
        while olaylar_onbellek:
            t_, m_ = olaylar_onbellek.pop(0)
            p.olay_ekle(t_, m_, simdi)
        kaynak.guncelle(simdi)
        n = p.adim(simdi)
        bld.kontrol()                          # WS 10 dk'dır kopuksa tek uyarı
        p.kalp_at(simdi, durum_dizini)         # tur başarıyla tamamlandı: kalp atışı (en çok 60 sn'de bir diske)
        for a in pdr.acik_pozisyonlar(p):
            if (a["kimlik"], a["sembol"], a["giris_zamani"]) not in gorulen_acik:
                gorulen_acik.add((a["kimlik"], a["sembol"], a["giris_zamani"]))
                tg.gonder(tg.islem_acildi_metni(a))
        for x in p.motor.islemler[bildirilen[0]:]:
            tg.gonder(tg.islem_kapandi_metni(pdr._islem_satiri(p, x)))
        bildirilen[0] = len(p.motor.islemler)
        if tohum_dizin is not None and (kiyas_son[0] is None or simdi - kiyas_son[0] >= pd.Timedelta(hours=1)):
            kiyas_son[0] = simdi
            kiyas_btc_guncelle(ist, tohum_dizin, simdi, p)
        o = _durum_yaz(p, kaynak, durum_dizini, simdi, veri_dizini=tohum_dizin)   # kıyas/güven okuması = tohum dizini (sunucuda StateDirectory)
        if n:
            p.kaydet()
        if ozet_zamani(p, simdi):
            dun = dun_tsi(simdi)
            tg.gonder(tg.ozet_metni(o, dun=dun_ozeti(p, dun)))
            p.son_ozet = dun                   # gönderim başarısız olsa da işaretlenir (her turda yeniden deneme seli olmasın; log'da görünür)
            p.kaydet()                         # yeniden başlatmada aynı gün tekrar gitmesin

    if tek_sefer:
        tur()
        p.kaydet()
        return 0

    def geri_yukle():
        """Hata sonrası: bellekteki (yarım işlenmiş olabilecek) durum atılır, son tutarlı kayıt yüklenir; olay/uyarı listesi korunur."""
        olaylar, uyarilar = list(p.olaylar), list(p.uyarilar)
        p.motor._acil = False
        if not p.yukle(ayar_guncelle=True, olay_yaz=False):
            raise RuntimeError("geri yüklenecek kayıtlı durum yok")
        p.olaylar, p.uyarilar = olaylar, uyarilar

    def kalici_yaz():
        p.kaydet()
        _durum_yaz(p, kaynak, durum_dizini, pd.Timestamp.now(tz="UTC"), veri_dizini=tohum_dizin)

    koruyucu = TurKoruyucu(p, geri_yukle, kalici_yaz, binance_hata=pv.BinanceHata)

    async def ana() -> int:
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
        try:
            while not durdur.is_set():
                if not await loop.run_in_executor(None, koruyucu.calistir, tur):
                    break                                                   # aynı hata art arda HATA_TEKRAR_SINIRI kez: kontrollü dur
                try:
                    await asyncio.wait_for(tetik.wait(), timeout=pc.YOKLAMA_SN)
                except asyncio.TimeoutError:
                    pass
                tetik.clear()
                await asyncio.sleep(pc.GRACE_SN)
        finally:
            ws.cancel()
            p.kalp_at(pd.Timestamp.now(tz="UTC"), durum_dizini, durdu=True)      # kapanış: kapanış ile açılış arası ölçülür
            if koruyucu.tutarli:
                p.kaydet()
            else:
                log.error("bellekteki durum tutarsız (geri yükleme başarısız): kayıt YAZILMADI, son tutarlı kayıt diskte duruyor")
        return koruyucu.cikis_kodu
    return asyncio.run(ana())


# ---------------------------------------------------------------------------- servis yardımcıları (hata koruması, günlük özet, kıyas)
HATA_TEKRAR_SINIRI = 5


class TurKoruyucu:
    """Servis turunu sarar. Sessiz yutma YOK: her hata loga (traceback ile) ve olaylar'a yazılır, Telegram'a 'motor hatası' gider.
    BinanceHata: geçici sayılır (olay + log, tur tekrar denenir; eski davranış). Diğer her istisna: bellekteki durum son tutarlı
    kayda geri döner (yarım işlenmiş satır iki kez uygulanmasın), olay + bildirim; AYNI hata art arda `sinir` kez olursa kontrollü
    durulur (calistir False döner, cikis_kodu=1 -> systemd yeniden başlatır / OnFailure bildirir). Geri yükleme de başarısızsa hemen durulur."""

    def __init__(self, p: "Paper", geri_yukle, kalici_yaz=None, sinir: int = HATA_TEKRAR_SINIRI, binance_hata=None):
        self.p, self.geri_yukle, self.kalici_yaz, self.sinir = p, geri_yukle, kalici_yaz, sinir
        self.binance_hata = binance_hata or ()
        self.imza: Optional[str] = None
        self.sayi = 0
        self.cikis_kodu = 0
        self.tutarli = True

    def calistir(self, tur_fn) -> bool:
        from motor.canli.telegram import maskele
        try:
            tur_fn()
        except self.binance_hata as e:
            self.p.olay_ekle("binance_hata", maskele(str(e))[:300])
            log.error("tur başarısız: %s", maskele(str(e)))
            return True
        except Exception as e:  # noqa: BLE001  (sessiz değil: log + olay + Telegram; tekrarda kontrollü dur)
            imza = maskele(f"{type(e).__name__}: {e}")[:300]
            self.sayi = self.sayi + 1 if imza == self.imza else 1
            self.imza = imza
            iz = traceback.extract_tb(e.__traceback__)
            yer = f" @ {Path(iz[-1].filename).name}:{iz[-1].lineno} ({iz[-1].name})" if iz else ""
            log.error("tur başarısız (motor hatası, art arda %d/%d): %s\n%s", self.sayi, self.sinir, imza,
                      maskele("".join(traceback.format_exception(e))))
            try:
                self.geri_yukle()
                geri = "bellek son tutarlı kayda döndürüldü"
            except Exception as e2:  # noqa: BLE001
                self.tutarli = False
                log.error("geri yükleme başarısız: %s", maskele("".join(traceback.format_exception(e2))))
                geri = f"GERİ YÜKLEME BAŞARISIZ ({maskele(type(e2).__name__ + ': ' + str(e2))[:150]})"
            simdi = pd.Timestamp.now(tz="UTC")
            self.p.olay_ekle("motor_hatasi", f"{imza}{yer}; art arda {self.sayi}/{self.sinir}; {geri}", simdi)
            dur = (not self.tutarli) or self.sayi >= self.sinir
            if dur:
                self.cikis_kodu = 1
                self.p.olay_ekle("motor_durdu", (f"aynı hata art arda {self.sayi} kez" if self.tutarli else "durum geri yüklenemedi")
                                 + f": {imza[:200]}. Motor durdu (çıkış kodu 1); systemd yeniden başlatır.", simdi)
            if self.tutarli and self.kalici_yaz is not None:
                try:
                    self.kalici_yaz()
                except Exception as e3:  # noqa: BLE001
                    log.error("hata sonrası durum yazılamadı: %s", maskele(f"{type(e3).__name__}: {e3}"))
            return not dur
        self.imza, self.sayi = None, 0
        return True


def dun_tsi(simdi) -> str:
    """Sunucu zamanına (UTC) göre bir önceki TSİ günü 'YYYY-MM-DD'."""
    from motor.canli import durum_ek as ek
    return str((pd.Timestamp(simdi).tz_convert(ek.TSI) - pd.Timedelta(days=1)).date())


OZET_SAAT_TSI = (0, 10)                       # günlük özet: TSİ 00:10'dan sonra, biten TSİ günü için (günde bir kez)


def ozet_zamani(p: "Paper", simdi) -> bool:
    """Günlük özet gönderilmeli mi: TSİ saati >= 00:10 ve biten TSİ günü (dün) için henüz gönderilmedi (p.son_ozet, state'te)."""
    from motor.canli import durum_ek as ek
    yer = pd.Timestamp(simdi).tz_convert(ek.TSI)
    return (yer.hour, yer.minute) >= OZET_SAAT_TSI and p.son_ozet != dun_tsi(simdi)


def dun_ozeti(p: "Paper", gun: str) -> dict:
    """Biten TSİ günü `gun` için tam gün K/Z: o günün son özsermayesi - önceki TSİ gününün son özsermayesi (pano ile aynı tanım,
    motor.gun_kapanis_tsi). -> {gun, pnl, getiri, not}."""
    gk = p.motor.gun_kapanis_tsi
    bas = Decimal(str(p.ayarlar.baslangic_sermaye))
    onceki = [g for g in gk if g < gun]
    e0 = Decimal(gk[max(onceki)]) if onceki else bas
    son = [g for g in gk if g <= gun]
    e1 = Decimal(gk[max(son)]) if son else e0
    pnl = e1 - e0
    notu = None if gun in gk else "o gün işlenen mum yok (değişim 0)"
    return {"gun": gun, "pnl": pnl, "getiri": float(pnl / e0) if e0 > 0 else 0.0, "not": notu}


KIYAS_SEMBOL, KIYAS_TF = "BTCUSDT", "1h"


def kiyas_btc_guncelle(ist, tohum_dizin: Path, simdi, p: Optional["Paper"] = None) -> Optional[int]:
    """BTC al-tut kıyası (kiyas.py, tohum dizinindeki BTCUSDT 1h dosyasını okur) bayatlamasın: Binance'ten kapanmış 1h mumları alınır,
    mevcut dosyaya eklenip ATOMİK yazılır (geçici dosya + replace). kiyas.py değişmez. Araştırma veri dizini (depo içi veri/mumlar)
    REDDEDİLİR (araştırma verisine yazılmaz). Hata (Binance/disk): log + uyarı, tur düşmez (sonraki saatte yeniden denenir).
    -> eklenen mum sayısı | None (yazılmadı)."""
    from motor.veri import depo
    try:
        if Path(tohum_dizin).resolve() == (KOK / "veri" / "mumlar").resolve():
            log.info("kıyas BTC güncellemesi atlandı: tohum dizini araştırma veri dizini (yazılmaz)")
            return None
        yol = depo.mum_yolu(KIYAS_SEMBOL, KIYAS_TF, Path(tohum_dizin))
        eski = pd.read_parquet(yol) if yol.exists() else None
        if eski is not None and len(eski):
            bas = eski.index[-1] + pd.Timedelta(hours=1)
        else:
            ilk = min(p.motor.gun_kapanis_tsi) if (p is not None and p.motor.gun_kapanis_tsi) else None
            bas = (pd.Timestamp(ilk, tz="UTC") if ilk else pd.Timestamp(simdi)) - pd.Timedelta(days=30)
        if pd.Timestamp(simdi) < bas + pd.Timedelta(hours=1):
            return 0
        yeni = ist.klines(KIYAS_SEMBOL, KIYAS_TF, bas, None, pd.Timestamp(simdi))
        if not len(yeni):
            return 0
        df = yeni if eski is None else pd.concat([eski, yeni[~yeni.index.isin(eski.index)]]).sort_index()
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_name(yol.name + ".tmp")
        df.to_parquet(gecici)
        gecici.replace(yol)
        return len(df) - (0 if eski is None else len(eski))
    except Exception as e:  # noqa: BLE001  (sessiz değil: log + uyarı; kıyas yalnız gösterge, motoru durdurmaz)
        msg = f"kıyas BTC 1h güncellenemedi: {type(e).__name__}: {str(e)[:200]}"
        log.error(msg)
        if p is not None:
            p.uyarilar.append(msg)
        return None


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
    return canli_calistir(Path(a.durum), Path(a.tohum) if a.tohum else None, a.ayar_guncelle, a.tek_sefer)   # != 0: kontrollü hata durması


if __name__ == "__main__":
    raise SystemExit(main())
