# Pesquisa e decisao da stack

Atende ao requisito de autonomia tecnologica com pesquisa previa (a stack deve ser defendida por escalabilidade, limites de memoria e desempenho de processamento) e aos objetivos 2 e 4 do Plano de Trabalho. A secao 4 do plano trazia uma **hipotese** de stack; este documento a confronta com as alternativas e com numeros medidos sobre os microdados reais.

- Numeros brutos: [`benchmark.json`](benchmark.json)
- Tabelas completas: [`benchmark.md`](benchmark.md)
- Script que reproduz tudo: [`scripts/benchmark_stack.py`](../../scripts/benchmark_stack.py) (dependencias em [`requirements-benchmark.txt`](../../requirements-benchmark.txt))

## 1. O problema que a stack precisa resolver

| Restricao | Valor | Origem |
| --- | --- | --- |
| Volume bruto | 4 edicoes, 7,5 GB de CSV em latin-1, 17,7 milhoes de linhas, 76 colunas | [`docs/profiling`](../profiling/README.md) |
| Colunas usadas pelo produto | 58 | [`docs/contrato`](../contrato/README.md) |
| Memoria do runtime web | cerca de 1 GB de RAM (hospedagem gratuita) | Plano, secao 4 |
| Latencia | consultas representativas em ate 3 s no ambiente-alvo | RNF02 |
| Runtime nao rele o CSV bruto | processamento pesado offline, runtime so consulta artefatos | RNF01, Plano, secao 4 |
| Privacidade | nenhum grupo com menos de 100 participantes | [`docs/privacidade.md`](../privacidade.md) |

Duas cargas de trabalho diferentes decorrem disso (Kleppmann, 2017):

1. **Lote offline** (ETL RAW -> TRUSTED -> ANALYTICS): roda poucas vezes, na maquina da equipe, com todos os nucleos. Importa o pico de memoria (tem que caber em um notebook de 8 a 16 GB) e o tempo total.
2. **Consulta online** (runtime web): roda a cada interacao, em 1 GB e poucos nucleos. Importa a latencia e, principalmente, o pico de memoria por consulta, porque estourar 1 GB derruba o app para todos os usuarios.

Os criterios do requisito foram operacionalizados assim:

| Criterio | Como foi medido |
| --- | --- |
| Limites de memoria | Pico de memoria residente (RSS) do processo e de seus filhos, amostrado a cada 20 ms e cruzado com o `VmHWM` do kernel |
| Desempenho de processamento | Tempo de parede do ETL por edicao; latencia da primeira consulta e mediana de 5 repeticoes |
| Escalabilidade | Comportamento do pico e do tempo quando o volume cresce (edicoes de 1,4 a 2,2 GB), modelo de execucao (em memoria, streaming, distribuido) e o que muda para crescer alem de uma maquina |
| Complementares (objetivo 2) | Tamanho em disco, complexidade operacional, custo de hospedagem e adequacao ao prazo |

## 2. Pesquisa das alternativas

### 2.1 Motor de processamento

| Ferramenta | Modelo de execucao | Memoria | Escalabilidade | Observacoes para o projeto |
| --- | --- | --- | --- | --- |
| **pandas** (3.x) | Imperativo e *eager*: cada operacao materializa um DataFrame inteiro. Leitura de CSV pelo parser C ou pelo pyarrow | O DataFrame precisa caber inteiro na RAM, com copias intermediarias; strings eram objetos Python ate o 2.x e no 3.x passam a usar Arrow | Vertical apenas; para crescer, depende de fatiar a leitura manualmente (`chunksize`) | Referencia de ensino e *baseline* do objetivo 4. Com filtros empurrados ao pyarrow (`read_parquet(filters=...)`) le so o necessario do Parquet |
| **Polars** (1.x) | DataFrame em Rust sobre Arrow, com API *lazy*: o plano da consulta e otimizado (projecao e predicado empurrados para a leitura) antes de executar. Motor de *streaming* para processar em lotes | Colunar e sem copias entre etapas; o modo streaming processa arquivos maiores que a RAM | Vertical, multithread; sem modo distribuido | O leitor de CSV exige UTF-8: os arquivos do INEP (latin-1) precisam ser transcodificados antes, e esse custo entrou no benchmark |
| **DuckDB** (1.x) | Banco OLAP embarcado (biblioteca no processo, sem servidor), execucao vetorizada e paralela, SQL (Raasveldt; Muhleisen, 2019) | Operadores que *derramam* para disco quando passam do `memory_limit`; le Parquet direto com projecao, filtro e poda por estatisticas de *row group* | Vertical, multithread; consulta varios arquivos Parquet como uma tabela | Le latin-1 nativamente. O `memory_limit` configuravel e o que permite garantir o teto de 1 GB no runtime |
| **Apache Spark** (4.x) | Motor distribuido na JVM: o *driver* planeja, os *executors* processam particoes, com otimizador Catalyst | Cada executor tem heap JVM fixo e derrama para disco; o custo fixo da JVM e alto | Horizontal: o mesmo codigo roda em um cluster | Pensado para dados que nao cabem em uma maquina. Exige Java 17+. O plano ja dizia: so seria adotado "com necessidade mensuravel" |

### 2.2 Formato de armazenamento

- **CSV**: texto, linha a linha, sem tipos nem estatisticas. Toda consulta rele e reconverte o arquivo inteiro. E o formato RAW preservado (com hash), nunca o de consulta.
- **Parquet**: colunar, tipado, comprimido por coluna, com estatisticas (min/max) por *row group* que permitem pular blocos inteiros (Apache Software Foundation, [s.d.]). Uma consulta que usa 2 de 58 colunas le so essas 2.
- **Codecs**: `snappy` prioriza velocidade, `gzip` compressao, e `zstd` fica entre os dois, com razao proxima do gzip e leitura proxima do snappy. O benchmark mediu os quatro.

### 2.3 Interface (frontend)

| Ferramenta | Modelo | Custo de memoria | Escalabilidade | Observacoes |
| --- | --- | --- | --- | --- |
| **Streamlit** | Script Python reexecutado de cima a baixo a cada interacao; estado por sessao em `st.session_state`; `st.cache_data`/`st.cache_resource` evitam refazer trabalho caro | Um processo servidor; cada sessao guarda seu estado. Caches compartilhados entre sessoes | Um processo por app; para crescer, replicas atras de um balanceador | Menor esforco para um MVP de dados; deploy gratuito nativo no Streamlit Community Cloud |
| **Dash** (Plotly) | App Flask com *callbacks* declarados entre componentes; so o callback afetado roda | Sem estado por sessao no servidor por padrao (estado vai para o navegador ou para `dcc.Store`) | Stateless: escala com varios *workers* WSGI | Mais controle do layout e do fluxo; mais codigo que Streamlit para o mesmo painel |
| **Shiny para Python** (Posit) | Programacao reativa: o grafo de dependencias recalcula so as saidas afetadas por uma entrada | Um processo servidor com estado por sessao (sessao via WebSocket) | Um processo por app; replicas com afinidade de sessao | Modelo reativo mais fino que o do Streamlit; ecossistema Python menor que o do R |
| **React + FastAPI** | SPA no navegador consumindo uma API REST/JSON | O servidor so responde consultas; o custo de renderizacao vai para o navegador | Maior teto: API stateless, escala horizontal, front em CDN | Duas bases de codigo (TypeScript e Python), build e deploy separados. Maior custo para o prazo do semestre |

## 3. Metodo do benchmark

- **Dados reais**, sem amostragem: as quatro edicoes completas (2019 a 2022), com as 58 colunas do contrato e os tipos fixados pelo profiling.
- **Isolamento**: cada medicao roda em um processo filho novo. O pico de memoria e o do filho e de todos os seus descendentes (inclui a JVM do Spark). A amostragem so comeca depois do `exec`, para nao contar a memoria do processo pai.
- **Cache justo**: o CSV e lido uma vez antes das medicoes de ETL, para que nenhum motor pague a leitura fria do disco sozinho.
- **Runtime simulado**: as consultas rodam presas a 2 nucleos (afinidade de CPU, `POLARS_MAX_THREADS=2`, `SET threads=2` no DuckDB, `pa.set_cpu_count(2)` no pyarrow). A memoria nao e limitada a forca, e sim medida e comparada com o orcamento de 1 GB.
- **Consultas representativas** do produto, todas com o piso de 100 participantes por grupo:
  - `q1`: percentil de uma nota de MT entre os elegiveis de 2022, sobre o dado individual;
  - `q2`: media e mediana de MT por UF de prova;
  - `q3`: renda x dependencia administrativa da escola nas 4 edicoes, com n, medias e quartis;
  - `q4`: histograma de MT em um recorte filtrado (escola publica, renda baixa);
  - `q5`: o mesmo percentil da `q1`, lido de um artefato ANALYTICS pre-agregado.
- **Corretude**: o resultado de cada motor e comparado com o do DuckDB (tolerancia de ponto flutuante `1e-9` relativa). So o veredito entra no repositorio; os resultados ficam em `data/bench/`, fora do git.
- **Limites**: uma unica maquina (ver ambiente em `benchmark.md`), uma execucao de ETL por motor e edicao. O ambiente-alvo tem CPUs mais lentas que o notebook de teste; as latencias medidas sao um limite inferior, e a margem para os 3 s do RNF02 e discutida abaixo.

## 4. Resultados

Rodada completa de 2026-09-25, quatro edicoes, cinco motores de ETL e tres de consulta. As tabelas com todos os numeros estao em [`benchmark.md`](benchmark.md); aqui ficam o que eles mostram para cada criterio.

### 4.1 Corretude

Todos os motores gravaram o numero de linhas esperado pelo profiling, nas quatro edicoes, com os mesmos tipos fisicos (`BIGINT`, `DOUBLE`, `VARCHAR`). Nas cinco consultas, pandas, Polars e DuckDB devolveram o mesmo resultado. O percentil lido do artefato ANALYTICS (`q5`) e igual ao calculado sobre o dado individual (`q1`): o artefato agregado nao perde informacao para esse uso.

### 4.2 ETL offline (limites de memoria e desempenho)

| Motor | Tempo por edicao | Pico de memoria | Como o pico cresce com o volume |
| --- | --- | --- | --- |
| pandas (parser C) | 45 a 76 s | 2,9 a 4,9 GB | Proporcional ao CSV, cerca de 2 vezes o tamanho do arquivo |
| pandas (parser pyarrow) | 9 a 17 s | 4,8 a 7,0 GB | Proporcional ao CSV, cerca de 3 vezes o tamanho do arquivo |
| Polars (com transcodificacao) | 8 a 15 s | 1,9 a 2,7 GB | Cresce com o CSV |
| **DuckDB** | **6 a 9 s** | 2,2 a 2,4 GB | Praticamente estavel entre edicoes |
| Spark (`local[*]`) | 29 a 40 s | 1,6 GB | Estavel (heap fixo da JVM) |

- O pandas com parser pyarrow e rapido, mas chega a 7 GB na edicao de 2019. Nao cabe em um notebook de 8 GB e ocupa quase metade de um de 16 GB.
- O Spark tem o menor pico, mas leva de 4 a 5 vezes o tempo do DuckDB. O custo fixo da JVM e do planejamento distribuido nao se paga em arquivos de 1,4 a 2,2 GB que cabem em uma maquina.
- O Polars fica perto do DuckDB no tempo, mas precisa transcodificar o latin-1 do INEP antes (um arquivo UTF-8 temporario do tamanho do CSV) e grava um Parquet cerca de 25% maior com o mesmo codec.
- O DuckDB e o mais rapido nas quatro edicoes. O pico medido foi com as configuracoes padrao; o `memory_limit` permite reduzi-lo se a maquina da equipe for menor.

### 4.3 Formato de armazenamento

Na edicao de 2019 (2,24 GB de CSV), o Parquet com `zstd` ocupa 101 MB, 22,6 vezes menor que o CSV, empatado com `gzip` em tamanho e com a velocidade de escrita do `snappy` (2,4 s contra 4,3 s do gzip). A leitura de uma agregacao por UF custa 36 ms, contra 25 ms do `snappy`: 11 ms a mais por consulta, irrelevante diante dos 3 s do RNF02. A camada TRUSTED das quatro edicoes soma 340 MB.

### 4.4 Consultas no orcamento de runtime (2 nucleos, 1 GB)

| Consulta | pandas | Polars | DuckDB |
| --- | --- | --- | --- |
| `q1`, `q2`, `q4` (filtro e agregacao em 2022) | 149 a 274 ms, ate 514 MB | 44 a 84 ms, ate 350 MB | 71 a 98 ms, ate 111 MB |
| `q3` (4 edicoes, quartis por grupo) | 2351 ms, **2044 MB** | 967 ms, **2111 MB** | 1037 ms, 497 MB |
| `q5` (artefato ANALYTICS) | 5 ms, 160 MB | 2 ms, 69 MB | 2 ms, 65 MB |

(mediana de 5 execucoes e pico do processo, incluindo o interpretador)

- Em latencia, Polars e DuckDB ficam na mesma ordem de grandeza, e o pandas e de 2 a 3 vezes mais lento.
- **Em memoria, so o DuckDB cabe no orcamento em todas as consultas.** Na `q3`, pandas e Polars passam de 2 GB e derrubariam o app no ambiente-alvo. O DuckDB fica em 497 MB porque respeita o `memory_limit` e derrama para disco quando precisa; Polars e pandas nao tem um teto equivalente.
- A `q3` leva cerca de 1 s no notebook de teste. Com CPUs de hospedagem gratuita mais lentas, a margem para os 3 s do RNF02 e de cerca de 3 vezes, pequena para uma consulta interativa.
- A `q5` mostra o efeito da camada ANALYTICS: o mesmo percentil da `q1` sai em 2 ms e 65 MB, lendo 0,2 MB em vez de 340 MB.

### 4.5 Custo fixo da interface

| Framework | Subida | Memoria ociosa |
| --- | --- | --- |
| Streamlit | 1,3 s | 73 MB |
| Dash | 0,5 s | 92 MB |
| Shiny | 0,6 s | 100 MB |
| FastAPI (backend de um front React) | 0,4 s | 76 MB |

As diferencas de memoria (73 a 100 MB) sao pequenas perto do orcamento e nao decidem a escolha. O que pesa no frontend e o custo por sessao, que depende do app real e sera medido no prototipo, e o esforco de desenvolvimento (secao 2.3).

## 5. Decisao

| Camada | Decisao | Hipotese do plano | Evidencia principal |
| --- | --- | --- | --- |
| ETL (RAW -> TRUSTED -> ANALYTICS) | **DuckDB** | Polars | Mais rapido nas 4 edicoes, le latin-1 sem transcodificar, Parquet 20% menor que o do Polars |
| Formato | **Parquet `zstd`** | Parquet ZSTD | 22,6 vezes menor que o CSV, escrita tao rapida quanto `snappy` |
| Consulta no runtime | **DuckDB** com `memory_limit` | DuckDB | Unico motor que ficou abaixo de 1 GB em todas as consultas |
| Interface | **Streamlit + Plotly** | Streamlit + Plotly | Custo fixo equivalente aos outros; menor esforco e deploy gratuito nativo no prazo do semestre |
| Processamento distribuido | **Spark nao adotado** | So com necessidade mensuravel | 4 a 5 vezes mais lento que o DuckDB; os dados cabem em uma maquina |

**O que mudou em relacao a hipotese:** o plano previa Polars na transformacao. O benchmark nao sustenta essa escolha para estes dados: o DuckDB e mais rapido, nao precisa converter a codificacao do INEP e gera arquivos menores. Usar um motor so no ETL e no runtime tambem elimina uma dependencia e uma segunda sintaxe (expressoes do Polars e SQL) para a equipe manter. O Polars continua uma boa ferramenta; so nao ha ganho medido que justifique os dois motores.

**Por que nao Spark:** o Spark foi medido, nao descartado por principio. Com o maior CSV em 2,2 GB e a camada TRUSTED inteira em 340 MB, o problema cabe em uma maquina com folga, e a JVM so acrescenta tempo e dependencia (Java 17+). Ele passaria a fazer sentido se o volume crescesse ao ponto de o ETL de uma edicao nao caber na memoria de uma maquina mesmo com derramamento para disco. Nas quatro edicoes do recorte, o pico do DuckDB ficou estavel entre 1,4 e 2,2 GB de CSV, sem sinal de se aproximar desse limite.

**Por que Streamlit, e nao React + FastAPI:** com memoria equivalente, a diferenca esta no custo de desenvolvimento. Uma SPA exigiria duas bases de codigo e dois deploys, e a AV2 pede um fluxo ponta a ponta em uma sprint. Dash fica como alternativa se o layout do Streamlit limitar a UX; a camada de dados nao muda, porque as consultas ficam em funcoes Python independentes do framework.

### 5.1 Consequencias para a implementacao

1. **Uma conexao DuckDB compartilhada no runtime**, criada uma vez (`st.cache_resource`) com `threads=2` e `memory_limit` abaixo do orcamento. O limite do DuckDB vale por instancia: com uma conexao por sessao, duas consultas `q3` simultaneas somariam cerca de 1 GB so de consulta.
2. **Consultas pesadas pre-agregadas na camada ANALYTICS.** Recortes como o da `q3` (renda x dependencia x edicao) viram artefatos no ETL, como o `dist_notas` da `q5`, e o runtime passa a responder em milissegundos. O dado individual da TRUSTED fica para consultas que dependem da nota informada pelo usuario.
3. **O piso de 100 participantes aplicado dentro da consulta** (`HAVING n >= 100`), como no benchmark, e nao depois na interface.
4. **Pendencias medidas no prototipo:** memoria por sessao do Streamlit e latencia no ambiente de hospedagem real (Streamlit Community Cloud ou Hugging Face Spaces), para confirmar a margem da secao 4.4.

## 6. Referencias

- APACHE SOFTWARE FOUNDATION. *Apache Parquet Documentation*. Disponivel em: https://parquet.apache.org/docs/.
- DASH. *Dash Documentation*. Plotly. Disponivel em: https://dash.plotly.com/.
- DUCKDB. *DuckDB Documentation*. Disponivel em: https://duckdb.org/docs/.
- FASTAPI. *FastAPI Documentation*. Disponivel em: https://fastapi.tiangolo.com/.
- KLEPPMANN, Martin. *Designing Data-Intensive Applications*. Sebastopol: O'Reilly Media, 2017.
- PANDAS. *pandas documentation*. Disponivel em: https://pandas.pydata.org/docs/.
- POLARS. *Polars User Guide*. Disponivel em: https://docs.pola.rs/.
- POSIT. *Shiny for Python*. Disponivel em: https://shiny.posit.co/py/.
- RAASVELDT, Mark; MUHLEISEN, Hannes. DuckDB: an embeddable analytical database. *Proceedings of SIGMOD 2019*. New York: ACM, 2019.
- STREAMLIT. *Streamlit Documentation*. Disponivel em: https://docs.streamlit.io/.
- ZAHARIA, Matei et al. Apache Spark: a unified engine for big data processing. *Communications of the ACM*, v. 59, n. 11, p. 56-65, 2016.
