#!/usr/bin/env bash
# Paper v2 setine 6 kapanış stratejisi ekleme (10 -> 16 hesap). ÖNCE KAPANIS_EKLEME_SUNUCU_ADIMLARI.md 1-3. adımları (stop, yedek, git pull) yapılmış olmalı:
#   cd /opt/1l3a && sudo bash deploy/v2_kapanis_ekle.sh
# Bu betik git pull YAPMAZ. Yaptıkları: paper durmuş mu bakar (değilse durdurur), ek kopya yedek alır, bağımlılıkları kurar,
# durum dosyasının 10'lu setin imzasını (985f914d0bb6b643) taşıdığını doğrular (değilse BAŞLATMAZ), çevrimdışı ön kontrol yapar,
# paper'ı başlatır, 3 dk sonra kontrol yazar. Mevcut 10 hesap aynen yüklenir; 6 yeni hesap sıfırdan açılır. Gizli anahtar kullanmaz.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "HATA: root olarak çalıştırın (sudo bash ...)"; exit 1; }
KOD=/opt/1l3a
VAR=/var/lib/1l3a-paper
BEKLENEN_IMZA=985f914d0bb6b643
YEDEK="$VAR/yedek_16_betik_$(date +%Y%m%d_%H%M)"
ASAMA="başlangıç"

hata() {
  echo
  echo "################ HATA: betik '$ASAMA' aşamasında durdu ################"
  echo "PAPER ŞU AN DURMUŞ OLABİLİR (1l3a-paper). Durum dosyaları SİLİNMEDİ; yedek: $YEDEK (ve adım 2'deki yedek_16_oncesi_*)."
  echo "Ne yapmalı:"
  echo "  1) Yukarıdaki hata mesajını bana (Claude'a) yapıştırın; bu hata düzelene kadar paper'ı BAŞLATMAYIN (açık hatayla düşer ve tekrar dener)."
  echo "  2) Eski haline hemen dönmek isterseniz: KAPANIS_EKLEME_SUNUCU_ADIMLARI.md 'Geri dönüş' bölümü"
  echo "     (git checkout <adım 2'de not ettiğiniz sürüm>; systemctl start 1l3a-paper). Eski kod 10'lu durumu sorunsuz yükler."
  echo "######################################################################"
}
trap hata ERR

cd "$KOD"
ASAMA="0/5 paper durmuş mu"
if systemctl is-active --quiet 1l3a-paper; then
  echo "paper hâlâ çalışıyor: durduruluyor (adım 1'i atlamışsınız; yedek aşağıda alınacak)"
  systemctl stop 1l3a-paper
fi

ASAMA="1/5 durum dosyası ve yedek"
[ -f "$VAR/durum/paper_state.json" ] || { echo "HATA: $VAR/durum/paper_state.json yok; bu betik MEVCUT bir paper durumu içindir"; false; }
cp -a "$VAR/durum" "$YEDEK"
echo "yedek: $YEDEK"

ASAMA="2/5 durum imzası kontrolü"
IMZA=$(python3 -c "import json;print(json.load(open('$VAR/durum/paper_state.json')).get('set_imza'))")
echo "durum dosyasındaki set_imza: $IMZA (beklenen $BEKLENEN_IMZA)"
if [ "$IMZA" != "$BEKLENEN_IMZA" ]; then
  if python3 -c "import json,sys;d=json.load(open('$VAR/durum/paper_state.json'));sys.exit(0 if len(d.get('hesaplar',{}))==16 else 1)"; then
    echo "Durum dosyası zaten 16 hesaplı (geçiş daha önce yapılmış). Başlatmak için: sudo systemctl start 1l3a-paper"
    exit 0
  fi
  echo "DURDU: durum dosyasının imzası 10'lu setinki değil; geçiş yapılmaz, paper BAŞLATILMADI. Dosya dokunulmadı."
  false
fi

ASAMA="3/5 bağımlılıklar"
sudo -u l3a .venv/bin/pip install -q -r requirements.txt

ASAMA="4/5 çevrimdışı ön kontrol (set, 16 hesap, fail-closed, bütünlük kaydı)"
sudo -u l3a env PYTHONPATH="$KOD" .venv/bin/python - <<'PY'
from motor.canli import paper_v2 as v2
s = v2.set_yukle()
t = v2.tanimlari_yukle(s)
assert len(t) == 16, len(t)
assert v2.onceki_set_imzasi(s) == "985f914d0bb6b643", v2.onceki_set_imzasi(s)
print("set tamam: 16 hesap; eski imza", v2.onceki_set_imzasi(s), "yeni imza", v2.set_imzasi(s))
PY
sudo -u l3a env PYTHONPATH="$KOD" .venv/bin/python -m motor.canli.guven | tail -3 || true

ASAMA="5/5 paper başlatılıyor"
systemctl daemon-reload
systemctl start 1l3a-paper
trap - ERR
echo "3 dakika bekleniyor (ilk açılış 6 yeni hesabın geçmişini kurar; 5m geçmişi biraz sürer)..."
sleep 180

echo "================ KONTROL ================"
systemctl is-active 1l3a-paper || true
echo "hesap klasörü sayısı (16 olmalı): $(ls "$VAR/durum/hesaplar" 2>/dev/null | wc -l)"
python3 - <<PY
import json
d = json.load(open("$VAR/durum/paper_state.json"))
print(" hesap sayısı:", len(d["hesaplar"]), " set_imza:", d["set_imza"], "(beklenen 4c22e27149b65a14)")
PY
journalctl -u 1l3a-paper -n 40 --no-pager
echo "yedek: $YEDEK"
echo "========== BU ÇIKTININ TAMAMINI CLAUDE'A YAPIŞTIRIN =========="
