import json
import math
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://www.seuimovelbb.com.br/catalogo'
DESTINO = Path('bb-catalogo-atualizado.json')

def consultar(pagina):
    dados = {
        'pagina': str(pagina),
        'categorias': '',
        'tipoVenda': '',
        'tipoPagamento': '',
        'evolua': '',
        'localidade': '||',
        'minimo': '0',
        'maximo': '27000000',
        'texto': '',
        'ordem': '0',
        'contento': '0'
    }
    req = urllib.request.Request(
        URL,
        data=urllib.parse.urlencode(dados).encode(),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0'
        }
    )
    with urllib.request.urlopen(req, timeout=40) as resposta:
        return json.load(resposta)

primeira = consultar(1)
total = int(primeira['imoveis'])
paginas = math.ceil(total / 50)
ids = {}

print(f'Catálogo anunciado: {total} imóveis')
print(f'Páginas previstas: {paginas}', flush=True)

for pagina in range(1, paginas + 1):
    dados = primeira if pagina == 1 else consultar(pagina)
    encontrados = re.findall(r'/imovel/id/(\d+)', dados.get('lista', ''))
    unicos = list(dict.fromkeys(encontrados))

    if not unicos:
        raise RuntimeError(f'Página {pagina} sem imóveis. Atualização interrompida.')

    for codigo in unicos:
        ids[codigo] = {
            'source_external_id': codigo,
            'source_url': f'https://www.seuimovelbb.com.br/imovel/id/{codigo}',
            'link_acesso': f'https://www.seuimovelbb.com.br/imovel/id/{codigo}'
        }


    print(f'Página {pagina}/{paginas}: {len(unicos)} imóveis', flush=True)

if len(ids) != total:
    raise RuntimeError(
        f'Catalogo incompleto: anunciado={total}, encontrados={len(ids)}'
    )

resultado = {
    'total_anunciado': total,
    'imoveis': list(ids.values())
}

Path('bb-catalogo-atualizado.json').write_text(
    json.dumps(resultado, ensure_ascii=False, indent=2),
    encoding='utf-8'
)

print(f'CONCLUÍDO: {len(ids)} imóveis únicos encontrados', flush=True)
