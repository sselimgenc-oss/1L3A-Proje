"""v2 havuz üretimi (ON_KAYIT_V2 bölüm 2): deterministik kurallar sentetik girdilerle; gerçek çıktı dosyaları için tutarlılık."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

KOK = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("havuz_v2_olustur", KOK / "araclar" / "havuz_v2_olustur.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


# ---------------------------------------------------------------- yardımcılar
def _hafta_indeksi(n: int, bas: str = "2019-01-07"):
    return pd.period_range(bas, periods=n, freq="W-SUN")


def _seriler_kor(matris_kor: np.ndarray, n: int = 150, tohum: int = 1, adlar=None) -> dict[str, pd.Series]:
    """Örnek korelasyon matrisi TAM olarak `matris_kor` olan seriler (QR ile)."""
    rng = np.random.default_rng(tohum)
    k = matris_kor.shape[0]
    x = rng.standard_normal((n, k))
    x -= x.mean(axis=0)
    q, _ = np.linalg.qr(x)
    l = np.linalg.cholesky(matris_kor)
    y = q @ l.T
    y = y / y.std(axis=0, ddof=0)
    adlar = adlar or [f"s{i}" for i in range(k)]
    idx = _hafta_indeksi(n)
    return {a: pd.Series(y[:, i], index=idx) for i, a in enumerate(adlar)}


def _kor2(r: float) -> np.ndarray:
    return np.array([[1.0, r], [r, 1.0]])


# ---------------------------------------------------------------- 2.3 klon kuralı
def test_klon_kurali_sadece_swing_kalir():
    adlar = ["swing__a", "daytrade__a", "scalp__a", "daytrade__b", "scalp__c", "swing__c", "dis__x", "onceki__y"]
    tutulan, atilan = H.klon_kurali(adlar)
    assert tutulan == {"swing__a": ["daytrade__a", "scalp__a"], "swing__c": ["scalp__c"]}
    assert atilan == ["daytrade__a", "daytrade__b", "scalp__a", "scalp__c"]     # swing karşılığı olmayan b havuza girmez
    assert "dis__x" not in atilan and "onceki__y" not in atilan                 # kitap önekli olmayan: kural dışı


def test_klon_kurali_klonsuz_swing_oldugu_gibi():
    tutulan, atilan = H.klon_kurali(["swing__z"])
    assert tutulan == {"swing__z": []} and atilan == []


# ---------------------------------------------------------------- 2.4 birincil tf
@pytest.mark.parametrize("metinler,beklenen", [
    (["4h"], "4h"), (["4H"], "4h"), (["4s"], "4h"), (["H4"], "4h"), (["240"], "4h"), (["240 dk"], "4h"),
    (["4h", "1d"], "1d"),                      # 4h var, 1d de var -> 1d
    (["4h veya günlük"], "1d"), (["4h daily"], "1d"), (["4h / D"], "1d"), (["4h 1g"], "1d"),
    ([], "1d"), ([""], "1d"), ([None], "1d"), (["  "], "1d"),   # boş -> 1d
    (["1h"], "1d"), (["15m"], "1d"), (["1W"], "1d"), (["60dk"], "1d"),
    (['{"islem": "4H", "ust_filtre": null}'], "4h"),
    (['{"islem": "4H", "ust_filtre": "1D"}'], "1d"),
    (["14h"], "1d"),                           # 4h için sol sınır: '14h' 4h değildir
])
def test_birincil_tf(metinler, beklenen):
    assert H.birincil_tf(metinler) == beklenen


# ---------------------------------------------------------------- sayısal parametre sayısı
def test_sayisal_parametre_sayisi():
    ayar = {"a": 1, "b": 2.5, "c": True, "d": "x", "e": None, "f": (1, 2), "g": [3, "u"], "h": {"i": 4, "j": False}}
    assert H.sayisal_parametre_sayisi(ayar) == 1 + 1 + 0 + 0 + 0 + 2 + 1 + 1
    assert H.sayisal_parametre_sayisi({}) == 0


def test_varsayilan_ayar_kart_ayari_ilk_kayit():
    class S:
        varsayilan_parametreler = {"p": 1, "q": 2}
    assert H.varsayilan_ayar(S, None) == {"p": 1, "q": 2}
    assert H.varsayilan_ayar(S, [{"parametreler": {"p": 9}}, {"parametreler": {"q": 7}}]) == {"p": 9, "q": 2}
    assert H.varsayilan_ayar(S, [{"parametreler": None}]) == {"p": 1, "q": 2}


# ---------------------------------------------------------------- 2.7 haftalık seri
def test_haftalik_seri_pazar_kapanisli_kabul_ve_sifir_doldurma():
    oos = pd.DataFrame({
        "cikis": pd.to_datetime(["2024-01-07 23:00", "2024-01-08 00:00", "2024-01-09 10:00", "2024-01-23 12:00",
                                 "2024-01-10 09:00"], utc=True),
        "kabul": [True, True, True, True, False],
        "pnl": [1.0, 2.0, 4.0, 8.0, 1000.0],
    })
    s = H.haftalik_seri(oos)
    # 2024-01-07 (Pazar) önceki haftada; Pazartesi 01-08 ve Salı 01-09 sonraki haftada; kabul=False atılır
    assert s.loc[pd.Period("2024-01-07", "W-SUN")] == 1.0
    assert s.loc[pd.Period("2024-01-14", "W-SUN")] == 6.0
    assert s.loc[pd.Period("2024-01-21", "W-SUN")] == 0.0          # işlemsiz hafta 0
    assert s.loc[pd.Period("2024-01-28", "W-SUN")] == 8.0
    assert len(s) == 4


# ---------------------------------------------------------------- 2.7 kümeleme (sentetik)
def test_korelasyon_071_ayni_kume_069_ayri():
    s = _seriler_kor(_kor2(0.71), adlar=["a", "b"])
    assert H.ortalama_baglanti(["a", "b"], s) == [["a", "b"]]
    s = _seriler_kor(_kor2(0.69), adlar=["a", "b"])
    assert H.ortalama_baglanti(["a", "b"], s) == [["a"], ["b"]]


def test_ortak_hafta_99_olculemedi_ayri_100_birlesir():
    s = _seriler_kor(_kor2(0.9), n=150, adlar=["a", "b"])
    a99 = s["a"].iloc[:99]
    assert np.isnan(H.korelasyon(a99, s["b"].iloc[:99]))
    assert H.ortalama_baglanti(["a", "b"], {"a": a99, "b": s["b"].iloc[:99]}) == [["a"], ["b"]]
    assert H.ortalama_baglanti(["a", "b"], {"a": s["a"].iloc[:100], "b": s["b"].iloc[:100]}) == [["a", "b"]]
    # ortak hafta, serilerin KESİŞİMİdir (ofsetli seriler)
    assert np.isnan(H.korelasyon(s["a"].iloc[:100], s["b"].iloc[50:]))          # kesişim 50 hafta


def test_serisi_olmayan_veya_sabit_ayri_kume():
    s = _seriler_kor(_kor2(0.95), adlar=["a", "b"])
    assert H.ortalama_baglanti(["a", "b", "c"], s) == [["a", "b"], ["c"]]        # c'nin serisi yok
    sabit = pd.Series(0.0, index=s["a"].index)
    assert H.ortalama_baglanti(["a", "z"], {"a": s["a"], "z": sabit}) == [["a"], ["z"]]


def test_ortalama_baglanti_zincirleme_yok():
    # a-b 0.85, b-c 0.85, a-c 0.6: {a,b}-c ortalama uzaklık (0.4 + 0.15)/2 = 0.275 <= 0.3 -> hepsi birleşir
    k = np.array([[1.0, 0.85, 0.6], [0.85, 1.0, 0.85], [0.6, 0.85, 1.0]])
    s = _seriler_kor(k, adlar=["a", "b", "c"])
    assert H.ortalama_baglanti(["a", "b", "c"], s) == [["a", "b", "c"]]
    # a-b 0.8, b-c 0.8, a-c 0.4: {a,b}-c ortalama uzaklık (0.6 + 0.2)/2 = 0.4 > 0.3 -> c ayrı (tek bağlantı olsaydı birleşirdi)
    k2 = np.array([[1.0, 0.8, 0.4], [0.8, 1.0, 0.8], [0.4, 0.8, 1.0]])
    s2 = _seriler_kor(k2, adlar=["a", "b", "c"])
    assert H.ortalama_baglanti(["a", "b", "c"], s2) == [["a", "b"], ["c"]]


def _upgma_lance_williams(d: np.ndarray, sinir: float) -> list[list[int]]:
    """Bağımsız referans: Lance-Williams güncellemesiyle ortalama bağlantı (kümeleme boyutuna göre ağırlıklı)."""
    n = d.shape[0]
    d = d.copy().astype(float)
    np.fill_diagonal(d, np.inf)
    boy = {i: 1 for i in range(n)}
    uye = {i: [i] for i in range(n)}
    aktif = set(range(n))
    while len(aktif) > 1:
        en = min(((d[i, j], i, j) for i in aktif for j in aktif if i < j), key=lambda x: (x[0], x[1], x[2]))
        if en[0] > sinir:
            break
        _, i, j = en
        for k in aktif - {i, j}:
            yeni = (boy[i] * d[i, k] + boy[j] * d[j, k]) / (boy[i] + boy[j])
            d[i, k] = d[k, i] = yeni
        uye[i] += uye[j]
        boy[i] += boy[j]
        aktif.remove(j)
        d[j, :] = np.inf
        d[:, j] = np.inf
    return sorted(sorted(uye[i]) for i in aktif)


def test_ortalama_baglanti_lance_williams_referansiyla_ayni():
    rng = np.random.default_rng(7)
    n, k = 160, 9
    taban = rng.standard_normal((n, 3))
    x = np.column_stack([taban[:, i % 3] * 0.9 + rng.standard_normal(n) * 0.5 for i in range(k)])
    idx = _hafta_indeksi(n)
    adlar = [f"s{i}" for i in range(k)]
    seriler = {a: pd.Series(x[:, i], index=idx) for i, a in enumerate(adlar)}
    benim = H.ortalama_baglanti(adlar, seriler)
    d = 1 - np.corrcoef(x.T)
    ref = _upgma_lance_williams(d, 0.3 + 1e-12)
    assert sorted(benim) == sorted([[adlar[i] for i in kume] for kume in ref])
    assert any(len(c) > 1 for c in benim)                 # test anlamlı: en az bir birleşme var


def test_temsilci_en_az_parametreli_sonra_alfabetik():
    psay = {"a": 5, "b": 3, "c": 3, "d": 9}
    assert H.temsilci(["a", "b", "c", "d"], psay) == "b"       # 3 eşit (b, c) -> alfabetik ilk
    assert H.temsilci(["a", "d"], psay) == "a"
    assert H.temsilci(["d"], psay) == "d"


def _satir(ad, stil="swing", tf="1d", psay=1):
    return {"strateji": ad, "stil_v2": stil, "tf": tf, "evren": "genel", "param_say": psay, "kaynak_strateji": ""}


def test_havuz_kur_ayni_etiket_alt_etiket_birlesir_farkli_ayrilir():
    s = _seriler_kor(np.array([[1, .71, .71], [.71, 1, .71], [.71, .71, 1]], dtype=float), adlar=["a", "b", "c"])
    sat = [_satir("a", psay=4), _satir("b", psay=2), _satir("c", psay=9)]
    et = {"a": {"etiket": "trend", "alt_etiket": "macd"}, "b": {"etiket": "trend", "alt_etiket": "macd"},
          "c": {"etiket": "trend", "alt_etiket": "rsi"}}
    havuz, kumeler = H.havuz_kur(sat, et, s, set())
    assert sorted(havuz["strateji"]) == ["b", "c"]            # a,b birleşti (temsilci b: 2 parametre), c alt etiketi farklı
    assert havuz.set_index("strateji").loc["b", "not"].endswith("kume_uyeleri_havuz_disi=a")
    assert sorted(map(sorted, kumeler)) == [["a", "b"], ["c"]]
    assert list(havuz["kume_no"]) == [1, 2]


def test_havuz_kur_v1_serisi_olmayan_sadece_klonla_kumelenir_yani_ayri():
    s = _seriler_kor(_kor2(0.95), adlar=["a", "b"])
    sat = [_satir("a"), _satir("b"), _satir("yeni")]
    et = {x: {"etiket": "donus", "alt_etiket": "rsi"} for x in ("a", "b", "yeni")}
    havuz, _ = H.havuz_kur(sat, et, s, set())
    assert sorted(havuz["strateji"]) == ["a", "yeni"]


def test_havuz_kur_gunici_ve_portfoy_kumelenmez_ve_kilit_bayragi():
    s = _seriler_kor(_kor2(0.95), adlar=["g1", "g2"])
    sat = [_satir("g1", "gunici_kripto", "15m"), _satir("g2", "gunici_kripto", "15m"), _satir("pf__x", "portfoy")]
    et = {x: {"etiket": "donus", "alt_etiket": "bollinger"} for x in ("g1", "g2", "pf__x")}
    havuz, _ = H.havuz_kur(sat, et, s, kilitli={"g2"})
    assert list(havuz["strateji"]) == ["g1", "g2", "pf__x"]       # sıra: stil sırası sonra alfabetik
    assert list(havuz["kilit_gorulmus"]) == ["hayir", "evet", "hayir"]
    assert list(havuz.columns) == H.SUTUNLAR


def test_havuz_kur_etiketsiz_veya_fazla_etiket_acik_hata():
    with pytest.raises(KeyError):
        H.havuz_kur([_satir("a")], {}, {}, set())
    with pytest.raises(KeyError):
        H.havuz_kur([_satir("a")], {"a": {"etiket": "trend", "alt_etiket": "x"},
                                    "z": {"etiket": "trend", "alt_etiket": "x"}}, {}, set())


# ---------------------------------------------------------------- 2.9 ad taraması
def test_adlari_tara_yalniz_adlar():
    metin = '{"stratejiler": ["swing__ma-kesisim", "dis__tsmom"], "pf": 1.23, "x": "dis__yok-boyle"}'
    assert H.adlari_tara(metin, {"swing__ma-kesisim", "dis__tsmom", "dis__baska"}) == {"swing__ma-kesisim", "dis__tsmom"}


def test_kilit_gorulmus_adlar_gecici_dizinde(tmp_path):
    (tmp_path / "stratejiler").mkdir()
    (tmp_path / "sonuclar" / "kilit").mkdir(parents=True)
    (tmp_path / "stratejiler" / "final_set.json").write_text(json.dumps({"stratejiler": ["dis__a", "dis__b"]}))
    (tmp_path / "sonuclar" / "kilit" / "set.csv").write_text("strateji,x\ndis__c,1\n")
    (tmp_path / "sonuclar" / "kilit" / "sonuc.csv").write_text("strateji,x\ndis__d,1\n")      # 'set' içermez: okunmaz
    bulunan = H.kilit_gorulmus_adlar({"dis__a", "dis__b", "dis__c", "dis__d", "dis__e"}, {"dis__e", "dis__zz"}, kok=tmp_path)
    assert bulunan == {"dis__a", "dis__b", "dis__c", "dis__e"}


# ---------------------------------------------------------------- 2.10 m
@pytest.mark.parametrize("n,m", [(300, 939), (938, 939), (939, 939), (940, 940), (1000, 1000), (0, 939)])
def test_m_kurali(n, m):
    assert H.m_hesapla(n) == m


# ---------------------------------------------------------------- csv + mühür
def _mini_havuz():
    return pd.DataFrame([{"strateji": "a", "stil_v2": "swing", "tf": "1d", "evren": "genel", "etiket": "trend",
                          "alt_etiket": "macd", "kume_no": 1, "kaynak_strateji": "", "kilit_gorulmus": "hayir",
                          "not": "param_say=3"}], columns=H.SUTUNLAR)


def test_csv_deterministik_ve_muhur_icerigi(tmp_path):
    havuz = _mini_havuz()
    b1, b2 = H.csv_baytlari(havuz), H.csv_baytlari(havuz)
    assert b1 == b2 and b1.endswith(b"\n") and b"\r" not in b1
    csv_yolu = tmp_path / "havuz.csv"
    csv_yolu.write_bytes(b1)
    etiket = tmp_path / "etiket.csv"
    etiket.write_text("strateji,etiket,alt_etiket,gerekce\n")
    muhur_yolu = tmp_path / "v2" / "havuz_muhru.json"
    zaman = H.dt.datetime(2026, 11, 9, 12, 0, 0, tzinfo=H.dt.timezone.utc)
    m = H.muhur_yaz(havuz, csv_yolu, muhur_yolu, Path(H.__file__), etiket, kok=KOK, zaman=zaman)
    j = json.loads(muhur_yolu.read_text(encoding="utf-8"))
    assert j == m
    assert j["havuz_csv_sha256"] == H.sha256_bayt(b1)
    assert j["satir_sayisi"] == 1 and j["m"] == 939
    assert j["script_sha256"] == H.sha256_bayt(Path(H.__file__).read_bytes())
    assert len(j["git_commit"]) == 40 and j["zaman_damgasi_utc"] == "2026-11-09T12:00:00Z"
    assert {"havuz_csv_sha256", "satir_sayisi", "m", "script_sha256", "git_commit", "zaman_damgasi_utc"} <= set(j)


# ---------------------------------------------------------------- etiket dosyası ve gerçek çıktı tutarlılığı
def test_etiket_dosyasi_gecerli():
    et = H.etiketleri_oku()
    assert len(et) == 216 and all(v["etiket"] in H.ETIKETLER and v["alt_etiket"] for v in et.values())


def test_etiketler_gecersizse_acik_hata(tmp_path):
    yol = tmp_path / "e.csv"
    yol.write_text("strateji,etiket,alt_etiket,gerekce\na,bilinmeyen,x,y\n")
    with pytest.raises(ValueError):
        H.etiketleri_oku(yol)
    yol.write_text("strateji,etiket,alt_etiket,gerekce\na,trend,x,y\na,trend,x,y\n")
    with pytest.raises(ValueError):
        H.etiketleri_oku(yol)


@pytest.mark.skipif(not H.HAVUZ_CSV.exists() or not H.MUHUR_JSON.exists(), reason="havuz henüz üretilmedi")
def test_gercek_havuz_kurallari_ve_muhur_uyumu():
    h = pd.read_csv(H.HAVUZ_CSV, dtype=str, keep_default_na=False)
    j = json.loads(H.MUHUR_JSON.read_text(encoding="utf-8"))
    assert list(h.columns) == H.SUTUNLAR
    assert j["havuz_csv_sha256"] == H.sha256_bayt(H.HAVUZ_CSV.read_bytes())
    assert j["satir_sayisi"] == len(h) and j["m"] == max(len(h), 939)
    assert h["strateji"].is_unique and h["kume_no"].astype(int).is_unique
    # 2.2/2.3: swing satırlarında daytrade__/scalp__ klonu yok
    assert not h["strateji"].str.startswith(("daytrade__", "scalp__")).any()
    # 2.4
    sw = h[h["stil_v2"] == "swing"]
    assert set(sw["tf"]) <= {"1d", "4h"} and set(sw["evren"]) == {"genel"}
    # 2.5: tam 7 satır, 15m, kripto
    gk = h[h["stil_v2"] == "gunici_kripto"]
    assert sorted(gk["strateji"]) == sorted(H.GUNICI_KRIPTO) and set(gk["tf"]) == {"15m"} and set(gk["evren"]) == {"kripto"}
    # portföy: 19 pf__ sınıfı, 1d
    pf = h[h["stil_v2"] == "portfoy"]
    assert len(pf) == 19 and pf["strateji"].str.startswith("pf__").all() and set(pf["tf"]) == {"1d"}
    assert set(h["kilit_gorulmus"]) <= {"evet", "hayir"}
    assert set(h["etiket"]) <= H.ETIKETLER
