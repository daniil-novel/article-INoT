import hashlib,json
from pathlib import Path
import fitz
from PIL import Image,ImageDraw
root=Path.cwd()
out=root/'submission/fse2027/review/2026-10-03/inspection-final'
out.mkdir(exist_ok=True)
records={}
for lang,rel in {'en':'submission/fse2027/paper/main.pdf','ru':'submission/fse2027/translation-ru/main.pdf'}.items():
 p=root/rel
 doc=fitz.open(p)
 records[lang]={'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pages':len(doc),'metadata':doc.metadata,'page_text_lengths':[len(x.get_text()) for x in doc]}
 (out/f'{lang}-all-pages.txt').write_text('\n'.join(f'\n=== PAGE {n+1} ===\n{page.get_text()}' for n,page in enumerate(doc)),encoding='utf-8')
 thumbs=[]
 for n,page in enumerate(doc):
  pix=page.get_pixmap(matrix=fitz.Matrix(0.9,0.9),alpha=False)
  img=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
  img.save(out/f'{lang}-page-{n+1:02d}.png')
  img.thumbnail((300,410))
  tile=Image.new('RGB',(320,440),'#ddd');tile.paste(img,((320-img.width)//2,10))
  ImageDraw.Draw(tile).text((10,423),f'{lang.upper()} page {n+1}',fill='black');thumbs.append(tile)
 for start in range(0,len(thumbs),12):
  tiles=thumbs[start:start+12];sheet=Image.new('RGB',(1280,((len(tiles)+3)//4)*440),'white')
  for i,tile in enumerate(tiles): sheet.paste(tile,((i%4)*320,(i//4)*440))
  sheet.save(out/f'{lang}-sheet-{start//12+1}.png')
(out/'final-pdfs.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(records,ensure_ascii=False,indent=2))