"""Test B — Meta-test sağlamlık (KEŞİF; ON_KAYIT.md'nin birebir uygulaması).

meta_test_secim.py'nin veri yükleme, kesim, G1-G3 kapıları, puan, P_i,k, D_k ve işaret çevirme fonksiyonlarını IMPORT eder.
Üç koşu: B1 "bilinen büyükler", B2 "kazananları çıkar" (yalnız ölçüm penceresinden), B3 "yalnız short".
Yalnız < 2025-11-08 veri. Tek koşu. Kullanım: python araclar/meta_test_saglamlik.py  (çıktı: sonuclar/evren/meta_test_saglamlik/)
"""
from __future__ import annotations

import contextlib
import dataclasses
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
CIKTI = KOK / "sonuclar" / "evren" / "meta_test_saglamlik"
HOLDOUT = mts.HOLDOUT_BAS

# ============================================================================ ön kayıtlı sabitler
B1_LISTE = ("BTCUSDT", "ETHUSDT", "DK_XAU", "DK_XAG", "DK_WTI", "DK_COPPER", "DK_NATGAS", "DK_AAPL", "DK_MSFT", "DK_AMZN",
            "DK_GOOGL", "DK_JPM", "DK_JNJ", "DK_V", "DK_MA", "DK_WMT", "DK_XOM")
B2_ADET = 5
SHORT = -1
LONG = 1
MUM_KOK_ADAYLARI = (KOK / "veri" / "mumlar", Path("/home/user/1L3A-Proje/veri/mumlar"))


# ============================================================================ yükleme (meta_test_secim._strateji_yukle yeniden kullanılır)
def idx_kur(kok: Path, sembol_filtre=None) -> dict:
    """mtm/ham dosya dizini. sembol_filtre (küme) verilirse yalnız o enstrüman dosyaları."""
    idx = {"ham2": {}, "mtm2": {}, "ham1": {}}
    for anahtar, alt in (("ham2", "ham/x2"), ("mtm2", "mtm/x2"), ("ham1", "ham/x1")):
        for p in sorted((kok / alt).glob("*.parquet")):
            ad, tf, sembol = p.stem.split("--", 2)
            if sembol_filtre is not None and sembol not in sembol_filtre:
                continue
            idx[anahtar].setdefault(f"{ad}--{tf}--", []).append(p)
    return idx


@contextlib.contextmanager
def yon_suzgeci(yon):
    """Yükleme süresince mts._ham_suz'u sarar: holdout süzgeci AYNEN uygulanır, sonra yalnız `yon` işlemleri kalır
    (islem_no özgün sırayla kalır; mtm artışları zaten ham'daki işlem kümesine bağlıdır). yon None -> değişiklik yok."""
    orijinal = mts._ham_suz
    if yon is None:
        yield
        return

    def sarmal(h, bilgi):
        out = orijinal(h, bilgi)
        assert set(np.unique(out["yon"].to_numpy())) <= {LONG, SHORT}, "beklenmeyen yon değeri"
        return out[out["yon"].to_numpy() == yon]
    mts._ham_suz = sarmal
    try:
        yield
    finally:
        mts._ham_suz = orijinal


def havuz_yukle(kok: Path, eleme: pd.DataFrame, sembol_filtre=None, yon=None) -> tuple:
    """v2_havuz_yukle ile aynı döngü; yalnız dosya kümesi enstrümana göre ve işlemler yöne göre süzülebilir."""
    idx = idx_kur(kok, sembol_filtre)
    bilgi = {"atilan_islem": 0, "atilan_mtm_satiri": 0, "kum_r_kontrol_islem": 0, "kum_r_max_fark": 0.0,
             "fonlama_sifir_degil": 0, "fonlama_r_ayrica_eklenirse_uyumsuz": 0, "veri_kok": str(kok)}
    hashler, havuz, dosyasiz = [], [], []
    eleme_h = eleme[eleme["durum"] != "hata"]
    with yon_suzgeci(yon):
        for _, r in eleme_h.iterrows():
            ons = f"{r['strateji']}--{r['tf']}--"
            if not (idx["ham2"].get(ons) and idx["mtm2"].get(ons) and idx["ham1"].get(ons)):
                dosyasiz.append(f"{r['strateji']}|{r['tf']}")
                continue
            havuz.append(mts._strateji_yukle(r["strateji"], r["tf"], r["etiket"], pd.Timestamp(r["analiz_bas"]), kok, idx,
                                             bilgi, hashler))
    bilgi.update({"havuz_n": len(havuz), "dosyasiz_satir_n": len(dosyasiz), "okunan_dosya_n": len(hashler)})
    return havuz, bilgi


def mevcut_semboller(kok: Path) -> set:
    """MTM dosyası olan (yani havuza girebilen) enstrümanlar; portföy satırları (_PORTFOY) mtm'siz olduğundan dışarıda."""
    return {p.stem.split("--", 2)[2] for p in (kok / "mtm" / "x2").glob("*.parquet")}


# ============================================================================ B2: kazananlar
def gunluk_kapanis(df: pd.DataFrame) -> pd.Series:
    """Mum tablosu (UTC indeksli, 'kapanis') -> UTC günün son kapanışı. Yalnız < HOLDOUT barlar kullanılır."""
    d = df[df.index < HOLDOUT]
    assert len(d), "mum verisi boş"
    mts._gor(d.index.max())
    s = d["kapanis"].groupby(d.index.tz_convert("UTC").normalize()).last()
    return s.dropna()


def mum_oku(sembol: str) -> pd.Series:
    for kok in MUM_KOK_ADAYLARI:
        for tf in ("1d", "1h", "5m"):
            p = kok / sembol / f"{tf}.parquet"
            if p.exists():
                return gunluk_kapanis(pd.read_parquet(p, columns=["kapanis"]))
    raise mts.DogrulamaHatasi(f"mum verisi yok: {sembol}")


def al_tut(seri: pd.Series, T: pd.Timestamp, son: pd.Timestamp, tolerans_gun: int = 10):
    """Pencere başı = T'den önceki son günlük kapanış, sonu = son'dan önceki son günlük kapanış. Başlangıçta veri yoksa
    (veri T-tolerans'tan eski/yok) ya da son kapanış pencere sonunu çok erken bırakıyorsa None."""
    a = seri[seri.index < T]
    b = seri[seri.index < son]
    if not len(a) or not len(b):
        return None
    if (T - a.index[-1]).days > tolerans_gun or (son - b.index[-1]).days > tolerans_gun:
        return None
    if b.index[-1] <= a.index[-1]:
        return None
    return float(b.iloc[-1] / a.iloc[-1] - 1.0)


def kazananlar(seriler: dict, T: pd.Timestamp, son: pd.Timestamp, adet: int = B2_ADET) -> list:
    """[(sembol, getiri)] pencerede al-tut getirisi en yüksek `adet` enstrüman (eşitte ad sırası)."""
    g = []
    for s, ser in seriler.items():
        r = al_tut(ser, T, son)
        if r is not None:
            g.append((s, r))
    g.sort(key=lambda x: (-x[1], x[0]))
    return g[:adet]


def pencereden_cikar(havuz: list, ins_gunluk: dict, T: pd.Timestamp, son: pd.Timestamp, cikar: list) -> list:
    """Her stratejinin günlük serisinden, YALNIZ [T, son) penceresinde, `cikar` enstrümanlarının katkısını siler. Geriye
    bakış kısmı ve işlem listeleri (kapılar) değişmez. ins_gunluk[sembol][kimlik] = o enstrümanın günlük serisi."""
    o1, o2 = mts._gun_ofset(T), mts._gun_ofset(son)
    out = []
    for sd in havuz:
        arr = sd.gunluk.copy()
        for s in cikar:
            a = ins_gunluk.get(s, {}).get(sd.kimlik)
            if a is not None:
                arr[o1:o2] -= a[o1:o2]
        w = arr[o1:o2]
        w[np.abs(w) < 1e-9] = 0.0                      # kayan nokta artığı "işlem yok" sayılsın
        out.append(dataclasses.replace(sd, gunluk=arr))
    return out


# ============================================================================ ortak istatistik
def d_istatistik(d: list) -> dict:
    s = mts.isaret_cevirme(d)
    ga = mts.guven_araligi_90(d) if len(d) >= 2 else (math.nan, math.nan)
    return {"n": s["n"], "dbar": s["dbar"], "p_yukari": s["p_yukari"], "p_asagi": s["p_asagi"], "ga90": ga,
            "pozitif_pencere": int(sum(x > 0 for x in d))}


def bir_pencere_kos(havuz: list, T: pd.Timestamp) -> dict:
    res = mts.sema_kos(havuz, [T])
    return res["pencereler"][0]


# ============================================================================ B3: long payı
def yon_tablosu(kok: Path, eleme: pd.DataFrame) -> dict:
    """kimlik -> (giris_ns, cikis_ns, yon): x2 ham işlemleri, girişi analiz başlangıcından sonra, holdout süzülmüş."""
    out = {}
    idx = idx_kur(kok)
    bilgi = {"atilan_islem": 0}
    for _, r in eleme[eleme["durum"] != "hata"].iterrows():
        ons = f"{r['strateji']}--{r['tf']}--"
        dosyalar = idx["ham2"].get(ons, [])
        if not dosyalar:
            continue
        bas = pd.Timestamp(r["analiz_bas"])
        g, c, y = [], [], []
        for p in dosyalar:
            h = mts._ham_suz(pd.read_parquet(p), bilgi)
            h = h[pd.DatetimeIndex(h["giris_zamani"]) >= bas]
            g.append(mts._ns(h["giris_zamani"]))
            c.append(mts._ns(h["cikis_zamani"]))
            y.append(h["yon"].to_numpy(dtype=np.int64))
        out[f"{r['strateji']}|{r['tf']}"] = (np.concatenate(g), np.concatenate(c), np.concatenate(y))
    return out


def long_payi(tablo: dict, kimlikler, T: pd.Timestamp, son: pd.Timestamp) -> dict:
    """Seçili stratejilerde havuzlanmış long işlem payı: geriye bakış (çıkış < T) ve ölçüm (giriş [T, son))."""
    Tn, Sn = mts._ts_ns(T), mts._ts_ns(son)
    lb_l = lb_n = ol_l = ol_n = 0
    for k in kimlikler:
        g, c, y = tablo[k]
        m = c < Tn
        lb_n += int(m.sum())
        lb_l += int((y[m] == LONG).sum())
        m = (g >= Tn) & (g < Sn)
        ol_n += int(m.sum())
        ol_l += int((y[m] == LONG).sum())
    return {"lb_n": lb_n, "lb_long_payi": lb_l / lb_n if lb_n else math.nan, "ol_n": ol_n,
            "ol_long_payi": ol_l / ol_n if ol_n else math.nan}


# ============================================================================ çıktı
def _f(x, n=2):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def rapor_yaz(yol: Path, oz: dict, long_df: pd.DataFrame, kos_df: pd.DataFrame) -> None:
    L = ["# Test B — Meta-test sağlamlık (keşif)", "",
         "Ana ölçü ve test meta-testle aynı: D̄ = 11 pencerede (S_k − N1) yüzdelik puan farkının ortalaması, işaret çevirme (2048), "
         "tek yönlü p. Üç ayrı koşu; eşik/p kararı yok.", "",
         f"Kontrol: tam veriyle D̄ yeniden hesaplandı = {_f(oz['taban']['dbar'])} (meta-test: {_f(oz['taban']['meta_dbar'])}).", "",
         "| koşul | pencere | D̄ | p_yukarı | p_aşağı | %90 GA | D_k > 0 |", "|---|---|---|---|---|---|---|"]
    for ad in ("B1", "B2", "B3"):
        r = oz[ad]
        L.append(f"| {ad} {r['ad']} | {r['n']} | **{_f(r['dbar'])}** | {_f(r['p_yukari'], 4)} | {_f(r['p_asagi'], 4)} | "
                 f"[{_f(r['ga90'][0])} ; {_f(r['ga90'][1])}] | {r['pozitif_pencere']}/{r['n']} |")
    L += ["", f"**Önceden yazılan yorum uygulaması:** {oz['yorum']}", "", "## Pencere başına D_k", "",
          "| kesim | tam veri | B1 | B2 | B3 |", "|---|---|---|---|---|"]
    for r in kos_df.itertuples():
        L.append(f"| {r.kesim} | {_f(r.D_tam)} | {_f(r.D_B1)} | {_f(r.D_B2)} | {_f(r.D_B3)} |")
    L += ["", "## Kesim başına kapı geçen / uygun sayıları", "", "| kesim | B1 geçen/uygun | B2 geçen/uygun | B3 geçen/uygun |",
          "|---|---|---|---|"]
    for r in kos_df.itertuples():
        L.append(f"| {r.kesim} | {r.gecen_B1}/{r.uygun_B1} | {r.gecen_B2}/{r.uygun_B2} | {r.gecen_B3}/{r.uygun_B3} |")
    L += ["", "## B2: her pencerenin al-tut kazananları (ölçüm penceresinden çıkarılanlar)", "",
          "| kesim | kazananlar (getiri %) |", "|---|---|"]
    for k, v in oz["B2_kazananlar"].items():
        L.append(f"| {k} | " + ", ".join(f"{s} ({100 * g:.0f})" for s, g in v) + " |")
    L += ["", "## B3: long işlem payı (S_k vs N1; tam veri, havuzlanmış işlem sayısıyla)", "",
          "| kesim | S_k long payı (geriye bakış) | N1 (geriye bakış) | S_k (ölçüm) | N1 (ölçüm) |", "|---|---|---|---|---|"]
    for r in long_df.itertuples():
        L.append(f"| {r.kesim} | {_f(r.S_lb, 3)} | {_f(r.N1_lb, 3)} | {_f(r.S_ol, 3)} | {_f(r.N1_ol, 3)} |")
    L += ["", f"Ortalama long payı — S_k: {_f(long_df['S_lb'].mean(), 3)} (geriye bakış), {_f(long_df['S_ol'].mean(), 3)} (ölçüm); "
          f"N1: {_f(long_df['N1_lb'].mean(), 3)} (geriye bakış), {_f(long_df['N1_ol'].mean(), 3)} (ölçüm).", "",
          "## B1 enstrüman eşleşmesi", "",
          f"Listedeki {len(B1_LISTE)} enstrümandan mtm dosyalarında bulunan: {len(oz['b1_bulunan'])}. "
          f"Bulunmayan: {', '.join(oz['b1_bulunmayan']) or 'yok'} (liste değiştirilmedi).", "",
          "## Uyarılar ve sınırlar", "",
          "- Keşif testi; sonuç sonrası tasarlandı (meta-testin ardından). Sonuç kilitli canlı planı değiştirmez.",
          "- Yalnız 11 pencere: güç düşük. Süzülmüş verilerde (B1, B3) kapıyı geçen sayısı küçülür; S_k çoğu kesimde N1'den "
          "tamamlanabilir (bkz. kapı geçen sayıları) — bu D̄'yi gürültülü yapar.",
          "- Evren 2026'da seçildi; kapılar geliştirme verisi görüldükten sonra tasarlandı (meta-testteki yanlılıklar geçerli).",
          "- B2: çıkarma yalnız ölçüm penceresinde ve günlük R serisinde yapıldı; geriye bakış ve seçim aynı. Pencere başı = T'den "
          "önceki son günlük kapanış, sonu = pencere sonundan önceki son günlük kapanış.",
          f"- Kullanılan en büyük tarih: {oz['maks_tarih']} (< 2025-11-08 doğrulandı). Betik sha256: {oz['girdi_hash']['betik']}; "
          f"commit: {oz['commit']}."]
    yol.write_text("\n".join(L) + "\n", encoding="utf-8")


def yorum_metni(oz: dict) -> str:
    pos = {ad: oz[ad]["dbar"] > 0 for ad in ("B1", "B2", "B3")}
    if all(pos.values()):
        return "Üçünde de D̄ > 0: evren/long şüphesi büyük ölçüde zayıflar."
    aciklama = {"B1": "seçim üstünlüğü bilinen büyük enstrümanlarda görünmüyor: sonuç evrendeki küçük/az bilinen enstrümanlara "
                      "(evren/örnek seçimi etkisine) bağlı olabilir",
                "B2": "üstünlük pencerenin en çok yükselen birkaç enstrümanına bağlı: birkaç büyük kazanana yaslanıyor olabilir",
                "B3": "üstünlük long yönünden geliyor: yükselen piyasa/long yanlılığı açıklaması destek buluyor"}
    kotu = [ad for ad, v in pos.items() if not v]
    return "D̄ ≤ 0 olan: " + "; ".join(f"{ad} — {aciklama[ad]}" for ad in kotu) + "."


def main() -> int:
    CIKTI.mkdir(parents=True, exist_ok=True)
    kok = mts.veri_kok()
    eleme = pd.read_csv(kok / "eleme.csv")
    tam, bilgi = havuz_yukle(kok, eleme)
    kesimler = mts.kesimleri_uret()
    assert len(kesimler) == 11 and str(kesimler[0].date()) == "2020-05-08" and str(kesimler[-1].date()) == "2025-05-08"
    assert mts.pencere_sonu(kesimler[-1]) == HOLDOUT

    # taban: tam veri (meta-testle aynı sonuç vermeli)
    taban = mts.sema_kos(tam, kesimler)
    meta_oz = json.loads((KOK / "sonuclar" / "evren" / "meta_test" / "ozet.json").read_text(encoding="utf-8"))
    meta_dbar = meta_oz["ana"]["dbar"]
    assert abs(taban["istatistik_N1"]["dbar"] - meta_dbar) < 1e-6, "taban D̄ meta-testten sapıyor"

    # B1
    mevcut = mevcut_semboller(kok)
    b1_bulunan = [s for s in B1_LISTE if s in mevcut]
    b1_yok = [s for s in B1_LISTE if s not in mevcut]
    b1_havuz, _ = havuz_yukle(kok, eleme, sembol_filtre=set(b1_bulunan))
    b1 = mts.sema_kos(b1_havuz, kesimler)

    # B2
    seriler = {s: mum_oku(s) for s in sorted(mevcut)}
    kaz = {}
    for T in kesimler:
        kaz[str(T.date())] = kazananlar(seriler, T, mts.pencere_sonu(T))
    birlesik = sorted({s for v in kaz.values() for s, _ in v})
    ins_gunluk = {}
    for s in birlesik:
        hv, _ = havuz_yukle(kok, eleme, sembol_filtre={s})
        ins_gunluk[s] = {sd.kimlik: sd.gunluk for sd in hv}
    b2_pw = []
    for T in kesimler:
        son = mts.pencere_sonu(T)
        cikar = [s for s, _ in kaz[str(T.date())]]
        b2_pw.append(bir_pencere_kos(pencereden_cikar(tam, ins_gunluk, T, son, cikar), T))
    b2_d = [w["D_N1"] for w in b2_pw]

    # B3
    sh_havuz, _ = havuz_yukle(kok, eleme, yon=SHORT)
    b3 = mts.sema_kos(sh_havuz, kesimler)
    ytab = yon_tablosu(kok, eleme)
    long_satir = []
    for T, w in zip(kesimler, taban["pencereler"]):
        son = mts.pencere_sonu(T)
        S = w["S"].split(";")
        n1 = [sd.kimlik for sd in tam if (lambda g: g["uygun"] and g["sum_r"] > 0)(mts.geriye_bakis(sd, T))]
        a, b = long_payi(ytab, S, T, son), long_payi(ytab, n1, T, son)
        long_satir.append({"kesim": str(T.date()), "S_lb": a["lb_long_payi"], "N1_lb": b["lb_long_payi"], "S_ol": a["ol_long_payi"],
                           "N1_ol": b["ol_long_payi"], "S_lb_n": a["lb_n"], "N1_lb_n": b["lb_n"], "S_ol_n": a["ol_n"],
                           "N1_ol_n": b["ol_n"]})
    long_df = pd.DataFrame(long_satir)

    maks = mts.maks_tarih_dogrula()
    kos_df = pd.DataFrame([{"kesim": str(T.date()), "D_tam": taban["pencereler"][i]["D_N1"], "D_B1": b1["pencereler"][i]["D_N1"],
                            "D_B2": b2_d[i], "D_B3": b3["pencereler"][i]["D_N1"],
                            "uygun_B1": b1["pencereler"][i]["n_uygun"], "gecen_B1": b1["pencereler"][i]["n_kapi_gecen"],
                            "uygun_B2": b2_pw[i]["n_uygun"], "gecen_B2": b2_pw[i]["n_kapi_gecen"],
                            "uygun_B3": b3["pencereler"][i]["n_uygun"], "gecen_B3": b3["pencereler"][i]["n_kapi_gecen"],
                            "S_B1": b1["pencereler"][i]["S"], "S_B2": b2_pw[i]["S"], "S_B3": b3["pencereler"][i]["S"]}
                           for i, T in enumerate(kesimler)])
    oz = {"taban": {"dbar": taban["istatistik_N1"]["dbar"], "meta_dbar": meta_dbar},
          "B1": {"ad": "bilinen büyükler", **d_istatistik(b1["D_N1"])},
          "B2": {"ad": "kazananları çıkar", **d_istatistik(b2_d)},
          "B3": {"ad": "yalnız short", **d_istatistik(b3["D_N1"])},
          "b1_bulunan": b1_bulunan, "b1_bulunmayan": b1_yok,
          "B2_kazananlar": kaz, "maks_tarih": str(maks),
          "girdi_hash": {"betik": mts._sha(Path(__file__)), "eleme_csv": mts._sha(kok / "eleme.csv"),
                         "on_kayit": mts._sha(CIKTI / "ON_KAYIT.md")},
          "commit": mts._git("rev-parse", "HEAD"), "veri": {k: v for k, v in bilgi.items()}}
    oz["yorum"] = yorum_metni(oz)
    kos_df.to_csv(CIKTI / "sonuc.csv", index=False)
    long_df.to_csv(CIKTI / "long_payi.csv", index=False)
    pd.DataFrame([{"kesim": k, "sira": i + 1, "sembol": s, "getiri": g} for k, v in kaz.items() for i, (s, g) in enumerate(v)]
                 ).to_csv(CIKTI / "b2_kazananlar.csv", index=False)
    (CIKTI / "ozet.json").write_text(json.dumps(mts._sade(oz), ensure_ascii=False, indent=2), encoding="utf-8")
    rapor_yaz(CIKTI / "rapor.md", mts._sade(oz), long_df, kos_df)
    for ad in ("B1", "B2", "B3"):
        r = oz[ad]
        print(ad, round(r["dbar"], 2), r["p_yukari"], r["p_asagi"], r["ga90"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
