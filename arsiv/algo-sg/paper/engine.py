"""Kağıt al-sat motoru (A: trend kırılımı A1+A2, B: kapitülasyon dönüşü; 10.000$ sanal).

Çalışma biçimi: her çalıştırmada kağıt dönemi başlangıcından bugüne kadar olan KAPANMIŞ mumlar,
backtest ile BİREBİR aynı kod (algo.strategies, algo.backtest, algo.portfolio) ile yeniden oynatılır.
Kararlar yalnızca kapanmış mumlara dayandığı için (ileriye bakma yok) sonuçlar, botun her saat
açık olmasıyla aynıdır; çalıştırma sıklığı yalnızca raporun güncelliğini etkiler.

Kullanım:  ALGO_LIVE=<durum>/live python -m paper.engine --durum <durum_klasoru>
"""
import argparse
import json
import os
import shutil
import sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.environ.get("PAPER_CFG") or os.path.join(ROOT, "paper", "config.json")))


def _features():
    from concurrent.futures import ProcessPoolExecutor
    from algo import features as F, data as D
    shutil.rmtree(F.CACHE, ignore_errors=True)  # canlı modda her çalıştırmada taze özellik
    F.build("BTCUSDT")
    syms = D.symbols()
    with ProcessPoolExecutor(4) as ex:
        feats = dict(zip(syms, ex.map(F.build, syms)))
    return feats


def _run_modules(feats, start, end):
    from algo.final import MODULES
    from algo.strategies import STRATS
    from algo import backtest as B
    out = {}
    for m, (fn, p) in MODULES.items():
        res = []
        for s, f in feats.items():
            f = f[f.index < end]
            if len(f) < 500:
                continue
            kw = STRATS[fn](f, p)
            side = np.asarray(kw["side"], dtype=float).copy()
            side[f.index < start] = 0  # kağıt dönemi öncesinde pozisyon yok
            kw["side"] = side
            t = B.simulate(f, funding=f["funding"].values, **kw)
            if len(t):
                t["sym"] = s; t["module"] = m
                res.append(t)
        out[m] = pd.concat(res, ignore_index=True) if res else pd.DataFrame()
    return out


def _mtm_usd(taken, feats, idx, end):
    """Saatlik öz sermaye değişimi ($): açık pozisyonlar son kapanışla değerlenir (kısmi kârlar yaklaşık)."""
    pnl = pd.Series(0.0, index=idx)
    for r in taken.itertuples():
        f = feats[r.sym]
        c = f["close"][f.index < end]
        e, x = int(r.entry_i), int(r.exit_i)
        usd_per_R = r.eq_entry * r.risk * (r.notional_frac / (r.risk / r.sl_pct))
        if r.is_open:
            path = c.iloc[e:].copy()
            vals = r.side * (path - r.entry) / (r.sl_pct * r.entry) * usd_per_R
            vals.iloc[-1] = r.pnl_usd
        else:
            path = c.iloc[e:x].copy()
            vals = r.side * (path - r.entry) / (r.sl_pct * r.entry) * usd_per_R
            vals = pd.concat([vals, pd.Series([r.pnl_usd], index=[c.index[min(x, len(c) - 1)] if x < len(c) else c.index[-1]])])
            vals = vals[~vals.index.duplicated(keep="last")]
        s = vals.reindex(idx).ffill()
        if not r.is_open:
            s = s.fillna(0.0) if s.first_valid_index() is None else s
        pnl = pnl.add(s.fillna(0.0), fill_value=0.0)
    return pnl


def _stats(closed):
    if len(closed) == 0:
        return dict(islem=0, kazanma=None, pf=None, ort_R=None, kar_usd=0.0)
    w = closed.R > 0
    gl = -closed.R[~w].sum()
    return dict(islem=int(len(closed)), kazanma=round(float(w.mean()) * 100, 1),
                pf=round(float(closed.R[w].sum() / gl), 2) if gl > 0 else None,
                ort_R=round(float(closed.R.mean()), 3), kar_usd=round(float(closed.pnl_usd.sum()), 2))


def _expected():
    p = os.path.join(ROOT, "results", "final_summary.json")
    if not os.path.exists(p):
        return {}
    s = json.load(open(p))
    out = {}
    for k in ("A", "B"):
        tl = s[k]["trade_level"]["ALL"]
        months = 81  # 2020-01 .. 2026-10
        out[k] = dict(kazanma=tl["win_rate"], pf=tl["pf"], ayda_islem=round(tl["trades"] / months, 1))
    return out


def main(state_dir):
    from algo.final import SLEEVES
    from algo.portfolio import simulate_portfolio
    os.makedirs(state_dir, exist_ok=True)
    start = pd.Timestamp(CFG["start"])
    end = start + pd.Timedelta(days=CFG["days"])
    feats = _features()
    last_bar = feats["BTCUSDT"].index[-1]
    finished = last_bar + pd.Timedelta("1h") >= end
    stale = sorted(s for s, f in feats.items() if f.index[-1] < last_bar - pd.Timedelta("2h"))
    if last_bar < start:
        print("Kağıt dönemi henüz başlamadı:", start); return
    mods = _run_modules(feats, start, end)
    idx = pd.date_range(start, min(last_bar, end - pd.Timedelta("1h")), freq="1h")
    summary, all_taken, eq_curves = {}, [], {}
    for name, sl in SLEEVES.items():
        cap = CFG["capital"] * CFG["sleeve_weights"][name]
        t = pd.concat([mods[m] for m in sl["modules"] if len(mods[m])], ignore_index=True) if any(len(mods[m]) for m in sl["modules"]) else pd.DataFrame()
        if len(t) == 0:
            eq_curves[name] = pd.Series(cap, index=idx); summary[name] = dict(sermaye=cap, **_stats(t)); continue
        _, taken = simulate_portfolio(t, risk=sl["risk"], max_open=sl["max_open"], start_equity=cap)
        taken = taken.assign(sleeve=name, risk=sl["risk"])
        all_taken.append(taken)
        eq_curves[name] = cap + _mtm_usd(taken, feats, idx, end)
        closed = taken[~taken.is_open]; op = taken[taken.is_open]
        summary[name] = dict(baslangic=cap, sermaye=round(float(eq_curves[name].iloc[-1]), 2),
                             gerceklesen_usd=round(float(closed.pnl_usd.sum()), 2), acik_kz_usd=round(float(op.pnl_usd.sum()), 2),
                             acik_pozisyon=int(len(op)), **{"kapali_" + k: v for k, v in _stats(closed).items()})
    taken = pd.concat(all_taken, ignore_index=True) if all_taken else pd.DataFrame()
    eq = pd.DataFrame(eq_curves); eq["TOPLAM"] = eq.sum(axis=1)
    dd = (eq["TOPLAM"] / eq["TOPLAM"].cummax() - 1).min()
    total = dict(baslangic=CFG["capital"], sermaye=round(float(eq["TOPLAM"].iloc[-1]), 2),
                 getiri_yuzde=round(float(eq["TOPLAM"].iloc[-1] / CFG["capital"] - 1) * 100, 2),
                 maks_dusus_yuzde=round(float(dd) * 100, 2))
    # --- kayıtlar
    def tid(r): return f"{r.module}-{r.sym}-{pd.Timestamp(r.entry_time):%Y%m%d%H}"
    prev = json.load(open(os.path.join(state_dir, "durum.json"))) if os.path.exists(os.path.join(state_dir, "durum.json")) else {}
    prev_open, prev_closed = set(prev.get("acik_idler", [])), set(prev.get("kapali_idler", []))
    if len(taken):
        taken["id"] = [tid(r) for r in taken.itertuples()]
        taken["reason_kod"] = taken["reason"].astype(int)
        taken["reason"] = [_neden(r) for r in taken.itertuples()]
        taken["yon"] = np.where(taken.side > 0, "LONG", "SHORT")
        taken["pozisyon_usd"] = (taken.eq_entry * taken.notional_frac).round(2)
    op = taken[taken.is_open] if len(taken) else taken
    cl = taken[~taken.is_open] if len(taken) else taken
    new_open = [i for i in (op.id if len(op) else []) if i not in prev_open and i not in prev_closed]
    new_closed = [i for i in (cl.id if len(cl) else []) if i not in prev_closed]
    cols_o = ["id", "sleeve", "module", "sym", "yon", "entry_time", "entry", "stop", "remaining", "pozisyon_usd", "R", "pnl_usd"]
    cols_c = ["id", "sleeve", "module", "sym", "yon", "entry_time", "entry", "exit_time", "exit_px", "reason", "reason_kod", "R", "pnl_usd", "pozisyon_usd"]
    (op[cols_o] if len(op) else pd.DataFrame(columns=cols_o)).to_csv(os.path.join(state_dir, "pozisyonlar.csv"), index=False)
    # islemler.csv: kısmi kâr alımları ayrı satır; ana satır kalan kısmın R ve $ sonucunu taşır (toplam = işlemin toplamı)
    cols_i = cols_c + ["kisim", "miktar", "tutar_usd"]
    if len(taken):
        kis, ayir = _kismi_cikislar(taken, feats, end)
        ana = cl.copy()
        ana["kisim"] = [1 - ayir[i][2] if i in ayir else 1.0 for i in ana.id]
        ana["R"] = [r.R - ayir[r.id][0] if r.id in ayir else r.R for r in ana.itertuples()]
        ana["pnl_usd"] = [r.pnl_usd - ayir[r.id][1] if r.id in ayir else r.pnl_usd for r in ana.itertuples()]
        ana["miktar"] = ana.pozisyon_usd * ana.kisim / ana.entry
        ana["tutar_usd"] = (ana.pozisyon_usd * ana.kisim).round(2)
        isl = pd.concat([ana[cols_i], kis[cols_i] if len(kis) else pd.DataFrame(columns=cols_i)], ignore_index=True)
        isl = isl.sort_values(["exit_time", "id"]) if len(isl) else isl
    else:
        isl = pd.DataFrame(columns=cols_i)
    isl.to_csv(os.path.join(state_dir, "islemler.csv"), index=False)
    eq.round(2).to_csv(os.path.join(state_dir, "ozsermaye.csv"), index_label="saat")
    exp = _expected()
    durum = dict(son_mum=str(last_bar), baslangic=str(start), bitis=str(end), bitti=bool(finished), toplam=total,
                 kollar=summary, beklenen_backtest=exp, eski_veri=stale,
                 acik_idler=list(op.id) if len(op) else [], kapali_idler=list(cl.id) if len(cl) else [],
                 son_rapor_gunu=prev.get("son_rapor_gunu"))
    # --- günlük rapor (her tamamlanan UTC günü için bir kez)
    day_done = (last_bar + pd.Timedelta("1h")).normalize() - pd.Timedelta("1D")
    if (prev.get("son_rapor_gunu") is None and day_done >= start.normalize()) or \
       (prev.get("son_rapor_gunu") and pd.Timestamp(prev["son_rapor_gunu"]).date() < day_done.date()) or (finished and not prev.get("bitti")):
        rep = _report(durum, op, cl, eq, title_day=day_done, final=finished)
        open(os.path.join(state_dir, "gunluk_rapor.md"), "w").write(rep)
        durum["son_rapor_gunu"] = str(day_done.date())
    json.dump(durum, open(os.path.join(state_dir, "durum.json"), "w"), indent=1, default=str)
    open(os.path.join(state_dir, "ozet.md"), "w").write(_report(durum, op, cl, eq, new_open=new_open, new_closed=new_closed, final=finished))
    print(f"son mum {last_bar} | sermaye {total['sermaye']} | getiri %{total['getiri_yuzde']} | açık {len(op)} | yeni açılan {len(new_open)} | yeni kapanan {len(new_closed)}")


def _kismi_cikislar(taken, feats, end):
    """Simülatörün tp1 kısmi kâr alımını (A1/A2: 1R'de %25) aynı kuralla yeniden bulur ve ayrı kayıt üretir.
    Simülatör kısmi çıkışı yalnız toplam R içinde tutar; burada mum, fiyat ve tutar ayrıştırılır. Strateji değişmez.
    Döner: (kısmi satırlar, {id: (kısmi_R, kısmi_usd)})."""
    from algo.final import MODULES
    rows, ayir = [], {}
    for r in taken.itertuples():
        p = MODULES.get(r.module, (None, {}))[1]
        frac, t1R = p.get("tp1_frac", 0.0), p.get("tp1_R", 1.0)
        if frac <= 0:
            continue
        f = feats[r.sym]; f = f[f.index < end]
        o, h, l = f["open"].values, f["high"].values, f["low"].values
        e, x, k = int(r.entry_i), int(r.exit_i), int(r.reason_kod)
        son = x if k in (4, 5) else x - 1  # 1: çıkış mumunda önce stop; 3: çıkış mumunun açılışında kapandı
        risk = r.sl_pct * r.entry
        t1 = r.entry + r.side * risk * t1R
        for j in range(e, min(son, len(o) - 1) + 1):
            if (r.side > 0 and h[j] >= t1) or (r.side < 0 and l[j] <= t1):
                px = max(t1, o[j]) if r.side > 0 else min(t1, o[j])
                pR = frac * r.side * (px - r.entry) / risk
                usd_per_R = r.eq_entry * r.risk * (r.notional_frac / (r.risk / r.sl_pct))
                pusd = pR * usd_per_R
                ayir[r.id] = (pR, pusd, frac)
                rows.append(dict(id=f"{r.id}-K", sleeve=r.sleeve, module=r.module, sym=r.sym, yon=r.yon, entry_time=r.entry_time,
                                 entry=r.entry, exit_time=f.index[j], exit_px=px, reason="partial", reason_kod=0, R=pR, pnl_usd=pusd,
                                 pozisyon_usd=r.pozisyon_usd, kisim=frac, miktar=r.pozisyon_usd * frac / r.entry,
                                 tutar_usd=round(r.pozisyon_usd * frac, 2)))
                break
    return pd.DataFrame(rows), ayir


REASON = {"partial": "kısmi kâr (%25)", "stop": "stop", "be_stop": "başabaş stop", "trail": "iz süren stop", "tp": "hedef", "ema_exit": "EMA çıkışı",
          "time": "süre doldu", "exit_signal": "çıkış sinyali (sonraki açılış)", "open": "açık"}


def _neden(r):
    """Simülatörün sayısal çıkış kodunu (1 stop, 2 hedef, 3 çıkış kuralı/süre, 4 açık, 5 sonraki açılışta çıkış)
    okunur metne çevirir. Stop türü, çıkıştaki stop seviyesinin girişe göre konumundan; kural/süre ayrımı,
    işlem süresinin modülün en uzun tutma süresine ulaşıp ulaşmadığından çıkarılır. Strateji mantığını değiştirmez."""
    from algo.final import MODULES
    k = int(r.reason)
    if k == 1:
        from algo.backtest import COST
        rel = r.side * (r.stop - r.entry) / r.entry
        return "stop" if rel < -1e-6 else ("be_stop" if rel <= 2 * COST + 1e-4 else "trail")  # başabaş = giriş + 2 x maliyet
    if k == 2:
        return "tp"
    if k == 3:
        mb = MODULES.get(r.module, (None, {}))[1].get("max_bars", 10**9)
        return "time" if int(r.exit_i) - int(r.entry_i) >= mb else "ema_exit"
    return {4: "open", 5: "exit_signal"}.get(k, str(k))


def _report(d, op, cl, eq, new_open=None, new_closed=None, title_day=None, final=False):
    L = []
    t = d["toplam"]
    head = "SON DEĞERLENDİRME" if final else (f"Günlük rapor — {title_day.date()}" if title_day is not None else "Anlık durum")
    L.append(f"# Kağıt al-sat (algo-sg: A trend + B kapitülasyon) — {head}\n")
    L.append(f"Son kapanmış mum: **{d['son_mum']}** · Dönem: {d['baslangic'][:10]} → {d['bitis'][:10]} · Gerçek para yoktur.\n")
    L.append(f"**Toplam:** {t['sermaye']:,.2f} $ (başlangıç {t['baslangic']:,} $) · getiri **%{t['getiri_yuzde']}** · en büyük düşüş %{t['maks_dusus_yuzde']}\n")
    L.append("| Kol | Sermaye $ | Gerçekleşen $ | Açık K/Z $ | Açık poz. | Kapanan işlem | Kazanma % | PF | Ort. R | Backtest beklentisi (kazanma / PF / ayda işlem) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for k, v in d["kollar"].items():
        e = d["beklenen_backtest"].get(k, {})
        L.append(f"| {k} | {v.get('sermaye', 0):,.2f} | {v.get('gerceklesen_usd', 0):,.2f} | {v.get('acik_kz_usd', 0):,.2f} | {v.get('acik_pozisyon', 0)} | "
                 f"{v.get('kapali_islem', 0)} | {v.get('kapali_kazanma') or '-'} | {v.get('kapali_pf') or '-'} | {v.get('kapali_ort_R') or '-'} | "
                 f"%{e.get('kazanma', '-')} / {e.get('pf', '-')} / {e.get('ayda_islem', '-')} |")
    if new_open is not None:
        L.append(f"\nSon çalıştırmada: **{len(new_open)} yeni pozisyon**, **{len(new_closed)} kapanan işlem**.")
    if d.get("eski_veri"):
        L.append(f"\n⚠️ Verisi 2 saatten eski semboller: {', '.join(d['eski_veri'])}")
    L.append("\n## Açık pozisyonlar\n")
    if len(op):
        L.append("| Kol | Modül | Coin | Yön | Giriş zamanı | Giriş | Güncel stop | Kalan | Pozisyon $ | K/Z $ |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in op.sort_values("entry_time").itertuples():
            L.append(f"| {r.sleeve} | {r.module} | {r.sym} | {r.yon} | {pd.Timestamp(r.entry_time):%Y-%m-%d %H:%M} | {r.entry:.6g} | {r.stop:.6g} | %{r.remaining*100:.0f} | {r.pozisyon_usd:,.0f} | {r.pnl_usd:,.2f} |")
    else:
        L.append("Açık pozisyon yok.")
    L.append("\n## Son 15 kapanan işlem\n")
    if len(cl):
        L.append("| Kol | Coin | Yön | Giriş | Çıkış | Sebep | R | K/Z $ |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in cl.sort_values("exit_time").tail(15).itertuples():
            L.append(f"| {r.sleeve} | {r.sym} | {r.yon} | {pd.Timestamp(r.entry_time):%m-%d %H:%M} @ {r.entry:.6g} | {pd.Timestamp(r.exit_time):%m-%d %H:%M} @ {r.exit_px:.6g} | {REASON.get(r.reason, r.reason)} | {r.R:+.2f} | {r.pnl_usd:+,.2f} |")
    else:
        L.append("Henüz kapanan işlem yok.")
    if final:
        L.append("\n## Değerlendirme ölçütleri (canlıya geçiş için)\n")
        L.append("- Kazanma oranı ve PF backtest beklentisine yakın mı (A: ~%50 / ~1.6, B: ~%64 / ~1.8)? 2 ayda işlem sayısı az olduğundan ±10 puan sapma normaldir.")
        L.append("- Toplam düşüş backtest'teki en kötü düşüşü (−%15) aşmadı mı?")
        L.append("- Veri kesintisi / eski veri uyarısı oldu mu?")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", required=True)
    a = ap.parse_args()
    main(a.durum)
