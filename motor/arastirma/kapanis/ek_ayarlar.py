"""d11j/d12b ek ayarlarını kaynak değerleriyle araştırma adayına bağlar.

Eski tarama/portföy koşucularının aday kümesine müdahale edilmez. Kapanış koşucusu
bu modülü açıkça çağırır; ızgara ve örtük varsayılan ayar eklenmez.
"""
from __future__ import annotations

import json
from pathlib import Path

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.strateji import kayit

KOK = Path(__file__).resolve().parents[3]
EK_DOSYALAR = (
    KOK / "stratejiler/ayarlar_d11j_ek.json",
    KOK / "stratejiler/ayarlar_d12b_ek.json",
)


def ek_ayarlari_oku(dosyalar: tuple[Path, ...] = EK_DOSYALAR) -> dict[str, dict]:
    """18 kimliği eksiksiz okur; çakışan/bozuk kayıt açık hata verir."""
    sonuc: dict[str, dict] = {}
    for yol in dosyalar:
        kayitlar = json.loads(yol.read_text(encoding="utf-8"))
        if not isinstance(kayitlar, list):
            raise ValueError(f"{yol}: liste bekleniyor")
        for satir in kayitlar:
            if not isinstance(satir, dict) or not all(k in satir for k in ("ayar_id", "hedef", "parametreler", "kaynak_dosya")):
                raise ValueError(f"{yol}: eksik alanlı ayar kaydı")
            if not isinstance(satir["parametreler"], dict):
                raise ValueError(f"{yol}/{satir['ayar_id']}: parametreler sözlük değil")
            kimlik = str(satir["ayar_id"])
            if kimlik in sonuc:
                raise ValueError(f"tekrarlanan ek ayar: {kimlik}")
            sonuc[kimlik] = {**satir, "ayar_dosyasi": str(yol.relative_to(KOK))}
    return sonuc


def ek_ayarli_strateji(ayar_id: str, ayarlar: dict[str, dict] | None = None):
    """Belirli tek ayarı strateji nesnesine çevirir; kaynak evrenini değiştirmez."""
    kayitlar = ek_ayarlari_oku() if ayarlar is None else ayarlar
    satir = kayitlar[ayar_id]
    hedef = satir["hedef"]
    sinif = tum_portfoy_stratejileri()[hedef] if hedef.startswith("pf__") else kayit.al(hedef)
    bilinmeyen = set(satir["parametreler"]) - set(sinif.varsayilan_parametreler)
    if bilinmeyen:
        raise ValueError(f"{ayar_id}: sınıfta olmayan parametre: {sorted(bilinmeyen)}")
    if satir.get("cikis_ayarlari") is not None:
        raise ValueError(f"{ayar_id}: özel çıkış ayarı bu okuyucuda desteklenmiyor")
    return sinif(**satir["parametreler"])
