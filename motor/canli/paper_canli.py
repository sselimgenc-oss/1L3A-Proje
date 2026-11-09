"""Canlı veri kaynağı + servis döngüsü (Aşama 4). Gerçek emir YOK; yalnız herkese açık Binance verisi.

Veri akışı
  - REST HER ZAMAN doğrudur: mum kapanışı WS'den gelen `x:true` kline olayıyla TETİKLENİR, ama işlenen bar REST'ten
    (kapanmış mum) okunur; WS barı REST ile uyuşmuyorsa uyarı loglanır/olay yazılır, REST kullanılır.
  - Açılışta ve her turda REST ile boşluk doldurulur: kaçan mumlar (servis kapalıyken) REST'ten alınır ve sırayla işlenir.
  - WS: Binance bağlantıyı 24 saatte keser; 23 saatte kendimiz yeniden bağlanırız (proaktif), kopmada üstel geri çekilmeyle
    yeniden bağlanırız; her kopma/yeniden bağlanma olay olarak yazılır. WS tamamen çökse bile REST yoklaması (30 sn) çalışır.
  - Geçmiş: yerel tohum parquet (varsa; `veri/mumlar`) + REST ile devamı; yoksa yalnız REST (TradFi için Binance geçmişi kısadır:
    uzun geçmiş isteyen stratejiler için tohum veri gerekir, bkz. deploy/KURULUM.md).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from motor.canli import paper_veri as pv
from motor.canli.paper_kaynak import TekrarKaynagi
from motor.veri.depo import aralik_suresi

log = logging.getLogger("paper.canli")
WS_YENIDEN_SN = 23 * 3600           # Binance 24 saatte keser
WS_SESSIZ_SN = 180                  # bu kadar süre hiç mesaj gelmezse bağlantı ölü sayılır
YOKLAMA_SN = 30
SEANS_KONTROL_SN = 300              # seanslı serilerde yeni bar yoksa en çok bu sıklıkta REST'e bak
GRACE_SN = 3                        # kapanıştan sonra REST'in mumu yayımlaması için
BIRIM_BEKLEME_SN = 900              # çok sembollü birim: beklenen sembol mumu gelmeden satır en çok bu kadar bekletilir (TradFi 300 sn yoklaması x 3)


class CanliKaynak(TekrarKaynagi):
    def __init__(self, ist: pv.FapiIstemci, tanimlar: list, pencere: dict, tohum_dizin: Optional[Path] = None,
                 olay=lambda tur, mesaj: None):
        super().__init__({}, {}, pencere)
        self.ist, self.olay = ist, olay
        self.tohum_dizin = tohum_dizin
        self.seriler = sorted({(s, t.tf) for t in tanimlar for s in t.veri_semboller})
        self.semboller = sorted({s for s, _ in self.seriler})
        self.son_kontrol: dict = {}
        self.funding_son: dict = {}
        self._bosluk_yazilan: set = set()

    # ------------------------------------------------------------------ satırlar (çok sembollü birim: tüm semboller gelene kadar beklet)
    def satirlar(self, birim, son_t, simdi) -> list:
        """Tekrar kaynağıyla aynı satırlar; ÇOK SEMBOLLÜ birimde bir satır, o kovada mumu BEKLENEN (paper_veri.kova_bekleniyor) her
        sembolün mumu gelene kadar yayımlanmaz (sonraki satırlar da beklenir; sıra korunur). Sembolün serisi t'yi geçmişse (t mumu hiç
        gelmeyecek) ya da kapanıştan BIRIM_BEKLEME_SN geçmişse satır eksik sembolle (None) yayımlanır ve `veri_bosluk` olayı yazılır.
        Neden: semboller REST'ten farklı anlarda gelir (TradFi 300 sn yoklaması); erken yayımlanan satırda eksik sembol o barda hiç
        işlenmez (stop kontrolü yok, karar bir bar gecikir). Tekrar modu (TekrarKaynagi) değişmez: orada tüm veri baştan vardır."""
        rows = super().satirlar(birim, son_t, simdi)
        if len(birim.semboller) < 2:
            return rows
        out = []
        for t, mumlar in rows:
            kap = t + birim.aralik
            eksik = [s for s, m in mumlar.items() if m is None and pv.kova_bekleniyor(s, birim.tf, t)]
            gelecek = [s for s in eksik if self.mumlar[(s, birim.tf)].index[-1] < t]      # serisi t'ye ulaşmamış: mum hâlâ gelebilir
            if gelecek and simdi < kap + pd.Timedelta(seconds=BIRIM_BEKLEME_SN):
                break
            for s in eksik:
                anahtar = (birim.ad, t, s)
                if anahtar not in self._bosluk_yazilan:
                    self._bosluk_yazilan.add(anahtar)
                    self.olay("veri_bosluk", f"{birim.ad} {t}: {s} {birim.tf} mumu gelmedi"
                                             + (f" ({BIRIM_BEKLEME_SN} sn beklendi)" if s in gelecek else " (borsa bu mumu vermedi)")
                                             + "; satır bu sembol olmadan işlendi")
            out.append((t, mumlar))
        return out

    # ------------------------------------------------------------------ başlangıç
    def _tohum(self, sembol: str, tf: str) -> Optional[pd.DataFrame]:
        if self.tohum_dizin is None:
            return None
        from motor.veri.yeniden_ornekle import tf_mumlari
        try:
            df = tf_mumlari(sembol, tf, None, None, dizin=self.tohum_dizin, kilit_ac=True,
                            gerekce="Aşama 4 paper: tohum geçmiş (kilit kullanılmış sayılır)")
        except FileNotFoundError:
            return None
        return df.drop(columns="eksik") if "eksik" in df.columns else df

    def baslat(self, simdi: pd.Timestamp):
        for s, tf in self.seriler:
            n = self.pencere.get(tf, 1500)
            gerek = simdi - n * aralik_suresi(tf)
            df = self._tohum(s, tf)
            if df is not None and len(df):
                bas = df.index[-1] + aralik_suresi(tf)
                yeni = pv.mumlar(self.ist, s, tf, bas, simdi)
                if len(yeni):
                    df = pd.concat([df, yeni[~yeni.index.isin(df.index)]]).sort_index()
                if df.index[-1] < simdi - 3 * aralik_suresi(tf) and tk_acik(s):
                    self.olay("veri_bosluk", f"{s} {tf}: tohum + REST sonrası son mum {df.index[-1]} (şimdi {simdi})")
            else:
                df = pv.mumlar(self.ist, s, tf, gerek.floor("D"), simdi)
            if not len(df):
                raise RuntimeError(f"{s} {tf}: hiç mum alınamadı")
            self.mumlar[(s, tf)] = df
            self.son_kontrol[(s, tf)] = simdi
        for s in self.semboller:
            self.funding_guncelle(s, simdi, ilk=True)

    # ------------------------------------------------------------------ tur
    def funding_guncelle(self, s: str, simdi, ilk=False):
        son = self.fundingler.get(s)
        bas = None if (son is None or not len(son)) else son.index[-1] + pd.Timedelta(1, "ms")
        if bas is None and ilk:
            bas = simdi - pd.Timedelta(days=40)
        yeni = self.ist.funding(pv.binance_sembol(s), bas)
        if len(yeni):
            self.fundingler[s] = yeni if son is None else pd.concat([son, yeni[~yeni.index.isin(son.index)]]).sort_index()

    def guncelle(self, simdi: pd.Timestamp) -> int:
        """Her seri için kapanmış yeni barları REST'ten alır. -> eklenen bar sayısı."""
        toplam = 0
        for s, tf in self.seriler:
            df = self.mumlar[(s, tf)]
            a = aralik_suresi(tf)
            sonraki_kapanis = df.index[-1] + 2 * a
            if simdi < sonraki_kapanis + pd.Timedelta(seconds=GRACE_SN):
                continue
            from motor.canli import paper_takvim as tk
            if tk.tur(s) != "kripto" and (simdi - self.son_kontrol[(s, tf)]).total_seconds() < SEANS_KONTROL_SN:
                continue
            self.son_kontrol[(s, tf)] = simdi
            yeni = pv.mumlar(self.ist, s, tf, df.index[-1] + a if tk.tur(s) == "kripto" else (df.index[-1] + a).floor("D"), simdi)
            yeni = yeni[~yeni.index.isin(df.index)]
            if len(yeni):
                if tk.tur(s) == "kripto":
                    ix = df.index[-1:].append(yeni.index)
                    for k in range(1, len(ix)):
                        bos = (ix[k] - ix[k - 1]) / a - 1
                        if bos > 0:
                            self.olay("veri_bosluk", f"{s} {tf}: {int(bos)} mum eksik ({ix[k - 1]} -> {ix[k]}); borsa bu mumları vermedi")
                self.mumlar[(s, tf)] = pd.concat([df, yeni])
                toplam += len(yeni)
        if (simdi - self.funding_son.get("t", simdi - pd.Timedelta(days=1))).total_seconds() >= 1800:
            for s in self.semboller:
                self.funding_guncelle(s, simdi)
            self.funding_son["t"] = simdi
        return toplam

    def ws_dogrula(self, sembol_b: str, tf: str, k: dict) -> None:
        """WS'den gelen kapanmış mum ile REST'teki aynı mumu karşılaştırır (uyuşmazlık loglanır; REST geçerli)."""
        s = next((x for x in self.semboller if pv.binance_sembol(x) == sembol_b), None)
        df = self.mumlar.get((s, tf))
        if df is None:
            return
        t = pd.Timestamp(int(k["t"]), unit="ms", tz="UTC")
        if t in df.index and abs(df.loc[t, "kapanis"] - float(k["c"])) > 1e-9 * max(1.0, abs(float(k["c"]))):
            self.olay("veri_uyusmazlik", f"{s} {tf} {t}: WS kapanış {k['c']} != REST {df.loc[t, 'kapanis']} (REST kullanılır)")

    def saglik_veri(self) -> list:
        return [{"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1], "mum_indeksi": df.index} for (s, tf), df in sorted(self.mumlar.items())]


def tk_acik(sembol: str) -> bool:
    from motor.canli import paper_takvim as tk
    return tk.tur(sembol) == "kripto"


# ---------------------------------------------------------------------------- WebSocket
def ws_url(akislar: list) -> str:
    # Binance USDⓈ-M piyasa akışları (kline vb.) /market yolunda; eski /stream bağlanıyor ama veri göndermiyor
    # (sunucuda doğrulandı 2026-11-07: /stream 12 sn'de 0 mesaj, /market/stream 32 mesaj).
    return f"{pv.WS_TABAN}/market/stream?streams={'/'.join(akislar)}"


def akislar(kaynak: CanliKaynak) -> list:
    out = []
    for s, tf in kaynak.seriler:
        b = pv.binance_sembol(s).lower()
        from motor.canli import paper_takvim as tk
        out.append(f"{b}@kline_{tf if tk.tur(s) == 'kripto' else '5m'}")
    return sorted(set(out))


async def ws_dongu(url: str, mesaj_fn, olay, durdur: asyncio.Event, baglan=None, yeniden_sn: float = WS_YENIDEN_SN,
                   sessiz_sn: float = WS_SESSIZ_SN, uyku=asyncio.sleep):
    """Bağlantıyı canlı tutar. mesaj_fn(dict) her mesajda çağrılır. Kopma/24 saat sınırı: yeniden bağlanır, olay yazar."""
    if baglan is None:
        import websockets
        baglan = websockets.connect
    bekle, ilk = 1.0, True
    while not durdur.is_set():
        neden = None
        try:
            async with baglan(url, ping_interval=20, ping_timeout=30, max_size=2**22) as ws:
                olay("ws_baglandi" if ilk else "ws_yeniden_baglandi", f"WS bağlandı ({url.count('@')} akış)")
                ilk, bekle = False, 1.0
                t0 = son = time.monotonic()
                while not durdur.is_set():
                    kalan = yeniden_sn - (time.monotonic() - t0)
                    if kalan <= 0:
                        neden = "ws_24sa_yenileme"
                        olay(neden, "Binance 24 saat sınırı: proaktif yeniden bağlanma")
                        break
                    try:
                        ham = await asyncio.wait_for(ws.recv(), timeout=min(30.0, kalan))
                    except asyncio.TimeoutError:
                        if time.monotonic() - son > sessiz_sn:
                            neden = "ws_sessiz"
                            olay("ws_koptu", f"WS {sessiz_sn:.0f} sn mesaj vermedi; yeniden bağlanılıyor")
                            break
                        continue
                    son = time.monotonic()
                    mesaj_fn(json.loads(ham))
        except Exception as e:  # noqa: BLE001  (kopma: olay olarak yazılır, geri çekilmeyle yeniden denenir)
            olay("ws_koptu", f"WS koptu: {e!r}")
            await uyku(bekle)
            bekle = min(bekle * 2, 60.0)
            continue
        if neden:
            await uyku(0.5)
