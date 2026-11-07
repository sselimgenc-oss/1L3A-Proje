"""Day trade kağıt al-sat motoru (10.000 $ sanal, 60 gün).

Her çalıştırmada veriler güncellenir ve kağıt döneminin başından bugüne kadar olan tüm
KAPANMIŞ mumlar backtest koduyla (daytrade.features + strategies + backtest) yeniden
oynatılır. Kararlar yalnızca kapanmış mumlara dayandığı için çalıştırma kaçsa/gecikse bile
işlem kaçmaz; sonuç bot 7/24 açıkmış gibidir.

  python -m kagit.motor --durum kagit_durum
  KAGIT_BASLANGIC=2026-09-15 python -m kagit.motor --durum /tmp/d     # geçmiş dönemle deneme
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from daytrade import data as D  # noqa: E402
from daytrade import universe as U  # noqa: E402
from daytrade.backtest import simulate  # noqa: E402
from daytrade.features import build  # noqa: E402
from daytrade.strategies import STRATEGIES  # noqa: E402

KOK = Path(__file__).resolve().parent
# Ayar dizini: varsayılan kagit/ (kripto hesabı). KAGIT_AYAR_DIZIN=kagit/hisse → ayrı hisse/emtia hesabı.
AYAR = Path(os.environ.get("KAGIT_AYAR_DIZIN") or KOK).resolve()
KISA = {"S10_trendday": "S10", "S13_falsebreak": "S13", "S15_tdpullback": "S15"}
ISINMA_GUN = 45  # göstergeler için başlangıçtan önce gereken geçmiş (4s EMA200 ≈ 34 gün)


def ayar():
    c = json.loads((AYAR / "config.json").read_text())
    if os.environ.get("KAGIT_BASLANGIC"):
        c["baslangic"] = os.environ["KAGIT_BASLANGIC"]
    bas = pd.Timestamp(c["baslangic"])
    bas = bas.tz_localize("UTC") if bas.tzinfo is None else bas.tz_convert("UTC")
    surumler = json.loads((AYAR / "ayarlar.json").read_text())["surumler"]
    for s in surumler:
        t = pd.Timestamp(s["gecerli"])
        s["_t"] = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    surumler.sort(key=lambda s: s["_t"])
    surumler[0]["_t"] = min(surumler[0]["_t"], bas)
    return c, bas, bas + pd.Timedelta(days=c["gun"]), surumler


def evren(dizin: Path) -> list[U.Instrument]:
    """Evren kağıt döneminin ilk çalıştırmasında sabitlenir (evren.json)."""
    f = dizin / "evren.json"
    if f.exists():
        return [U.Instrument(**d) for d in json.loads(f.read_text())]
    siniflar = json.loads((AYAR / "config.json").read_text()).get("siniflar")
    conn = D.check_connectivity()
    kripto = bist = None
    try:
        if conn["coingecko"] and conn["binance"]:
            kripto = U.refresh_crypto_top25(D._session())
    except Exception as e:
        print("Kripto listesi yenilenemedi:", e)
    try:
        if conn["yahoo"] and (not siniflar or "bist" in siniflar):
            bist = U.refresh_bist_top10()
    except Exception as e:
        print("BIST listesi yenilenemedi:", e)
    insts = U.build_universe(kripto, bist)
    if siniflar:
        insts = [i for i in insts if i.asset_class in siniflar]
    f.write_text(json.dumps([i.__dict__ for i in insts], ensure_ascii=False, indent=1))
    return insts


def veri_guncelle(insts, tf, bas):
    gun = max(ISINMA_GUN + 5, (pd.Timestamp.now(tz="UTC") - bas).days + ISINMA_GUN + 5)
    for inst in insts:
        for t in (tf, "1h", "4h"):
            try:
                D.update(inst, t, days=gun)
            except Exception as e:
                print(f"VERİ HATASI {inst.symbol} {t}: {e}")


def islemleri_uret(insts, tf, bas, son, surumler):
    """Tüm strateji/enstrüman işlemleri (giriş ∈ [bas, son)); açıklar 'acik', son mum
    sinyalleri 'bekleyen' olarak döner. Her işlem, giriş anında geçerli parametre sürümüyle."""
    out, son_veri = [], {}
    btc = None

    def hazirla(inst):
        e, h1, h4 = D.load(inst, tf), D.load(inst, "1h"), D.load(inst, "4h")
        if e is None or h1 is None or len(e) < 300:
            return None
        if h4 is None or len(h4) < 210:
            h4 = D.resample(h1, "4h")
        e = e[(e.index >= bas - pd.Timedelta(days=ISINMA_GUN)) & (e.index < son)]
        if len(e) < 300:
            return None
        return build(inst, e, h1[h1.index < son], h4[h4.index < son], tf)

    b_inst = next((i for i in insts if i.symbol == "BTCUSDT"), None)
    if b_inst is not None:
        btc = hazirla(b_inst)
    for inst in insts:
        df = btc if (inst is b_inst and btc is not None) else hazirla(inst)
        if df is None:
            print(f"ATLA {inst.symbol}: veri yetersiz")
            continue
        if btc is not None and inst.asset_class == "crypto":
            # Backus "S&P 500 olumluyken al" → BTC 4s trendi ve gün içi hareketi
            df = df.copy()
            df["mkt_move"] = ((btc["close"] - btc["dopen"]) / btc["atr_d"]).reindex(df.index)
            df["mkt_h4_up"] = (btc["h4_ema20"] > btc["h4_ema50"]).reindex(df.index)
            df["mkt_h4_dn"] = (btc["h4_ema20"] < btc["h4_ema50"]).reindex(df.index)
        son_veri[inst.symbol] = df.index[-1]
        guc = (df["close"] - df["dopen"]) / df["atr_d"]
        for k, sv in enumerate(surumler):
            t0 = sv["_t"]
            t1 = surumler[k + 1]["_t"] if k + 1 < len(surumler) else son
            for st, cfg in sv["stratejiler"].items():
                if inst.asset_class not in cfg.get("siniflar", []):
                    continue
                fn, _ = STRATEGIES[st]
                tr = simulate(df, fn(df, **cfg.get("params", {})), inst.cost_pct, inst.symbol,
                              st, mark_open=True)
                tr = tr[(tr["entry_time"] >= max(t0, bas)) & (tr["entry_time"] < t1)]
                if len(tr):
                    sb = tr["entry_time"] - pd.Timedelta(minutes=D.TF_MINUTES[tf])
                    skor = tr["dir"].to_numpy() * guc.reindex(sb).to_numpy()
                    tr = tr.assign(asset_class=inst.asset_class, surum=k, skor=skor)
                    out.append(tr)
    tr = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    return tr, son_veri


def portfoy(tr: pd.DataFrame, c: dict) -> pd.DataFrame:
    """Portföy kuralları: işlem başına %risk (gerçekleşen özsermayeden), en fazla N pozisyon,
    tek pozisyon ≤ max_agirlik, toplam ≤ max_toplam_agirlik (kaldıraç yok), aynı sembolde tek
    pozisyon, günlük zarar limiti aşılınca o gün yeni işlem yok."""
    if tr.empty:
        return tr
    tr = tr[tr["reason"] != "bekleyen"]
    # Aynı anda birden çok sinyal varsa önce en güçlüsü (skor: göreceli güç; Christensen
    # "hareketteki hisse" seçimi), yoksa strateji sırası.
    if "skor" in tr.columns:
        tr = tr.sort_values(["entry_time", "skor"], ascending=[True, False])
    else:
        tr = tr.sort_values(["entry_time", "strategy"])
    tr = tr.reset_index(drop=True)
    ozs = float(c["sermaye"])
    acik, alinan = [], []
    gun_bas, gun_pnl = {}, {}

    def gerceklestir(t):
        nonlocal ozs
        for x in sorted([x for x in acik if x["exit_time"] <= t and x["reason"] != "acik"],
                        key=lambda x: x["exit_time"]):
            ozs += x["kar_usd"]
            d = x["exit_time"].date()
            gun_pnl[d] = gun_pnl.get(d, 0.0) + x["kar_usd"]
            acik.remove(x)

    for _, r in tr.iterrows():
        gerceklestir(r["entry_time"])
        d = r["entry_time"].date()
        gun_bas.setdefault(d, ozs)
        if gun_pnl.get(d, 0.0) <= c["gunluk_zarar_limiti"] * gun_bas[d]:
            continue
        if len(acik) >= c["max_pozisyon"] or any(x["symbol"] == r["symbol"] for x in acik):
            continue
        stop_pct = r["risk"] / r["entry"]
        w = min(c["risk"] / stop_pct, c["max_agirlik"])
        toplam = sum(x["agirlik_usd"] for x in acik) / ozs
        w = min(w, c["max_toplam_agirlik"] - toplam)
        if w <= 0.01:
            continue
        tutar = w * ozs
        kar = tutar * r["R"] * stop_pct
        x = {**r.to_dict(), "agirlik": w, "agirlik_usd": tutar, "kar_usd": kar,
             "ozs_giris": ozs}
        acik.append(x)
        alinan.append(x)
    return pd.DataFrame(alinan)


def portfoy_ayri(tr: pd.DataFrame, c: dict) -> pd.DataFrame:
    """ayri_hesap=True: her strateji sermayenin ve pozisyon hakkının eşit payıyla kendi alt
    hesabında çalışır (stratejiler aynı coinde birbirinin yerini kapmaz)."""
    if tr.empty or not c.get("ayri_hesap"):
        return portfoy(tr, c)
    st = sorted(tr["strategy"].unique())
    parts = [portfoy(tr[tr["strategy"] == s_], dict(c, sermaye=c["sermaye"] / len(st),
                                                       max_pozisyon=max(1, c["max_pozisyon"] // len(st))))
             for s_ in st]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def egri(al: pd.DataFrame, bas, bitis, sermaye) -> pd.Series:
    idx = pd.date_range(bas.floor("h"), bitis.floor("h"), freq="h")
    deger = pd.Series(sermaye, index=idx, dtype=float)
    for _, x in al.iterrows():
        if x["reason"] == "acik":
            deger.iloc[-1] += x["kar_usd"]  # açık pozisyon son kapanıştan (çıkış maliyeti dahil)
        else:
            deger[deger.index >= x["exit_time"].floor("h")] += x["kar_usd"]
    return deger


def _f(x, fmt):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else format(x, fmt)


def istat(df):
    if df is None or len(df) == 0:
        return dict(islem=0, kazanma=None, ort_R=None, pf=None)
    r = df["R"].to_numpy()
    gl = -r[r <= 0].sum()
    return dict(islem=len(r), kazanma=float((r > 0).mean()), ort_R=float(r.mean()),
                pf=float(r[r > 0].sum() / gl) if gl > 0 else None)


def calistir_kagit(dizin, veri=True):
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    c, bas, son, surumler = ayar()
    eski = json.loads((dizin / "durum.json").read_text()) if (dizin / "durum.json").exists() else {}
    simdi = pd.Timestamp.now(tz="UTC")
    insts = evren(dizin)
    if veri:
        veri_guncelle(insts, c["giris_tf"], bas)
    tr, son_veri = islemleri_uret(insts, c["giris_tf"], bas, son, surumler)
    al = portfoy_ayri(tr, c)
    kapali = al[al["reason"] != "acik"] if len(al) else al
    acik = al[al["reason"] == "acik"] if len(al) else al
    bekleyen = tr[tr["reason"] == "bekleyen"] if len(tr) else tr
    if len(bekleyen) and len(acik):
        bekleyen = bekleyen[~bekleyen["symbol"].isin(acik["symbol"])]
    sermaye = float(c["sermaye"])
    sv = max(son_veri.values()) if son_veri else simdi
    bitis = min(simdi, son)
    e = egri(al, bas, bitis, sermaye) if bitis > bas else pd.Series([sermaye], index=[bas])
    deger = float(e.iloc[-1])
    gerceklesen = sermaye + (float(kapali["kar_usd"].sum()) if len(kapali) else 0.0)
    dd = float((e / e.cummax() - 1).min())
    st = istat(kapali)
    strat = {}
    for k, kisa in KISA.items():
        s = istat(kapali[kapali["strategy"] == k] if len(kapali) else None)
        strat[kisa] = {**s, "acik": int((acik["strategy"] == k).sum()) if len(acik) else 0}
    sinif = {}
    for k in (c.get("siniflar") or ("crypto", "us_stock", "bist", "commodity")):
        s = istat(kapali[kapali["asset_class"] == k] if len(kapali) else None)
        sinif[k] = {**s, "kar_usd": round(float(kapali.loc[kapali["asset_class"] == k, "kar_usd"].sum()), 2)
                    if len(kapali) else 0.0}
    bitti = simdi >= son
    durum = dict(
        baslangic=str(bas), bitis=str(son), sermaye=sermaye, giris_tf=c["giris_tf"],
        guncelleme=simdi.strftime("%Y-%m-%d %H:%M UTC"), son_veri=str(sv),
        deger=round(deger, 2), getiri=round(deger / sermaye - 1, 5), gerceklesen=round(gerceklesen, 2),
        max_dusus=round(dd, 5), kapanan_islem=st["islem"], kazanma_orani=st["kazanma"],
        ort_R=st["ort_R"], pf=st["pf"], acik_pozisyon=len(acik), strateji=strat, sinif=sinif,
        parametre_surumu=len(surumler) - 1, enstruman=len(son_veri), beklenti=c["beklenti"],
        bitti=bool(bitti), son_rapor_gunu=eski.get("son_rapor_gunu"),
    )

    def satir(x, acik_mi=False):
        return dict(strateji=KISA[x["strategy"]], sembol=x["symbol"], sinif=x["asset_class"],
                    yon="AL" if x["dir"] == 1 else "SAT",
                    giris_zamani=x["entry_time"].strftime("%Y-%m-%d %H:%M"), giris="%.6g" % x["entry"],
                    stop="%.6g" % (x["entry"] - x["dir"] * x["risk"]),
                    tutar_usd=round(x["agirlik_usd"], 2),
                    cikis_zamani="" if acik_mi else x["exit_time"].strftime("%Y-%m-%d %H:%M"),
                    neden="açık" if acik_mi else x["reason"], kismi=bool(x["partial"]),
                    R=round(x["R"], 2), kar_usd=round(x["kar_usd"], 2))

    pd.DataFrame([satir(x) for _, x in kapali.iterrows()]).to_csv(dizin / "islemler.csv", index=False)
    pz = pd.DataFrame([satir(x, True) for _, x in acik.iterrows()])
    pz.to_csv(dizin / "pozisyonlar.csv", index=False)
    e.rename("deger").round(2).to_frame().rename_axis("zaman").to_csv(dizin / "ozsermaye.csv")
    bek = pd.DataFrame([dict(strateji=KISA[x["strategy"]], sembol=x["symbol"],
                             yon="AL" if x["dir"] == 1 else "SAT",
                             sinyal=x["entry_time"].strftime("%Y-%m-%d %H:%M"),
                             stop="%.6g" % (x["entry"] - x["dir"] * x["risk"]))
                        for _, x in bekleyen.iterrows()]) if len(bekleyen) and not bitti else pd.DataFrame()
    (dizin / "durum.json").write_text(json.dumps(durum, ensure_ascii=False, indent=2, default=float))
    oz = ozet_md(durum, kapali, pz, bek)
    (dizin / "ozet.md").write_text(oz)
    bugun = str(simdi.date())
    if simdi >= bas and (durum["son_rapor_gunu"] != bugun or (bitti and not eski.get("bitti"))):
        baslik = ("## Son değerlendirme (kağıt dönemi bitti)\n\n" if bitti
                  else f"## Günlük rapor — {bugun}\n\n")
        (dizin / "gunluk_rapor.md").write_text(baslik + oz.split("\n", 2)[2])
        durum["son_rapor_gunu"] = bugun
        (dizin / "durum.json").write_text(json.dumps(durum, ensure_ascii=False, indent=2, default=float))
    if bitti:
        (dizin / "BITTI").write_text(simdi.isoformat() + "\n")
    print(oz)


def ozet_md(d, kapali, pz, bek):
    baslik = "Hisse/emtia" if AYAR != KOK else "Kripto"
    sat = [f"# {baslik} day trade kağıt al-sat — {d['guncelleme']}", "",
           f"Dönem {d['baslangic'][:16]} → {d['bitis'][:16]} UTC · giriş {d['giris_tf']} · "
           f"{d['enstruman']} enstrüman · son veri {d['son_veri'][:16]} · gerçek para yoktur.", "",
           "| Değer | Getiri | Gerçekleşen | Maks. düşüş | Kapanan işlem | Kazanma | PF | Ort. R | Açık |",
           "|---|---|---|---|---|---|---|---|---|",
           f"| {d['deger']:,.0f} $ | {d['getiri']:+.2%} | {d['gerceklesen']:,.0f} $ | {d['max_dusus']:.1%} | "
           f"{d['kapanan_islem']} | {_f(d['kazanma_orani'], '.0%')} | {_f(d['pf'], '.2f')} | "
           f"{_f(d['ort_R'], '+.2f')} | {d['acik_pozisyon']} |", "",
           "| Strateji | Kapanan | Kazanma | PF | Ort. R | Açık |", "|---|---|---|---|---|---|"]
    for k, s in d["strateji"].items():
        sat.append(f"| {k} | {s['islem']} | {_f(s['kazanma'], '.0%')} | {_f(s['pf'], '.2f')} | "
                   f"{_f(s['ort_R'], '+.2f')} | {s['acik']} |")
    sat += ["", "| Sınıf | Kapanan | Kazanma | Kâr $ |", "|---|---|---|---|"]
    for k, s in d["sinif"].items():
        sat.append(f"| {k} | {s['islem']} | {_f(s['kazanma'], '.0%')} | {s['kar_usd']:+,.0f} |")
    b = d["beklenti"]
    if b.get("kazanma_orani"):
        sat += ["", f"Backtest beklentisi: kazanma ~%{b['kazanma_orani'] * 100:.0f}, ort. R "
                    f"{_f(b.get('ort_R'), '+.2f')}, 60 günde {b.get('60_gunde_islem')} işlem."]
    sat += ["", f"Parametre sürümü: {d['parametre_surumu']} (kagit/ayarlar.json)", "",
            "### Açık pozisyonlar", "", pz.to_markdown(index=False) if len(pz) else "_yok_",
            "", "### Bekleyen sinyaller (bir sonraki mum açılışında)", "",
            bek.to_markdown(index=False) if len(bek) else "_yok_", "", "### Son kapanan işlemler", ""]
    if len(kapali):
        k = kapali.sort_values("exit_time").tail(15)
        sat.append(pd.DataFrame([dict(strateji=KISA[x["strategy"]], sembol=x["symbol"],
                                      yon="AL" if x["dir"] == 1 else "SAT",
                                      giris=x["entry_time"].strftime("%m-%d %H:%M"),
                                      cikis=x["exit_time"].strftime("%m-%d %H:%M"), neden=x["reason"],
                                      R=round(x["R"], 2), kar_usd=round(x["kar_usd"], 2))
                                 for _, x in k.iterrows()]).to_markdown(index=False))
    else:
        sat.append("_henüz yok_")
    return "\n".join(sat) + "\n"


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--durum", required=True)
    a.add_argument("--veri-yok", action="store_true", help="veriyi güncelleme (önbellekle çalış)")
    x = a.parse_args()
    calistir_kagit(x.durum, veri=not x.veri_yok)
