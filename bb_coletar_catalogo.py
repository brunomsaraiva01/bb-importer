#!/usr/bin/env python3
"""Coleta BB com retomada, limites de taxa e auditoria; sem publicar dados."""
import argparse
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from bb_extrator_v1_1 import parse

parser = argparse.ArgumentParser(description='Coleta e valida detalhes de imóveis BB')
parser.add_argument('--catalogo', default='bb-catalogo-validacao.json')
parser.add_argument('--limite', type=int, default=20, help='Quantidade máxima por execução; use 0 para todos')
parser.add_argument('--pausa', type=float, default=2.0, help='Segundos mínimos entre solicitações')
parser.add_argument('--saida', default='bb-coleta')
args = parser.parse_args()
if args.pausa < 1: parser.error('Use --pausa de pelo menos 1 segundo')
base = Path(args.saida)
html_dir = base / 'html'
html_dir.mkdir(parents=True, exist_ok=True)
source = json.loads(Path(args.catalogo).read_text(encoding='utf-8'))
items = source.get('imoveis', [])
ids = set()
ordered = []
for item in items:
    ident = str(item['source_external_id'])
    url = item.get('link_acesso') or item.get('source_url')
    expected = f'https://www.seuimovelbb.com.br/imovel/id/{ident}'
    if not ident.isdigit() or url != expected:
        raise ValueError(f'ID/URL inesperados: {ident} {url}')
    if ident not in ids:
        ids.add(ident)
        ordered.append((ident, url))

new_downloads = 0
errors = {}
for ident, url in ordered:
    target = html_dir / f'{ident}.html'
    if target.exists() and target.stat().st_size > 10000:
        continue
    if args.limite and new_downloads >= args.limite:
        break
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; BRLeiloesCatalogValidation/1.0)'})
            with urllib.request.urlopen(request, timeout=40) as response:
                if response.status != 200: raise RuntimeError(f'HTTP {response.status}')
                raw = response.read()
                charset = response.headers.get_content_charset() or 'utf-8'
            content = raw.decode(charset, errors='replace')
            if len(raw) < 10000 or f'/imagem/imovel/{ident}_' not in content:
                raise ValueError('HTML incompleto ou sem referência ao imóvel esperado')
            temp = target.with_suffix('.tmp')
            temp.write_text(content, encoding='utf-8')
            temp.replace(target)
            new_downloads += 1
            print(f'OK {ident} ({len(raw)} bytes) | novos {new_downloads}', flush=True)
            break
        except Exception as exc:
            if attempt == 2:
                errors[ident] = str(exc)
                print(f'FALHA {ident}: {exc}', flush=True)
            else:
                time.sleep(3 * (attempt + 1))
        finally:
            time.sleep(args.pausa + random.uniform(0, 0.5))

rows = []
for ident, _ in ordered:
    target = html_dir / f'{ident}.html'
    if not target.exists():
        continue
    try:
        row = parse(target)
        if str(row.get('source_external_id')) != ident:
            raise ValueError('ID extraído diferente do esperado')
        rows.append(row)
    except Exception as exc:
        errors[ident] = f'Erro de parser: {exc}'

by_state = defaultdict(list)
for row in rows:
    uf = row.get('state')
    if isinstance(uf, str) and len(uf) == 2 and uf.isalpha():
        by_state[uf.upper()].append(row)
    else:
        by_state['SEM_UF'].append(row)

uf_dir = base / 'por-uf'
uf_dir.mkdir(exist_ok=True)
for stale in uf_dir.glob('*.json'):
    stale.unlink()
for uf, properties in sorted(by_state.items()):
    (uf_dir / f'{uf}.json').write_text(json.dumps({'imoveis': properties}, ensure_ascii=False, indent=2), encoding='utf-8')

report = {
    'gerado_em_utc': datetime.now(timezone.utc).isoformat(),
    'total_anunciado_no_catalogo': source.get('total_anunciado'),
    'ids_unicos_catalogo': len(ordered),
    'htmls_salvos': sum((html_dir / f'{ident}.html').exists() for ident, _ in ordered),
    'extraidos': len(rows),
    'por_uf': {uf: len(properties) for uf, properties in sorted(by_state.items())},
    'com_preco': sum(isinstance(r.get('asking_price'), (int, float)) for r in rows),
    'com_endereco': sum(bool(r.get('address')) for r in rows),
    'com_foto': sum(bool(r.get('images')) for r in rows),
    'com_matricula_numero': sum(bool(r.get('registry_number')) for r in rows),
    'com_parceiro': sum(bool(r.get('partner_url')) for r in rows),
    'erros': errors,
    'observacao': 'Arquivos por UF são preliminares, não homologados para importação no Lovable.'
}
(base / 'auditoria.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nAUDITORIA\n' + json.dumps(report, ensure_ascii=False, indent=2), flush=True)
