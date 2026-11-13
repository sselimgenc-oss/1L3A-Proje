"""Lider: v3 ham kataloglarında alt küme dosyalarını 'tümü' dosyalarındaki satıra bağlar (birleştirme talimatı üretir).
Çıktı: ara/lider_birlestir_ile.csv (ham_id, hedef_ham_id, anahtar, gerekce). birlestir.py bunu okur: satır kendi kararını
korur, yalnız tekil olarak hedef satırın tekiline katılır (kod bağlantısı olan KOD/AYAR/ESDEGER satırlar hariç)."""
import csv
from pathlib import Path
HD = Path(__file__).resolve().parents[1]; KOK = HD.parents[1]
D = KOK / "stratejiler/v3_adaylar/ham"
kid = {r["yol"]: r["kaynak_id"] for r in csv.DictReader(open(HD / "kaynaklar.csv"))}
CIFT = [("asya-siteleri-katalog__b_duzeyi.csv", "asya-siteleri-katalog__tumu.csv", "tam"),
        ("bolgesel-katalog__b_duzeyi.csv", "bolgesel-katalog__tumu.csv", "tam"),
        ("github-backtest-katalog-denetimli__gercek_ek.csv", "github-backtest-katalog-denetimli__tumu.csv", "repo+strateji"),
        ("github-backtest-katalog-denetimli__dogrulanan_48.csv", "github-backtest-katalog-denetimli__tumu.csv", "repo+strateji"),
        ("github-backtest-katalog-v4__sayfa_dogrulamasi.csv", "github-backtest-katalog-denetimli__tumu.csv", "repo+strateji")]
out = []
for alt, tum, tip in CIFT:
    A = list(csv.reader(open(D / alt, encoding="utf-8-sig")))[1:]
    T = list(csv.reader(open(D / tum, encoding="utf-8-sig")))[1:]
    key = (lambda r: tuple(r)) if tip == "tam" else (lambda r: (r[0].strip(), r[2].strip()))
    idx = {}
    for i, r in enumerate(T, 1):
        idx.setdefault(key(r), i)
    ka, kt = kid["stratejiler/v3_adaylar/ham/" + alt], kid["stratejiler/v3_adaylar/ham/" + tum]
    for i, r in enumerate(A, 1):
        j = idx.get(key(r))
        if j:
            out.append({"ham_id": f"{ka}:{i}", "hedef_ham_id": f"{kt}:{j}", "anahtar": tip,
                        "gerekce": f"{alt} satırı {tum} içinde ({tip} eşleşmesi): aynı katalog kaydı"})
with open(HD / "ara" / "lider_birlestir_ile.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["ham_id", "hedef_ham_id", "anahtar", "gerekce"]); w.writeheader(); w.writerows(out)
print(len(out))
