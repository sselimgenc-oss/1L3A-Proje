"""Sonuç CSV'lerinden DIS_STRATEJILER.md tablolarını ve aday listesini üretir."""
import os, glob
import numpy as np, pandas as pd
from . import ortak as O

HERE = os.path.dirname(__file__)
SER = os.environ.get("DIS_SERI", "/tmp/dis_seriler")

# Eleme ölçütleri (önceden sabit): iki dönemde de kenar (PF>1.2, Sharpe>0.5) + stres evreninde kenar (PF>1.1).
# Düşük (DD) kaldıraca bağlı olduğu için eleme ölçütü değil; raporda gösterilir.
def gecti(r):
    try:
        return (r["pf_is"] > 1.2 and r["pf_oos"] > 1.2 and r["pf_stres"] > 1.1 and r["sh_is"] > 0.5 and r["sh_oos"] > 0.5)
    except TypeError:
        return False


def bizim_seriler():
    """Bizim A ve B kollarımızın günlük getirisi (kapanan işlemler, risk A %0.5, B %0.75; 50/50)."""
    out = {}
    for k, risk in (("A", 0.005), ("B", 0.0075)):
        t = pd.read_csv(os.path.join(HERE, "..", "results", f"final_trades_{k}.csv"), parse_dates=["exit_time"])
        g = (t.set_index("exit_time")["R"] * risk).resample("1D").sum()
        out[k] = g
    ab = (out["A"].add(out["B"], fill_value=0)) / 2
    return out["A"], out["B"], ab


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:.{nd}f}"


def tablo(df, cols):
    head = "| " + " | ".join(c[1] for c in cols) + " |\n|" + "---|" * len(cols) + "\n"
    rows = []
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(((str(r[c[0]]) if not pd.isna(r[c[0]]) else "–") if c[0] in ("id", "strateji", "kaynak", "tf", "kapsam", "karar") else fmt(r.get(c[0]), c[2] if len(c) > 2 else 2)) for c in cols) + " |")
    return head + "\n".join(rows)


COLS = [("id", "ID"), ("strateji", "Strateji"), ("tf", "TF"), ("islem", "İşlem", 0), ("wr", "WR %", 0),
        ("pf_is", "PF IS"), ("pf_oos", "PF OOS"), ("pf_2022", "PF 2022"), ("sh_is", "Sh IS"), ("sh_oos", "Sh OOS"),
        ("dd", "DD %", 0), ("pf_stres", "PF stres"), ("pf_gel_is", "PF gel IS"), ("pf_gel_oos", "PF gel OOS"), ("karar", "Karar")]


GEL_AT = (0.96, 1.53)  # geleneksel evren eşit ağırlıklı al-tut Sharpe (IS, OOS) — sonuc_aday_saglamlik.csv


def karar(r):
    if isinstance(r.get("hata"), str):
        return "hata"
    if "geleceği görüyor" in str(r.get("kapsam", "")):
        return "geçersiz (ileriye bakma)"
    if gecti(r):
        return "**aday**"
    # geleneksel evrende (Mag7 + BIST10 + emtia) seçim yanlılığı var: yalnız eşit ağırlıklı al-tut'u
    # iki dönemde de Sharpe olarak geçen kural anlamlı sayılır (al-tut Sharpe: IS 0.96, OOS 1.53)
    sgi, sgo = r.get("sh_gel_is", np.nan), r.get("sh_gel_oos", np.nan)
    if isinstance(sgi, float) and sgi > GEL_AT[0] and sgo > GEL_AT[1] and r.get("pf_gel_is", 0) > 1.2 and r.get("pf_gel_oos", 0) > 1.2:
        return "geleneksel: al-tut'u geçiyor"
    return "ele"


def yukle():
    dfs = []
    for f in ("sonuc_jesuistm.csv", "sonuc_kural.csv", "sonuc_awesome.csv", "sonuc_freqtrade.csv", "sonuc_freqtrade_dakika_tablo.csv"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            d = pd.read_csv(p)
            if "id" not in d:
                d["id"] = ["JT%02d" % (i + 1) for i in range(len(d))]
                d["kaynak"] = "je-suis-tm/quant-trading"; d["tf"] = ["1h" if any(k in s for k in ("Bollinger_W", "London", "Dual")) else "1D" for s in d["strateji"]]
            dfs.append(d)
    df = pd.concat(dfs, ignore_index=True)
    if "tf" not in df: df["tf"] = ""
    df["tf"] = df["tf"].fillna("1h")
    df["karar"] = [karar(r) for _, r in df.iterrows()]
    return df


def korelasyon(ids):
    A, B, AB = bizim_seriler()
    out = {}
    for i in ids:
        p = os.path.join(SER, f"{i}.pkl")
        if not os.path.exists(p):
            continue
        g = pd.read_pickle(p)
        j = pd.concat([g, AB], axis=1).dropna(); j.columns = ["s", "ab"]
        j = j[j.index >= pd.Timestamp("2020-03-01", tz="UTC")]
        w = j.resample("W").sum()
        out[i] = {"kor_gunluk": j["s"].corr(j["ab"]), "kor_haftalik": w["s"].corr(w["ab"])}
    return out


if __name__ == "__main__":
    df = yukle()
    df.to_csv(os.path.join(HERE, "sonuc_tum.csv"), index=False)
    print(df["karar"].value_counts())
    ad = df[df["karar"] != "ele"]
    print(ad[["id", "strateji", "pf_is", "pf_oos", "pf_2022", "sh_is", "sh_oos", "dd", "pf_stres", "karar"]].to_string())


def md_tablolar(df):
    """Kaynak deposuna göre gruplanmış markdown tabloları."""
    out = []
    sira = ["freqtrade-strategies", "freqtrade-strategies (dakikalık)", "je-suis-tm/quant-trading", "backtrader", "backtesting.py",
            "finmarketpy", "QuantDinger", "ai_quant_trade", "OctoBot", "binance-trading-bot", "awesome-systematic-trading"]
    cols = [c for c in COLS if c[0] in df.columns or c[0] == "karar"]
    for k in sira:
        d = df[df["kaynak"] == k]
        if d.empty:
            continue
        d = d.sort_values("sh_oos", ascending=False, na_position="last")
        out.append(f"### {k} ({len(d)} test)\n\n" + tablo(d, cols) + "\n")
    return "\n".join(out)


def yaz_md(df, yol):
    open(yol, "w").write(md_tablolar(df))
