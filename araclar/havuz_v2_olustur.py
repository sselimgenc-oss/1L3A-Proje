"""v2 dondurulmuş strateji havuzunu üretir (ÖN KAYIT v2, bölüm 2 — Aşama 0).

Girdiler:
  * motor/ strateji kaydı (kayit.tum_stratejiler) ve portföy sınıfları (tum_portfoy_stratejileri);
  * stratejiler/havuz_v2_etiketler.csv  (2.6 etiketleri; YALNIZ kural metni/kod/kart'tan, sonuç görmeden yazıldı);
  * kaynak kartlar (veri/kartlar_ham, stratejiler/aileler.json, kodlama_*.csv, dis_envanter.csv) -> 2.4 zaman dilimi;
  * sonuclar/evren/2017_gelistirme/oos/*.parquet (YALNIZ 2.7(b) haftalık seri; etiketler sabitlendikten sonra okunur);
  * stratejiler/final_set.json, sonuclar/kilit/*set* (YALNIZ strateji ADLARI; sonuç değeri okunmaz) -> 2.9.
Çıktılar:
  * stratejiler/havuz_v2.csv
  * sonuclar/evren/v2/havuz_muhru.json

Ağ yok, rastgelelik yok; aynı girdiyle aynı csv (bayt bayt). Hata sessiz yutulmaz.
Kullanım:  python araclar/havuz_v2_olustur.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

# ------------------------------------------------------------------ sabitler (ON_KAYIT_V2 bölüm 2)
ETIKET_DOSYASI = KOK / "stratejiler" / "havuz_v2_etiketler.csv"
HAVUZ_CSV = KOK / "stratejiler" / "havuz_v2.csv"
MUHUR_JSON = KOK / "sonuclar" / "evren" / "v2" / "havuz_muhru.json"
OOS_DIZINI = KOK / "sonuclar" / "evren" / "2017_gelistirme" / "oos"
KART_DIZINI = KOK / "veri" / "kartlar_ham"
AILELER = KOK / "stratejiler" / "aileler.json"
ENVANTER = KOK / "stratejiler" / "dis_envanter.csv"
FINAL_SET = KOK / "stratejiler" / "final_set.json"
KILIT_DIZINI = KOK / "sonuclar" / "kilit"
SON1AY_BILGI = KOK / "sonuclar" / "son1ay_kilit_bilgi.json"

SUTUNLAR = ["strateji", "stil_v2", "tf", "evren", "etiket", "alt_etiket", "kume_no", "kaynak_strateji",
            "kilit_gorulmus", "not"]
ETIKETLER = {"trend", "geri_cekilme", "donus", "kirilim", "formasyon", "seviye", "takvim", "hacim", "funding",
             "kesitsel", "karma"}
STIL_SIRASI = {"swing": 0, "gunici_kripto": 1, "portfoy": 2}
KITAP_ONEKLERI = ("swing", "daytrade", "scalp")

# 2.5: gün içi kripto hipotezi, tam 7 satır
GUNICI_KRIPTO = ("dis__ewo-ema-ofset", "dis__bb-alt-bant-osilator", "dis__ft-cluc-may2018", "dis__ft-binhv45",
                 "dis__ft-cofibit", "dis__e0v1en", "dis__aroon-stochrsi-ema-dip")
GUNICI_TF = "15m"
# 2.7(b)
RHO_ESIK = 0.7
MIN_ORTAK_HAFTA = 100
# 2.10
M_TABAN = 939
# 2.4 işaretleri (küçük harfe çevrilmiş metinde; sol sınır: önünde harf/rakam yok)
_TF4H = re.compile(r"(?<![0-9a-z])(?:4h|4s|h4|240)")
_TF1D = re.compile(r"(?<![0-9a-z])(?:1d|1g|daily|günlük)|(?<![0-9a-z])d(?![0-9a-z])")
_AD_RE = re.compile(r"[a-z0-9]+__[a-z0-9_\-]+")


# ------------------------------------------------------------------ 2.3 klon kuralı
def govde_adi(ad: str) -> str | None:
    """Kitap stratejisi (swing__/daytrade__/scalp__) ise gövde adı, değilse None."""
    onek, ayrac, govde = ad.partition("__")
    return govde if ayrac and onek in KITAP_ONEKLERI else None


def klon_kurali(tum_adlar) -> tuple[dict[str, list[str]], list[str]]:
    """2.3: aynı gövde adı birden çok stilde varsa yalnız `swing__` kalır; swing karşılığı yoksa strateji havuza girmez.
    Dönüş: ({swing__ ad: [elenen klonlar]}, [swing__ olmayan kitap stratejileri (havuz dışı)]).
    Kitap önekli olmayan adlar (dis__, onceki__ ...) klon kuralına girmez."""
    govdeler: dict[str, list[str]] = {}
    for ad in sorted(set(tum_adlar)):
        g = govde_adi(ad)
        if g is not None:
            govdeler.setdefault(g, []).append(ad)
    tutulan, atilan = {}, []
    for g, adlar in sorted(govdeler.items()):
        swing = f"swing__{g}"
        if swing in adlar:
            tutulan[swing] = [a for a in adlar if a != swing]
        atilan += [a for a in adlar if a != swing]
    return tutulan, sorted(atilan)


# ------------------------------------------------------------------ 2.4 birincil tf
def birincil_tf(zaman_dilimi_metinleri) -> str:
    """4h <=> (4h|4s|H4|240 içeriyor) VE (1d|1g|D|günlük|daily içermiyor); aksi halde (boş dahil) 1d.
    Metinler birleştirilir (birden çok kaynak kaydı varsa HEPSİNDE birlikte bakılır: bir kayıt bile 1d diyorsa 1d)."""
    metin = " ".join(str(m) for m in zaman_dilimi_metinleri if m is not None and str(m).strip()).lower()
    if not metin:
        return "1d"
    if _TF4H.search(metin) and not _TF1D.search(metin):
        return "4h"
    return "1d"


def _kart_metni(kart: dict) -> str:
    z = kart.get("zaman_dilimi")
    return "" if z is None else (json.dumps(z, ensure_ascii=False) if not isinstance(z, str) else z)


class KaynakKayitlari:
    """Strateji -> kaynak kayıtlarının `zaman_dilimi` metinleri (kart ya da dis_envanter.csv). Yalnız okuma."""

    def __init__(self, kok: Path = KOK):
        self.kartlar: dict[str, str] = {}
        for yol in sorted((kok / "veri" / "kartlar_ham").rglob("*.json")):
            for k in json.loads(yol.read_text(encoding="utf-8-sig")):
                if isinstance(k, dict) and "kart_id" in k:
                    self.kartlar[k["kart_id"]] = _kart_metni(k)
        self.aileler = {a["aile_id"]: a for a in json.loads((kok / "stratejiler" / "aileler.json")
                                                             .read_text(encoding="utf-8"))}
        self.env = pd.read_csv(kok / "stratejiler" / "dis_envanter.csv", dtype=str, keep_default_na=False)
        # strateji adı -> [envanter satır no] ve [kart id]
        self.env_satir: dict[str, set[int]] = {}
        self.kart_kimlik: dict[str, set[str]] = {}
        sd = kok / "stratejiler"
        ad_env = {}
        for i, a in enumerate(self.env["ad"]):
            ad_env.setdefault(a, []).append(i)
        a_csv = pd.read_csv(sd / "kodlama_2026-11-07_a.csv", dtype=str, keep_default_na=False)
        for _, r in a_csv.iterrows():
            if r["yeni_strateji_adi"]:
                self.env_satir.setdefault(r["yeni_strateji_adi"], set()).add(int(r["satir_indeksi"]))
        b_csv = pd.read_csv(sd / "kodlama_2026-11-07_b.csv", dtype=str, keep_default_na=False)
        for _, r in b_csv.iterrows():
            if r["yeni_strateji_adi"] and r["kaynak_dosya"] == "dis_envanter":
                self.env_satir.setdefault(r["yeni_strateji_adi"], set()).add(int(r["satir_indeksi_veya_madde_no"]))
        for yol in sorted(sd.glob("kodlama_*.csv")):
            d = pd.read_csv(yol, dtype=str, keep_default_na=False)
            if "kaynak_kartlar" not in d.columns:
                continue
            for _, r in d.iterrows():
                ad = r["yeni_strateji_adi"]
                if not ad:
                    continue
                for tok in (t.strip() for t in r["kaynak_kartlar"].split(";")):
                    if tok in self.kartlar:
                        self.kart_kimlik.setdefault(ad, set()).add(tok)
                    elif tok.startswith("repo:") and tok[5:] in ad_env:
                        self.env_satir.setdefault(ad, set()).update(ad_env[tok[5:]])
        self.dosya_env = {}
        for i, f in enumerate(self.env["dosya"]):
            if f:
                self.dosya_env.setdefault(f, []).append(i)

    def metinler(self, ad: str, sinif_dokumani: str = "") -> list[str]:
        """Bu strateji için bulunan tüm kaynak kaydı zaman_dilimi metinleri (boş olanlar atılır)."""
        satirlar = set(self.env_satir.get(ad, ()))
        kartlar = set(self.kart_kimlik.get(ad, ()))
        if ad in self.aileler:
            kartlar |= {k for k in self.aileler[ad].get("kaynak_kartlar", []) if k in self.kartlar}
        for f in re.findall(r"arsiv/[^\s,;)\"']+", sinif_dokumani or ""):
            satirlar.update(self.dosya_env.get(f.rstrip("."), ()))
        cikti = [self.kartlar[k] for k in sorted(kartlar)]
        cikti += [self.env.iloc[i]["zaman_dilimi"] for i in sorted(satirlar)]
        return [m for m in cikti if m and m.strip()]


# ------------------------------------------------------------------ varsayılan ayar ve sayısal parametre sayısı
def varsayilan_ayar(sinif, kart_ayari_listesi=None) -> dict:
    """1.1: sınıfın varsayılan parametreleri; kart ayarı dosyası varsa İLK kaydın parametreleri üstüne bindirilir."""
    ayar = dict(sinif.varsayilan_parametreler)
    if kart_ayari_listesi:
        ayar.update(kart_ayari_listesi[0].get("parametreler") or {})
    return ayar


def sayisal_parametre_sayisi(ayar: dict) -> int:
    """Varsayılan ayar sözlüğündeki SAYISAL (int/float, bool DEĞİL) değer sayısı; liste/tuple/dict içindeki sayılar
    tek tek sayılır; metin, bool, None sayılmaz."""
    def say(v) -> int:
        if isinstance(v, bool) or v is None:
            return 0
        if isinstance(v, (int, float, np.integer, np.floating)):
            return 1
        if isinstance(v, dict):
            return sum(say(x) for x in v.values())
        if isinstance(v, (list, tuple, set, frozenset)):
            return sum(say(x) for x in v)
        return 0
    return sum(say(v) for v in ayar.values())


# ------------------------------------------------------------------ 2.7 kümeleme
def haftalik_seri(oos: pd.DataFrame) -> pd.Series:
    """Kabul edilen işlemlerin pnl'i çıkış gününe (UTC), haftalık (Pazar kapanışlı) toplam. İndeks: PeriodIndex('W-SUN');
    serinin ilk-son haftası arasındaki işlemsiz haftalar 0."""
    k = oos[oos["kabul"].astype(bool)]
    if k.empty:
        return pd.Series(dtype=float, index=pd.PeriodIndex([], freq="W-SUN"))
    cikis = pd.DatetimeIndex(pd.to_datetime(k["cikis"], utc=True)).tz_convert("UTC").tz_localize(None)
    hafta = cikis.to_period("W-SUN")
    s = pd.Series(k["pnl"].to_numpy(dtype=float), index=hafta).groupby(level=0).sum()
    tam = pd.period_range(s.index.min(), s.index.max(), freq="W-SUN")
    return s.reindex(tam, fill_value=0.0)


def korelasyon(a: pd.Series | None, b: pd.Series | None, min_hafta: int = MIN_ORTAK_HAFTA) -> float:
    """Ortak haftalardaki Pearson korelasyonu; ortak hafta < min_hafta ya da sabit seri ise NaN (= ölçülemedi)."""
    if a is None or b is None:
        return float("nan")
    ortak = a.index.intersection(b.index)
    if len(ortak) < min_hafta:
        return float("nan")
    x, y = a.loc[ortak].to_numpy(dtype=float), b.loc[ortak].to_numpy(dtype=float)
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def ortalama_baglanti(adlar: list[str], seriler: dict, rho_esik: float = RHO_ESIK,
                      min_hafta: int = MIN_ORTAK_HAFTA) -> list[list[str]]:
    """Tek bir (etiket, alt_etiket) grubu için ortalama bağlantılı (UPGMA) kümeleme; uzaklık = 1 - rho; iki küme,
    ortalama uzaklık <= 1 - rho_esik ise birleşir. Ölçülemeyen çift (NaN) uzaklığı SONSUZ sayılır: böyle bir çifti
    içeren kümeler hiç birleşmez ('ölçülemedi = ayrı küme'). Eşitlikte alfabetik (ilk üye adı) sırası."""
    adlar = sorted(adlar)
    n = len(adlar)
    d = np.full((n, n), np.inf)
    for i in range(n):
        for j in range(i + 1, n):
            r = korelasyon(seriler.get(adlar[i]), seriler.get(adlar[j]), min_hafta)
            if not np.isnan(r):
                d[i, j] = d[j, i] = 1.0 - r
    kumeler = [[i] for i in range(n)]
    sinir = 1.0 - rho_esik + 1e-12
    while len(kumeler) > 1:
        en_iyi = None
        for a in range(len(kumeler)):
            for b in range(a + 1, len(kumeler)):
                ort = float(np.mean([d[i, j] for i in kumeler[a] for j in kumeler[b]]))
                if ort <= sinir and (en_iyi is None or ort < en_iyi[0] - 1e-15):
                    en_iyi = (ort, a, b)
        if en_iyi is None:
            break
        _, a, b = en_iyi
        kumeler[a] = sorted(kumeler[a] + kumeler[b])
        del kumeler[b]
        kumeler.sort(key=lambda k: k[0])
    return [[adlar[i] for i in k] for k in kumeler]


def temsilci(uyeler: list[str], parametre_sayisi: dict[str, int]) -> str:
    """En az sayısal parametreli; eşitlikte alfabetik ilk."""
    return min(uyeler, key=lambda a: (parametre_sayisi[a], a))


# ------------------------------------------------------------------ 2.9 ad taraması
def adlari_tara(metin: str, gecerli_adlar: set[str]) -> set[str]:
    """Metindeki strateji ADLARI (sonuç değeri okunmaz); yalnız havuz adlarıyla kesişim."""
    return {a for a in _AD_RE.findall(metin.lower()) if a in gecerli_adlar}


def kilit_gorulmus_adlar(gecerli_adlar: set[str], son1ay_kod_adlari: set[str], kok: Path = KOK) -> set[str]:
    bulunan: set[str] = set(son1ay_kod_adlari) & gecerli_adlar
    kaynaklar = [kok / "stratejiler" / "final_set.json", kok / "sonuclar" / "son1ay_kilit_bilgi.json"]
    kaynaklar += sorted(p for p in (kok / "sonuclar" / "kilit").rglob("*") if p.is_file() and "set" in p.name.lower()
                        and p.suffix in (".csv", ".json", ".md", ".txt"))
    for yol in kaynaklar:
        if yol.exists():
            bulunan |= adlari_tara(yol.read_text(encoding="utf-8"), gecerli_adlar)
    return bulunan


# ------------------------------------------------------------------ havuz kurma
def etiketleri_oku(yol: Path = ETIKET_DOSYASI) -> dict[str, dict]:
    d = pd.read_csv(yol, dtype=str, keep_default_na=False)
    if list(d.columns) != ["strateji", "etiket", "alt_etiket", "gerekce"]:
        raise ValueError(f"{yol}: beklenmeyen sütunlar {list(d.columns)}")
    if d["strateji"].duplicated().any():
        raise ValueError(f"{yol}: yinelenen strateji: {d['strateji'][d['strateji'].duplicated()].tolist()}")
    kotu = d[~d["etiket"].isin(ETIKETLER) | (d["alt_etiket"] == "")]
    if len(kotu):
        raise ValueError(f"{yol}: geçersiz etiket/alt_etiket: {kotu['strateji'].tolist()}")
    return {r["strateji"]: {"etiket": r["etiket"], "alt_etiket": r["alt_etiket"], "gerekce": r["gerekce"]}
            for _, r in d.iterrows()}


def aday_satirlari() -> tuple[list[dict], dict]:
    """Kümeleme öncesi aday satırlar (strateji, stil_v2, tf, evren, parametre sayısı, klonlar) ve ek bilgi."""
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    from motor.strateji import kayit

    kaynak = KaynakKayitlari()
    reg = kayit.tum_stratejiler()
    pf = tum_portfoy_stratejileri()
    tutulan, atilan = klon_kurali(reg.keys())
    satirlar: list[dict] = []
    for ad in sorted(reg):
        s = reg[ad]
        if ad in GUNICI_KRIPTO:
            stil_v2, tf, evren = "gunici_kripto", GUNICI_TF, "kripto"
        elif s.stil == "swing":
            if govde_adi(ad) is not None and ad not in tutulan:      # klon kuralı (swing_ olmayan kitap) — swing stilinde olmaz
                continue
            doc = reg[ad].__dict__.get("__doc__") or ""
            tf = birincil_tf(kaynak.metinler(ad, doc))
            # funding_gerekli: funding dosyası yalnız kripto perp'te var (DK_ sembollerde yok -> açık hata) -> evren kripto
            stil_v2, evren = "swing", ("kripto" if getattr(s, "funding_gerekli", False) else "genel")
        else:
            continue
        ayar = varsayilan_ayar(s, kayit.kart_ayarlari(ad))
        satirlar.append({"strateji": ad, "stil_v2": stil_v2, "tf": tf, "evren": evren,
                         "param_say": sayisal_parametre_sayisi(ayar),
                         "kaynak_strateji": ";".join(tutulan.get(ad, []))})
    for ad in sorted(pf):
        satirlar.append({"strateji": ad, "stil_v2": "portfoy", "tf": "1d", "evren": "genel",
                         "param_say": sayisal_parametre_sayisi(varsayilan_ayar(pf[ad])), "kaynak_strateji": ""})
    eksik = [g for g in GUNICI_KRIPTO if g not in reg]
    if eksik:
        raise KeyError(f"2.5 stratejileri kayıtta yok: {eksik}")
    son1ay = {a for a, s in reg.items() if s.__module__.endswith("d7_son1ay")}
    son1ay |= {a for a, s in pf.items() if s.__module__.endswith("stratejiler.son1ay")}
    return satirlar, {"son1ay_kod_adlari": son1ay}


def oos_serileri(satirlar: list[dict], oos_dizini: Path = OOS_DIZINI) -> dict[str, pd.Series]:
    seriler = {}
    for r in satirlar:
        yol = oos_dizini / f"{r['strateji']}--{r['tf']}.parquet"
        if yol.exists():
            seriler[r["strateji"]] = haftalik_seri(pd.read_parquet(yol, columns=["cikis", "kabul", "pnl"]))
    return seriler


def havuz_kur(satirlar: list[dict], etiketler: dict[str, dict], seriler: dict, kilitli: set[str],
              kumeleme_stilleri=("swing",)) -> tuple[pd.DataFrame, list[list[str]]]:
    """Etiketleri bağlar, 2.7 kümelemesini uygular (yalnız `kumeleme_stilleri` stillerinde, aynı stil + aynı
    etiket + alt_etiket grubunda), temsilcileri seçer. Dönüş: (havuz tablosu, tüm kümeler)."""
    eksik = [r["strateji"] for r in satirlar if r["strateji"] not in etiketler]
    if eksik:
        raise KeyError(f"etiketi olmayan strateji: {eksik}")
    fazla = sorted(set(etiketler) - {r["strateji"] for r in satirlar})
    if fazla:
        raise KeyError(f"etiket dosyasında olup havuz adayı olmayan strateji: {fazla}")
    by = {r["strateji"]: r for r in satirlar}
    grup: dict[tuple, list[str]] = {}
    for r in satirlar:
        e = etiketler[r["strateji"]]
        anahtar = (r["stil_v2"], e["etiket"], e["alt_etiket"]) if r["stil_v2"] in kumeleme_stilleri \
            else (r["stil_v2"], "tekil", r["strateji"])
        grup.setdefault(anahtar, []).append(r["strateji"])
    kumeler: list[list[str]] = []
    for anahtar in sorted(grup):
        kumeler += ortalama_baglanti(grup[anahtar], seriler)
    psay = {a: by[a]["param_say"] for a in by}
    secilen = []
    for k in kumeler:
        t = temsilci(k, psay)
        secilen.append((t, k))
    secilen.sort(key=lambda x: (STIL_SIRASI[by[x[0]]["stil_v2"]], x[0]))
    satir_cikti = []
    for no, (t, k) in enumerate(secilen, start=1):
        r, e = by[t], etiketler[t]
        diger = [a for a in k if a != t]
        not_ = f"param_say={r['param_say']}"
        if diger:
            not_ += f"; kume_uyeleri_havuz_disi={'/'.join(diger)}"
        satir_cikti.append({"strateji": t, "stil_v2": r["stil_v2"], "tf": r["tf"], "evren": r["evren"],
                            "etiket": e["etiket"], "alt_etiket": e["alt_etiket"], "kume_no": no,
                            "kaynak_strateji": r["kaynak_strateji"],
                            "kilit_gorulmus": "evet" if (set(k) & kilitli) else "hayir", "not": not_})
    return pd.DataFrame(satir_cikti, columns=SUTUNLAR), [sorted(k) for k in kumeler]


def m_hesapla(satir_sayisi: int) -> int:
    """2.10: m = max(havuz satır sayısı, 939)."""
    return max(int(satir_sayisi), M_TABAN)


def csv_baytlari(havuz: pd.DataFrame) -> bytes:
    tampon = io.StringIO()
    havuz.to_csv(tampon, index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    return tampon.getvalue().encode("utf-8")


def sha256_bayt(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_bilgisi(kok: Path = KOK) -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kok, capture_output=True, text=True, check=True).stdout.strip()
    kirli = bool(subprocess.run(["git", "status", "--porcelain", "--", "motor", "araclar/havuz_v2_olustur.py"],
                                cwd=kok, capture_output=True, text=True, check=True).stdout.strip())
    return commit, kirli


def muhur_yaz(havuz: pd.DataFrame, csv_yolu: Path, muhur_yolu: Path, script_yolu: Path, etiket_yolu: Path,
              kok: Path = KOK, zaman: dt.datetime | None = None) -> dict:
    commit, kirli = git_bilgisi(kok)
    zaman = zaman or dt.datetime.now(dt.timezone.utc)
    muhur = {
        "surum": 1,
        "havuz_csv": str(csv_yolu.relative_to(kok)) if csv_yolu.is_relative_to(kok) else str(csv_yolu),
        "havuz_csv_sha256": sha256_bayt(csv_yolu.read_bytes()),
        "satir_sayisi": int(len(havuz)),
        "m": m_hesapla(len(havuz)),
        "m_kurali": f"max(havuz satır sayısı, {M_TABAN}) (ON_KAYIT_V2 2.10)",
        "etiket_dosyasi_sha256": sha256_bayt(etiket_yolu.read_bytes()),
        "script_sha256": sha256_bayt(script_yolu.read_bytes()),
        "git_commit": commit,
        "git_kod_degismis": kirli,
        "zaman_damgasi_utc": zaman.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    muhur_yolu.parent.mkdir(parents=True, exist_ok=True)
    muhur_yolu.write_text(json.dumps(muhur, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return muhur


def main() -> int:
    etiketler = etiketleri_oku()
    satirlar, ek = aday_satirlari()
    seriler = oos_serileri(satirlar)
    kilitli = kilit_gorulmus_adlar({r["strateji"] for r in satirlar}, ek["son1ay_kod_adlari"])
    havuz, kumeler = havuz_kur(satirlar, etiketler, seriler, kilitli)
    HAVUZ_CSV.write_bytes(csv_baytlari(havuz))
    muhur = muhur_yaz(havuz, HAVUZ_CSV, MUHUR_JSON, Path(__file__).resolve(), ETIKET_DOSYASI)
    birlesen = sum(len(k) - 1 for k in kumeler)
    print(f"aday {len(satirlar)} -> havuz {len(havuz)} satır; birleşen {birlesen}; "
          f"çok üyeli küme {sum(1 for k in kumeler if len(k) > 1)}; m={muhur['m']}")
    print(havuz.groupby(["stil_v2", "tf"]).size().to_string())
    print(havuz.groupby(["stil_v2", "etiket"]).size().to_string())
    print(f"kilit_gorulmus=evet: {int((havuz['kilit_gorulmus'] == 'evet').sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
