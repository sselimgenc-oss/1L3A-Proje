"""Aşama 1: linklerden Pine kaynağını çek (tv/pine/<id>.pine) ve tv/ham/meta.json yaz."""
import re, json, sys, subprocess, concurrent.futures as cf, urllib.parse, pathlib
K = pathlib.Path(__file__).parent
UA = "Mozilla/5.0"
def curl(url):
    r = subprocess.run(["curl","-sSL","-m","40","-A",UA,url],capture_output=True)
    return r.stdout.decode("utf8","replace")
def isle(link):
    link = link.strip()
    m = re.search(r"/script/([A-Za-z0-9]{8})", link)
    sid = m.group(1)
    page = curl(f"https://www.tradingview.com/script/{sid}/")
    pid = re.search(r'script_id_part":"(PUB;[^"]+)"', page)
    t = re.search(r"<title>([^<]*)", page)
    ad = t.group(1).rsplit(" — ",1)[0] if t else ""
    yazar = ""
    ym = re.search(r"by ([^ ]+)$", ad)
    if ym: yazar = ym.group(1)
    meta = dict(id=sid, link=link, ad=ad, yazar=yazar, pub=pid.group(1) if pid else None, kaynak=None, erisim="?", tur="?")
    if pid:
        js = curl("https://pine-facade.tradingview.com/pine-facade/get/"+urllib.parse.quote(pid.group(1))+"/last")
        try:
            d = json.loads(js)
            meta["kaynak"] = d.get("source"); meta["erisim"] = d.get("scriptAccess","?")
            meta["tur"] = d.get("extra",{}).get("kind","?")
            meta["ad"] = d.get("scriptName") or ad
        except Exception: meta["erisim"]="hata"
    return meta
if __name__ == "__main__":
    links = [l for l in open(K/"kaynak/linkler.txt").read().split() if l.startswith("http")]
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(isle, links))
    for m in res:
        if m["kaynak"]: (K/"pine"/f"{m['id']}.pine").write_text(m["kaynak"].replace("\r\n","\n"))
        m.pop("kaynak")
    json.dump(res, open(K/"ham/meta.json","w"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter((m["erisim"],m["tur"]) for m in res))
