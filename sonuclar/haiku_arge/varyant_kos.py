"""Sınırdaki adayların ön kayıtlı varyantlarının WF koşusu (sonuclar/haiku_arge/GELISTIRME_ON_KAYIT.md).

Varyantlar motor/strateji/dis/haiku__varyant.py içinde (12 sınıf, önek haiku__). Ayarlar wf_kos ile aynı:
izgara açık, kilit 2025-11-01, 5 enstrüman, stil tf'leri. Çıktı ve deneme kaydı sonuclar/haiku_arge/ altında.
Kullanım: python sonuclar/haiku_arge/varyant_kos.py
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor.arastirma import wf_tarama  # noqa: E402
from motor.strateji import kayit  # noqa: E402

HA = KOK / "sonuclar" / "haiku_arge"
SEMBOLLER = ["BTCUSDT", "DK_XAU", "DK_SPX", "DK_UKOIL", "XU30"]

if __name__ == "__main__":
    adlar = sorted(a for a in kayit.tum_stratejiler() if a.startswith("haiku__"))
    print(f"[varyant] {len(adlar)} strateji x {SEMBOLLER}", flush=True)
    s = wf_tarama.wf_tara("haiku_varyant", stratejiler=adlar, semboller=SEMBOLLER, surec=4,
                          bitis="2025-11-01", izgara=True, cikti_dizini=HA / "wf",
                          deneme_kaydi_yolu=HA / "deneme_kaydi.jsonl")
    print(f"[varyant] bitti: {len(s)} satır", flush=True)
