"""Paper v2 KABUL TESTİ: tekrar modu (--tekrar mantığı) holdout dönemi (2025-11-08 -> 2026-11-06) üzerinde 10 stratejiyi KENDİ KASASINDA koşturur ve
holdout net getirisiyle karşılaştırır (sonuclar/evren/v2/holdout/holdout.csv ve holdout_kesif/holdout_kesif.csv).

Her strateji için:
  - ref_net / ref_n_ham: holdout dosyalarındaki değerler (n_islem = hesap limitlerinden ÖNCEKİ ham işlem sayısı).
  - hold_yeniden_net: holdout kodunun aynı adımları BURADA yeniden koşulur (tek-sembol backtest + kasa.oynat) -> yerel verinin holdout verisiyle özdeş olduğunun kanıtı.
  - paper_net: PaperKasalar tekrar modu (canlı yolla aynı Paper.baslat / Paper.adim).
  - eşleşme: (sembol, giriş zamanı) anahtarıyla holdout-kabul edilen işlemler <-> paper işlemleri; eşleşenlerde R farkı.
  - teşhis (yalnız bu araç, ÜRETİM KODU DEĞİL): hesap limitleri iki tarafta da kaldırılarak (holdout: OynatmaAyari toplam_risk/kaldıraç/günlük/kill çok büyük;
    paper: motor.top_risk/kal örnek değişkenleri ve günlük/kill sabitleri YALNIZ çağrı süresince) işlem mekaniği karşılaştırılır. Sert limitler üretimde ASLA gevşetilmez; bu yalnız ölçüm.

Kilit: holdout dönemi verisi için mevcut onaylı yol (kilit_ac + gerekçe; sonuclar/kilit_acilis.jsonl'e yazılır).
Kullanım: PYTHONPATH=. python araclar/paper_v2_uyum.py [--kimlik AD ...] [--surec 4] [--onbellek-hazirla] [--teshis]
Çıktı: sonuclar/paper_v2/uyum/<strateji>.json ve uyum_raporu.md (tüm json'lardan derlenir).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from motor.backtest.motor import D
from motor.canli import paper_v2 as v2

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "sonuclar" / "paper_v2" / "uyum"
ONBELLEK = KOK / "sonuclar" / "paper_v2" / "onbellek"
HOLDOUT_CSV = KOK / "sonuclar" / "evren" / "v2" / "holdout" / "holdout.csv"
KESIF_CSV = KOK / "sonuclar" / "evren" / "v2" / "holdout_kesif" / "holdout_kesif.csv"


def referans(ad: str) -> dict:
    for yol in (HOLDOUT_CSV, KESIF_CSV):
        d = pd.read_csv(yol)
        r = d[d.strateji == ad]
        if len(r):
            return {"kaynak": yol.name, "net": float(r.iloc[0]["net"]), "n_islem": int(r.iloc[0]["n_islem"])}
    raise RuntimeError(f"{ad}: holdout referansı bulunamadı")


def holdout_ham(t, mumlar, fund, tablo) -> tuple:
    """holdout.GercekSaglayici.tek_islemler ile AYNI adımlar (tek-sembol backtest + islem_hazirla), sağlayıcı kilidi kullanılmadan."""
    from motor.arastirma import evren_maliyet, wf_evren as we
    from motor.arastirma.v2 import ham as hm, sabit
    from motor.backtest.motor import backtest
    from motor.strateji import funding
    etiket, st = hm.varsayilan_strateji(t.kimlik)
    sira = sabit.evren_listesi("kripto" if t.tf == "15m" else "genel")
    out = {}
    for s in sira:
        if (s, t.tf) not in mumlar:
            continue
        m, f = mumlar[(s, t.tf)], fund.get(s)
        if not len(m) or m.index[-1] < sabit.HOLDOUT_BAS:
            continue
        kural = we.tarama.SEMBOL_KURALLARI.get(s, we.tarama.VARSAYILAN_KURAL)
        ay = evren_maliyet.maliyet_ayarlari(s, kural, 1.0, tablo)
        res = backtest(funding.stratejiye_hazirla(st, m, f, s, t.tf), st, ay, f)
        h, _ = hm.islem_hazirla(res.islemler, s, t.tf, 1.0, m, tablo)
        h = h[pd.DatetimeIndex(h["giris_zamani"]) >= sabit.HOLDOUT_BAS]
        if len(h):
            out[s] = h.reset_index(drop=True)
    return out, sira


def holdout_oynat(ad: str, ham: dict, sira, s: float, tablo, limitsiz: bool = False) -> dict:
    from motor.arastirma.v2 import holdout as ho, kasa, sabit
    bit = pd.Timestamp("2026-11-06", tz="UTC")
    oos = kasa.oos_birlestir({ad: ham}, {ad: sira}, sabit.HOLDOUT_BAS, 1.0, tablo)
    ay = ho._ayar(s)
    if limitsiz:
        ay = dataclasses.replace(ay, toplam_risk=1e6, kaldirac=1e6, gunluk_kayip=1e6, kill=1e6)
    tb, res = kasa.oynat(oos, sabit.HOLDOUT_BAS, bit, ay)
    oos = oos.copy()
    oos["kabul"] = oos.index.isin(res["kabul"])
    oos["pnl_h"] = [res["islem_pnl"].get(i, (0, 0.0))[1] for i in oos.index]
    return {"net": float(res["nakit_son"] - 1.0), "n_ham": int(len(oos)), "n_kabul": int(len(res["kabul"])), "sayac": res["sayac"], "oos": oos}


def paper_kos(tanimlar, mumlar, fund, s, bas, bit, onbellek, limitsiz: bool = False) -> v2.PaperKasalar:
    """limitsiz=True YALNIZ ÖLÇÜM (bu araç): hesap limitleri (toplam stop riski, kaldıraç, günlük -%3, kill) bu çağrı süresince kaldırılır.
    Üretim kodu değişmez; sert limitler servis/tekrar CLI'de ASLA gevşetilmez."""
    from motor.canli import paper_motor as pm
    p = v2.kasalar_kur(tanimlar, mumlar, fund, s, onbellek=onbellek)
    if not limitsiz:
        return v2.kos(p, bas, bit)
    for h in p.hesaplar.values():
        h.motor.top_risk = D(10 ** 6)
        h.motor.kal = 10 ** 6
    orijinal = pm.SERT_LIMITLER
    pm.SERT_LIMITLER = dataclasses.replace(orijinal, gunluk_max_kayip_yuzde=1e6, kill_switch_dusus_yuzde=1e6)
    try:
        return v2.kos(p, bas, bit)
    finally:
        pm.SERT_LIMITLER = orijinal


def _anahtar(sembol, zaman) -> str:
    return f"{sembol}|{pd.Timestamp(zaman).tz_convert('UTC').isoformat()}"


def eslestir(oos: pd.DataFrame, islemler: list) -> dict:
    pt = pd.DataFrame(islemler)
    a = oos[oos["kabul"]].copy()
    a["k"] = [_anahtar(x, y) for x, y in zip(a["sembol"], a["giris_zamani"])]
    pt["k"] = [_anahtar(x, y) for x, y in zip(pt["sembol"], pt["giris_zamani"])]
    ortak = set(a["k"]) & set(pt["k"])
    ah, bp = a[a["k"].isin(ortak)].set_index("k"), pt[pt["k"].isin(ortak)].set_index("k")
    j = ah[["r", "pnl_h"]].join(bp[["r", "net_pnl"]], lsuffix="_h", rsuffix="_p", how="inner")
    dr = (j["r_h"] - j["r_p"]).abs()
    tum = oos.copy()
    tum["k"] = [_anahtar(x, y) for x, y in zip(tum["sembol"], tum["giris_zamani"])]
    return {"holdout_kabul": int(len(a)), "paper": int(len(pt)), "ortak": int(len(ortak)),
            "sadece_holdout": int(len(set(a["k"]) - ortak)), "sadece_paper": int(len(set(pt["k"]) - ortak)),
            "sadece_paper_ham_listede": int(len((set(pt["k"]) - ortak) & set(tum["k"]))),
            # başlangıç etkisi: paper tekrarı bas'ta DÜZ başlar; sinyali süren (backtestte bas'tan önce girilmiş, holdout'a sayılmayan) pozisyona ilk
            # barlarda yarı-trendde girer. 'sadece paper' işlemlerinden ilk 5 gün içinde girenler:
            "sadece_paper_baslangic_n": int((pd.DatetimeIndex(pt.loc[~pt["k"].isin(ortak), "giris_zamani"]) < v2.HOLDOUT_BAS + pd.Timedelta(days=5)).sum()),
            "sadece_paper_baslangic_pnl": float(pt.loc[~pt["k"].isin(ortak) & (pd.DatetimeIndex(pt["giris_zamani"]) < v2.HOLDOUT_BAS + pd.Timedelta(days=5)), "net_pnl"].sum()),
            "ortak_medyan_abs_dR": float(dr.median()) if len(dr) else None, "ortak_maks_abs_dR": float(dr.max()) if len(dr) else None,
            "ortak_pnl_holdout": float(j["pnl_h"].sum() * 10000.0) if len(j) else 0.0,
            "ortak_pnl_paper": float(j["net_pnl"].sum()) if len(j) else 0.0,
            "sadece_holdout_pnl": float(a[~a["k"].isin(ortak)]["pnl_h"].sum() * 10000.0),
            "sadece_paper_pnl": float(pt[~pt["k"].isin(ortak)]["net_pnl"].sum())}


def sayac(p: v2.PaperKasalar) -> dict:
    from collections import Counter
    m = next(iter(p.hesaplar.values())).motor
    return {"reddedilen": dict(Counter(x["neden"] for x in m.reddedilenler)), "kirpilan": dict(Counter(x["tur"] for x in m.kirpmalar)),
            "cikis_nedenleri": dict(Counter(x["cikis_nedeni"] for x in m.islemler)), "kill": bool(m.kill), "gunluk_limit": int(m.gunluk_limit_sayisi)}


def kos_bir(k: dict, s: dict, surec: int, teshis: bool, sadece_onbellek: bool) -> dict:
    ad = k["strateji"]
    t0 = time.time()
    set1 = dict(s)
    set1["stratejiler"] = [k]
    tan = v2.tanimlari_yukle(set1)
    t = tan[0]
    mumlar, fund = v2.veri_yukle(tan, gerekce=v2.UYUM_GEREKCE)
    print(f"[{ad}] veri {time.time() - t0:.0f}s evren {len(t.veri_semboller)} düşen {t.disarida}", flush=True)
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    onb = v2.karar_onbellegi_olustur(tan, mumlar, fund, v2.HOLDOUT_BAS, v2.UYUM_BIT, ONBELLEK, surec)
    print(f"[{ad}] önbellek {time.time() - t0:.0f}s ({len(onb)} karar)", flush=True)
    if sadece_onbellek:
        return {}
    ref = referans(ad)
    tablo = v2.TABLO_YOLU
    sonuc = {"strateji": ad, "etiket": k["etiket"], "tf": k["tf"], "evren": k["evren"], "referans": ref, "disarida": t.disarida}
    p = paper_kos(tan, mumlar, fund, s, v2.HOLDOUT_BAS, v2.UYUM_BIT, onb)
    h = next(iter(p.hesaplar.values()))
    sonuc["paper"] = {"net": float(h.motor.ozsermaye() / D(h.ayarlar.baslangic_sermaye) - 1), "n_islem": len(h.motor.islemler), **sayac(p)}
    print(f"[{ad}] paper net {sonuc['paper']['net']:.4f} işlem {sonuc['paper']['n_islem']}  holdout {ref['net']:.4f}", flush=True)
    if k["tur"] == "tek":
        ham, sira = holdout_ham(t, mumlar, fund, tablo)
        ho = holdout_oynat(ad, ham, sira, float(s["s"]), tablo)
        sonuc["holdout_yeniden"] = {kk: vv for kk, vv in ho.items() if kk != "oos"}
        sonuc["eslesme"] = eslestir(ho["oos"], h.motor.islemler)
        print(f"[{ad}] holdout yeniden net {ho['net']:.4f} (kabul {ho['n_kabul']}/{ho['n_ham']}) eşleşme {sonuc['eslesme']['ortak']}", flush=True)
        if teshis:
            hf = holdout_oynat(ad, ham, sira, float(s["s"]), tablo, limitsiz=True)
            pf = paper_kos(tan, mumlar, fund, s, v2.HOLDOUT_BAS, v2.UYUM_BIT, onb, limitsiz=True)
            hp = next(iter(pf.hesaplar.values()))
            sonuc["teshis_limitsiz"] = {"holdout_net": hf["net"], "paper_net": float(hp.motor.ozsermaye() / D(hp.ayarlar.baslangic_sermaye) - 1),
                                        "holdout_n": hf["n_kabul"], "paper_n": len(hp.motor.islemler),
                                        "eslesme": eslestir(hf["oos"].assign(kabul=True), hp.motor.islemler)}
            print(f"[{ad}] TEŞHİS limitsiz: holdout {hf['net']:.4f} paper {sonuc['teshis_limitsiz']['paper_net']:.4f}", flush=True)
    sonuc["sure_sn"] = time.time() - t0
    CIKTI.mkdir(parents=True, exist_ok=True)
    (CIKTI / f"{ad}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return sonuc


def rapor_yaz() -> str:
    satir = ["# Paper v2 kabul testi (tekrar modu ↔ holdout)", "",
             f"Dönem: {v2.HOLDOUT_BAS.date()} → 2026-11-06 (holdout). Her strateji kendi 10.000 USD kasasında, s = 0.5, v2 varsayılan ayar. "
             "Net = kasa son özsermayesi / 10000 − 1 (açık pozisyonlar veri sonunda kapatılır).", "",
             "| strateji | etiket | holdout net | holdout yeniden | paper net | fark (puan) | ham/kabul (holdout) | paper işlem | ortak | sadece H | sadece P | teşhis limitsiz H / P |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for yol in sorted(CIKTI.glob("*.json")):
        r = json.loads(yol.read_text())
        ref, pa = r["referans"], r["paper"]
        hy, es, ts = r.get("holdout_yeniden"), r.get("eslesme"), r.get("teshis_limitsiz")
        satir.append("| " + " | ".join([
            r["strateji"], r["etiket"], f"{ref['net'] * 100:+.2f}%", f"{hy['net'] * 100:+.2f}%" if hy else "—", f"{pa['net'] * 100:+.2f}%",
            f"{(pa['net'] - ref['net']) * 100:+.2f}", f"{hy['n_ham']}/{hy['n_kabul']}" if hy else f"{ref['n_islem']}/—", str(pa["n_islem"]),
            str(es["ortak"]) if es else "—", str(es["sadece_holdout"]) if es else "—", str(es["sadece_paper"]) if es else "—",
            f"{ts['holdout_net'] * 100:+.2f}% / {ts['paper_net'] * 100:+.2f}%" if ts else "—"]) + " |")
    satir += ["", "## Strateji bazında yorum", "", "| strateji | yorum |", "|---|---|"]
    for yol in sorted(CIKTI.glob("*.json")):
        ad = json.loads(yol.read_text())["strateji"]
        satir.append(f"| {ad} | {ACIKLAMA.get(ad, '—')} |")
    satir += ["", "`teşhis limitsiz`: ölçüm amaçlı; HESAP limitleri (toplam stop riski, kaldıraç, günlük -%3, kill) iki tarafta da kaldırılır, işlem mekaniği "
              "(giriş/çıkış/boyut/maliyet) karşılaştırılır. Üretimde limitler ASLA gevşetilmez.", "", NEDENLER]
    return "\n".join(satir)


ACIKLAMA = {
    "dis__e0v1en": "81/83 işlem eşleşti; eşleşen işlemlerin K/Z toplamı farkı -3 USD. Fark -0.43 puan neredeyse tamamen başlangıç etkisi (neden 4): ZEC'te 2025-11-08'in ilk saatlerinde "
                   "paper-only 3 işlem (-58 USD) ve holdout-only 2 işlem (-19 USD; giriş saatleri farklı). Limitler hiç bağlamadı.",
    "dis__ewo-ema-ofset": "Tam uyum: 46/46 işlem birebir eşleşti (limitler hiç devreye girmedi); fark 0.03 puan (maliyet/yuvarlama).",
    "dis__uc-ortalama-boga-sma60": "Uyum: 42 işlem eşleşti; holdout'ta 6 işlem kabul edilip paper'da ayrıca girmedi (nedenler 1-2); limitsiz 9.04 / 8.94.",
    "pf__sabit_sepet": "Uyum: portföy ölçeği (s = grup payı 0.5) ↔ pf_net = prod(1 + s x günlük getiri) - 1; fark 0.04 puan.",
    "dis__haftalik-macd-gunluk-ma": "Uyum: 57 işlem eşleşti, fark 0.03 puan (holdout'ta 7 işlem tavanla paper'dan farklı kabul edildi; limitsiz 4.66 / 4.42).",
    "dis__lube": "20/20 holdout işlemi eşleşti. Fark 0.44 puan: paper'da ek 1 işlem (başlangıç etkisi, -32 USD; neden 4) + özsermaye boyutu (neden 5).",
    "dis__gauss-stoch-eth": "Limitler kaldırılınca fark -1.4 puan (neden 4: 4 başlangıç işlemi -35 USD; neden 5: ortak işlem K/Z'si -9%). Limitliyken fark -4.3: "
                            "paper'da tavan (neden 1) 202 girişi kırptı / 166'sını reddetti; holdout oynatmasında 22 red (neden 1, 2).",
    "dis__hma-atr-rider": "Mekanik uyum (limitsiz 8.31 / 8.52, 282/282 işlem). Limitli fark +6.8 puan tamamen neden 1: kayan stop (ATR izi) nedeniyle anlık stop riski küçülür, "
                          "paper 49 ek girişi kabul eder (+458 USD; ölçüm: anlık risk / başlangıç risk toplamı medyan 0.42); holdout oynatması başlangıç riskini sabit tuttuğu için 52 girişi reddeder.",
    "dis__jt-awesome-osilator": "Mekanik uyum (limitsiz 17.41 / 16.36, 208/208 işlem; ortak işlem K/Z'si -6%). Limitli fark -14.2 puan, neden 1: sabit stoplu kârdaki pozisyonlarda anlık stop riski "
                                "büyür (ölçüm: giriş anlarında anlık risk / başlangıç risk toplamı medyan 1.94, p90 3.78), paper 138 girişi reddedip 149'unu kırptı ve 70 işlem yaptı; "
                                "holdout oynatması başlangıç riskini sabit tuttuğu için 208 ham işlemin 112'sini kabul etti. Günlük -%3 limiti paper'da 1 kez tetiklendi (4 işlem), holdout oynatmasında hiç (neden 3/5).",
    "dis__voltarget-trend": "Limitsiz: +2.9 puan (neden 4: ilk barda 17 yarı-trend girişi, +495 USD). Limitliyken -1.2: tavan çok sık bağlar (687 red); hangi işlemlerin girdiği iki tarafta farklı (6 ortak işlem).",
}


NEDENLER = """## Fark nedenleri (belgelenmiş)
1. **Toplam açık stop riski ölçüsü (%5 tavan).** Holdout oynatması (`secim.yeniden_oyna`) her açık işlemin *başlangıç* risk tutarını sabit toplar; motorlar (backtest, portföy, paper)
   tavanı pozisyonun *anlık* stopa mesafesiyle ((fiyat − stop) × miktar) ölçer. Kayan (trailing) stoplu stratejide (hma-atr-rider) paper daha az giriş reddeder; sabit stoplu kârdaki
   pozisyonlarda daha çok. Tavan bağlayıcı olduğunda hangi işlemlerin girdiği ve boyutları iki tarafta farklıdır. Paper, motorun sert limit uygulamasıdır; holdout ölçümü yaklaşıklıktır.
2. **Reddedilen girişin akıbeti.** Holdout'ta reddedilen işlem sonsuza dek kaybolur; paper'da sinyal sürüyorsa sonraki barlarda yeniden denenir (farklı giriş tarihi -> "sadece paper"/"sadece holdout").
3. **Günlük -%3 limitinin zorla kapatması.** Holdout, açık işlemleri R yolunun doğrusal ara değeriyle değerler ve yeniden girmez; paper gerçek son fiyattan (stop kayması) kapatır ve sinyal sürüyorsa sonra yeniden girer.
4. **Başlangıç etkisi.** Holdout yalnız girişi >= 2025-11-08 olan işlemleri sayar (o tarihte açık olan pozisyon sayılmaz); paper tekrarı düz başlar ve sinyali süren stratejide ilk barda
   (TradFi için ilk işlem günü) yarı-trendde girer. Canlı paper'da da aynıdır (strateji o günkü durumdan başlar).
5. **Özsermaye tanımı (boyutlandırma).** Holdout: nakit + yalnız açık işlemlerin zararı (muhafazakâr); paper: gerçek MTM özsermaye (açık kâr dahil) -> kârlı dönemde paper'ın pozisyonları biraz daha büyük.
6. **Funding.** Kripto: aynı gerçek seri. TradFi (DK_): holdout sürekli süre x giriş fiyatı x %0.01/8s (yalnız long); tekrar modu 8 saatte bir ayrık, o anki fiyatla (short'a yazılmaz; aynı kural). Canlı paper
   gerçek Binance TradFi funding'ini öder ve ayrı alanda tutar.
7. **Ayrıntılar.** Adım/tick yuvarlaması ve min notional (paper'da `min_notional` ile reddedilen çok küçük girişler), sembol kuralları varsayılanı; etkileri küçük.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kimlik", nargs="*")
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--teshis", action="store_true", help="limitsiz karşılaştırma (yalnız ölçüm)")
    ap.add_argument("--onbellek-hazirla", action="store_true", help="yalnız karar önbelleğini üret (uzun, kaldığı yerden devam eder)")
    a = ap.parse_args(argv)
    s = v2.set_yukle()
    for k in s["stratejiler"]:
        if a.kimlik and k["strateji"] not in a.kimlik:
            continue
        kos_bir(k, s, a.surec, a.teshis, a.onbellek_hazirla)
    if not a.onbellek_hazirla:
        md = rapor_yaz()
        (CIKTI / "uyum_raporu.md").write_text(md, encoding="utf-8")
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
