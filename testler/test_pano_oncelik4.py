"""Pano öncelik 4: veri güveni, backtest bütünlük, sürüm izi + giriş gerekçesi, kalp atışı / kesinti ölçümü. Ağ yok, ağır backtest yok."""
import json
import shutil
from datetime import datetime, timezone

import pandas as pd
import pytest

from motor.canli import aylik_rapor as ar
from motor.canli import durum as d
from motor.canli import giris_izi as gi
from motor.canli import guven as gv
from motor.canli import kalp_atisi as kh
from motor.canli import pano
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from motor.canli import paper_sinyal as psg
from motor.canli import paper_veri as pv
from testler.test_paper_canli import SahteFapi
from testler.test_paper_motor import TAN, kural, sentetik


# ---------------------------------------------------------------------------- (a) veri güveni
def _ix(*zamanlar):
    return pd.DatetimeIndex(pd.to_datetime(list(zamanlar), utc=True))


def test_bosluk_olc_kripto_eksik_mum_sayar():
    # 30m: 10:00, 10:30, [11:00 11:30 eksik], 12:00 ... son kapanış 12:30
    ix = _ix("2026-11-08 10:00", "2026-11-08 10:30", "2026-11-08 12:00", "2026-11-08 12:30")
    r = gv.bosluk_olc("BTCUSDT", "30m", ix, pd.Timestamp("2026-11-08 13:00", tz="UTC"))
    assert r == {"pencere_mum": 4, "eksik_mum": 2, "bosluk_sayisi": 1, "en_uzun_bosluk_mum": 2}


def test_bosluk_olc_pencere_ve_kapanmamis_mum_lookahead_yok():
    ix = _ix("2026-09-01 00:00", "2026-11-07 00:00", "2026-11-08 00:00")
    # 1d: pencere 30 gün: eylül mumu dışarıda; 11-08 mumu simdi=11-08 12:00'de HENÜZ KAPANMADI -> sayılmaz
    r = gv.bosluk_olc("BTCUSDT", "1d", ix, pd.Timestamp("2026-11-08 12:00", tz="UTC"))
    assert r["pencere_mum"] == 1 and r["eksik_mum"] == 0


def test_bosluk_olc_hisse_hafta_sonu_sayilmaz_hafta_ici_eksik_sayilir():
    # DK_AAPL 1d: Cuma 6, Pazartesi 9 arası hafta sonu (kapalı) -> eksik değil; Pazartesi 9 -> Çarşamba 11 arası Salı seans günü -> 1 eksik
    ix = _ix("2026-11-05 00:00", "2026-11-06 00:00", "2026-11-09 00:00", "2026-11-11 00:00")
    r = gv.bosluk_olc("DK_AAPL", "1d", ix, pd.Timestamp("2026-11-13 00:00", tz="UTC"))
    assert r["eksik_mum"] == 1 and r["bosluk_sayisi"] == 1 and r["pencere_mum"] == 4


def test_veri_guveni_indeks_yoksa_null_ve_neden_kaynak_ve_spot_vekil(tmp_path):
    (tmp_path / "BTCUSDT").mkdir()
    (tmp_path / "BTCUSDT" / "kaynak.json").write_text(json.dumps({"spot_vekil_baslangic": "2017-08-17", "spot_vekil_bitis": "2019-12-31",
                                                                  "perp_baslangic": "2020-01-01"}))
    sag = [{"sembol": "BTCUSDT", "tf": "1d", "son_mum_zamani": "2026-11-07T00:00:00Z", "bayatlik_dk": 30, "esik_dk": 2890, "bayat": False},
           {"sembol": "DK_XAU", "tf": "4h", "son_mum_zamani": "2026-11-06T20:00:00Z", "bayatlik_dk": 5, "esik_dk": 490, "bayat": False}]
    ix = {("BTCUSDT", "1d"): _ix("2026-11-05", "2026-11-07")}                    # 11-06 eksik
    g = gv.veri_guveni(sag, ix, pd.Timestamp("2026-11-08 00:30", tz="UTC"), "paper", "2026-11-08T00:30:00Z", veri_dizini=tmp_path)
    b, x = g["semboller"]
    assert b["eksik_mum"] == 1 and b["bayatlik_dk"] == 30 and b["son_mum_kapanis"] == "2026-11-08T00:00:00Z"
    assert b["kaynak"] == "binance_perp" and b["spot_vekil"]["bit"] == "2019-12-31"
    assert x["eksik_mum"] is None and "ölçülmedi" in x["eksik_neden"] and x["seans"] == "emtia"
    assert x["kaynak"] == "binance_perp" and "Dukascopy" in x["kaynak_ayrinti"]               # canlıda TradFi perp, geçmiş tohum Dukascopy
    assert g["ozet"]["eksik_mum_toplam"] == 1 and g["ozet"]["olculmeyen_seri"] == 1
    # tekrar/backtest: yerel arşiv kaynağı
    assert gv.kaynak_bilgisi("DK_XAU", False)["kaynak"] == "dukascopy" and gv.kaynak_bilgisi("BIST_AKBNK", False)["kaynak"] == "yahoo"
    assert gv.kaynak_bilgisi("ETHUSDT", True, tmp_path)["spot_vekil_neden"]                  # kaynak.json yok -> neden yazılı


# ---------------------------------------------------------------------------- (b) bütünlük
def _kok(tmp_path):
    kok = tmp_path / "kok"
    for _, yol, _, muhur in gv.IZLENEN:
        (kok / yol).parent.mkdir(parents=True, exist_ok=True)
        (kok / yol).write_text(f"icerik {yol}\n")
        if muhur:
            (kok / muhur).write_text(gv.sha256_dosya(kok / yol) + "\n")
    return kok


def test_butunluk_eslesti_uyusmuyor_kayit_yok_dosya_yok(tmp_path):
    from motor.portfoy.motor import PortfoyAyarlari
    kok = _kok(tmp_path)
    ay = PortfoyAyarlari()
    kyol = kok / "sonuclar" / "final" / "butunluk_kayit.json"
    b0 = gv.butunluk("paper", "2026-11-08T00:00:00Z", ay, kok=kok, kayit_yolu=kyol, onbellek_sn=0)
    assert b0["genel_durum"] == "eksik" and b0["sayim"]["kayit_yok"] >= 6                    # kayıt yok: eşleşme uydurulmaz
    gv.kaydet(ay, "2026-11-08T00:00:00Z", kok=kok, kayit_yolu=kyol)
    b1 = gv.butunluk("paper", "2026-11-08T00:00:00Z", ay, kok=kok, kayit_yolu=kyol, onbellek_sn=0)
    assert b1["genel_durum"] == "eslesti" and b1["sayim"]["eslesti"] == len(gv.IZLENEN) + 2
    assert all(x["eslesti"] is True for x in b1["dosyalar"])
    (kok / "sonuclar/final/guncel_ayarlar.csv").write_text("degisti\n")                    # ayar yenilemesi gibi
    b2 = gv.butunluk("paper", "2026-11-08T00:00:00Z", ay, kok=kok, kayit_yolu=kyol, onbellek_sn=0)
    g = next(x for x in b2["dosyalar"] if x["id"] == "guncel_ayarlar")
    assert b2["genel_durum"] == "uyusmuyor" and g["durum"] == "uyusmuyor" and g["eslesti"] is False and g["sha256"] != g["kayitli_sha256"]
    (kok / "stratejiler/final_set.json").unlink()
    b3 = gv.butunluk("paper", "2026-11-08T00:00:00Z", ay, kok=kok, kayit_yolu=kyol, onbellek_sn=0)
    assert next(x for x in b3["dosyalar"] if x["id"] == "set_dosyasi")["durum"] == "dosya_yok"
    # maliyet tablosu kendi mührüyle karşılaştırılır
    m = next(x for x in b3["dosyalar"] if x["id"] == "maliyet_tablosu")
    assert m["durum"] == "eslesti" and m["kayit_kaynagi"] == "sonuclar/evren/maliyet_tablosu.sha256"
    # backtest: maliyet modeli ölçülmez (null + neden)
    b4 = gv.butunluk("backtest", "2026-11-08T00:00:00Z", None, kok=kok, kayit_yolu=kyol, onbellek_sn=0)
    mm = next(x for x in b4["sanal"] if x["id"] == "maliyet_modeli")
    assert mm["durum"] == "olculmedi" and mm["sha256"] is None and mm["neden"]


def test_kod_surumu_git_yoksa_null_ve_neden(tmp_path, monkeypatch):
    monkeypatch.delenv("L3A_GIT_COMMIT", raising=False)
    k = gv.kod_surumu(tmp_path)                                  # git deposu değil
    assert k["commit"] is None and k["neden"] and k["kirli"] is None
    monkeypatch.setenv("L3A_GIT_COMMIT", "abcdef1234567890")
    k = gv.kod_surumu(tmp_path)
    assert k["commit"] == "abcdef1234567890" and k["kaynak"] == "ortam" and k["kirli"] is None and "git okunamadı" in k["neden"]
    gercek = gv.kod_surumu()                                     # bu depo
    assert gercek["kaynak"] == "git" and len(gercek["commit"]) == 40 and isinstance(gercek["kirli"], bool)


def test_gercek_depo_kayitla_eslesir():
    """sonuclar/final/butunluk_kayit.json depodaki dosyalarla uyumlu (ayar yenilemesi/elle değişiklik olursa bu test kaydın yenilenmesini ister)."""
    from motor.portfoy.motor import PortfoyAyarlari
    b = gv.butunluk("paper", "2026-11-08T00:00:00Z", PortfoyAyarlari(), onbellek_sn=0)
    assert b["genel_durum"] == "eslesti", [(x["id"], x["durum"]) for x in b["dosyalar"] + b["sanal"] if x["durum"] != "eslesti"]


# ---------------------------------------------------------------------------- (c) sürüm izi + giriş gerekçesi
@pytest.fixture(scope="module")
def kosu(tmp_path_factory):
    tans = [TAN["swing__cci-esik|SOLUSDT|1d"], TAN["pf__kesit_ls|kripto|1d"]]
    mum = {("SOLUSDT", "1d"): sentetik(520, "1d", 3, vol=0.04)}
    for k, s in enumerate(["BTCUSDT", "ETHUSDT"]):
        mum[(s, "1d")] = sentetik(520, "1d", 20 + k, vol=0.04)
    kur = {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}
    ix = mum[("SOLUSDT", "1d")].index
    p = pp.tekrar_calistir(tans, mum, {}, kur, ix[380], ix[-1] + pd.Timedelta(days=1), kapat=False)
    simdi = ix[-1] + pd.Timedelta(days=1, minutes=5)
    sag = [{"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1], "mum_indeksi": df.index} for (s, tf), df in mum.items()]
    dizin = tmp_path_factory.mktemp("durum")
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=[], kaynak="paper")
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"], gecmis=o["gecmis"], ekstra=o["ekstra"])
    return p, o, dizin, simdi, mum


def test_islem_satirlarinda_ayar_surumu_ve_gerekce(kosu):
    p, o, dizin, simdi, mum = kosu
    satirlar = o["islemler"]
    assert len(satirlar) >= 5
    assert all(s["ayar_surumu"] and s["giris_gerekcesi"] for s in satirlar)
    for s in satirlar:
        av, g = s["ayar_surumu"], s["giris_gerekcesi"]
        t = p.tanim_ad[s["kimlik"]]
        assert av == gi.ayar_surumu(t.strateji_ad, t.ayar, t.ayar_dosyasi) and len(av["hash"]) == 12
        assert g["sablon"] == "genel/1" and g["yon"] == s["yon"] and g["sembol"] == s["sembol"] and g["metin"]
        # LOOKAHEAD YOK: gerekçe girişten ÖNCE bilinen mumdandır; kapanış fiyatı o mumun gerçek kapanışı
        assert pd.Timestamp(g["sinyal_mumu_kapanis"]) <= pd.Timestamp(s["giris_zamani"])
        assert g["sinyal_kapanis_fiyati"] == pytest.approx(float(mum[(s["sembol"], "1d")].loc[pd.Timestamp(g["sinyal_mumu_acilis"]), "kapanis"]))
    # dosyadan okununca aynı (JSONL geçerli, NaN yok)
    assert all(x.get("giris_gerekcesi") for x in d.oku_islemler(dizin))


def test_gerekce_yalniz_karar_anindaki_mumlardan(kosu):
    """Aynı kararı yalnız sinyal mumuna kadar olan veriyle yeniden üret: gerekçe birebir aynı (gelecek mumlar etkisiz)."""
    p, o, dizin, simdi, mum = kosu
    s = next(x for x in o["islemler"] if x["kimlik"].startswith("swing__"))
    t = p.tanim_ad[s["kimlik"]]
    m = mum[(t.sembol, t.tf)]
    sinyal = pd.Timestamp(s["giris_gerekcesi"]["sinyal_mumu_acilis"])
    tekrar = psg.tek_karar(t, m.loc[:sinyal], None)[t.kimlik]["gerekce"]
    assert tekrar == s["giris_gerekcesi"]


def test_eski_islem_ve_durum_dosyasi_uyumlu(kosu, tmp_path):
    p, o, dizin, simdi, mum = kosu
    # eski kayıt (alan yok) -> satırda null
    x = dict(p.motor.islemler[0])
    x.pop("ayar_surumu"), x.pop("giris_gerekcesi")
    p.motor.islemler.append(x)
    try:
        satir = pdr._islem_satiri(p, x)
    finally:
        p.motor.islemler.pop()
    assert satir["ayar_surumu"] is None and satir["giris_gerekcesi"] is None
    d.dogrula_islem(satir)
    # eski paper_state.json (kalp_atisi/karar_meta/giris_meta yok) yüklenir
    yol = tmp_path / "paper_state.json"
    p.kaydet(yol)
    v = json.loads(yol.read_text())
    assert "kalp_atisi" in v and "karar_meta" in v["motor"] and "giris_meta" in v["motor"]
    v.pop("kalp_atisi")
    v["motor"].pop("karar_meta"), v["motor"].pop("giris_meta")
    yol.write_text(json.dumps(v))
    tans = [TAN["swing__cci-esik|SOLUSDT|1d"], TAN["pf__kesit_ls|kripto|1d"]]
    from motor.canli.paper_kaynak import TekrarKaynagi
    p2 = pp.Paper(tans, TekrarKaynagi(mum, {}, None), {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}, durum_yolu=yol)
    assert p2.yukle() and p2.kalp_atisi is None and p2.motor.karar_meta == {} and p2.motor.giris_meta == {}


def test_acik_pozisyon_gerekcesi_yeniden_baslatmada_korunur(kosu, tmp_path):
    p, o, dizin, simdi, mum = kosu
    yol = tmp_path / "s.json"
    p.kaydet(yol)
    from motor.canli.paper_kaynak import TekrarKaynagi
    tans = [TAN["swing__cci-esik|SOLUSDT|1d"], TAN["pf__kesit_ls|kripto|1d"]]
    p2 = pp.Paper(tans, TekrarKaynagi(mum, {}, None), {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}, durum_yolu=yol)
    p2.yukle()
    assert p2.motor.giris_meta == p.motor.giris_meta and p2.motor.karar_meta == p.motor.karar_meta
    assert set(p.motor.acik) <= set(p.motor.giris_meta)          # her açık pozisyonun izi var


# ---------------------------------------------------------------------------- (d) kalp atışı + kesinti
def test_kesinti_ve_olay_mesaji_kesinti_olc_okur():
    k = kh.kesinti("2026-11-08T10:00:00Z", pd.Timestamp("2026-11-08T13:30:00Z"))
    assert k["sn"] == 12600.0 and k["neden"] is None
    ol = [{"zaman": "2026-11-08T13:30:00Z", "tur": "yeniden_baslatma", "mesaj": kh.olay_mesaji(k)}]
    c = ar.kesinti_olc(ol)
    assert c["saat"] == pytest.approx(3.5) and c["olculen_olay"] == 1 and c["olculemeyen_olay"] == 0
    # önceki kalp atışı yok / saat geri gitti -> ölçülemez (null + neden), uydurma yok
    k0 = kh.kesinti(None, pd.Timestamp("2026-11-08T13:30:00Z"))
    assert k0["sn"] is None and "ölçülemedi" in k0["neden"]
    c0 = ar.kesinti_olc([{"zaman": "2026-11-08T13:30:00Z", "tur": "yeniden_baslatma", "mesaj": kh.olay_mesaji(k0)}])
    assert c0["saat"] is None and c0["olculemeyen_olay"] == 1
    kg = kh.kesinti("2026-11-08T14:00:00Z", pd.Timestamp("2026-11-08T13:30:00Z"))
    assert kg["sn"] is None and "geri" in kg["neden"]
    # eski biçimli olay (aralıksız) hâlâ ölçülemeyen
    assert ar.kesinti_olc([{"zaman": "2026-11-08T13:30:00Z", "tur": "yeniden_baslatma", "mesaj": "x"}])["saat"] is None
    # yeniden başlatma ile veri boşluğu çakışırsa iki kez sayılmaz
    bosluk = {"zaman": "2026-11-08T13:30:00Z", "tur": "veri_bosluk", "mesaj": "X 1d: 3 mum eksik (2026-11-08 11:00:00+00:00 -> 2026-11-08 13:00:00+00:00)"}
    assert ar.kesinti_olc(ol + [bosluk])["saat"] == pytest.approx(3.5)


class _SahteFapiGec(SahteFapi):
    """Aynı sahte borsa; sunucu saati 3 saat ileride (servis 3 saat kapalı kaldı)."""

    def __init__(self):
        super().__init__()
        self.simdi = pd.Timestamp("2026-03-01 15:07", tz="UTC")


def test_canli_yeniden_baslatma_kesintiyi_olcer(tmp_path, monkeypatch):
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    for tf, n in (("1d", 120), ("4h", 120), ("30m", 300)):
        monkeypatch.setitem(pp.PENCERE, tf, n)
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    kd = kh.oku(tmp_path)
    assert kd["zaman"] == "2026-03-01T12:07:00Z" and kd["onceki_kalp_atisi"] is None
    s1 = d.oku_saglik(tmp_path)
    assert s1["kalp_atisi"]["son"] == "2026-03-01T12:07:00Z" and s1["kalp_atisi"]["son_kesinti_sn"] is None
    assert json.loads((tmp_path / "paper_state.json").read_text())["kalp_atisi"] == "2026-03-01T12:07:00Z"
    # 3 saat sonra yeniden başlat
    monkeypatch.setattr(pv, "FapiIstemci", _SahteFapiGec)
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    ev = [o for o in d.ek_oku(tmp_path, "olaylar") if o["tur"] == "yeniden_baslatma"]
    assert len(ev) == 1 and "(2026-03-01T12:07:00Z -> 2026-03-01T15:07:00Z)" in ev[0]["mesaj"] and "10800 sn" in ev[0]["mesaj"]
    s2 = d.oku_saglik(tmp_path)
    assert s2["kalp_atisi"]["son_kesinti_sn"] == 10800.0 and s2["kalp_atisi"]["son"] == "2026-03-01T15:07:00Z"
    assert s2["kalp_atisi"]["onceki_kalp_atisi"] == "2026-03-01T12:07:00Z"
    state = json.loads((tmp_path / "paper_state.json").read_text())
    c = ar.kesinti_olc(state["olaylar"])
    assert c["saat"] is not None and c["saat"] >= 3.0 and c["olculen_olay"] >= 1
    # yeni ek dosyalar yazıldı ve okunur
    assert d.ek_oku(tmp_path, "veri_guveni")["semboller"] and d.ek_oku(tmp_path, "butunluk")["kod_surumu"]


def test_eski_durumla_baslatma_kesinti_olculemedi_olay_yazar(tmp_path, monkeypatch):
    """Kalp atışı olmayan eski paper_state.json: servis açılır, olay 'ölçülemedi' der (kesinti uydurulmaz)."""
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    for tf, n in (("1d", 120), ("4h", 120), ("30m", 300)):
        monkeypatch.setitem(pp.PENCERE, tf, n)
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    yol = tmp_path / "paper_state.json"
    v = json.loads(yol.read_text())
    v.pop("kalp_atisi")
    yol.write_text(json.dumps(v))
    (tmp_path / kh.DOSYA).unlink()
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    ev = [o for o in d.ek_oku(tmp_path, "olaylar") if o["tur"] == "yeniden_baslatma"]
    assert len(ev) == 1 and "ölçülemedi" in ev[0]["mesaj"]
    assert d.oku_saglik(tmp_path)["kalp_atisi"]["son_kesinti_sn"] is None
    # bozuk kalp atışı dosyası da açık hata olarak olaya yazılır (sessiz değil)
    (tmp_path / kh.DOSYA).write_text("{bozuk")
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    assert any("okunamadı" in o["mesaj"] for o in d.ek_oku(tmp_path, "olaylar") if o["tur"] == "yeniden_baslatma")


def test_kalp_atisi_dosyaya_en_cok_dakikada_bir_yazilir(tmp_path):
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    from motor.canli.paper_kaynak import TekrarKaynagi
    m = sentetik(100, "1d", 1)
    p = pp.Paper([t], TekrarKaynagi({("SOLUSDT", "1d"): m}, {}, None), {"SOLUSDT": kural("SOLUSDT")})
    t0 = pd.Timestamp("2026-03-01 12:00:00", tz="UTC")
    p.surec_basla(t0, tmp_path, False)
    assert kh.oku(tmp_path)["zaman"] == "2026-03-01T12:00:00Z"
    p.kalp_at(t0 + pd.Timedelta(seconds=30), tmp_path)
    assert p.kalp_atisi == "2026-03-01T12:00:30Z" and kh.oku(tmp_path)["zaman"] == "2026-03-01T12:00:00Z"     # bellek güncel, dosya 60 sn dolmadı
    p.kalp_at(t0 + pd.Timedelta(seconds=61), tmp_path)
    assert kh.oku(tmp_path)["zaman"] == "2026-03-01T12:01:01Z"
    p.kalp_at(t0 + pd.Timedelta(seconds=70), tmp_path, durdu=True)                                          # kapanış her zaman yazılır
    k = kh.oku(tmp_path)
    assert k["zaman"] == "2026-03-01T12:01:10Z" and k["durdu"] is True


# ---------------------------------------------------------------------------- pano biçimi (yalnız biçim)
def test_pano_yeni_kartlari_gosterir_ve_eski_durumda_veri_yok_der(kosu, tmp_path):
    p, o, dizin, simdi, mum = kosu
    veri, sorun = pano.yukle(dizin)
    assert not sorun
    h = pano.html_olustur(veri, sorun, datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc))
    for beklenen in ("Veri güveni", "Backtest bütünlüğü", "İşlem izi: ayar sürümü ve giriş gerekçesi", "Eksik mum", "sha256 (şimdi)", "SOLUSDT",
                     veri["islemler"][-1]["ayar_surumu"]["hash"], "genel/1"):
        assert beklenen in h, beklenen
    # sayılar dosyadakiyle aynı
    g = veri["veri_guveni"]
    assert f"{g['semboller'][0]['bayatlik_dk']} dk" in h
    # eski motor: yeni dosyalar yok -> 'veri yok', çökme yok
    eski = tmp_path / "eski"
    shutil.copytree(dizin, eski)
    for f in ("veri_guveni.json", "butunluk.json"):
        (eski / f).unlink()
    v2, s2 = pano.yukle(eski)
    assert not s2 and v2["veri_guveni"] is None and v2["butunluk"] is None
    h2 = pano.html_olustur(v2, s2, datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc))
    assert "veri_guveni.json" in h2 and "butunluk.json" in h2


def test_pano_butunluk_uyusmuyorsa_uyari(kosu):
    p, o, dizin, simdi, mum = kosu
    veri, sorun = pano.yukle(dizin)
    b = veri["butunluk"]
    b["genel_durum"] = "uyusmuyor"
    b["dosyalar"][3]["durum"] = "uyusmuyor"
    u = pano.uyarilar(veri, sorun, datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc))
    assert any("Backtest bütünlüğü" in m and b["dosyalar"][3]["id"] in m for _, m in u)


def test_backtest_besleyici_yeni_alanlar():
    """Backtest durumu: eksik mum ölçülmedi (null + neden), ayar sürümü kilit ayarından; giriş gerekçesi null."""
    from motor.canli import backtest_durum as bd
    o = bd.olustur()
    vg, bt = o["ekstra"]["veri_guveni"], o["ekstra"]["butunluk"]
    assert all(x["eksik_mum"] is None and x["eksik_neden"] for x in vg["semboller"]) and vg["kaynak"] == "backtest"
    assert bt["kaynak"] == "backtest" and bt["genel_durum"] in ("eslesti", "eksik", "uyusmuyor")
    assert next(x for x in bt["sanal"] if x["id"] == "maliyet_modeli")["durum"] == "olculmedi"
    assert all(s["ayar_surumu"] and s["giris_gerekcesi"] is None for s in o["islemler"])
    assert "kalp_atisi" not in o["saglik"] or o["saglik"]["kalp_atisi"] is None
