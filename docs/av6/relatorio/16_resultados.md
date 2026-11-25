#C Resultados e validação da aplicação em nuvem | O que a aplicação publicada entrega, medido pelo link público

## Validação funcional pelo link público

A validação mais direta de um produto em nuvem é usá-lo pelo endereço público, como faria qualquer visitante, e conferir se o resultado coincide com o calculado de forma independente. A equipe fez isso nas quatro páginas, com o caso de referência do relatório (edição 2022, Matemática 650,0), e comparou cada número com o valor obtido diretamente dos artefatos pelo motor estatístico e, no caso do percentil nacional, com a conta feita à mão na seção 4.3.

!! Endereço validado: || <https://radarenem-projetoaplicado3-kirasapiens.replit.app>

Quadro: Resultados exibidos pelo link público no caso de referência (2022, Matemática 650,0)
Larguras: 22,40,20,18
| Página | Resultado exibido | Grupo (N) | Conferência |
| --- | --- | --- | --- |
| Início | Percentil 81,4%; Z +0,92 | Brasil (1.927.753) | Igual ao cálculo manual (seção 4.3) |
| Equidade, renda D | 87,1% na faixa R2; 41,3% no contraste; diferença de 45,8 pp; probabilidade de superioridade 18,9% | R2 (558.228); contraste (43.532) | Igual ao artefato |
| Recorte territorial, SC | 76,4% em SC; 77,8% na Região Sul; 81,4% no Brasil; 5,0 pp abaixo do Brasil; PS de SC 56,6% e da Região Sul 55,4%; 3ª maior mediana entre as 27 UFs | SC (43.658); Sul (211.210); Brasil (1.927.753) | Igual ao artefato |
| Capital escolar, pai e mãe E | 85,2% no nível E; 81,4% no Brasil | Nível E (729.727); Brasil (1.927.753) | Igual ao artefato |
Fonte: testes pelo link público em 19/11/2026 (beta), 24/11/2026 (identidade visual) e 24/11/2026 (Equidade, depois da última republicação); valores de referência calculados pela equipe sobre os artefatos da execução de referência.

Em todas as páginas, o percentil nacional foi o mesmo (81,4%), o que confirma que os quatro artefatos usam a mesma população: a auditoria de publicação já conferia que o total do Brasil é igual entre os artefatos (seção 3.11), e a tela confirma o mesmo fato de ponta a ponta.

A validação incluiu também os casos de erro: página sem nota ("Informe ao menos uma nota."), módulo sem o atributo escolhido, nota de redação fora dos múltiplos de 20 e entrada vazia em todos os campos. Nenhum deles derrubou a página ou mostrou detalhe técnico.

## Desempenho medido

As medições foram feitas em três ambientes, com instrumentos diferentes, e cada número é apresentado com o seu ambiente, para não comparar máquinas diferentes como se fossem a mesma.

Quadro: Medições de desempenho e de recursos da aplicação publicada
Larguras: 34,36,30
| Medida | Valor | Ambiente e instrumento |
| --- | --- | --- |
| Consulta p50 / p95, Início | 52 / 70 ms | Shell do Replit, `medir_desempenho.py`, 200 consultas |
| Consulta p50 / p95, Equidade | 179 / 255 ms | Idem |
| Consulta p50 / p95, Recorte territorial | 308 / 416 ms | Idem |
| Consulta p50 / p95, Capital escolar | 294 / 407 ms | Idem |
| Primeira abertura do Recorte territorial | 4,1 s, uma vez por processo | Idem |
| Memória da publicação | Pico de 838 MiB (40,9% de 2 GiB); média de 782 MiB | Painel de monitoramento do Replit, 19/11 |
| CPU da publicação | Média de 16,3%; pico de 50,0% da cota | Idem |
| Saúde pela rede, p50 / p95 | `/_stcore/health` 402 / 764 ms; página inicial 233 / 582 ms; 0 falhas em 40 | `checar_saude.py`, 19/11 |
| Saúde pela rede, p95 (republicação de 24/11) | `/_stcore/health` 732 ms; página inicial 593 ms; 0 falhas em 40 | `checar_saude.py`, 24/11 |
| Execução da página territorial com cache quente | 611 ms antes; 23 ms depois do pente fino | `AppTest` com 1 CPU, artefatos reais |
Fonte: `docs/deploy/replit.md` (tabela de medições), `docs/deploy/medicoes/` e `docs/qa/relatorio-qa-av6.md`.

**Leitura das medidas contra o RNF02 (até 3 s).** Todas as consultas ficaram abaixo de meio segundo no percentil 95, com folga de mais de sete vezes sobre a meta, numa máquina de 0,5 vCPU. A única operação acima de 3 s é a primeira abertura do Recorte territorial depois de cada publicação ou reinício, que carrega 2,2 milhões de linhas uma única vez por processo; o procedimento de publicação abre as quatro páginas logo depois de publicar para que nenhum visitante pague esse custo. No teste pelo link público de 24/11, a página da Equidade foi aberta logo depois de um reinício e mostrou por alguns segundos a mensagem de carregamento, exatamente a situação que o pente fino trocou por um texto legível ("Carregando os dados do ENEM...").

**Memória.** O pico de 838 MiB na VM publicada ficou em 41% dos 2 GiB. No Shell, com as quatro páginas no mesmo processo de medição, o pico foi de 1.310 MB, também dentro do limite. A VM dedicada (1 vCPU, 4 GB), prevista como primeira resposta a falta de memória (DL-08, item 5), não foi necessária. O cache sem cópia do pente fino reduz ainda o consumo por sessão, porque as sessões deixam de manter cópias próprias dos artefatos.

**Evolução entre ambientes.** No teste local de 03/11 (2 vCPU, versão anterior do Streamlit), a primeira abertura do territorial levou 10,4 s e as consultas, de 0,4 a 1,4 s; no ambiente de desenvolvimento de 16/11, 2,8 s e p95 até 370 ms; no Shell do Replit, 4,1 s e p95 até 416 ms. As diferenças refletem máquinas, versões e instrumentos diferentes e não devem ser lidas como ganho ou perda de uma mesma configuração; o que importa é que, no ambiente de produção, a meta foi atendida com folga.

## Disponibilidade e privacidade verificadas de fora

O `checar_saude.py` faz, de fora da plataforma, as duas perguntas que mais importam a um produto público com dados sensíveis: a aplicação está respondendo, e algum artefato pode ser baixado? Ele mede o tempo de resposta de `/_stcore/health` e da página inicial e tenta baixar os cinco artefatos por caminhos diretos e pelo servidor de estáticos, inclusive com `..` codificado.

Quadro: Verificações externas de saúde e privacidade
Larguras: 22,26,26,26
| Data | Requisições | Falhas | Artefatos expostos |
| --- | --- | --- | --- |
| 19/11/2026 (beta) | 40 | 0 | Nenhum |
| 24/11/2026 (PR #38) | 40 | 0 | Nenhum |
| 24/11/2026 (monitor do GitHub Actions, duas execuções) | 20 | 0 | Nenhum |
| A partir de 25/11/2026 | Monitor a cada 3 h | Histórico na aba Actions | Job falha se algum artefato for baixado |
Fonte: `docs/deploy/medicoes/` e workflow `monitor-producao.yml`.

A conferência manual de 24/11 confirmou também os cabeçalhos de segurança da plataforma (HSTS) e a proteção XSRF ativa, e que os caminhos dos artefatos e dos logotipos devolvem a página da aplicação, nunca o arquivo (seção 6.11).

## Resultados analíticos dos módulos

Além de validar a aplicação, a execução dos módulos sobre os microdados reais produziu resultados que respondem às perguntas do produto em escala nacional. São resultados descritivos sobre as populações elegíveis de cada edição.

### Equidade socioeconômica

Quadro: Mediana de Matemática por faixa de renda familiar
Larguras: 12,11,11,11,11,11,11,22
| Edição | R1 | R2 | R3 | R4 | R5 | R6 | Contraste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 456,5 | 485,3 | 525,3 | 571,1 | 624,2 | 687,9 | 690,3 |
| 2020 | 450,3 | 498,1 | 548,2 | 591,0 | 634,0 | 684,2 | 678,7 |
| 2021 | 463,4 | 499,8 | 540,7 | 582,2 | 628,1 | 678,6 | 671,9 |
| 2022 | 472,8 | 520,2 | 561,5 | 596,2 | 637,6 | 681,6 | 674,6 |
Fonte: `docs/modulos/equidade-resultados.md` (execução de 02/11/2026 sobre os microdados do INEP).

Nas 20 combinações de edição e área, a mediana cresce de R1 para R6 sem exceção. A probabilidade de superioridade da faixa mais baixa (R1, até 1 salário mínimo) contra o contraste fica entre 8,1% e 17,0% em todas as edições e áreas: sorteando uma pessoa de cada grupo, a da faixa R1 tem nota maior em menos de um par em cada cinco. Na faixa R6 (acima de 10 salários mínimos), o valor fica perto de 50% (46,8% a 54,5%): entre as famílias de maior renda, quem declarou escola privada quase não se distingue do restante da faixa. Parte da faixa R6 não declarou escola, porque concluiu o ensino médio antes, e essa diferença de composição impede leitura causal.

### Recorte territorial

O módulo publica 640 grupos de UF e região (32 por edição e área), além do Brasil. No exemplo de referência, Santa Catarina tem a 3ª maior mediana de Matemática entre as 27 UFs em 2022, e a mesma nota fica 5,0 pontos percentuais abaixo na UF do que no Brasil, porque a distribuição de Santa Catarina está deslocada para notas mais altas (mediana 563,4, contra 529,0 no Brasil). A auditoria dos limites de exibição, sobre os 640 grupos, registrou zero rótulos falsos e zero inversões de ordem; empates na mediana entre UFs ocorrem em 9 das 20 combinações de edição e área, incluindo as quatro da Redação.

### Capital escolar familiar

Quadro: Mediana de Matemática por nível de escolaridade dos responsáveis
Larguras: 12,10,11,10,10,10,10,27
| Edição | A | B e C | D | E | F | G | Brasil |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 436,7 | 462,0 | 479,5 | 502,0 | 572,8 | 611,4 | 497,4 |
| 2020 | 425,4 | 454,7 | 476,6 | 503,7 | 577,5 | 609,8 | 502,7 |
| 2021 | 442,4 | 466,5 | 483,6 | 508,4 | 576,5 | 607,3 | 513,1 |
| 2022 | 446,9 | 477,3 | 495,2 | 523,7 | 588,6 | 615,0 | 529,0 |
Fonte: `docs/modulos/capital-escolar-resultados.md` (execução de 10/11/2026 sobre os microdados do INEP).

Quadro: Posição da nota 650,0 em Matemática 2022 por nível de escolaridade
Larguras: 50,50
| Grupo | Percentil |
| --- | --- |
| Nível A (nunca estudou) | 96,9% |
| Nível B e C (Fundamental incompleto) | 93,5% |
| Nível D (Fundamental completo) | 90,7% |
| Nível E (Médio completo) | 85,2% |
| Nível F (Superior completo) | 68,8% |
| Nível G (Pós-graduação) | 60,8% |
| Brasil | 81,4% |
Fonte: `docs/modulos/capital-escolar-resultados.md`.

A mediana cresce a cada nível nas 20 combinações de edição e área, e o maior salto entre níveis vizinhos é a passagem do ensino médio completo para o superior completo (probabilidade de superioridade de F contra E entre 60,7% e 64,1%). Mesmo entre os extremos, os grupos se sobrepõem bastante: a probabilidade de superioridade do nível G contra o nível A fica entre 77,5% e 84,8%, de modo que, em 15% a 22% dos pares sorteados, a pessoa do nível A tem nota maior ou igual. Entre 2019 e 2022, o nível A caiu de 2,3% para 1,4% dos participantes com nível informado e o nível G subiu de 9,9% para 15,4%, mudança de composição de quem fez a prova que o módulo descreve sem indicar causa.

### Leitura conjunta

Os três módulos mostram o mesmo fenômeno por ângulos diferentes: a posição de uma nota depende do grupo de comparação, e os grupos diferem de forma sistemática. A mesma nota 650,0 em Matemática, em 2022, vai de 41,3% (entre participantes de escola privada de alta renda) a 96,9% (entre participantes cujos responsáveis nunca estudaram), com 81,4% na referência nacional. O produto entrega essa leitura em segundos, para qualquer nota, edição e grupo, com o tamanho do grupo sempre visível e sem atribuir causa.

## Atendimento aos requisitos

Quadro: Matriz final de atendimento aos requisitos com evidência medida
Larguras: 10,44,46
| Requisito | Critério verificado | Resultado |
| --- | --- | --- |
| RF01 | Entrada de notas e atributos nas quatro páginas | Atendido: formulários com as alternativas do questionário de cada edição |
| RF02 | Percentil, média, mediana, desvio, Z-Score e N | Atendido: todos exibidos na visão técnica; percentil conferido contra contagem direta (0,0 pp) |
| RF03 | Módulos autorais, um por integrante | Atendido: três módulos com regras, testes e tags individuais; quarto módulo cortado com registro (DL-07) |
| RF04 | Visualizações e explicações com limitações | Atendido: histogramas protegidos, curvas, caixa protegida, gráfico de pontos e blocos metodológicos |
| RF05 | Entradas inválidas e grupos insuficientes | Atendido: casos de erro testados e validados no link público |
| RF06 | Aplicação web pública | Atendido: link público desde 19/11/2026, sem cadastro |
| RNF01 | Runtime sem o CSV bruto | Atendido: 12,6 MB de artefatos em lugar de 7,51 GB |
| RNF02 | Consultas em até 3 s no ambiente-alvo | Atendido: p95 de 70 a 416 ms no Replit; só a primeira abertura do Recorte territorial depois de cada publicação ou reinício passa da meta (4,1 s, uma vez por processo, seção 7.2) |
| RNF03 | Pipeline reprodutível, testado e rastreável | Atendido: hash, manifestos com `run_id`, 282 testes, CI e PRs revisados |
| RNF04 | Não persistência da entrada | Atendido: sessão apenas, sem URL, log ou terceiros; teste automatizado |
| RNF05 | Segurança, acessibilidade, responsividade e monitoramento | Atendido: pip-audit, XSRF, nenhum artefato exposto, 0 violações WCAG 2.1 AA, telas de 375 px e monitor a cada 3 h; teste com usuários externos não realizado (DL-10) |
Fonte: elaborado pela equipe a partir das evidências dos capítulos 3 a 7.

## Atendimento aos objetivos do Plano de Trabalho

Quadro: Situação final dos objetivos específicos
Larguras: 6,34,14,46
| Nº | Objetivo | Situação | Observação |
| --- | --- | --- | --- |
| 1 | Profiling, contrato e dicionário | Atendido | Quatro edições caracterizadas; contrato de 76 colunas gerado de uma fonte única |
| 2 | Benchmark e justificativa da stack | Atendido | Cinco motores e quatro codecs medidos; a decisão mudou em relação ao Plano (DuckDB em vez de Polars) |
| 3 | Pipeline offline reprodutível | Atendido | RAW, TRUSTED e ANALYTICS com escrita atômica, funil, manifestos e barreira de publicação |
| 4 | Volumetria e desempenho | Atendido | Redução de 95,0%; pipeline em 112,3 s; consultas p95 até 416 ms na nuvem |
| 5 | Motor estatístico testado; inferência só quando pertinente | Atendido | Medidas exatas, decisão justificada de não usar testes de hipótese e quatro análises com dados reais |
| 6 | Módulos autorais | Atendido em parte | Três de quatro módulos; o mínimo de um por integrante foi cumprido e o corte foi registrado |
| 7 | Interface responsiva e acessível | Atendido | Duas visões, dois temas, celular e auditoria WCAG sem violações; falta o teste com usuários |
| 8 | Beta e versão pública estável com monitoramento | Atendido | Beta em 19/11, versão `v1.0` com monitor externo e não persistência |
| 9 | Gestão ágil e DataOps | Atendido em parte | PRs revisados, CI, Decision Log, ADR e tags; o quadro Kanban do GitHub Projects não foi mantido e a POC de nuvem atrasou |
| 10 | Documentação acadêmica coerente | Atendido | Relatórios da AV3, AV4 e AV6 com números rastreáveis até o código e os manifestos |
Fonte: elaborado pela equipe.

## Evidências de produto implantado

O checklist de aceitação de produto implantado resume o estado final.

Quadro: Checklist de produto implantado
Larguras: 44,18,38
| Evidência | Situação | Onde |
| --- | --- | --- |
| Dependências reprodutíveis e versões registradas | Atendido | `requirements.txt` fixo; CI com pip-audit |
| Pipeline com logs, contagens e recuperação | Atendido (offline) | Manifestos, funil, escrita atômica |
| Dados publicados conferidos antes de publicar | Atendido | `auditar_artefatos.py`, `_manifesto_publicacao.json` |
| Dados pessoais e acesso mínimo documentados | Atendido | `docs/privacidade.md`; projeto privado |
| Persistência fora do disco efêmero | Não se aplica | A aplicação não grava nada |
| Backup e restauração | Atendido em parte | Cópia dos artefatos e hashes; republicação medida; recriação do zero estimada |
| Métricas de disponibilidade, erro, latência e custo | Atendido | Monitor externo, medições no Replit, painel de cobrança |
| Documentação de arquitetura, responsáveis, fontes e limites | Atendido | Este relatório, Decision Log, `docs/av6/nuvem.md` |
| Modelo de ML com monitoramento e rollback | Não se aplica | O produto não usa modelo de aprendizado de máquina |
Fonte: `docs/av6/nuvem.md`, seção 8, atualizado com o pente fino.
