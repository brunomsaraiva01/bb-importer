import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

marcador = Path('.bb-ultima-atualizacao.txt')
manual = os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch'
executar = manual or not marcador.exists()

if not executar:
    ultima = datetime.fromisoformat(marcador.read_text().strip())
    executar = datetime.now(timezone.utc) - ultima >= timedelta(days=15)

with open(os.environ['GITHUB_OUTPUT'], 'a') as saida:
    saida.write(f"run={'true' if executar else 'false'}\n")

print('Executar coleta:', executar)
