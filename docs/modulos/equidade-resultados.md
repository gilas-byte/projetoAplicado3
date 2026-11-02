# Módulo Equidade socioeconômica — execução com os microdados reais

Autor: Samuel Silva de Rezende. Regras em [`docs/decisoes/README.md`](../decisoes/README.md#dl-03--regras-do-módulo-equidade-socioeconômica) (DL-03).

## Execução

- **Data:** 02/11/2026, branch `modulo-equidade`.
- **Fonte:** CSVs oficiais do INEP das edições 2019 a 2022 (7,51 GB). O número de linhas de cada
  edição confere com o profiling versionado: 17.744.217 registros no total.
- **Ambiente:** máquina virtual Linux no notebook do autor (Intel i5-12450H, 2 vCPU, 3,9 GB de
  memória), Python 3.10.12, DuckDB 1.5.5 com `memory_limit = 1800MB`.
- **Tempos:** TRUSTED 62,8 s nas quatro edições (19,8 + 18,5 + 12,3 + 12,2), ANALYTICS 66,8 s,
  módulo de equidade 35,1 s.
- **Artefato:** `data/analytics/dist_equidade.parquet`, 515.218 linhas, 1,93 MB (fora do git, uso
  restrito ao backend).
- **Grupos:** 140 publicados (4 edições × 5 áreas × 7 grupos); nenhum suprimido pelo piso de 100.
- **Conferência:** a CDF gerada em SQL coincidiu linha a linha com a montada em Python, e a
  maior divergência entre o percentil da CDF e a contagem direta na TRUSTED foi 0,0 ponto
  percentual.

Elegíveis por edição: 3.174.212 (2019), 2.242.169 (2020), 1.870.734 (2021) e 1.927.753 (2022).
O grupo de contraste tem entre 36 mil e 50 mil participantes por edição e área.

## Mediana por faixa de renda

Matemática:

| Edição | R1 | R2 | R3 | R4 | R5 | R6 | Contraste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 456,5 | 485,3 | 525,3 | 571,1 | 624,2 | 687,9 | 690,3 |
| 2020 | 450,3 | 498,1 | 548,2 | 591,0 | 634,0 | 684,2 | 678,7 |
| 2021 | 463,4 | 499,8 | 540,7 | 582,2 | 628,1 | 678,6 | 671,9 |
| 2022 | 472,8 | 520,2 | 561,5 | 596,2 | 637,6 | 681,6 | 674,6 |

Redação:

| Edição | R1 | R2 | R3 | R4 | R5 | R6 | Contraste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 540 | 560 | 600 | 640 | 680 | 760 | 800 |
| 2020 | 540 | 560 | 600 | 660 | 720 | 800 | 800 |
| 2021 | 560 | 600 | 620 | 660 | 720 | 800 | 800 |
| 2022 | 580 | 620 | 660 | 700 | 760 | 820 | 820 |

Nas 20 combinações de edição e área, a mediana cresce de R1 para R6 sem exceção.

## Probabilidade de superioridade contra o contraste

P(faixa > contraste) + 0,5 · P(empate), em %:

| Edição | Área | R1 | R6 |
| --- | --- | --- | --- |
| 2019 | Matemática | 8,1 | 49,4 |
| 2019 | Redação | 12,3 | 46,8 |
| 2022 | Matemática | 12,5 | 51,8 |
| 2022 | Redação | 15,7 | 49,0 |

Na faixa R1, o valor fica entre 8,1% e 17,0% em todas as edições e áreas. Na faixa R6, fica perto de 50% (46,8% a 54,5%):
entre as famílias de renda acima de 10 salários mínimos, quem declarou escola privada não se
distingue do restante da faixa. Parte da faixa R6 não declarou escola (concluiu o ensino médio
antes), e essa diferença de composição impede leitura causal.

## Exemplo da interface

Edição 2022, renda D (mais de 1 até 2 SM), Matemática 650,0: percentil 87,1% na faixa
(558.228 participantes) e 41,3% no contraste (43.532), diferença de 45,8 pontos percentuais e
probabilidade de superioridade de 18,9%.
