#C Metodologia estatística e rigor analítico de backend | Motor estatístico, regras dos módulos e análises com os dados reais

## População, e não amostra

A decisão estatística que orienta todas as outras é a natureza dos dados. Cada edição do ENEM entra inteira no produto: todos os participantes elegíveis (presentes nos dois dias e não treineiros) com nota na área, 9.214.868 pessoas nas quatro edições. As medidas exibidas são, portanto, **parâmetros populacionais calculados exatamente**, e não estimativas de uma amostra. Três consequências decorrem disso e são aplicadas no código:

- a variância usa divisor N, e não N − 1 (DL-01);
- o percentil vem da função de distribuição acumulada empírica exata, sem interpolação e sem aproximação por curva teórica (ADR-001);
- nenhuma medida exibida leva intervalo de confiança nem teste de significância, porque não há erro amostral a expressar (seção 4.6).

Os conceitos de população e amostra, medidas de posição e dispersão, histograma, boxplot e distribuição normal usados neste capítulo seguem a bibliografia do Plano de Trabalho (BUSSAB; MORETTIN, 2017; DEVORE, 2011).

## Motor estatístico

O motor estatístico está em `scripts/estatistica.py` e é compartilhado pelas quatro páginas. Todas as funções trabalham sobre a CDF exata de um grupo, representada como uma lista de triplas (nota, n, abaixo) ordenada por nota, sem nenhum dado individual. As somas de média e variância usam frações exatas (`fractions.Fraction`), de modo que uma distribuição de nota única dá variância exatamente zero, sem resíduo de ponto flutuante.

Quadro: Medidas calculadas pelo motor estatístico
Larguras: 22,48,30
| Medida | Definição | Função |
| --- | --- | --- |
| Percentil | (abaixo + iguais / 2) / N × 100, posto médio, sem interpolação | `percentil_exato_acumulado`, `dobro_posicao` |
| Média e variância | Momentos populacionais (divisor N), somas em frações | `resumo` |
| Desvio-padrão | Raiz da variância populacional | `resumo` |
| Quantis (mediana, quartis, P5, P95) | Menor nota observada com pelo menos p · N participantes nela ou abaixo | `quantil` |
| Z-Score | (nota − média) / desvio; indefinido se o desvio for zero | `z_score` |
| Probabilidade de superioridade | P(A > B) + 0,5 · P(A = B), igual a U / (n_A · n_B) | `prob_superioridade` |
| Caixa protegida | Q1, mediana, Q3, IQR e bigodes em P5 e P95, só com N ≥ 2.000 | `caixa_protegida` |
| Distância de Kolmogorov-Smirnov | Máximo de \|F_A(x) − F_B(x)\| | `ks_distancia` |
| PSI | Σ (a − r) · ln(a / r), com classes nos decis da referência | `psi` |
| Limites de exibição | Bordas do percentil exibível em grupos de UF, região, renda e escolaridade | `limites_exibicao`, `exibir_percentil` |
Fonte: `scripts/estatistica.py` e `docs/av6/estatistica.md`, seção 2.

A moda, prevista no Plano "quando pertinente", não é exibida. Nas quatro áreas objetivas a nota vem da TRI, com mais de seis mil valores distintos por edição, e a moda seria uma nota qualquer com poucas pessoas a mais que as vizinhas. Na redação, cujas notas são múltiplas de 20, ela seria interpretável, mas não responde à pergunta do produto, que é a posição de uma nota.

## Percentil exato por posto médio

### A decisão do ADR-001

O MVP da AV2 calculava a posição interpolando dentro de faixas de pelo menos 100 participantes, o que dava uma aproximação com erro de até 0,0047 ponto percentual. O Plano de Ensino pede percentis populacionais exatos, e a equipe preferiu não declarar como exato um valor aproximado. O ADR-001 (`docs/av3/DECISAO-001-percentil-exato.md`) manteve as faixas protegidas para os histogramas e acrescentou a CDF exata, de uso exclusivo do backend, com o percentil dado por:

```
percentil(x) = ( abaixo(x) + 0,5 × iguais(x) ) / N × 100
```

em que `abaixo(x)` é o número de participantes com nota estritamente menor que x, `iguais(x)` é o número com nota exatamente igual e N é o total do grupo. É a regra do posto médio: quem tirou a mesma nota do usuário conta pela metade, de modo que o percentil de uma nota observada é a média entre a proporção estritamente abaixo e a proporção até ela. Para uma nota não observada, `iguais(x)` é zero e vale a contagem estritamente inferior, sem interpolação. A posição na CDF é encontrada por busca binária, em tempo logarítmico, o que levou 0,11 ms por consulta na medição da AV3.

### Exemplo com os dados reais

Na edição de 2022, a CDF nacional de Matemática tem 6.369 notas distintas e N = 1.927.753 participantes elegíveis. Para a nota 650,0:

- participantes com nota menor que 650,0: abaixo = 1.568.849;
- participantes com nota igual a 650,0: iguais = 374;
- percentil = (1.568.849 + 0,5 × 374) / 1.927.753 × 100 = 1.569.036 / 1.927.753 × 100 = **81,39%**, exibido como 81,4%;
- média do grupo 542,09 e desvio-padrão 117,41, logo Z = (650,0 − 542,09) / 117,41 = **+0,92**.

É exatamente o que a página inicial mostra (seção 5.2) e o que o link público devolveu na validação (seção 7.1).

### Conferência contra o dado individual

A exatidão da CDF não é presumida: o ETL compara o percentil calculado pela CDF com uma contagem direta, em SQL, sobre os registros individuais da TRUSTED, para um conjunto de notas de cada edição e área que inclui os extremos, a mediana, uma nota não observada e valores fora do intervalo. Em todas as execuções com os microdados reais (13/10/2026 no pipeline nacional e 02/11 e 10/11/2026 nos módulos), a maior divergência foi **0,0 ponto percentual**, e o manifesto registra esse resultado.

## Convenções do motor

O contrato do motor estatístico v1 deixou três convenções para aceite do PO, registradas na DL-01:

- **Variância populacional** (divisor N). Cada edição é o conjunto completo dos elegíveis. Com o piso de 100 participantes, a diferença para o divisor N − 1 seria de no máximo 0,5% do desvio-padrão.
- **Mediana inferior.** A mediana é a menor nota observada em que abaixo + n ≥ 0,5 · N. Com N par e as duas notas centrais diferentes, é a de baixo, e não a média das duas. Assim a mediana é sempre uma nota que algum participante realmente obteve, e segue a mesma regra de todos os quantis do motor. Quem compara com `numpy.median` deve esperar essa diferença, documentada e testada (`test_mediana_com_n_par_e_a_nota_inferior`).
- **Arredondamento só na exibição.** As funções não arredondam. A interface mostra percentil, notas, média e mediana com uma casa decimal, Z-Score com duas e probabilidade de superioridade em porcentagem com uma casa.

## Probabilidade de superioridade como tamanho de efeito

### Definição

A comparação entre dois grupos (faixa de renda contra o contraste, UF contra o restante do país, nível de escolaridade contra o vizinho) é feita pela probabilidade de superioridade:

```
PS(A, B) = P(nota de A > nota de B) + 0,5 × P(nota de A = nota de B)
```

Sorteando uma pessoa de cada grupo, é a chance de a do primeiro ter nota maior, com o empate contando metade. É o tamanho de efeito de "linguagem comum" proposto por McGraw e Wong (1992), equivale à estatística U de Mann-Whitney dividida por n_A · n_B e à área sob a curva ROC que separa os dois grupos. Vale 50% quando os grupos são equivalentes e se afasta de 50% à medida que as distribuições se separam. A função `prob_superioridade` calcula o valor exato, sem amostragem de pares: para cada nota de A, conta por busca binária quantas pessoas de B ficam abaixo e quantas empatam, acumulando o dobro de U em inteiros para não perder precisão.

### Exemplo de cálculo

O exemplo da DL-04, reproduzível com as funções do módulo territorial: a UF tem as notas {500, 500, 600} e o Brasil, {500, 500, 500, 600, 700}. O restante do país, sem a UF, é {500, 700}. São 3 × 2 = 6 pares. A UF vence em 1 par (600 contra 500) e empata em 2 (500 contra 500). PS = (1 + 0,5 × 2) / 6 = **0,333**.

### Por que o restante do país, e não o Brasil inteiro

No módulo territorial, a UF e a região são comparadas com o Brasil **sem elas mesmas** (DL-04, item 9). Comparar uma UF com o Brasil inteiro colocaria a UF dos dois lados da comparação e puxaria o valor para 50%, sobretudo em São Paulo, que concentra cerca de 16% dos participantes. A função `restante` subtrai a CDF da UF da CDF do Brasil e levanta erro se alguma nota da UF tiver frequência maior que a do Brasil, o que impede calcular a medida sobre artefatos inconsistentes.

## Por que não há testes de hipótese nem intervalos de confiança

O Plano de Trabalho (objetivo 5) restringe intervalos de confiança e testes de hipótese aos casos em que são metodologicamente pertinentes e têm premissas explícitas. O Radar ENEM não é um desses casos, por três razões.

- **Os grupos são populações completas.** A pergunta "a diferença existe na população?" já está respondida pelo próprio cálculo: a probabilidade de superioridade de 18,9% entre a faixa de renda R2 e o contraste, em Matemática 2022, é o valor da população elegível daquela edição, e não uma estimativa.
- **O teste não discriminaria nada.** Com grupos de dezenas de milhares a milhões de pessoas, o teste de Mann-Whitney rejeitaria a igualdade para qualquer diferença, por menor que fosse, e o p-valor seria praticamente zero em todas as comparações. Ele não separaria uma diferença relevante de uma irrelevante.
- **Um intervalo exigiria outra leitura do dado.** Só faria sentido tratar a edição como amostra de uma "superpopulação" de edições possíveis, leitura que o produto não adota e que não é necessária para a pergunta do usuário.

Por isso o produto informa o **tamanho** da diferença, em pontos percentuais e em probabilidade de superioridade, e não sua significância. Nenhuma medida é apresentada como efeito causal da renda, do território ou da escolaridade dos pais: as DLs de cada módulo registram a leitura causal como fora do escopo, e a interface diz isso ao usuário.

## Privacidade estatística

Um motor que responde à posição exata de qualquer nota digitada pode, se usado sem cuidado, revelar informação sobre poucas pessoas. O projeto trata esse risco com quatro mecanismos complementares, todos implementados no backend.

### Piso de 100 participantes

Nenhum grupo de comparação, célula de tabela exibida ou barra de histograma com menos de 100 participantes é publicado (`PISO_GRUPO`, regra R3). O valor foi aceito pelo PO junto com o ADR-001 e a DL-04 e dá folga sobre o mínimo estatístico usual de 30. Abaixo do piso, a interface mostra "grupo insuficiente" e não calcula o cenário. Os histogramas usam as faixas protegidas de `dist_notas.parquet`, nunca a CDF.

### Limites de exibição do percentil

O problema foi identificado no módulo territorial (DL-04, item 8). Média, mediana e desvio são fixos por grupo, mas o percentil muda com a nota digitada. Quem testa notas vizinhas nas pontas de uma UF pequena pode descobrir a nota de uma única pessoa. Em Roraima, Matemática 2022 (N = 3.984), a mudança de posição entre duas notas vizinhas nos extremos revela a nota de um participante.

A regra adotada, com uma casa decimal e piso de 100, é:

```
limite superior = piso( 1000 × (N − 100) / N ) décimos de ponto
limite inferior = teto( 1000 × 100 / N )      décimos de ponto
```

Se o percentil passar do limite superior, a interface mostra "acima de X%"; se ficar abaixo do inferior, "abaixo de X%"; nos demais casos, o percentil exato. Em Roraima, Matemática 2022: superior = piso(1000 × 3.884 / 3.984) = 974, ou seja, 97,4%; inferior = teto(100.000 / 3.984) = 26, ou seja, 2,6%. Três decisões de implementação garantem a correção da regra:

- **comparar o percentil, e não contar pessoas acima**, porque com empates a contagem gera rótulos falsos (em Minas Gerais, Redação 2020, 1.820 pessoas empatadas em 980 e uma acima: a posição real é 99,59%, abaixo do limite de 99,9%, e a regra por contagem diria "acima de 99,9%");
- **comparar com o limite já arredondado**, porque com o limite sem arredondar 281 dos 640 grupos exibiriam uma nota maior com posição menor; com o limite arredondado, zero inversões;
- **conta em inteiros**, comparando 1000 × o dobro da posição com o limite × 2N, para que nenhum erro de ponto flutuante desloque a borda.

A mesma função (`exibir_percentil`, em `scripts/estatistica.py`) é usada pelos três módulos (DL-03, item 10; DL-05, item 13). O percentil nacional continua exato, como decidido no ADR-001: saber a posição de uma nota entre quase dois milhões de pessoas não isola ninguém. A auditoria dos limites sobre os dados reais (`scripts/auditoria_limites.py`, 640 grupos, notas de 0 a 1.000 de 0,1 em 0,1) confirmou zero rótulos falsos e zero inversões, e reduziu em 10% as mudanças de posição atribuíveis a uma única pessoa; o risco residual no meio da distribuição de grupos pequenos foi aceito pelo PO em 03/11/2026, com os motivos registrados na DL-04.

### Dependência entre medidas

Quando um dos dois percentis de uma comparação está em limite, a diferença entre eles não é exibida: somada à posição exata do outro grupo, ela devolveria o valor escondido (DL-04, item 8.7; DL-03, item 10). A probabilidade de superioridade continua exibida, porque compara os dois grupos inteiros e não depende da nota digitada.

### Caixa protegida no boxplot

O Plano prometia boxplots e quartis, e a AV6 os acrescentou à página inicial. No boxplot clássico, o mínimo, o máximo e os pontos discrepantes são notas de pessoas isoladas, o que contraria o piso. Na caixa protegida, os bigodes param nos percentis 5 e 95, não há pontos soltos e a caixa só existe quando 5% do grupo chega ao piso, ou seja, com N ≥ 2.000. O teste `test_bigodes_deixam_pelo_menos_o_piso_de_fora` garante que pelo menos 100 pessoas ficam além de cada bigode.

Quadro: Quartis nacionais de 2022 usados na caixa protegida
Larguras: 25,12,12,13,12,13,13
| Área | P5 | Q1 | Mediana | Q3 | P95 | IQR |
| --- | --- | --- | --- | --- | --- | --- |
| Ciências da Natureza | 396,8 | 440,8 | 486,7 | 545,6 | 629,9 | 104,8 |
| Ciências Humanas | 391,7 | 479,5 | 532,5 | 585,7 | 659,2 | 106,2 |
| Linguagens e Códigos | 379,9 | 470,8 | 527,4 | 575,4 | 633,9 | 104,6 |
| Matemática | 378,5 | 447,4 | 529,0 | 622,1 | 754,5 | 174,7 |
| Redação | 300,0 | 540,0 | 620,0 | 780,0 | 920,0 | 240,0 |
Fonte: `docs/av6/analises_av6.json` (chave `caixas`), calculado sobre `dist_exata.parquet` da execução de referência.

## Regras de negócio dos módulos autorais

Cada módulo tem regras registradas no Decision Log antes do código, com o autor como responsável e o aceite do PO. O quadro reúne as regras que afetam o cálculo.

Quadro: Regras dos três módulos autorais
Larguras: 16,28,28,28
| Regra | Equidade socioeconômica (DL-03) | Recorte territorial (DL-04) | Capital escolar familiar (DL-05) |
| --- | --- | --- | --- |
| Autor | Samuel Silva de Rezende | Vinícius Joacir dos Anjos | Guilherme da Silva Anselmo |
| Variável do INEP | `Q006` (renda familiar) e `TP_ESCOLA` | `SG_UF_PROVA` (UF do local de prova) | `Q001` (pai) e `Q002` (mãe) |
| Grupos | Seis faixas em salários mínimos (R1 a R6) e o contraste: escola privada com renda acima de 10 SM | 27 UFs, 5 regiões do IBGE e Brasil | Nível A; B e C; D; E; F; G (maior escolaridade entre pai e mãe) |
| Por que esses grupos | As 17 alternativas soltas teriam faixas altas com 0,6% a 1,7% dos inscritos; seis faixas mantêm o gradiente | A UF da escola falta para 64% a 76% dos elegíveis; município ficaria abaixo do piso e permitiria dedução por diferença | B e C significam "não terminou o Fundamental"; pares pai × mãe dariam 64 combinações com células pequenas |
| Ausências | `Q006` vazia ou inválida: fora das faixas, mantém a posição nacional | UF vazia ou inválida: fora de todos os grupos (nenhum caso nos dados reais) | "Não sei" ou vazio nos dois: só posição nacional; campo inválido contamina o registro |
| Comparação | Faixa contra o contraste | UF, região e Brasil lado a lado; UF e região contra o restante do país | Mesmo nível; outro nível opcional, o vizinho de cima (ou de baixo, no nível G) |
| Medidas | Percentil, média, mediana, desvio, Z, N, diferença em pp e PS | As mesmas e a posição da mediana da UF entre as 27 | As mesmas |
| Artefato | `dist_equidade.parquet`, 140 grupos | `dist_territorial.parquet`, 32 grupos por edição e área mais o Brasil | `dist_capital.parquet`, 140 grupos |
| Fora do escopo | Renda per capita, cruzamento com UF ou cor e leitura causal | Município, UF da escola e cruzamentos | Pares pai × mãe e leitura causal |
Fonte: Decision Log (DL-03, DL-04 e DL-05) e relatórios de execução dos módulos.

Três pontos das regras merecem destaque metodológico. No módulo de Equidade, o grupo de contraste é o único cruzamento de duas variáveis do produto (escola × renda); a exceção foi aceita porque o grupo é fixo (o usuário não escolhe o cruzamento), é grande (36 mil a 50 mil participantes por edição e área) e passa pelo mesmo piso. No módulo territorial, a UF de prova foi escolhida porque está preenchida para 100% dos elegíveis, e a interface pergunta "Em qual UF você fez a prova?", e não "onde você mora". No módulo de Capital escolar, a regra "vale o maior nível informado entre pai e mãe" tem uma limitação conhecida e exibida: com pai "Não sei" e mãe no nível A, o participante entra no nível A, embora o pai possa ter escolaridade maior; o "Não sei" aparece de 3 a 4 vezes mais na pergunta sobre o pai.

## Análise 1: a curva normal no lugar do percentil exato

O Z-Score é exibido junto com o percentil, mas não pode substituí-lo. Se as notas seguissem uma distribuição normal, o percentil seria Φ(z). A análise `scripts/analises_av6.py` compara Φ(z) com o percentil exato em todas as notas observadas de cada edição e área, ponderando cada nota pelo número de pessoas.

Quadro: Erro do percentil pela curva normal em relação ao percentil exato
Larguras: 11,24,15,15,15,20
| Edição | Área | Erro médio (pp) | Erro máximo (pp) | Assimetria | Curtose em excesso |
| --- | --- | --- | --- | --- | --- |
| 2019 | Matemática | 4,25 | 8,60 | 0,74 | 0,04 |
| 2021 | Matemática | 3,89 | 8,08 | 0,62 | −0,23 |
| 2022 | Matemática | 2,57 | 5,67 | 0,52 | −0,17 |
| 2022 | Ciências da Natureza | 3,00 | 5,95 | 0,59 | 0,29 |
| 2022 | Redação | 2,55 | 7,32 | −0,96 | 1,58 |
| 2022 | Ciências Humanas | 0,71 | 1,37 | −0,37 | 1,38 |
Fonte: `docs/av6/analises_av6.json`, gerado em 16/11/2026 sobre os artefatos da execução de referência (SHA-256 das entradas no próprio arquivo).

Figura: f_normal.png | 14 | Percentil exato e percentil pela curva normal, Matemática 2019
Fonte: elaborado pela equipe a partir de `dist_exata.parquet` (percentil calculado em notas de 2 em 2 pontos, de 320 a 860).

Em Matemática 2019, a mediana real (497,4) está no percentil 50,0, mas a curva normal com a mesma média (520,7) e o mesmo desvio (109,2) a colocaria no percentil 41,6, um erro de 8,5 pontos percentuais exatamente no meio da distribuição, onde está a maior parte dos participantes. A causa é a assimetria positiva de Matemática e Ciências da Natureza, com cauda longa para as notas altas, efeito da TRI. Na Redação, a assimetria é negativa e a curtose alta, porque há concentração de notas altas e um grupo de notas zero.

A conclusão justifica com dados duas decisões: calcular o percentil pela CDF exata (ADR-001) e exibir o Z-Score apenas como distância à média, em desvios-padrão, separado do percentil e sem conversão pela curva normal (indicador IND-04, seção 5.6).

## Análise 2: o que uma amostra de 1% erraria

O produto não amostra, e esta análise quantifica o que se perderia se amostrasse, com os dois desenhos amostrais mais comuns: aleatório simples e estratificado. Para 2022, foram sorteadas 200 amostras de 1% dos elegíveis (19.278 pessoas) de duas formas: aleatória simples e estratificada por UF com alocação proporcional (27 estratos). Em cada amostra foram estimados os quantis P10 a P90 e comparados com o valor da população. O sorteio é com reposição, aproximação adequada para uma fração de 1%, e usa semente fixa para ser reproduzível.

Quadro: Erro dos quantis estimados com amostras de 1%, Matemática 2022 (pontos de nota, 200 amostras)
Larguras: 12,14,18,18,19,19
| Quantil | População | Simples: erro médio | Simples: maior erro | Estratificada: erro médio | Estratificada: maior erro |
| --- | --- | --- | --- | --- | --- |
| P10 | 398,4 | 0,59 | 2,3 | 0,64 | 2,0 |
| P25 | 447,4 | 0,76 | 2,9 | 0,80 | 3,0 |
| P50 | 529,0 | 0,98 | 3,7 | 1,08 | 3,5 |
| P75 | 622,1 | 1,04 | 3,7 | 1,02 | 4,2 |
| P90 | 701,2 | 1,24 | 4,5 | 1,21 | 6,0 |
Fonte: `docs/av6/analises_av6.json` (chave `amostragem`).

Dois resultados merecem leitura. Primeiro, a estratificação por UF não reduziu o erro. A teoria de amostragem prevê ganho de precisão quando a variável de estratificação está associada à variável medida, e a UF explica pouco da variação das notas dentro de uma edição; o resultado esperado pela teoria ficou agora medido. Segundo, na Redação, cujas notas são múltiplas de 20, o quantil estimado ou acerta a nota ou erra por 20 pontos (maior erro de 20 em todos os quantis até P75; erro médio de 1,2 a 4,4).

Para o produto, um ponto de nota no meio da distribuição de Matemática 2022 equivale a cerca de 0,25 a 0,33 ponto percentual de posição (entre P10 e P75, medido na CDF exata). Usar a população inteira custa cerca de dois minutos de processamento offline e elimina esse erro. A decisão de não amostrar fica justificada com números, e não só pelo enunciado do Plano.

## Análise 3: mudança das distribuições entre edições

O produto nunca compara notas de edições diferentes. A análise mede o quanto as distribuições mudam de uma edição para outra com duas medidas usuais de monitoramento de mudança de dados (*data drift*): a distância D de Kolmogorov-Smirnov, calculada exatamente sobre as CDFs, e o PSI, com classes nos decis da edição de referência.

Quadro: Mudança das distribuições entre edições (D de Kolmogorov-Smirnov e PSI)
Larguras: 20,20,20,20,20
| Área | 2019→2020 | 2020→2021 | 2021→2022 | 2019→2022 |
| --- | --- | --- | --- | --- |
| Ciências da Natureza | D 0,067 · PSI 0,031 | D 0,022 · PSI 0,010 | D 0,060 · PSI 0,056 | D 0,122 · PSI 0,182 |
| Ciências Humanas | D 0,071 · PSI 0,069 | D 0,049 · PSI 0,016 | D 0,104 · PSI 0,108 | D 0,111 · PSI 0,080 |
| Linguagens e Códigos | D 0,066 · PSI 0,051 | D 0,124 · PSI 0,087 | D 0,098 · PSI 0,049 | D 0,058 · PSI 0,067 |
| Matemática | D 0,062 · PSI 0,044 | D 0,083 · PSI 0,106 | D 0,046 · PSI 0,021 | D 0,095 · PSI 0,048 |
| Redação | D 0,062 · PSI 0,048 | D 0,117 · PSI 0,119 | D 0,048 · PSI 0,019 | D 0,149 · PSI 0,118 |
Fonte: `docs/av6/analises_av6.json` (chave `drift`).

Figura: f_drift.png | 14 | Percentil de cada nota de Matemática na própria edição, de 2019 a 2022
Fonte: elaborado pela equipe a partir de `dist_exata.parquet` (percentil calculado em notas de 2 em 2 pontos).

D é a maior diferença, num mesmo ponto de corte, entre as proporções de participantes abaixo dele. Em Ciências da Natureza de 2019 para 2022, D = 0,122: existe uma nota de corte em que a proporção abaixo dela difere 12,2 pontos percentuais entre as duas edições. Pela convenção de mercado do PSI (abaixo de 0,1 estável; de 0,1 a 0,25 moderado; acima de 0,25 grande), cinco das vinte comparações indicam mudança moderada e nenhuma, mudança grande. Como na seção 4.6, não há p-valor: com milhões de participantes, qualquer D seria "significativo".

As consequências para o produto são duas.

- **Justificativa da regra de comparar só dentro da edição.** Uma mesma nota ocupa posições diferentes conforme a edição. A nota 650 em Matemática fica no percentil 85,8 em 2019, 85,3 em 2020, 82,5 em 2021 e 81,4 em 2022, e a mediana passou de 497,4 em 2019 para 529,0 em 2022. Comparar uma nota com a distribuição de outra edição daria a posição errada. Por isso o usuário escolhe a edição, e a partição física por edição (`ano=AAAA`) é também uma fronteira estatística.
- **Barreira de qualidade para edições futuras.** Quando o INEP publicar uma nova edição, rodar `scripts/analises_av6.py` com ela mostra se a distribuição está dentro da variação já observada entre 2019 e 2022 (D até 0,15 e PSI até 0,18). Um valor muito acima disso não prova erro, mas exige investigar a carga, o filtro de elegibilidade ou uma mudança real do exame antes de publicar. É um sinal para investigação, e não uma falha automática.

## Validação do backend

### Testes automatizados

O repositório tem 282 testes automatizados, todos com dados sintéticos de resultado conhecido, gerados em tempo de execução. Eles rodam sem os microdados, em qualquer máquina e no CI.

Quadro: Testes automatizados por arquivo
Larguras: 30,10,60
| Arquivo | Testes | O que garantem |
| --- | --- | --- |
| `test_motor.py` | 16 | Medidas v1: média, variância, mediana inferior, quantis, Z-Score e probabilidade de superioridade |
| `test_percentil_exato.py` | 4 | Empates, nota não observada, limites e frequências inválidas na CDF |
| `test_estatistica_av6.py` | 14 | Caixa protegida, bigodes que deixam o piso de fora, KS, PSI e percentil pela normal |
| `test_etl.py` | 9 | Identificador fora da TRUSTED, elegibilidade, funil, CSV de outra edição e faixas com piso |
| `test_analytics.py` | 10 | Ponta a ponta: RAW sintético → TRUSTED → ANALYTICS comparado com cálculo independente; idempotência, `run_id` e falha sem publicação parcial |
| `test_auditar_artefatos.py` | 5 | A barreira de publicação aceita artefatos válidos e recusa chave repetida, CDF incoerente, grupo abaixo do piso, Brasil diferente entre artefatos e artefato ausente |
| `test_equidade.py` | 49 | Regras da DL-03, limites de exibição e página do módulo |
| `test_territorial.py` | 59 | Regras da DL-04, restante do país, posição da mediana, limites e casos de erro da página |
| `test_capital_escolar.py` | 70 | Regras da DL-05, maior nível, "Não sei", campo inválido, vizinho e página |
| `test_modulos_independentes.py` | 3 | Os módulos não importam a lógica uns dos outros (autoria da AV4) |
| `test_app.py` | 6 | Página inicial: percentil exibido, grupo insuficiente, visões simples e técnica, caixa protegida e notas fora da URL |
| `test_ui.py` | 37 | Contraste das cores nos dois temas, cache sem cópia, identidade visual e texto alternativo |
| **Total** | **282** | Todos passando no CI e localmente com o Streamlit 1.66.1 |
Fonte: contagem dos métodos de teste em `tests/` na branch do PR #39 e execução de `python -m unittest discover -s tests`.

A cobertura de linhas do núcleo do produto (app, motor estatístico, três módulos, ETL e auditoria) é de 95% (2.176 linhas, 119 sem execução); por página do app, vai de 93% a 98%. A cobertura do repositório inteiro é de 58%, porque os scripts de uso único (benchmark, profiling, dicionário e contrato) e os que dependem de rede (`checar_saude.py`) não têm teste automatizado.

### Casos de erro

Cada página trata as entradas inválidas sem quebrar: nenhuma nota informada ("Informe ao menos uma nota."), atributo do módulo não escolhido, nota de redação que não é múltipla de 20, nota fora de 0 a 1.000 (o próprio campo limita), grupo abaixo do piso ("grupo insuficiente"), grupo com todas as notas iguais (Z-Score "indefinido", com aviso) e nota acima da maior observada (posição calculada sem exceção). Cada caso tem teste próprio, e as mensagens mostram apenas o tipo do erro, nunca o valor digitado (`showErrorDetails = "type"`).

## Arquitetura do backend em execução

O backend roda no mesmo processo do Streamlit. Três decisões de implementação sustentam o desempenho e a segurança.

- **Leitura parametrizada.** O app lê cada artefato uma vez, com DuckDB, por uma consulta parametrizada (`read_parquet(?)`). Nenhum valor digitado entra em SQL: as notas só entram em funções Python de cálculo.
- **Cache compartilhado e somente leitura.** Os artefatos são carregados com `st.cache_resource`, que guarda um único objeto para todas as sessões. Até a AV6 era usado `st.cache_data`, que devolve uma cópia (via pickle) a cada chamada; como o Streamlit reexecuta a página a cada clique, o app copiava até 37 MB por interação e por sessão. A troca reduziu a execução da página territorial de 611 ms para 23 ms (seção 6.10). Para que nenhum código altere o objeto compartilhado por engano, o que afetaria todos os visitantes, a função `ui.congelar()` o congela em todos os níveis (dicionários viram `MappingProxyType`, listas viram tuplas e qualquer tipo mutável desconhecido é recusado), e os testes de `TestCacheSemCopia` conferem que nenhum nível pode ser alterado e que nenhuma página volta a usar `cache_data` nos artefatos.
- **Separação entre lógica e interface.** As regras de cada módulo estão em `scripts/equidade.py`, `scripts/territorial.py` e `scripts/capital_escolar.py`, testáveis sem o Streamlit; as funções compartilhadas de exibição foram extraídas dos módulos para `scripts/estatistica.py` no PR #17, e o teste `test_modulos_independentes.py` impede que um módulo importe a lógica de outro.
