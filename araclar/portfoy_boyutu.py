"""Test A — "Kaç strateji ideal?" (KEŞİF; ON_KAYIT.md'nin birebir uygulaması).

meta_test_secim.py'nin veri yükleme, kesim ve kapı (G1-G3) fonksiyonlarını IMPORT eder; mantığı kopyalamaz.
Aynı 11 kesim, 6 aylık ölçüm penceresi, yalnız < 2025-11-08 veri. Tohum 20261111. Tek koşu.
Kullanım: python araclar/portfoy_boyutu.py   (çıktı: sonuclar/evren/portfoy_boyutu/)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_KOK = Path(__file__).resolve().parents[1]
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

from araclar import meta_test_secim as mts  # noqa: E402

KOK = mts.KOK
CIKTI = KOK / "sonuclar" / "evren" / "portfoy_boyutu"

# ============================================================================ ön kayıtlı sabitler
TOHUM = 20261111
N_LISTESI = (1, 2, 3, 4, 6, 8, 10)
CEKILIS = 2000
KASA = 250.0
ISLEM_RISK = 0.015          # günlük R toplamı × 0.015 = kasanın günlük getiri oranı
STRATEJI_KILL = 0.30        # strateji kasası kendi zirvesinden -%30 -> o strateji durur
HESAP_KILL = 0.20           # toplam kasa kendi zirvesinden -%20 -> hepsi durur
DOYMA_PUAN = 1.0            # doyma: sonraki N adımında ort. max düşüş iyileşmesi < 1 puan
YUZDELIKLER = (5, 50, 95)
BUYUK = 10 ** 9             # "kill olmadı" işareti (gün indeksi)
EPS = 1e-12


# ============================================================================ para hesabı
def strateji_kasa_yollari(R: np.ndarray, kasa: float = KASA, risk: float = ISLEM_RISK,
                          esik: float = STRATEJI_KILL) -> tuple:
    """R: (G, T) günlük R (x2). Her satır AYRI kasa. v_t = v_{t-1}·(1 + risk·R_t). Kasa kendi zirvesinden -esik'e inerse
    (v <= (1-esik)·zirve) o gün sonunda durur, kalan günlerde değeri sabit. Dönüş: V (G, T+1) [ilk sütun = kasa], kill_gun (G,)
    (kill günü = 1..T, kill yoksa BUYUK)."""
    R = np.asarray(R, dtype=float)
    G, T = R.shape
    v = np.full(G, kasa, dtype=float)
    zirve = v.copy()
    canli = np.ones(G, dtype=bool)
    kd = np.full(G, BUYUK, dtype=np.int64)
    V = np.empty((G, T + 1))
    V[:, 0] = v
    for t in range(T):
        v = np.where(canli, v * (1.0 + risk * R[:, t]), v)
        zirve = np.maximum(zirve, v)
        yeni = canli & (v <= (1.0 - esik) * zirve + EPS)
        kd = np.where(yeni, t + 1, kd)
        canli = canli & ~yeni
        V[:, t + 1] = v
    return V, kd


def hesap_kill_uygula(toplam: np.ndarray, esik: float = HESAP_KILL) -> tuple:
    """toplam: (D, T+1) kasa toplamları. Toplam kendi zirvesinden -esik'e inerse (<= (1-esik)·zirve) hepsi durur: o günden
    sonra toplam sabit. Dönüş: dondurulmus (D, T+1), hesap_kill_gun (D,) (yoksa BUYUK)."""
    toplam = np.asarray(toplam, dtype=float)
    D, T1 = toplam.shape
    zirve = np.maximum.accumulate(toplam, axis=1)
    kosul = toplam <= (1.0 - esik) * zirve + EPS
    var = kosul.any(axis=1)
    ilk = np.where(var, kosul.argmax(axis=1), BUYUK)
    t = np.arange(T1)[None, :]
    idx = np.minimum(t, np.where(var, ilk, T1 - 1)[:, None])
    return np.take_along_axis(toplam, idx, axis=1), ilk.astype(np.int64)


def max_dusus_yuzde(seri: np.ndarray) -> np.ndarray:
    """(D, T+1) -> (D,) zirveden en büyük düşüş, % (pozitif sayı)."""
    zirve = np.maximum.accumulate(seri, axis=1)
    return 100.0 * (1.0 - seri / zirve).max(axis=1)


def ort_korelasyon(C: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """C: (G, G) korelasyon (tanımsız = NaN). idx: (D, N) seçili satırlar. Her çekiliş için çiftlerin ortalaması (köşegen hariç,
    NaN çiftler atlanır). N=1 -> NaN."""
    D, N = idx.shape
    if N < 2:
        return np.full(D, np.nan)
    sub = C[idx[:, :, None], idx[:, None, :]].copy()
    ii = np.arange(N)
    sub[:, ii, ii] = np.nan
    gecerli = ~np.isnan(sub)
    n = gecerli.sum(axis=(1, 2))
    s = np.where(gecerli, sub, 0.0).sum(axis=(1, 2))
    return np.where(n > 0, s / np.maximum(n, 1), np.nan)


def portfoy_olc(V: np.ndarray, kd: np.ndarray, C: np.ndarray, idx: np.ndarray) -> dict:
    """idx: (D, N) strateji satırları. V: (G, T+1) kasa yolları, kd: strateji kill günleri. Dönüş: D'lik diziler."""
    toplam = V[idx].sum(axis=1)                          # (D, T+1)
    don, ka = hesap_kill_uygula(toplam)
    getiri = 100.0 * (don[:, -1] / don[:, 0] - 1.0)
    dd = max_dusus_yuzde(don)
    kdi = kd[idx]
    en_az_bir = ((kdi < BUYUK) & (kdi <= ka[:, None])).any(axis=1)     # hesap durduktan SONRAKİ strateji kill'leri sayılmaz
    return {"getiri": getiri, "dd": dd, "hesap_kill": (ka < BUYUK).astype(float), "strateji_kill": en_az_bir.astype(float),
            "korelasyon": ort_korelasyon(C, idx)}


def korelasyon_matrisi(R: np.ndarray) -> np.ndarray:
    """Günlük R serileri arasında Pearson; sd=0 olan satır -> NaN."""
    R = np.asarray(R, dtype=float)
    sd = R.std(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (R - R.mean(axis=1, keepdims=True)) / sd[:, None]
        C = z @ z.T / R.shape[1]
    C[sd == 0, :] = np.nan
    C[:, sd == 0] = np.nan
    return C


# ============================================================================ kesim verisi
def kesim_gecenler(havuz: list, T: pd.Timestamp) -> list:
    """T'de kapıyı (G1-G3) geçenler, puana göre azalan (eşitte kimlik sırası). [(SData, puan), ...]"""
    out = []
    for sd in havuz:
        g = mts.geriye_bakis(sd, T)
        if g["uygun"] and g["gecti"]:
            out.append((sd, g["puan"]))
    out.sort(key=lambda x: (-x[1], x[0].kimlik))
    return out


def pencere_R(sd: "mts.SData", T: pd.Timestamp, son: pd.Timestamp) -> np.ndarray:
    return sd.gunluk[mts._gun_ofset(T):mts._gun_ofset(son)]


# ============================================================================ ana hesap
def kesim_kos(gecen: list, T: pd.Timestamp, son: pd.Timestamp, rng: np.random.Generator,
              n_listesi=N_LISTESI, cekilis: int = CEKILIS) -> list:
    """Bir kesim için tüm N ve iki tür. Dönüş: satır sözlükleri. Kapı geçen < N ise o N atlanır (satır yok)."""
    G = len(gecen)
    if G == 0:
        return []
    R = np.vstack([pencere_R(sd, T, son) for sd, _ in gecen])
    V, kd = strateji_kasa_yollari(R)
    C = korelasyon_matrisi(R)
    satirlar = []
    for N in n_listesi:
        if G < N:
            continue
        ust = portfoy_olc(V, kd, C, np.arange(N)[None, :])
        satirlar.append({"tur": "ust", "N": N, "kesim": str(T.date()), "n_gecen": G, "n_cekilis": 1,
                         "getiri": ust["getiri"][0], "dd": ust["dd"][0], "hesap_kill": ust["hesap_kill"][0],
                         "strateji_kill": ust["strateji_kill"][0], "korelasyon": ust["korelasyon"][0],
                         **{f"getiri_p{q}": ust["getiri"][0] for q in YUZDELIKLER},
                         **{f"dd_p{q}": ust["dd"][0] for q in YUZDELIKLER}, "dd_maks_cekilis": ust["dd"][0]})
        idx = np.argsort(rng.random((cekilis, G)), axis=1)[:, :N]
        ras = portfoy_olc(V, kd, C, idx)
        kor = ras["korelasyon"]
        satirlar.append({"tur": "rastgele", "N": N, "kesim": str(T.date()), "n_gecen": G, "n_cekilis": cekilis,
                         "getiri": float(ras["getiri"].mean()), "dd": float(ras["dd"].mean()),
                         "hesap_kill": float(ras["hesap_kill"].mean()), "strateji_kill": float(ras["strateji_kill"].mean()),
                         "korelasyon": float(np.nanmean(kor)) if np.isfinite(kor).any() else math.nan,
                         **{f"getiri_p{q}": float(np.percentile(ras["getiri"], q)) for q in YUZDELIKLER},
                         **{f"dd_p{q}": float(np.percentile(ras["dd"], q)) for q in YUZDELIKLER},
                         "dd_maks_cekilis": float(ras["dd"].max())})
    return satirlar


def toplulastir(sonuc: pd.DataFrame, n_kesim: int, n_listesi=N_LISTESI) -> pd.DataFrame:
    """N ve tür başına kesimler üzerinden özet."""
    rows = []
    for tur in ("ust", "rastgele"):
        for N in n_listesi:
            d = sonuc[(sonuc["tur"] == tur) & (sonuc["N"] == N)]
            if d.empty:
                continue
            g = d["getiri"].to_numpy()
            rows.append({"tur": tur, "N": N, "n_kesim": len(d), "n_kesim_atlanan": n_kesim - len(d),
                         "ort_getiri": g.mean(), "medyan_getiri": float(np.median(g)),
                         "sd_getiri": float(g.std(ddof=1)) if len(g) > 1 else math.nan,
                         "ort_dd": d["dd"].mean(), "en_kotu_dd": d["dd"].max(),
                         "p_hesap_kill": d["hesap_kill"].mean(), "p_strateji_kill": d["strateji_kill"].mean(),
                         "ort_korelasyon": float(d["korelasyon"].mean()) if d["korelasyon"].notna().any() else math.nan,
                         **{f"getiri_p{q}": d[f"getiri_p{q}"].mean() for q in YUZDELIKLER},
                         **{f"dd_p{q}": d[f"dd_p{q}"].mean() for q in YUZDELIKLER},
                         "dd_maks_cekilis": d["dd_maks_cekilis"].max()})
    return pd.DataFrame(rows)


def doyma_noktasi(tablo: pd.DataFrame, tur: str, n_listesi=N_LISTESI, esik: float = DOYMA_PUAN):
    """Ön kayıtlı yorum: ort. max düşüşteki iyileşmenin bir sonraki N adımında < esik puan kaldığı en küçük N.
    Hiçbiri yoksa None."""
    dd = {int(r.N): r.ort_dd for r in tablo[tablo["tur"] == tur].itertuples()}
    for a, b in zip(n_listesi, n_listesi[1:]):
        if a in dd and b in dd and (dd[a] - dd[b]) < esik:
            return a
    return None


# ============================================================================ çıktı
def _f(x, n=2):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def rapor_yaz(yol: Path, tablo: pd.DataFrame, oz: dict, kesim_ozet: pd.DataFrame) -> None:
    L = ["# Test A — Kaç strateji ideal? (keşif)", "",
         "Her kesimde kapıyı (G1–G3) geçenlerden N tanesi alınıp 6 ay boyunca para hesabıyla yürütüldü. "
         "\"üst-N\" = puana göre ilk N; \"rastgele-N\" = kapı geçenlerden 2000 rastgele N'li çekiliş (kesim içi ortalaması). "
         "Her strateji 250 USD ayrı kasa, işlem başı %1,5 risk, kasa zirveden −%30'a inerse o strateji durur, "
         "toplam kasa zirveden −%20'ye inerse hepsi durur.", "",
         f"Doyma noktası (ön kayıtlı yorum; ort. max düşüşte sonraki adımda < 1 puan iyileşme): "
         f"üst-N: **{oz['doyma_ust']}**, rastgele-N: **{oz['doyma_rastgele']}** (None = 10'a kadar doymadı). "
         "Tek başına karar değildir.", ""]
    for tur, ad in (("ust", "üst-N (puana göre ilk N)"), ("rastgele", "rastgele-N (kesim içi ortalama)")):
        L += [f"## {ad}", "",
              "| N | kesim | ort getiri % | medyan % | sd (kesimler) | ort maks düşüş % | en kötü maks düşüş % | hesap kill | "
              "en az 1 strateji kill | ort korelasyon |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in tablo[tablo["tur"] == tur].itertuples():
            L.append(f"| {r.N} | {r.n_kesim}/{r.n_kesim + r.n_kesim_atlanan} | {_f(r.ort_getiri)} | {_f(r.medyan_getiri)} | "
                     f"{_f(r.sd_getiri)} | {_f(r.ort_dd)} | {_f(r.en_kotu_dd)} | {_f(r.p_hesap_kill, 3)} | "
                     f"{_f(r.p_strateji_kill, 3)} | {_f(r.ort_korelasyon, 3)} |")
        L.append("")
    L += ["## Rastgele-N: kesim içi dağılım (kesimler üzerinden ortalaması alınmış yüzdelikler)", "",
          "| N | getiri % p5 | p50 | p95 | maks düşüş % p5 | p50 | p95 | tek çekilişte en kötü düşüş % |",
          "|---|---|---|---|---|---|---|---|"]
    for r in tablo[tablo["tur"] == "rastgele"].itertuples():
        L.append(f"| {r.N} | {_f(r.getiri_p5)} | {_f(r.getiri_p50)} | {_f(r.getiri_p95)} | {_f(r.dd_p5)} | {_f(r.dd_p50)} | "
                 f"{_f(r.dd_p95)} | {_f(r.dd_maks_cekilis)} |")
    L += ["", "## Kesim başına kapıyı geçen sayısı", "", "| kesim | kapı geçen |", "|---|---|"]
    for r in kesim_ozet.itertuples():
        L.append(f"| {r.kesim} | {r.n_gecen} |")
    L += ["", "## Uyarılar ve sınırlar", "",
          "- Keşif testidir; sonuç sonrası tasarlandı (meta-testin ardından). Sonuç kilitli canlı planı değiştirmez.",
          "- Yalnız 11 pencere: güç düşük, kesimler arası sd büyük; N'ler arası küçük farklar gürültüdür.",
          "- Kaldıraç ve marj sınırı MODELLENMEDİ: gerçekte çok sayıda eşzamanlı pozisyon marj/kaldıraç tavanına çarpabilir.",
          "- Günlük R toplamı kasa oranıyla çarpıldı (bileşik); gün içi tepe/dip görülmez, kill kontrolü gün sonunda.",
          "- Kapı geçen sayısı N'den az olan kesimler o N için atlandı (tablodaki 'kesim' sütunu); farklı N'lerin kesim "
          "kümesi farklı olabilir, N'ler arası karşılaştırmayı bozar.",
          "- Rastgele-N, kapı geçenlerin tamamı yerine rastgele alt kümedir; üst-N puan sırasına güvenir (meta-test: sıralama "
          "sınırlı bilgi taşıyor, p 0,046).",
          f"- Kullanılan en büyük tarih: {oz['maks_tarih']} (< 2025-11-08 doğrulandı). Betik sha256: {oz['girdi_hash']['betik']}; "
          f"commit: {oz['commit']}."]
    yol.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    CIKTI.mkdir(parents=True, exist_ok=True)
    havuz, eleme, bilgi = mts.v2_havuz_yukle()
    rng = np.random.default_rng(TOHUM)
    kesimler = mts.kesimleri_uret()
    assert len(kesimler) == 11 and str(kesimler[0].date()) == "2020-05-08" and str(kesimler[-1].date()) == "2025-05-08"
    satirlar, kes_ozet = [], []
    for T in kesimler:
        son = mts.pencere_sonu(T)
        gecen = kesim_gecenler(havuz, T)
        kes_ozet.append({"kesim": str(T.date()), "n_gecen": len(gecen)})
        satirlar += kesim_kos(gecen, T, son, rng)
    sonuc = pd.DataFrame(satirlar)
    tablo = toplulastir(sonuc, len(kesimler))
    kes_df = pd.DataFrame(kes_ozet)
    maks = mts.maks_tarih_dogrula()
    oz = {"n_listesi": list(N_LISTESI), "cekilis": CEKILIS, "tohum": TOHUM, "kesim_gecen": kes_ozet,
          "doyma_ust": doyma_noktasi(tablo, "ust"), "doyma_rastgele": doyma_noktasi(tablo, "rastgele"),
          "tablo": json.loads(tablo.to_json(orient="records")), "maks_tarih": str(maks),
          "girdi_hash": {"betik": mts._sha(Path(__file__)), "eleme_csv": mts._sha(mts.veri_kok() / "eleme.csv"),
                         "on_kayit": mts._sha(CIKTI / "ON_KAYIT.md"), "v2_dosyalar": bilgi["dosya_hash_ozeti"]},
          "commit": mts._git("rev-parse", "HEAD"), "veri": {k: v for k, v in bilgi.items() if k != "dosyasiz_satirlar"}}
    sonuc.to_csv(CIKTI / "sonuc.csv", index=False)
    tablo.to_csv(CIKTI / "ozet_tablo.csv", index=False)
    kes_df.to_csv(CIKTI / "kesim_gecen.csv", index=False)
    (CIKTI / "ozet.json").write_text(json.dumps(mts._sade(oz), ensure_ascii=False, indent=2), encoding="utf-8")
    rapor_yaz(CIKTI / "rapor.md", tablo, oz, kes_df)
    print(tablo.round(2).to_string())
    print("doyma", oz["doyma_ust"], oz["doyma_rastgele"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
