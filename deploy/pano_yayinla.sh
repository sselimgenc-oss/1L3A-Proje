#!/usr/bin/env bash
# Sunucudaki pano.html'i Cloudflare Workers'a yayımlar; pano bir Worker'ın ARKASINDADIR (Basic Auth, kullanıcı "1l3a").
# Gerekli ortam değişkenleri (/etc/1l3a-pano.env, chmod 600; asla repoya girmez):
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, PANO_SIFRE (en az 16 karakter; yoksa betik HATA verir, yayımlamaz).
# İsteğe bağlı: PANO_AD (varsayılan 1l3a-pano) -> https://<PANO_AD>.<hesap-alt-alanı>.workers.dev
# Şifre Worker secret'ı olarak stdin'den verilir; yalnız ilk kez / değiştiğinde (sha256'sı 600 izinli dosyada tutulur).
# Kullanıcı kararı (2026-11-14): PANO_KILITSIZ=1 ise pano ŞİFRESİZ yayımlanır (yalnız statik sayfa; Worker kilidi yok).
#   Bu açık bir tercihtir: tanımlı değilse eski davranış (şifre zorunlu, fail-closed) aynen geçerli.
set -euo pipefail
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN tanımlı değil (/etc/1l3a-pano.env)}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID tanımlı değil (/etc/1l3a-pano.env)}"
kilitsiz=0
[ "${PANO_KILITSIZ:-0}" = "1" ] && kilitsiz=1
if [ "$kilitsiz" = 0 ]; then
  : "${PANO_SIFRE:?PANO_SIFRE tanımlı değil (/etc/1l3a-pano.env); şifresiz pano yayımlanmaz (şifresiz istenirse PANO_KILITSIZ=1)}"
  [ "${#PANO_SIFRE}" -ge 16 ] || { echo "HATA: PANO_SIFRE en az 16 karakter olmalı" >&2; exit 1; }
fi
ad="${PANO_AD:-1l3a-pano}"
kaynak="${PANO_DOSYA:-/var/lib/1l3a-paper/durum/pano.html}"
[ -s "$kaynak" ] || { echo "HATA: $kaynak yok ya da boş (1l3a-pano.timer çalışıyor mu?)" >&2; exit 1; }
hash_dosya="${PANO_SIFRE_HASH_DOSYA:-/var/lib/1l3a-paper/yayin-ev/pano_sifre.sha256}"
betik_dizin="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
gecici="$(mktemp -d)"
trap 'rm -rf "$gecici"' EXIT
mkdir "$gecici/site"
cp "$kaynak" "$gecici/site/index.html"
cd "$gecici"
export WRANGLER_SEND_METRICS=false
if [ "$kilitsiz" = 1 ]; then
  # şifresiz: yalnız statik sayfa; önbelleğe alınmasın, arama motoru dizinlemesin
  printf '/*\n  Cache-Control: private, no-store\n  X-Robots-Tag: noindex\n' > "$gecici/site/_headers"
  cat > "$gecici/wrangler.jsonc" <<JSON
{
  "name": "$ad",
  "compatibility_date": "2026-11-01",
  "workers_dev": true,
  "assets": { "directory": "site" }
}
JSON
  timeout -k 10 180 wrangler deploy --config wrangler.jsonc
  echo "pano yayımlandı (ŞİFRESİZ, PANO_KILITSIZ=1): $(date -u +%FT%TZ)"
  exit 0
fi
cp "$betik_dizin/pano_worker.js" "$gecici/pano_worker.js"
cat > "$gecici/wrangler.jsonc" <<JSON
{
  "name": "$ad",
  "main": "pano_worker.js",
  "compatibility_date": "2026-11-01",
  "workers_dev": true,
  "assets": { "directory": "site", "binding": "ASSETS", "run_worker_first": true }
}
JSON
timeout -k 10 180 wrangler deploy --config wrangler.jsonc
yeni_hash="$(printf '%s' "$PANO_SIFRE" | sha256sum | cut -d' ' -f1)"
eski_hash="$(cat "$hash_dosya" 2>/dev/null || true)"
if [ "$yeni_hash" != "$eski_hash" ]; then
  # secret stdin'den gider: komut satırında ve logda görünmez
  printf '%s' "$PANO_SIFRE" | timeout -k 10 120 wrangler secret put PANO_SIFRE --name "$ad"
  mkdir -p "$(dirname "$hash_dosya")"
  ( umask 077; printf '%s\n' "$yeni_hash" > "$hash_dosya" )
  chmod 600 "$hash_dosya"
  echo "PANO_SIFRE secret'ı güncellendi"
fi
echo "pano yayımlandı: $(date -u +%FT%TZ)"
