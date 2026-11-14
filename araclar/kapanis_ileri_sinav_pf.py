"""Kapanış ön kayıt eki (12) kapsamı dışındaki 6 PORTFÖY kaydının ileri dönem koşusu (bilgi amaçlı, tek seferlik).

Dönem: 2025-11-08 00:00 UTC (= `sabit.HOLDOUT_BAS`) -> mevcut en son kapanmış mum. Dönem öncesi veri yalnız ısınmadır; getiri, Sharpe,
dengeleme, kill ve al-tut ölçümü yalnız dönem günlerinde yapılır. Portföy hesabı aşama 1'dekiyle aynıdır
(`motor.arastirma.kapanis.portfoy._hesap`: %1,5 işlem riski eşlemesi, -%30 kalıcı kill, x1/x2 maliyet; funding hazırlığı
`wf_evren_portfoy._kos` içinde `funding.stratejiye_hazirla` ile). Veri YALNIZ resmi kilit açma yolundan gelir
(`tf_mumlari(..., kilit_ac=True, gerekce=...)`, `depo.funding_oku(..., kilit_ac=True, ...)`; açılış `kilit_acilis.jsonl`'a yazılır).
`portfoy._veri_topla` içindeki geliştirme dönemi sızıntı bekçisi (`sizinti_kontrol`, HOLDOUT_BAS/DONEM_SONU) holdout verisinde kesin
hata vereceğinden `veri_topla_ileri`de yinelenmez (diğer adımlar aynı); koruma kapatılmaz, veri kilit yolundan alınır.

Ölçütler (ek 2 portföy kapılarının ileri dönem karşılığı, BİLGİ AMAÇLI): (a) net x2 > 0, (b) kill x2 yok, Sharpe x2 raporlanır,
(c) long-only kayıtta aynı dönem eşit ağırlıklı dengeli günlük al-tut net x2 <= strateji net x2; dengeleme sayısı raporlanır.
Hesap dönem başında taze sermayeyle başlar (ısınmada işlem/kill yok, devralınan pozisyon yok); ısınmada kill görülürse HATA (olmamalı). "Bu evrende uygun değil" vb. de HATA yazılır.
Tek koşu: çıktı ya da `.kilit_acildi` işareti varsa yeniden koşu reddedilir; `--zorla` yoktur.

Kullanım: python araclar/kapanis_ileri_sinav_pf.py --kuru   |   python araclar/kapanis_ileri_sinav_pf.py
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

from araclar import kapanis_ileri_sinav as iik  # noqa: E402
from araclar import kapanis_kosu as kk  # noqa: E402
from araclar import kapanis_kosu_listesi as kl  # noqa: E402
from motor.arastirma import wf_portfoy as wp  # noqa: E402
from motor.arastirma.v2 import ham as v2_ham  # noqa: E402
from motor.strateji import funding  # noqa: E402
from motor.arastirma.kapanis import portfoy as kpf  # noqa: E402
from motor.portfoy.motor import portfoy_backtest  # noqa: E402
from motor.veri import depo  # noqa: E402
from motor.veri.yeniden_ornekle import tf_mumlari  # noqa: E402

KAPANIS = KOK / "sonuclar" / "kapanis"
CIKTI = KAPANIS / "ileri_sinav_ek12_pf"
ISARET = iik.ISARET
GEREKCE = "kapanış ek 12 ileri dönem sınavı, portföy kayıtları bilgi amaçlı (kullanıcı kararı 2026-11-14)"
DONEM_BAS = iik.DONEM_BAS
LISTE = KAPANIS / "kosu_listesi_asama1.csv"
KIMLIKLER = ("AYAR:pf__kesit_ls:d12b:kesit-ibs:ibs_k3_gunluk", "AYAR:pf__kesit_ls:d12b:kesit-orantili-agirlik:donus_orantili",
             "KOD:pf__v3-funding-1s-devam", "KOD:pf__v3-funding-kesit-decil-carry", "KOD:pf__v3-funding-z90-3gun",
             "KOD:v3__donchian-ansambl-vol-hedef")
SUTUNLAR = ["kimlik", "asama", "sinif", "tf", "yon", "gun", "dengeleme", "sharpe_x1", "sharpe_x2", "net_x1", "net_x2", "max_dusus_x2",
            "kill_x1", "kill_x2", "long_only", "bh_net_x2", "a_net_pozitif", "b_kill_yok", "c_al_tutu_gecti", "karar", "hata"]
TekKosuHatasi = iik.TekKosuHatasi


# ---------------------------------------------------------------- kayıt seçimi
def kayit_satirlari(kimlikler=KIMLIKLER, yol: Path = LISTE, dogrula: bool = True) -> list:
    if dogrula:
        kl.dogrula_dosya(Path(yol))
    tum = {s["kimlik"]: s for s in kk.liste_oku(Path(yol))}
    out = []
    for k in kimlikler:
        s = tum.get(k)
        if s is None:
            raise KeyError(f"{k}: aşama 1 listesinde yok")
        if s["durum"] != "KOSULACAK":
            raise ValueError(f"{k}: durum {s['durum']} (KOSULACAK değil)")
        _, pf = kl.sinif_coz(s["sinif"], s["modul"])
        if not pf:
            raise ValueError(f"{k}: portföy sınıfı değil")
        out.append({**s, "asama": 1})
    return out


# ---------------------------------------------------------------- veri (resmi kilit açma yolu)
def veri_al_ileri(sembol: str, tf: str, simdi=None, dizin=None):
    """(mumlar, funding): tüm geçmiş + kilitli dönem; kilit_ac=True + GEREKCE. Kapanmamış mum atılır."""
    mumlar = tf_mumlari(sembol, tf, None, None, dizin=dizin, kilit_ac=True, gerekce=GEREKCE)
    try:
        fund = depo.funding_oku(sembol, None, None, dizin=dizin, kilit_ac=True, gerekce=GEREKCE)
    except FileNotFoundError:
        fund = None
    return iik.kapanmis_mumlar(mumlar, tf, simdi), fund


def veri_topla_ileri(evren, tf, veri_al):
    """`portfoy._veri_topla` ile aynı, yalnız holdout sızıntı bekçisi ve DONEM_SONU denetimi yok."""
    v, f, dis = {}, {}, []
    for s in evren:
        try:
            mumlar, fonlama = veri_al(s, tf)
        except (FileNotFoundError, ValueError) as e:
            dis.append(f"{s}: {type(e).__name__}: {e}")
            continue
        if mumlar is None or not len(mumlar):
            dis.append(f"{s}: mum yok")
            continue
        v[s] = mumlar.drop(columns="eksik") if "eksik" in mumlar.columns else mumlar
        if fonlama is not None and len(fonlama):
            f[s] = fonlama
    if not v:
        raise FileNotFoundError(f"evrende hiç veri yok: {dis}")
    return v, f, dis


def hesap_ileri(st, v, f, evren_t, tf, carpan, tablo_yolu, limitler, bas=DONEM_BAS):
    """`portfoy._hesap` ile aynı adımlar; fark: hesap `bas` anında TAZE sermayeyle (10.000 USDT, aynı limitler) başlar. `bas`tan önceki
    veri yalnız gösterge/sinyal ısınmasıdır: `islem_baslangic=bas` ile ısınmada işlem açılmaz (özsermaye düz, kill/limit olayı yok);
    dönem başında devralınan pozisyon yoktur. Döner: PortfoyHesap (getiri/özsermaye ısınma günlerini de içerir, düz 0)."""
    import dataclasses
    if carpan not in (1.0, 2.0):
        raise ValueError(f"maliyet çarpanı 1 veya 2 olmalı: {carpan}")
    from motor.arastirma import wf_portfoy as _wp
    ay = dataclasses.replace(v2_ham.maliyet_pf(evren_t, carpan, tablo_yolu), limit_modu="uygula",
                             baslangic_sermaye=kpf.BASLANGIC_SERMAYE, risk_yuzde=limitler["islem_risk"])
    sec = _wp.gerekli_semboller(st, evren_t)
    hazir = {s: funding.stratejiye_hazirla(st, v[s], f.get(s), s, tf) for s in sec}
    with kpf.arastirma_limitleri(**limitler):
        r = portfoy_backtest(hazir, st, ay, {s: f[s] for s in sec if s in f}, islem_baslangic=pd.Timestamp(bas))
    ozs = r.gunluk_ozsermaye.copy()
    ozs.index = pd.DatetimeIndex(ozs.index).floor("D")
    ozs = ozs.groupby(level=0).last().astype(float)
    getiri = ozs.pct_change().fillna(0.0)
    getiri, fon = v2_ham.pf_fonlama_duzeltmesi(getiri, r.gunluk_ozsermaye, r.pozisyon_gecmisi, v, tablo_yolu)
    q = r.pozisyon_gecmisi
    degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
    gun = set(pd.DatetimeIndex(q.index[degisti.to_numpy()]).floor("D")) if len(q) else set()
    deng = pd.Series([g in gun for g in getiri.index], index=getiri.index)
    kill = [o for o in r.limit_olaylari if o.get("tur") == "kill_switch"]
    return kpf.PortfoyHesap(carpan, ozs, getiri, r.islemler, deng, kill, list(r.limit_olaylari), len(r.kirpmalar), list(r.uyarilar), fon,
                            float(ozs.iloc[-1] / kpf.BASLANGIC_SERMAYE - 1.0) if len(ozs) else math.nan)


# ---------------------------------------------------------------- saf ölçüt işlevleri
def donem_getiri(getiri: pd.Series, bas=DONEM_BAS, bit=None) -> pd.Series:
    """Günlük getiri serisini [bas, bit) kes."""
    g = getiri[pd.DatetimeIndex(getiri.index) >= pd.Timestamp(bas)]
    if bit is not None:
        g = g[pd.DatetimeIndex(g.index) < pd.Timestamp(bit)]
    return g


def net(g) -> float:
    g = np.asarray(g, dtype=float)
    return float(np.prod(1.0 + g) - 1.0) if len(g) else math.nan


def max_dusus(g) -> float:
    g = np.asarray(g, dtype=float)
    if not len(g):
        return math.nan
    e = np.cumprod(1.0 + g)
    zirve = np.maximum.accumulate(np.r_[1.0, e])[1:]
    return float(np.max((zirve - e) / zirve))


def kill_say(olaylar, bas=DONEM_BAS) -> tuple:
    """-> (dönem öncesi, dönem içi) kill sayısı (olay 'zaman' alanına göre)."""
    once = ici = 0
    for o in olaylar:
        t = pd.Timestamp(o["zaman"])
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        if t < pd.Timestamp(bas):
            once += 1
        else:
            ici += 1
    return once, ici


def olcut_pf(net_x2, kill_x2, long_only: bool, bh_net) -> dict:
    ok = lambda v: v is not None and not (isinstance(v, float) and math.isnan(v))  # noqa: E731
    a = bool(ok(net_x2) and net_x2 > 0)
    b = bool(ok(kill_x2) and kill_x2 == 0)
    c = bool(ok(bh_net) and ok(net_x2) and bh_net <= net_x2) if long_only else None
    karar = "paper_cikar" if not (a and b) else ("al_tutu_gecemedi" if c is False else "gecti")
    return {"a_net_pozitif": a, "b_kill_yok": b, "c_al_tutu_gecti": c, "karar": karar}


# ---------------------------------------------------------------- tek kayıt
def kayit_kos(satir: dict, tablo: Path = kk.TABLO, veri_al=None, hesap_fn=None, bas=DONEM_BAS) -> dict:
    """veri_al(sembol, tf)->(mumlar, funding); hesap_fn = `portfoy._hesap` imzası (varsayılan `hesap_ileri`: dönem başında taze sermaye) -> PortfoyHesap."""
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    veri_al = veri_al or veri_al_ileri
    hesap_fn = hesap_fn or (lambda *a: hesap_ileri(*a, bas=bas))
    tf = satir["tf"]
    ok, aciklama = kk.tf_cozum(tf)
    if not ok:
        raise FileNotFoundError(aciklama)
    evren = kl.evren_coz(satir["evren"])
    par = json.loads(satir["parametreler"])
    sinif = tum_portfoy_stratejileri().get(satir["sinif"])
    if sinif is None:
        raise KeyError(f"bilinmeyen portföy stratejisi: {satir['sinif']}")
    v, f, dis = veri_topla_ileri(evren, tf, veri_al)
    evren_t = tuple(v)
    st = sinif(**par)
    etkin = st.etkin_semboller(evren_t)
    st = st.yeni(semboller=etkin) if etkin else st
    if not st.uygun_mu(evren_t):
        raise RuntimeError(f"{satir['sinif']}: bu evrende uygun değil (yeterli sembol/çift yok)")
    lim = {"islem_risk": kpf.ISLEM_RISK_YUZDE, "kill": kpf.KILL_YUZDE, "toplam_risk": kpf.TOPLAM_RISK_YUZDE}
    h1 = hesap_fn(st, v, f, evren_t, tf, 1.0, tablo, lim)
    h2 = hesap_fn(st, v, f, evren_t, tf, 2.0, tablo, lim)
    son_kapanis = max(pd.Timestamp(m.index[-1]) for m in v.values()) + depo.aralik_suresi(tf)
    bit = iik.bh_bitisi(son_kapanis)                                  # kısmi son gün ölçüme girmez
    once1, ici1 = kill_say(h1.kill_olaylari, bas)
    once2, ici2 = kill_say(h2.kill_olaylari, bas)
    if once1 or once2:
        raise RuntimeError(f"ısınma döneminde kill tetiklendi (x1 {once1}, x2 {once2}); beklenmedik, ölçülemez")
    g1, g2 = donem_getiri(h1.getiri, bas, bit), donem_getiri(h2.getiri, bas, bit)
    if not len(g2):
        raise RuntimeError("dönem içinde günlük getiri yok")
    deng = int(h2.dengeleme[(pd.DatetimeIndex(h2.dengeleme.index) >= pd.Timestamp(bas)) & (pd.DatetimeIndex(h2.dengeleme.index) < bit)].sum())
    long_only = satir["yon"] == "long"
    bh_net = math.nan
    if long_only:
        bh = kk.bh_net_getiri(v, evren_t, bas, bit, 2.0, tablo)
        bh_net = iik.bh_toplam(bh) if len(bh) else math.nan
    o = olcut_pf(net(g2), ici2, long_only, bh_net)
    return {"kimlik": satir["kimlik"], "asama": satir.get("asama"), "sinif": satir["sinif"], "tf": tf, "yon": satir["yon"],
            "parametreler": par, "donem_bas": str(bas), "donem_bit": str(bit), "gun": int(len(g2)), "dengeleme": deng,
            "sharpe_x1": wp.sharpe_gunluk(g1.to_numpy(dtype=float)), "sharpe_x2": wp.sharpe_gunluk(g2.to_numpy(dtype=float)),
            "net_x1": net(g1), "net_x2": net(g2), "max_dusus_x2": max_dusus(g2), "kill_x1": ici1, "kill_x2": ici2,
            "long_only": long_only, "bh_net_x2": bh_net, "disarida": dis, "hata": "", **o}


# ---------------------------------------------------------------- çıktı
def rapor_uret(sonuclar: list) -> str:
    bit = next((r.get("donem_bit") for r in sonuclar if r.get("donem_bit")), "?")
    sat = ["# Kapanış ek 12 — portföy kayıtları, ileri dönem (bilgi amaçlı)", "",
           f"Dönem: {DONEM_BAS} -> {bit}. Kilit gerekçesi: \"{GEREKCE}\". Bilgi amaçlıdır; ön kayıtlı kanıt değildir, "
           "iyi görünen kayıt \"keşif — kanıt değil\" etiketi alır; paper'a girmesi yeni ön kayıt ve ileri veri gerektirir.", "",
           "| kimlik | TF | gün | dengeleme | Sharpe x1 | Sharpe x2 | net x1 | net x2 | maks düşüş x2 | kill x2 | long-only | al-tut x2 | a | b | c | karar |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def f(v, p=3):
        return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{p}f}"

    for r in sonuclar:
        if r.get("hata"):
            sat.append(f"| {r['kimlik']} | {r.get('tf', '')} | HATA: {r['hata'][:140]} |||||||||||||")
            continue
        c = "-" if r["c_al_tutu_gecti"] is None else ("geçti" if r["c_al_tutu_gecti"] else "GEÇEMEDİ")
        sat.append(f"| {r['kimlik']} | {r['tf']} | {r['gun']} | {r['dengeleme']} | {f(r['sharpe_x1'], 2)} | {f(r['sharpe_x2'], 2)} | "
                   f"{f(r['net_x1'])} | {f(r['net_x2'])} | {f(r['max_dusus_x2'])} | {r['kill_x2']} | {'evet' if r['long_only'] else 'hayır'} | "
                   f"{f(r['bh_net_x2'])} | {'geçti' if r['a_net_pozitif'] else 'GEÇEMEDİ'} | "
                   f"{'geçti' if r['b_kill_yok'] else 'GEÇEMEDİ'} | {c} | {r['karar']} |")
    sat += ["", "Karar anlamı: paper_cikar = (a) ya da (b) geçilemedi; al_tutu_gecemedi = (c) geçilemedi; gecti = (a)-(c) geçildi "
            "(bilgi amaçlı). Bu kayıtlar dönem öncesi tek grafik/portföy kapılarında elenmişti; 6 kayıtta şansla iyi görünen beklenir.", ""]
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


def kos(satirlar: list, cikti: Path = CIKTI, tablo: Path = kk.TABLO, veri_al=None, hesap_fn=None, bas=DONEM_BAS) -> list:
    iik.tek_kosu_kontrol(cikti)
    Path(cikti).mkdir(parents=True, exist_ok=True)
    (Path(cikti) / ISARET).write_text(f"{datetime.now(timezone.utc).isoformat()}\n{GEREKCE}\n", encoding="utf-8")   # veri açılmadan ÖNCE
    sonuclar = []
    for s in satirlar:
        try:
            r = kayit_kos(s, tablo, veri_al, hesap_fn, bas)
        except Exception as e:  # noqa: BLE001 — HATA olarak yazılır; sınav yeniden koşulmaz
            r = {"kimlik": s["kimlik"], "asama": s.get("asama"), "sinif": s["sinif"], "tf": s["tf"], "karar": "HATA",
                 "hata": f"{type(e).__name__}: {e}"}
        sonuclar.append(r)
        print("[ileri-pf]", r["kimlik"], r.get("karar"), r.get("hata", ""), flush=True)
    sonuclari_yaz(sonuclar, cikti)
    return sonuclar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kapanış ek 12: 6 portföy kaydının ileri dönem koşusu (tek sefer; --zorla yok)")
    ap.add_argument("--kuru", action="store_true", help="veri okumadan yalnız kurulum/çözümleme kontrolü")
    ap.add_argument("--cikti", default=str(CIKTI))
    a = ap.parse_args(argv)
    satirlar = kayit_satirlari()
    if a.kuru:
        rapor = kk.kuru(satirlar)
        for r in rapor:
            print(f"{r['kimlik']:<58} {r['tf']:<4} {r['durum']:<8} {r.get('tur', '-'):<4} veri_mb={r['veri_mb']} {r['sorun']}")
        var = Path(a.cikti).exists() and any(Path(a.cikti).iterdir())
        print(f"[kuru] {len(rapor)} kayıt; dönem {DONEM_BAS} -> son kapanmış mum; kilit gerekçesi: {GEREKCE!r}; "
              f"çıktı {a.cikti} ({'VAR - koşu reddedilir' if var else 'boş/yok'})")
        return 0 if all(r["durum"] == "TAMAM" for r in rapor) else 1
    sonuclar = kos(satirlar, Path(a.cikti))
    print(f"yazıldı: {a.cikti}/sonuc.csv, rapor.md ({len(sonuclar)} kayıt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
