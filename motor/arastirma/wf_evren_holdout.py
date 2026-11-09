"""Evren holdout aşaması (ON_KAYIT Güncelleme 5.1): son 12 ay (2025-11-08 -> veri sonu), BİR KEZ.

Akış: secim aşaması iyi/iyiye yakın listelerini yazar ve mühürler (`liste_muhru.json`, sürüm 2: listeler + wf_evren.parquet +
saglamlik.parquet + pbo.csv sha256'ları, maliyet tablosu hash'i, ölçüt/eşik hash'i, koşulacak ayar ve dışlanan semboller,
stratejilerin kaynak + kart dosyası hash'leri). Holdout aşaması önce mührü doğrular (herhangi bir uyuşmazlık HoldoutHatasi:
DUR), sonra listedeki her stratejiyi MÜHÜRLÜ kayıttaki ayarla (WF'nin geliştirme dönemindeki SON seçilen ayarı) holdout'ta
tek koşuda sınar. Sembol hatası sayılır; varsa satır durum='hata'. Kapı: evren net > 0 ve PF(R) >= 1.1 ->
"dogrulanmis", aksi "holdout_ta_kaldi". Holdout sonucuna göre ayar/eşik/liste DEĞİŞTİRİLMEZ.

Bir kerelik: `holdout/holdout_gunlugu.jsonl` (yalnız ekler). Herhangi bir "basladi" kaydı varsa yeniden koşu HoldoutTekrarHatasi
verir; zorla=True + boş olmayan gerekçe ile açılır ve günlüğe yazılır. Holdout verisi yalnız burada okunur (donem="holdout").
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from motor.arastirma import evren_maliyet, saglamlik, tarama
from motor.arastirma import wf_evren as we

MUHUR = "liste_muhru.json"
GUNLUK = "holdout/holdout_gunlugu.jsonl"
LISTE_DOSYALARI = ("iyi_liste.csv", "iyiye_yakin_liste.csv", "secim.csv")
# Denetim O3/Ö4: listeleri üreten girdiler de mühürlü (WF ayar seçimleri + dışlamalar, sağlamlık, PBO).
MUHUR_DOSYALARI = LISTE_DOSYALARI + ("wf_evren.parquet", "saglamlik.parquet", "pbo.csv")
MUHUR_SURUM = 3                    # 3: + evren üyeliği, git commit, ortak motor modülleri hash'i (denetim Y-4). 2 hâlâ okunur.
OKUNUR_SURUMLER = (2, 3)
# Tüm stratejileri etkileyen ortak motor/takvim modülleri (strateji kaynağı hash'i bunları kapsamaz).
ORTAK_MODULLER = ("motor/backtest/motor.py", "motor/backtest/metrikler.py", "motor/backtest/walk_forward.py",
                  "motor/backtest/eleme.py", "motor/backtest/deneme_kaydi.py", "motor/risk/limitler.py",
                  "motor/strateji/seans_takvimi.py", "motor/strateji/daytrade/_ortak.py", "motor/strateji/kayit.py",
                  "motor/arastirma/evren_maliyet.py", "motor/arastirma/wf_evren.py", "motor/arastirma/saglamlik.py",
                  "motor/arastirma/tarama.py", "motor/arastirma/wf_evren_holdout.py")


class HoldoutHatasi(RuntimeError):
    """Liste mührü bozuk / eksik: holdout reddedilir."""


class HoldoutTekrarHatasi(HoldoutHatasi):
    """Holdout daha önce başlatılmış (bir kerelik)."""


def _sha(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest() if Path(yol).exists() else ""


def gunluk_oku(cikti: Path) -> list:
    yol = Path(cikti) / GUNLUK
    if not yol.exists():
        return []
    return [json.loads(x) for x in yol.read_text(encoding="utf-8").splitlines() if x.strip()]


def holdout_baslamis_mi(cikti: Path) -> bool:
    return any(k.get("olay") == "basladi" for k in gunluk_oku(cikti))


def olcut_hash() -> str:
    """Geçme ölçütleri + kıl payı eşikleri (OLCUT, YAKIN_OLCUT) JSON'unun sha256'sı."""
    j = json.dumps({"OLCUT": we.OLCUT, "YAKIN_OLCUT": we.YAKIN_OLCUT}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(j.encode()).hexdigest()


def evren_imzasi() -> dict:
    """{stil: {"imza": we.evren_imza(...), "semboller": [sıralı]}} — etkin evren üyeliği (EVREN_STIL / deneme geçersiz kılması)."""
    out = {}
    for stil in sorted(we.EVREN_STIL):
        ev = sorted(we.evren_stil(stil))
        out[stil] = {"imza": we.evren_imza(ev), "semboller": ev}
    return out


def git_commit() -> str:
    """Çalışma kopyasının HEAD commit hash'i; git yok/depo değilse 'yok'."""
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=we.KOK, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "yok"
    h = r.stdout.strip()
    return h if r.returncode == 0 and len(h) >= 7 else "yok"


def _commit_ata_mi(muhurlu: str, simdi: str) -> bool:
    """Mühürdeki commit şimdiki HEAD'in atası (ya da aynısı) mı? Biri 'yok' ise karşılaştırılamaz -> True (ortak modül hash'leri
    kod değişimini zaten yakalar); git komutu çalışmazsa da karşılaştırılamaz sayılır."""
    import subprocess
    if "yok" in (muhurlu, simdi) or muhurlu == simdi:
        return True
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", muhurlu, simdi], cwd=we.KOK, capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return True
    return r.returncode == 0


def ortak_modul_hashleri() -> dict:
    """{göreli yol: sha256} — paylaşılan motor/takvim modülleri (dosya yoksa ''; mühürden sonra eklenir/silinirse fark çıkar)."""
    return {y: _sha(we.KOK / y) for y in ORTAK_MODULLER}


def strateji_dosyalari(ad: str, stil: str) -> list:
    """Stratejinin kaynak dosyaları (sınıf + proje içindeki tüm ata sınıfların modülleri) ve ayar/kart dosyaları
    (stratejiler/kart_ayarlari/<ad>.json, stratejiler/dis_ayarlari/<ad>.json; varsa). -> KOK'a göre göreli yollar (sıralı)."""
    import inspect
    from motor.strateji import kayit
    if stil == "portfoy":
        from motor.portfoy.stratejiler import tum_portfoy_stratejileri
        sinif = tum_portfoy_stratejileri()[ad]
    else:
        sinif = kayit.al(ad)
    yollar = set()
    for c in sinif.__mro__:
        if c is object:
            continue
        try:
            f = inspect.getsourcefile(c)
        except TypeError:                                  # yerleşik sınıf: proje dosyası değil
            continue
        if f and Path(f).resolve().is_relative_to(we.KOK):
            yollar.add(Path(f).resolve())
    for d in (kayit.KART_AYAR_DIZINI, tarama.DIS_AYAR_DIZINI):
        if (Path(d) / f"{ad}.json").exists():
            yollar.add((Path(d) / f"{ad}.json").resolve())
    return sorted(str(y.relative_to(we.KOK)) for y in yollar)


def strateji_hashleri(kosular: list) -> dict:
    """{strateji: {göreli yol: sha256}} — listedeki her stratejinin kaynak + kart/ayar dosyaları."""
    out = {}
    for k in kosular:
        if k["strateji"] not in out:
            out[k["strateji"]] = {y: _sha(we.KOK / y) for y in strateji_dosyalari(k["strateji"], k["stil"])}
    return out


def holdout_kosulari(cikti: Path) -> list:
    """iyi + iyiye yakın listelerindeki her strateji için holdout'ta koşulacak SABİT girdiler (mühre yazılır):
    WF'nin son seçilen ayarı ve dışlanan semboller (kisa_gecmis/disarida/hatali_sembol) wf_evren.parquet'ten."""
    cikti = Path(cikti)
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    kosular = []
    for liste, dosya in (("iyi", "iyi_liste.csv"), ("iyiye_yakin", "iyiye_yakin_liste.csv")):
        f = cikti / dosya
        if not (f.exists() and f.stat().st_size > 5):
            continue
        for r in pd.read_csv(f).to_dict("records"):
            w = wf[(wf["strateji"] == r["strateji"]) & (wf["tf"] == r["tf"])]
            if len(w) != 1:
                raise HoldoutHatasi(f"{r['strateji']} {r['tf']}: wf_evren.parquet'te {len(w)} satır (tam 1 olmalı)")
            w = w.iloc[0]
            dis = sorted({x for col in ("kisa_gecmis", "disarida", "hatali_sembol") for x in str(w.get(col) or "").split(",") if x})
            kosular.append({"liste": liste, "strateji": r["strateji"], "tf": r["tf"], "stil": r["stil"],
                            "ayar": son_secilen_ayar(w["secimler"]), "dislanan": dis,
                            "gelistirme_pf": _sayi(w.get("profit_factor")), "gelistirme_sharpe": _sayi(w.get("sharpe"))})
    return kosular


def _sayi(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def muhur_yaz(cikti: Path) -> dict:
    """secim aşaması çıktıları yazıldıktan sonra çağrılır. Holdout başlamışsa listeler artık değiştirilemez.
    Mühür (sürüm 3; 2 de okunur; v3 = v2 + evren üyeliği, git commit, ortak modül hash'leri): MUHUR_DOSYALARI sha256 (listeler + wf_evren.parquet + saglamlik.parquet + pbo.csv; hepsi VAR olmalı),
    maliyet tablosu hash'i, ölçüt/eşik JSON hash'i, holdout koşuları (strateji, tf, stil, ayar, dışlanan) ve listedeki
    stratejilerin kaynak + kart/ayar dosyası hash'leri."""
    cikti = Path(cikti)
    if holdout_baslamis_mi(cikti):
        raise HoldoutHatasi("holdout daha önce başlatıldı: iyi/iyiye yakın listeleri ve mühür değiştirilemez")
    eksik = [f for f in MUHUR_DOSYALARI if not (cikti / f).exists()]
    if eksik:
        raise HoldoutHatasi(f"mühürlenecek dosya yok: {eksik}")
    kosular = holdout_kosulari(cikti)
    m = {"surum": MUHUR_SURUM, "zaman": datetime.now(timezone.utc).isoformat(),
         "dosyalar": {f: _sha(cikti / f) for f in MUHUR_DOSYALARI},
         "maliyet_hash": evren_maliyet.tablo_hash(), "olcut_hash": olcut_hash(),
         "kosular": kosular, "strateji_hash": strateji_hashleri(kosular),
         "evren": evren_imzasi(), "git_commit": git_commit(), "ortak_modul_hash": ortak_modul_hashleri()}
    (cikti / MUHUR).write_text(json.dumps(m, ensure_ascii=False, indent=1))
    return m


def muhur_kontrol(cikti: Path) -> dict:
    """Mührü doğrular; herhangi bir uyuşmazlıkta HoldoutHatasi (holdout DURUR, günlüğe 'basladi' yazılmaz)."""
    cikti = Path(cikti)
    yol = cikti / MUHUR
    if not yol.exists():
        raise HoldoutHatasi(f"{MUHUR} yok: önce secim aşaması listeleri yazıp mühürlemeli")
    m = json.loads(yol.read_text())
    if m.get("surum") not in OKUNUR_SURUMLER or set(m.get("dosyalar", {})) != set(MUHUR_DOSYALARI):
        raise HoldoutHatasi(f"{MUHUR} eski/eksik biçimde (sürüm {m.get('surum')}); secim aşamasını yeniden koşup mühürleyin")
    for f, h in m["dosyalar"].items():
        if _sha(cikti / f) != h:
            raise HoldoutHatasi(f"liste değişmiş: {f} (mühürlü hash ile uyuşmuyor); holdout reddedildi")
    if m.get("maliyet_hash") != evren_maliyet.tablo_hash():
        raise HoldoutHatasi("maliyet tablosu mühürden sonra değişmiş; holdout reddedildi")
    if m.get("olcut_hash") != olcut_hash():
        raise HoldoutHatasi("geçme ölçütleri/eşikler (OLCUT/YAKIN_OLCUT) mühürden sonra değişmiş; holdout reddedildi")
    if holdout_kosulari(cikti) != m["kosular"]:              # mühür dosyası elle düzenlenmişse (hash'li girdilerle çelişki)
        raise HoldoutHatasi("mühürdeki holdout koşuları (ayar/dışlanan) mühürlü listeler + wf_evren.parquet ile uyuşmuyor; "
                            "holdout reddedildi")
    simdi = strateji_hashleri(m["kosular"])
    for ad, dosyalar in m["strateji_hash"].items():
        if simdi.get(ad) != dosyalar:
            fark = sorted(set(dosyalar.items()) ^ set(simdi.get(ad, {}).items()))
            raise HoldoutHatasi(f"strateji kodu/kartı mühürden sonra değişmiş: {ad} ({fark[0][0] if fark else '?'}); "
                                "holdout reddedildi")
    if m["surum"] >= 3:                                         # v2 mühürlerde bu alanlar yok: yalnız eski kontroller
        if m.get("evren") != evren_imzasi():
            raise HoldoutHatasi("evren üyeliği (EVREN_STIL sembol listeleri) mühürden sonra değişmiş; holdout reddedildi")
        simdi_ortak, muh_ortak = ortak_modul_hashleri(), m.get("ortak_modul_hash")
        if muh_ortak != simdi_ortak:
            fark = sorted(y for y in set(simdi_ortak) | set(muh_ortak or {}) if (muh_ortak or {}).get(y) != simdi_ortak.get(y))
            raise HoldoutHatasi(f"ortak motor modülü mühürden sonra değişmiş: {fark[0] if fark else '?'}; holdout reddedildi")
        if not _commit_ata_mi(str(m.get("git_commit", "")), git_commit()):
            raise HoldoutHatasi("mühürdeki git commit şimdiki HEAD'in atası değil (geçmiş yeniden yazılmış); holdout reddedildi")
    return m


def son_secilen_ayar(secimler_json: str) -> Optional[str]:
    """WF'nin geliştirme dönemindeki SON seçilen ayarı (ayar seçilen son pencere)."""
    for s in reversed(json.loads(secimler_json)):
        if s.get("secilen") is not None and s.get("ayar"):
            return s["ayar"]
    return None


def holdout_kos(ad: str, tf: str, stil: str, etiket: str, dislanan=(), ayar=None) -> dict:
    """Tek strateji, tek ayar, evrende holdout (girişi >= HOLDOUT_BAS). veri_ayarla(..., 'holdout') kurulu olmalı."""
    evren = [s for s in we.evren_stil(stil) if s not in set(dislanan)]
    st = saglamlik.ayar_coz(ad, etiket)
    parcalar, n_veri, sem_hata = [], 0, {}
    for sembol in evren:
        try:
            mumlar, fund = we._veri(sembol, tf)
        except (FileNotFoundError, ValueError):
            continue
        if not len(mumlar) or mumlar.index[-1] < we.HOLDOUT_BAS:
            continue
        n_veri += 1
        kural = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
        t = we.sembol_islemleri(st, sembol, tf, mumlar, fund, evren_maliyet.maliyet_ayarlari(sembol, kural, 1.0), sem_hata)
        if t is None or not len(t):                   # hata sayılır (O4); FundingYokHatasi 'beklenen' (K-L)
            continue
        o = we.islem_ozet(t, 0)
        o = o[pd.DatetimeIndex(o["giris_zamani"]) >= we.HOLDOUT_BAS].copy()
        if len(o):
            o["sembol"] = sembol
            o["son_mum"] = mumlar.index[-1]
            parcalar.append(o)
    satir = {"n_enstruman_veri": n_veri, **we.hata_ozeti(sem_hata)}
    if not parcalar:
        satir.update(islem_sayisi=0, net_getiri=0.0, profit_factor=math.nan, nedenler="holdout'ta işlem yok")
        return satir
    oos = pd.concat(parcalar, ignore_index=True)
    bit = oos["son_mum"].max() + pd.Timedelta(1, "ns")
    oos, atilan = we.sembol_cakismasini_ele(oos.drop(columns="son_mum"))
    m = we.kasa_metrikleri(we.oynatma_tablosu(oos, tuple(evren), carpan=1.0), we.HOLDOUT_BAS, bit, ayar)
    for kx in ("kabul", "pnl", "getiri_serisi", "sinif_net", "enstruman_net", "enstruman_adet"):
        m.pop(kx, None)
    satir.update(m)
    satir.update(holdout_bit=str(bit), cakisma_atilan=atilan)
    return satir


def kapi(m: dict) -> bool:
    pf = m.get("profit_factor")
    return (m.get("islem_sayisi", 0) or 0) > 0 and (m.get("net_getiri", 0.0) or 0.0) > 0 \
        and pf is not None and not (isinstance(pf, float) and math.isnan(pf)) and pf >= we.OLCUT["holdout_pf"]


def holdout_asamasi(cikti: Path, donem: str = "2017_gelistirme", veri_dizini=None, zorla: bool = False,
                    gerekce: str = "", ayar=None) -> pd.DataFrame:
    cikti = Path(cikti)
    muhur = muhur_kontrol(cikti)                                     # liste değişmişse HoldoutHatasi
    (cikti / "holdout").mkdir(parents=True, exist_ok=True)
    if holdout_baslamis_mi(cikti):
        if not zorla:
            raise HoldoutTekrarHatasi("holdout bir kerelik ve daha önce başlatıldı; tekrar için zorla=True ve gerekçe gerekir "
                                      "(günlüğe yazılır, yöntem ihlali olarak raporlanır)")
        if not isinstance(gerekce, str) or not gerekce.strip():
            raise HoldoutTekrarHatasi("zorla tekrar için boş olmayan gerekçe zorunlu")
    elif zorla:
        raise HoldoutTekrarHatasi("zorla bayrağı yalnız daha önce koşulmuş holdout için anlamlı; ilk koşuda kullanılmaz")

    def yaz(k):
        with open(cikti / GUNLUK, "a", encoding="utf-8") as f:
            f.write(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), **k}, ensure_ascii=False) + "\n")
    yaz({"olay": "basladi", "zorla": bool(zorla), "gerekce": gerekce, "muhur": muhur["dosyalar"], "donem": donem})
    we.veri_ayarla(veri_dizini, "holdout")
    satirlar = []
    for k in muhur["kosular"]:                                       # ayar + dışlamalar MÜHÜRLÜ kayıttan (O3)
        ad, tf, stil, etiket = k["strateji"], k["tf"], k["stil"], k["ayar"]
        satir = {"liste": k["liste"], "strateji": ad, "tf": tf, "stil": stil, "ayar": etiket or "", "hata": "",
                 "gelistirme_pf": k.get("gelistirme_pf"), "gelistirme_sharpe": k.get("gelistirme_sharpe")}
        if etiket is None:
            satir.update(durum="holdout_ta_kaldi", nedenler="WF'de seçilen ayar yok")
        else:
            dis = set(k["dislanan"])
            try:
                if stil == "portfoy":
                    from motor.arastirma import wf_evren_portfoy
                    satir.update(wf_evren_portfoy.holdout_kos(ad, etiket, tf, dis, ayar))
                else:
                    satir.update(holdout_kos(ad, tf, stil, etiket, dis, ayar))
                if satir.get("n_hata_sembol"):                         # O4: sembol hatası -> satır 'hata' (doğrulanmış sayılmaz)
                    satir.update(hata=f"{satir['n_hata_sembol']} sembol hatası; ilk: {satir['hata_ornegi']}"[:300],
                                 durum="hata", nedenler="sembol hatası")
                else:
                    satir["durum"] = "dogrulanmis" if kapi(satir) else "holdout_ta_kaldi"
            except Exception as e:  # noqa: BLE001  (satıra yazılır, durum 'hata')
                satir.update(hata=f"{type(e).__name__}: {e}"[:300], durum="hata", nedenler="hata")
        satirlar.append(satir)
    df = pd.DataFrame(satirlar)
    df.to_csv(cikti / "holdout" / "holdout.csv", index=False)
    yaz({"olay": "bitti", "n": len(df), "dogrulanmis": int((df["durum"] == "dogrulanmis").sum()) if len(df) else 0,
         "hata": int((df["durum"] == "hata").sum()) if len(df) else 0})
    return df
