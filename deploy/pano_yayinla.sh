#!/usr/bin/env bash
# Sunucudaki pano.html'i Cloudflare Workers'a (statik sayfa) yayımlar. Yalnız kopyala + yükle; hesap yapmaz.
# Gerekli ortam değişkenleri (/etc/1l3a-pano.env, chmod 600; asla repoya girmez): CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID.
# İsteğe bağlı: PANO_AD (varsayılan 1l3a-pano) -> https://<PANO_AD>.<hesap-alt-alanı>.workers.dev
set -euo pipefail
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN tanımlı değil (/etc/1l3a-pano.env)}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID tanımlı değil (/etc/1l3a-pano.env)}"
kaynak="${PANO_DOSYA:-/var/lib/1l3a-paper/durum/pano.html}"
[ -s "$kaynak" ] || { echo "HATA: $kaynak yok ya da boş (1l3a-pano.timer çalışıyor mu?)" >&2; exit 1; }
gecici="$(mktemp -d)"
trap 'rm -rf "$gecici"' EXIT
mkdir "$gecici/site"
cp "$kaynak" "$gecici/site/index.html"
cd "$gecici"
WRANGLER_SEND_METRICS=false timeout -k 10 180 wrangler deploy --assets=site --name "${PANO_AD:-1l3a-pano}" \
  --compatibility-date=2026-11-01
echo "pano yayımlandı: $(date -u +%FT%TZ)"
