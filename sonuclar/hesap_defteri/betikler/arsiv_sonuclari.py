"""Arsiv TV sonuc kimlikleri; yalniz mevcut raporlar, yeni kosu yok."""
import json
from envanter import ROOT,OUT,write

def main():
    rows=[]
    for p in sorted((ROOT/'arsiv/strateji-sg').glob('*/sonuclar/*.json')):
        r=json.loads(p.read_text())
        if 'pine_id' not in r:continue
        rows.append(dict(dosya=p.relative_to(ROOT).as_posix(),ad=r['ad'],pine_id=r['pine_id'],tf=r['tf'],evren=json.dumps(r['evren'],ensure_ascii=False),gecti=r['gecti'],neden=r['neden'],olcut=json.dumps(r['olcut'],ensure_ascii=False),asama='onceki_proje_arsivi; 1L3A gecti anlami tasimaz'))
    assert len(rows)==135
    write('ara/P3_arsiv_tv_sonuclari.csv',rows,list(rows[0]))
    print('Arsiv TV sonuc:',len(rows))
if __name__=='__main__':main()
