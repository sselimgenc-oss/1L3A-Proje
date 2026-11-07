"""Güncel ayar seçimi (Aşama 4 hazırlık): walk-forward kuralının İLERİYE doğru uygulanması.

Her final set stratejisi için ayar, VERİNİN SONUNDA biten son eğitim penceresinde seçilir:
  swing / portföy: eğitim 730 gün; daytrade: eğitim 365 gün (wf_tarama.PENCERE_GUN / wf_portfoy.EGITIM_GUN).
  Aday kümesi, skor (tek-grafik PF(R); portföy günlük Sharpe) ve asgari işlem AYNIDIR: kilit_testi.ayar_sec_tek /
  ayar_sec_portfoy (`guncel=True`) yeniden kullanılır.
Yenileme periyodu = WF test penceresi: swing/portföy 180 gün, daytrade 90 gün. Bir sonraki yenileme = eğitim bitiş günü + periyot.

KİLİT: kilitli dönem kullanılmış sayılır (ON_KAYIT); veri okumaları kilit_ac=True + sabit gerekçe ile yapılır ve
sonuclar/kilit_acilis.jsonl'a yazılır. Bu seçim kilit sınavının sonucunu DEĞİŞTİRMEZ (set sabit; yalnız paper ayarı).
Hata satıra yazılır (sessiz yutma yok).

CLI: python -m motor.arastirma.guncel_ayar   -> sonuclar/final/guncel_ayarlar.csv
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from motor.arastirma import final_set, kilit_testi
from motor.arastirma import wf_tarama as wf

KOK = Path(__file__).resolve().parents[2]
CIKTI = KOK / "sonuclar" / "final" / "guncel_ayarlar.csv"
GEREKCE = "Aşama 4 hazırlık: güncel ayar seçimi (kilit dönemi kullanılmış, ON_KAYIT)"
YENILEME_GUN = {"swing": 180, "daytrade": 90, "portfoy": 180}


def secim_yap(s: dict, veri_dizini=None) -> dict:
    """Tek bir final_set satırı için güncel ayar (kilit_testi fonksiyonlarını çağırır)."""
    if s["kol"] == "portfoy":
        return kilit_testi.ayar_sec_portfoy(s["strateji"], s["sembol"], s["tf"], veri_dizini, guncel=True, gerekce=GEREKCE)
    return kilit_testi.ayar_sec_tek(s["strateji"], s["sembol"], s["tf"], veri_dizini, guncel=True, gerekce=GEREKCE)


def tablo(set_: dict, veri_dizini=None, secici=secim_yap) -> pd.DataFrame:
    satirlar = []
    for s in set_["stratejiler"]:
        t0 = time.perf_counter()
        stil = "portfoy" if s["kol"] == "portfoy" else s["stil"]
        gun = YENILEME_GUN[stil]
        satir = {"kimlik": s["kimlik"], "stil": stil, "skor_turu": "gunluk_sharpe" if s["kol"] == "portfoy" else "pf_r",
                 "kilit_testi_ayari": s["kilit_testi_ayari"], "hata": ""}
        try:
            r = secici(s, veri_dizini)
            ayar = r["secilen_ayar"]
            bit = pd.Timestamp(r["egitim_bit"])
            satir.update({"ayar": ayar if isinstance(ayar, str) else "", "egitim_bas": r["egitim_bas"], "egitim_bit": r["egitim_bit"],
                          "egitim_skor": r["egitim_skor"], "egitim_islem": r["egitim_islem"], "veri_son": r["veri_son"],
                          "n_aday": r["n_aday"], "n_aday_hatali": r["n_aday_hatali"],
                          "yenileme_gun": gun,
                          "sonraki_yenileme": str((bit.floor("D") + pd.Timedelta(days=gun)).date())})
            if not satir["ayar"]:
                satir["hata"] = "ayar seçilemedi (eğitim penceresinde asgari işlem/gün sağlanmadı)"
            satir["kilit_ayarindan_farkli"] = bool(satir["ayar"] != s["kilit_testi_ayari"])
        except Exception as e:  # noqa: BLE001  (satıra yazılır)
            satir["hata"] = f"{type(e).__name__}: {e}"
            satir["kilit_ayarindan_farkli"] = ""
        satir["sure_sn"] = round(time.perf_counter() - t0, 1)
        satirlar.append(satir)
    cols = ["kimlik", "stil", "ayar", "kilit_testi_ayari", "kilit_ayarindan_farkli", "egitim_bas", "egitim_bit", "skor_turu",
            "egitim_skor", "egitim_islem", "yenileme_gun", "sonraki_yenileme", "veri_son", "n_aday", "n_aday_hatali", "hata", "sure_sn"]
    return pd.DataFrame(satirlar).reindex(columns=cols)


def main():
    set_ = final_set.yukle()
    df = tablo(set_)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CIKTI, index=False)
    print(df.drop(columns=["kilit_testi_ayari"]).to_string())
    print(f"[guncel_ayar] {CIKTI}: {len(df)} satır; hata {int((df['hata'].fillna('') != '').sum())}; "
          f"kilit ayarından farklı {int((df['kilit_ayarindan_farkli'] == True).sum())}")  # noqa: E712


if __name__ == "__main__":
    main()
