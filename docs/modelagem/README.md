# Modelo de dados analítico — grão, fatos e dimensões

Documenta a camada ANALYTICS como um modelo dimensional (Engenharia de Dados e MLOps,
aula 2: processo de negócio, grão, dimensões e fatos) e registra as regras de
integridade que o projeto aplica sem um banco relacional (Banco de Dados II, ementa de
2026/1: chaves, restrições, índices e planos de consulta).

## 1. Processo e camadas

| Camada (medalhão) | Nome no projeto | Grão | Onde |
| --- | --- | --- | --- |
| Bronze | RAW | Um registro por inscrito, como o INEP publica (76 colunas, latin-1) | `data/raw/` (fora do git), hash em `data/raw/hashes.sha256` |
| Prata | TRUSTED | Um registro por inscrito, 58 colunas do contrato tipadas e 4 derivadas | `data/trusted/enem/ano=<ano>/` (fora do git), contrato em `docs/contrato/` |
| Ouro | ANALYTICS | Uma linha por nota distinta de um grupo de comparação (abaixo) | `data/analytics/` (fora do git), conferida por `scripts/auditar_artefatos.py` |

O processo de negócio modelado é "a distribuição das notas dos participantes elegíveis
de uma edição, por área e por grupo de comparação". O produto responde a uma única
pergunta sobre ele: em que posição fica uma nota.

## 2. Tabela fato da ANALYTICS

Os artefatos dos módulos (`dist_equidade`, `dist_territorial` e `dist_capital`) têm o
mesmo esquema e formam uma tabela fato de distribuição particionada por módulo; a CDF
nacional (`dist_exata`) é o mesmo fato sem as colunas de grupo.

**Frase do grão:** cada linha equivale a **uma nota distinta observada, numa edição, numa
área e num grupo de comparação**, com quantos participantes elegíveis tiveram exatamente
essa nota e quantos ficaram abaixo dela.

| Coluna | Papel | Observação |
| --- | --- | --- |
| `ano` | Chave da dimensão edição | 2019 a 2022; também partição física da TRUSTED |
| `area` | Chave da dimensão área | `cn`, `ch`, `lc`, `mt`, `redacao` |
| `recorte` | Chave da dimensão módulo | `renda`, `territorial`, `capital` |
| `grupo` | Chave da dimensão grupo de comparação | Códigos com prefixo: `BR`, `RG-<região>`, `UF-<sigla>`, `R1`…`R6`, `CONTRASTE`, `NV-<nível>` (DL-04, item 4) |
| `nota` | Chave degenerada | Nota observada; a chave do grão termina nela |
| `n` | Medida **aditiva** | Pode ser somada entre notas, entre UFs de uma região e entre regiões |
| `abaixo` | Medida **semiaditiva** | Acumulada dentro do grupo; não se soma entre notas |
| `total` | Medida **não aditiva** entre linhas | Repete o N do grupo em todas as linhas dele |

**Chave do grão (única):** (`ano`, `area`, `recorte`, `grupo`, `nota`). Nas faixas do
histograma (`dist_notas`), (`ano`, `area`, `nota_min`).

**Dimensões.** São pequenas e estáveis, por isso ficam no código e não em tabelas
separadas: áreas e rótulos em cada módulo (`AREAS`), UFs e regiões em
`scripts/territorial.py`, faixas de renda em `scripts/equidade.py`, níveis de
escolaridade em `scripts/capital_escolar.py`. Um modelo estrela físico, com tabelas
`dim_*` e chaves substitutas, não traria ganho para um conjunto somente leitura de
13 MB lido inteiro em memória. Se o produto passar a ter histórico de mudanças nos
rótulos (por exemplo, nova faixa de renda numa edição futura), a dimensão de grupo vira
tabela com chave substituta e vigência.

**Por que não há medida "média por grupo" na tabela.** Média, mediana, desvio e quartis
são calculados a partir das linhas (`n` por nota) pelo motor estatístico. Guardar a
média pronta numa tabela agregada abriria o risco de somar médias de grupos de tamanhos
diferentes, armadilha registrada pela disciplina de BI (média de percentuais sem
ponderação).

## 3. Regras de integridade (Banco de Dados II, sem SGBD)

O projeto não usa banco relacional (justificativa em `docs/av6/nuvem.md`, seção 3), mas
aplica as mesmas restrições que um esquema declararia. Elas são verificadas por código
antes de publicar:

| Restrição que um SGBD declararia | Equivalente no projeto | Onde |
| --- | --- | --- |
| `PRIMARY KEY (ano, area, recorte, grupo, nota)` | Chave do grão sem repetição | `auditar_artefatos.py` |
| `CHECK (n > 0)` | n positivo | `auditar_artefatos.py`; `construir_acumulada` |
| `CHECK (nota BETWEEN 0 AND 1000)` | Faixa de nota | `auditar_artefatos.py`; validação da entrada nos módulos |
| `CHECK` de coerência (`abaixo` = soma dos `n` anteriores; `total` = soma do grupo) | CDF coerente | `auditar_artefatos.py` |
| Integridade entre tabelas (o Brasil de um artefato igual ao dos outros) | Total nacional igual entre artefatos | `auditar_artefatos.py` |
| `CHECK (total >= 100)` | Piso de privacidade por grupo | `auditar_artefatos.py`; ETL de cada módulo |
| Tipos e nulidade por coluna | Contrato de dados | `scripts/colunas.py`, `docs/contrato/` |

**Normalização.** A TRUSTED é deliberadamente uma tabela larga, sem normalização: é uma
camada analítica (OLAP), lida por varredura colunar, sem atualização linha a linha, e
não sofre as anomalias de inserção e atualização que a normalização evita num sistema
transacional. O relatório da AV3 (seção 5.4) registra a única desnormalização que pesa:
o nome do município ocupa espaço e poderia ir para uma dimensão de cerca de 1,7 mil
linhas, mantendo só o código IBGE. Como o produto não usa município (DL-04, item 3), a
mudança não foi feita.

**Índices, triggers e procedures.** Não se aplicam: não há SGBD transacional. O
equivalente a índice é o próprio layout: Parquet colunar, partição por edição na
TRUSTED e artefatos ordenados por grupo e nota, o que permite busca binária na CDF em
memória (percentil em cerca de 0,1 ms, relatório da AV3).

**Plano de consulta.** `python scripts/auditar_artefatos.py --explicar` mostra o
`EXPLAIN ANALYZE` da consulta que o app faz ao abrir: uma varredura do Parquet com
projeção das cinco colunas usadas e ordenação, sem filtro, porque o app carrega a
distribuição inteira uma vez e responde às consultas em memória.
