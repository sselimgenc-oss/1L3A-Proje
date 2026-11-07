"""Elenen havuz WF sonuçlarının sağlamlık koşusu (Ar-Ge kolu).

WF çıktısı: sonuclar/haiku_arge/wf/<etiket>.parquet (yalnız gecti == True satırlar değerlendirilir).
Yöntem: motor/arastirma/saglamlik.py (maliyet×2, rastgele giriş, bootstrap, komşu parametre) — değişmez.
Çıktılar ve deneme kaydı sonuclar/haiku_arge/ altında; ana proje dosyaları değişmez.

Kullanım: python sonuclar/haiku_arge/saglamlik_kos.py <wf_etiket>
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor.arastirma import saglamlik  # noqa: E402

HA = KOK / "sonuclar" / "haiku_arge"

if __name__ == "__main__":
    etiket = sys.argv[1]
    t = saglamlik.saglamlik_tara(
        etiket, etiket=etiket, surec=2,
        wf_dizini=HA / "wf", cikti_dizini=HA / "saglamlik",
        deneme_kaydi_yolu=HA / "deneme_kaydi.jsonl",
    )
    print(t.to_string() if len(t) else "sağlamlık: aday yok")
