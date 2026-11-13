"""Markdown kaynaklarindaki strateji baslik/tablo/kimlik atiflarini indeksler.
Bu otomatik aday bulma adimidir; mantiksal eslesme/akibet karari DEGILDIR.
"""
import csv,hashlib,re
from envanter import ROOT,OUT,write

ID=re.compile(r'(?<![\w/])(?:dis|swing|daytrade|scalp|onceki|pf|v3|ornek)__[\w-]+')
def main():
    inv=list(csv.DictReader((OUT/'kaynaklar.csv').open())); rows=[]; docs=[]
    for x in inv:
        rel=x['dosya'];p=ROOT/rel
        if p.suffix not in ('.md','.txt') or not p.is_file() or p.is_symlink():continue
        lines=p.read_text(encoding='utf-8-sig').splitlines(); count=0; table=None; table_sep=False
        for i,line in enumerate(lines,1):
            ids=sorted(set(ID.findall(line)))
            for sid in ids:
                count+=1;rows.append(dict(dosya=rel,satir=i,tur='kimlik_atfi',ad=sid,kimlik=sid,durum='mantik_kontrolu_bekliyor'))
            if line.startswith('|'):
                cells=[c.strip().strip('`* ') for c in line.strip().strip('|').split('|')]
                if cells and all(re.fullmatch(r':?-+:?',c.replace(' ','')) for c in cells):table_sep=True;continue
                if not table_sep:
                    table=cells;continue
                target=next((j for j,c in enumerate(table or []) if c.casefold().startswith(('strateji','strategy')) or c.casefold() in ('ad','aday','aile')),None)
                if target is not None and target<len(cells) and cells[target]:
                    count+=1;rows.append(dict(dosya=rel,satir=i,tur='tablo_adayi',ad=cells[target],kimlik='',durum='strateji_mi_ve_eslesme_kontrolu_bekliyor'))
            else:table=None;table_sep=False
            m=re.match(r'^#{2,6}\s+(?:\d+[.)]\s+|(?:[A-Z]\d|S\d|T\d|E\d)\b)(.*)',line)
            if m:
                count+=1;rows.append(dict(dosya=rel,satir=i,tur='numarali_baslik_adayi',ad=line.lstrip('# ').strip(),kimlik='',durum='strateji_mi_ve_eslesme_kontrolu_bekliyor'))
        docs.append(dict(dosya=rel,fiziksel_satir=len(lines),bulunan_atif=count,kapsam='tum satirlar otomatik tarandi; anlamsal tam okuma tamamlanmadi'))
    write('ara/belge_atiflari.csv',rows,list(rows[0]));write('ara/belge_tarama_kapsami.csv',docs,list(docs[0]));print('belge',len(docs),'atif',len(rows))
if __name__=='__main__':main()
