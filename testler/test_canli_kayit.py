"""Canlı yürütücü KAYIT dosyaları (islemler.jsonl, ozsermaye_gunluk.jsonl, olaylar_arsiv.jsonl). HTTP/borsa SAHTE (test_canli_borsa.py deseni)."""
import json
from decimal import Decimal as D

import pandas as pd

from motor.canli.borsa import canli_kayit as ck
from motor.canli.borsa.binance_futures import BorsaHata
from motor.canli.borsa.canli_yurutucu import Ayar, Niyet, PozGorunum
from testler.test_canli_borsa import ARALIK, Ortam, Sahte, T0, Yanit, ZAMAN, ac_niyeti, gor, istemci

KOMISYON = D("0.0005")


def satirlar(yol):
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()] if yol.exists() else []


class SahteKayit(Sahte):
    """Sahte + userTrades/income: her piyasa dolumu komisyonlu kaydedilir; gerçekleşen K/Z reduceOnly dolumlarında hesaplanır."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fills, self.giris_px, self.no, self.t = [], {}, 0, 1_800_000_000_000
        self.fills_hatasi = self.komisyon_varlik = None
        self.funding = D("-0.12")

    def _fill(self, s, yon, q, px, emir_id, reduce):
        self.no += 1
        self.t += 1000
        isaret = 1 if yon == "SELL" else -1                  # SELL reduce: long kapanır
        pnl = (px - self.giris_px[s]) * q * isaret if reduce else D(0)
        if not reduce:
            self.giris_px[s] = px
        self.fills.append({"id": self.no, "emir_id": emir_id, "yon": yon, "fiyat": px, "miktar": q, "komisyon": px * q * KOMISYON,
                           "komisyon_varlik": self.komisyon_varlik or "USDT", "gercek_pnl": pnl, "zaman_ms": self.t})

    def piyasa(self, s, yon, q, cid, reduce_only=False):
        o = super().piyasa(s, yon, q, cid, reduce_only)
        self._fill(s, yon, q, o["ort_fiyat"], o["id"], reduce_only)
        return o

    def stop_calisti(self, s, px):
        q = self.poz.pop(s)
        self._fill(s, "SELL" if q > 0 else "BUY", abs(q), D(px), "stop-emri", True)

    def kullanici_islemleri(self, s, bas_ms, bit_ms=None):
        if self.fills_hatasi:
            raise BorsaHata("userTrades 503", http=503, belirsiz=True)
        return list(self.fills)

    def funding_gecmisi(self, s, bas_ms, bit_ms=None):
        return self.funding


def _ac_ve_kapat(e, mark_kapanis="50500"):
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.mark["BTCUSDT"] = D(mark_kapanis)
    e.zaman[0] += pd.Timedelta(minutes=30)
    e.y.adim(gor([Niyet("kapat", "K1", "BTCUSDT", 1, neden="sinyal", aralik=ARALIK)], {"K1": PozGorunum("BTCUSDT", 1, D("49000"))}))


# ---------------------------------------------------------------------------------------------- islemler.jsonl
def test_kapanista_islem_satiri_ve_alanlari(tmp_path):
    e = Ortam(tmp_path, borsa=SahteKayit())
    _ac_ve_kapat(e)
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    q = D(s["miktar"])
    assert q > 0 and e.borsa.poz == {}
    assert (s["strateji"], s["kol"], s["sembol"], s["yon"]) == ("S1", "K1", "BTCUSDT", "long")
    assert D(s["giris_fiyati"]) == D(50000) and D(s["cikis_fiyati"]) == D(50500)
    komisyon = (D(50000) + D(50500)) * q * KOMISYON
    assert D(s["komisyon_usd"]) == komisyon and s["komisyon_neden"] is None
    assert D(s["brut_pnl_usd"]) == D(500) * q
    assert D(s["funding_usd"]) == D("-0.12") and s["net_funding_dahil"] is True
    net = D(500) * q - komisyon + D("-0.12")
    assert D(s["net_pnl_usd"]) == net
    assert D(s["planlanan_risk_usd"]) > 0 and abs(s["r"] - float(net / D(s["planlanan_risk_usd"]))) < 1e-9
    assert (s["cikis_nedeni"], s["cikis_ayrinti"]) == ("strateji", "sinyal")
    assert s["niyet_id"].startswith("1l3a-G-") and s["sinyal_zamani"].startswith("2026-11-11 08:00")
    assert s["stop_giris"] == "49000" and abs(s["stop_mesafesi_oran"] - 0.02) < 1e-9
    assert s["model_maliyet_bps"] == 10.0                                          # 2 x taker 5 bps (stop çıkışı değil)
    assert abs(s["gercek_maliyet_bps"] - float(komisyon / (D(50000) * q) * 10000)) < 1e-6
    assert s["kismi_cikis_sayisi"] == 1 and s["veri_kaynagi"] == "userTrades"
    assert e.y.durum["kayit"] == {}                                                # tamamlanan kayıt temizlendi


def test_stop_borsada_calisinca_cikis_nedeni_stop_ve_kayma(tmp_path):
    e = Ortam(tmp_path, borsa=SahteKayit())
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.stop_calisti("BTCUSDT", "48990")                                       # stop 49000, 10 USD kayma
    e.y.adim(gor([]))                                                              # mutabakat: pozisyon yok -> kayıt temizlenir
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    assert s["cikis_nedeni"] == "stop"
    q = D(s["miktar"])
    assert D(s["brut_pnl_usd"]) == D(-1010) * q and s["r"] is not None and s["r"] < -0.9   # stopta ~ -1R (kayma ve komisyonla biraz fazla)
    assert s["model_maliyet_bps"] == 15.0                                          # 2 x taker + stop kayması 5 bps
    assert s["cikis_kayma_bps"] > 0 and s["gercek_maliyet_bps"] > 10.0


def test_komisyon_alinamazsa_null_ve_neden(tmp_path):
    e = Ortam(tmp_path)                                                            # Sahte: userTrades yok
    _ac_ve_kapat(e)
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    assert s["komisyon_usd"] is None and "desteklemiyor" in s["komisyon_neden"]
    assert s["net_pnl_usd"] is None and s["r"] is None and s["gercek_maliyet_bps"] is None
    assert D(s["giris_fiyati"]) == D(50000) and s["cikis_fiyati"] is None and s["veri_kaynagi"] == "yok"
    assert any("r hesaplanamadı" in n for n in s["notlar"])


def test_komisyon_bnb_ise_null_ve_neden(tmp_path):
    b = SahteKayit()
    b.komisyon_varlik = "BNB"
    e = Ortam(tmp_path, borsa=b)
    _ac_ve_kapat(e)
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    assert s["komisyon_usd"] is None and "BNB" in s["komisyon_neden"] and s["net_pnl_usd"] is None and s["brut_pnl_usd"] is not None


def test_dolum_gecmisi_gecici_hata_yeniden_denenir_sonra_bos_alanli_satir(tmp_path):
    b = SahteKayit()
    e = Ortam(tmp_path, borsa=b)
    e.y.adim(gor([ac_niyeti()]))
    b.fills_hatasi = True
    b.poz.clear()
    e.y.adim(gor([]))                                                              # mutabakat: pozisyon yok; userTrades hata -> satır yok, yeniden denenecek
    assert satirlar(tmp_path / "islemler.jsonl") == [] and "canli_kayit_hatasi" in e.turler()
    for _ in range(ck.DENEME_SINIRI):
        e.y.adim(gor([]))
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    assert s["komisyon_usd"] is None and "alınamadı" in s["komisyon_neden"] and e.y.kayit_hata_sayisi["dolum_gecmisi"] >= ck.DENEME_SINIRI


def test_giris_dolmadiysa_satir_yazilmaz(tmp_path):
    e = Ortam(tmp_path, borsa=SahteKayit())
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.fills.clear()                                                          # (sahte) giriş dolumu borsa geçmişinde yok
    e.borsa.poz.clear()
    e.y.adim(gor([]))
    assert satirlar(tmp_path / "islemler.jsonl") == [] and e.y.durum["kayit"] == {}


def test_kismi_cikis_tek_satir_ve_sonraki_pozisyon_karismaz():
    def f(i, yon, px, q, ms, emir, pnl="0"):
        return {"id": i, "emir_id": emir, "yon": yon, "fiyat": D(px), "miktar": D(q), "komisyon": D("0.1"), "komisyon_varlik": "USDT",
                "gercek_pnl": D(pnl), "zaman_ms": ms}
    fills = [f(1, "BUY", 100, "10", 1000, "e1"), f(2, "SELL", 101, "4", 2000, "x1", "4"), f(3, "SELL", 102, "6", 3000, "x2", "12"),
             f(4, "BUY", 110, "5", 3500, "e2")]                                    # e2: aynı turda açılan SONRAKİ pozisyon
    g, c, tam = ck.yasam_dongusu(fills, 1, "e1", 0)
    assert len(g) == 1 and len(c) == 2 and tam
    kay = {"strateji": "S", "kol": "K", "bsembol": "BTCUSDT", "yon": 1, "stop_giris": "95", "planlanan_risk_usd": "50", "giris_order_id": "e1", "acilis_ms": 0}
    s = ck.islem_satiri(kay, fills, None, None, "yok", None, "2026-01-01T00:00:00Z")
    assert s["kismi_cikis_sayisi"] == 2 and D(s["cikis_fiyati"]) == D("101.6") and D(s["miktar"]) == 10
    assert D(s["brut_pnl_usd"]) == 16 and D(s["komisyon_usd"]) == D("0.3")         # e2 dahil değil
    assert D(s["net_pnl_usd"]) == D("15.7") and s["r"] == 15.7 / 50 and s["net_funding_dahil"] is False


def test_cikis_siniflama():
    assert ck.cikis_sinifla("kill_switch", None, None, None)[0] == "kill"
    assert ck.cikis_sinifla("hesap_kill", None, None, None)[0] == "kill"
    assert ck.cikis_sinifla("sinyal", None, None, None)[0] == "strateji"
    assert ck.cikis_sinifla("hedef", None, None, None)[0] == "hedef"
    assert ck.cikis_sinifla("stop_basarisiz", None, None, None)[0] == "sistem"
    assert ck.cikis_sinifla(None, D("48990"), D(49000), D(52000))[0] == "stop"
    assert ck.cikis_sinifla(None, D("52010"), D(49000), D(52000))[0] == "hedef"
    assert ck.cikis_sinifla(None, D("50500"), D(49000), D(52000))[0] == "bilinmiyor"


def test_kayit_yok_synthetic_pozisyon_yine_satir_yazar(tmp_path):
    """Yeniden başlatma: kayıt (durum['kayit']) kaybolmuş ama pozlar'da vardı -> tur öncesi kayıttan türetilir, planlanan risk null, r null."""
    b = SahteKayit()
    e = Ortam(tmp_path, borsa=b)
    e.y.adim(gor([ac_niyeti()]))
    e.y.durum["kayit"] = {}                                                        # kayıt kaybı
    b.stop_calisti("BTCUSDT", "49000")
    e.y.adim(gor([]))
    (s,) = satirlar(tmp_path / "islemler.jsonl")
    assert s["planlanan_risk_usd"] is None and s["r"] is None and s["net_pnl_usd"] is not None
    assert any("giriş kaydı yok" in n for n in s["notlar"])


# ---------------------------------------------------------------------------------------------- hata yönetimi
def test_kayit_yazimi_hata_verirse_islem_akisi_surer_ve_uyari_gorunur(tmp_path, monkeypatch):
    def boz(yol, satir):
        raise OSError("disk dolu")
    monkeypatch.setattr(ck, "satir_ekle", boz)
    e = Ortam(tmp_path, borsa=SahteKayit())
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz and [o for o in e.borsa.acik.values() if o["tur"] == "STOP_MARKET"]      # giriş + stop normal kuruldu
    assert "canli_kayit_hatasi" in e.turler() and any("kaydı yazılamadı" in b and "disk dolu" in b for b in e.bildirimler)   # Telegram
    assert e.y.kayit_hata_sayisi["ozsermaye_gunluk"] >= 1 and e.y.durum["kayit_hata_sayisi"]["ozsermaye_gunluk"] >= 1
    n_bildirim = len(e.bildirimler)
    e.y.adim(gor([]))
    assert e.borsa.poz and len(e.bildirimler) == n_bildirim                         # aynı dosya için uyarı tekrar tekrar gönderilmez
    monkeypatch.undo()
    e.y.adim(gor([]))                                                               # düzelince yazım sürer
    assert satirlar(tmp_path / "ozsermaye_gunluk.jsonl")


def test_kayit_dizin_yoksa_hicbir_sey_yazilmaz_akis_surer():
    from motor.canli.borsa.canli_yurutucu import Yurutucu
    from testler.test_canli_borsa import bilgi
    b = Sahte()
    y = Yurutucu("S1", b, bilgi(), Ayar("testnet", D(1000)), None, olay=lambda t, m: None, saat=lambda: T0 + ARALIK + pd.Timedelta(seconds=60), sembol_esle=lambda s: s)
    y.adim(gor([ac_niyeti()]))
    assert b.poz


# ---------------------------------------------------------------------------------------------- ozsermaye_gunluk.jsonl
def test_gunluk_ozsermaye_ve_sermaye_hareketi(tmp_path):
    e = Ortam(tmp_path, ozs="1000", tahsis=60)
    e.y.adim(gor([]))
    e.y.adim(gor([]))                                                               # aynı gün: yeni satır yok
    r = satirlar(tmp_path / "ozsermaye_gunluk.jsonl")
    assert len(r) == 1 and r[0]["tur"] == "strateji" and r[0]["neden"] == "servis_basi"
    assert (r[0]["strateji"], r[0]["ozsermaye"], r[0]["tahsis_usd"], r[0]["kasa"], r[0]["acik_kz_usd"]) == ("S1", "1000", "60", "60", "0")
    e.zaman[0] += pd.Timedelta(days=1)
    e.y.adim(gor([]))
    assert [x["neden"] for x in satirlar(tmp_path / "ozsermaye_gunluk.jsonl") if x["tur"] == "strateji"] == ["servis_basi", "gun"]
    e.ayar = Ayar("testnet", D(250))                                                # 60 -> 250 (ayar değişti, servis yeniden başladı)
    e.y = e.yeni()
    e.y.adim(gor([]))
    r = satirlar(tmp_path / "ozsermaye_gunluk.jsonl")
    h = [x for x in r if x["tur"] == "sermaye_hareketi"]
    assert len(h) == 1 and h[0]["onceki_tahsis_usd"] == "60" and h[0]["yeni_tahsis_usd"] == "250" and h[0]["fark_usd"] == "190" and h[0]["ozsermaye_o_an"] == "1000"
    assert r[-1]["tur"] == "strateji" and r[-1]["neden"] == "servis_basi" and r[-1]["tahsis_usd"] == "250" and r[-1]["kasa"] == "250"
    e.y = e.yeni()
    e.y.adim(gor([]))
    assert len([x for x in satirlar(tmp_path / "ozsermaye_gunluk.jsonl") if x["tur"] == "sermaye_hareketi"]) == 1       # tahsis aynı: yeni hareket yok


def test_acik_kz_yazilir(tmp_path):
    b = SahteKayit()
    e = Ortam(tmp_path, borsa=b)
    b.poz["BTCUSDT"] = D("0.01")
    b.pozisyonlar = lambda: [{"sembol": "BTCUSDT", "miktar": D("0.01"), "giris": D(50000), "mark": D(51000), "marj_tipi": "ISOLATED"}]
    e.y.adim(gor([]))
    r = satirlar(tmp_path / "ozsermaye_gunluk.jsonl")[0]
    assert D(r["acik_kz_usd"]) == D(10) and r["acik_pozisyon"] == 1


def test_hesap_kaydi_servis_basi_ve_gunde_bir(tmp_path):
    hk = ck.HesapKaydi(tmp_path / "ozsermaye_gunluk.jsonl")
    h = {"toplam": "310", "zirve": "330", "kimlikler": ["a", "b"], "kill": False}
    assert hk.yaz(h, pd.Timestamp("2026-12-15 10:00", tz="UTC")) is True
    assert hk.yaz(h, pd.Timestamp("2026-12-15 18:00", tz="UTC")) is False
    assert hk.yaz(h, pd.Timestamp("2026-12-16 00:05", tz="UTC")) is True
    r = satirlar(tmp_path / "ozsermaye_gunluk.jsonl")
    assert [x["neden"] for x in r] == ["servis_basi", "gun"] and r[0]["tur"] == "hesap" and r[0]["toplam"] == "310" and r[0]["zirve"] == "330"


# ---------------------------------------------------------------------------------------------- olaylar_arsiv.jsonl
def test_olay_arsivi_dolan_atlanan_ve_neden(tmp_path):
    e = Ortam(tmp_path, borsa=SahteKayit())
    e.y.adim(gor([ac_niyeti()]))                                                    # dolan
    e.y.adim(gor([ac_niyeti(kol="K2", t=T0 - pd.Timedelta(hours=5))]))              # eski sinyal: atlanır
    a = satirlar(tmp_path / "olaylar_arsiv.jsonl")
    turler = [x["tur"] for x in a]
    assert "canli_emir_doldu" in turler and "canli_giris_atlandi" in turler and "canli_stop_kuruldu" in turler
    atl = next(x for x in a if x["tur"] == "canli_giris_atlandi")
    assert atl["strateji"] == "S1" and "sinyal barı" in atl["mesaj"] and atl["zaman"].endswith("Z")
    n = len(a)
    e.y = e.yeni()                                                                  # yeniden başlatma: arşiv SİLİNMEZ, eklenir
    e.y.olay("deneme", "x", bildir=False)
    assert len(satirlar(tmp_path / "olaylar_arsiv.jsonl")) == n + 1


# ---------------------------------------------------------------------------------------------- BinanceFutures okuma yardımcıları (sahte HTTP)
def test_binance_kullanici_islemleri_ve_funding_sahte_http():
    tr = [{"id": 11, "orderId": 7, "side": "BUY", "price": "50000", "qty": "0.01", "realizedPnl": "0", "commission": "0.25", "commissionAsset": "USDT", "time": 1_700_000_001_000},
          {"id": 12, "orderId": 8, "side": "SELL", "price": "50500", "qty": "0.01", "realizedPnl": "5", "commission": "0.2525", "commissionAsset": "USDT", "time": 1_700_000_100_000}]
    c, o = istemci([ZAMAN, Yanit(200, tr), Yanit(200, [{"income": "-0.10", "time": 1}, {"income": "0.02", "time": 2}])])
    f = c.kullanici_islemleri("BTCUSDT", 1_700_000_000_000)
    assert [x["id"] for x in f] == [11, 12] and f[1]["gercek_pnl"] == D(5) and f[0]["komisyon"] == D("0.25") and f[0]["emir_id"] == "7" and f[1]["yon"] == "SELL"
    assert c.funding_gecmisi("BTCUSDT", 1_700_000_000_000) == D("-0.08")
    u1, u2 = o.istekler[1][1], o.istekler[2][1]
    assert "/fapi/v1/userTrades?" in u1 and "symbol=BTCUSDT" in u1 and "startTime=1700000000000" in u1
    assert "/fapi/v1/income?" in u2 and "incomeType=FUNDING_FEE" in u2
    assert all(i[0] == "GET" for i in o.istekler)                                    # yalnız okuma


def test_binance_kullanici_islemleri_7_gunden_uzun_pencerelere_bolunur_ve_tekrar_elenir():
    ayni = {"id": 5, "orderId": 1, "side": "BUY", "price": "1", "qty": "1", "realizedPnl": "0", "commission": "0", "commissionAsset": "USDT", "time": 1}
    c, o = istemci([ZAMAN, Yanit(200, [ayni]), Yanit(200, [ayni])])
    f = c.kullanici_islemleri("BTCUSDT", 1_700_000_000_000 - 10 * 24 * 3600 * 1000)    # 10 gün: 2 pencere
    assert len(f) == 1 and len(o.istekler) == 3
