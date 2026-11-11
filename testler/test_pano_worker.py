"""B18: pano Worker kilidi (node ile) ve pano_yayinla.sh şifre zorunluluğu."""
import base64
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
WORKER = KOK / "deploy" / "pano_worker.js"
BETIK = KOK / "deploy" / "pano_yayinla.sh"

NODE_KOD = r"""
import { pathToFileURL } from "node:url";
const w = (await import(pathToFileURL(process.argv[1]).href)).default;
const b = (k, s) => "Basic " + Buffer.from(k + ":" + s).toString("base64");
const env = (sifre) => ({ PANO_SIFRE: sifre, ASSETS: { fetch: async () => new Response("<html>pano</html>", { status: 200 }) } });
async function dene(e, auth) {
  const h = auth ? { Authorization: auth } : {};
  const r = await w.fetch(new Request("https://x.test/", { headers: h }), e);
  return { durum: r.status, cache: r.headers.get("Cache-Control"), robots: r.headers.get("X-Robots-Tag"),
           www: r.headers.get("WWW-Authenticate"), govde: await r.text() };
}
const S = "dogru-sifre-0123456789";
console.log(JSON.stringify({
  dogru: await dene(env(S), b("1l3a", S)),
  yanlis: await dene(env(S), b("1l3a", "yanlis")),
  yanlis_kullanici: await dene(env(S), b("biri", S)),
  baslik_yok: await dene(env(S), null),
  bozuk: await dene(env(S), "Basic !!!"),
  secret_yok: await dene(env(undefined), b("1l3a", "")),
  secret_bos: await dene(env(""), b("1l3a", "")),
}));
"""


@pytest.fixture(scope="module")
def sonuc():
    if not shutil.which("node"):
        pytest.skip("node yok")
    r = subprocess.run(["node", "--input-type=module", "-e", NODE_KOD, str(WORKER)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_dogru_sifre_200(sonuc):
    assert sonuc["dogru"]["durum"] == 200 and "pano" in sonuc["dogru"]["govde"]


@pytest.mark.parametrize("k", ["yanlis", "yanlis_kullanici", "baslik_yok", "bozuk", "secret_yok", "secret_bos"])
def test_reddedilenler_401(sonuc, k):
    assert sonuc[k]["durum"] == 401
    assert "Basic" in sonuc[k]["www"]
    assert "pano" not in sonuc[k]["govde"]


def test_basliklar(sonuc):
    for k in ("dogru", "yanlis", "secret_yok"):
        assert sonuc[k]["cache"] == "private, no-store"
        assert sonuc[k]["robots"] == "noindex"


def _sahte_wrangler(tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    log = tmp_path / "cagrilar.log"
    w = bin_ / "wrangler"
    w.write_text(f'#!/usr/bin/env bash\necho "$@" >> {log}\nif [ "$1 $2" = "secret put" ]; then cat > {tmp_path}/stdin.txt; fi\n')
    w.chmod(w.stat().st_mode | stat.S_IXUSR)
    return bin_, log


def _calistir(tmp_path, **ek):
    bin_, log = _sahte_wrangler(tmp_path)
    pano = tmp_path / "pano.html"
    pano.write_text("<html></html>")
    env = {"PATH": f"{bin_}:{os.environ['PATH']}", "CLOUDFLARE_API_TOKEN": "t", "CLOUDFLARE_ACCOUNT_ID": "a",
           "PANO_DOSYA": str(pano), "PANO_SIFRE_HASH_DOSYA": str(tmp_path / "h" / "sifre.sha256")}
    env.update(ek)
    r = subprocess.run(["bash", str(BETIK)], env=env, capture_output=True, text=True, timeout=60)
    return r, log


def test_betik_sifre_yoksa_hata(tmp_path):
    r, log = _calistir(tmp_path)
    assert r.returncode != 0 and "PANO_SIFRE" in r.stderr
    assert not log.exists()          # wrangler hiç çağrılmadı


def test_betik_kisa_sifre_hata(tmp_path):
    r, log = _calistir(tmp_path, PANO_SIFRE="kisa")
    assert r.returncode != 0 and not log.exists()


def test_betik_secret_yalniz_degisince(tmp_path):
    s = "x" * 20
    r, log = _calistir(tmp_path, PANO_SIFRE=s)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "stdin.txt").read_text() == s
    assert s not in log.read_text()                       # komut satırında görünmez
    assert (tmp_path / "h" / "sifre.sha256").stat().st_mode & 0o777 == 0o600
    log.unlink()
    r, log = _calistir(tmp_path, PANO_SIFRE=s)           # ikinci yayın: secret put yok
    assert r.returncode == 0 and "secret put" not in log.read_text() and "deploy" in log.read_text()
