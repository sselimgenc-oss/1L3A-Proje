"""python -m motor.arastirma.v3 <komut> — v3 eleme hattı (ON_KAYIT_V3).
  dondur                       : sonuclar/v3/dondurma.json (hash'ler + commit); var olan dondurma değiştirilmez
  destek [--gercek]            : rastgele-giriş destek ön şartı (satır başına ok/değil + neden); --gercek: veri zaman damgası kapsamı da
  eleme [--satir N] [--isci K] : dondurma.dogrula() sonra satırları koşar (dondurma yoksa REDDEDER); satır sonuçları sonuclar/v3/satir/
  rapor                        : eleme.csv + ELEME_RAPORU.md"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from motor.arastirma.v3 import dondurma, sabit


def _yaz_atomik(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    g = yol.with_suffix(".jtmp")
    g.write_text(json.dumps(veri, ensure_ascii=False, indent=1, default=str, sort_keys=True), encoding="utf-8")
    g.replace(yol)


def eleme_calistir(satir_no=None, isci: int = 1, yeniden_altyapi: bool = False, cikti_dizini: Path = None,
                   dondurma_yol: Path = None, ilerleme: bool = True) -> list:
    """Dondurma doğrulanır (eksik/bozuk -> DondurmaHatasi, koşu başlamaz); her satırdan sonra yeniden doğrulanır (koşu sırasında kod
    değişirse koşu geçersiz). Biten satır atlanır; yalnız altyapı hatası veren satır, bir kez, --yeniden-altyapi ile yeniden koşulur."""
    from motor.arastirma.v3 import kos, veri
    cikti_dizini = Path(cikti_dizini or sabit.SATIR_DIZINI)
    dondurma_yol = Path(dondurma_yol or sabit.DONDURMA)
    dondurma.dogrula(dondurma_yol)
    damga = dondurma.sha256(dondurma_yol)
    veri.hazirla()
    secim = [sabit.satir_al(satir_no)] if satir_no else list(sabit.satirlar())
    sonuc = []
    for s in secim:
        yol = cikti_dizini / f"satir_{s.no}.json"
        onceki = json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None
        if onceki is not None:
            if not (yeniden_altyapi and onceki.get("hata_turu") == "altyapi" and not onceki.get("yeniden_sayisi")):
                if ilerleme:
                    print(f"[v3 eleme] satır {s.no}: bitmiş ({onceki.get('durum')}), atlandı", flush=True)
                sonuc.append(onceki)
                continue
        if ilerleme:
            print(f"[v3 eleme] satır {s.no} {s.strateji} başlıyor", flush=True)
        r = kos.satir_calistir(s, veri.oku, veri.pf_oku, sabit.MALIYET_V2, isci=isci)
        r["dondurma_sha256"] = damga
        if onceki is not None:
            r["yeniden_sayisi"] = 1
            r["guncelleme"] = f"altyapı hatası sonrası bir kez yeniden koşuldu (önceki hata: {onceki.get('hata')})"
        dondurma.dogrula(dondurma_yol)                              # koşu sırasında kod/ön kayıt değişmiş olamaz
        _yaz_atomik(yol, r)
        if ilerleme:
            print(f"[v3 eleme] satır {s.no}: {r['durum']} ({r['sure_sn']} sn)" + (f" HATA: {r['hata']}" if r["hata"] else ""), flush=True)
        sonuc.append(r)
    return sonuc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m motor.arastirma.v3", description="v3 eleme (ON_KAYIT_V3)")
    ap.add_argument("komut", choices=["dondur", "destek", "eleme", "rapor"])
    ap.add_argument("--satir", type=int, default=None, help="eleme: yalnız bu satır (1-9)")
    ap.add_argument("--isci", type=int, default=1, help="eleme: rastgele-ağırlık testi için işçi süreç sayısı")
    ap.add_argument("--yeniden-altyapi", action="store_true", help="eleme: altyapı hatası veren satırı bir kez yeniden koş")
    ap.add_argument("--kirli-ok", action="store_true", help="dondur: commit edilmemiş dosya kontrolünü atla (yalnız geliştirme)")
    ap.add_argument("--gercek", action="store_true", help="destek: gerçek verinin zaman damgası kapsamını da yaz (performans hesaplanmaz)")
    a = ap.parse_args(argv)
    try:
        if a.komut == "dondur":
            d = dondurma.yaz(git_kontrol=not a.kirli_ok)
            print(f"dondurma yazıldı: commit {d['git_commit'][:12]}, ön kayıt {d['on_kayit_sha256'][:12]}, "
                  f"{sum(len(v) for v in d['dosyalar'].values())} dosya özeti")
            return 0
        if a.komut == "destek":
            from motor.arastirma.v3 import destek
            sonuc = destek.destek_kontrol(gercek=a.gercek)
            for r in sonuc:
                print(f"satır {r['no']} {r['strateji']}: {'OK' if r['ok'] else 'DESTEKLENMİYOR'} — {r['neden']}")
                if r.get("tur") == "tek":
                    print(f"    çıkış sütunları: {r.get('cikis')}; v2 yolu tutma süresini korur mu: {r.get('v2_tutma_korur')}; kullanılan: {r.get('kullanilan')}")
                if "kapsam" in r:
                    print(f"    kapsam: {r['kapsam']}")
            return 0 if all(r["ok"] for r in sonuc) else 1
        if a.komut == "eleme":
            eleme_calistir(a.satir, a.isci, a.yeniden_altyapi)
            return 0
        from motor.arastirma.v3 import rapor
        rapor.rapor_yaz()
        print(f"yazıldı: {sabit.ELEME_CSV}, {sabit.RAPOR_MD}")
        return 0
    except dondurma.DondurmaHatasi as e:
        print(f"HATA (dondurma): {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
