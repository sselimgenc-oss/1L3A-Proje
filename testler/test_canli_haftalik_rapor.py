"""araclar/canli_haftalik_rapor.py: sahte durum dizini ile eşik uyarıları, e0v1en 60 işlem kuralı, maliyet oranı, Σ min(özsermaye, tahsis), eksik alan."""
import json
from decimal import Decimal

from araclar import canli_haftalik_rapor as cr
from motor.canli.borsa import canli_limitler as cl

BIT = "2026-12-21"


def _yaz(yol, d):
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(d), encoding="utf-8")


def _jsonl(yol, satirlar):
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("\n".join(json.dumps(s) for s in satirlar) + "\n", encoding="utf-8")


def _hesap(dizin, kasalar, zirve=None, kill=False):
    h = {"surum": 1, "kimlikler": None, "zirve": None, "toplam": None, "kill": False, "kill_neden": None}
    cl.hesap_kill_guncelle(h, {k: Decimal(str(v)) for k, v in kasalar.items()})
    if zirve is not None:
        h["zirve"] = str(zirve)
    h["kill"] = kill
    _yaz(dizin / "canli" / "hesap_durumu.json", h)


def _ayar(yol, tahsisler):
    _yaz(yol, {"mod": "canli", "stratejiler": [{"id": k, "api_key_env": "A", "api_secret_env": "B", "tahsis_usd": v, "islem_risk": 0.015} for k, v in tahsisler.items()]})


def _isl(sid, i, r, gun):
    z = f"2026-12-{gun:02d}T10:00:00Z"
    return {"zaman": z, "kimlik": sid, "sembol": "BTCUSDT", "yon": "long", "cikis_zamani": z, "r": r}


def _rapor(d, **kw):
    return cr.rapor_uret(d, bitis=BIT, **kw)


def test_ozsermaye_min_tahsis_toplami(tmp_path):
    # strateji A: özsermaye 300 > tahsis 250 -> 250 sayılır; B: 200 < 250 -> 200. Σ = 450
    kasalar = {"dis__e0v1en": min(Decimal(300), Decimal(250)), "dis__ewo-ema-ofset": min(Decimal(200), Decimal(250))}
    _hesap(tmp_path, kasalar)
    _ayar(tmp_path / "a.json", {"dis__e0v1en": 250, "dis__ewo-ema-ofset": 250})
    r = _rapor(tmp_path, ayar=str(tmp_path / "a.json"))
    assert r["toplam"]["guncel_ozsermaye"] == 450.0
    assert r["toplam"]["baslangic_tahsis"] == 500.0
    assert r["toplam"]["net_usd"] == -50.0 and r["toplam"]["net_pct"] == -0.1
    assert r["toplam"]["dusus"]["guncel_dusus"] == 0.0  # zirve ilk toplam


def test_dusus_esikleri():
    assert cr.dusus_durumu(1000, 950, False)["mesajlar"] == []
    m = cr.dusus_durumu(1000, 900, False)["mesajlar"]
    assert any("BÜYÜME FRENİ" in x for x in m) and not any("HEDEF AŞILDI" in x for x in m)
    m = cr.dusus_durumu(1000, 850, False)["mesajlar"]
    assert any("HEDEF AŞILDI" in x for x in m) and any("BÜYÜME FRENİ" in x for x in m)
    assert any("HESAP KILL" in x for x in cr.dusus_durumu(1000, 800, True)["mesajlar"])


def test_dusus_rapora_yansir(tmp_path):
    _hesap(tmp_path, {"dis__e0v1en": 850}, zirve=1000)
    r = _rapor(tmp_path)
    assert any("HEDEF AŞILDI" in u for u in r["uyarilar"])
    assert any("BÜYÜME FRENİ: yeni kademe/para ekleme durur, kullanıcı gözden geçirir" in u for u in r["uyarilar"])
    assert r["toplam"]["en_buyuk_dusus"] == cr.YOK
    assert r["toplam"]["baslangic_tahsis"] is None  # --ayar yok -> uydurma yok
    assert "tahsis" in " ".join(r["eksik_dosyalar"])


def test_e0v1en_60_islem_kurali():
    def lst(rler):
        return [(None, r) for r in rler]
    assert "EMEKLİLİK" in cr.r_durum_e0v1en(cr.son_n_r(lst([-0.3] * 60), 60))        # -18R
    assert cr.r_durum_e0v1en(cr.son_n_r(lst([-0.2] * 60), 60)).startswith("UYARI")   # -12R
    assert cr.r_durum_e0v1en(cr.son_n_r(lst([-0.1] * 60), 60)).startswith("normal")  # -6R
    # son 60 pencere: eski kötü işlemler dışarıda kalır
    assert cr.r_durum_e0v1en(cr.son_n_r(lst([-5.0] * 10 + [0.1] * 60), 60)).startswith("normal")
    # sınır: tam -10R ve tam -15R
    assert cr.r_durum_e0v1en(cr.son_n_r(lst([-10 / 60] * 60), 60)).startswith("UYARI")
    assert cr.r_durum_e0v1en(cr.son_n_r(lst([-15 / 60] * 60), 60)).startswith("EMEKLİLİK")


def test_yetersiz_ornek():
    d = cr.r_durum_e0v1en(cr.son_n_r([(None, -1.0)] * 20, 60))
    assert d.startswith("yetersiz örnek") and "20/60" in d and "-20.00R" in d      # mevcut ΣR yine gösterilir
    assert "veri yok" in cr.r_durum_e0v1en(cr.son_n_r([], 60))


def test_e0v1en_canli_islemlerden_rapora(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60})
    _jsonl(tmp_path / "canli" / "islemler.jsonl", [_isl(cr.S_E0V1EN, i, -0.3, 1 + i % 20) for i in range(60)])
    r = _rapor(tmp_path)
    assert r["stratejiler"][cr.S_E0V1EN]["emeklilik_kurali"]["durum"].startswith("EMEKLİLİK")
    assert any("EMEKLİLİK" in u for u in r["uyarilar"])


def test_maliyet_orani_ve_e0v1en_30_islem():
    m = cr.maliyet_durumu("x", {"canli_maliyet_bps": 9.0, "model_maliyet_bps": 6.0}, 10)
    assert m["oran"] == 1.5 and "UYARI" not in m["durum"]                      # > 1,5 şart; tam 1,5 uyarı değil
    m = cr.maliyet_durumu("x", {"canli_maliyet_bps": 10.0, "model_maliyet_bps": 6.0}, 10)
    assert "UYARI" in m["durum"]
    e = cr.maliyet_durumu(cr.S_E0V1EN, {"canli_maliyet_bps": 10.0, "model_maliyet_bps": 6.0}, 30)
    assert e["emeklilik"].startswith("EMEKLİLİK")
    e = cr.maliyet_durumu(cr.S_E0V1EN, {"canli_maliyet_bps": 10.0, "model_maliyet_bps": 6.0}, 12)
    assert "12/30" in e["emeklilik"] and not e["emeklilik"].startswith("EMEKLİLİK")
    e = cr.maliyet_durumu(cr.S_E0V1EN, {"canli_maliyet_bps": 7.0, "model_maliyet_bps": 6.0}, 30)
    assert "geçildi" in e["emeklilik"]
    assert cr.maliyet_durumu("x", {}, None)["durum"] == cr.YOK


def test_maliyet_uyarisi_rapora(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60})
    _yaz(tmp_path / "canli" / "haftalik_karsilastirma.json", {cr.S_E0V1EN: {"canli_maliyet_bps": 12, "model_maliyet_bps": 6, "eslesme_orani": 0.90, "islem_sayisi": 31}})
    r = _rapor(tmp_path)
    assert any("maliyet oranı 2.00" in u for u in r["uyarilar"])
    assert any("eşleşme %90.0" in u for u in r["uyarilar"])
    assert any("EMEKLİLİK ölçütü" in u for u in r["uyarilar"])


def test_eslesme_olaylardan(tmp_path):
    s = cr.S_EWO
    ol = [{"zaman": "2026-12-16T10:00:00Z", "tur": "canli_emir_doldu", "mesaj": f"[{s}] k BTCUSDT LONG 1 @ 1"},
          {"zaman": "2026-12-17T10:00:00Z", "tur": "canli_emir_doldu", "mesaj": f"[{s}] k BTCUSDT LONG 1 @ 1"},
          {"zaman": "2026-12-18T10:00:00Z", "tur": "min_tutar_alti", "mesaj": f"[{s}] k (X): min_tutar_alti: ..."},
          {"zaman": "2026-12-19T10:00:00Z", "tur": "canli_giris_atlandi", "mesaj": f"[{s}] k: günlük kayıp limiti (-%6) aşıldı"},
          {"zaman": "2026-12-19T11:00:00Z", "tur": "canli_emir_doldu", "mesaj": "[baska] k X LONG 1 @ 1"}]
    _jsonl(tmp_path / "olaylar.jsonl", ol)
    _hesap(tmp_path, {s: 250})
    e = _rapor(tmp_path)["stratejiler"][s]["eslesme"]
    assert e["doldu"] == 2 and e["atlanan"] == 2 and e["oran"] == 0.5
    assert e["nedenler"] == {"min tutar (borsa asgari emri)": 1, "günlük kayıp limiti": 1}
    assert e["durum"].startswith("HEDEF ALTINDA")


def test_olay_kaydi_kesikse_eslesme_veri_yok(tmp_path):
    s = cr.S_EWO
    ol = [{"zaman": "2026-12-20T10:00:00Z", "tur": "canli_emir_doldu", "mesaj": f"[{s}] k"} for _ in range(50)]   # 50 olay, hafta başından sonra başlıyor
    _jsonl(tmp_path / "olaylar.jsonl", ol)
    _hesap(tmp_path, {s: 250})
    e = _rapor(tmp_path)["stratejiler"][s]["eslesme"]
    assert e["oran"] is None and e["durum"] == cr.YOK and "son 50" in e["aciklama"]


def test_ewo_bandi():
    k = cr.ewo_konum(-16.0, 365)
    assert k["inceleme"] is True and k["konum"] == "bandın altında"
    k = cr.ewo_konum(10.0, 365.25 / 2)          # yarı süre: orantılı bant ≈ -3,5 … +16,5
    assert k["konum"] == "bant içinde" and abs(k["orantili_bant_r"][1] - 16.5) < 0.2 and k["inceleme"] is False
    assert cr.ewo_konum(30.0, 100)["konum"] == "bandın üstünde"
    assert "bilinmiyor" in cr.ewo_konum(0, None)["konum"]


def test_ewo_rapora_ve_inceleme(tmp_path):
    _hesap(tmp_path, {cr.S_EWO: 250})
    _ayar(tmp_path / "a.json", {cr.S_EWO: 250})
    _jsonl(tmp_path / "canli" / "islemler.jsonl", [_isl(cr.S_EWO, i, -1.0, 1 + i) for i in range(16)])
    r = _rapor(tmp_path, ayar=str(tmp_path / "a.json"), baslangic="2026-12-01")
    b = r["stratejiler"][cr.S_EWO]["ewo_bant"]
    assert b["kumulatif_r"] == -16.0 and b["inceleme"] is True and b["r_basina_usd"] == 3.75
    assert any("EMEKLİLİK İNCELEMESİ" in u for u in r["uyarilar"])


def test_eksik_alan_veri_yok_ve_vekil(tmp_path):
    """Yürütücü canlı işlem yazmıyor: R kuralları 'veri yok'; gömülü paper vekil olarak ayrı etiketli; stopsuz sayılır."""
    _hesap(tmp_path, {cr.S_E0V1EN: 60, cr.S_EWO: 250})
    _jsonl(tmp_path / "islemler.jsonl", [_isl(cr.S_E0V1EN, i, -1.0, 1 + i) for i in range(5)])
    for sid, h in ((cr.S_E0V1EN, "aaa"), (cr.S_EWO, "bbb")):
        _yaz(tmp_path / "canli" / f"yurutucu_{h}.json", {"strateji": sid, "kill": False, "gun_blok": False, "zirve": "60",
                                                          "pozlar": {"k": {"durum": "acik", "stop_id": None}, "k2": {"durum": "acik", "stop_id": "x"}}})
    r = _rapor(tmp_path)
    e = r["stratejiler"][cr.S_E0V1EN]["emeklilik_kurali"]
    assert e["durum"] == cr.YOK and e["vekil_paper"]["toplam_r"] == -5.0
    assert r["stratejiler"][cr.S_EWO]["ewo_bant"]["durum"] == cr.YOK
    assert r["stratejiler"][cr.S_E0V1EN]["maliyet"]["durum"] == cr.YOK
    assert r["sistem"]["stopsuz_toplam"] == 2
    assert any("STOPSUZ" in u for u in r["uyarilar"])
    assert any("canlı kapanan işlem kaydı" in x for x in r["yazilmayan_alanlar"])
    md = cr.markdown(r)
    assert "veri yok (yürütücü yazmıyor)" in md and "girilmedi" in md   # sunucu gideri


def test_sunucu_gideri_ve_cikti_dosyalari(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60})
    cikti = tmp_path / "out" / "rapor.md"
    assert cr.main(["--canli-durum", str(tmp_path), "--bitis", BIT, "--baslangic", "2026-12-01", "--sunucu-gider-usd-ay", "6", "--cikti", str(cikti)]) == 0
    assert "6 USD/ay" in cikti.read_text(encoding="utf-8")
    j = json.loads(cikti.with_suffix(".json").read_text(encoding="utf-8"))
    assert j["toplam"]["sunucu_gideri"]["usd_ay"] == 6.0


def test_bozuk_dosya_acik_hata(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60})
    (tmp_path / "olaylar.jsonl").write_text('{"zaman": 1\n', encoding="utf-8")
    r = _rapor(tmp_path)
    assert any("bozuk JSON" in h for h in r["okuma_hatalari"])


def test_paper_stratejileri(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60})
    pdir = tmp_path / "paper"
    _jsonl(pdir / "islemler.jsonl", [_isl("dis__lube", 0, 2.0, 20), _isl("dis__lube", 1, -1.0, 3)])
    r = cr.rapor_uret(tmp_path, paper_durum=pdir, bitis=BIT)
    p = r["paper_stratejileri"]["dis__lube"]
    assert p["islem"] == 2 and p["toplam_r"] == 1.0 and p["hafta_islem"] == 1 and p["hafta_r"] == 2.0


# ============================================================================= yürütücünün yazdığı yeni kayıt dosyalarından (islemler / ozsermaye_gunluk / olaylar_arsiv)
def _srow(gun, sid, kasa, tahsis, ozs=None, neden="gun", kz=0):
    return {"tur": "strateji", "zaman": f"{gun}T00:05:00.000000Z", "gun": gun, "neden": neden, "strateji": sid, "mod": "canli", "ozsermaye": str(ozs or kasa),
            "tahsis_usd": str(tahsis), "kasa": str(kasa), "acik_kz_usd": str(kz), "acik_pozisyon": 0}


def _hrow(gun, toplam, neden="gun"):
    return {"tur": "hesap", "gun": gun, "zaman": f"{gun}T00:06:00.000000Z", "neden": neden, "toplam": str(toplam), "zirve": str(toplam), "kimlikler": [cr.S_EWO], "kill": False}


def test_en_buyuk_dusus_gunluk_kesitten_ve_esik(tmp_path):
    S = cr.S_EWO
    rows = [_srow("2026-12-15", S, 250, 250, neden="servis_basi"), _hrow("2026-12-15", 250, "servis_basi"),
            _srow("2026-12-16", S, 280, 280), _hrow("2026-12-16", 280),
            _srow("2026-12-17", S, 252, 280), _hrow("2026-12-17", 252),
            _srow("2026-12-18", S, 266, 280), _hrow("2026-12-18", 266)]       # dip %10, güncel %5
    _jsonl(tmp_path / "canli" / "ozsermaye_gunluk.jsonl", rows)
    _hesap(tmp_path, {S: 266}, zirve=280)
    r = _rapor(tmp_path)
    e = r["toplam"]["en_buyuk_dusus"]
    assert abs(e["oran"] - 0.10) < 1e-6 and e["dip_zaman"].startswith("2026-12-17") and e["kesit_sayisi"] == 4
    assert abs(r["toplam"]["dusus"]["guncel_dusus"] - 0.05) < 1e-6
    assert r["toplam"]["net_usd"] == 16.0 and r["toplam"]["baslangic_tahsis"] == 250.0       # ilk kasa 250; ayar gerekmedi
    md = cr.markdown(r)
    assert "En büyük düşüş: %10.00" in md


def test_sermaye_hareketi_kar_sayilmaz_net_ve_dusus(tmp_path):
    S = cr.S_E0V1EN
    rows = [_srow("2026-12-15", S, 60, 60, ozs=60, neden="servis_basi"), _hrow("2026-12-15", 60, "servis_basi"),
            {"tur": "sermaye_hareketi", "zaman": "2026-12-16T00:04:00.000000Z", "gun": "2026-12-16", "strateji": S, "onceki_tahsis_usd": "60", "yeni_tahsis_usd": "250",
             "fark_usd": "190", "ozsermaye_o_an": "250"},
            _srow("2026-12-16", S, 250, 250, neden="servis_basi"), _hrow("2026-12-16", 250, "servis_basi")]
    _jsonl(tmp_path / "canli" / "ozsermaye_gunluk.jsonl", rows)
    _hesap(tmp_path, {S: 250})
    r = _rapor(tmp_path)
    t = r["toplam"]
    assert t["sermaye_hareketi_usd"] == 190.0 and t["baslangic_tahsis"] == 250.0
    assert t["net_usd"] == 0.0                                                       # 60 -> 250 geçişi kâr sayılmadı
    assert r["stratejiler"][S]["net_sonuc"] == 0.0 and r["stratejiler"][S]["sermaye_hareketi_usd"] == 190.0
    assert t["en_buyuk_dusus"]["oran"] == 0.0 and r["toplam"]["dusus"]["guncel_dusus"] == 0.0
    assert r["sistem"]["yeniden_baslatma_haftada"] == 1                              # ilk başlangıç yeniden başlatma değil, ikincisi öyle


def test_sermaye_hareketi_ara_donem_zarari_sermaye_sayilmaz():
    g = cr.gunluk_analiz([_srow("2026-12-15", "a", 100, 100, neden="servis_basi"),
                          {"tur": "sermaye_hareketi", "zaman": "2026-12-16T00:04:00Z", "strateji": "a", "yeni_tahsis_usd": "250", "fark_usd": "150", "ozsermaye_o_an": "90"},
                          _srow("2026-12-16", "a", 90, 250)])
    assert g["stratejiler"]["a"]["hareket_usd"] == 0.0                              # para yatırılmadı (özsermaye düşmüş): hareket 0, zarar korunur


def test_yeni_strateji_sonradan_eklenince_sermaye_girisi():
    g = cr.gunluk_analiz([_srow("2026-12-15", "a", 100, 100, neden="servis_basi"), _srow("2026-12-20", "b", 250, 250, neden="servis_basi")])
    assert g["stratejiler"]["b"]["ilk_kasa"] == 0.0 and g["stratejiler"]["b"]["hareket_usd"] == 250.0
    assert g["stratejiler"]["a"]["hareket_usd"] == 0.0


def _islem(sid, i, r, gercek=None, model=6.0, net=1.0):
    return {"strateji": sid, "kol": "K", "sembol": "BTCUSDT", "cikis_zamani": f"2026-12-{1 + i % 20:02d}T10:{i % 60:02d}:00.000000Z", "zaman": f"2026-12-{1 + i % 20:02d}T10:{i % 60:02d}:00.000000Z",
            "giris_fiyati": "50000", "miktar": "0.01", "r": r, "net_pnl_usd": str(net), "komisyon_usd": "0.5", "funding_usd": "-0.01",
            "gercek_maliyet_bps": gercek, "model_maliyet_bps": model}


def test_maliyet_ilk30_islem_emeklilik_olcutu_islemlerden(tmp_path):
    S = cr.S_E0V1EN
    _hesap(tmp_path, {S: 60})
    _jsonl(tmp_path / "canli" / "islemler.jsonl", [_islem(S, i, -0.1, gercek=12.0) for i in range(30)])        # oran 12/6 = 2
    r = _rapor(tmp_path)
    m = r["stratejiler"][S]["maliyet"]
    assert m["oran"] == 2.0 and m["oran_ilk30"] == 2.0 and m["emeklilik"].startswith("EMEKLİLİK")
    assert any("maliyet oranı 2.00" in u for u in r["uyarilar"]) and any("EMEKLİLİK ölçütü" in u for u in r["uyarilar"])
    ci = r["stratejiler"][S]["canli_islemler"]
    assert ci["islem"] == 30 and ci["net_usd"] == 30.0 and ci["komisyon_usd"] == 15.0 and ci["funding_usd"] == -0.3


def test_maliyet_yalniz_ilk_30_islem_sayilir_sonrasi_oran_degistirmez(tmp_path):
    S = cr.S_E0V1EN
    _hesap(tmp_path, {S: 60})
    satirlar = [_islem(S, i, 0.0, gercek=7.0) for i in range(30)] + [_islem(S, 30 + i, 0.0, gercek=30.0) for i in range(10)]   # ilk 30: 7/6 (< 1,5); sonraki 10 pahalı
    for i, x in enumerate(satirlar):
        x["cikis_zamani"] = x["zaman"] = f"2026-12-{1 + i // 2:02d}T{i % 2:02d}:00:00.000000Z"
    _jsonl(tmp_path / "canli" / "islemler.jsonl", satirlar)
    m = _rapor(tmp_path)["stratejiler"][S]["maliyet"]
    assert m["oran_ilk30"] < 1.5 and "geçildi" in m["emeklilik"] and m["oran"] > 1.5          # genel oran uyarı, emeklilik ölçütü yalnız ilk 30


def test_e0v1en_ve_ewo_kurallari_islemler_jsonl_strateji_alanindan(tmp_path):
    _hesap(tmp_path, {cr.S_E0V1EN: 60, cr.S_EWO: 250})
    _jsonl(tmp_path / "canli" / "islemler.jsonl", [_islem(cr.S_E0V1EN, i, -0.3) for i in range(60)] + [_islem(cr.S_EWO, i, -1.0) for i in range(16)])
    r = _rapor(tmp_path, baslangic="2026-12-01")
    assert r["stratejiler"][cr.S_E0V1EN]["emeklilik_kurali"]["durum"].startswith("EMEKLİLİK")
    assert r["stratejiler"][cr.S_EWO]["ewo_bant"]["inceleme"] is True and any("EMEKLİLİK İNCELEMESİ" in u for u in r["uyarilar"])


def test_eslesme_arsivden_sinirsiz_ve_kumulatif(tmp_path):
    S = cr.S_EWO
    _hesap(tmp_path, {S: 250})
    ol = [{"zaman": f"2026-12-{10 + i // 12:02d}T{i % 12:02d}:00:00.000000Z", "strateji": S, "tur": "canli_emir_doldu", "mesaj": "k BTCUSDT LONG 1 @ 1"} for i in range(60)]   # 60 > 50
    ol += [{"zaman": "2026-12-19T20:00:00.000000Z", "strateji": S, "tur": "min_tutar_alti", "mesaj": "k (X): min_tutar_alti: ..."}]
    _jsonl(tmp_path / "canli" / "olaylar_arsiv.jsonl", ol)
    e = _rapor(tmp_path)["stratejiler"][S]["eslesme"]
    assert e["kumulatif_doldu"] == 60 and e["kumulatif_atlanan"] == 1 and abs(e["kumulatif_oran"] - 60 / 61) < 1e-3
    assert e["oran"] is not None and "olaylar_arsiv" in e["aciklama"] and e["nedenler"] == {"min tutar (borsa asgari emri)": 1}


def test_yaz_karsilastirma_risk_adim_kontrol_sozlesmesiyle(tmp_path):
    from motor.canli.borsa.risk_adim_kontrol import kontrol
    S = cr.S_E0V1EN
    _hesap(tmp_path, {S: 60})
    _jsonl(tmp_path / "canli" / "islemler.jsonl", [_islem(S, i, 0.1, gercek=12.0) for i in range(5)])        # oran 2,0 -> maliyet şartı HAYIR
    _jsonl(tmp_path / "canli" / "olaylar_arsiv.jsonl", [{"zaman": "2026-12-18T10:00:00.000000Z", "strateji": S, "tur": "canli_emir_doldu", "mesaj": "k"} for _ in range(19)]
           + [{"zaman": "2026-12-18T11:00:00.000000Z", "strateji": S, "tur": "min_tutar_alti", "mesaj": "k"}])                                     # %95 eşleşme
    _yaz(tmp_path / "canli" / "yurutucu_x.json", {"strateji": S, "kill": False, "pozlar": {}})
    r = _rapor(tmp_path, karsilastirma_yaz=True)
    d = json.loads((tmp_path / "canli" / "haftalik_karsilastirma.json").read_text(encoding="utf-8"))
    assert d[S]["canli_maliyet_bps"] == 12.0 and d[S]["model_maliyet_bps"] == 6.0 and d[S]["eslesme_orani"] == 0.95 and d[S]["islem_sayisi"] == 5
    assert r["karsilastirma_yazildi"].endswith("haftalik_karsilastirma.json")
    k = kontrol(tmp_path)[S]
    assert k["maliyet_orani_ok"] == "hayir" and k["eslesme_ok"] == "evet"                    # risk_adim_kontrol artık 'bilinmiyor' değil
    # yazma yalnız bayrakla
    (tmp_path / "canli" / "haftalik_karsilastirma.json").unlink()
    _rapor(tmp_path)
    assert not (tmp_path / "canli" / "haftalik_karsilastirma.json").exists()


def test_kayit_hata_sayisi_uyari(tmp_path):
    _hesap(tmp_path, {cr.S_EWO: 250})
    _yaz(tmp_path / "canli" / "yurutucu_x.json", {"strateji": cr.S_EWO, "kill": False, "pozlar": {}, "kayit_hata_sayisi": {"islemler": 2}})
    r = _rapor(tmp_path)
    assert any("kayıt yazım hataları" in u for u in r["uyarilar"])
