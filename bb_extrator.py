#!/usr/bin/env python3
"""Extrai dados do imóvel principal de páginas HTML do Seu Imóvel BB.
Uso: python3 bb_extrator.py 10020.html 12226.html -o bb-amostra-extraida.json
Dependência: pip install beautifulsoup4
"""
import argparse, json, re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE='https://www.seuimovelbb.com.br'

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def match(pattern, text, flags=re.I):
    m=re.search(pattern, text, flags)
    return clean(m.group(1)) if m else None

def parse(path):
    path=Path(path)
    html=path.read_text(encoding='utf-8')
    soup=BeautifulSoup(html,'html.parser')
    ident=path.stem
    if not ident.isdigit():
        ident=match(r'/imovel/id/(\d+)',html)
    if not ident:
        raise ValueError(f'ID não identificado: {path}')
    root=soup.select_one('.box-content')
    if not root:
        raise ValueError(f'Conteúdo principal não identificado: {path}')
    # Excluir imóveis relacionados antes de analisar o imóvel principal.
    related=root.select_one('.box-similar-highlights')
    if related: related.decompose()
    crumbs=root.select('.breadcrumb-item')
    uf=clean(crumbs[-2].get_text(' ',strip=True)) if len(crumbs)>=3 else None
    city=clean(crumbs[-1].get_text(' ',strip=True)) if len(crumbs)>=3 else None
    price_el=root.select_one('.valor .numero')
    price_label=root.select_one('.valor .titulo')
    price_text=clean(price_el.get_text(' ',strip=True)) if price_el else None
    price=None
    if price_text and re.fullmatch(r'R\$\s*[\d.]+,\d{2}',price_text):
        price=float(price_text.replace('R$','').replace('.','').replace(',','.').strip())
    description=None
    observations=[]
    auction_date_raw=None
    box=root.select_one('.box-description')
    if box:
        h4s=box.select('h4')
        for h in h4s:
            heading=clean(h.get_text(' ',strip=True))
            if 'Data do leilão:' in heading:
                auction_date_raw=clean(heading.split('Data do leilão:',1)[1])
            if heading=='Descrição':
                sibling=h.find_next_sibling('div')
                if sibling: description=clean(sibling.get_text(' ',strip=True))
            if heading=='Observações':
                for sibling in h.find_next_siblings('div'):
                    observations.append(clean(sibling.get_text(' ',strip=True)))
    gallery=soup.select('.box-images .slick-images a[data-fancybox]')
    images=list(dict.fromkeys(urljoin(BASE,a.get('href')) for a in gallery if a.get('href') and re.search(r'/imagem/imovel/'+re.escape(ident)+r'_',a.get('href'))))
    partner_link=None
    for a in root.select('a[onclick]'):
        onclick=a.get('onclick','')
        if '_redirecionar(' in onclick:
            partner_link=match(r'_redirecionar\([\'\"](https?://[^\'\"]+)',onclick)
            break
    text=description or ''
    registry=match(r'matr[ií]cula\s*(?:n[ºo.]\s*)?([\d.]+)',text)
    registry_office=match(r'matr[ií]cula\s*(?:n[ºo.]\s*)?[\d.]+\s+(?:do|da)\s+([^.;]+)',text)
    occupied=bool(re.search(r'encontra-se ocupado por terceiros',text,re.I))
    occupancy='ocupado_por_terceiros' if occupied else None
    external_reference=match(r'\bID\s*(\d+)',text)
    address=match(r'(?:situad[oa]\s+(?:na|no|à|ao)\s+)(.*?)(?:,\s*Munic[ií]pio|\.\s*Melhor descrito)',text)
    sale_modality='aceita_bb' if price_text and 'Aceita BB' in price_text else None
    if not sale_modality and price_label:
        label=clean(price_label.get_text(' ',strip=True)).lower()
        if 'valor para proposta' in label: sale_modality='proposta'
    # Tarjas ocultas não são indicadores confiáveis de modalidade.
    latitude=longitude=None
    coords=re.search(r'path\s*=\s*\{\s*lat:\s*(-?\d+(?:\.\d+)?),\s*lng:\s*(-?\d+(?:\.\d+)?)',html)
    if coords:
        latitude=float(coords.group(1)); longitude=float(coords.group(2))
    return {
      'source_type':'bb','source_external_id':ident,
      'source_url':f'{BASE}/imovel/id/{ident}',
      'external_reference':external_reference,'city':city,'state':uf,
      'address':address,'asking_price':price,'price_display':price_text,
      'sale_modality_hint':sale_modality,'auction_date_raw':auction_date_raw,
      'description':description,'observations':observations,
      'occupancy_status':occupancy,
      'registry_number':registry,'registry_office':registry_office,
      'partner_url':partner_link,'images':images,
      'latitude':latitude,'longitude':longitude,
      'documents':{'edital_url':None,'matricula_url':None},
      'notes':'Dados extraídos de HTML público; confirmar edital e condições no parceiro vendedor.'
    }

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('html',nargs='+')
    parser.add_argument('-o','--output',default='bb-amostra-extraida.json')
    args=parser.parse_args()
    rows=[parse(p) for p in args.html]
    Path(args.output).write_text(json.dumps({'imoveis':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(rows)} imóveis extraídos -> {args.output}')
    for row in rows:
        print(row['source_external_id'],row['city'],row['state'],row['asking_price'],row['occupancy_status'],len(row['images']))
