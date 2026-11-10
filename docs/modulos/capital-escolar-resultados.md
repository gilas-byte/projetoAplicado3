# Módulo Capital escolar familiar — execução com os microdados reais

Autor: Guilherme da Silva Anselmo. Regras em [`docs/decisoes/README.md`](../decisoes/README.md#dl-05--regras-do-módulo-capital-escolar-familiar) (DL-05).

## Execução

- **Data:** 10/11/2026, código do commit `45ff259` (PR #20, branch `modulo-capital-escolar-codigo`).
- **Quem rodou:** Samuel Silva de Rezende, com os microdados oficiais do INEP das edições 2019 a 2022. Os números abaixo vêm do manifesto `_manifesto_capital.json` dessa execução; o manifesto fica fora do git, como os artefatos.
- **Como rodou:** `etapa_capital` foi executada uma vez por edição, por causa do limite de tempo por execução na máquina usada. Os quatro parquets anuais foram unidos em `data/analytics/dist_capital.parquet`, ordenado por edição, área, grupo e nota. As linhas e os tempos do manifesto são somas das quatro execuções.
- **Artefato:** `data/analytics/dist_capital.parquet`, 508.214 linhas, 2,08 MB (fora do git, uso restrito ao backend, ADR-001).
- **Grupos:** 140 publicados (4 edições × 5 áreas × 7 grupos: o Brasil e os seis níveis); nenhum suprimido pelo piso de 100. O menor grupo é o nível A em 2022, com 26.521 participantes, então o caso de nível vizinho abaixo do piso (DL-05, item 6) não ocorreu com os dados reais. O código continua tratando esse caso, e ele é coberto pelos testes.
- **Conferência:** a CDF gerada em SQL coincidiu com a montada em Python, os níveis nunca somaram mais que o Brasil, e a maior divergência entre o percentil da CDF e a contagem direta na TRUSTED foi 0,0 ponto percentual nas quatro edições.

| Edição | Linhas | Tempo | Maior divergência |
| --- | --- | --- | --- |
| 2019 | 122.405 | 99,1 s | 0,0 pp |
| 2020 | 128.985 | 69,8 s | 0,0 pp |
| 2021 | 128.750 | 57,8 s | 0,0 pp |
| 2022 | 128.074 | 58,6 s | 0,0 pp |

## Funil de escolaridade

Participantes elegíveis (presentes nos dois dias, não treineiros) por situação de `Q001` e `Q002`:

| Edição | Elegíveis | Com nível | Sem nível | Pai "Não sei" | Mãe "Não sei" |
| --- | --- | --- | --- | --- | --- |
| 2019 | 3.174.212 | 3.112.988 (98,1%) | 61.224 (1,9%) | 274.454 (8,6%) | 87.480 (2,8%) |
| 2020 | 2.242.169 | 2.180.105 (97,2%) | 62.064 (2,8%) | 180.710 (8,1%) | 51.391 (2,3%) |
| 2021 | 1.870.734 | 1.841.296 (98,4%) | 29.438 (1,6%) | 152.756 (8,2%) | 43.415 (2,3%) |
| 2022 | 1.927.753 | 1.888.899 (98,0%) | 38.854 (2,0%) | 177.391 (9,2%) | 55.401 (2,9%) |

- **Sem nível** é quem respondeu "Não sei" ou deixou em branco nos dois campos (DL-05, item 3). Esses participantes ficam só na posição nacional.
- Nenhum registro teve código fora de A a H: `campo_invalido` é 0 nas quatro edições, então a regra dos itens 8 e 9 não excluiu ninguém.
- Com nível + sem nível = elegíveis em todas as edições.
- O "Não sei" é cerca de 3 a 4 vezes mais frequente na pergunta do pai do que na da mãe, como a DL-05 já previa. Quando só o pai responde "Não sei", o nível vem da mãe, e vale a limitação descrita na DL-05 (item 2): o grupo pode ficar abaixo do real se o pai tiver escolaridade maior.

## Tamanho dos níveis

Participantes por nível, Matemática (as outras áreas têm os mesmos tamanhos, com uma exceção na Redação de 2019, descrita abaixo):

| Edição | A | B e C | D | E | F | G |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 72.486 | 788.153 | 398.099 | 1.149.020 | 395.667 | 309.563 |
| 2020 | 43.800 | 510.679 | 243.741 | 813.314 | 302.357 | 266.214 |
| 2021 | 27.576 | 349.441 | 193.655 | 693.484 | 292.415 | 284.725 |
| 2022 | 26.521 | 344.478 | 203.195 | 729.727 | 293.688 | 291.290 |

Participação de cada nível entre os participantes com nível, em %:

| Edição | A | B e C | D | E | F | G |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 2,3 | 25,3 | 12,8 | 36,9 | 12,7 | 9,9 |
| 2020 | 2,0 | 23,4 | 11,2 | 37,3 | 13,9 | 12,2 |
| 2021 | 1,5 | 19,0 | 10,5 | 37,7 | 15,9 | 15,5 |
| 2022 | 1,4 | 18,2 | 10,8 | 38,6 | 15,5 | 15,4 |

Entre 2019 e 2022, o nível A cai de 2,3% para 1,4% e o grupo B e C de 25,3% para 18,2%, enquanto o nível G sobe de 9,9% para 15,4%. É a composição de quem fez a prova em cada edição; o módulo não indica a causa dessa mudança.

Observação sobre a Redação em 2019: o grupo do Brasil tem 3.174.211 participantes (um a menos que nas outras áreas) e o nível E tem 1.149.019 (também um a menos), o que indica um participante elegível sem nota de Redação nessa edição. Nas demais edições os tamanhos coincidem em todas as áreas.

## Mediana por nível

Medidas calculadas por Samuel Silva de Rezende em 10/11/2026 sobre o `dist_capital.parquet` da execução de referência, com `carregar` e `resumo` deste módulo; o tamanho de cada grupo bate com o manifesto. Matemática:

| Edição | A | B e C | D | E | F | G | Brasil |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 436,7 | 462,0 | 479,5 | 502,0 | 572,8 | 611,4 | 497,4 |
| 2020 | 425,4 | 454,7 | 476,6 | 503,7 | 577,5 | 609,8 | 502,7 |
| 2021 | 442,4 | 466,5 | 483,6 | 508,4 | 576,5 | 607,3 | 513,1 |
| 2022 | 446,9 | 477,3 | 495,2 | 523,7 | 588,6 | 615,0 | 529,0 |

Redação (as notas andam de 20 em 20):

| Edição | A | B e C | D | E | F | G | Brasil |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 500 | 540 | 560 | 580 | 640 | 680 | 580 |
| 2020 | 480 | 520 | 560 | 580 | 640 | 700 | 580 |
| 2021 | 520 | 560 | 580 | 600 | 680 | 720 | 620 |
| 2022 | 520 | 560 | 600 | 620 | 700 | 760 | 620 |

Nas 20 combinações de edição e área, a mediana cresce a cada nível, sem exceção. Em Matemática 2022, vai de 446,9 (nível A) a 615,0 (nível G); a mediana do Brasil é 529,0. Isso descreve diferenças entre grupos de participantes e não indica que a escolaridade dos responsáveis causa a nota.

## Probabilidade de superioridade entre níveis

P(nível de cima > nível de baixo) + 0,5 · P(empate), em %, mesma fórmula da DL-05 (item 12). Matemática:

| Edição | B e C contra A | D contra B e C | E contra D | F contra E | G contra F | G contra A |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | 59,6 | 55,4 | 56,0 | 63,7 | 56,7 | 84,3 |
| 2020 | 59,6 | 55,7 | 56,1 | 64,1 | 56,4 | 84,7 |
| 2021 | 59,3 | 55,4 | 56,4 | 63,2 | 55,4 | 83,4 |
| 2022 | 59,4 | 54,6 | 56,5 | 63,0 | 55,4 | 82,9 |

Nas 20 combinações de edição e área:
- **F contra E** (Médio completo para Superior completo) é o maior salto entre vizinhos: de 60,7% a 64,1%.
- Nos demais pares vizinhos (B e C contra A, D contra B e C, E contra D e G contra F), vai de 52,7% a 61,0%.
- **G contra A**, os extremos: de 77,5% a 84,8%. Mesmo aí os grupos se sobrepõem bastante: o complemento (o par em que o nível A fica à frente ou empata, empates pela metade) é de 15,2% a 22,5%.

Conferência: para Matemática 2022, a contagem, a mediana e a média dos 7 grupos foram conferidas direto na TRUSTED, e a probabilidade de superioridade G contra F por contagem de pares deu 0,55426, igual à da função do módulo.

## Exemplo da interface

Edição 2022, Matemática, nota 650,0. Posição (percentil) da mesma nota, por grupo:

| Grupo | Percentil |
| --- | --- |
| Nível A | 96,9% |
| Nível B e C | 93,5% |
| Nível D | 90,7% |
| Nível E | 85,2% |
| Nível F | 68,8% |
| Nível G | 60,8% |
| Brasil | 81,4% |

A mesma nota fica em posições diferentes conforme o grupo de comparação: de 60,8% entre participantes do nível G a 96,9% entre os do nível A, com 81,4% na referência nacional. Todos os grupos têm mais de 26 mil participantes, então nenhuma dessas posições fica em limite de exibição (DL-05, item 13).
