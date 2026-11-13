"""Kodlu strateji kaydı: ara/kod_kaydi.csv (ad, tur, stil, dosya, sinif, satir). Yalnız içe aktarır, strateji koşmaz."""
import csv, inspect, os
from pathlib import Path
KOK = Path(__file__).resolve().parents[3]
os.chdir(KOK)
import sys; sys.path.insert(0, str(KOK))
from motor.strateji.kayit import tum_stratejiler
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
rows = []
for ad, s in sorted(tum_stratejiler().items()):
    rows.append([ad, "tek_grafik", s.stil, str(Path(inspect.getsourcefile(s)).relative_to(KOK)), s.__name__, inspect.getsourcelines(s)[1]])
for ad, s in sorted(tum_portfoy_stratejileri().items()):
    rows.append([ad, "portfoy", "portfoy", str(Path(inspect.getsourcefile(s)).relative_to(KOK)), s.__name__, inspect.getsourcelines(s)[1]])
with open("sonuclar/hesap_defteri/ara/kod_kaydi.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["ad", "tur", "stil", "dosya", "sinif", "satir"]); w.writerows(rows)
print(len(rows))
