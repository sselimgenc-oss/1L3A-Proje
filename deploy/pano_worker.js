// 1L3A pano kilidi (B18): tüm istekler önce buradan geçer; HTTP Basic Auth doğruysa statik pano döner.
// Kullanıcı adı sabit "1l3a"; şifre Worker secret'ı PANO_SIFRE. Secret yoksa HER İSTEK 401 (fail-closed).
const KULLANICI = "1l3a";

async function ozet(metin) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(metin)));
}

// Sabit zamanlı karşılaştırma: iki değerin SHA-256'sı (eşit uzunluk) bayt bayt XOR'lanır, erken çıkış yok.
async function esitMi(a, b) {
  const x = await ozet(a);
  const y = await ozet(b);
  let fark = 0;
  for (let i = 0; i < x.length; i++) fark |= x[i] ^ y[i];
  return fark === 0;
}

function baslikEkle(yanit) {
  const h = new Headers(yanit.headers);
  h.set("Cache-Control", "private, no-store");
  h.set("X-Robots-Tag", "noindex");
  return new Response(yanit.body, { status: yanit.status, statusText: yanit.statusText, headers: h });
}

function red() {
  return baslikEkle(new Response("Yetkisiz", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="1L3A pano", charset="UTF-8"' },
  }));
}

function bilgiCoz(baslik) {
  if (!baslik || !/^basic /i.test(baslik)) return null;
  try {
    const bin = atob(baslik.slice(6).trim());
    const metin = new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
    const i = metin.indexOf(":");
    if (i < 0) return null;
    return { kullanici: metin.slice(0, i), sifre: metin.slice(i + 1) };
  } catch (_) {
    return null;
  }
}

export default {
  async fetch(istek, env) {
    const sifre = env.PANO_SIFRE;
    if (typeof sifre !== "string" || sifre.length === 0) return red();
    const bilgi = bilgiCoz(istek.headers.get("Authorization"));
    if (!bilgi) return red();
    // iki karşılaştırma da her zaman yapılır (kullanıcı adı yanlışsa bile süre sızdırmasın)
    const kOk = await esitMi(bilgi.kullanici, KULLANICI);
    const sOk = await esitMi(bilgi.sifre, sifre);
    if (!(kOk && sOk)) return red();
    return baslikEkle(await env.ASSETS.fetch(istek));
  },
};
