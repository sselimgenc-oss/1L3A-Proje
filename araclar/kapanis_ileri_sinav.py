"""Kapanış ön kayıt eki (10): 6 kayıt için TEK SEFERLİK ileri dönem sınavı.

Dönem: 2025-11-08 00:00 UTC (= v2 `sabit.HOLDOUT_BAS`) -> mevcut en son kapanmış mum. Isınma için dönem öncesi veri okunur; giriş zamanı
dönem başlangıcından önce olan işlem ölçüme girmez (`kendi_hesabi_oynat` analiz_bas süzgeci + burada ayrıca doğrulanır).

Kilitli dönem okuması: `motor.veri.kilit.kilit_siniri` yolu (`tf_mumlari`/`depo.funding_oku` -> `kilit_ac=True` + zorunlu gerekçe; açılış
`sonuclar/kilit_acilis.jsonl` günlüğüne yazılır). Koruma devre dışı bırakılmaz. NOT: `tek_ham_kos` içindeki `sizinti_kontrol`
(geliştirme dönemi sızıntı bekçisi) holdout verisinde kesin hata verdiği için o fonksiyonun gövdesi (yedi satır) `ham_kos_ileri`de bu
bekçi OLMADAN yinelenir; veri yine yalnız resmi kilit açma yolundan gelir.

Ölçütler (her kayıt ayrı; maliyet x2): (a) net getiri > 0, (b) %1,5 işlem riski ve -%30 kill ile kill olayı yok,
(c) tüm işlemler long ise dengeli eşit ağırlıklı günlük al-tut net getirisi (x2) <= strateji net getirisi. <20 işlem: "yetersiz_ornek".
Tek koşu: çıktı (ya da kilit açıldı işareti) varsa yeniden koşu reddedilir; `--zorla` yoktur.

Kullanım: python araclar/kapanis_ileri_sinav.py --kuru   |   python araclar/kapanis_ileri_sinav.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from araclar import kapanis_kosu as kk  # noqa: E402
from araclar import kapanis_kosu_listesi as kl  # noqa: E402
from motor.arastirma import evren_maliyet, wf_evren  # noqa: E402
from motor.arastirma.kapanis.tek_grafik import kendi_hesabi_oynat  # noqa: E402
from motor.arastirma.v2 import ham as v2_ham  # noqa: E402
from motor.arastirma.v2 import sabit  # noqa: E402
from motor.backtest.motor import backtest  # noqa: E402
from motor.strateji import funding  # noqa: E402
from motor.veri import depo  # noqa: E402
from motor.veri.yeniden_ornekle import tf_mumlari  # noqa: E402

KAPANIS = KOK / "sonuclar" / "kapanis"
CIKTI = KAPANIS / "ileri_sinav"
ISARET = ".kilit_acildi"
GEREKCE = "kapanış ek 10 tek seferlik ileri dönem sınavı (kullanıcı kararı 2026-11-14)"
DONEM_BAS = sabit.HOLDOUT_BAS                      # 2025-11-08 00:00 UTC
MIN_ISLEM = 20
KAYITLAR = (("HAM:X005:664#v1", 1), ("HAM:X005:705", 1), ("HAM:X005:301#v1", 1), ("HAM:X005:138#v3", 1),
            ("HAM:B001:670#v1", 2), ("HAM:B001:574#v1", 2))
LISTELER = {1: KAPANIS / "kosu_listesi_asama1.csv", 2: KAPANIS / "kosu_listesi_asama2.csv"}
SUTUNLAR = ["kimlik", "asama", "sinif", "tf", "n_islem", "yetersiz_ornek", "ort_r", "pf_x2", "net_x1", "net_x2", "max_dusus_x2",
            "kill_x2", "kill_x1", "long_only", "bh_net_x2", "a_net_pozitif", "b_kill_yok", "c_al_tutu_gecti", "karar", "hata"]


class TekKosuHatasi(RuntimeError):
    """Sınav bir kez koşulur; çıktı ya da kilit açıldı işareti varken yeniden koşu reddedilir."""


# ---------------------------------------------------------------- kayıt seçimi
def kayitlar_ek11() -> tuple:
    """Ek 11: aşama 1/2 sonuç tablolarındaki paper_adayi=True kayıtlar, ek 10'daki 6 hariç (sıra: tablo sırası)."""
    import pandas as _pd
    ek10 = {k for k, _ in KAYITLAR}
    out = []
    for asama in (1, 2):
        d = _pd.read_csv(KAPANIS / f"sonuc_asama{asama}.csv")
        out += [(k, asama) for k in d.loc[d["paper_adayi"] == True, "kimlik"] if k not in ek10]  # noqa: E712
    return tuple(out)


def kayit_satirlari(kayitlar=KAYITLAR, listeler=None, dogrula: bool = True) -> list:
    """6 kimliğin satırları (dondurulmuş listelerden; SHA doğrulanır). Bulunamayan/KOSULACAK olmayan/portföy kayıt -> hata."""
    listeler = listeler or LISTELER
    tum = {}
    for asama, yol in listeler.items():
        if dogrula:
            kl.dogrula_dosya(Path(yol))
        tum[asama] = {s["kimlik"]: s for s in kk.liste_oku(Path(yol))}
    out = []
    for kimlik, asama in kayitlar:
        s = tum.get(asama, {}).get(kimlik)
        if s is None:
            raise KeyError(f"{kimlik}: aşama {asama} listesinde yok")
        if s["durum"] != "KOSULACAK":
            raise ValueError(f"{kimlik}: durum {s['durum']} (KOSULACAK değil)")
        _, pf = kl.sinif_coz(s["sinif"], s["modul"])
        if pf:
            raise ValueError(f"{kimlik}: portföy sınıfı; bu sınav yalnız tek grafik kayıtlarını kapsar")
        out.append({**s, "asama": asama})
    return out


# ---------------------------------------------------------------- veri (resmi kilit açma yolu)
def veri_al_ileri(sembol: str, tf: str, simdi=None, dizin=None):
    """(mumlar, funding): TÜM geçmiş + kilitli dönem; `kilit_ac=True` + GEREKCE (kilit_acilis.jsonl'a yazılır). Kapanmamış mum atılır."""
    mumlar = tf_mumlari(sembol, tf, None, None, dizin=dizin, kilit_ac=True, gerekce=GEREKCE)
    try:
        fund = depo.funding_oku(sembol, None, None, dizin=dizin, kilit_ac=True, gerekce=GEREKCE)
    except FileNotFoundError:
        fund = None
    return kapanmis_mumlar(mumlar, tf, simdi), fund


def kapanmis_mumlar(mumlar: pd.DataFrame, tf: str, simdi=None) -> pd.DataFrame:
    if mumlar is None or mumlar.empty:
        return mumlar
    simdi = pd.Timestamp(datetime.now(timezone.utc) if simdi is None else simdi)
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    return mumlar[(pd.DatetimeIndex(mumlar.index) + depo.aralik_suresi(tf)) <= simdi]


def ham_kos_ileri(strateji, sembol: str, tf: str, carpan: float, tablo: Path, veri_al):
    """`tek_ham_kos` ile aynı adımlar; yalnız geliştirme dönemi sızıntı bekçisi (`sizinti_kontrol`) yok: bu sınavın verisi kasıtlı
    olarak holdout'tur ve yalnız resmi kilit açma yolundan (`veri_al_ileri`) gelir. -> (ham, mtm, mumlar)."""
    if carpan not in (1.0, 2.0):
        raise ValueError(f"maliyet çarpanı 1 veya 2 olmalı: {carpan}")
    mumlar, fonlama = veri_al(sembol, tf)
    if mumlar is None or mumlar.empty:
        raise FileNotFoundError(f"{sembol} {tf}: mum yok")
    kural = wf_evren.tarama.SEMBOL_KURALLARI.get(sembol, wf_evren.tarama.VARSAYILAN_KURAL)
    ayarlar = evren_maliyet.maliyet_ayarlari(sembol, kural, carpan, tablo)
    hazir = funding.stratejiye_hazirla(strateji, mumlar, fonlama, sembol, tf)
    sonuc = backtest(hazir, strateji, ayarlar, fonlama)
    ham, mtm = v2_ham.islem_hazirla(sonuc.islemler, sembol, tf, carpan, mumlar, tablo)
    return ham, mtm, mumlar


# ---------------------------------------------------------------- saf ölçüt işlevleri (testli)
def donem_kes(ham: pd.DataFrame, bas=DONEM_BAS) -> pd.DataFrame:
    """Giriş zamanı >= dönem başlangıcı olan işlemler."""
    if ham is None or not len(ham):
        return ham
    return ham[pd.DatetimeIndex(ham["giris_zamani"]) >= pd.Timestamp(bas)].copy()


def bh_bitisi(son_kapanis) -> pd.Timestamp:
    """Al-tut için hariç bitiş: tam kapanmış son UTC gününün ertesi 00:00 (kısmi gün al-tuta girmez)."""
    t = pd.Timestamp(son_kapanis)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    sonu = (t - pd.Timedelta(1, "ns")).floor("D")            # t gece yarısıysa önceki gün tamdır
    tam_son = sonu if t == t.floor("D") else sonu - pd.Timedelta(1, "D")
    return tam_son + pd.Timedelta(1, "D")


def bh_toplam(gunluk) -> float:
    g = np.asarray(gunluk, dtype=float)
    g = g[~np.isnan(g)]
    return float(np.prod(1.0 + g) - 1.0) if len(g) else math.nan


def olcut_degerlendir(net_x2, kill_x2, long_only: bool, bh_net, n_islem: int) -> dict:
    """Ek 10 ölçütleri. (c) yalnız long_only için anlamlı; değilse None. NaN/None = geçmez."""
    def ok(v):
        return v is not None and not (isinstance(v, float) and math.isnan(v))
    a = bool(ok(net_x2) and net_x2 > 0)
    b = bool(ok(kill_x2) and kill_x2 == 0)
    c = None
    if long_only:
        c = bool(ok(bh_net) and ok(net_x2) and bh_net <= net_x2)
    yetersiz = n_islem < MIN_ISLEM
    if not (a and b):
        karar = "paper_cikar"
    elif c is False:
        karar = "al_tutu_gecemedi"
    else:
        karar = "gecti"
    return {"a_net_pozitif": a, "b_kill_yok": b, "c_al_tutu_gecti": c, "yetersiz_ornek": yetersiz, "karar": karar}


# ---------------------------------------------------------------- tek kayıt
def kayit_kos(satir: dict, tablo: Path = kk.TABLO, veri_al=None, ham_fn=None, bas=DONEM_BAS) -> dict:
    """Bir kaydı koşar. veri_al(sembol, tf)->(mumlar, funding); ham_fn(strateji, sembol, tf, carpan, tablo, veri_al) -> (ham, mtm, mumlar)."""
    veri_al = veri_al or veri_al_ileri
    ham_fn = ham_fn or ham_kos_ileri
    evren = kl.evren_coz(satir["evren"])
    tf = satir["tf"]
    ok, aciklama = kk.tf_cozum(tf)
    if not ok:
        raise FileNotFoundError(aciklama)
    onbellek: dict = {}

    def al(sembol, tf_):
        if (sembol, tf_) not in onbellek:
            onbellek[(sembol, tf_)] = veri_al(sembol, tf_)
        return onbellek[(sembol, tf_)]

    ham = {1.0: {}, 2.0: {}}
    mumlar_s: dict = {}
    for s in evren:
        for c in (1.0, 2.0):
            st, _, _ = kk._kur(satir)
            h, _, m = ham_fn(st, s, tf, c, tablo, al)
            ham[c][s] = h
            mumlar_s[s] = m
    dur = depo.aralik_suresi(tf)
    son_kapanis = max(pd.Timestamp(m.index[-1]) for m in mumlar_s.values() if len(m)) + dur
    analiz_bit = son_kapanis
    m1, _ = kendi_hesabi_oynat(ham[1.0], evren, bas, analiz_bit, 1.0, tablo)
    m2, tablo2 = kendi_hesabi_oynat(ham[2.0], evren, bas, analiz_bit, 2.0, tablo)
    if len(tablo2) and (pd.DatetimeIndex(tablo2["giris"]) < pd.Timestamp(bas)).any():
        raise RuntimeError("dönem öncesi giriş ölçüme sızdı")            # asla olmamalı
    parca = [donem_kes(h, bas)["yon"] for h in ham[2.0].values() if h is not None and len(donem_kes(h, bas))]
    yonler = pd.concat(parca, ignore_index=True) if parca else pd.Series([], dtype=int)
    long_only = bool(len(yonler) > 0 and (yonler == 1).all())
    kabul = m2.get("kabul") or []
    ort_r = float(tablo2.iloc[kabul]["r"].mean()) if len(kabul) else math.nan
    bh_net = math.nan
    if long_only:
        bh = kk.bh_net_getiri(mumlar_s, evren, bas, bh_bitisi(son_kapanis), 2.0, tablo)
        bh_net = bh_toplam(bh) if len(bh) else math.nan
    n = int(m2.get("islem_sayisi", 0))
    o = olcut_degerlendir(m2.get("net_getiri"), m2.get("kill_olayi"), long_only, bh_net, n)
    return {"kimlik": satir["kimlik"], "asama": satir.get("asama"), "sinif": satir["sinif"], "tf": tf,
            "parametreler": json.loads(satir["parametreler"]), "donem_bas": str(bas), "donem_bit": str(son_kapanis),
            "n_islem": n, "n_islem_x1": int(m1.get("islem_sayisi", 0)), "ort_r": ort_r,
            "pf_x2": m2.get("profit_factor"), "pf_x1": m1.get("profit_factor"),
            "net_x1": m1.get("net_getiri"), "net_x2": m2.get("net_getiri"), "max_dusus_x2": m2.get("max_dusus"),
            "kill_x2": m2.get("kill_olayi"), "kill_x1": m1.get("kill_olayi"), "long_only": long_only,
            "bh_net_x2": bh_net, "r_enstruman": m2.get("r_enstruman"), "hata": "", **o}


# ---------------------------------------------------------------- tek koşu koruması + çıktı
def tek_kosu_kontrol(cikti: Path) -> None:
    cikti = Path(cikti)
    if not cikti.exists():
        return
    var = [p.name for p in cikti.iterdir() if p.name in ("sonuc.csv", "rapor.md", ISARET) or p.suffix == ".json"]
    if var:
        raise TekKosuHatasi(f"{cikti}: sınav daha önce koşulmuş/başlatılmış ({', '.join(sorted(var))}); tek seferlik, yeniden koşu yok")


def rapor_uret(sonuclar: list) -> str:
    sat = ["# Kapanış ek 10 — tek seferlik ileri dönem sınavı", "",
           f"Dönem: {DONEM_BAS} -> {sonuclar[0].get('donem_bit') if sonuclar else '?'} (en son kapanmış mum). "
           f"Kilit gerekçesi: \"{GEREKCE}\". Sapma kaydıdır; ön kayıtlı kanıt değildir. Geçen kayıt için \"gerekli, yeterli değil\"; "
           "canlı şartı (12 hafta paper + kullanıcı onayı) değişmez.", "",
           "| kimlik | TF | işlem | ort R | PF x2 | net x1 | net x2 | maks düşüş | kill | long-only | al-tut x2 | a | b | c | karar |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def f(v, p=3):
        return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{p}f}"

    for r in sonuclar:
        if r.get("hata"):
            sat.append(f"| {r['kimlik']} | {r.get('tf', '')} | HATA: {r['hata'][:120]} |||||||||||")
            continue
        et = " (yetersiz_ornek)" if r["yetersiz_ornek"] else ""
        c = "-" if r["c_al_tutu_gecti"] is None else ("geçti" if r["c_al_tutu_gecti"] else "GEÇEMEDİ")
        sat.append(f"| {r['kimlik']} | {r['tf']} | {r['n_islem']}{et} | {f(r['ort_r'])} | {f(r['pf_x2'], 2)} | {f(r['net_x1'])} | "
                   f"{f(r['net_x2'])} | {f(r['max_dusus_x2'])} | {r['kill_x2']} | {'evet' if r['long_only'] else 'hayır'} | "
                   f"{f(r['bh_net_x2'])} | {'geçti' if r['a_net_pozitif'] else 'GEÇEMEDİ'} | "
                   f"{'geçti' if r['b_kill_yok'] else 'GEÇEMEDİ'} | {c} | {r['karar']} |")
    sat += ["", "Karar anlamı: paper_cikar = (a) ya da (b) geçilemedi; al_tutu_gecemedi = (c) geçilemedi (trend kaydı paper'da kalır, etiketli); "
            "gecti = (a)-(c) geçildi (gerekli, yeterli değil). <20 işlem 'yetersiz_ornek' etiketi alır, ölçütler yine uygulanır.", ""]
    return "\n".join(sat) + "\n"


def sonuclari_yaz(sonuclar: list, cikti: Path) -> None:
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    for r in sonuclar:
        kk.atomik_yaz(cikti / f"{kk.guvenli(r['kimlik'])}.json", r)
    with open(cikti / "sonuc.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUNLAR, extrasaction="ignore")
        w.writeheader()
        for r in sonuclar:
            row = {k: r.get(k, "") for k in SUTUNLAR}
            row["karar"] = r.get("karar") or "HATA"
            w.writerow(row)
    (cikti / "rapor.md").write_text(rapor_uret(sonuclar), encoding="utf-8")


def kos(satirlar: list, cikti: Path = CIKTI, tablo: Path = kk.TABLO, veri_al=None, ham_fn=None, bas=DONEM_BAS) -> list:
    tek_kosu_kontrol(cikti)
    Path(cikti).mkdir(parents=True, exist_ok=True)
    (Path(cikti) / ISARET).write_text(f"{datetime.now(timezone.utc).isoformat()}\n{GEREKCE}\n", encoding="utf-8")   # veri açılmadan ÖNCE
    sonuclar = []
    for s in satirlar:
        try:
            sonuclar.append(kayit_kos(s, tablo, veri_al, ham_fn, bas))
        except Exception as e:  # noqa: BLE001 — kayıt HATA olarak yazılır; sınav yeniden koşulmaz
            sonuclar.append({"kimlik": s["kimlik"], "asama": s.get("asama"), "sinif": s["sinif"], "tf": s["tf"],
                             "karar": "HATA", "hata": f"{type(e).__name__}: {e}"})
    sonuclari_yaz(sonuclar, cikti)
    return sonuclar


# ---------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kapanış ek 10: tek seferlik ileri dönem sınavı (yeniden koşu/--zorla yok)")
    ap.add_argument("--kuru", action="store_true", help="holdout okumadan yalnız kurulum/çözümleme kontrolü")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--ek11", action="store_true", help="ek 11: kalan 35 paper adayı (ek 10'daki 6 hariç), ayrı çıktı ve gerekçe")
    a = ap.parse_args(argv)
    global GEREKCE
    if a.ek11:
        GEREKCE = "kapanış ek 11 ileri dönem sınavı, kalan paper adayları (kullanıcı kararı 2026-11-14)"
        a.cikti = a.cikti or str(KAPANIS / "ileri_sinav_ek11")
        satirlar = kayit_satirlari(kayitlar_ek11())
    else:
        a.cikti = a.cikti or str(CIKTI)
        satirlar = kayit_satirlari()
    if a.kuru:
        rapor = kk.kuru(satirlar)
        for r in rapor:
            print(f"{r['kimlik']:<20} {r['tf']:<4} {r['durum']:<8} {r.get('tur', '-'):<4} veri_mb={r['veri_mb']} {r['sorun']}")
        print(f"[kuru] {len(rapor)} kayıt; dönem {DONEM_BAS} -> son kapanmış mum; kilit gerekçesi: {GEREKCE!r}; "
              f"çıktı dizini {a.cikti} ({'VAR - koşu reddedilir' if Path(a.cikti).exists() and any(Path(a.cikti).iterdir()) else 'boş/yok'})")
        return 0 if all(r["durum"] == "TAMAM" for r in rapor) else 1
    sonuclar = kos(satirlar, Path(a.cikti))
    for r in sonuclar:
        print(r["kimlik"], r.get("karar"), r.get("hata", ""))
    print(f"yazıldı: {a.cikti}/sonuc.csv, rapor.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
