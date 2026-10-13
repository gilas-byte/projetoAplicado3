# AV3 — Roteiro técnico para auditoria e entrega

## Fonte, estado e separação de evidências

O pacote de origem é uma cópia ZIP do repositório `gilas-byte/projetoAplicado3`, sem metadados `.git`. Assim, não é possível comprovar commits, PRs, autores ou branches remotos usando somente estes arquivos. A conta autenticada no conector é `kiraabin`, sem acesso ao repositório da equipe no momento da análise. Essas melhorias constituem **proposta local não publicada**.

O plano de trabalho AV1 registrou quatro integrantes originalmente. O README da cópia atual registra três: Samuel Silva de Rezende (Product Owner), Vinícius Joacir dos Anjos (desenvolvimento/IA) e Guilherme da Silva Anselmo (QA, integridade, segurança, design e frontend). A distribuição **histórica real por commits não pode ser certificada** pelo ZIP.

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
- [ ] Executar todos os testes com dependências do projeto.
- [ ] Executar ETL sobre todas as edições oficiais e arquivar hashes/manifests e logs.
- [ ] Verificar exatidão contra contagem direta em DuckDB com notas e filtros controlados.
- [ ] Validar que nenhum artefato interno fica disponível via URL pública.
- [ ] Consolidar o diagrama e copiar volumetria real para o relatório.
- [ ] Confirmar rubrica somando 120% e formato final da entrega com docente.

## Testes e limites

O teste puro `tests/test_percentil_exato.py` não necessita DuckDB. Os testes legados exigem `duckdb` e alguns exigem `streamlit`. As verificações integrais e o deploy não podem ser marcados como aprovados apenas pela compilação dos módulos Python.
