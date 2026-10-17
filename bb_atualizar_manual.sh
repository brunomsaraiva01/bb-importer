#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "ERRO: existem alteracoes locais pendentes."
  echo "Sincronize o repositorio antes de atualizar."
  exit 1
fi

echo "Verificando sincronizacao com GitHub..."
git fetch origin main
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  echo "ATENCAO: repositorio local diferente do GitHub."
  echo "Atualize o repositorio antes de continuar."
  exit 1
fi

echo "1/4 - Descobrindo imoveis..."
.venv/bin/python bb_descobrir_catalogo.py

echo "2/4 - Coletando dados e fotos..."
rm -rf bb-coleta-temporaria
.venv/bin/python bb_coletar_catalogo.py \
  --catalogo bb-catalogo-atualizado.json \
  --limite 0 \
  --pausa 2 \
  --saida bb-coleta-temporaria

echo "3/4 - Validando coleta..."
.venv/bin/python bb_validar_publicacao.py

echo "4/4 - Coleta aprovada."
echo "Pronto para publicar no GitHub."

echo "Publicando catalogo validado..."

# Preparar todos os novos arquivos antes de substituir os anteriores
test -s bb-coleta-temporaria/auditoria.json
test -n "$(find bb-coleta-temporaria/por-uf -name '*.json' -print -quit)"

commit_anterior=$(git rev-parse HEAD)
publicado=false

restaurar() {
  if [ "$publicado" = false ]; then
    echo "Falha na publicacao. Recuperando versao anterior..."
    git reset --hard "$commit_anterior"
  fi
}
trap restaurar ERR

mkdir -p bb-coleta/por-uf
rm -f bb-coleta/por-uf/*.json
cp bb-coleta-temporaria/por-uf/*.json bb-coleta/por-uf/
cp bb-coleta-temporaria/auditoria.json bb-coleta/auditoria.json
cp bb-catalogo-atualizado.json bb-catalogo-validacao.json

date -u +"%Y-%m-%dT%H:%M:%S+00:00" > .bb-ultima-atualizacao.txt

git add -A -- bb-coleta/por-uf/
git add -- bb-catalogo-atualizado.json bb-catalogo-validacao.json
git add -- .bb-ultima-atualizacao.txt
git add -f -- bb-coleta/auditoria.json

if git diff --cached --quiet; then
  echo "Nenhuma alteracao para publicar."
  exit 0
fi

git commit -m "Atualizacao manual do catalogo BB"
git push origin HEAD:main
publicado=true
trap - ERR

echo "ATUALIZACAO BB CONCLUIDA COM SUCESSO!"
