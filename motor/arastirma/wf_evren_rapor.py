"""Evren stratejileri: seçim (aşama 5), kilit bilgisi (aşama 6) ve OZET.md. Yöntem: wf_evren modül belgesi (K-I, K-K)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import wf_evren as we

KILIT_ADLARI = {"K1_maliyet2_pf": "maliyet x2 PF", "K1b_maliyet3_pf": "maliyet x3 PF", "K1c_gecikme_pf": "1 mum gecikme PF",
                "K2_rastgele_p": "rastgele giriş p", "K3_boot_alt": "bootstrap alt sınır",
                "K4_komsu_param": "komşu ayarlar", "K5_dsr": "DSR", "hata": "hata"}


def _pbo_oku(cikti: Path) -> pd.DataFrame:
    yol = Path(cikti) / "pbo.csv"
    if not yol.exists():
        raise RuntimeError("pbo.csv yok: önce `pbo` aşamasını koşun (PBO kapısı atlanamaz)")
    return pd.read_csv(yol)


def secim_ve_ozet(cikti: Path = we.CIKTI) -> pd.DataFrame:
    """iyi/iyiye yakın listeleri (DSR + PBO dahil), stil başına <= 3 seçim ve liste mührü (holdout aşaması hash'i kontrol eder).
    Holdout bir kez başladıysa listeler değiştirilemez (HoldoutHatasi)."""
    from motor.arastirma import wf_evren_holdout as wh
    cikti = Path(cikti)
    if wh.holdout_baslamis_mi(cikti):
        raise wh.HoldoutHatasi("holdout başlatıldı: secim aşaması yeniden koşturulamaz")
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    sag = pd.read_parquet(cikti / "saglamlik.parquet") if (cikti / "saglamlik.parquet").exists() else pd.DataFrame()
    sec = pd.DataFrame()
    if len(sag):
        iyi, yakin = we.listeler(wf, sag, _pbo_oku(cikti))
        seriler = {}
        for r in iyi.to_dict("records"):
            if r["stil"] == "portfoy":              # portföy: OOS günlük getirisi (pf/<strateji>--gunluk.parquet)
                seriler[f"{r['strateji']}|{r['tf']}"] = pd.read_parquet(
                    cikti / "pf" / f"{r['strateji']}--gunluk.parquet")["oos_getiri"].astype(float)
                continue
            oos = pd.read_parquet(cikti / "oos" / f"{r['strateji']}--{r['tf']}.parquet")
            seriler[f"{r['strateji']}|{r['tf']}"] = we.yay_serisi(oos, pd.Timestamp(r["oos_bas"]), pd.Timestamp(r["oos_bit"]))
        sec = we.secim_yap(iyi, seriler) if seriler else pd.DataFrame()
        iyi.to_csv(cikti / "iyi_liste.csv", index=False)
        yakin.to_csv(cikti / "iyiye_yakin_liste.csv", index=False)
    sec.to_csv(cikti / "secim.csv", index=False)
    if len(sag):
        wh.muhur_yaz(cikti)
    return sec


def kilit_ve_ozet(cikti: Path = we.CIKTI, donem: str = "2020_bugun") -> None:
    cikti = Path(cikti)
    if donem != "kilit_oncesi":                     # GÜNCELLEME 3/5: eski kilit bilgisi aşaması yok (holdout aşaması var)
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


def _i(x) -> str:
    try:
        return "-" if x is None or x != x else str(int(x))
    except (TypeError, ValueError):
        return "-"


def _red(r) -> str:
    """Ö3: tek kasada reddedilen giriş sayıları (bilgi): toplam stop riski / kaldıraç / günlük limit / kill."""
    return "/".join(_i(r.get(k)) for k in ("red_toplam_risk", "red_kaldirac", "red_gunluk", "red_kill"))


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
    def _oku(ad):
        y = Path(cikti) / ad
        return pd.read_csv(y) if y.exists() and y.stat().st_size > 5 else pd.DataFrame()
    sec, kb = _oku("secim.csv"), _oku("kilit_bilgi.csv")
    L = ["# Evren stratejileri — özet (karar 27)", "",
         "Her strateji, tek bir ayarla evrenin TÜM enstrümanlarında birden çalışır; işlemler tek kasada birleşir "
         "(işlem başı %1 risk, toplam stop riski %5, 3x). Ayar, yürüyen pencerelerde yalnızca geçmiş verilerle seçilir. "
         "Ölçütler `ON_KAYIT.md`'deki gibidir; sonuç görüldükten sonra değiştirilmedi.",
         ("Geliştirme dönemi: en eski veri → 2025-11-07 (GÜNCELLEME 5). Son 12 ay (2025-11-08 → veri sonu) HOLDOUT'tur: "
          "ham/WF/sağlamlık/PBO/seçim aşamaları onu hiç görmedi; listeler dondurulduktan sonra bir kez koşuldu."
          if donem in we.GELISTIRME_DONEMLERI else
          "Test dönemi 2020-01-01 → veri sonu (GÜNCELLEME 3, eski); holdout yok." if donem == "2020_bugun"
          else "Dönem: kilit öncesi (< 2025-11-01); kilitli yıl yalnız bilgi."), ""]
    n_hata = int((wf["hata"].fillna("") != "").sum())
    L += ["## Sayılar", "",
          f"- Denenen (strateji × zaman dilimi): {len(wf)} (hatalı {n_hata})",
          f"- Yürüyen pencere (WF) ölçütlerini (1 ve 2) geçen: {int((wf['gecti'] == True).sum())}",   # noqa: E712
          f"- Sağlamlığı (K1 x2/x3/gecikme, K2, K3, K4, K5 DSR) geçen: {int((sag['saglam_mi'] == True).sum()) if len(sag) else 0}",    # noqa: E712
          f"- Seçilen: {len(sec)}",
          f"- Maliyet tablosu sha256: `{we.evren_maliyet.tablo_hash()[:16]}…` (sonuclar/evren/maliyet_tablosu.csv; koşulardan önce sabitlendi)",
          "- DSR (K5, GÜNCELLEME 6): N ve V her stil × tf grubunun TÜM aday ayarlarından (pbo.csv `dsr_n`, `dsr_v`); grup N: "
          + (", ".join(f"{a}/{b}={_i(n)}" for a, b, n in sorted({(x, y, z) for x, y, z in zip(sag['stil'], sag['tf'], sag['dsr_n_deneme'])}))
             if len(sag) and "dsr_n_deneme" in sag else "-")
          + ". Önceki denemelerle bilgi DSR'si `dsr_bilgi` (N="
          + (_i(sag['dsr_n_bilgi'].dropna().iloc[0]) if len(sag) and "dsr_n_bilgi" in sag and sag['dsr_n_bilgi'].notna().any() else "-")
          + "), eski sembol çarpanlı `dsr_sembol` — ikisi de kapı değil.",
          "- BIST (GÜNCELLEME 6): evrende koşulur ama genişlik kapılarında sayılmaz; `net_bist`, `bist_islem`, `bist_short_payi` bilgi.",
          "- Kill / günlük limit / red sayıları kapı değil, bilgi (listelerde ayrı sütun).", ""]
    for st in ("swing", "daytrade", "scalp", "portfoy"):
        g = wf[wf["stil"] == st]
        L.append(f"  - {st}: {len(g)} kombinasyon, WF geçen {int((g['gecti'] == True).sum())}")   # noqa: E712
    L += ["", "## Uyarılar", "",
          "- Evren bugünkü büyük şirket/coin listesiyle sabit: geçmişte küçükken büyüyenler bugün listede, düşenler yok "
          "(hayatta kalma yanlılığı, karar 10). Sonuçlar iyimser olabilir.",
          "- Dışarıda kalan: XMR, LEO (Binance vadelide yok), ABBV (veri yok), XU030 scalp (5m verisi yok). BIST'te WF için yeterli "
          "geçmişi olmayanlar `kisa_gecmis` sütununda.",
          "- BIST gün içi (1h) verisi yalnız 2023-12'den başlar: BIST daytrade KISA DÖNEM'dir (wf_evren.csv `bist_kisa_donem` sütunu). "
          "Analiz başlangıcının %75 sayımına bu kısa geçmişli BIST sembolleri katılmaz (sapma, K-C notu).",
          "- Spot vekil: kriptolarda perp öncesi dönem (2017-2019) spot veriyle doldurulur, funding yoktur; maliyet perp ile aynı "
          "varsayılır. Hangi sembolde nereye kadar spot olduğu `wf_evren.csv` `spot_vekil` sütununda.",
          "- Maliyet tablosu tahminî ve tutucudur (CFD spread'leri, BIST komisyonu); kesin olmayanlar tabloda `tutucu=evet`.",
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
        for st in ("swing", "daytrade", "scalp", "portfoy"):
            g = df[df["stil"] == st] if len(df) else pd.DataFrame()
            L += [f"### {baslik} — {st} ({len(g)})", ""]
            if len(g):
                L += ["| # | Strateji | TF | İşlem | PF | Sharpe | Düşüş | K2 p | DSR | PBO | Kill | Günlük lim. | Red (risk/kaldıraç/günlük/kill) | Kaçan |",
                      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
                for i, r in enumerate(g.to_dict("records"), 1):
                    kacan = r["nedenler"] if isinstance(r.get("nedenler"), str) and r["nedenler"] else ""
                    if isinstance(r.get("kapi_basarisiz"), str) and r["kapi_basarisiz"]:
                        kacan = (kacan + "; " if kacan else "") + "sağlamlık: " + ", ".join(
                            KILIT_ADLARI.get(x, x) for x in r["kapi_basarisiz"].split(";"))
                    if r.get("pbo_dusurdu") is True or str(r.get("pbo_dusurdu")) == "True":
                        kacan = (kacan + "; " if kacan else "") + "PBO > 0.5 (iyiden düştü)"
                    L.append(f"| {i} | {r['strateji']} | {r['tf']} | {int(r['islem_sayisi'])} | {_f(r['profit_factor'])} | "
                             f"{_f(r['sharpe'])} | {_p(r['max_dusus'])} | {_f(r.get('rnd_p'), 3)} | {_f(r.get('dsr_deneme'), 2)} | "
                             f"{_f(r.get('pbo'), 2)} | {_i(r.get('kill_olayi'))} | {_i(r.get('gunluk_limit_olayi'))} | "
                             f"{_red(r)} | {kacan} |")
                L.append("")
    pb = cikti / "pbo.csv"
    if pb.exists():
        pdf = pd.read_csv(pb)
        L += ["## PBO (CSCV, 16 blok) — stil × zaman dilimi", "",
              "Tüm aday ayarların OOS-dönem günlük getiri matrisiyle (tek-kasa limitleri uygulanmadan, yaklaşık). PBO > 0.5 olan "
              "gruptan çıkan 'iyi' strateji 'iyiye yakın'a düşer.", "",
              "| Stil | TF | Strateji | Aday sütun | PBO |", "|---|---|---|---|---|"]
        for r in pdf.to_dict("records"):
            L.append(f"| {r['stil']} | {r['tf']} | {int(r['n_strateji'])} | {int(r['n_aday'])} | {_f(r['pbo'], 2)} |")
        L.append("")
    hy = cikti / "holdout" / "holdout.csv"
    L += ["## Holdout (2025-11-08 → veri sonu; bir kerelik)", ""]
    if hy.exists() and hy.stat().st_size > 5:
        h = pd.read_csv(hy)
        L += ["Kapı: evren net > 0 ve PF ≥ 1.1. Ayar: WF'nin geliştirme dönemindeki son seçilen ayarı; holdout sonucuna göre "
              "ayar/eşik/liste değiştirilmedi.", "",
              f"Doğrulanmış: {int((h['durum'] == 'dogrulanmis').sum())} / {len(h)}", "",
              "| Liste | Strateji | TF | İşlem | Net | PF | Sharpe | Düşüş | Geliştirme PF | Durum |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in h.to_dict("records"):
            durum = {"dogrulanmis": "doğrulanmış", "hata": "HATA"}.get(r["durum"], "holdout'ta kaldı")
            L.append(f"| {r['liste']} | {r['strateji']} | {r['tf']} | {int(r.get('islem_sayisi') or 0)} | {_p(r.get('net_getiri'))} | "
                     f"{_f(r.get('profit_factor'))} | {_f(r.get('sharpe'))} | {_p(r.get('max_dusus'))} | "
                     f"{_f(r.get('gelistirme_pf'))} | {durum} |")
        L.append("")
        gl = we.Path(cikti) / "holdout" / "holdout_gunlugu.jsonl"
        if gl.exists():
            zor = [json.loads(x) for x in gl.read_text().splitlines() if x.strip() and json.loads(x).get("zorla")]
            if zor:
                L += [f"UYARI: holdout {len(zor)} kez ZORLA yeniden koşuldu (yöntem ihlali); gerekçeler günlükte.", ""]
    else:
        L += ["Henüz koşulmadı (listeler dondurulduktan sonra `holdout` aşaması).", ""]
    ajanlar = {"swing": "Swing ajanı", "daytrade": "Day trade ajanı", "scalp": "Scalp ajanı", "portfoy": "Portföy ajanı"}
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
                  f"- Sağlamlık: maliyet x2 PF {_f(r['m2_pf'])}, x3 PF {_f(r.get('m3_pf'))}, 1 mum gecikme PF {_f(r.get('g1_pf'))}, "
                  f"DSR {_f(r.get('dsr_deneme'))}, PBO {_f(r.get('pbo'))}, rastgele giriş p {_f(r['rnd_p'], 3)}, "
                  f"bootstrap alt {_f(r['pf_boot_alt'])}, komşu ayar oranı {_p(r['par_oran'], 0)}",
                  f"- Limit olayları (BİLGİ, kapı değil): kill {_i(r.get('kill_olayi'))}, günlük limit {_i(r.get('gunluk_limit_olayi'))}, "
                  f"reddedilen giriş (risk/kaldıraç/günlük/kill) {_red(r)}, kırpılan {_i(r.get('kirpilan'))}",
                  f"- BIST (BİLGİ, genişlik kapısında sayılmaz): net {_p(r.get('net_bist'))}, işlem {_i(r.get('bist_islem'))}, "
                  f"short payı {_p(r.get('bist_short_payi'), 0)}; bilgi DSR (önceki denemelerle) {_f(r.get('dsr_bilgi'))}",
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
