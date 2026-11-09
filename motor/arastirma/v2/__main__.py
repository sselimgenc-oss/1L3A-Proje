"""python -m motor.arastirma.v2 <asama> [...]  (ON_KAYIT_V2 bölüm 10). Bu dosyada aşamalar: maliyet, ham, eleme.
Sıra zorunludur: ham için havuz mührü, eleme için ham çıktısı yoksa açık hata."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from motor.arastirma.v2 import sabit


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m motor.arastirma.v2", description="v2 evren seçimi (ON_KAYIT_V2)")
    ap.add_argument("asama", choices=["maliyet", "ham", "eleme"])
    ap.add_argument("--cikti", default=None, help=f"çıktı dizini (varsayılan {sabit.CIKTI})")
    ap.add_argument("--surec", type=int, default=sabit.SUREC_VARSAYILAN)
    ap.add_argument("--butce", type=float, default=None, help="saniye; dolunca yeni görev başlatılmaz, biten sonuçlar yazılır")
    ap.add_argument("--stratejiler", nargs="*", default=None, help="ham: yalnız bu havuz satırları (duman koşusu)")
    ap.add_argument("--semboller", nargs="*", default=None, help="ham: yalnız bu semboller (duman koşusu)")
    ap.add_argument("--hatalari-yeniden", action="store_true", help="ham: hata yan dosyalarını silip yeniden dene")
    ap.add_argument("--havuz", default=None, help="havuz csv (yalnız test/duman; varsayılan donmuş havuz)")
    ap.add_argument("--muhur", default=None, help="havuz mührü (yalnız test/duman)")
    ap.add_argument("--yeniden", action="store_true", help="eleme: satır önbelleğini yok say")
    a = ap.parse_args(argv)
    cikti = Path(a.cikti) if a.cikti else sabit.CIKTI
    if a.asama == "maliyet":
        from motor.arastirma.v2 import maliyet
        from motor.arastirma import evren_maliyet
        y = maliyet.tabloyu_hazirla(cikti)
        print(y, evren_maliyet.tablo_hash(y))
        return 0
    if a.asama == "ham":
        from motor.arastirma.v2 import ham
        o = ham.ham_asamasi(cikti, a.surec, a.butce, stratejiler=a.stratejiler, semboller=a.semboller,
                            hatalari_yeniden=a.hatalari_yeniden, havuz_yolu=a.havuz, muhur_yolu=a.muhur)
        return 1 if o["hata"] else 0
    from motor.arastirma.v2 import eleme
    o = eleme.eleme_asamasi(cikti, a.surec, a.butce, a.havuz, a.muhur, yeniden=a.yeniden)
    return 2 if o.get("bekleyen") else 0


if __name__ == "__main__":
    sys.exit(main())
