"""Tüm kağıt hesapların (5 repo) tek tabloda karşılaştırması. Her repo'nun durum dalından ozsermaye.csv okunur.

  python -m karsilastirma.tum_hesaplar     (repolar /home/user/<repo> altında klonlu olmalı)
Salt okunur: hiçbir repoya yazmaz.
"""
import io
import subprocess

import numpy as np
import pandas as pd

KOK = "/home/user"
HESAPLAR = [
    # ad, repo, dal, zaman kolonu, değer kolonu, beklenti (60 gün)
    ("Strateji KGT+KMN", "strateji-sg", "kagit-durum", "zaman", "toplam", "yıllık %35-45, DD %15-20"),
    ("Algo A+B (kripto)", "algo-sg", "kagit-durum", "saat", "TOPLAM", "A KO ~%50, B KO ~%64"),
    ("Day trade S10+S13+S15", "day-trade-sg", "kagit-durum", "zaman", "deger", "60 günde +%2-4, DD ~%5"),
    ("Swing S1+S2+S3", "swing-sg", "kagit-durum", "tarih", "deger", "60 günde +%3-4, DD ~%13"),
    ("Swing trend kolları", "swing-sg", "kagit-trend-durum", "tarih", "deger", "60 günde +%3-4, DD ~%7"),
]


def oku(repo, dal, zk, dk):
    d = f"{KOK}/{repo}"
    subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", "origin", dal], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run(["git", "-C", d, "show", "FETCH_HEAD:ozsermaye.csv"], capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        return None
    df = pd.read_csv(io.StringIO(r.stdout))
    if zk not in df or dk not in df:
        return None
    s = pd.Series(df[dk].values, index=pd.to_datetime(df[zk], utc=True).dt.tz_localize(None)).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def rapor():
    satir, gunluk = [], {}
    for ad, repo, dal, zk, dk, bek in HESAPLAR:
        s = oku(repo, dal, zk, dk)
        if s is None or not len(s):
            satir.append(dict(hesap=ad, durum="veri yok", deger="-", getiri="-", maks_dusus="-", son="-", beklenti=bek))
            continue
        bas = s.iloc[0]
        yas = (pd.Timestamp.now(tz="UTC").tz_localize(None) - s.index[-1]).total_seconds() / 3600
        durum = "çalışıyor" if yas <= 30 else f"⚠️ {yas:.0f} saattir güncellenmedi"
        satir.append(dict(hesap=ad, durum=durum, deger=f"{s.iloc[-1]:,.0f} $", getiri=f"{s.iloc[-1] / bas - 1:+.2%}",
                          maks_dusus=f"{(s / s.cummax() - 1).min():.1%}", son=str(s.index[-1])[:16], beklenti=bek))
        gunluk[ad] = s.resample("D").last().ffill()
    t = pd.DataFrame(satir)
    out = ["## Tüm kağıt hesaplar", "", t.to_markdown(index=False), ""]
    if gunluk:
        df = pd.DataFrame(gunluk).ffill()
        norm = df / df.bfill().iloc[0]
        esit = norm.mean(axis=1)
        out += [f"**Eşit ağırlıklı tüm hesaplar:** {esit.iloc[-1] - 1:+.2%} "
                f"(maks. düşüş {(esit / esit.cummax() - 1).min():.1%})", ""]
        r = df.pct_change().dropna(how="all")
        if len(r) >= 10:
            out += ["Günlük getiri korelasyonu:", "", r.corr().round(2).to_markdown(), ""]
        else:
            out += [f"_Korelasyon için en az 10 gün gerekiyor (şu an {len(r)})._", ""]
    return "\n".join(out)


if __name__ == "__main__":
    print(rapor())
