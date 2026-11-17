# AV6 — Metodologia estatística e análises com os dados reais

Documento de apoio ao relatório final (AV6, critério "Metodologia Estatística e Rigor
Analítico de Backend"). Registra o que o motor estatístico calcula, o que foi
deliberadamente deixado de fora e o resultado de quatro análises executadas sobre os
artefatos reais da camada ANALYTICS.

- **Código:** `scripts/estatistica.py` (funções), `scripts/analises_av6.py` (análises).
- **Testes:** `tests/test_estatistica_av6.py` e `tests/test_app.py` (dados sintéticos de
  resultado conhecido).
- **Saída completa:** `docs/av6/analises_av6.json`, com o SHA-256 das entradas
  (`dist_exata.parquet` e `dist_territorial.parquet` da execução de referência) e o
  commit do código.
- **Reproduzir:** com os artefatos em `data/analytics/`,
  `./.venv/bin/python scripts/analises_av6.py` (cerca de 15 s).

Referência acadêmica: a ementa de Estatística I (2026/2) prevê amostragem, medidas de
tendência central e dispersão, histogramas, boxplots, distribuições, estimação,
intervalos de confiança e testes de hipótese. Como não houve material de aula
disponível no AVA, as escolhas abaixo citam a ementa e a bibliografia do Plano de
Trabalho (Bussab e Morettin, 2017; Devore, 2011), e não aulas específicas.

## 1. População, não amostra

Cada edição do ENEM entra inteira: todos os participantes elegíveis (presentes nos dois
dias e não treineiros) com nota na área. São 9.214.868 elegíveis nas quatro edições. As
medidas do produto são, portanto, **parâmetros populacionais calculados exatamente**, e
não estimativas. Consequências:

- variância com divisor N (DL-01);
- percentil pela CDF empírica exata, sem interpolação (ADR-001);
- nenhum intervalo de confiança nas medidas exibidas: não há erro amostral a expressar.

A seção 6 mostra, com os próprios dados, quanto uma amostra de 1% erraria.

## 2. Medidas do motor

| Medida | Definição | Onde |
| --- | --- | --- |
| Percentil | (abaixo + iguais / 2) / N × 100, posto médio | `percentil_exato_acumulado`, `dobro_posicao` |
| Média, variância, desvio-padrão | Momentos populacionais, somas em frações | `resumo` |
| Quantis (mediana, quartis, P5, P95) | Menor nota observada com pelo menos p · N participantes nela ou abaixo | `quantil` |
| Z-Score | (nota − média) / desvio | `z_score` |
| Probabilidade de superioridade | P(A > B) + 0,5 · P(A = B) | `prob_superioridade` |
| Caixa protegida | Q1, mediana, Q3, IQR e bigodes em P5 e P95 | `caixa_protegida` |
| D de Kolmogorov-Smirnov | máx \|F_A(x) − F_B(x)\| | `ks_distancia` |
| PSI | Σ (a − r) · ln(a / r) em decis da referência | `psi` |

**Moda.** O Plano previa a moda "quando pertinente". Nas quatro áreas objetivas a nota
vem da TRI, com milhares de valores distintos por edição, e a moda seria uma nota
qualquer com poucas pessoas a mais que as vizinhas, sem significado. Na redação (notas
múltiplas de 20) ela seria interpretável, mas não responde à pergunta do produto, que é
a posição de uma nota. Por isso não é exibida.

## 3. Probabilidade de superioridade como tamanho de efeito

A comparação entre dois grupos (faixa de renda contra contraste, UF contra o restante do
país, nível de escolaridade contra o vizinho) é feita pela probabilidade de
superioridade. Ela é o tamanho de efeito de "linguagem comum" (McGraw e Wong, 1992):
sorteando uma pessoa de cada grupo, é a chance de a do primeiro ter nota maior, com
empate contando metade. Equivale à estatística U de Mann-Whitney dividida por
n_A · n_B, ou seja, à área sob a curva ROC de separação entre os grupos.

**Por que não há teste de hipótese.** Com grupos de dezenas de milhares a milhões de
pessoas, o teste de Mann-Whitney rejeitaria a igualdade para qualquer diferença, por
menor que fosse; o p-valor seria praticamente zero em todas as comparações e não
diferenciaria uma diferença relevante de uma irrelevante. Além disso, os grupos são as
populações completas da edição, e não amostras de uma população maior, de modo que a
pergunta "a diferença existe na população?" já está respondida pelo próprio cálculo. O
Plano de Trabalho (item 6) restringe a inferência aos casos em que premissas e
significado são adequados, e este não é um deles. O produto informa o **tamanho** da
diferença (pontos percentuais e probabilidade de superioridade), e não sua
significância.

**Por que não há intervalo de confiança.** Pelo mesmo motivo: o valor calculado é o
parâmetro da população elegível daquela edição. Um intervalo só faria sentido se a
edição fosse tratada como amostra de uma "superpopulação" de edições possíveis, leitura
que o produto não adota e que não é necessária para a pergunta do usuário.

**Leitura causal.** Nenhuma medida é apresentada como efeito causal da renda, do
território ou da escolaridade dos pais (DL-03, DL-04 e DL-05, "Fora do escopo").

## 4. Caixa protegida (boxplot) e quartis

O Plano de Trabalho (item 6) prometia boxplots e quartis. A página inicial passa a
mostrar, para cada área informada, os quartis em texto e um gráfico de caixa com a nota
do usuário marcada.

**Decisão de privacidade.** No boxplot clássico, o mínimo, o máximo e os pontos
discrepantes são notas de pessoas isoladas, o que contraria o piso de 100 (R3). Os
bigodes param nos percentis 5 e 95, não há pontos soltos e a caixa só existe quando 5%
do grupo chega ao piso (N ≥ 2.000). O teste
`test_bigodes_deixam_pelo_menos_o_piso_de_fora` garante que pelo menos 100 pessoas
ficam em cada ponta.

Quartis nacionais de 2022 (notas):

| Área | P5 | Q1 | Mediana | Q3 | P95 | IQR |
| --- | --- | --- | --- | --- | --- | --- |
| Ciências da Natureza | 396,8 | 440,8 | 486,7 | 545,6 | 629,9 | 104,8 |
| Ciências Humanas | 391,7 | 479,5 | 532,5 | 585,7 | 659,2 | 106,2 |
| Linguagens e Códigos | 379,9 | 470,8 | 527,4 | 575,4 | 633,9 | 104,6 |
| Matemática | 378,5 | 447,4 | 529,0 | 622,1 | 754,5 | 174,7 |
| Redação | 300,0 | 540,0 | 620,0 | 780,0 | 920,0 | 240,0 |

(As quatro edições estão em `analises_av6.json`, chave `caixas`.)

## 5. Z-Score contra a curva normal

O Z-Score é exibido junto com o percentil, mas não pode substituí-lo. Se as notas
seguissem uma normal, o percentil seria Φ(z). A análise compara Φ(z) com o percentil
exato em todas as notas observadas, ponderando cada nota pelo número de pessoas.

| Edição | Área | Erro médio (pp) | Erro máximo (pp) | Assimetria | Curtose em excesso |
| --- | --- | --- | --- | --- | --- |
| 2019 | Matemática | 4,25 | 8,60 | 0,74 | 0,04 |
| 2021 | Matemática | 3,89 | 8,08 | 0,62 | −0,23 |
| 2022 | Matemática | 2,57 | 5,67 | 0,52 | −0,17 |
| 2022 | Ciências da Natureza | 3,00 | 5,95 | 0,59 | 0,29 |
| 2022 | Redação | 2,55 | 7,32 | −0,96 | 1,58 |
| 2022 | Ciências Humanas | 0,71 | 1,37 | −0,37 | 1,38 |

Exemplo: em Matemática 2019, a mediana real (497,4) está no percentil 50,0, mas a normal
a colocaria no percentil 41,6, um erro de 8,5 pontos percentuais no meio da
distribuição, onde está a maior parte dos participantes. A assimetria positiva de
Matemática e Ciências da Natureza (cauda longa para notas altas, efeito da TRI) é a causa.

Conclusão: a normal erraria até 8,6 pontos percentuais. Isso justifica com dados a
decisão do ADR-001 de calcular o percentil pela CDF exata e a regra de exibir o Z-Score
apenas como distância à média, separado do percentil (Plano de Trabalho, item 6).

## 6. Amostragem: o que uma amostra de 1% erraria

A ementa de Estatística I prevê amostragem aleatória simples, sistemática e
estratificada. O projeto não amostra, e esta análise quantifica o que se perderia se
amostrasse. Para 2022, foram sorteadas 200 amostras de 1% dos elegíveis (19.278 pessoas)
de duas formas: aleatória simples e estratificada por UF com alocação proporcional
(27 estratos, a partir de `dist_territorial.parquet`). Em cada amostra foram estimados
os quantis P10 a P90 e comparados com o valor da população. O sorteio é com reposição,
aproximação adequada para uma fração de 1%.

Matemática 2022 (erro do quantil estimado, em pontos de nota; 200 amostras):

| Quantil | População | Simples: erro médio | Simples: maior erro | Estratificada: erro médio | Estratificada: maior erro |
| --- | --- | --- | --- | --- | --- |
| P10 | 398,4 | 0,59 | 2,3 | 0,64 | 2,0 |
| P25 | 447,4 | 0,76 | 2,9 | 0,80 | 3,0 |
| P50 | 529,0 | 0,98 | 3,7 | 1,08 | 3,5 |
| P75 | 622,1 | 1,04 | 3,7 | 1,02 | 4,2 |
| P90 | 701,2 | 1,24 | 4,5 | 1,21 | 6,0 |

- A estratificação por UF não reduziu o erro: a UF explica pouco da variação das notas
  dentro de uma edição, e estratificar por uma variável pouco associada à nota não traz
  ganho de precisão. É um resultado esperado pela teoria de amostragem e agora medido.
- Na Redação, as notas são múltiplas de 20: o quantil estimado ou acerta a nota ou erra
  por 20 pontos (maior erro de 20 em todos os quantis até P75; erro médio de 1,2 a 4,4).

Para o produto, um ponto de nota no meio da distribuição de Matemática 2022 equivale a
cerca de 0,25 a 0,33 ponto percentual de posição (entre P10 e P75, medido na CDF exata),
e o Plano de Trabalho pede o percentil exato. Usar a
população inteira custa cerca de 2 minutos de processamento offline (relatório da AV3) e
elimina esse erro. A decisão de não amostrar fica justificada com números.

## 7. Drift entre edições

O produto nunca compara notas de edições diferentes (relatório da AV3, seção 2.5). A
análise mede o quanto as distribuições mudam de uma edição para outra com duas medidas
da aula de Data Drift (Engenharia de Dados e MLOps): o D de Kolmogorov-Smirnov, calculado
exatamente sobre as CDFs, e o PSI, com classes nos decis da edição de referência.

| Área | 2019→2020 | 2020→2021 | 2021→2022 | 2019→2022 |
| --- | --- | --- | --- | --- |
| Ciências da Natureza | D 0,067 · PSI 0,031 | D 0,022 · PSI 0,010 | D 0,060 · PSI 0,056 | D 0,122 · PSI 0,182 |
| Ciências Humanas | D 0,071 · PSI 0,069 | D 0,049 · PSI 0,016 | D 0,104 · PSI 0,108 | D 0,111 · PSI 0,080 |
| Linguagens e Códigos | D 0,066 · PSI 0,051 | D 0,124 · PSI 0,087 | D 0,098 · PSI 0,049 | D 0,058 · PSI 0,067 |
| Matemática | D 0,062 · PSI 0,044 | D 0,083 · PSI 0,106 | D 0,046 · PSI 0,021 | D 0,095 · PSI 0,048 |
| Redação | D 0,062 · PSI 0,048 | D 0,117 · PSI 0,119 | D 0,048 · PSI 0,019 | D 0,149 · PSI 0,118 |

**Leitura.** D é a maior diferença, num mesmo ponto de corte, entre as proporções de
participantes abaixo dele. Em Ciências da Natureza de 2019 para 2022, D = 0,122: existe
uma nota de corte em que a proporção abaixo dela difere 12,2 pontos percentuais entre as
duas edições. Pela convenção de mercado do PSI (abaixo de 0,1 estável; 0,1 a 0,25
moderado; acima de 0,25 grande), cinco das vinte comparações indicam mudança moderada e
nenhuma, mudança grande. Não há p-valor: com milhões de participantes, qualquer D seria
"significativo" (ver seção 3).

**Consequências para o produto:**

1. **Justificativa da regra.** Uma mesma nota ocupa posições diferentes conforme a
   edição: a mediana de Matemática passou de 497,4 em 2019 para 529,0 em 2022. Comparar
   uma nota com a distribuição de outra edição daria a posição errada. Por isso o usuário
   escolhe a edição e o particionamento por edição (ano=AAAA) é também uma fronteira
   estatística.
2. **Barreira de qualidade para edições futuras.** Quando o INEP publicar uma nova edição,
   rodar `scripts/analises_av6.py` com ela mostra se a distribuição está dentro da
   variação já observada entre 2019 e 2022 (D até 0,15 e PSI até 0,18 nas comparações
   desta tabela). Um valor muito acima disso não prova erro, mas exige investigar
   carga, filtro de elegibilidade ou mudança real do exame antes de publicar. É sinal de
   investigação, não de falha (Engenharia de Dados e MLOps, aula 10).

## 8. Referências

BUSSAB, Wilton O.; MORETTIN, Pedro A. *Estatística básica*. 9. ed. São Paulo: Saraiva, 2017.

DEVORE, Jay L. *Probabilidade e estatística para engenharia e ciências*. São Paulo: Cengage, 2011.

MCGRAW, Kenneth O.; WONG, S. P. A common language effect size statistic. *Psychological
Bulletin*, v. 111, n. 2, p. 361-365, 1992.
