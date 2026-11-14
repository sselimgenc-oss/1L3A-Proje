"""Veri güveni + backtest bütünlük kartları (pano öncelik 4; envanter F36, F37). Hesap BURADA (motor); pano yalnız biçimler.

`veri_guveni.json` (sembol/tf başına): son mum zamanı, bayatlık (saglik.json ile AYNI sayı: seans takvimi `paper_takvim`), son `GUVEN_PENCERE_GUN`
günde eksik mum ve boşluk sayısı, veri kaynağı. Eksik mum = ardışık iki mum arasında piyasa AÇIKKEN beklenen ama gelmeyen mum yuvası
(kripto: duvar saati; hisse/emtia: yalnız seans içindeki yuvalar, hafta sonu/tatil/gece sayılmaz). Mum indeksi verilmediyse (backtest besleyici)
`eksik_mum: null` + neden (uydurma yok).

`butunluk.json`: pano/backtest durumunun dayandığı dosyaların sha256 özeti ↔ KAYITLI değer, kod sürümü (git commit). Kayıtlı değer:
  - maliyet tablosu: kendi mühür dosyası `sonuclar/evren/maliyet_tablosu.sha256` (araştırma katmanı koşulardan önce yazar);
  - diğerleri: `sonuclar/final/butunluk_kayit.json` (`python -m motor.canli.guven --kaydet --set eski` ile, kullanıcı onayıyla yazılır; bu modül otomatik YAZMAZ).
  PAPER V2 profili (`profil="v2"`): izlenen dosyalar `IZLENEN_V2` (paper_v2_seti.json, havuz_v2.csv, maliyet_tablosu_v2.csv + kendi .sha256 mührü),
  kayıt `stratejiler/butunluk_kayit_v2_20.json` (`python -m motor.canli.guven --kaydet`), maliyet_modeli = HESAP BAŞINA PortfoyAyarlari özeti
  (paper_v2.hesap_ayarlari: v2 tablosundan sembol bazlı maliyet); sert_limitler aynı kod sabiti.
  Eşleşmeme gizlenmez: `durum` = eslesti | uyusmuyor | kayit_yok | dosya_yok. Ayar yenilemesi `guncel_ayarlar.csv`'yi bilerek değiştirir:
  bu "uyusmuyor" gösterir ve kullanıcı yeni özeti kaydedene kadar öyle kalır (sessizce uydurulmaz).
Sanal kalemler (dosya değil, kod sabiti): `maliyet_modeli` (paper'ın PortfoyAyarlari maliyet/risk alanları), `sert_limitler` (SERT_LIMITLER değerleri).
Kod sürümü: `git rev-parse HEAD`; git yoksa/depo değilse `commit: null` + `neden` (ortam değişkeni `L3A_GIT_COMMIT` varsa o, kaynak "ortam").
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import pandas as pd

from motor.canli import durum as d
from motor.canli import paper_takvim as tk
from motor.veri.depo import aralik_suresi

KOK = Path(__file__).resolve().parents[2]
VERI_DIZINI = KOK / "veri" / "mumlar"
KAYIT_YOLU = KOK / "sonuclar" / "final" / "butunluk_kayit.json"
KAYIT_YOLU_V2_ESKI = KOK / "sonuclar" / "final" / "butunluk_kayit_v2.json"      # MÜHÜRLÜ: 10'lu setin kaydı; artık okunmaz/yazılmaz (kanıt olarak durur)
KAYIT_YOLU_V2 = KOK / "stratejiler" / "butunluk_kayit_v2_20.json"                  # 20'li set (10 + 6 kapanış adayı + 4 kapanış ek adayı, 2026-11-14) kaydı; 16'lık kayıt dosyası arşivde kalır; yalnız paper v2 profili
GUVEN_PENCERE_GUN = 30
GIT_ZAMAN_ASIMI_SN = 10
GIT_YOLLARI = ("motor", "stratejiler", "araclar", "sonuclar/final", "sonuclar/kilit", "sonuclar/evren")   # kirli denetimi (kilit_acilis.jsonl günlüğü hariç)
ONBELLEK_SN = 300

# (kimlik, yol, açıklama, mühür dosyası|None)
IZLENEN = (
    ("set_dosyasi", "stratejiler/final_set.json", "Final set: 7 strateji, kol payları, risk bütçesi, kilit testi ayarları", None),
    ("beklenti_araliklari", "sonuclar/final/beklenti_araliklari.csv", "Beklenti aralıkları (4/8 hafta persentiller, alarm eşikleri)", None),
    ("beklenti_islem_referansi", "sonuclar/final/beklenti_islem_referansi.csv", "Dersler için örneklem-dışı işlem referansı", None),
    ("guncel_ayarlar", "sonuclar/final/guncel_ayarlar.csv", "Paper'ın kullandığı güncel strateji ayarları", None),
    ("maliyet_tablosu", "sonuclar/evren/maliyet_tablosu.csv", "Sembol başına maliyet tablosu (mühürlü)", "sonuclar/evren/maliyet_tablosu.sha256"),
    ("kilit_set", "sonuclar/kilit/set.csv", "Kilit testi set günlük serisi (backtest görünümü buna birebir bağlıdır)", None),
    ("kilit_sonuc", "sonuclar/kilit/sonuc.csv", "Kilit testi strateji sonuçları (final set A grubu)", None),
)

# Paper v2 seti (10 strateji, hesap başına kasa): izlenen dosyalar. Eski sette olup v2'de karşılığı olmayanlar (beklenti aralıkları, güncel ayarlar,
# kilit testi) bilerek yok: v2 paper'ı onları kullanmaz. Maliyet tablosu kendi mühür dosyasıyla (araştırma katmanı yazar) karşılaştırılır.
IZLENEN_V2 = (
    ("set_dosyasi", "stratejiler/paper_v2_seti.json", "Paper v2 seti: 10 strateji, etiketler, hesap başına sermaye ve risk ölçeği", None),
    ("havuz", "stratejiler/havuz_v2.csv", "v2 havuzu (evren/tf/ayar kaynağı; set ile tutarlılık denetlenir)", None),
    ("maliyet_tablosu", "sonuclar/evren/v2/maliyet_tablosu_v2.csv", "v2 sembol başına maliyet tablosu (mühürlü)", "sonuclar/evren/v2/maliyet_tablosu_v2.sha256"),
)
PROFILLER = {
    "eski": {"izlenen": IZLENEN, "kayit_yolu": KAYIT_YOLU, "kayit_adi": "butunluk_kayit.json"},
    "v2": {"izlenen": IZLENEN_V2, "kayit_yolu": KAYIT_YOLU_V2, "kayit_adi": "butunluk_kayit_v2_20.json"},
}


def _profil(profil: str) -> dict:
    if profil not in PROFILLER:
        raise ValueError(f"bilinmeyen bütünlük profili: {profil!r} ({'|'.join(PROFILLER)})")
    return PROFILLER[profil]


# ---------------------------------------------------------------------------- yardımcılar
_SHA_ONBELLEK: dict = {}


def sha256_dosya(yol: Path) -> str:
    """Ham bayt sha256 (satır sonu dönüşümü yok). (yol, mtime, boyut) değişmedikçe önbellekten."""
    st = yol.stat()
    anahtar = (str(yol), st.st_mtime_ns, st.st_size)
    if anahtar not in _SHA_ONBELLEK:
        _SHA_ONBELLEK[anahtar] = hashlib.sha256(yol.read_bytes()).hexdigest()
    return _SHA_ONBELLEK[anahtar]


def sha256_sozluk(v: dict) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _git(kok: Path, *arg) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(kok), *arg], capture_output=True, text=True, timeout=GIT_ZAMAN_ASIMI_SN)


def kod_surumu(kok: Path = KOK) -> dict:
    """-> {commit, kisa, kirli, kirli_dosyalar, kaynak, neden}. Okunamayan değer null + neden."""
    ortam = os.environ.get("L3A_GIT_COMMIT", "").strip()
    try:
        r = _git(kok, "rev-parse", "HEAD")
    except FileNotFoundError:
        r = None
        neden = "git komutu bulunamadı"
    except subprocess.TimeoutExpired:
        r = None
        neden = f"git {GIT_ZAMAN_ASIMI_SN} sn içinde yanıt vermedi"
    else:
        neden = (r.stderr.strip().splitlines() or ["git rev-parse başarısız"])[0] if r.returncode != 0 else None
    if r is not None and r.returncode == 0:
        commit = r.stdout.strip()
        try:
            s = _git(kok, "status", "--porcelain", "--untracked-files=no", "--", *GIT_YOLLARI)
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return {"commit": commit, "kisa": commit[:8], "kirli": None, "kirli_dosyalar": [], "kaynak": "git",
                    "neden": f"kirli denetimi yapılamadı: {type(e).__name__}"}
        if s.returncode != 0:
            return {"commit": commit, "kisa": commit[:8], "kirli": None, "kirli_dosyalar": [], "kaynak": "git",
                    "neden": "kirli denetimi başarısız: " + ((s.stderr.strip().splitlines() or ["?"])[0])}
        kirli = [x[3:] for x in s.stdout.splitlines() if x.strip()]
        return {"commit": commit, "kisa": commit[:8], "kirli": bool(kirli), "kirli_dosyalar": kirli[:10], "kaynak": "git", "neden": None}
    if ortam:
        return {"commit": ortam, "kisa": ortam[:8], "kirli": None, "kirli_dosyalar": [], "kaynak": "ortam",
                "neden": f"git okunamadı ({neden}); L3A_GIT_COMMIT ortam değişkeni kullanıldı, çalışma ağacı denetlenemedi"}
    return {"commit": None, "kisa": None, "kirli": None, "kirli_dosyalar": [], "kaynak": None, "neden": neden}


def maliyet_modeli(ayarlar) -> dict:
    """PortfoyAyarlari'ndan yalnız maliyet/risk alanları (paper'ın gerçekten kullandığı model)."""
    a = dataclasses.asdict(ayarlar)
    alanlar = ("baslangic_sermaye", "risk_yuzde", "kaldirac", "komisyon_taker_yuzde", "komisyon_maker_yuzde", "hedef_limit_emri", "kayma_bps",
               "stop_kayma_bps", "limit_modu", "toplam_risk_tavani_yuzde", "max_pozisyon", "maliyet_sembol")
    return {k: a.get(k) for k in alanlar}


def sert_limitler() -> dict:
    from motor.risk.limitler import SERT_LIMITLER
    return dataclasses.asdict(SERT_LIMITLER)


# ---------------------------------------------------------------------------- kayıt (kullanıcı onayıyla yazılır)
def kayit_oku(yol: Path = KAYIT_YOLU) -> Optional[dict]:
    if not yol.exists():
        return None
    try:
        v = json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise d.DurumHatasi(f"{yol.name}: bozuk JSON ({e})") from e
    if not isinstance(v, dict) or "dosyalar" not in v:
        raise d.DurumHatasi(f"{yol.name}: 'dosyalar' alanı yok")
    return v


def _muhur(kok: Path, yol: str) -> Optional[str]:
    p = kok / yol
    if not p.exists():
        return None
    ilk = p.read_text(encoding="utf-8").split()
    return ilk[0].lower() if ilk else None


def _kalem(durum: str, sha: Optional[str], kayitli: Optional[str], kaynak: Optional[str], neden: Optional[str]) -> dict:
    return {"sha256": sha, "kayitli_sha256": kayitli, "kayit_kaynagi": kaynak,
            "eslesti": (sha == kayitli) if (sha and kayitli) else None, "durum": durum, "neden": neden}


def _karsilastir(sha: Optional[str], kayitli: Optional[str], kaynak: Optional[str], yok_neden: str) -> dict:
    if sha is None:
        return _kalem("dosya_yok", None, kayitli, kaynak, yok_neden)
    if kayitli is None:
        return _kalem("kayit_yok", sha, None, kaynak, "kayıtlı değer yok (python -m motor.canli.guven --kaydet)")
    if sha == kayitli:
        return _kalem("eslesti", sha, kayitli, kaynak, None)
    return _kalem("uyusmuyor", sha, kayitli, kaynak, "dosya kayıt alındıktan sonra değişmiş (ayar yenilemesi/elle değişiklik); yeni özet kullanıcı onayıyla kaydedilir")


def dosya_ozetleri(kok: Path = KOK, kayit: Optional[dict] = None, profil: str = "eski") -> list:
    """Her izlenen dosya için {id, ad, yol, sha256, kayitli_sha256, kayit_kaynagi, eslesti, durum, neden}."""
    kayit_d = (kayit or {}).get("dosyalar", {})
    pr = _profil(profil)
    out = []
    for kid, yol, ad, muhur in pr["izlenen"]:
        p = kok / yol
        sha = sha256_dosya(p) if p.exists() else None
        if muhur:
            kayitli, kaynak = _muhur(kok, muhur), muhur
            if kayitli is None:
                kayitli, kaynak = (kayit_d.get(kid) or {}).get("sha256"), pr["kayit_adi"]
        else:
            kayitli, kaynak = (kayit_d.get(kid) or {}).get("sha256"), pr["kayit_adi"]
        out.append({"id": kid, "ad": ad, "yol": yol, **_karsilastir(sha, kayitli, kaynak if kayitli else None, "dosya bu makinede yok")})
    return out


def sanal_ozetler(ayarlar, kayit: Optional[dict] = None, profil: str = "eski", maliyet: Optional[dict] = None) -> list:
    """Kod sabitleri (maliyet modeli, sert limitler). `ayarlar` None ise (backtest) maliyet modeli ölçülmez: null + neden.
    `maliyet` (v2): {hesap kimliği: maliyet_modeli(hesap ayarları)} — v2'de maliyet modeli hesap başınadır (sembol bazlı tablo + risk ölçeği);
    verilirse `ayarlar` yerine bu ölçülür."""
    kayit_s = (kayit or {}).get("sanal", {})
    kaynak_adi = _profil(profil)["kayit_adi"]
    out = []
    if maliyet is not None:
        out.append({"id": "maliyet_modeli", "ad": "Maliyet modeli (hesap başına PortfoyAyarlari, v2 maliyet tablosundan)",
                    "yol": "kod: motor/canli/paper_v2.py::hesap_ayarlari", "ayrinti": maliyet,
                    **_karsilastir(sha256_sozluk(maliyet), (kayit_s.get("maliyet_modeli") or {}).get("sha256"), kaynak_adi, "")})
    elif ayarlar is None:
        out.append({"id": "maliyet_modeli", "ad": "Maliyet modeli (paper PortfoyAyarlari)", "yol": "kod: motor/portfoy/motor.py::PortfoyAyarlari",
                    **_kalem("olculmedi", None, (kayit_s.get("maliyet_modeli") or {}).get("sha256"), None,
                             "backtest besleyici maliyeti kilit testi kodunda (secim.yeniden_oyna) uygular; ayrı tablo yok")})
    else:
        mm = maliyet_modeli(ayarlar)
        out.append({"id": "maliyet_modeli", "ad": "Maliyet modeli (paper PortfoyAyarlari)", "yol": "kod: motor/portfoy/motor.py::PortfoyAyarlari",
                    "ayrinti": mm, **_karsilastir(sha256_sozluk(mm), (kayit_s.get("maliyet_modeli") or {}).get("sha256"),
                                                  kaynak_adi, "")})
    sl = sert_limitler()
    out.append({"id": "sert_limitler", "ad": "Sert risk limitleri", "yol": "kod: motor/risk/limitler.py::SERT_LIMITLER", "ayrinti": sl,
                **_karsilastir(sha256_sozluk(sl), (kayit_s.get("sert_limitler") or {}).get("sha256"), kaynak_adi, "")})
    return out


_BUTUNLUK_ONBELLEK: dict = {}


def butunluk(kaynak: str, zaman: str, ayarlar=None, kok: Path = KOK, kayit_yolu: Optional[Path] = None, onbellek_sn: float = ONBELLEK_SN,
             profil: str = "eski", maliyet: Optional[dict] = None) -> dict:
    """butunluk.json içeriği. profil: "eski" (7'li final set) | "v2" (paper v2 seti; kayıt butunluk_kayit_v2_20.json, `maliyet` = hesap başına model). Hesap pahalı değil ama her turda git çağırmamak için `onbellek_sn` kadar kod sürümü önbelleğe alınır
    (dosya özetleri mtime ile zaten önbellekli; değişiklik anında görünür)."""
    kayit_yolu = kayit_yolu or _profil(profil)["kayit_yolu"]
    kayit = kayit_oku(kayit_yolu)
    anahtar = str(kok)
    simdi = time.monotonic()
    k = _BUTUNLUK_ONBELLEK.get(anahtar)
    if k is None or simdi - k[0] >= onbellek_sn:
        k = (simdi, kod_surumu(kok))
        _BUTUNLUK_ONBELLEK[anahtar] = k
    dosyalar = dosya_ozetleri(kok, kayit, profil)
    sanal = sanal_ozetler(ayarlar, kayit, profil, maliyet)
    tum = dosyalar + sanal
    sayim = Counter(x["durum"] for x in tum)
    if sayim.get("uyusmuyor"):
        genel = "uyusmuyor"
    elif sayim.get("kayit_yok") or sayim.get("dosya_yok") or sayim.get("olculmedi"):
        genel = "eksik"
    else:
        genel = "eslesti"
    return {**d._zarf("butunluk", kaynak, zaman), "kod_surumu": k[1], "dosyalar": dosyalar, "sanal": sanal, "genel_durum": genel, "profil": profil,
            "sayim": {a: sayim.get(a, 0) for a in ("eslesti", "uyusmuyor", "kayit_yok", "dosya_yok", "olculmedi")},
            "kayit_dosyasi": str(kayit_yolu.relative_to(kok)) if kayit_yolu.is_relative_to(kok) else str(kayit_yolu),
            "kayit_zamani": (kayit or {}).get("kaydedildi"),
            "not": "sha256 ham baytlardandır. Kayıt kullanıcı onayıyla yazılır; ayar yenilemesi guncel_ayarlar.csv'yi bilerek değiştirir "
                   "(o zaman 'uyuşmuyor' görünür, yeni özet onayla kaydedilir). Backtest sonuçları sonuclar/kilit/set.csv'ye birebir bağlıdır."}


def kaydet(ayarlar, kaydedildi: str, kok: Path = KOK, kayit_yolu: Optional[Path] = None, profil: str = "eski",
           maliyet: Optional[dict] = None) -> dict:
    """Güncel özetleri kayıt dosyasına yazar (KULLANICI ONAYIYLA çağrılır; motor otomatik çağırmaz). Mühürlü dosyalar (.sha256) kendi mührünü kullanır."""
    kayit_yolu = kayit_yolu or _profil(profil)["kayit_yolu"]
    dosyalar = {}
    for kid, yol, ad, muhur in _profil(profil)["izlenen"]:
        p = kok / yol
        if not p.exists():
            raise FileNotFoundError(f"{yol}: kayıt için dosya yok")
        dosyalar[kid] = {"yol": yol, "sha256": sha256_dosya(p), "ad": ad}
    mm = maliyet if maliyet is not None else maliyet_modeli(ayarlar)
    sanal = {"maliyet_modeli": {"sha256": sha256_sozluk(mm), "ayrinti": mm},
             "sert_limitler": {"sha256": sha256_sozluk(sert_limitler()), "ayrinti": sert_limitler()}}
    kod = kod_surumu(kok)
    veri = {"surum": 1, "profil": profil, "kaydedildi": kaydedildi, "kod_commit": kod["commit"], "dosyalar": dosyalar, "sanal": sanal,
            "not": "Bu kayıt butunluk.json'daki 'kayıtlı değer'dir. Güncellemek kullanıcı kararıdır."}
    d.atomik_yaz_json(kayit_yolu, veri)
    return veri


# ---------------------------------------------------------------------------- veri güveni
def kaynak_bilgisi(sembol: str, canli: bool, veri_dizini: Path = VERI_DIZINI) -> dict:
    """-> {kaynak (binance_perp|dukascopy|yahoo), kaynak_ayrinti, spot_vekil {bas,bit,perp_baslangic}|None, spot_vekil_neden}.
    canli=True (paper servis): TradFi sembolleri Binance TradFi perpetual'dan akar, geçmiş tohum Dukascopy. canli=False (tekrar/backtest): yerel arşiv."""
    if sembol.startswith("DK_"):
        if canli:
            return {"kaynak": "binance_perp", "kaynak_ayrinti": "Binance TradFi perpetual (canlı REST/WS); geçmiş tohum Dukascopy",
                    "spot_vekil": None, "spot_vekil_neden": None}
        return {"kaynak": "dukascopy", "kaynak_ayrinti": "Dukascopy (yerel arşiv)", "spot_vekil": None, "spot_vekil_neden": None}
    if sembol.startswith("BIST_"):
        return {"kaynak": "yahoo", "kaynak_ayrinti": "Yahoo Finance (yerel arşiv)", "spot_vekil": None, "spot_vekil_neden": None}
    ayr = "Binance USDⓈ-M perpetual (canlı REST/WS)" if canli else "Binance USDⓈ-M perpetual (yerel arşiv)"
    yol = Path(veri_dizini) / sembol / "kaynak.json"
    if not yol.exists():
        return {"kaynak": "binance_perp", "kaynak_ayrinti": ayr, "spot_vekil": None, "spot_vekil_neden": f"{sembol}/kaynak.json bu makinede yok"}
    try:
        k = json.loads(yol.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"kaynak": "binance_perp", "kaynak_ayrinti": ayr, "spot_vekil": None, "spot_vekil_neden": f"{sembol}/kaynak.json bozuk: {e}"}
    if k.get("spot_vekil_baslangic"):
        return {"kaynak": "binance_perp", "kaynak_ayrinti": ayr + "; perp öncesi geçmiş spot vekil", "spot_vekil_neden": None,
                "spot_vekil": {"bas": str(k["spot_vekil_baslangic"]), "bit": str(k.get("spot_vekil_bitis")), "perp_baslangic": str(k.get("perp_baslangic"))}}
    return {"kaynak": "binance_perp", "kaynak_ayrinti": ayr, "spot_vekil": None, "spot_vekil_neden": None}


def bosluk_olc(sembol: str, tf: str, indeks: pd.DatetimeIndex, simdi, gun: int = GUVEN_PENCERE_GUN) -> dict:
    """Son `gun` günde, KAPANMIŞ mumlar arasında piyasa açıkken beklenen ama gelmeyen mum yuvaları.
    -> {pencere_mum, eksik_mum, bosluk_sayisi, en_uzun_bosluk_mum}. Kapanışı `simdi`den sonra olan mum sayılmaz (lookahead yok);
    son mumdan `simdi`ye kadar olan süre eksik değil BAYATLIKtır (saglik/bayatlik_dk)."""
    a = aralik_suresi(tf)
    simdi = pd.Timestamp(simdi)
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    ix = pd.DatetimeIndex(indeks)
    ix = ix.tz_localize("UTC") if ix.tz is None else ix.tz_convert("UTC")
    ix = ix[(ix >= simdi - pd.Timedelta(days=gun)) & (ix + a <= simdi)].sort_values()
    eksik = bosluk = enuzun = 0
    kripto = tk.tur(sembol) == "kripto"
    for onceki, sonraki in zip(ix[:-1], ix[1:]):
        kap = onceki + a
        if sonraki <= kap:
            continue
        if kripto:
            n = int((sonraki - kap) // a)
        else:
            dk = pd.date_range(kap, sonraki - pd.Timedelta(minutes=1), freq="1min")
            ac = dk[tk.seans_maskesi(sembol, dk)]
            n = len(set(((ac - kap) // a).tolist())) if len(ac) else 0
        if n > 0:
            eksik += n
            bosluk += 1
            enuzun = max(enuzun, n)
    return {"pencere_mum": int(len(ix)), "eksik_mum": eksik, "bosluk_sayisi": bosluk, "en_uzun_bosluk_mum": enuzun}


def veri_guveni(saglik_veri: list, mum_indeksleri: Optional[dict], simdi, kaynak: str, zaman: str, veri_dizini: Path = VERI_DIZINI,
                gun: int = GUVEN_PENCERE_GUN) -> dict:
    """veri_guveni.json içeriği. saglik_veri: saglik.json `veri[]` (bayatlık orada hesaplanmıştır; AYNI sayı kopyalanır).
    mum_indeksleri: {(sembol, tf): DatetimeIndex} | None."""
    canli = kaynak != "backtest"
    satirlar = []
    for v in saglik_veri:
        s, tf = v["sembol"], v["tf"]
        ix = (mum_indeksleri or {}).get((s, tf))
        kapanis = pd.Timestamp(v["son_mum_zamani"]) + aralik_suresi(tf)
        satir = {"sembol": s, "tf": tf, "seans": v.get("seans") or tk.tur(s), "son_mum_acilis": v["son_mum_zamani"],
                 "son_mum_kapanis": d.zaman_str(kapanis), "bayatlik_dk": v["bayatlik_dk"], "esik_dk": v["esik_dk"], "bayat": bool(v["bayat"]),
                 **kaynak_bilgisi(s, canli, veri_dizini)}
        if ix is None:
            satir.update({"pencere_mum": None, "eksik_mum": None, "bosluk_sayisi": None, "en_uzun_bosluk_mum": None,
                          "eksik_neden": "mum indeksi bu kaynakta tutulmaz (backtest besleyici günlük seriyi yeniden oynatır); eksik mum ölçülmedi"})
        else:
            satir.update({**bosluk_olc(s, tf, ix, simdi, gun), "eksik_neden": None})
        satirlar.append(satir)
    olculen = [x for x in satirlar if x["eksik_mum"] is not None]
    ozet = {"seri_sayisi": len(satirlar), "bayat_sayisi": sum(1 for x in satirlar if x["bayat"]),
            "eksik_mum_toplam": sum(x["eksik_mum"] for x in olculen) if olculen else None,
            "bosluk_toplam": sum(x["bosluk_sayisi"] for x in olculen) if olculen else None,
            "olculmeyen_seri": len(satirlar) - len(olculen),
            "kaynaklar": dict(Counter(x["kaynak"] for x in satirlar))}
    return {**d._zarf("veri_guveni", kaynak, zaman), "pencere_gun": gun, "semboller": satirlar, "ozet": ozet,
            "not": f"Eksik mum: son {gun} günde kapanmış mumlar arasında piyasa açıkken gelmeyen yuvalar (hisse/emtia: yalnız seans içi). "
                   "Bayatlık saglik.json ile aynı sayıdır (son mum kapanışından beri seans dakikası)."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backtest bütünlük kaydı (sha256 özetleri) — KULLANICI ONAYIYLA çalıştırın")
    ap.add_argument("--kaydet", action="store_true", help="güncel özetleri sonuclar/final/butunluk_kayit.json'a yaz")
    ap.add_argument("--goster", action="store_true", help="kayıtlı değerlerle karşılaştırmayı yazdır (varsayılan)")
    ap.add_argument("--set", choices=tuple(PROFILLER), default="v2", dest="set_adi",
                    help="v2 (varsayılan): paper v2 seti, kayıt butunluk_kayit_v2_20.json | eski: 7'li final set, kayıt butunluk_kayit.json")
    a = ap.parse_args(argv)
    from motor.portfoy.motor import PortfoyAyarlari
    ay = PortfoyAyarlari(limit_modu="uygula")
    mal = None
    if a.set_adi == "v2":
        from motor.canli import paper_v2 as v2
        mal = v2.cevrimdisi_maliyet_modeli()       # sunucudaki PaperKasalar'la aynı hesap (bkz. fonksiyon açıklaması)
    yol = PROFILLER[a.set_adi]["kayit_yolu"]
    if a.kaydet:
        from datetime import datetime, timezone
        v = kaydet(ay, d.zaman_str(datetime.now(timezone.utc)), profil=a.set_adi, maliyet=mal)
        print(f"[guven] kayıt yazıldı: {yol} ({len(v['dosyalar'])} dosya, {len(v['sanal'])} sanal kalem, commit {v['kod_commit']})")
        return 0
    b = butunluk("paper", d.zaman_str(pd.Timestamp.now(tz="UTC")), ay, profil=a.set_adi, maliyet=mal)
    for x in b["dosyalar"] + b["sanal"]:
        print(f"{x['durum']:10s} {x['id']:26s} {(x.get('sha256') or '-')[:12]}")
    print(f"genel: {b['genel_durum']}; kod: {b['kod_surumu']['kisa']} kirli={b['kod_surumu']['kirli']}")
    return 0 if b["genel_durum"] == "eslesti" else 1


if __name__ == "__main__":
    raise SystemExit(main())
