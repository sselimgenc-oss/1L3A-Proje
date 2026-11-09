"""v2 Aşama 6 — mühür (6.3) ve holdout (bölüm 7; P1-6). Holdout verisini okuyan TEK modül (yalnız `GercekSaglayici`).

Akış (bölüm 7):
 1. Mühür doğrulanır (uyuşmazlık = HoldoutHatasi, DUR). Set boşsa ("0 strateji") holdout AÇILMAZ. Günlüğe "basladi" VERİ OKUNMADAN
    önce yazılır; kayıt varsa ikinci koşu HoldoutTekrarHatasi (zorla / ikinci deneme YOKTUR).
 2. Mühürlü set, mühürlü ayarlar ve s ile, aynı sabit evrende, HOLDOUT_BAS -> veri sonu, tek kasada (maliyet x1, TradFi funding dahil;
    işlem başı risk s x %1, sert limitler aynen). Yalnız girişi >= HOLDOUT_BAS olan işlemler sayılır.
 3. Set kapısı (ikisi de şart): set net getirisi > 0 VE havuzlanmış rastgele-giriş testi p_set <= HOLDOUT_P_SET. T_set = setteki tek-grafik
    stratejilerin holdout işlemlerinin ΣR'si (enstrüman başı çakışma süzgeci sonrası); sıfır dağılımı: her strateji için 5.1 kuralıyla
    (çeyrekler holdout içinde, sınırı aşan çeyrek kesilir) B = HOLDOUT_B_SET çekim, tohum `hset`; b'inci set çekimi = stratejilerin b'inci
    çekimlerinin toplamı. Portföy satırı set p'sine GİRMEZ (ayrı raporlanır); set net > 0 şartına girer.
 4. Strateji budaması (kapı değil): kapı GEÇTİYSE, holdout neti <= 0 VEYA kendi K2 p'si (B = HOLDOUT_B_STRATEJI, tohum `hk2`) > HOLDOUT_BUDAMA_P
    olan strateji setten çıkarılır; yerine yenisi alınmaz. Kapı, budamadan ÖNCEKİ mühürlü set üzerinden değerlendirilir.
 5. Kapı kalırsa paper girdisi ÜRETİLMEZ. 6. Rapor: strateji bazında net, PF(R), işlem sayısı, K2 p; kilit_gorulmus; evren notu.
Holdout verisi bir `HoldoutSaglayici` üzerinden gelir: testler SENTETİK sağlayıcı verir; gerçek sağlayıcı yalnız mühür + günlük sonrası kurulur.
"""
from __future__ import annotations

import dataclasses
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_holdout as v1h
from motor.arastirma.v2 import ham as hm, kasa, sabit
from motor.arastirma.v2 import test as k2

V2_DIZIN = Path(__file__).resolve().parent
EVREN_NOTU = ("Evren üyeliği 2026-11-07'de sabitlendi (ileriyi görme: bugün listelenen enstrümanlar); "
              "holdout dönemi evreni geçmişte seçmedi ama üyelik bu tarihe bağlıdır.")


class HoldoutHatasi(RuntimeError):
    """Mühür bozuk / eksik / set boş: holdout reddedilir."""


class HoldoutTekrarHatasi(HoldoutHatasi):
    """Holdout daha önce başlatıldı (bir kerelik; zorla yolu YOKTUR)."""


# ============================================================================ mühür (6.3)
def v2_modul_hashleri() -> dict:
    return {f"motor/arastirma/v2/{f.name}": kasa.sha256(f) for f in sorted(V2_DIZIN.glob("*.py"))}


def strateji_hashleri(set_kayitlari: list) -> dict:
    """{strateji: {göreli yol: sha256}} — v1 mühür sürüm 3 kapsamı (kaynak + kart/ayar dosyaları)."""
    return v1h.strateji_hashleri([{"strateji": k["strateji"], "stil": ("portfoy" if k["stil_v2"] == "portfoy" else "swing")}
                                  for k in set_kayitlari])


def _dosya_yollari(cikti: Path, havuz_yolu=None) -> dict:
    cikti = Path(cikti)
    return {"havuz_v2.csv": Path(havuz_yolu or sabit.HAVUZ_CSV), "eleme.csv": cikti / "eleme.csv", "test.csv": cikti / "test.csv",
            "saglamlik.csv": cikti / "saglamlik.csv", "set.csv": cikti / "set.csv"}


def muhur_yaz(cikti: Path, havuz_yolu=None, ozet: Optional[dict] = None) -> dict:
    """set aşaması sonunda: set listesi + ayarlar + s + tüm dosya hash'leri (6.3). Holdout başlamışsa değiştirilemez."""
    cikti = Path(cikti)
    if baslamis_mi(cikti):
        raise HoldoutHatasi("holdout daha önce başlatıldı: mühür değiştirilemez")
    ozet = ozet or json.loads((cikti / "set_ozet.json").read_text())
    dosyalar = _dosya_yollari(cikti, havuz_yolu)
    eksik = [k for k, y in dosyalar.items() if not y.exists()]
    if eksik:
        raise HoldoutHatasi(f"mühürlenecek dosya yok: {eksik}")
    tablo = cikti / sabit.TABLO_V2_AD
    secilen = [{k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in a.items()} for a in ozet.get("secilen", [])]
    muhur = {"surum": sabit.MUHUR_SURUM, "zaman": datetime.now(timezone.utc).isoformat(), "sonuc": ozet.get("sonuc", "0 strateji"),
             "set": [{k: a.get(k) for k in ("strateji", "tf", "stil_v2", "evren", "ayar", "etiket", "alt_etiket", "kilit_gorulmus", "p", "kume", "sira")}
                     for a in secilen],
             "s": ozet.get("s"), "s_tablo": ozet.get("s_tablo", {}),
             "dosyalar": {k: kasa.sha256(y) for k, y in dosyalar.items()},
             "maliyet_tablosu_v2_sha256": evren_maliyet.tablo_hash(tablo), "on_kayit_v2_sha256": kasa.sha256(sabit.ON_KAYIT_V2),
             "git_commit": v1h.git_commit(), "ortak_modul_hash": v1h.ortak_modul_hashleri(), "v2_modul_hash": v2_modul_hashleri(),
             "strateji_hash": strateji_hashleri(secilen) if secilen else {}, "evren": v1h.evren_imzasi()}
    kasa.atomik_yaz_json(cikti / sabit.SET_MUHRU, muhur)
    return muhur


def muhur_kontrol(cikti: Path, havuz_yolu=None) -> dict:
    """Mührü doğrular: herhangi bir uyuşmazlıkta HoldoutHatasi. Boş set (sonuç 0) de HoldoutHatasi (holdout açılmaz)."""
    cikti = Path(cikti)
    yol = cikti / sabit.SET_MUHRU
    if not yol.exists():
        raise HoldoutHatasi(f"{sabit.SET_MUHRU} yok: önce set aşaması mühürlemeli (holdout açılmaz)")
    m = json.loads(yol.read_text())
    if m.get("surum") != sabit.MUHUR_SURUM:
        raise HoldoutHatasi(f"{sabit.SET_MUHRU} sürümü tanınmıyor: {m.get('surum')}")
    for k, y in _dosya_yollari(cikti, havuz_yolu).items():
        if not y.exists() or kasa.sha256(y) != m["dosyalar"].get(k):
            raise HoldoutHatasi(f"mühürlü dosya değişmiş ya da yok: {k}; holdout DURDU")
    tablo = cikti / sabit.TABLO_V2_AD
    if not tablo.exists() or evren_maliyet.tablo_hash(tablo) != m.get("maliyet_tablosu_v2_sha256"):
        raise HoldoutHatasi("v2 maliyet tablosu mühürden sonra değişmiş; holdout DURDU")
    if kasa.sha256(sabit.ON_KAYIT_V2) != m.get("on_kayit_v2_sha256"):
        raise HoldoutHatasi("ON_KAYIT_V2.md mühürden sonra değişmiş; holdout DURDU")
    if v1h.ortak_modul_hashleri() != m.get("ortak_modul_hash"):
        raise HoldoutHatasi("ortak motor modülü mühürden sonra değişmiş; holdout DURDU")
    if v2_modul_hashleri() != m.get("v2_modul_hash"):
        raise HoldoutHatasi("v2 modülü mühürden sonra değişmiş; holdout DURDU")
    if v1h.evren_imzasi() != m.get("evren"):
        raise HoldoutHatasi("evren üyeliği mühürden sonra değişmiş; holdout DURDU")
    if not v1h._commit_ata_mi(str(m.get("git_commit", "")), v1h.git_commit()):
        raise HoldoutHatasi("mühürdeki git commit şimdiki HEAD'in atası değil; holdout DURDU")
    if not m.get("set"):
        raise HoldoutHatasi("set boş (v2 sonucu: 0 strateji): holdout AÇILMAZ")
    if strateji_hashleri(m["set"]) != m.get("strateji_hash"):
        raise HoldoutHatasi("strateji kaynağı/kartı mühürden sonra değişmiş; holdout DURDU")
    sd = pd.read_csv(cikti / "set.csv")
    if [(r["strateji"], r["tf"], r["ayar"]) for r in sd.to_dict("records")] != [(a["strateji"], a["tf"], a["ayar"]) for a in m["set"]]:
        raise HoldoutHatasi("set.csv mühürdeki set/ayarlarla uyuşmuyor; holdout DURDU")
    if m.get("s") not in sabit.S_IZGARA:
        raise HoldoutHatasi(f"mühürdeki s geçersiz: {m.get('s')}")
    return m


# ============================================================================ günlük (bir kerelik)
def gunluk_oku(cikti: Path) -> list:
    yol = Path(cikti) / sabit.HOLDOUT_GUNLUK
    return [json.loads(x) for x in yol.read_text(encoding="utf-8").splitlines() if x.strip()] if yol.exists() else []


def baslamis_mi(cikti: Path) -> bool:
    return any(k.get("olay") == "basladi" for k in gunluk_oku(cikti))


def gunluge_yaz(cikti: Path, olay: dict) -> None:
    yol = Path(cikti) / sabit.HOLDOUT_GUNLUK
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), **olay}, ensure_ascii=False, default=str) + "\n")


# ============================================================================ veri sağlayıcı
class HoldoutSaglayici:
    """Holdout verisinin TEK giriş noktası. Gerçek: GercekSaglayici. Test: sentetik alt sınıf."""

    def veri_sonu(self) -> str:
        raise NotImplementedError

    def tek_islemler(self, kayit: dict) -> tuple:
        """-> ({sembol: ham df (girişi >= HOLDOUT_BAS)}, sembol_sirasi, hatalar[list[str]])"""
        raise NotImplementedError

    def k2_baglam(self, kayit: dict) -> tuple:
        """-> (veri_al, cikis_al) — k2_simule için; mumlar holdout dönemini ve ısınmayı kapsar."""
        raise NotImplementedError

    def pf_gunluk(self, kayit: dict) -> pd.Series:
        """Portföy satırı: HOLDOUT_BAS'tan itibaren günlük getiri."""
        raise NotImplementedError

    def pf_k2_p(self, kayit: dict, n_sim: int, tohum: int) -> float:
        raise NotImplementedError


_YETKI = {"acik": False}


class GercekSaglayici(HoldoutSaglayici):
    """GERÇEK holdout verisi. Yalnız holdout_asamasi içinde, mühür doğrulanıp günlüğe "basladi" yazıldıktan sonra kurulabilir."""

    def __init__(self, tablo_yolu):
        if not _YETKI["acik"]:
            raise HoldoutHatasi("GercekSaglayici yalnız holdout_asamasi içinde (mühür + günlük sonrası) kurulabilir")
        self.tablo_yolu = tablo_yolu
        we.veri_ayarla(None, "holdout")                                     # holdout verisi YALNIZ burada açılır
        self._st, self._cikis = {}, {}

    def _strateji(self, kayit):
        ad = kayit["strateji"]
        if ad not in self._st:
            etiket, st = hm.varsayilan_strateji(ad)
            if etiket != kayit["ayar"]:
                raise HoldoutHatasi(f"{ad}: mühürlü ayar {kayit['ayar']!r}, şimdiki varsayılan {etiket!r}")
            self._st[ad] = st
        return self._st[ad]

    def veri_sonu(self) -> str:
        return str(max(we._veri(s, "1d")[0].index[-1] for s in sabit.evren_listesi("genel")))

    def tek_islemler(self, kayit):
        from motor.backtest.motor import backtest
        from motor.strateji import funding
        ad, tf = kayit["strateji"], kayit["tf"]
        st = self._strateji(kayit)
        sira = sabit.evren_listesi(kayit["evren"])
        out, hatalar = {}, []
        for s in sira:
            try:
                mumlar, fund = we._veri(s, tf)
            except (FileNotFoundError, ValueError):
                continue
            if not len(mumlar) or mumlar.index[-1] < sabit.HOLDOUT_BAS:
                continue
            try:
                kural = we.tarama.SEMBOL_KURALLARI.get(s, we.tarama.VARSAYILAN_KURAL)
                ay = evren_maliyet.maliyet_ayarlari(s, kural, 1.0, self.tablo_yolu)
                res = backtest(funding.stratejiye_hazirla(st, mumlar, fund, s, tf), st, ay, fund)
                h, _ = hm.islem_hazirla(res.islemler, s, tf, 1.0, mumlar, self.tablo_yolu)
            except Exception as e:  # noqa: BLE001  (sayılır ve raporlanır: kayıt['hatalar'])
                hatalar.append(f"{s}: {type(e).__name__}: {e}"[:200])
                continue
            h = h[pd.DatetimeIndex(h["giris_zamani"]) >= sabit.HOLDOUT_BAS]
            if len(h):
                out[s] = h.reset_index(drop=True)
        return out, sira, hatalar

    def k2_baglam(self, kayit):
        from motor.arastirma import evren_k2
        from motor.strateji import funding
        ad, tf = kayit["strateji"], kayit["tf"]
        st = self._strateji(kayit)

        def veri_al(s):
            mumlar, _ = we._veri(s, tf)
            kural = we.tarama.SEMBOL_KURALLARI.get(s, we.tarama.VARSAYILAN_KURAL)
            return mumlar, evren_maliyet.maliyet_ayarlari(s, kural, 1.0, self.tablo_yolu)

        def cikis_al(s):
            k = (ad, s)
            if k not in self._cikis:
                mumlar, fund = we._veri(s, tf)
                self._cikis[k] = evren_k2.cikis_bilgisi(st, funding.stratejiye_hazirla(st, mumlar, fund, s, tf))
            return self._cikis[k]
        return veri_al, cikis_al

    def _pf_kos(self, kayit):
        from motor.arastirma import wf_evren_portfoy as wep
        v, f, _ = wep.veri_yukle(sabit.evren_listesi(kayit["evren"]), "1d")
        ev = tuple(v)
        st = hm.varsayilan_pf(kayit["strateji"], ev)
        if st is None:
            raise HoldoutHatasi(f"{kayit['strateji']}: varsayılan ayar holdout evreninde uygun değil")
        return wep._kos(st, v, f, ev, hm.maliyet_pf(ev, 1.0, self.tablo_yolu), 0), v

    def pf_gunluk(self, kayit):
        r, v = self._pf_kos(kayit)
        return k2.pf_gunluk_getiri(r, v, self.tablo_yolu, sabit.HOLDOUT_BAS)

    def pf_k2_p(self, kayit, n_sim, tohum):
        gercek = k2.sharpe_gunluk(self.pf_gunluk(kayit).to_numpy())
        sims = k2.pf_k2_simule(kayit["strateji"], kayit["evren"], self.tablo_yolu, sabit.HOLDOUT_BAS, n_sim, tohum, holdout=True)
        return k2.p_degeri(gercek, sims)


# ============================================================================ hesap (saf; sağlayıcıdan bağımsız)
def _ayar(s: float) -> secim.OynatmaAyari:
    return dataclasses.replace(we.SINIRLAR, risk=s * sabit.ISLEM_RISK)


def oynat_net(islemler_by_ad: dict, siralar: dict, s: float, tablo_yolu, bit) -> float:
    """Tek kasa, maliyet x1: net getiri (nakit_son - 1). islemler_by_ad: {strateji: {sembol: ham df}}."""
    oos = kasa.oos_birlestir(islemler_by_ad, siralar, sabit.HOLDOUT_BAS, 1.0, tablo_yolu)
    if not len(oos):
        return 0.0
    tablo, res = kasa.oynat(oos, sabit.HOLDOUT_BAS, bit, _ayar(s))
    return float(res["nakit_son"] - 1.0)


def pf_net(gunluk: pd.Series, s: float) -> float:
    return float(np.prod(1.0 + s * gunluk.to_numpy(dtype=float)) - 1.0) if len(gunluk) else 0.0


def strateji_olc(kayit: dict, sag: HoldoutSaglayici, s: float, tablo_yolu, bit, ilk: dict) -> dict:
    """Tek stratejinin holdout özeti (tek başına tek kasa neti, PF(R), işlem sayısı, K2 p) — K2 p B = HOLDOUT_B_STRATEJI, tohum `hk2`."""
    ad, tf = kayit["strateji"], kayit["tf"]
    if kayit["stil_v2"] == "portfoy":
        g = ilk["pf_gunluk"][ad]
        tohum = sabit.satir_tohumu(ad, tf, "hk2")
        p = sag.pf_k2_p(kayit, sabit.HOLDOUT_B_STRATEJI, tohum)
        return {"net": pf_net(g, s), "pf_r": math.nan, "n_islem": int(len(g)), "k2_p": p, "hatalar": ""}
    islemler = ilk["islemler"][ad]
    sira = ilk["sira"][ad]
    net = oynat_net({ad: islemler}, {ad: sira}, s, tablo_yolu, bit)
    r = [d["r"].to_numpy(dtype=float) for d in islemler.values() if len(d)]
    pf = we._pf(np.concatenate(r)) if r else math.nan
    gercek = k2.cakisma_suz(islemler, sabit.HOLDOUT_BAS)
    if gercek:
        veri_al, cikis_al = sag.k2_baglam(kayit)
        sim = k2.k2_simule(gercek, veri_al, cikis_al, sabit.HOLDOUT_B_STRATEJI, sabit.satir_tohumu(ad, tf, "hk2"), alt_sinir=sabit.HOLDOUT_BAS)
        p = k2.p_degeri(k2.toplam_r(gercek), sim["toplam_r"])
    else:
        p = math.nan
    return {"net": net, "pf_r": pf, "n_islem": int(sum(len(d) for d in islemler.values())), "k2_p": p, "hatalar": "; ".join(ilk["hatalar"][ad])}


def set_kapisi(net_set: float, p_set: float) -> bool:
    """Set kapısı: net > 0 VE p_set <= HOLDOUT_P_SET (NaN = geçmez)."""
    return bool(math.isfinite(net_set) and net_set > 0 and math.isfinite(p_set) and p_set <= sabit.HOLDOUT_P_SET)


def budama(olcumler: dict) -> tuple:
    """-> (kalan, cikan{ad: neden}). Net <= 0 VEYA k2 p > HOLDOUT_BUDAMA_P (NaN p = çıkar). Yerine yenisi alınmaz."""
    kalan, cikan = [], {}
    for ad, o in olcumler.items():
        if not o["net"] > 0:
            cikan[ad] = f"holdout neti {o['net']:.4f} <= 0"
        elif not (math.isfinite(o["k2_p"]) and o["k2_p"] <= sabit.HOLDOUT_BUDAMA_P):
            cikan[ad] = f"K2 p {o['k2_p']} > {sabit.HOLDOUT_BUDAMA_P}"
        else:
            kalan.append(ad)
    return kalan, cikan


def holdout_asamasi(cikti: Path = None, saglayici: Optional[HoldoutSaglayici] = None, havuz_yolu=None) -> dict:
    """Bölüm 7. Mühür doğrulanamazsa / set boşsa / daha önce başlatıldıysa HİÇBİR veri okunmadan açık hata."""
    import os
    if saglayici is None and os.environ.get("PYTEST_CURRENT_TEST"):
        raise HoldoutHatasi("testler gerçek holdout verisiyle holdout çalıştıramaz (sentetik sağlayıcı verin)")
    cikti = Path(cikti or sabit.CIKTI)
    muhur = muhur_kontrol(cikti, havuz_yolu)
    if baslamis_mi(cikti):
        raise HoldoutTekrarHatasi("holdout bir kerelik ve daha önce başlatıldı; ikinci deneme yoktur")
    s = float(muhur["s"])
    gunluge_yaz(cikti, {"olay": "basladi", "set": [a["strateji"] for a in muhur["set"]], "s": s, "muhur_dosyalar": muhur["dosyalar"]})
    _YETKI["acik"] = True
    try:
        tablo_yolu = cikti / sabit.TABLO_V2_AD
        sag = saglayici or GercekSaglayici(tablo_yolu)
        sonuc = _kos(muhur, sag, s, tablo_yolu, cikti)
    except Exception as e:  # noqa: BLE001  (günlüğe yazılır ve YENİDEN FIRLATILIR; holdout yine de "başlamış" sayılır)
        gunluge_yaz(cikti, {"olay": "hata", "hata": f"{type(e).__name__}: {e}"[:500]})
        raise
    finally:
        _YETKI["acik"] = False
    gunluge_yaz(cikti, {"olay": "bitti", "kapi_gecti": sonuc["kapi_gecti"], "kalan": sonuc["kalan"]})
    return sonuc


def _kos(muhur: dict, sag: HoldoutSaglayici, s: float, tablo_yolu, cikti: Path) -> dict:
    set_ = muhur["set"]
    bit = pd.Timestamp(sag.veri_sonu())
    bit = bit.tz_localize("UTC") if bit.tzinfo is None else bit.tz_convert("UTC")
    ilk = {"islemler": {}, "sira": {}, "hatalar": {}, "pf_gunluk": {}}
    for k in set_:
        if k["stil_v2"] == "portfoy":
            ilk["pf_gunluk"][k["strateji"]] = sag.pf_gunluk(k)
        else:
            isl, sira, hat = sag.tek_islemler(k)
            ilk["islemler"][k["strateji"]], ilk["sira"][k["strateji"]], ilk["hatalar"][k["strateji"]] = isl, sira, hat
    # ---- set kapısı (BUDAMADAN ÖNCEKİ mühürlü set)
    tek = [k for k in set_ if k["stil_v2"] != "portfoy"]
    net_tek = oynat_net({k["strateji"]: ilk["islemler"][k["strateji"]] for k in tek}, {k["strateji"]: ilk["sira"][k["strateji"]] for k in tek},
                        s, tablo_yolu, bit) if tek else 0.0
    net_pf = sum(pf_net(g, s) for g in ilk["pf_gunluk"].values())
    net_set = net_tek + net_pf
    p_set, T_set, B_set = math.nan, math.nan, sabit.HOLDOUT_B_SET
    toplam = np.zeros(B_set)
    T = 0.0
    for k in tek:
        gercek = k2.cakisma_suz(ilk["islemler"][k["strateji"]], sabit.HOLDOUT_BAS)
        T += k2.toplam_r(gercek)
        if gercek:
            veri_al, cikis_al = sag.k2_baglam(k)
            toplam += k2.k2_simule(gercek, veri_al, cikis_al, B_set, sabit.satir_tohumu(k["strateji"], k["tf"], "hset"),
                                   alt_sinir=sabit.HOLDOUT_BAS)["toplam_r"]
    if tek:
        T_set, p_set = T, k2.p_degeri(T, toplam)
    kapi = set_kapisi(net_set, p_set)
    # ---- strateji düzeyi ölçümler (rapor; budama yalnız kapı geçtiyse)
    olc = {k["strateji"]: strateji_olc(k, sag, s, tablo_yolu, bit, ilk) for k in set_}
    kalan, cikan = (budama(olc) if kapi else ([], {}))
    sonuc = {"kapi_gecti": bool(kapi), "net_set": net_set, "net_tek": net_tek, "net_portfoy": net_pf, "p_set": p_set, "T_set": T_set,
             "B_set": B_set, "s": s, "veri_sonu": str(bit), "olcumler": olc, "cikan": cikan, "kalan": kalan,
             "kilit_gorulmus": {k["strateji"]: k.get("kilit_gorulmus") for k in set_}}
    _rapor_yaz(cikti, sonuc, set_)
    if kapi and kalan:
        kasa.atomik_yaz_json(cikti / "holdout" / "paper_girdisi.json",
                             {"set": [k for k in set_ if k["strateji"] in kalan], "s": s, "not": "holdout set kapısı geçti; budama sonrası"})
    return sonuc


def _rapor_yaz(cikti: Path, sonuc: dict, set_: list) -> None:
    d = Path(cikti) / "holdout"
    d.mkdir(parents=True, exist_ok=True)
    satirlar = []
    for k in set_:
        o = sonuc["olcumler"][k["strateji"]]
        satirlar.append({"strateji": k["strateji"], "tf": k["tf"], "stil_v2": k["stil_v2"], "ayar": k["ayar"], "net": o["net"],
                         "pf_r": o["pf_r"], "n_islem": o["n_islem"], "k2_p": o["k2_p"], "kilit_gorulmus": k.get("kilit_gorulmus"),
                         "durum": ("budandi" if k["strateji"] in sonuc["cikan"] else ("kaldi" if k["strateji"] in sonuc["kalan"] else "kapi_kalmadi")),
                         "hatalar": o["hatalar"]})
    pd.DataFrame(satirlar).to_csv(d / "holdout.csv", index=False)
    kasa.atomik_yaz_json(d / "holdout_sonuc.json", sonuc)
    sat = ["# v2 holdout raporu", "",
           f"Set kapısı: {'GEÇTİ' if sonuc['kapi_gecti'] else 'KALDI'} (net {sonuc['net_set']:.4f}; p_set {sonuc['p_set']}; "
           f"koşul: net > 0 ve p_set <= {sabit.HOLDOUT_P_SET}). Veri sonu: {sonuc['veri_sonu']}. s = {sonuc['s']}.", "",
           "| strateji | tf | net | PF(R) | işlem | K2 p | kilit_gorulmus | durum |", "|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        sat.append(f"| {r['strateji']} | {r['tf']} | {r['net']:.4f} | {r['pf_r']} | {r['n_islem']} | {r['k2_p']} | {r['kilit_gorulmus']} | {r['durum']} |")
    sat += ["", EVREN_NOTU, "",
            "Kapı kaldıysa bu set paper'a gitmez; holdout'a bakılarak ayar/eşik/set değiştirilmez; yeni tasarım denenmez (ON_KAYIT_V2 0.3)."]
    (d / "holdout_raporu.md").write_text("\n".join(sat), encoding="utf-8")
