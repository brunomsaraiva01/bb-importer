import json
from pathlib import Path

base = Path('bb-coleta-temporaria')
auditoria = json.loads((base / 'auditoria.json').read_text())
total = auditoria['ids_unicos_catalogo']
extraidos = auditoria['extraidos']
fotos = auditoria['com_foto']
precos = auditoria['com_preco']

def exigir(condicao, mensagem):
    if not condicao:
        raise SystemExit('VALIDACAO REPROVADA: ' + mensagem)

exigir(total > 0, 'Catalogo vazio')
exigir(extraidos >= total * 0.95, 'Menos de 95% dos imoveis extraidos')
exigir(fotos >= extraidos * 0.95, 'Cobertura de fotos insuficiente')
exigir(precos >= extraidos * 0.90, 'Cobertura de precos insuficiente')

arquivos = list((base / 'por-uf').glob('*.json'))
exigir(len(arquivos) >= 20, 'Quantidade insuficiente de estados')

soma = 0
ids = set()

for arquivo in arquivos:
    dados = json.loads(arquivo.read_text(encoding='utf-8'))
    for imovel in dados['imoveis']:
        codigo = str(imovel['source_external_id'])
        exigir(codigo not in ids, f'Imovel duplicado: {codigo}')
        ids.add(codigo)
        soma += 1

exigir(soma == extraidos, 'Divergencia entre JSONs e auditoria')

print(f'VALIDACAO APROVADA: {extraidos}/{total} imoveis')
print(f'Fotos: {fotos} | Precos: {precos}')
print(f'Estados: {len(arquivos)} | IDs unicos: {len(ids)}')
