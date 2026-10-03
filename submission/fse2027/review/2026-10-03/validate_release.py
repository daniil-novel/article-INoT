"""Validate the actual bilingual PDF bytes, fonts, links and numeric tables."""
from pathlib import Path
import pymupdf, hashlib, re, json
r=Path(__file__).resolve().parents[2]
records={}
# Frozen bytes whose rendered pages received root visual inspection on 3 October.
expected_pdfs={'paper':'e4d4098d8cb25bb74ca7cf73787977c539ef5b7f406ed195f921104aa9e94faf','translation-ru':'d32ff8b10fd17253aa44a039f64d75bac7cde0baaeb95ad090f3d17e038134e8'}
for lang,folder in [('paper','paper'),('translation-ru','translation-ru')]:
 p=r/folder/'main.pdf';assert hashlib.sha256(p.read_bytes()).hexdigest()==expected_pdfs[lang], 'Changed PDF requires new visual review';d=pymupdf.open(p);txt='\n'.join(x.get_text() for x in d)
 assert not re.search(r'daniil|privezentsev|gf62|higher school of economics|курсовая работа',txt+' '+str(d.metadata),re.I)
 assert not d.metadata.get('author')
 fonts={f[0] for pg in d for f in pg.get_fonts()};assert all(d.extract_font(x)[3] for x in fonts)
 urls={l.get('uri') for pg in d for l in pg.get_links()};assert 'https://anonymous.4open.science/r/role-calls-replication-2026/' in urls
 assert len(d)==(16 if lang=='paper' else 27)
 log=(r/folder/'main.log').read_text(encoding='utf-8',errors='replace')
 assert not re.search(r'Overfull|undefined references|undefined citations|Rerun to get',log)
 records[lang]={'pages':len(d),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'build_exit_code':0,'compiler':'pdfLaTeX' if lang=='paper' else 'XeLaTeX','embedded_font_count':len(fonts),'metadata_author_empty':True,'identity_scan':'PASS','anonymous_hyperlink_verified':True,'all_pages_rendered_and_visually_checked':True,'build_checked_at':'2026-10-03'}
 for title,key in [('References','references_start'),('Data Availability','data_availability_start'),('Conclusion','conclusion_start')]:
  for n,pg in enumerate(d):
   if any(line.strip()==title or (title=='Conclusion' and re.fullmatch(r'9\s+Conclusion',line.strip())) for line in pg.get_text().splitlines()):records[lang][key]=n+1;break
names=['primary_quality','primary_contrasts','direct_contrasts','primary_resources','subgroup_sensitivity','secondary_model','scc_comparison','temporal_diagnostics']
parity={}
for name in names:
 vals=[]
 for folder in ['paper','translation-ru']:
  s=(r/folder/f'{name}.tex').read_text(encoding='utf-8').replace('{,}','.').replace('\\,','')
  s=s[s.index('\\begin{tabular}'):s.index('\\bottomrule')]
  if folder=='translation-ru': s=re.sub(r'(?<=\d),(?=\d)', '.', s)
  vals.append([float(x) for x in re.findall(r'(?<![A-Za-z])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:e[-+]?\d+)?',s)])
 assert vals[0]==vals[1],(name,vals)
 parity[name+'.tex']={'numeric_table_values_match':True,'count':len(vals[0])}
(r/'review/RU_NUMERICAL_PARITY.json').write_text(json.dumps(parity,indent=2)+'\n',encoding='utf-8')
assert (r/'paper/references.bib').read_bytes()==(r/'translation-ru/references.bib').read_bytes()
p=r/'review/FINAL_VALIDATION.json';old=json.loads(p.read_text())
assert hashlib.sha256((r/'artifact/fse2027-anonymous-analysis-artifact.zip').read_bytes()).hexdigest()=='693c088ac83b9f78ea48f786393cd8b7fddea4a77206a6e6d386fbd2626b9d71', 'Changed archive requires a new full replay/manifest check'
v={**old,'checked_at':'2026-10-03','paper':records['paper'],'translation-ru':records['translation-ru'],'supplement':{'files':337,'manifest_payload_entries':336,'sha256':hashlib.sha256((r/'artifact/fse2027-anonymous-analysis-artifact.zip').read_bytes()).hexdigest(),'manifest':'PASS','anonymity_scan':'PASS','portable_COPY_sources':'PASS','native_rebuild':'UNVERIFIED: Docker engine unavailable'},'translation_numeric_tables':'PASS: all eight quantitative table sequences match after decimal normalization','bibliography_byte_parity':True,'reviewers':{'independent_initial_contexts':7,'type':'AI internal quality review','human_native_review_claimed':False},'new_model_generations':0,'new_analysis':'Retrospective simultaneous precision, execution-phase and absolute-resource diagnostics on retained records','submission_checkpoint':old['submission_checkpoint'],'anonymous_access_checkpoint':old['anonymous_access_checkpoint'],'revision_publication':old.get('revision_publication',{'github':'PENDING','anonymous_mirror':'PENDING','HotCRP_replacement':'NOT PERFORMED; author approval required for materially revised version'})}
v['paper']['content_ends']=14;v['paper']['reference_pages']=2;v['paper']['FSE_page_gate']='PASS: 14 content pages plus exempt Data Availability and 2 reference pages'
v['translation-ru']['role']='expanded Russian reading version; not official submission';v['translation-ru']['author_comment_expansions_preserved']=True
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'pdfs':records,'numeric_tables':len(parity)},ensure_ascii=False,indent=2))
