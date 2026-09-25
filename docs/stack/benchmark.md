# Benchmark da stack (numeros medidos)

Gerado por `scripts/benchmark_stack.py` a partir de `benchmark.json`. A analise e a decisao estao em [`README.md`](README.md).

## Ambiente

- Maquina: Intel(R) Core(TM) i5-9300H CPU @ 2.40GHz, 8 threads, 15.4 GB de RAM, Linux 7.0.0-34-generic
- Python 3.12.3; openjdk version "17.0.20.1" 2026-08-18
- Versoes: pandas 3.0.6, pyarrow 25.0.1, polars 1.44.2, duckdb 1.5.5, pyspark 4.2.0, streamlit 1.64.0, dash 4.4.1, shiny 1.8.0, fastapi 0.141.1, uvicorn 0.54.0, plotly 7.1.0
- Execucao: 2026-09-25

## 1. ETL: CSV RAW -> Parquet ZSTD (58 colunas do contrato)

Uma execucao por motor e edicao, com o CSV ja no cache do sistema operacional. Todos os nucleos da maquina liberados (etapa offline). `Pico` e a memoria residente maxima do processo e seus filhos. O tempo do Polars inclui a transcodificacao latin-1 -> UTF-8.

| Edicao | CSV | pandas tempo | pandas pico | pandas_pyarrow tempo | pandas_pyarrow pico | polars tempo | polars pico | duckdb tempo | duckdb pico | spark tempo | spark pico |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 2.24 GB | 75.7s | 4.29 GB | 17.0s | 7.04 GB | 14.5s | 2.70 GB | 8.6s | 2.20 GB | 39.5s | 1.60 GB |
| 2020 | 1.89 GB | 73.4s | 4.88 GB | 15.9s | 6.92 GB | 12.5s | 2.32 GB | 9.0s | 2.39 GB | 39.6s | 1.60 GB |
| 2021 | 1.40 GB | 44.8s | 2.93 GB | 9.4s | 4.81 GB | 8.4s | 1.87 GB | 5.9s | 2.23 GB | 29.6s | 1.59 GB |
| 2022 | 1.46 GB | 46.0s | 3.00 GB | 10.4s | 5.07 GB | 8.7s | 1.90 GB | 6.2s | 2.24 GB | 29.2s | 1.56 GB |

Tamanho do Parquet gerado e conferencia de linhas contra o profiling:

| Edicao | pandas | pandas_pyarrow | polars | duckdb | spark |
| --- | --- | --- | --- | --- | --- |
| 2019 | 100.6 MB (ok) | 100.6 MB (ok) | 125.9 MB (ok) | 101.3 MB (ok) | 101.4 MB (ok) |
| 2020 | 102.1 MB (ok) | 102.1 MB (ok) | 120.1 MB (ok) | 103.2 MB (ok) | 102.9 MB (ok) |
| 2021 | 65.3 MB (ok) | 65.3 MB (ok) | 80.4 MB (ok) | 66.4 MB (ok) | 65.9 MB (ok) |
| 2022 | 68.4 MB (ok) | 68.4 MB (ok) | 84.2 MB (ok) | 69.1 MB (ok) | 68.6 MB (ok) |

Tipos fisicos gravados por motor: pandas: BIGINT, DOUBLE, VARCHAR; pandas_pyarrow: BIGINT, DOUBLE, VARCHAR; polars: BIGINT, DOUBLE, VARCHAR; duckdb: BIGINT, DOUBLE, VARCHAR; spark: BIGINT, DOUBLE, VARCHAR.

## 2. Compressao do Parquet (edicao 2019)

Mesmas 58 colunas, gravadas pelo DuckDB. CSV original completo: 2.24 GB. `Leitura` e a mediana de 5 execucoes de uma agregacao por UF sobre 2 colunas.

| Codec | Tamanho | Razao sobre o CSV | Escrita | Leitura |
| --- | --- | --- | --- | --- |
| uncompressed | 142.0 MB | 16.2x | 2.3s | 23 ms |
| snappy | 125.1 MB | 18.4x | 2.2s | 25 ms |
| gzip | 102.4 MB | 22.4x | 4.3s | 32 ms |
| zstd | 101.4 MB | 22.6x | 2.4s | 36 ms |

## 3. Consultas representativas no orcamento de runtime

Processo preso a 2 nucleos (afinidade de CPU), lendo a camada TRUSTED das edicoes 2019, 2020, 2021, 2022 (340.1 MB em Parquet) ou o artefato ANALYTICS agregado (0.2 MB). `1a` e a primeira execucao no processo; `mediana` e a de 5 execucoes seguintes. `Pico` inclui o interpretador e as bibliotecas importadas (`base`); o orcamento de referencia e 1024 MB. Toda consulta aplica o piso de 100 participantes por grupo.

| Consulta | pandas 1a / mediana | pandas pico | polars 1a / mediana | polars pico | duckdb 1a / mediana | duckdb pico | Resultados |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `q1_percentil` | 183 / 149 ms | 386 MB | 76 / 44 ms | 224 MB | 90 / 71 ms | 79 MB | iguais |
| `q2_uf` | 309 / 274 ms | 514 MB | 161 / 81 ms | 350 MB | 113 / 98 ms | 111 MB | iguais |
| `q3_recorte` | 2834 / 2351 ms | 2044 MB | 1131 / 967 ms | 2111 MB | 1076 / 1037 ms | 497 MB | iguais |
| `q4_histograma` | 248 / 206 ms | 436 MB | 125 / 84 ms | 191 MB | 114 / 92 ms | 89 MB | iguais |
| `q5_percentil_agregado` | 29 / 5 ms | 160 MB | 11 / 2 ms | 69 MB | 9 / 2 ms | 65 MB | iguais |

- `q1_percentil`: Percentil de uma nota de MT entre os elegiveis de 2022 (dado individual).
- `q2_uf`: Media e mediana de MT por UF de prova, 2022, com piso de grupo.
- `q3_recorte`: Renda x dependencia da escola nas 4 edicoes: n, medias e quartis.
- `q4_histograma`: Histograma de MT (faixas de 20 pontos) em um recorte filtrado.
- `q5_percentil_agregado`: Mesmo percentil da q1, lido do artefato ANALYTICS agregado.

Memoria so com as bibliotecas importadas, antes da primeira consulta: pandas 103 MB, polars 49 MB, duckdb 61 MB.

Percentil pelo artefato agregado (`q5`) igual ao calculado sobre o dado individual (`q1`): sim.

## 4. Custo fixo do servidor de interface

App minimo de cada framework importando DuckDB e Plotly, medido 2 s depois de responder a primeira requisicao HTTP. E o piso de memoria antes de qualquer sessao de usuario; o custo por sessao sera medido no prototipo.

| Framework | Subida | Memoria ociosa |
| --- | --- | --- |
| streamlit | 1.3s | 73 MB |
| dash | 0.5s | 92 MB |
| shiny | 0.6s | 100 MB |
| fastapi | 0.4s | 76 MB |
