"""secim.py: yeniden oynatıcıda sert limitler, korelasyon/örtüşme ölçüleri, açgözlü seçimin eşiği koruması."""
import numpy as np
import pandas as pd

from motor.arastirma import secim as S

T0 = pd.Timestamp("2022-01-03", tz="UTC")


def _t(satirlar):
    """satirlar: [(giris_saat, cikis_saat, r, sf, yon, sembol)] -> yeniden_oyna tablosu."""
    return pd.DataFrame({
        "kol": [f"k{i}" for i in range(len(satirlar))],
        "sembol": [x[5] if len(x) > 5 else "AAA" for x in satirlar],
        "yon": [x[4] if len(x) > 4 else 1 for x in satirlar],
        "giris": [T0 + pd.Timedelta(hours=x[0]) for x in satirlar],
        "cikis": [T0 + pd.Timedelta(hours=x[1]) for x in satirlar],
        "r": [float(x[2]) for x in satirlar],
        "sf": [float(x[3]) for x in satirlar],
        "maliyet_payi": 0.0})          # 0: yalnız fiyat riski (sınır testleri maliyetten bağımsız); maliyet dahil: test_maliyet_dahil_risk.py


def test_tek_islem_getirisi_risk_kadar():
    s = S.yeniden_oyna(_t([(1, 30, 2.0, 0.05)]))
    assert abs(s["gunluk"].iloc[-1] - 1.02) < 1e-9
    assert s["sayac"]["reddedilen"] == 0


def test_toplam_acik_risk_5_yuzde_asilamaz():
    # 7 eşzamanlı işlem, r=0: 5'i tam, kalanı reddedilir (bütçe bitti); hiçbiri 5% üstü risk taşımaz
    s = S.yeniden_oyna(_t([(1 + i * 0.01, 40, 0.0, 0.05) for i in range(7)]))
    assert s["sayac"]["giris_kabul"] == 5
    assert s["sayac"]["reddedilen"] == 2 and s["sayac"]["red_toplam_risk"] == 2


def test_toplam_risk_kirpma():
    # 4 tam + yarım bütçe kalınca 5. kırpılır (kabul), 6. reddedilir
    satir = [(1 + i * 0.01, 40, 0.0, 0.05) for i in range(4)]
    satir.append((1.1, 40, 0.0, 0.05))
    s = S.yeniden_oyna(_t(satir), S.OynatmaAyari(toplam_risk=0.045))
    assert s["sayac"]["giris_kabul"] == 5 and s["sayac"]["kirpilan"] == 1


def test_kaldirac_3x_tavani():
    # sf=0.001 -> 1x-risk kaldıracı 10x; 3x tavanına kırpılır (ölçek 0.3)
    s = S.yeniden_oyna(_t([(1, 5, 1.0, 0.001)]))
    assert s["sayac"]["kirpilan"] == 1
    assert abs(s["gunluk"].iloc[-1] - (1 + 0.01 * 0.3)) < 1e-9


def test_gunluk_kayip_limiti_pozisyon_kapatir_ve_girisi_engeller():
    # 4 eşzamanlı -1R işlem aynı günde: gün içi muhafazakâr kayıp %3'ü aşar -> limit; sonraki aynı gün girişi reddedilir
    satir = [(1 + i * 0.01, 20, -1.0, 0.05) for i in range(4)]
    satir.append((19.0, 22, 1.0, 0.05))     # limitten sonra, aynı UTC günü
    s = S.yeniden_oyna(_t(satir))
    assert s["sayac"]["gunluk_limit_olayi"] == 1
    assert s["sayac"]["red_gunluk"] == 1
    assert s["sayac"]["zorla_kapanan"] >= 1
    # ertesi gün girişi serbest
    s2 = S.yeniden_oyna(_t(satir + [(30.0, 40, 1.0, 0.05)]))
    assert s2["sayac"]["giris_kabul"] == s["sayac"]["giris_kabul"] + 1


def test_kill_switch_sonra_islem_yok():
    # her gün tek işlem, r=-3 (%3 kayıp, günlük limiti tetiklemeden kapanır... >=%3 sınırda) -> r=-2.9
    satir = [(24 * d + 1, 24 * d + 5, -2.9, 0.05) for d in range(12)]
    s = S.yeniden_oyna(_t(satir))
    assert s["sayac"]["kill_olayi"] == 1
    assert s["sayac"]["red_kill"] >= 1
    # kill sonrası özsermaye sabit
    assert s["gunluk"].iloc[-1] == s["gunluk"].iloc[-3]
    assert s["gunluk"].min() > 0.74


def test_ozsermaye_bilesik_boyut():
    # sıralı iki +1R işlem: ikincisi büyümüş özsermayenin %1'i
    s = S.yeniden_oyna(_t([(1, 5, 1.0, 0.05), (30, 35, 1.0, 0.05)]))
    assert abs(s["gunluk"].iloc[-1] - 1.01 * 1.01) < 1e-9


def test_gunluk_getiri_toplami_korunur():
    d = pd.DataFrame({"giris_zamani": [T0 + pd.Timedelta(hours=5), T0 + pd.Timedelta(hours=50)],
                      "cikis_zamani": [T0 + pd.Timedelta(hours=100), T0 + pd.Timedelta(hours=60)],
                      "r": [2.0, -1.0]})
    for mod in ("yay", "cikis"):
        assert abs(S.gunluk_getiri(d, mod).sum() - 0.01) < 1e-12


def _seri(v, n=400):
    return pd.Series(v, index=pd.date_range(T0.floor("D"), periods=n, freq="D"))


def test_korelasyon_ozdes_bagimsiz_ve_yetersiz_ortak():
    rng = np.random.default_rng(1)
    a = _seri(rng.normal(size=400))
    b = _seri(rng.normal(size=400))
    ar = (a.index[0], a.index[-1])
    assert abs(S.korelasyon_cifti(a, a, ar, ar)[0] - 1) < 1e-9
    assert abs(S.korelasyon_cifti(a, b, ar, ar)[0]) < 0.2
    assert abs(S.korelasyon_cifti(a, -a, ar, ar)[0] + 1) < 1e-9
    kisa = (a.index[0], a.index[100])
    assert np.isnan(S.korelasyon_cifti(a, b, ar, kisa)[0])      # ortak gün < MIN_ORTAK_GUN


def test_yonlu_ortusme():
    def tbl(sat):
        return pd.DataFrame({"giris_zamani": [T0 + pd.Timedelta(hours=a) for a, _, _ in sat],
                             "cikis_zamani": [T0 + pd.Timedelta(hours=b) for _, b, _ in sat],
                             "yon": [y for _, _, y in sat]})
    a = S.pozisyon_aralari(tbl([(0, 10, 1)]), "X")
    assert abs(S.yonlu_ortusme(a, S.pozisyon_aralari(tbl([(5, 15, 1)]), "X")) - 0.5) < 1e-9
    assert S.yonlu_ortusme(a, S.pozisyon_aralari(tbl([(5, 15, -1)]), "X")) == 0.0      # zıt yön
    assert S.yonlu_ortusme(a, S.pozisyon_aralari(tbl([(0, 10, 1)]), "Y")) == 0.0       # başka sembol


def _kor(n, tohum):
    rng = np.random.default_rng(tohum)
    x = rng.normal(size=(n, 60))
    x[1] = x[0] + 0.3 * rng.normal(size=60)           # 0 ve 1 yüksek korelasyonlu
    k = np.corrcoef(x)
    ids = [f"c{i}" for i in range(n)]
    return pd.DataFrame(k, index=ids, columns=ids), ids


def test_acgozlu_secim_esigi_korur():
    for tohum in range(10):
        kor, ids = _kor(20, tohum)
        s = S.acgozlu_sec(ids, kor, None, n_secim=3, n_yedek=5, esik_korr=0.5)
        kabul = s["secim"] + s["yedek"]
        assert kabul[0] == ids[0]
        for i, a in enumerate(kabul):
            for b in kabul[:i]:
                assert kor.loc[a, b] <= 0.5
        assert len(s["secim"]) <= 3 and len(s["yedek"]) <= 5
    kor, ids = _kor(20, 0)
    s = S.acgozlu_sec(ids, kor, None)
    assert "c1" not in s["secim"] + s["yedek"] and "c1" in s["elenen"]


def test_acgozlu_ortusme_esigi():
    ids = ["a", "b", "c"]
    kor = pd.DataFrame(np.eye(3), index=ids, columns=ids)
    ort = pd.DataFrame(np.eye(3), index=ids, columns=ids)
    ort.loc["a", "b"] = ort.loc["b", "a"] = 0.9
    s = S.acgozlu_sec(ids, kor, ort, esik_ortusme=0.3)
    assert s["secim"] == ["a", "c"] and "b" in s["elenen"]


def test_kumeler():
    ids = list("abcd")
    k = np.eye(4)
    k[0, 1] = k[1, 0] = 0.9
    k[2, 3] = k[3, 2] = 0.8
    kume = S.kumeler(pd.DataFrame(k, index=ids, columns=ids))
    assert kume["a"] == kume["b"] and kume["c"] == kume["d"] and kume["a"] != kume["c"]


def test_b04_sifir_sureli_islem_hayalet_pozisyon_birakmaz():
    # B04: giris == cikis (stop_gap ile giriş mumunda kapanan işlem). Eskiden çıkış kendi girişinden önce işlenir, pozisyon
    # hiç kapanmaz ve risk/kaldıraç bütçesini sonsuza dek tutardı; sonraki girişler red_kaldirac ile reddedilirdi.
    satirlar = [(2, 2, -17.0, 0.05, 1, "X")] + [(30 + 24 * i, 40 + 24 * i, 1.0, 0.05, 1, "Y") for i in range(10)]
    s = S.yeniden_oyna(_t(satirlar))
    assert s["sayac"]["reddedilen"] == 0 and s["sayac"]["giris_kabul"] == 11
    assert s["sayac"]["red_kaldirac"] == 0
    beklenen = (1 - 0.17) * 1.01 ** 10
    assert abs(s["nakit_son"] - beklenen) < 1e-9
    assert 0 in s["islem_pnl"]


def test_b04_ayni_zamanli_diger_cikis_giristen_once_kalir():
    # başka işlemin aynı zaman damgasındaki çıkışı hâlâ girişten ÖNCE işlenir (bütçe serbest kalır)
    s = S.yeniden_oyna(_t([(1, 10, 0.0, 0.05)] * 5 + [(10, 20, 0.0, 0.05)]))
    assert s["sayac"]["giris_kabul"] == 6 and s["sayac"]["reddedilen"] == 0
