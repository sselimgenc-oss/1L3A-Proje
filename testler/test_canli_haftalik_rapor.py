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
