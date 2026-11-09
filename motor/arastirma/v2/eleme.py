"""v2 Aşama 2 — eleme (ON_KAYIT_V2 bölüm 4; P1-2 ve P0-4).

Beş kapı, HEPSİ şart; NaN = geçmez. Tek kasa oynatmasında KABUL edilen işlemler üzerinden (v1 `wf_evren.oynatma_tablosu` +
`kasa_metrikleri` + `secim.yeniden_oyna`; sıra = giriş zamanı, eşitlikte evren sırası). Oynatma aralığı: analiz başlangıcı
(evrenin ≥ %75'inin verisinin başladığı gün, v1 ile aynı) → geliştirme verisinin sonu; analiz başlangıcından önce girilen işlem
sayılmaz.
  E1 kârlılık: ×2 oynatmasında net > 0 VE ×1'de PF(R) ≥ E1_PF_MIN
  E2 örnek: ×1'de kabul ≥ E2_MIN_ISLEM VE işlem yapılan enstrüman ≥ 10 (kripto evreninde 6)
  E3 yoğunlaşma: ΣR'si en yüksek enstrüman çıkarılınca ΣR > 0 VE ΣR'si en yüksek takvim yılı (giriş, UTC) çıkarılınca ΣR > 0
  E4 genişlik: genel evrende kripto/hisse/emtia'dan ≥ 2'sinin her biri ΣR'nin ≥ %15'i (toplam ΣR ≤ 0 ise payı tanımsız = geçmez);
     kripto evreninde kapı yok
  E5 hayatta kalma (P0-4): ×1 oynatmasında kill_olayi == 0
Portföy satırları: E1 = ×2 net > 0 VE ×1 günlük Sharpe ≥ 0.5; E2 = dönem ≥ 1095 gün VE ≥ 20 yeniden dengeleme; E3 = yalnız en iyi
takvim yılı çıkarılınca (kalan günlerin bileşik) net > 0; E4 yok; E5 aynı (portföy motorunun kill olayı, ×1).
Elemeyi geçemeyen / hata veren satırın resmi test p-değeri 1'dir (5.3): `p_ust` = 1.0.
Eşik sayıları YALNIZ sabit.py'de.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet, secim
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_portfoy as wp
from motor.arastirma.v2 import ham as hm
from motor.arastirma.v2 import maliyet, sabit

KAPILAR = ("e1", "e2", "e3", "e4", "e5")


# ============================================================================ saf kapı işlevleri
def _gecer(v, ok) -> bool:
    """NaN/None = geçmez."""
    if v is None:
        return False
    try:
        if isinstance(v, float) and math.isnan(v):
            return False
        return bool(ok(v))
    except TypeError:
        return False


def _kalan_toplam(d: dict) -> float:
    """En yüksek toplamlı anahtar çıkarılınca kalanların toplamı (NaN içeren/boş sözlük -> NaN)."""
    if not d or any(v is None or (isinstance(v, float) and math.isnan(v)) for v in d.values()):
        return math.nan
    en = max(d, key=lambda k: d[k])
    return float(sum(v for k, v in d.items() if k != en))


def eleme_tek(m: dict, evren: str) -> dict:
    """Tek-grafik satırı. m: net_x2, pf_x1, n_islem_x1, n_enstruman_x1, kill_x1, r_enstruman {sembol: ΣR},
    r_yil {yıl: ΣR}, r_sinif {sınıf: ΣR} (hepsi kabul edilen işlemlerden). -> {e1..e5, gecti, nedenler}."""
    ned = []
    e1a = _gecer(m.get("net_x2"), lambda v: v > 0)
    e1b = _gecer(m.get("pf_x1"), lambda v: v >= sabit.E1_PF_MIN)
    e1 = e1a and e1b
    if not e1a:
        ned.append(f"E1 net(x2) {m.get('net_x2')} <= 0 ya da hesaplanamadı")
    if not e1b:
        ned.append(f"E1 PF(x1) {m.get('pf_x1')} < {sabit.E1_PF_MIN} ya da hesaplanamadı")
    min_en = sabit.E2_MIN_ENSTRUMAN_KRIPTO if evren == "kripto" else sabit.E2_MIN_ENSTRUMAN_GENEL
    e2a = _gecer(m.get("n_islem_x1"), lambda v: v >= sabit.E2_MIN_ISLEM)
    e2b = _gecer(m.get("n_enstruman_x1"), lambda v: v >= min_en)
    e2 = e2a and e2b
    if not e2a:
        ned.append(f"E2 işlem {m.get('n_islem_x1')} < {sabit.E2_MIN_ISLEM}")
    if not e2b:
        ned.append(f"E2 enstrüman {m.get('n_enstruman_x1')} < {min_en}")
    e3a = _gecer(_kalan_toplam(m.get("r_enstruman") or {}), lambda v: v > 0)
    e3b = _gecer(_kalan_toplam(m.get("r_yil") or {}), lambda v: v > 0)
    e3 = e3a and e3b
    if not e3a:
        ned.append("E3 en iyi enstrüman çıkarılınca ΣR <= 0 ya da hesaplanamadı")
    if not e3b:
        ned.append("E3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı")
    if evren == "kripto":
        e4 = True
    else:
        rs = m.get("r_sinif") or {}
        top = sum(v for v in rs.values() if v is not None and not (isinstance(v, float) and math.isnan(v)))
        if _gecer(top, lambda v: v > 0):
            adet = sum(1 for s in sabit.GENEL_SINIFLAR if _gecer(rs.get(s), lambda v: v / top >= sabit.E4_SINIF_PAY_MIN))
        else:
            adet = 0
        e4 = adet >= sabit.E4_MIN_SINIF
        if not e4:
            ned.append(f"E4 payı ≥ %{sabit.E4_SINIF_PAY_MIN * 100:g} olan sınıf {adet} < {sabit.E4_MIN_SINIF} ya da ΣR <= 0")
    e5 = _gecer(m.get("kill_x1"), lambda v: v <= sabit.E5_MAKS_KILL)
    if not e5:
        ned.append(f"E5 kill_olayi(x1) {m.get('kill_x1')} (hayatta kalma)")
    return _sonuc(e1, e2, e3, e4, e5, ned)


def eleme_portfoy(m: dict) -> dict:
    """Portföy satırı. m: net_x2, sharpe_x1, gun, dengeleme, net_en_iyi_yil_haric, kill_x1."""
    ned = []
    e1 = _gecer(m.get("net_x2"), lambda v: v > 0) and _gecer(m.get("sharpe_x1"), lambda v: v >= sabit.E1_PORTFOY_SHARPE_MIN)
    if not e1:
        ned.append(f"E1 net(x2) {m.get('net_x2')} / Sharpe(x1) {m.get('sharpe_x1')} (> 0 ve >= {sabit.E1_PORTFOY_SHARPE_MIN})")
    e2 = (_gecer(m.get("gun"), lambda v: v >= sabit.E2_PORTFOY_MIN_GUN)
          and _gecer(m.get("dengeleme"), lambda v: v >= sabit.E2_PORTFOY_MIN_DENGELEME))
    if not e2:
        ned.append(f"E2 gün {m.get('gun')} / yeniden dengeleme {m.get('dengeleme')} "
                   f"(>= {sabit.E2_PORTFOY_MIN_GUN} ve >= {sabit.E2_PORTFOY_MIN_DENGELEME})")
    e3 = _gecer(m.get("net_en_iyi_yil_haric"), lambda v: v > 0)
    if not e3:
        ned.append("E3 en iyi yıl çıkarılınca net <= 0 ya da hesaplanamadı")
    e5 = _gecer(m.get("kill_x1"), lambda v: v <= sabit.E5_MAKS_KILL)
    if not e5:
        ned.append(f"E5 kill_olayi(x1) {m.get('kill_x1')}")
    return _sonuc(e1, e2, e3, True, e5, ned)


def _sonuc(e1, e2, e3, e4, e5, ned) -> dict:
    d = {"e1": bool(e1), "e2": bool(e2), "e3": bool(e3), "e4": bool(e4), "e5": bool(e5)}
    d["gecti"] = all(d[k] for k in KAPILAR)
    d["nedenler"] = "; ".join(ned)
    return d


def p_ust(gecti: bool) -> float:
    """5.3: elemeyi geçemeyen satırın resmi test p-değeri 1."""
    return math.nan if gecti else 1.0


# ============================================================================ metrik hesabı
def maliyet_payi_v2(oos: pd.DataFrame, carpan: float, tablo_yolu) -> np.ndarray:
    """wf_evren.oynatma_maliyet_payi ile AYNI formül; maliyet v2 tablosundan (v1 tablosunun aynı değerleri)."""
    sk, tk = np.empty(len(oos)), np.empty(len(oos))
    for s in pd.unique(oos["sembol"]):
        m = (oos["sembol"] == s).to_numpy()
        taker_y, _, _, stop_bps = evren_maliyet.sembol_maliyeti(s, carpan, tablo_yolu)
        sk[m], tk[m] = stop_bps / 1e4, taker_y / 100.0
    return secim.maliyet_payi(oos["sf"].to_numpy(dtype=float), oos["yon"].to_numpy(), sk, tk)


def kasa_oynat(ham: dict, sira: tuple, analiz_bas, oos_bit, carpan: float, tablo_yolu) -> tuple:
    """-> (metrikler dict | None, tablo). Ham işlemler {sembol: df}; analiz başlangıcından önce girilenler atılır."""
    parcalar = []
    for s in sira:
        df = ham.get(s)
        if df is None or not len(df):
            continue
        d = df[pd.DatetimeIndex(df["giris_zamani"]) >= analiz_bas].copy()
        if len(d):
            d["sembol"] = s
            parcalar.append(d)
    if not parcalar:
        return None, None
    oos = pd.concat(parcalar, ignore_index=True)
    oos["maliyet_payi"] = maliyet_payi_v2(oos, carpan, tablo_yolu)
    tablo = we.oynatma_tablosu(oos, sira)
    return we.kasa_metrikleri(tablo, analiz_bas, oos_bit), tablo


def tek_metrikler(ham1: dict, ham2: dict, bilgi1: dict, evren_adi: str, tablo_yolu) -> dict:
    """x1 ve x2 ham sonuçlarından eleme_tek'in girdisi. Ayrıca bilgi alanları (analiz_bas, ...)."""
    sira = sabit.evren_listesi(evren_adi)
    analiz_bas = we.analiz_bas_hesapla(bilgi1["veri_bas"])
    oos_bit = max(bilgi1["veri_bit"].values()) + pd.Timedelta(1, "ns")
    m1, t1 = kasa_oynat(ham1, sira, analiz_bas, oos_bit, 1.0, tablo_yolu)
    m2, _ = kasa_oynat(ham2, sira, analiz_bas, oos_bit, 2.0, tablo_yolu)
    nan = math.nan
    out = {"analiz_bas": str(analiz_bas), "net_x2": nan if m2 is None else m2.get("net_getiri", nan),
           "net_x1": nan if m1 is None else m1.get("net_getiri", nan),
           "pf_x1": nan if m1 is None else m1.get("profit_factor", nan),
           "n_islem_x1": 0 if m1 is None else int(m1["islem_sayisi"]),
           "n_enstruman_x1": 0 if m1 is None else int(m1.get("n_enstruman_islemli", 0)),
           "kill_x1": nan if m1 is None else m1.get("kill_olayi", nan),
           "sharpe_x1": nan if m1 is None else m1.get("sharpe", nan),
           "max_dusus_x1": nan if m1 is None else m1.get("max_dusus", nan),
           "r_enstruman": {}, "r_yil": {}, "r_sinif": {}}
    if m1 is not None and m1["islem_sayisi"]:
        kabul = m1["kabul"]
        r = t1["r"].to_numpy(dtype=float)[kabul]
        sem = t1["sembol"].to_numpy()[kabul]
        yil = pd.DatetimeIndex(t1["giris"])[kabul].year
        for nm, anahtar in (("r_enstruman", sem), ("r_yil", yil), ("r_sinif", np.array([sabit.sinif_of(s) for s in sem]))):
            sr = pd.Series(r).groupby(anahtar).sum()
            out[nm] = {(int(k) if nm == "r_yil" else str(k)): float(v) for k, v in sr.items()}
    return out


def _yil_haric_net(getiri: pd.Series) -> float:
    """En iyi takvim yılı (yıllık bileşik getiri en yüksek) çıkarılınca kalan günlerin bileşik neti."""
    if not len(getiri):
        return math.nan
    yil = getiri.groupby(getiri.index.year).apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))
    en = yil.idxmax()
    kalan = getiri[getiri.index.year != en]
    return float(np.prod(1.0 + kalan.to_numpy()) - 1.0) if len(kalan) else math.nan


def portfoy_metrikleri(g1: pd.DataFrame, m1: dict, g2: pd.DataFrame) -> dict:
    vb = {s: pd.Timestamp(t) for s, t in m1["veri_bas_sembol"].items()}
    analiz_bas = we.analiz_bas_hesapla(vb)

    def kes(g):
        x = g[pd.DatetimeIndex(g["gun"]) >= analiz_bas]
        return pd.Series(x["getiri"].to_numpy(dtype=float), index=pd.DatetimeIndex(x["gun"])), x
    r1, x1 = kes(g1)
    r2, _ = kes(g2)
    nan = math.nan
    return {"analiz_bas": str(analiz_bas),
            "net_x1": float(np.prod(1.0 + r1.to_numpy()) - 1.0) if len(r1) else nan,
            "net_x2": float(np.prod(1.0 + r2.to_numpy()) - 1.0) if len(r2) else nan,
            "sharpe_x1": wp.sharpe_gunluk(r1.to_numpy()) if len(r1) else nan,
            "gun": int((r1.index[-1] - r1.index[0]).days + 1) if len(r1) else 0,
            "dengeleme": int(x1["dengeleme"].sum()),
            "net_en_iyi_yil_haric": _yil_haric_net(r1),
            "kill_x1": m1.get("kill_olayi", nan)}


# ============================================================================ satır işlemi
def satir_degerlendir(row: dict, cikti: Path, tablo_yolu, tablo_hash: str) -> dict:
    """Bir havuz satırı -> sonuç sözlüğü (csv satırı). Ham koşu bitmemişse RuntimeError('ham koşu bitmemiş')."""
    ad, tf, evren, stil = row["strateji"], row["tf"], row["evren"], row["stil_v2"]
    out = {"strateji": ad, "tf": tf, "evren": evren, "stil_v2": stil, "durum": "", "hata": "", "n_disarida": 0, "n_hatali": 0,
           "maliyet_hash": tablo_hash}
    if stil == "portfoy":
        g1, m1 = hm.pf_yukle(cikti, 1.0, ad, tablo_hash)
        g2, m2 = hm.pf_yukle(cikti, 2.0, ad, tablo_hash)
        if g1 is None or g2 is None:
            hata = (m1 if g1 is None else m2).get("hata", "")
            return _hata_satir(out, f"portföy koşusu hata: {hata}")
        out["n_disarida"] = len(m1.get("disarida", []))
        met = portfoy_metrikleri(g1, m1, g2)
        k = eleme_portfoy(met)
    else:
        evren_t = sabit.evren_listesi(evren)
        ham1, b1 = hm.ham_yukle(cikti, 1.0, ad, tf, evren_t, tablo_hash)
        ham2, b2 = hm.ham_yukle(cikti, 2.0, ad, tf, evren_t, tablo_hash)
        out["n_disarida"], out["n_hatali"] = len(b1["disarida"]), len(set(b1["hatali"]) | set(b2["hatali"]))
        if out["n_hatali"]:
            return _hata_satir(out, f"{out['n_hatali']} sembolde koşu hatası: {b1['hata_ornegi'] or b2['hata_ornegi']}")
        if not ham1:
            return _hata_satir(out, "hiç enstrümanda ham sonuç yok (veri yok)")
        if set(ham1) != set(ham2):
            return _hata_satir(out, "x1 ve x2 farklı enstrüman kümeleri")
        met = tek_metrikler(ham1, ham2, b1, evren, tablo_yolu)
        k = eleme_tek(met, evren)
        out["ayar"] = b1["ayar"]
    for kk, v in met.items():
        out[kk] = json.dumps(v, sort_keys=True) if isinstance(v, dict) else v
    out.update(k)
    out["durum"] = "gecti" if k["gecti"] else "elendi"
    out["p_ust"] = p_ust(k["gecti"])
    return out


def _hata_satir(out: dict, neden: str) -> dict:
    out.update(durum="hata", hata=neden, gecti=False, nedenler="hata: " + neden, p_ust=1.0)
    out.update({k: False for k in KAPILAR})
    return out


# ============================================================================ aşama
_AYAR: dict = {}


def _baslat(ayar: dict):
    _AYAR.clear()
    _AYAR.update(ayar)


def _isci(g: dict):
    son = _AYAR.get("son")
    if son is not None and time.time() > son:
        return {"ertelendi": True, "strateji": g["row"]["strateji"], "tf": g["row"]["tf"]}
    cikti = Path(_AYAR["cikti"])
    try:
        s = satir_degerlendir(g["row"], cikti, _AYAR["tablo_yolu"], _AYAR["tablo_hash"])
    except RuntimeError as e:
        if "bitmemiş" in str(e):
            return {"ertelendi": True, "neden": str(e), "strateji": g["row"]["strateji"], "tf": g["row"]["tf"]}
        raise
    _satir_yaz(cikti, s)
    return s


def _satir_yolu(cikti: Path, ad: str, tf: str) -> Path:
    return Path(cikti) / "eleme_satir" / f"{ad}--{tf}.json"


def _satir_yaz(cikti: Path, s: dict):
    y = _satir_yolu(cikti, s["strateji"], s["tf"])
    y.parent.mkdir(parents=True, exist_ok=True)
    g = y.with_suffix(".jtmp")
    g.write_text(json.dumps(s, ensure_ascii=False, default=str))
    g.replace(y)


def eleme_asamasi(cikti: Path = None, surec: int = sabit.SUREC_VARSAYILAN, butce_sn: Optional[float] = None, havuz_yolu=None, muhur_yolu=None,
                  ilerleme: bool = True, yeniden: bool = False) -> dict:
    """P1-2. Satır sonuçları bitince diske yazılır (eleme_satir/); tüm satırlar tamsa eleme.csv (+ eleme_ozet.json) yazılır.
    Eksik ham koşu ya da bütçe dolması: eleme.csv YAZILMAZ, kalanlar raporlanır (yeniden çalıştırınca sürer)."""
    cikti = Path(cikti or sabit.CIKTI)
    muhur = hm.havuz_muhru_dogrula(havuz_yolu, muhur_yolu)
    havuz = hm.havuz_oku(havuz_yolu)
    tablo = maliyet.tablo_yolu(cikti)
    if not tablo.exists():
        raise RuntimeError(f"v2 maliyet tablosu yok: {tablo} (önce ham aşaması)")
    tablo_hash = evren_maliyet.tablo_hash(tablo)
    gorev = []
    for _, row in havuz.iterrows():
        y = _satir_yolu(cikti, row["strateji"], row["tf"])
        if y.exists() and not yeniden:
            continue
        gorev.append({"row": {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in row.items()}})
    if ilerleme:
        print(f"[v2 eleme] {len(havuz)} satır, hesaplanacak {len(gorev)}", flush=True)
    ayar = {"cikti": str(cikti), "tablo_yolu": str(tablo), "tablo_hash": tablo_hash}
    sonuc = we.havuz_calistir(_isci, gorev, surec, _baslat, ayar, butce_sn, ilerleme, "v2 eleme")
    bekleyen = [s for s in sonuc if s.get("ertelendi")]
    eksik = [r for _, r in havuz.iterrows() if not _satir_yolu(cikti, r["strateji"], r["tf"]).exists()]
    ozet = {"satir": len(havuz), "hesaplanan": len(sonuc) - len(bekleyen), "bekleyen": len(eksik)}
    if eksik:
        ornek = next((s.get("neden") for s in bekleyen if s.get("neden")), "bütçe doldu")
        ozet["neden"] = ornek
        if ilerleme:
            print(f"[v2 eleme] TAMAMLANMADI: {ozet}", flush=True)
        return ozet
    satirlar = []
    for _, row in havuz.iterrows():
        s = json.loads(_satir_yolu(cikti, row["strateji"], row["tf"]).read_text())
        for c in ("etiket", "alt_etiket", "kume_no", "kilit_gorulmus"):
            s[c] = row.get(c)
        satirlar.append(s)
    df = pd.DataFrame(satirlar)
    on = ["strateji", "stil_v2", "tf", "evren", "etiket", "alt_etiket", "kume_no", "kilit_gorulmus", "durum", "gecti"]
    sut = on + [c for c in ("e1", "e2", "e3", "e4", "e5", "p_ust", "nedenler", "hata") if c in df.columns]
    df = df[sut + [c for c in df.columns if c not in sut]]
    yol = cikti / "eleme.csv"
    df.to_csv(yol, index=False)
    import hashlib
    ozet.update(gecen=int((df["durum"] == "gecti").sum()), elenen=int((df["durum"] == "elendi").sum()),
                hata=int((df["durum"] == "hata").sum()), m=muhur.get("m"),
                kapi_gecen={k: int(df[k].astype(bool).sum()) for k in KAPILAR if k in df.columns},
                eleme_csv_sha256=hashlib.sha256(yol.read_bytes()).hexdigest(), havuz_csv_sha256=muhur["havuz_csv_sha256"],
                maliyet_tablosu_sha256=tablo_hash)
    (cikti / "eleme_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    if ilerleme:
        print(f"[v2 eleme] {ozet}", flush=True)
    return ozet
