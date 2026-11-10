#!/usr/bin/env bash
# Paper v2 setine tek komutla geçiş (sunucuda root olarak):
#   cd /opt/1l3a && sudo -u l3a git pull && bash deploy/v2_gecis.sh
# Yaptıkları: paper'ı durdurur, eski 7'li durumu SİLMEDEN kenara alır, bağımlılıkları kurar, yeni hisse/emtia
# sembollerinin tohum geçmişini (Dukascopy saatlik) sunucuda indirir, paper'ı başlatır, 5 dk sonra kontrol yazar.
# Kripto için tohum gerekmez: geçmiş Binance REST'ten alınır. Gizli anahtar kullanmaz.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "HATA: root olarak çalıştırın"; exit 1; }
KOD=/opt/1l3a
VAR=/var/lib/1l3a-paper
YENI_DK="DK_AVGO DK_LLY DK_WMT DK_JPM DK_V DK_MU DK_AMD DK_XOM DK_XAG DK_NATGAS"

echo "== 1/5 paper durduruluyor"
systemctl stop 1l3a-paper

echo "== 2/5 eski durum kenara alınıyor (silinmez)"
if [ -d "$VAR/durum" ]; then
  HEDEF="$VAR/durum_eski_7li_$(date +%Y%m%d_%H%M)"
  mv "$VAR/durum" "$HEDEF"
  echo "eski durum: $HEDEF"
fi

echo "== 3/5 bağımlılıklar"
cd "$KOD"
sudo -u l3a .venv/bin/pip install -q -r requirements.txt

echo "== 4/5 yeni sembollerin tohum geçmişi indiriliyor (birkaç dakika)"
install -d -o l3a -g l3a "$VAR/veri" "$VAR/veri/mumlar"
sudo -u l3a env PYTHONPATH="$KOD" "$KOD/.venv/bin/python" -m motor.veri.dukascopy \
  --semboller $YENI_DK --aralik 1h --baslangic 2017-01
for s in $YENI_DK; do
  if [ -f "$KOD/veri/mumlar/$s/1h.parquet" ]; then
    install -d -o l3a -g l3a "$VAR/veri/mumlar/$s"
    install -o l3a -g l3a -m 644 "$KOD/veri/mumlar/$s/1h.parquet" "$VAR/veri/mumlar/$s/1h.parquet"
  else
    echo "UYARI: $s indirilemedi; strateji bu sembolde kısa geçmişle başlar"
  fi
done
chown -R l3a:l3a "$VAR"

echo "== 5/5 paper başlatılıyor"
systemctl daemon-reload
systemctl start 1l3a-paper
echo "5 dakika bekleniyor (ilk açılış geçmişi kurar)..."
sleep 300

echo "================ KONTROL ================"
systemctl is-active 1l3a-paper || true
echo "hesap klasörü sayısı (10 olmalı): $(ls "$VAR/durum/hesaplar" 2>/dev/null | wc -l)"
journalctl -u 1l3a-paper -n 40 --no-pager
echo "========== BU ÇIKTININ TAMAMINI CLAUDE'A YAPIŞTIRIN =========="
