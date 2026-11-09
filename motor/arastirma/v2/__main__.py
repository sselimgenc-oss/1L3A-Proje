"""python -m motor.arastirma.v2 <asama> [...]  (ON_KAYIT_V2 bölüm 10). Aşamalar: maliyet, ham, eleme, test, saglamlik, set, holdout.
Sıra zorunludur: ham için havuz mührü, eleme için ham çıktısı, test için eleme.csv, saglamlik için test.csv, set için saglamlik.csv,
holdout için set mührü (set_muhru.json) yoksa açık hata. Uzun aşamalar --butce ile zaman kutulanır ve yeniden çalıştırınca kaldığı yerden sürer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from motor.arastirma.v2 import sabit


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m motor.arastirma.v2", description="v2 evren seçimi (ON_KAYIT_V2)")
    ap.add_argument("asama", choices=["maliyet", "ham", "eleme", "test", "saglamlik", "set", "holdout"])
    ap.add_argument("--cikti", default=None, help=f"çıktı dizini (varsayılan {sabit.CIKTI})")
    ap.add_argument("--surec", type=int, default=sabit.SUREC_VARSAYILAN)
    ap.add_argument("--butce", type=float, default=None, help="saniye; dolunca yeni görev başlatılmaz, biten sonuçlar yazılır")
    ap.add_argument("--stratejiler", nargs="*", default=None, help="ham: yalnız bu havuz satırları (duman koşusu)")
    ap.add_argument("--semboller", nargs="*", default=None, help="ham: yalnız bu semboller (duman koşusu)")
    ap.add_argument("--hatalari-yeniden", action="store_true", help="ham: hata yan dosyalarını silip yeniden dene")
    ap.add_argument("--havuz", default=None, help="havuz csv (yalnız test/duman; varsayılan donmuş havuz)")
    ap.add_argument("--muhur", default=None, help="havuz mührü (yalnız test/duman)")
    ap.add_argument("--yeniden", action="store_true", help="eleme: satır önbelleğini yok say")
    ap.add_argument("--spa-yok", action="store_true", help="test: Hansen SPA (rapor) hesaplanmasın")
    ap.add_argument("--holdout-bir-kez", action="store_true",
                    help="holdout: BİR KEZ açılacağını onaylar (set mührü + ilk koşu şartı; ikinci deneme yoktur)")
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
    if a.asama == "test":
        from motor.arastirma.v2 import test as k2test
        o = k2test.test_asamasi(cikti, a.surec, a.butce, a.havuz, a.muhur, spa_hesapla=not a.spa_yok)
        return 2 if o.get("bekleyen") else 0
    if a.asama == "saglamlik":
        from motor.arastirma.v2 import saglamlik
        o = saglamlik.saglamlik_asamasi(cikti, a.surec, a.butce)
        return 2 if o.get("bekleyen") else 0
    if a.asama == "set":
        from motor.arastirma.v2 import set as set_asama
        o = set_asama.set_asamasi(cikti, a.butce, a.havuz, a.muhur)
        return 2 if o.get("bekleyen") else 0
    if a.asama == "holdout":
        from motor.arastirma.v2 import holdout
        if not a.holdout_bir_kez:
            ap.error("holdout: --holdout-bir-kez onayı gerekli (holdout BİR KEZ açılır)")
        o = holdout.holdout_asamasi(cikti, havuz_yolu=a.havuz)
        print({k: o[k] for k in ("kapi_gecti", "net_set", "p_set", "kalan")})
        return 0
    from motor.arastirma.v2 import eleme
    o = eleme.eleme_asamasi(cikti, a.surec, a.butce, a.havuz, a.muhur, yeniden=a.yeniden)
    return 2 if o.get("bekleyen") else 0


if __name__ == "__main__":
    sys.exit(main())
