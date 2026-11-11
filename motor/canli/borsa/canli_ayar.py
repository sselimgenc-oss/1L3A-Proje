"""Canlı yürütme yapılandırması. Anahtarlar DOSYADA YOKTUR: yalnız ortam değişkeni ADLARI yazılır; değerler sunucuda
/etc/1l3a-canli.env (chmod 600) içinden systemd ile ortama yüklenir.

Örnek: stratejiler/canli_ayar.ornek.json. Kurallar:
  - mod: kuru | testnet | canli (varsayılan testnet). `canli` için ayrıca ortamda CANLI_ONAY=evet şart; yoksa başlamaz.
  - Bir Binance hesabı (API anahtar çifti) = bir strateji. Aynı anahtar adı iki stratejide kullanılamaz (strateji arası netleştirme yok).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional

MODLAR = ("kuru", "testnet", "canli")
ONAY_ENV, ONAY_DEGER = "CANLI_ONAY", "evet"
VARSAYILAN_YOL = Path(__file__).resolve().parents[3] / "stratejiler" / "canli_ayar.json"


class CanliAyarHatasi(ValueError):
    pass


class CanliOnayHatasi(CanliAyarHatasi):
    """`canli` modu CANLI_ONAY=evet olmadan istendi: başlatma reddedilir."""


@dataclass(frozen=True)
class StratejiAyar:
    id: str
    api_key_env: str
    api_secret_env: str
    tahsis_usd: Decimal


@dataclass(frozen=True)
class CanliAyar:
    mod: str
    stratejiler: tuple
    working_type: str = "MARK_PRICE"
    giris_gecikme_max_sn: int = 900
    kosullu_modu: str = "algo"
    hedef_emri: bool = True


def yukle(yol: Optional[Path] = None, env: Optional[dict] = None) -> CanliAyar:
    env = os.environ if env is None else env
    yol = Path(yol or env.get("CANLI_AYAR") or VARSAYILAN_YOL)
    try:
        h = json.loads(yol.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CanliAyarHatasi(f"yapılandırma yok: {yol}") from None
    return coz(h, env)


def coz(h: dict, env: dict) -> CanliAyar:
    mod = h.get("mod", "testnet")
    if mod not in MODLAR:
        raise CanliAyarHatasi(f"mod {MODLAR} içinden olmalı: {mod!r}")
    if mod == "canli" and env.get(ONAY_ENV, "").strip().lower() != ONAY_DEGER:
        raise CanliOnayHatasi(f"mod=canli için ortamda {ONAY_ENV}={ONAY_DEGER} gerekir; yok: GERÇEK PARA ile başlatma reddedildi")
    wt = h.get("working_type", "MARK_PRICE")
    if wt not in ("MARK_PRICE", "CONTRACT_PRICE"):
        raise CanliAyarHatasi("working_type MARK_PRICE | CONTRACT_PRICE")
    km = h.get("kosullu_modu", "algo")
    if km not in ("algo", "klasik"):
        raise CanliAyarHatasi("kosullu_modu algo | klasik")
    ss, gorulen_id, gorulen_anahtar = [], set(), set()
    for x in h.get("stratejiler", []):
        for a in ("id", "api_key_env", "api_secret_env", "tahsis_usd"):
            if a not in x:
                raise CanliAyarHatasi(f"strateji girdisinde '{a}' yok: {x}")
        tahsis = Decimal(str(x["tahsis_usd"]))
        if tahsis <= 0:
            raise CanliAyarHatasi(f"{x['id']}: tahsis_usd > 0 olmalı")
        if x["id"] in gorulen_id or x["api_key_env"] in gorulen_anahtar:
            raise CanliAyarHatasi(f"{x['id']}: bir hesap = bir strateji (strateji ya da anahtar adı tekrarlı)")
        gorulen_id.add(x["id"])
        gorulen_anahtar.add(x["api_key_env"])
        ss.append(StratejiAyar(x["id"], x["api_key_env"], x["api_secret_env"], tahsis))
    if not ss:
        raise CanliAyarHatasi("en az bir strateji gerekir")
    return CanliAyar(mod, tuple(ss), wt, int(h.get("giris_gecikme_max_sn", 900)), km, bool(h.get("hedef_emri", True)))


def anahtarlar(s: StratejiAyar, env: Optional[dict] = None) -> tuple:
    """(anahtar, gizli) yalnız ortamdan. Eksikse hata MESAJI yalnız değişken adını içerir (değer asla)."""
    env = os.environ if env is None else env
    a, g = env.get(s.api_key_env, "").strip(), env.get(s.api_secret_env, "").strip()
    if not a or not g:
        raise CanliAyarHatasi(f"{s.id}: ortam değişkeni {s.api_key_env} / {s.api_secret_env} tanımlı değil")
    return a, g
