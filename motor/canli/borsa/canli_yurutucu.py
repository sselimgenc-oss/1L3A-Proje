"""Canlı yürütücü: paper motorunun NİYETLERİNİ (aç / kapat / stop yükselt) tek strateji = tek Binance hesabı için gerçek emre çevirir.

Karar mantığı BURADA DEĞİLDİR: sinyal yolu paper motorunun kendisidir (köprü: motor_kopru.py). Burası yalnız
  - borsa filtrelerine göre boyutlandırır, CANLI_LIMITLER'i (canli_limitler.py; kullanıcı kararı 2026-11-11) yuvarlanmış miktarla ve kasayla doğrular (kurallar.py),
  - girişten HEMEN sonra borsa tarafında STOP_MARKET (reduceOnly) kurar; kurulamazsa pozisyonu hemen kapatır (çıplak pozisyon yok),
  - her turda borsayı doğruluk kaynağı sayıp mutabakat yapar (stopsuz / bilinmeyen / kayıp pozisyon),
  - kasada günlük -%6'da o gün YENİ girişi bloklar (açık pozisyonlar kapatılmaz); zirveden -%30'da (strateji) ya da hesap toplamında -%20'de (calistir.py) kapatıp KALICI durur (kill),
  - idempotent newClientOrderId kullanır (yeniden başlatma çift emir üretmez).
Modlar: kuru (hiçbir şey gönderilmez; KuruBorsa), testnet, canli (CANLI_ONAY=evet gerekir; bkz. canli_ayar).
Bilinmeyen pozisyon için ASLA otomatik işlem yapılmaz (yalnız uyarı). Bu dosyada gizli anahtar yoktur ve loga yazılmaz.
"""
from __future__ import annotations

import hashlib
import html
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from motor.strateji import cikislar as cks

from motor.canli.borsa.binance_futures import BorsaHata, EmirReddi
from motor.canli.borsa import canli_kayit as ck
from motor.canli.borsa import canli_limitler as cl
from motor.canli.borsa.kurallar import KuralHatasi, SembolKurali, boyutlandir, hedef_yuvarla, kural_cikar, stop_yuvarla

log = logging.getLogger("canli.yurutucu")
D = Decimal
ONEK = "1l3a"
HATA_BLOK_SINIRI = 3
SONLANMIS = {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED", "FILLED", "TRIGGERED", "FINISHED", "EXPIRED_IN_MATCH"}


# ---------------------------------------------------------------------------- motor -> yürütücü sözleşmesi
@dataclass
class Niyet:
    """Paper motorunun bu turda borsada yapılmasını istediği eylem."""
    tur: str                       # "ac" | "kapat"
    kol: str
    sembol: str                    # strateji sembolü (DK_... ya da BTCUSDT)
    yon: int = 0
    stop: Optional[Decimal] = None
    hedef: Optional[Decimal] = None
    sinyal_zamani: Optional[pd.Timestamp] = None   # sinyali üreten barın AÇILIŞ zamanı
    aralik: pd.Timedelta = pd.Timedelta(hours=1)
    neden: str = ""
    risk_oran: Decimal = D("0.01")     # paper alanı; CANLIDA KULLANILMAZ (canlı risk kuralı canli_limitler.py'de sabit)
    grup_payi: Decimal = D(1)          # paper alanı; canlıda kullanılmaz
    stop_kayma: Decimal = D("0.0005")
    taker: Decimal = D("0.0005")
    sabit_r: Optional[float] = None    # CikisAyarlari.sabit_r_hedefi: paper hedefi dolum fiyatından türetir; canlıda GERÇEK dolumdan aynı formülle


@dataclass
class PozGorunum:
    sembol: str
    yon: int
    stop: Decimal
    hedef: Optional[Decimal] = None


@dataclass
class MotorGorunumu:
    niyetler: list = field(default_factory=list)
    pozlar: dict = field(default_factory=dict)         # {kol: PozGorunum} paper motorunun açık pozisyonları
    kollar: dict = field(default_factory=dict)         # {kol: strateji sembolü}
    son_satir: dict = field(default_factory=dict)      # {kol: son işlenen satırın açılış zamanı}
    aralik: dict = field(default_factory=dict)         # {kol: bar süresi}


@dataclass
class Ayar:
    mod: str = "testnet"                  # kuru | testnet | canli
    tahsis: Decimal = D(1000)
    islem_risk: Optional[Decimal] = None  # None: yalnız CANLI_LIMITLER %3 tavanı (doğrudan kullanım); calistir.py yapılandırmadan HER ZAMAN verir
    working_type: str = "MARK_PRICE"      # MARK_PRICE | CONTRACT_PRICE
    giris_gecikme_max_sn: int = 900       # sinyal barı kapandıktan en geç bu kadar sonra giriş; sonrası atlanır
    hedef_emri: bool = True               # stratejinin hedefi varsa TAKE_PROFIT_MARKET kur


def client_id(rol: str, strateji: str, kol: str, zaman, ek: str = "") -> str:
    """Belirleyici emir kimliği (<=36 karakter). Aynı (strateji, kol, sinyal zamanı, rol, ek) -> aynı kimlik."""
    h = hashlib.sha1(f"{strateji}|{kol}|{pd.Timestamp(zaman).isoformat()}|{ek}".encode()).hexdigest()[:24]
    return f"{ONEK}-{rol}-{h}"


def _yon_taraf(yon: int) -> str:
    return "BUY" if yon == 1 else "SELL"




def _aktif(o: Optional[dict]) -> bool:
    """Emir borsada hâlâ geçerli mi (iptal/süresi dolmuş/reddedilmiş/dolmuş DEĞİL). Durum bilinmiyorsa (boş) aktif sayılır."""
    return o is not None and str(o.get("durum", "")).upper() not in SONLANMIS


class Yurutucu:
    def __init__(self, strateji: str, borsa, bilgi: dict, ayar: Ayar, durum_yolu: Optional[Path] = None,
                 olay: Optional[Callable] = None, bildir: Optional[Callable] = None, saat: Optional[Callable] = None,
                 sembol_esle: Optional[Callable] = None):
        from motor.canli.paper_veri import binance_sembol
        self.sid, self.borsa, self.bilgi, self.ayar = strateji, borsa, bilgi, ayar
        self.durum_yolu = Path(durum_yolu) if durum_yolu else None
        self._olay, self._bildir = olay, bildir
        self.saat = saat or (lambda: pd.Timestamp.now(tz="UTC"))
        self.esle = sembol_esle or binance_sembol
        self.durum = self._yukle()
        self._hazir: set = set()
        self._uyarilan: set = set()
        self._ardisik_hata = 0
        self.kurallar: dict = {}
        self.kayit_dizin = self.durum_yolu.parent if self.durum_yolu else None     # KAYIT dosyaları (canli_kayit.py); işlem mantığına bağlı değil
        self.kayit_hata_sayisi: dict = {}
        self._tur_kapat: dict = {}
        self._tur_oncesi: dict = {}
        self._kayit_basladi = False

    # ------------------------------------------------------------------ durum / olay
    def _bos(self) -> dict:
        return {"surum": 1, "strateji": self.sid, "zirve": None, "gun": None, "gun_basi": None, "kill": False, "kill_neden": None,
                "gun_blok": False, "islenen": {}, "pozlar": {}}

    def _yukle(self) -> dict:
        import json
        if self.durum_yolu and self.durum_yolu.exists():
            d = json.loads(self.durum_yolu.read_text(encoding="utf-8"))
            if d.get("strateji") != self.sid:
                raise RuntimeError(f"{self.durum_yolu}: başka strateji için ({d.get('strateji')})")
            return d
        return self._bos()

    def _kaydet(self) -> None:
        if self.durum_yolu:
            from motor.canli.durum import atomik_yaz_json
            self.durum_yolu.parent.mkdir(parents=True, exist_ok=True)
            self.durum["islenen"] = dict(sorted(self.durum["islenen"].items(), key=lambda kv: kv[1])[-500:])
            atomik_yaz_json(self.durum_yolu, self.durum)

    def olay(self, tur: str, mesaj: str, bildir: bool = True) -> None:
        log.info("canlı olay %s [%s]: %s", tur, self.sid, mesaj)
        self._olay_kaydet(tur, mesaj)
        if self._olay:
            self._olay(tur, f"[{self.sid}] {mesaj}")
        if bildir and self._bildir:
            self._bildir(f"🔴 <b>1L3A CANLI</b> ({html.escape(self.ayar.mod)}) · {html.escape(self.sid)}\n<b>{html.escape(tur)}</b>: {html.escape(mesaj[:600])}")

    def _bir_kez(self, anahtar: str, tur: str, mesaj: str) -> None:
        """Aynı koşul sürerken aynı uyarı tekrar gönderilmez (koşul `_uyari_sil` ile sıfırlanınca yeniden mümkün)."""
        if anahtar not in self._uyarilan:
            self._uyarilan.add(anahtar)
            self.olay(tur, mesaj)

    def _uyari_sil(self, onek: str) -> None:
        self._uyarilan = {a for a in self._uyarilan if not a.startswith(onek)}

    def _kural(self, bs: str) -> SembolKurali:
        if bs not in self.kurallar:
            self.kurallar[bs] = kural_cikar(self.bilgi, bs)
        return self.kurallar[bs]

    # ------------------------------------------------------------------ ana tur
    def adim(self, g: MotorGorunumu) -> None:
        """Bir tur. İstisnayı yutmaz ama paper turunu da düşürmez: hata loglanır + olay + Telegram; art arda 3 hatada yeni giriş bloklanır."""
        self._tur_kapat = {}
        self._tur_oncesi = {k: dict(v) for k, v in self.durum["pozlar"].items()}      # kayıt için tur öncesi görüntü (yalnız okuma)
        try:
            self._adim(g)
            self._ardisik_hata = 0
        except Exception as e:  # noqa: BLE001  (sessiz değil: log + olay + Telegram; yeni giriş art arda hatada bloklanır)
            self._ardisik_hata += 1
            self.olay("canli_yurutucu_hatasi", f"{type(e).__name__}: {e} (art arda {self._ardisik_hata}/{HATA_BLOK_SINIRI})")
            log.exception("yürütücü turu başarısız")
        finally:
            self._kayit_tur_sonu()
            self._kaydet()

    def _poz(self) -> dict:
        return {p["sembol"]: p for p in self.borsa.pozisyonlar()}

    def _adim(self, g: MotorGorunumu) -> None:
        simdi = self.saat()
        E = self.kasa_oku()      # kasa = min(borsa özsermayesi, tahsis): boyutlandırma, günlük -%6 ve kill -%30 hepsi bunun üzerinden
        self._risk_izle(E, simdi)
        poz = self._poz()
        if self.durum["kill"]:                                  # kill (strateji -%30 / hesap -%20): hepsini kapat, kalıcı dur
            self._hepsini_kapat(poz, self.durum["kill_neden"] or "kill_switch", g)
            return
        self._mutabakat(g, poz)
        poz = self._poz()
        for n in [x for x in g.niyetler if x.tur == "kapat"]:
            self._kapat_niyeti(n, poz)
        if self.durum["gun_blok"]:                              # günlük -%6: YALNIZ yeni giriş yok (açık pozisyonlar stop + strateji çıkışıyla sürer); ertesi UTC günü açılır
            for n in [x for x in g.niyetler if x.tur == "ac"]:
                gid = client_id("G", self.sid, n.kol, n.sinyal_zamani)
                if gid not in self.durum["islenen"] and n.kol not in self.durum["pozlar"]:
                    self.durum["islenen"][gid] = str(simdi)
                    self.olay("canli_giris_atlandi", f"{n.kol}: günlük kayıp limiti (-%{cl.CANLI_LIMITLER.gunluk_max_kayip_oran * 100:g}) aşıldı; bugün yeni giriş yok", bildir=False)
        else:
            for n in [x for x in g.niyetler if x.tur == "ac"]:
                self._ac_niyeti(n, g, E, simdi)
        self._stop_yukselt(g, self._poz())

    # ------------------------------------------------------------------ kasa / kill switch
    def kasa_oku(self) -> Decimal:
        """Bu strateji hesabının kasası = min(borsa özsermayesi, tahsis edilen sermaye)."""
        return min(self.borsa.bakiye()["ozsermaye"], self.ayar.tahsis)

    def _risk_izle(self, E: Decimal, simdi) -> None:
        for tur, mesaj in cl.gunluk_kill_guncelle(self.durum, E, str(pd.Timestamp(simdi).date())):
            self.olay(tur, mesaj)
        if not self.durum["gun_blok"]:
            self._uyari_sil("gunluk")

    def hesap_kill_ver(self, mesaj: str) -> None:
        """Hesap düzeyi kill (calistir.py toplam kasayı izler): bu stratejiyi de kalıcı durdurur; sonraki turda pozisyonlar kapatılır."""
        if not self.durum["kill"]:
            self.durum["kill"], self.durum["kill_neden"] = True, "hesap_kill"
            self.olay("canli_kill_switch", mesaj)
            self._kaydet()

    def _hepsini_kapat(self, poz: dict, neden: str, g: MotorGorunumu) -> None:
        """ÖNCE reduceOnly piyasa ile kapat; emirler (stoplar) YALNIZ pozisyonun sıfırlandığı borsada doğrulanınca iptal edilir.
        Kapatma başarısızsa stoplar yerinde kalır, her turda yeniden denenir ve mutabakat stopları korur."""
        sorun = False
        for bs, p in poz.items():
            if self._piyasa_kapat(bs, p["miktar"], client_id("K", self.sid, bs, self.saat().floor("min"), neden), neden):
                self._uyari_sil(f"kapatma:{bs}")
            else:
                sorun = True
        kalan = self._poz()
        for bs in sorted((set(poz) | {r["bsembol"] for r in self.durum["pozlar"].values()}) - set(kalan)):
            try:
                self.borsa.hepsini_iptal(bs)
            except BorsaHata as e:
                self._bir_kez(f"killiptal:{bs}", "canli_kill_hatasi", f"{bs} kalan emirler iptal edilemedi: {e}")
                continue
            self.durum["pozlar"] = {k: r for k, r in self.durum["pozlar"].items() if r["bsembol"] != bs}
        if kalan:
            sorun = True
        if sorun:
            self._bir_kez("kill_kapatilamadi", "canli_kill_hatasi", f"pozisyon(lar) kapatılamadı: {sorted(kalan)}; stoplar yerinde, her turda yeniden denenecek. ELLE KONTROL EDİN")
            self._mutabakat(g, kalan)

    # ------------------------------------------------------------------ yardımcı borsa işlemleri
    def _piyasa_kapat(self, bs: str, miktar: Decimal, cid: str, neden: str) -> bool:
        taraf = "SELL" if miktar > 0 else "BUY"
        try:
            self.borsa.piyasa(bs, taraf, abs(miktar), cid, reduce_only=True)
        except BorsaHata as e:
            if e.belirsiz:
                try:
                    if self.borsa.sorgula(bs, cid) is not None:
                        return True
                except BorsaHata:
                    pass
            self._bir_kez(f"kapatma:{bs}", "canli_kapatma_hatasi", f"{bs} kapatılamadı ({neden}): {e}")
            return False
        self.olay("canli_kapandi", f"{bs} {abs(miktar)} piyasa emriyle kapatıldı ({neden})")
        return True

    def _sil_emirler(self, bs: str) -> None:
        """Yalnız KENDİ emirlerimiz (1l3a- önekli) iptal edilir. Başarısızlık BorsaHata olarak yükselir."""
        for o in self.borsa.emirler(bs):
            if o["client_id"].startswith(ONEK + "-"):
                self.borsa.iptal(bs, o["client_id"], kosullu=o.get("kosullu", True))

    def _hazirla(self, bs: str, kaldirac: int) -> None:
        """İzole marj + one-way + bu girişin kaldıracı (stop mesafesine göre 3x/2x). Pozisyon yokken sembol başına her girişte ayarlanır."""
        if (bs, kaldirac) not in self._hazir:
            self.borsa.hazirla(bs, kaldirac)
            self._hazir = {h for h in self._hazir if h[0] != bs} | {(bs, kaldirac)}

    def _risk_ozeti(self, poz: dict) -> tuple:
        """(brüt nominal, açık stop riski) borsa pozisyonlarından; stopu bilinmeyen pozisyon tüm nominaliyle risk sayılır (tutucu)."""
        brut = risk = D(0)
        for bs, p in poz.items():
            q, mark = abs(p["miktar"]), p["mark"]
            brut += q * mark
            r = next((r for r in self.durum["pozlar"].values() if r["bsembol"] == bs), None)
            if r and r.get("stop"):
                yon = 1 if p["miktar"] > 0 else -1
                risk += max((mark - D(r["stop"])) * q * yon, D(0))
            else:
                risk += q * mark
        return brut, risk

    # ------------------------------------------------------------------ giriş
    def _ac_niyeti(self, n: Niyet, g: MotorGorunumu, E: Decimal, simdi) -> None:
        bs = self.esle(n.sembol)
        gid = client_id("G", self.sid, n.kol, n.sinyal_zamani)
        d = self.durum
        if gid in d["islenen"] or n.kol in d["pozlar"]:
            return
        if self._ardisik_hata >= HATA_BLOK_SINIRI:
            self._bir_kez("hata_blok", "canli_giris_blok", f"art arda {HATA_BLOK_SINIRI} yürütücü hatası: yeni giriş yapılmıyor")
            return
        gecikme = (pd.Timestamp(simdi) - (pd.Timestamp(n.sinyal_zamani) + n.aralik)).total_seconds()
        if gecikme > self.ayar.giris_gecikme_max_sn:
            d["islenen"][gid] = str(simdi)
            self.olay("canli_giris_atlandi", f"{n.kol}: sinyal barı {gecikme:.0f} sn önce kapandı (> {self.ayar.giris_gecikme_max_sn}); eski sinyalle girilmez", bildir=False)
            return
        try:
            k = self._kural(bs)
        except KuralHatasi as e:
            d["islenen"][gid] = str(simdi)
            self.olay("canli_giris_atlandi", f"{n.kol}: {e}")
            return
        poz = self._poz()
        if bs in poz:
            d["islenen"][gid] = str(simdi)
            self.olay("canli_giris_atlandi", f"{n.kol}: {bs} için borsada zaten pozisyon var; yeni giriş yapılmadı")
            return
        mark = self.borsa.mark_fiyat(bs)
        brut, risk = self._risk_ozeti(poz)
        stop = stop_yuvarla(n.stop, n.yon, k)
        ortak = dict(ozsermaye=E, tahsis=self.ayar.tahsis, islem_risk=self.ayar.islem_risk, yon=n.yon, stop=stop, kural=k,
                     stop_kayma=n.stop_kayma, taker=n.taker, diger_brut=brut, diger_stop_riski=risk)
        bo = boyutlandir(giris=mark, **ortak)
        if bo.neden is not None:
            d["islenen"][gid] = str(simdi)
            tur = "min_tutar_alti" if bo.neden == "min_tutar_alti" else "canli_giris_atlandi"
            self.olay(tur, f"{n.kol} ({bs}): {bo.neden}: {bo.ayrinti}")
            return
        self._hazirla(bs, bo.kaldirac)
        hedef = hedef_yuvarla(n.hedef, n.yon, k) if (n.hedef is not None and self.ayar.hedef_emri) else None
        rec = {"sembol": n.sembol, "bsembol": bs, "yon": n.yon, "qty": str(bo.qty), "stop": str(stop), "hedef": str(hedef) if hedef else None,
               "giris_bar": str(pd.Timestamp(n.sinyal_zamani)), "aralik_sn": int(n.aralik.total_seconds()), "durum": "gonderildi",
               "giris_id": gid, "stop_id": None, "hedef_id": None, "stop_deneme": 0, "kaldirac": bo.kaldirac}
        d["pozlar"][n.kol] = rec
        d["islenen"][gid] = str(simdi)
        self._kaydet()                                    # emirden ÖNCE yaz: belirsiz/çökme olursa mutabakat stopu buradaki kayıttan kurar
        self._kayit_acilis(n, bs, gid, E, stop, bo, mark)
        yanit, sonuc = self._giris_gonder(bs, n, bo.qty, gid)
        if sonuc == "yok":
            d["pozlar"].pop(n.kol, None)
            return
        if sonuc == "belirsiz":                           # kayıt 'gonderildi' kalır: borsada pozisyon görününce stop HEMEN kurulur (mutabakat)
            return
        qty, avg = yanit["dolan"], (yanit.get("ort_fiyat") or mark)
        rec.update(durum="acik", qty=str(qty), giris=str(avg))
        self._kayit_dolum(n.kol, yanit, qty, avg)
        self.olay("canli_emir_doldu", f"{n.kol} {bs} {'LONG' if n.yon == 1 else 'SHORT'} {qty} @ {avg} (stopta kayıp %{bo.risk_yuzde:.3f} kasa, brüt {bo.brut_kat:.2f}x, {bo.kaldirac}x, sınırlayan: {bo.baglayan})")
        qty = self._dolum_sonrasi_risk(n.kol, rec, qty, D(avg), ortak)
        if qty is None:
            return
        if n.hedef is None and n.sabit_r and self.ayar.hedef_emri:       # paper: sabit R hedefi DOLUM fiyatından; canlı da gerçek dolumdan aynı formülle
            rec["hedef"] = str(hedef_yuvarla(D(repr(cks.r_hedef_fiyati(n.yon, float(avg), float(abs(D(avg) - stop)), n.sabit_r))), n.yon, k))
        self._koru(n.kol, rec, qty)

    def _dolum_sonrasi_risk(self, kol: str, rec: dict, qty: Decimal, avg: Decimal, ortak: dict) -> Optional[Decimal]:
        """GERÇEK dolum fiyatı ve miktarıyla CANLI_LIMITLER yeniden doğrulanır (kayma riski artırmış olabilir). İhlalde pozisyon reduceOnly ile
        küçültülür (sığmıyorsa tamamen kapatılır). -> kalan miktar; None: pozisyon kapandı."""
        bs, yon = rec["bsembol"], rec["yon"]
        E = min(ortak["ozsermaye"], ortak["tahsis"])
        ihlal = cl.limit_ihlalleri(qty=qty, giris=avg, stop=D(rec["stop"]), kasa=E, stop_kayma=ortak["stop_kayma"], taker=ortak["taker"],
                                   kaldirac=rec.get("kaldirac") or 1, diger_brut=ortak["diger_brut"], diger_stop_riski=ortak["diger_stop_riski"])
        if not ihlal:
            return qty
        girdi = {k: v for k, v in ortak.items() if k != "stop"}
        yeni = boyutlandir(giris=avg, stop=D(rec["stop"]), kaldirac_ust=rec.get("kaldirac"), **girdi)
        if yeni.neden is not None or yeni.qty <= 0:
            self.olay("canli_risk_asimi", f"{kol} {bs}: gerçek dolumla sert limit aşıldı ({'; '.join(ihlal)}) ve küçültme mümkün değil; pozisyon kapatılıyor")
            if self._piyasa_kapat(bs, qty * yon, client_id("K", self.sid, kol, rec["giris_bar"], "risk_asimi"), "risk_asimi"):
                self.durum["pozlar"].pop(kol, None)
                return None
            return qty
        fazla = qty - yeni.qty
        self.olay("canli_risk_asimi", f"{kol} {bs}: gerçek dolumla ({avg}) sert limit aşıldı ({'; '.join(ihlal)}); {fazla} küçültülüyor, kalan {yeni.qty}")
        if fazla > 0 and self._piyasa_kapat(bs, fazla * yon, client_id("K", self.sid, kol, rec["giris_bar"], "risk_azalt"), "risk_azalt"):
            rec["qty"] = str(yeni.qty)
            return yeni.qty
        return qty

    def _giris_gonder(self, bs: str, n: Niyet, qty: Decimal, gid: str) -> tuple:
        """-> (yanıt | None, sonuç): 'doldu' | 'yok' (emir kesinlikle yok/dolmadı ve iptal edildi) | 'belirsiz' (sonuç bilinmiyor; kayıt korunur).
        Emir POST'u otomatik tekrar edilmez; belirsizlikte kimlikle sorgulanır, YALNIZ borsa 'böyle emir yok' derse bir kez yeniden gönderilir."""
        taraf = _yon_taraf(n.yon)
        try:
            y = self.borsa.sorgula(bs, gid)                  # yeniden başlatma: aynı kimlikli emir zaten gönderildi mi?
            if y is None:
                try:
                    y = self.borsa.piyasa(bs, taraf, qty, gid)
                except EmirReddi as e:
                    raise e
                except BorsaHata:
                    y = self.borsa.sorgula(bs, gid)
                    if y is None:                            # borsa: emir yok -> güvenle bir kez daha
                        y = self.borsa.piyasa(bs, taraf, qty, gid)
            if not y.get("dolan") or y["dolan"] <= 0:
                y = self.borsa.sorgula(bs, gid) or y
            if not y.get("dolan") or y["dolan"] <= 0:
                self.olay("canli_giris_hatasi", f"{n.kol} {bs}: giriş emri dolmadı (durum {y.get('durum')}); iptal ediliyor")
                self.borsa.iptal(bs, gid, kosullu=False)
                return None, "yok"
        except EmirReddi as e:
            self.olay("canli_giris_hatasi", f"{n.kol} {bs} giriş emri reddedildi: {e}")
            return None, "yok"
        except BorsaHata as e:
            self.olay("canli_giris_belirsiz", f"{n.kol} {bs}: giriş sonucu BELİRSİZ ({e}); kayıt korunuyor, pozisyon görünürse stop hemen kurulacak")
            return None, "belirsiz"
        return y, "doldu"

    def _koru(self, kol: str, rec: dict, qty: Decimal) -> bool:
        """Girişten hemen sonra borsa tarafı stop (+ hedef). Stop kurulamazsa pozisyon HEMEN kapatılır. -> stop kuruldu mu."""
        bs, yon = rec["bsembol"], rec["yon"]
        if not self._stop_kur(kol, rec, qty):
            self.olay("canli_stop_basarisiz", f"{kol} {bs}: stop kurulamadı; pozisyon HEMEN kapatılıyor (çıplak pozisyon yok)")
            kapandi = self._piyasa_kapat(bs, qty * yon, client_id("K", self.sid, kol, rec["giris_bar"], "stopsuz"), "stop_basarisiz")
            if kapandi:
                self.durum["pozlar"].pop(kol, None)
            else:
                self.olay("canli_stop_basarisiz", f"{kol} {bs}: KAPATMA DA BAŞARISIZ; pozisyon stopsuz olabilir, her turda yeniden denenecek. ELLE KONTROL EDİN")
            return False
        if rec.get("hedef") and self.ayar.hedef_emri and not rec.get("hedef_id"):
            self._hedef_kur(kol, rec, qty)
        return True

    def _stop_kur(self, kol: str, rec: dict, qty: Decimal, ek: str = "") -> bool:
        """Başarı YALNIZ borsada AKTİF (iptal/süresi dolmuş/dolmuş değil) stop varsa. Her yeniden kurulumda deneme sayacı kimliğe girer
        (eski, iptal edilmiş aynı kimlikli kayıt 'kuruldu' sayılmasın). Sayaç emirden önce diske yazılır."""
        bs, yon = rec["bsembol"], rec["yon"]
        rec["stop_deneme"] = rec.get("stop_deneme", 0) + 1
        cid = client_id("S", self.sid, kol, rec["giris_bar"], f"{rec['stop']}|{ek}|{rec['stop_deneme']}")
        self._kaydet()
        try:
            o = self.borsa.kosullu(bs, "STOP_MARKET", "SELL" if yon == 1 else "BUY", qty, D(rec["stop"]), cid, self.ayar.working_type)
            ok = _aktif(o)
        except BorsaHata as e:
            try:
                ok = _aktif(self.borsa.sorgula(bs, cid))      # sonuç belirsizse: kimlikle doğrula (yalnız AKTİF ise başarı)
            except BorsaHata:
                ok = False
            if not ok:
                log.warning("%s %s stop emri hatası: %s", kol, bs, e)      # çağıran raporlar (stop_basarisiz / stop yükseltme uyarısı; tekrar yok)
        if ok:
            rec["stop_id"] = cid
            self.olay("canli_stop_kuruldu", f"{kol} {bs} STOP_MARKET reduceOnly {qty} @ {rec['stop']} ({self.ayar.working_type})")
        return ok

    def _hedef_kur(self, kol: str, rec: dict, qty: Decimal) -> None:
        bs, yon = rec["bsembol"], rec["yon"]
        cid = client_id("T", self.sid, kol, rec["giris_bar"], rec["hedef"])
        try:
            o = self.borsa.kosullu(bs, "TAKE_PROFIT_MARKET", "SELL" if yon == 1 else "BUY", qty, D(rec["hedef"]), cid, self.ayar.working_type)
            if _aktif(o):
                rec["hedef_id"] = cid
        except BorsaHata as e:                              # hedef olmadan da pozisyon stopla korunur: uyarı, kapatma yok
            self.olay("canli_hedef_hatasi", f"{kol} {bs}: hedef emri kurulamadı (stop var): {e}")

    # ------------------------------------------------------------------ çıkış / stop
    def _kapat_rec(self, kol: str, rec: dict, p: dict, neden: str) -> bool:
        """Pozisyonu kapat; kayıt YALNIZ kalan emirler de iptal edilince silinir (yetim reduceOnly emir kalmasın)."""
        bs = rec["bsembol"]
        if not self._piyasa_kapat(bs, p["miktar"], client_id("K", self.sid, kol, rec["giris_bar"], neden), neden):
            return False
        try:
            self._sil_emirler(bs)
        except BorsaHata as e:
            self._bir_kez(f"iptal:{bs}", "canli_iptal_hatasi", f"{bs} kalan emirler iptal edilemedi ({e}); kayıt tutuluyor, her turda yeniden denenecek")
            return True
        self.durum["pozlar"].pop(kol, None)
        return True

    def _kapat_niyeti(self, n: Niyet, poz: dict) -> None:
        rec = self.durum["pozlar"].get(n.kol)
        if rec is None or rec["bsembol"] not in poz:
            return
        self._kapat_rec(n.kol, rec, poz[rec["bsembol"]], n.neden)

    def _stop_yukselt(self, g: MotorGorunumu, poz: dict) -> None:
        """Paper stopu lehe yükseldiyse: yeni stop ÖNCE kurulur, sonra eskisi iptal (stopsuz an yok). Gevşetme yok. Fiyat yeni stopu zaten
        geçtiyse piyasada kapatılır; paper yönü kayıttan farklıysa kapatılır. Aynı koşul için uyarı bir kez."""
        for kol, rec in list(self.durum["pozlar"].items()):
            pg, bs = g.pozlar.get(kol), rec["bsembol"]
            if pg is None or rec["durum"] != "acik" or bs not in poz:
                continue
            p, yon = poz[bs], rec["yon"]
            if pg.yon != yon:
                self.olay("canli_uyusmazlik", f"{kol} {bs}: paper yönü ({pg.yon}) kayıttan ({yon}) farklı; borsada kapatılıyor")
                self._kapat_rec(kol, rec, p, "yon_degisti")
                continue
            k = self._kural(bs)
            yeni = stop_yuvarla(pg.stop, yon, k)
            if (yeni - D(rec["stop"])) * yon <= 0:
                continue
            if (p["mark"] - yeni) * yon <= 0:                    # fiyat yeni stopun ötesinde: borsa stopu kabul etmez -> kapat
                self.olay("canli_uyusmazlik", f"{kol} {bs}: paper stopu {yeni} fiyatın ({p['mark']}) ötesinde; piyasada kapatılıyor")
                self._kapat_rec(kol, rec, p, "stop_asildi")
                continue
            eski_id, eski = rec["stop_id"], rec["stop"]
            rec["stop"] = str(yeni)
            if self._stop_kur(kol, rec, abs(p["miktar"])):
                self._uyari_sil(f"stopyuk:{kol}")
                if eski_id:
                    try:
                        self.borsa.iptal(bs, eski_id, kosullu=True)
                    except BorsaHata as e:
                        self._bir_kez(f"iptal:{bs}:{eski_id}", "canli_iptal_hatasi", f"{kol}: eski stop iptal edilemedi: {e}")
            else:
                rec["stop"], rec["stop_id"] = eski, eski_id           # yeni kurulamadı: eski stop yerinde kalır
                self._bir_kez(f"stopyuk:{kol}:{yeni}", "canli_stop_hatasi", f"{kol}: stop yükseltilemedi ({eski} -> {yeni}); eski stop yerinde")

    # ------------------------------------------------------------------ mutabakat (borsa doğruluk kaynağı)
    def _mutabakat(self, g: MotorGorunumu, poz: dict) -> None:
        d = self.durum
        bs_kol = {self.esle(s): kol for kol, s in g.kollar.items()}
        tum_emirler = self.borsa.emirler()
        benim = [o for o in tum_emirler if o["client_id"].startswith(ONEK + "-") and _aktif(o)]
        for bs, p in poz.items():
            yon = 1 if p["miktar"] > 0 else -1
            kol = bs_kol.get(bs)
            rec = d["pozlar"].get(kol) if kol else None
            if kol is None or (rec is None and not (kol in g.pozlar and g.pozlar[kol].yon == yon)):
                self._bir_kez(f"bilinmeyen:{bs}:{p['miktar']}", "canli_uyusmazlik",
                              f"BİLİNMEYEN pozisyon: {bs} {p['miktar']}; stratejinin beklemediği bir pozisyon. Otomatik işlem YAPILMADI, elle bakın")
                continue
            aralik_sn = int(g.aralik[kol].total_seconds()) if kol in g.aralik else 0
            if rec is None:                                   # durum kaybı: motor da pozisyonu biliyor -> benimse
                pg = g.pozlar[kol]
                rec = d["pozlar"][kol] = {"sembol": pg.sembol, "bsembol": bs, "yon": yon, "qty": str(abs(p["miktar"])), "stop": str(pg.stop),
                                          "hedef": str(pg.hedef) if pg.hedef else None, "giris_bar": str(g.son_satir.get(kol, self.saat())),
                                          "aralik_sn": aralik_sn, "durum": "acik", "giris_id": None, "stop_id": None, "hedef_id": None,
                                          "giris": str(p["giris"]), "stop_deneme": 0}
                self.olay("canli_uyusmazlik", f"{kol} {bs}: kayıtsız pozisyon motorla eşleşti, benimsendi")
            if rec["yon"] != yon:
                self._bir_kez(f"yon:{bs}", "canli_uyusmazlik", f"{kol} {bs}: borsa yönü kayıttan farklı; otomatik işlem yok, elle bakın")
                continue
            self._uyari_sil(f"yon:{bs}")
            if rec["durum"] == "gonderildi":                  # belirsiz/çökmüş giriş borsada doğrulandı -> gerçek miktar/fiyatla 'acik'
                rec.update(durum="acik", qty=str(abs(p["miktar"])), giris=str(p["giris"]))
                if not rec.get("aralik_sn"):
                    rec["aralik_sn"] = aralik_sn
                self.olay("canli_uyusmazlik", f"{kol} {bs}: 'gönderildi' kaydı borsa pozisyonuyla doğrulandı ({abs(p['miktar'])} @ {p['giris']}); stop hemen kontrol ediliyor")
            qty = abs(p["miktar"])
            ts = g.son_satir.get(kol)
            if kol not in g.pozlar and ts is not None and rec.get("aralik_sn") and \
                    pd.Timestamp(ts) >= pd.Timestamp(rec["giris_bar"]) + pd.Timedelta(seconds=rec["aralik_sn"]) and \
                    not any(n.kol == kol and n.tur == "ac" for n in g.niyetler):
                self.olay("canli_uyusmazlik", f"{kol} {bs}: paper motoru pozisyonu kapattı ama borsada açık; borsada da kapatılıyor")
                self._kapat_rec(kol, rec, p, "motor_kapali")
                continue
            step = self._kural(bs).market_step
            stoplar = [o for o in benim if o["sembol"] == bs and o["tur"] == "STOP_MARKET" and o["reduce_only"]]
            uygun = [o for o in stoplar if abs(o["miktar"] - qty) < step]
            if not stoplar:
                self.olay("canli_uyusmazlik", f"{kol} {bs}: pozisyon STOPSUZ; kayıtlı stop {rec['stop']} kuruluyor")
                rec["stop_id"] = None
                self._koru(kol, rec, qty)
            elif not uygun:
                self.olay("canli_uyusmazlik", f"{kol} {bs}: stop miktarı ({stoplar[0]['miktar']}) pozisyondan ({qty}) farklı; yeniden kuruluyor")
                if self._stop_kur(kol, rec, qty, ek=str(qty)):
                    for o in stoplar:
                        if o["client_id"] != rec["stop_id"]:        # yeni kurulanı ASLA iptal etme
                            self.borsa.iptal(bs, o["client_id"], kosullu=True)
            elif rec.get("stop_id") not in {o["client_id"] for o in uygun}:
                rec["stop_id"] = uygun[-1]["client_id"]             # borsadaki uygun stop devralındı (kayıt eskimişti)
            if rec.get("hedef") and self.ayar.hedef_emri and not rec.get("hedef_id") and \
                    not any(o["sembol"] == bs and o["tur"] == "TAKE_PROFIT_MARKET" for o in benim):
                self._hedef_kur(kol, rec, qty)
        # kayıtlı olup borsada pozisyonu olmayanlar: kayıt YALNIZ kalan emirler iptal edildikten sonra silinir
        for kol, rec in list(d["pozlar"].items()):
            bs = rec["bsembol"]
            if bs in poz:
                continue
            if rec["durum"] == "gonderildi":                  # emir sonucu belirsiz kalmıştı
                try:
                    y = self.borsa.sorgula(bs, rec["giris_id"])
                except BorsaHata:
                    continue                                  # hâlâ bilinmiyor: kayıt korunur
                if y is not None and y.get("dolan") and not any(o["sembol"] == bs for o in benim):
                    pass                                      # doldu ve zaten kapandı (stop çalıştı)
                elif y is None or not y.get("dolan"):
                    d["pozlar"].pop(kol)
                    continue
            try:
                self._sil_emirler(bs)
            except BorsaHata as e:
                self._bir_kez(f"iptal:{bs}", "canli_iptal_hatasi", f"{kol} {bs}: kalan emirler iptal edilemedi ({e}); kayıt tutuluyor, yeniden denenecek")
                continue
            d["pozlar"].pop(kol)
            self._uyari_sil(f"iptal:{bs}")
            self.olay("canli_uyusmazlik", f"{kol} {bs}: borsada pozisyon yok (stop/hedef çalışmış ya da elle kapatılmış olabilir); kayıt temizlendi, kalan emirler iptal")
        # yetim reduceOnly emirler: pozisyonu olmayan sembolde kalan kendi emirlerimiz sonradan açılacak pozisyonu kapatabilir -> iptal
        for o in benim:
            if o["reduce_only"] and o["sembol"] not in poz and not any(r["bsembol"] == o["sembol"] and r["durum"] == "gonderildi" for r in d["pozlar"].values()):
                try:
                    self.borsa.iptal(o["sembol"], o["client_id"], kosullu=o.get("kosullu", True))
                    self.olay("canli_uyusmazlik", f"{o['sembol']}: pozisyonsuz yetim {o['tur']} emri iptal edildi", bildir=False)
                except BorsaHata as e:
                    self._bir_kez(f"yetim:{o['client_id']}", "canli_iptal_hatasi", f"{o['sembol']}: yetim emir iptal edilemedi: {e}")

    # ------------------------------------------------------------------ KAYIT (denetim dosyaları; işlem mantığına DOKUNMAZ)
    # Kural: kayıt yazımı/okuması başarısız olsa da işlem akışı SÜRER; ama hata sessiz de değildir: log + sayaç (kayit_hata_sayisi, durum["kayit_hata_sayisi"])
    # + olay/Telegram uyarısı (aynı dosya için bir kez; başarılı yazımdan sonra yeniden uyarabilir). Dosyalar ve alanlar: canli_kayit.py.
    def _kayit_hata(self, ad: str, e: Exception) -> None:
        self.kayit_hata_sayisi[ad] = self.kayit_hata_sayisi.get(ad, 0) + 1
        self.durum["kayit_hata_sayisi"] = dict(self.kayit_hata_sayisi)
        log.error("kayıt hatası [%s] %s: %s: %s", self.sid, ad, type(e).__name__, str(e)[:200])
        self._bir_kez(f"kayit:{ad}", "canli_kayit_hatasi", f"{ad} kaydı yazılamadı ({type(e).__name__}: {str(e)[:200]}); işlem akışı sürüyor, kayıt eksik kalabilir "
                                                           f"(bu dosyada hata sayısı {self.kayit_hata_sayisi[ad]})")

    def _kayit_guvenli(self, ad: str, fn, *a) -> bool:
        try:
            fn(*a)
        except Exception as e:  # noqa: BLE001  (kayıt hatası işlemi durdurmaz; AÇIK: log + sayaç + olay/Telegram uyarısı)
            self._kayit_hata(ad, e)
            return False
        self._uyari_sil(f"kayit:{ad}")
        return True

    def _kayit_yolu(self, dosya: str) -> Path:
        return self.kayit_dizin / dosya

    def _zaman_iso(self, ts=None) -> str:
        return pd.Timestamp(ts if ts is not None else self.saat()).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _olay_kaydet(self, tur: str, mesaj: str) -> None:
        """Her olay append-only arşive; 'canli_kapandi' metninden kapatma nedeni (çıkış nedeni sınıflaması için) tutulur."""
        if self.kayit_dizin is None:
            return
        if tur == "canli_kapandi":
            c = ck.kapat_nedeni_cikar(mesaj)
            if c and c[1] != "risk_azalt":
                self._tur_kapat[c[0]] = c[1]
        self._kayit_guvenli("olaylar_arsiv", ck.satir_ekle, self._kayit_yolu("olaylar_arsiv.jsonl"),
                            {"zaman": self._zaman_iso(), "strateji": self.sid, "tur": tur, "mesaj": mesaj[:1000]})

    def _kayit_acilis(self, n, bs: str, gid: str, E: Decimal, stop: Decimal, bo, mark: Decimal) -> None:
        if self.kayit_dizin is None:
            return

        def f():
            kayit = self.durum.setdefault("kayit", {})
            eski = kayit.get(n.kol)
            if eski is not None:                                  # aynı kolda önceki pozisyon henüz sonuçlanmadıysa kaybolmasın
                kayit[f"{n.kol}#{str(eski.get('niyet_id'))[-8:]}"] = eski
            simdi = self.saat()
            kayit[n.kol] = {"strateji": self.sid, "kol": n.kol, "bsembol": bs, "yon": n.yon, "stop_giris": str(stop), "son_stop": str(stop),
                            "son_hedef": str(n.hedef) if n.hedef else None, "planlanan_risk_usd": str(E * D(str(bo.risk_yuzde)) / 100),
                            "mark_giris": str(mark), "giris_order_id": None, "acilis_zaman": self._zaman_iso(simdi),
                            "acilis_ms": int(pd.Timestamp(simdi).value // 10**6) - 2000, "niyet_id": gid,
                            "sinyal_zamani": str(pd.Timestamp(n.sinyal_zamani)), "model_taker": str(n.taker), "model_stop_kayma": str(n.stop_kayma),
                            "deneme": 0}
        self._kayit_guvenli("islemler", f)

    def _kayit_dolum(self, kol: str, yanit: dict, qty: Decimal, avg) -> None:
        if self.kayit_dizin is None:
            return

        def f():
            k = self.durum.get("kayit", {}).get(kol)
            if k is not None:
                k.update(giris_order_id=str(yanit.get("id")) if yanit.get("id") is not None else None, giris_qty=str(qty), giris_ort=str(avg))
        self._kayit_guvenli("islemler", f)

    def _kayit_tur_sonu(self) -> None:
        if self.kayit_dizin is None:
            return
        self._kayit_guvenli("ozsermaye_gunluk", self._kayit_gunluk)
        self._kayit_guvenli("islemler", self._kayit_kapanislar)

    def _kayit_gunluk(self) -> None:
        """Servis başlangıcında ve her UTC günü: strateji özsermaye satırı; tahsis değiştiyse ayrıca `sermaye_hareketi` (kâr sayılmaz)."""
        simdi = pd.Timestamp(self.saat())
        gun = str(simdi.date())
        if self._kayit_basladi and self.durum.get("kayit_gun") == gun:
            return
        b, poz = self.borsa.bakiye(), self.borsa.pozisyonlar()
        ozs, tahsis = b["ozsermaye"], self.ayar.tahsis
        dosya = self._kayit_yolu("ozsermaye_gunluk.jsonl")
        onceki = self.durum.get("kayit_tahsis")
        if onceki is not None and D(onceki) != tahsis:
            ck.satir_ekle(dosya, {"tur": "sermaye_hareketi", "zaman": self._zaman_iso(simdi), "gun": gun, "strateji": self.sid, "onceki_tahsis_usd": onceki,
                                  "yeni_tahsis_usd": str(tahsis), "fark_usd": str(tahsis - D(onceki)), "ozsermaye_o_an": str(ozs),
                                  "not": "tahsis (ayar) değişimi: sermaye hareketi, kâr/zarar DEĞİL"})
        self.durum["kayit_tahsis"] = str(tahsis)
        kz = sum(((p["mark"] - p["giris"]) * p["miktar"] for p in poz), D(0))
        ck.satir_ekle(dosya, {"tur": "strateji", "zaman": self._zaman_iso(simdi), "gun": gun, "neden": "gun" if self._kayit_basladi else "servis_basi",
                              "strateji": self.sid, "mod": self.ayar.mod, "ozsermaye": str(ozs), "tahsis_usd": str(tahsis), "kasa": str(min(ozs, tahsis)),
                              "acik_kz_usd": str(kz), "acik_pozisyon": len(poz)})
        self.durum["kayit_gun"], self._kayit_basladi = gun, True

    def _kayit_kapanislar(self) -> None:
        """Bu turda sonuçlanan (kaydı pozlar'dan düşen) her pozisyon için BİR `islemler.jsonl` satırı. Dolum/komisyon/funding borsanın
        userTrades/income uçlarından (salt okuma); alınamazsa alan null + neden. Giriş hiç dolmadıysa satır yazılmaz."""
        kayit = self.durum.setdefault("kayit", {})
        pozlar = self.durum["pozlar"]
        for kol, rec in pozlar.items():                       # açık pozisyonların güncel stop/hedefi (çıkış sınıflaması ve kayma için)
            if kol in kayit:
                kayit[kol].update(son_stop=rec["stop"], son_hedef=rec.get("hedef"))
        adaylar = [k for k in kayit if k not in pozlar] + [k for k in self._tur_oncesi if k not in kayit and k not in pozlar]
        for anahtar in adaylar:
            kay = kayit.get(anahtar)
            if kay is None:                                   # kayıt yok (yeniden başlatma / benimsenen pozisyon): tur öncesi kayıttan türet
                r = self._tur_oncesi[anahtar]
                kay = {"strateji": self.sid, "kol": anahtar, "bsembol": r["bsembol"], "yon": r["yon"], "stop_giris": r["stop"], "son_stop": r["stop"],
                       "son_hedef": r.get("hedef"), "planlanan_risk_usd": None, "mark_giris": None, "giris_order_id": None, "acilis_zaman": r["giris_bar"],
                       "acilis_ms": int(pd.Timestamp(r["giris_bar"]).value // 10**6), "niyet_id": r.get("giris_id"), "sinyal_zamani": r["giris_bar"],
                       "model_taker": "0.0005", "model_stop_kayma": "0.0005", "deneme": 0,
                       "notlar": ["giriş kaydı yok (yeniden başlatma ya da benimsenen pozisyon): planlanan risk/mark bilinmiyor"]}
            if not kay.get("giris_qty") and kay.get("planlanan_risk_usd") is not None and getattr(self.borsa, "kullanici_islemleri", None) is None:
                kayit.pop(anahtar, None)                      # giriş hiç dolmadı (doldu kaydı yok) ve dolum geçmişi okunamıyor: işlem yok
                continue
            bs = kay["bsembol"]
            fills = fills_neden = None
            oku = getattr(self.borsa, "kullanici_islemleri", None)
            if oku is None:
                fills_neden = "borsa dolum geçmişini desteklemiyor (kuru/sahte)"
            else:
                try:
                    fills = oku(bs, int(kay["acilis_ms"]))
                except BorsaHata as e:
                    kay["deneme"] = kay.get("deneme", 0) + 1
                    kayit[anahtar] = kay
                    self._kayit_hata("dolum_gecmisi", e)
                    if kay["deneme"] < ck.DENEME_SINIRI:
                        continue                              # sonraki turda yeniden denenir
                    fills_neden = f"dolum geçmişi alınamadı ({type(e).__name__}) {ck.DENEME_SINIRI} denemede"
            funding = funding_neden = None
            if fills is not None:
                g, c, _tam = ck.yasam_dongusu(fills, int(kay["yon"]), kay.get("giris_order_id"), int(kay["acilis_ms"]))
                if not g:
                    kayit.pop(anahtar, None)                  # giriş dolmadı: işlem yok
                    continue
                ful = getattr(self.borsa, "funding_gecmisi", None)
                if ful is None:
                    funding_neden = "borsa funding geçmişini desteklemiyor"
                else:
                    try:
                        funding = ful(bs, g[0]["zaman_ms"], (c[-1]["zaman_ms"] if c else int(pd.Timestamp(self.saat()).value // 10**6)) + 1)
                    except BorsaHata as e:
                        funding_neden = f"funding alınamadı ({type(e).__name__})"
                cikis_z = self._zaman_iso(pd.Timestamp(c[-1]["zaman_ms"], unit="ms", tz="UTC")) if c else self._zaman_iso()
            else:
                cikis_z = self._zaman_iso()
            satir = ck.islem_satiri(kay, fills, fills_neden, funding, funding_neden, self._tur_kapat.get(bs), cikis_z)
            if satir is None:
                kayit.pop(anahtar, None)
                continue
            if self._kayit_guvenli("islemler", ck.satir_ekle, self._kayit_yolu("islemler.jsonl"), satir):
                kayit.pop(anahtar, None)
