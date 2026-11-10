"""B16 (denetim kapanışı): kimlik damgasının kapsamı. Yalnız SENTETİK veri.
  1. veri özeti (veri_sha256) her okuma/devam kararında şimdiki veriyle karşılaştırılır; veri değişince görev yeniden koşar/reddedilir;
  2. devam kararı yalnız "yan dosya var" değildir: bayat damga atlanmaz;
  3. motor_hash kapsamı htf/gösterge/yeniden örnekleme/çıkış/funding/depo/ham modüllerini de içerir;
  4. eski (damgasız) v2 çıktısı yalnız açık bayrakla okunur ve DEĞİŞTİRİLMEZ."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_maliyet
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import ham, maliyet

KOK = Path(__file__).resolve().parents[1]
AD, TF, SEM = "swing__bant-donus", "1d", "DK_XAU"


def sentetik(n=1500, seed=3, bas="2018-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.005, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.005, n)))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": rng.uniform(1e3, 2e3, n)}, index=idx)


@pytest.fixture(autouse=True)
def _temiz(monkeypatch):
    ham.damga_onbellegini_sifirla()
    monkeypatch.delenv(ham.ESKI_ORTAM, raising=False)

    def yok(sembol, tf):
        raise FileNotFoundError("test: gerçek veri yok")
    monkeypatch.setattr(we, "_veri", yok)
    yield
    ham.damga_onbellegini_sifirla()


@pytest.fixture()
def tablo(tmp_path):
    y = maliyet.tabloyu_hazirla(tmp_path)
    return y, evren_maliyet.tablo_hash(y)


@pytest.fixture(scope="module")
def veri_a():
    return sentetik()


@pytest.fixture(scope="module")
def veri_b():
    return sentetik(seed=4)                                   # AYNI uzunluk/indeks, farklı içerik


def _yan(cikti: Path) -> Path:
    return ham.dosya_yolu(cikti / "ham" / "x1", AD, TF, SEM).with_suffix(".json")


def _kos(cikti, y, h, veri, **kw):
    return ham.ham_gorev(AD, TF, SEM, 1.0, cikti, y, h, _veri=lambda s, t: (veri, None), **kw)


def _yeniden_koşmuş_mu(r) -> bool:
    return r != {"atlandi": True} and r.get("n_islem", 0) > 0


# ------------------------------------------------------------------ 1. veri değişimi
def test_veri_degisince_gorev_yeniden_kosar(tablo, tmp_path, veri_a, veri_b):
    y, h = tablo
    ilk = _kos(tmp_path, y, h, veri_a)
    assert ilk["veri_sha256"] == ham.veri_sha256(veri_a, None)
    assert _kos(tmp_path, y, h, veri_a) == {"atlandi": True}                      # aynı veri: atlanır (davranış korunur)
    r = _kos(tmp_path, y, h, veri_b)                                              # veri değişti: ATLANMAZ
    assert _yeniden_koşmuş_mu(r) and r["veri_sha256"] == ham.veri_sha256(veri_b, None) != ilk["veri_sha256"]
    assert json.loads(_yan(tmp_path).read_text())["veri_sha256"] == r["veri_sha256"]          # yan dosya yenilendi


def test_veri_degisince_planlama_gorevi_kuyruga_alir(tablo, tmp_path, veri_a, veri_b):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    havuz = pd.DataFrame([{"strateji": AD, "stil_v2": "swing", "tf": TF, "evren": "kripto"}])
    kripto_tek = lambda s, t: (veri_a, None)                                      # noqa: E731
    # DK_XAU kripto evreninde değil: yalnız o dosyayı sınamak için BTCUSDT yan dosyasını elle kopyala
    kaynak = _yan(tmp_path)
    hedef = ham.dosya_yolu(tmp_path / "ham" / "x1", AD, TF, "BTCUSDT").with_suffix(".json")
    hedef.write_text(kaynak.read_text())
    _, _, kalan_ayni = ham.gorevleri_uret(havuz, tmp_path, veri_al=kripto_tek)
    _, _, kalan_degisti = ham.gorevleri_uret(havuz, tmp_path, veri_al=lambda s, t: (veri_b, None))
    assert kalan_ayni == 25 and kalan_degisti == 26                               # bayat dosya "bitti" sayılmaz


def test_veri_degisince_ham_yukle_reddeder_ve_veri_al_zorunlu(tablo, tmp_path, veri_a, veri_b):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    ok = ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=lambda s, t: (veri_a, None))[0]
    assert SEM in ok
    with pytest.raises(RuntimeError, match="veri_sha256 uyuşmuyor"):
        ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=lambda s, t: (veri_b, None))
    with pytest.raises(ValueError, match="veri özeti"):                           # özet verilmedi: sessizce atlanmaz
        ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h)


def test_veri_sonradan_gelirse_veri_yok_yan_dosyasi_bayat(tablo, tmp_path, veri_a):
    y, h = tablo

    def yok(s, t):
        raise FileNotFoundError("yok")
    r = ham.ham_gorev(AD, TF, SEM, 1.0, tmp_path, y, h, _veri=yok)
    assert r["veri_yok"] and r["veri_sha256"] is None
    assert ham.ham_gorev(AD, TF, SEM, 1.0, tmp_path, y, h, _veri=yok) == {"atlandi": True}
    assert _yeniden_koşmuş_mu(_kos(tmp_path, y, h, veri_a))                       # veri geldi: yeniden koşar


# ------------------------------------------------------------------ 2. devam kararı bayat damgayı atlamaz
@pytest.mark.parametrize("alan", ["strateji_hash", "motor_hash", "maliyet_hash"])
def test_bayat_damga_devamda_atlanmaz(alan, tablo, tmp_path, veri_a):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    yan = _yan(tmp_path)
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps(dict(m, **{alan: "0" * 64})))
    r = _kos(tmp_path, y, h, veri_a)
    assert _yeniden_koşmuş_mu(r)
    assert json.loads(yan.read_text())[alan] == m[alan]                           # yeni damga yazıldı
    assert _kos(tmp_path, y, h, veri_a) == {"atlandi": True}


def test_commit_atasi_degilse_devamda_atlanmaz(tablo, tmp_path, veri_a, monkeypatch):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    from motor.arastirma import wf_evren_holdout as v1h
    monkeypatch.setattr(v1h, "_commit_ata_mi", lambda a, b: False)
    assert _yeniden_koşmuş_mu(_kos(tmp_path, y, h, veri_a))


def test_bayat_planlamada_kuyruga_girer(tablo, tmp_path, veri_a):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    yan = _yan(tmp_path)
    hedef = ham.dosya_yolu(tmp_path / "ham" / "x1", AD, TF, "BTCUSDT").with_suffix(".json")
    m = json.loads(yan.read_text())
    hedef.write_text(json.dumps(dict(m, strateji_hash="1" * 64)))
    havuz = pd.DataFrame([{"strateji": AD, "stil_v2": "swing", "tf": TF, "evren": "kripto"}])
    _, _, kalan = ham.gorevleri_uret(havuz, tmp_path, veri_al=lambda s, t: (veri_a, None))
    assert kalan == 26


# ------------------------------------------------------------------ 3. motor_hash kapsamı
EK = ("htf.py", "gostergeler.py", "yeniden_ornekle.py", "cikislar.py", "funding.py", "depo.py", "ham.py")


def test_motor_hash_girdisi_ek_modulleri_kapsar():
    g = ham.motor_hash_girdisi()
    for ad in EK:
        yol = [y for y in ham.MOTOR_EK_MODULLER if y.endswith("/" + ad)]
        assert len(yol) == 1 and (KOK / yol[0]).is_file(), ad
        assert g[yol[0]], f"{yol[0]} özeti boş (dosya okunamadı)"
    assert "motor/backtest/motor.py" in g                                         # v1 ortak modülleri de duruyor


def test_htf_icerigi_degisince_eski_cikti_bayat(tablo, tmp_path, veri_a, monkeypatch):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=lambda s, t: (veri_a, None))      # şimdi uyumlu
    gercek = ham.motor_hash_girdisi()
    monkeypatch.setattr(ham, "motor_hash_girdisi", lambda: {**gercek, "motor/strateji/htf.py": "degisti"})   # htf.py içeriği değişti
    ham.damga_onbellegini_sifirla()
    with pytest.raises(RuntimeError, match="motor_hash"):
        ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=lambda s, t: (veri_a, None))
    assert _yeniden_koşmuş_mu(_kos(tmp_path, y, h, veri_a))                       # devam: atlanmaz, yeni damgayla yeniden koşar
    assert ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=lambda s, t: (veri_a, None))[0]


def test_dosya_icerigi_hash_girdisine_yansir(monkeypatch):
    """Gerçek özet yolu: htf.py'nin v1 `_sha` çıktısı değişirse motor_hash girdisi değişir."""
    from motor.arastirma import wf_evren_holdout as v1h
    once = ham.motor_hash_girdisi()
    gercek = v1h._sha
    monkeypatch.setattr(v1h, "_sha", lambda p: "x" if Path(p).name == "htf.py" else gercek(p))
    sonra = ham.motor_hash_girdisi()
    assert once["motor/strateji/htf.py"] != sonra["motor/strateji/htf.py"] == "x"
    assert {k: v for k, v in once.items() if k != "motor/strateji/htf.py"} == {k: v for k, v in sonra.items() if k != "motor/strateji/htf.py"}


# ------------------------------------------------------------------ 4. eski (damgasız) çıktı: yalnız açık bayrakla, değişmeden
def test_eski_bayrak_hala_okur_ve_dosyaya_dokunmaz(tablo, tmp_path, veri_a, monkeypatch):
    y, h = tablo
    _kos(tmp_path, y, h, veri_a)
    yan = _yan(tmp_path)
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps({k: v for k, v in m.items() if k not in ham.DAMGA_ALANLARI}))      # v2 tarihsel biçim
    once = (yan.read_bytes(), ham.dosya_yolu(tmp_path / "ham" / "x1", AD, TF, SEM).read_bytes())
    veri = lambda s, t: (veri_a, None)                                                          # noqa: E731
    with pytest.raises(RuntimeError, match="kimlik damgası yok"):
        ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=veri)
    with pytest.raises(RuntimeError, match="kimlik damgası yok"):                  # devam: reddedilir, SESSİZCE atlanmaz / yeniden yazılmaz
        _kos(tmp_path, y, h, veri_a)
    assert SEM in ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, eski_kabul=True)[0]           # bayrak: veri_al'sız da okunur
    monkeypatch.setenv(ham.ESKI_ORTAM, "1")
    assert SEM in ham.ham_yukle(tmp_path, 1.0, AD, TF, (SEM,), h, veri_al=veri)[0]
    assert _kos(tmp_path, y, h, veri_a) == {"atlandi": True}                       # bayrakla devam: tarihsel kayıt geçerli, atlanır
    havuz = pd.DataFrame([{"strateji": AD, "stil_v2": "swing", "tf": TF, "evren": "kripto"}])
    ham._yan_yaz(ham.dosya_yolu(tmp_path / "ham" / "x1", AD, TF, "BTCUSDT").with_suffix(".json"), json.loads(yan.read_text()))
    assert ham.gorevleri_uret(havuz, tmp_path, veri_al=veri)[2] == 25
    assert (yan.read_bytes(), ham.dosya_yolu(tmp_path / "ham" / "x1", AD, TF, SEM).read_bytes()) == once    # dosyalar değişmedi


def test_gercek_muhurlu_v2_yan_dosyalari_damgasiz_ve_bayrakla_okunur():
    """Mühürlü sonuclar/evren/v2 çıktısına dokunulmaz: varsa yan dosyaları damgasızdır (bayrak gerekir)."""
    kok = KOK / "sonuclar" / "evren" / "v2" / "ham"
    yanlar = sorted(kok.glob("x1/*.json"))[:5] if kok.exists() else []
    for yan in yanlar:
        m = json.loads(yan.read_text())
        assert not any(a in m for a in ham.DAMGA_ALANLARI)
        assert ham.kimlik_farki(m, AD, "swing")[0] == "damgasiz"
        assert ham.kimlik_farki(m, AD, "swing", eski_kabul=True) == (None, "")
