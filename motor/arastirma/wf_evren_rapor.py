"""Evren stratejileri: seçim (aşama 5), kilit bilgisi (aşama 6) ve OZET.md. Yöntem: wf_evren modül belgesi (K-I, K-K)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import wf_evren as we

KILIT_ADLARI = {"K1_maliyet2_pf": "maliyet x2 PF", "K2_rastgele_p": "rastgele giriş p", "K3_boot_alt": "bootstrap alt sınır",
                "K4_komsu_param": "komşu ayarlar", "hata": "hata"}


def secim_ve_ozet(cikti: Path = we.CIKTI) -> pd.DataFrame:
    cikti = Path(cikti)
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    sag = pd.read_parquet(cikti / "saglamlik.parquet") if (cikti / "saglamlik.parquet").exists() else pd.DataFrame()
    if not len(sag):
        sec = pd.DataFrame()
    else:
        gecen = sag[sag["saglam_mi"] == True]                                  # noqa: E712
        seriler = {}
        for r in wf.merge(gecen[["strateji", "tf"]], on=["strateji", "tf"]).to_dict("records"):
            oos = pd.read_parquet(cikti / "oos" / f"{r['strateji']}--{r['tf']}.parquet")
            seriler[f"{r['strateji']}|{r['tf']}"] = we.yay_serisi(oos, pd.Timestamp(r["oos_bas"]), pd.Timestamp(r["oos_bit"]))
        sec = we.secim_yap(wf, sag, seriler) if seriler else pd.DataFrame()
    sec.to_csv(cikti / "secim.csv", index=False)
    if len(sag):
        listeleri_yaz(cikti)
    return sec


def listeleri_yaz(cikti: Path = we.CIKTI):
    cikti = Path(cikti)
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    sag = pd.read_parquet(cikti / "saglamlik.parquet") if (cikti / "saglamlik.parquet").exists() else pd.DataFrame()
    iyi, yakin = we.listeler(wf, sag)
    iyi.to_csv(cikti / "iyi_liste.csv", index=False)
    yakin.to_csv(cikti / "iyiye_yakin_liste.csv", index=False)
    return iyi, yakin


def kilit_ve_ozet(cikti: Path = we.CIKTI, donem: str = "2020_bugun") -> None:
    cikti = Path(cikti)
    if donem == "2020_bugun":                       # GÜNCELLEME 3: kilit ayrımı yok, ayrı kilit bilgisi üretilmez
        pd.DataFrame().to_csv(cikti / "kilit_bilgi.csv", index=False)
        ozet_yaz(cikti, donem)
        return
    sec = pd.read_csv(cikti / "secim.csv") if (cikti / "secim.csv").exists() and (cikti / "secim.csv").stat().st_size > 5 else pd.DataFrame()
    if len(sec):
        we._kilit_asamasi(cikti)
    else:
        pd.DataFrame().to_csv(cikti / "kilit_bilgi.csv", index=False)
    ozet_yaz(cikti, donem)


def _f(x, d=2):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def _p(x, d=1):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.{d}f}%"


def _enstruman_tablosu(r) -> str:
    adet = json.loads(r["enstruman_adet"])
    net = json.loads(r["enstruman_net"])
    satir = ["| Enstrüman | Sınıf | İşlem | Net (kasanın %'si) |", "|---|---|---|---|"]
    for s in sorted(net, key=lambda k: -net[k]):
        satir.append(f"| {s} | {we.SINIF.get(s, '?')} | {adet.get(s, 0)} | {100 * net[s]:.1f}% |")
    return "\n".join(satir)


def ozet_yaz(cikti: Path, donem: str = "2020_bugun") -> None:
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    sag = pd.read_parquet(cikti / "saglamlik.parquet") if (cikti / "saglamlik.parquet").exists() else pd.DataFrame()
    sec = pd.read_csv(cikti / "secim.csv") if (cikti / "secim.csv").stat().st_size > 5 else pd.DataFrame()
    kb = pd.read_csv(cikti / "kilit_bilgi.csv") if (cikti / "kilit_bilgi.csv").stat().st_size > 5 else pd.DataFrame()
    L = ["# Evren stratejileri — özet (karar 27)", "",
         "Her strateji, tek bir ayarla evrenin TÜM enstrümanlarında birden çalışır; işlemler tek kasada birleşir "
         "(işlem başı %1 risk, toplam stop riski %5, 3x). Ayar, yürüyen pencerelerde yalnızca geçmiş verilerle seçilir. "
         "Ölçütler `ON_KAYIT.md`'deki gibidir; sonuç görüldükten sonra değiştirilmedi.",
         ("Test dönemi 2020-01-01 → veri sonu (GÜNCELLEME 3); ayrı kilitli dönem yok, bağımsız son sınav paper trading'dir."
          if donem == "2020_bugun" else "Dönem: kilit öncesi (< 2025-11-01); kilitli yıl yalnız bilgi."), ""]
    n_hata = int((wf["hata"].fillna("") != "").sum())
    L += ["## Sayılar", "",
          f"- Denenen (strateji × zaman dilimi): {len(wf)} (hatalı {n_hata})",
          f"- Yürüyen pencere (WF) ölçütlerini (1 ve 2) geçen: {int((wf['gecti'] == True).sum())}",   # noqa: E712
          f"- Sağlamlığı (K1–K4) geçen: {int((sag['saglam_mi'] == True).sum()) if len(sag) else 0}",    # noqa: E712
          f"- Seçilen: {len(sec)}", ""]
    for st in ("swing", "daytrade", "scalp"):
        g = wf[wf["stil"] == st]
        L.append(f"  - {st}: {len(g)} kombinasyon, WF geçen {int((g['gecti'] == True).sum())}")   # noqa: E712
    L += ["", "## Uyarılar", "",
          "- Evren bugünkü büyük şirket/coin listesiyle sabit: geçmişte küçükken büyüyenler bugün listede, düşenler yok "
          "(hayatta kalma yanlılığı, karar 10). Sonuçlar iyimser olabilir.",
          "- Dışarıda kalan: XMR, LEO (BIST'te WF için yeterli geçmişi olmayanlar `kisa_gecmis` sütununda) (Binance vadeli işlemlerinde yok). Verisi gelmeyen / bir zaman diliminde verisi olmayan "
          "enstrümanlar aşağıda her satırda 'dışarıda' sütununda.",
          "- Hiçbir ölçüt sonuç görülerek değiştirilmedi. Çok sayıda deneme yapıldığı için 'şans' payı vardır; "
          "DSR değerleri `saglamlik.csv`'de. Not: 20% kill switch çok yıllık OOS'ta kalıcı durdurur; maliyet x2 testinde bu tetiklenirse işlem sayısı düşer (`m2_kill_olayi`).", ""]
    ly = cikti / "iyi_liste.csv"
    iyi = pd.read_csv(ly) if ly.exists() and ly.stat().st_size > 5 else pd.DataFrame()
    yk = cikti / "iyiye_yakin_liste.csv"
    yakin = pd.read_csv(yk) if yk.exists() and yk.stat().st_size > 5 else pd.DataFrame()
    L += ["## Stil bazında sıralı listeler (strateji düzeyi; enstrüman sıralaması yok)", "",
          "İyi = tüm ölçütler (WF + sağlamlık). İyiye yakın = en çok bir ölçütü kıl payı kaçıran (PF ≥ 1.1, Sharpe ≥ 0.4, "
          "düşüş ≤ %25; sağlamlıkta en çok bir kontrol kalan) — geliştirme adayıdır. Sıra: Sharpe × (1 − rastgele giriş p).", ""]
    for baslik, df in (("İyi", iyi), ("İyiye yakın", yakin)):
        for st in ("swing", "daytrade", "scalp"):
            g = df[df["stil"] == st] if len(df) else pd.DataFrame()
            L += [f"### {baslik} — {st} ({len(g)})", ""]
            if len(g):
                L += ["| # | Strateji | TF | İşlem | PF | Sharpe | Düşüş | Kaçan |", "|---|---|---|---|---|---|---|---|"]
                for i, r in enumerate(g.to_dict("records"), 1):
                    kacan = r["nedenler"] if isinstance(r.get("nedenler"), str) and r["nedenler"] else ""
                    if isinstance(r.get("kapi_basarisiz"), str) and r["kapi_basarisiz"]:
                        kacan = (kacan + "; " if kacan else "") + "sağlamlık: " + ", ".join(
                            KILIT_ADLARI.get(x, x) for x in r["kapi_basarisiz"].split(";"))
                    L.append(f"| {i} | {r['strateji']} | {r['tf']} | {int(r['islem_sayisi'])} | {_f(r['profit_factor'])} | "
                             f"{_f(r['sharpe'])} | {_p(r['max_dusus'])} | {kacan} |")
                L.append("")
    ajanlar = {"swing": "Swing ajanı", "daytrade": "Day trade ajanı", "scalp": "Scalp ajanı"}
    for st, baslik in ajanlar.items():
        L += [f"## {baslik}", ""]
        s = sec[sec["ajan"] == st] if len(sec) else pd.DataFrame()
        if not len(s):
            L += ["Geçen strateji yok; bu ajan boş kalır (zorlama yok).", ""]
        for r in s.to_dict("records"):
            L += [f"### {int(r['sira'])}. {r['strateji']} — {r['tf']}", "",
                  f"- Ayar (en sık seçilen): `{r['en_sik_ayar']}`; {int(r['n_farkli_ayar'])} farklı ayar seçildi",
                  f"- Test dönemi (OOS): {str(r['oos_bas'])[:10]} → {str(r['oos_bit'])[:10]}; "
                  f"{int(r['n_enstruman'])}/{int(r['n_enstruman_evren'])} enstrümanda veri",
                  f"- İşlem {int(r['islem_sayisi'])}, net {_p(r['net_getiri'])}, PF {_f(r['profit_factor'])}, "
                  f"Sharpe {_f(r['sharpe'])}, max düşüş {_p(r['max_dusus'])}",
                  f"- Sağlamlık: maliyet x2 PF {_f(r['m2_pf'])}, rastgele giriş p {_f(r['rnd_p'], 3)}, "
                  f"bootstrap alt {_f(r['pf_boot_alt'])}, komşu ayar oranı {_p(r['par_oran'], 0)}",
                  f"- Kârlı enstrüman oranı {_p(r['enstruman_kar_orani'], 0)}, en büyük enstrümanın kâr payı "
                  f"{_p(r['tek_enstruman_pay'], 0)} ({r['en_buyuk_enstruman']})", "", _enstruman_tablosu(r), ""]
            if len(kb):
                k = kb[(kb["strateji"] == r["strateji"]) & (kb["tf"] == r["tf"])]
                if len(k):
                    k = k.iloc[0]
                    L += [f"Kilitli dönem (BİLGİ, seçimde kullanılmadı; ayar `{k.get('ayar', '')}`): "
                          f"işlem {int(k.get('islem_sayisi', 0) or 0)}, net {_p(k.get('net_getiri', math.nan))}, "
                          f"PF {_f(k.get('profit_factor', math.nan))}, Sharpe {_f(k.get('sharpe', math.nan))}, "
                          f"düşüş {_p(k.get('max_dusus', math.nan))}", ""]
        # en yakın 10 geçemeyen
        d = wf[(wf["stil"] == st) & (wf["hata"].fillna("") == "") & (wf["islem_sayisi"].fillna(0) > 0)].copy()
        if len(sag):
            d = d.merge(sag[["strateji", "tf", "saglam_mi", "kapi_basarisiz"]], on=["strateji", "tf"], how="left")
        else:
            d["saglam_mi"], d["kapi_basarisiz"] = np.nan, ""
        secili = set(zip(s["strateji"], s["tf"])) if len(s) else set()
        d = d[pd.Series([(a, t) not in secili for a, t in zip(d["strateji"], d["tf"])], index=d.index, dtype=bool)]
        if "kapi_basarisiz" not in d:
            d["saglam_mi"], d["kapi_basarisiz"] = np.nan, ""
        if len(d):
            kapi_say = d["kapi_basarisiz"].fillna("").map(lambda x: len([y for y in str(x).split(";") if y])).astype(int)
            d["_kacan"] = d["basarisiz_sayi"].fillna(99).astype(float) + kapi_say
            d = d.sort_values(["_kacan", "sharpe"], ascending=[True, False]).head(10)
        L += [f"### {baslik}: geçemeyenlerin en yakın 10'u", ""]
        if len(d):
            L += ["| Strateji | TF | İşlem | PF | Sharpe | Düşüş | Neden kaldı |", "|---|---|---|---|---|---|---|"]
            for r in d.to_dict("records"):
                neden = r["nedenler"] if isinstance(r["nedenler"], str) and r["nedenler"] else ""
                kp = r.get("kapi_basarisiz")
                if isinstance(kp, str) and kp:
                    neden = (neden + "; " if neden else "") + "sağlamlık: " + ", ".join(KILIT_ADLARI.get(x, x) for x in kp.split(";"))
                elif r.get("saglam_mi") == True and not neden:                  # noqa: E712
                    neden = "korelasyon/üst sınır nedeniyle seçilmedi"
                L.append(f"| {r['strateji']} | {r['tf']} | {int(r['islem_sayisi'])} | {_f(r['profit_factor'])} | "
                         f"{_f(r['sharpe'])} | {_p(r['max_dusus'])} | {neden} |")
        else:
            L.append("Kayıt yok.")
        L.append("")
    (cikti / "OZET.md").write_text("\n".join(L), encoding="utf-8")
