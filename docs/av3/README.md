# AV3 — Roteiro técnico para auditoria e entrega

## Fonte, estado e separação de evidências

A base desta revisão é uma cópia ZIP do repositório (`projetoAplicado3-main`), sem metadados `.git`. As alterações desta branch foram implementadas por Samuel Silva de Rezende, cada uma em um commit separado, e aguardam revisão da equipe por Pull Request (sem merge automático). O histórico anterior do repositório (commits, PRs, branches) será consultado no GitHub e registrado nesta trilha.

O Plano de Trabalho AV1 previu quatro integrantes; atualmente a equipe é composta por três: Samuel Silva de Rezende (Product Owner), Vinícius Joacir dos Anjos (desenvolvimento/IA) e Guilherme da Silva Anselmo (QA, integridade, segurança, design e frontend). A contribuição individual de cada integrante será registrada a partir do histórico do GitHub.

## Pipeline e desenhos

```text
INEP (2019 a 2022; ZIP/CSV; dicionário)
    | hashes.sha256 / profiling / contrato
    v
RAW local preservado
    | scripts/etl.py -> seleção de campos, tipagem, elegibilidade
    v
TRUSTED: data/trusted/enem/ano=AAAA/data_0.parquet (ZSTD)
    | DuckDB SELECT/GROUP BY/ORDER BY
    +---> dist_notas.parquet: faixas protegidas (visualização)
    +---> dist_exata.parquet: CDF exata (somente backend)
    +---> _manifesto_analytics.json: tamanhos, hashes, totais
                 |
                 v
      app/app.py: percentil por posto médio e histograma
```

## Critérios da AV3 e evidências

1. Arquitetura: RAW/TRUSTED/ANALYTICS, fluxo offline vs aplicação em tempo de consulta; descrever que não existe *streaming*.
2. ETL e código: `scripts/etl.py`, `scripts/colunas.py`, `scripts/estatistica.py`, `scripts/contrato.py`; documentar transformações e regras de elegibilidade.
3. Requisitos: registrar RF/RNF com status: entregue, parcial ou planejado, evitando tratar o escopo AV4 como implementado.
4. Volumetria: `docs/profiling/profiling_*.json` e `docs/stack/benchmark.json` são medidas existentes; **não** confundir Parquet de 58 colunas do benchmark com TRUSTED efetiva, que tem derivados e elegibilidade.
5. Rastreabilidade: link da branch `engineering` apenas após confirmação remota; diferenciar atribuições de papel da autoria real.
6. Documento: Word editável para revisão interna; exportação PDF com template exigido pelo AVA.

## Checklist de aceitação pendente

- [ ] Confirmar os três integrantes ativos com a equipe e autorias por commit.
- [ ] Obter acesso GitHub e criar PR rastreável, sem dar merge automático.
- [x] Executar todos os testes com dependências do projeto (25 testes OK em 13/10/2026; ver *Evidências de execução*).
- [ ] Executar ETL sobre todas as edições oficiais e arquivar hashes/manifests e logs.
- [x] Verificar exatidão contra contagem direta em DuckDB com notas controladas (sintético; o ETL também compara a CDF com o DuckDB a cada execução).
- [ ] Repetir essa verificação sobre os microdados reais do INEP (as quatro edições).
- [ ] Validar que nenhum artefato interno fica disponível via URL pública.
- [ ] Consolidar o diagrama e copiar volumetria real para o relatório.
- [ ] Confirmar rubrica somando 120% e formato final da entrega com docente.

## Testes e limites

O teste puro `tests/test_percentil_exato.py` não necessita DuckDB. Os testes legados exigem `duckdb` e alguns exigem `streamlit`. As verificações integrais e o deploy não podem ser marcados como aprovados apenas pela compilação dos módulos Python.

## Evidências de execução (13/10/2026)

Ambiente: Python 3.13, `duckdb==1.5.5`, `streamlit==1.64.0`, `plotly==7.1.0` (as versões de `requirements.txt`), venv limpo.

| Verificação | Resultado |
|---|---|
| `python -m compileall -q scripts app tests` | OK |
| `python -m unittest discover -s tests` | **25 testes OK** (13 do projeto original, 4 de `test_percentil_exato.py`, 8 de `test_analytics.py`) |
| `python scripts/verificar_piso.py` | OK: nenhuma contagem abaixo do piso de 100 em `docs/` |
| Verificação por mutação (empate contado inteiro; nota não observada tratada como empate) | Os testes novos **falham** quando o cálculo é quebrado, e o próprio ETL aborta a publicação |

`tests/test_analytics.py` executa RAW sintético → TRUSTED → ANALYTICS com as funções reais do ETL e compara a CDF publicada com um cálculo independente em Python puro.

**O que continua não comprovado:** nenhuma execução sobre os microdados reais do INEP. Os números de volumetria dos artefatos novos (`dist_exata.parquet`, `_manifesto_analytics.json`) só existirão após rodar `scripts/etl.py` com os CSVs em `data/raw/`. Os 17.744.217 registros / 7,51 GB / 356,55 MB / 95,25% citados no relatório vêm de `docs/profiling/` e `docs/stack/benchmark.json` (benchmark), não deste ETL.
