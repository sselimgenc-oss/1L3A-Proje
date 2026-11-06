"""Aşama 3 çıktıları: tv/sonuclar/ozet.csv ve tv/RAPOR.md (sonuclar/*.json'dan)."""
import json, glob, pathlib, csv
import pandas as pd
K = pathlib.Path(__file__).parent
from tv import motor

def yukle():
    out = []
    for f in sorted(glob.glob(str(K/"sonuclar/*.json"))):
        d = json.load(open(f)); out.append(d)
    return out

def maliyet_rt(evren):
    ort = sum(motor.MASRAF[g] for g in evren)/len(evren)
    return 2*(ort + motor.KAYMA)

def siralama(d):
    m = d["olcut"]; g = lambda k, dv=0: (m.get(k) if m.get(k) is not None else dv)
    s = {
     "calmar>=1": g("calmar") >= 1.0,
     "dd_suresi<180g": g("dd_gun", 9999) < 180,
     "psr>=90": g("psr") >= 0.90,
     "ort_islem>=3xmaliyet": g("ort_islem_getiri", -1) >= 3*maliyet_rt(d["evren"]),
     "maks_kor<=0.6": (m.get("maks_kor") is not None and m["maks_kor"] <= 0.6),
    }
    return s

def yaz():
    D = yukle(); rows = []
    for d in D:
        m = d["olcut"]; r = dict(strateji=d["ad"], pine_id=d["pine_id"], tf=d["tf"], tur=m.get("tur"), islem=m["n"],
            kar_faktoru=m.get("pf"), sharpe=m.get("sharpe"), maks_dusus=m.get("maxdd"), beklenti_R=m.get("beklenti_R"),
            kazanma=m.get("kazanma"), sharpe_egitim=m.get("sharpe_egitim"), sharpe_oos=m.get("sharpe_oos"),
            kf_maliyet2x=m.get("pf_maliyet2x"), komsu_karda=m.get("komsu_karda"), enstr_karda=m.get("enstr_karda"),
            calmar=m.get("calmar"), dd_gun=m.get("dd_gun"), psr=m.get("psr"), ort_islem_getiri=m.get("ort_islem_getiri"),
            maks_kor=m.get("maks_kor"))
        for k, v in d["kurallar"].items(): r["K_"+k] = "geçti" if v else "kaldı"
        r["SONUC"] = "GEÇTİ" if d["gecti"] else "kaldı"
        for k, v in siralama(d).items(): r["S_"+k] = "geçti" if v else "kaldı"
        r["siralama_puani"] = sum(siralama(d).values()) if d["gecti"] else ""
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(K/"sonuclar/ozet.csv", index=False)
    (K/"gecenler.json").write_text(json.dumps([d["ad"] for d in D if d["gecti"]], ensure_ascii=False))
    return D, df

def rapor_md(D, df):
    adaylar = list(csv.DictReader(open(K/"aday.csv")))
    n_aday = sum(a["karar"] == "al" for a in adaylar); n_cev = len(D)
    gecen = [d for d in D if d["gecti"]]
    kural_ad = list(D[0]["kurallar"].keys())
    kal = {k: sum(not d["kurallar"][k] for d in D) for k in kural_ad}
    L = ["# TradingView stratejileri: eleme raporu", "",
         f"- Kaynak: {len(adaylar)} benzersiz betik (2 PDF). Kaynağı açık: {sum(a['erisim']=='acik' for a in adaylar)}, kapalı: {sum(a['erisim']=='kapali' for a in adaylar)}.",
         f"- Aşama 1 ön eleme: **{n_aday} aday** seçildi, {len(adaylar)-n_aday} elendi (gerekçeler `tv/aday.csv`).",
         f"- Aşama 2: {n_cev} aday Python'a çevrildi ve backtest edildi ({n_aday-n_cev} çevrilemedi, nedenleri `aday.csv`).",
         f"- Aşama 3: **{len(gecen)} strateji** tüm zorunlu kuralları geçti.", ""]
    L += ["## Kural bazında kaybedenler", "", "| Kural | Kalan strateji |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in kal.items()]
    L += ["", "## Geçenler", ""]
    if gecen:
        L += ["| Strateji | İşlem | KF | Sharpe | Maks. düşüş | Beklenti R | OOS/Eğitim Sharpe | Sıralama puanı (5 üzerinden) |", "|---|---|---|---|---|---|---|---|"]
        for d in sorted(gecen, key=lambda d: -sum(siralama(d).values())):
            m = d["olcut"]; L.append(f"| {d['ad']} ({d['pine_id']}) | {m['n']} | {m['pf']:.2f} | {m['sharpe']:.2f} | %{m['maxdd']*100:.0f} | {m['beklenti_R']:.2f} | {m['sharpe_oos']:.2f}/{m['sharpe_egitim']:.2f} | {sum(siralama(d).values())} |")
    else: L.append("Geçen yok.")
    L += ["", "## Kalanlar (en yakın 10: sağlanan zorunlu kural sayısına göre)", "", "| Strateji | Geçilen kural | Başarısız kurallar |", "|---|---|---|"]
    kalan = sorted([d for d in D if not d["gecti"]], key=lambda d: -sum(d["kurallar"].values()))[:10]
    for d in kalan:
        bas = ", ".join(k for k, v in d["kurallar"].items() if not v)
        L.append(f"| {d['ad']} | {sum(d['kurallar'].values())}/{len(d['kurallar'])} | {bas} |")
    L += ["", "## Yöntem ve varsayımlar", ""]
    L += open(K/"yontem.md").read().splitlines() if (K/"yontem.md").exists() else []
    (K/"RAPOR.md").write_text("\n".join(L)+"\n")

if __name__ == "__main__":
    D, df = yaz(); rapor_md(D, df); print(len(D), "strateji; geçen:", sum(d["gecti"] for d in D))
