import json, re, time, html
from pathlib import Path
from urllib.request import Request, urlopen

pasta = Path.home() / 'Downloads' / 'bb-importador-teste'
dados = json.loads((pasta / 'bb-catalogo-validacao.json').read_text(encoding='utf-8'))
imoveis = dados['imoveis']
indices = [round(i * (len(imoveis) - 1) / 9) for i in range(10)]
saida = pasta / 'detalhes-amostra'
saida.mkdir(exist_ok=True)
resultados = []

for indice in indices:
    item = imoveis[indice]
    codigo = item['source_external_id']
    url = item['link_acesso']
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=30) as resp:
            bruto = resp.read()
            charset = resp.headers.get_content_charset() or 'utf-8'
            pagina = bruto.decode(charset, errors='replace')
            status = resp.status
        (saida / f'{codigo}.html').write_text(pagina, encoding='utf-8')
        links = re.findall(r'href=[\'\"]([^\'\"]+)[\'\"]', pagina, re.I)
        pdfs = [html.unescape(x) for x in links if '.pdf' in x.lower()]
        imagens = list(dict.fromkeys(re.findall(r'/imagem/imovel/[^\'\"\s<>]+', pagina, re.I)))
        resultado = {'id': codigo, 'url': url, 'http': status, 'html_bytes': len(bruto), 'imagens_encontradas': len(imagens), 'links_pdf': pdfs[:10], 'erro': None}
        print(f"ID {codigo}: HTTP {status}, {len(bruto)} bytes, {len(imagens)} imagens, {len(pdfs)} PDFs")
    except Exception as exc:
        resultado = {'id': codigo, 'url': url, 'erro': str(exc)}
        print(f'ID {codigo}: ERRO {exc}')
    resultados.append(resultado)
    time.sleep(1)

arquivo = saida / 'resultado-amostra.json'
arquivo.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nResultado salvo em:', arquivo)
