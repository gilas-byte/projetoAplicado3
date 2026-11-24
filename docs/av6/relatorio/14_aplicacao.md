#C Aplicação web | Interface, visualizações, acessibilidade e privacidade na tela

## Organização da interface

A interface tem uma barra lateral fixa e uma coluna central de conteúdo. A barra lateral traz o logotipo do Radar ENEM no topo, a navegação entre as quatro páginas, o interruptor de modo escuro e, no pé, o logotipo da KiraSapiens Neurotech, startup do PO. A navegação nativa do Streamlit foi substituída por uma navegação própria (`app/ui.py`), porque a nativa chamava a página principal de "app". Cada página segue a mesma ordem: título, pergunta do módulo em uma frase, edição de comparação, formulário, resultado em duas abas, bloco "Como a comparação é feita" e rodapé com a fonte dos dados, a data da conferência dos artefatos e o commit do código.

As capturas deste capítulo foram feitas em 24/11/2026 com o código do PR #39 (pente fino) rodando sobre os cinco artefatos reais da execução de referência, os mesmos publicados no Replit (hashes conferidos pela auditoria). Todas usam a edição de 2022 e a nota 650,0 em Matemática, o exemplo usado ao longo do relatório; a página inicial também mostra a Redação 760.

## Página inicial

A página inicial responde à pergunta mais simples: em que posição a nota fica entre todos os participantes elegíveis da edição. O usuário informa de uma a cinco notas.

Figura: g_inicio.png | 16 | Página inicial (2022, Matemática 650,0 e Redação 760): à esquerda, o formulário e o resultado na visão simples; à direita, a visão técnica (histograma protegido e caixas) e o bloco "Como a posição é calculada"
Fonte: capturas do Radar ENEM feitas pela equipe em 24/11/2026, com os artefatos gerados a partir dos Microdados do ENEM 2022 (INEP).

A visão simples traduz cada percentil em frequência natural ("Sua nota foi maior que a de 81,4% dos participantes: cerca de 81 em cada 100") e numa barra de 0 a 100%, em que a parte colorida é o grupo que tirou nota menor. A visão técnica mostra, para cada área, o cartão com o percentil, o histograma das notas com a nota do usuário marcada por uma linha tracejada, o N do grupo, os quartis e a mediana, e, ao final, a caixa protegida de todas as áreas informadas.

O histograma é desenhado a partir das faixas de pelo menos 100 participantes de `dist_notas.parquet`, nunca da CDF; as barras à direita da nota do usuário aparecem em tom mais claro. A caixa protegida mostra Q1, mediana e Q3, com os bigodes nos percentis 5 e 95 e a nota do usuário marcada por um losango; o texto abaixo do gráfico explica por que o mínimo, o máximo e os pontos isolados não são desenhados.

O bloco metodológico, presente em todas as páginas, informa quem entra na comparação, como o percentil e os quartis são calculados, como a privacidade é protegida, o que o resultado não significa e qual é a fonte dos dados. É a forma de cumprir o RF04 sem exigir que o usuário leia este relatório.

## Módulo Equidade socioeconômica

O módulo de Samuel Silva de Rezende compara a mesma nota em dois cenários: entre participantes da mesma faixa de renda familiar e entre participantes de escola privada com renda familiar acima de 10 salários mínimos. O usuário escolhe a alternativa da pergunta de renda com o texto e os valores em reais do questionário da edição escolhida.

Figura: g_equidade.png | 16 | Módulo Equidade socioeconômica (renda "D", mais de 1 até 2 SM; Matemática 650,0; 2022): à esquerda, o resultado; à direita, a visão técnica
Fonte: capturas do Radar ENEM feitas pela equipe em 24/11/2026, com `dist_equidade.parquet` gerado a partir dos Microdados do ENEM 2022 (INEP).

O resultado abre com o anel do percentil na faixa do usuário (87,1%, entre 558.228 participantes) e dois cartões: a posição na própria faixa e a posição entre os participantes de escola privada de alta renda (41,3%, entre 43.532). Abaixo, duas frases dão a leitura comparativa: a mesma nota fica 45,8 pontos percentuais abaixo quando comparada com o grupo de contraste, e, sorteando uma pessoa da faixa e uma do contraste, a da faixa tem nota maior em 18,9% dos pares.

Na visão técnica, a tabela traz participantes, média, mediana, desvio-padrão e Z da nota em cada grupo, e o gráfico sobrepõe as duas distribuições, em faixas protegidas, com a nota do usuário marcada. As duas cores são da paleta usada em todo o produto (azul para o grupo do usuário e ocre para o contraste) e foram escolhidas para continuar distinguíveis por quem tem daltonismo.

## Módulo Recorte territorial

O módulo de Vinícius Joacir dos Anjos responde se a mesma nota ocupa a mesma posição no estado, na região e no Brasil. O usuário informa a UF onde fez a prova, com sigla e nome.

Figura: g_territorial.png | 16 | Módulo Recorte territorial (Santa Catarina; Matemática 650,0; 2022): à esquerda, o resultado e a visão técnica com as medidas e as curvas da UF, da região e do Brasil; à direita, o gráfico de pontos com a mediana de cada UF
Fonte: capturas do Radar ENEM feitas pela equipe em 24/11/2026, com `dist_territorial.parquet` gerado a partir dos Microdados do ENEM 2022 (INEP).

Os três cartões mostram a posição em Santa Catarina (76,4%, entre 43.658 participantes), na Região Sul (77,8%, entre 211.210) e no Brasil (81,4%, entre 1.927.753). As frases informam a diferença entre a UF e o Brasil (5,0 pontos percentuais abaixo), a probabilidade de superioridade de Santa Catarina contra o restante do país (56,6%) e da Região Sul contra o restante (55,4%) e a posição da mediana de Santa Catarina entre as 27 UFs (3ª maior).

O gráfico da mediana de cada UF era, até a AV4, um gráfico de barras com o eixo cortado, o que exagerava as diferenças entre estados. Na AV6 ele virou um gráfico de pontos (*dot plot*), em que o eixo ajustado aos dados não engana, porque a leitura é de posição e não de comprimento. O N de cada UF passou para o rótulo do eixo, para que a informação essencial não dependa de passar o mouse. A UF do usuário aparece como losango, as UFs da mesma região em ocre e as demais como círculos vazados.

## Módulo Capital escolar familiar

O módulo de Guilherme da Silva Anselmo compara a nota entre participantes cujos responsáveis têm a mesma escolaridade. O usuário responde às duas perguntas do questionário (pai e mãe, ou os responsáveis), e o nível do participante é o maior dos dois.

Figura: g_capital.png | 16 | Módulo Capital escolar familiar (pai e mãe com ensino médio completo, alternativa E; Matemática 650,0; 2022): à esquerda, o resultado; à direita, a visão técnica
Fonte: capturas do Radar ENEM feitas pela equipe em 24/11/2026, com `dist_capital.parquet` gerado a partir dos Microdados do ENEM 2022 (INEP).

A página informa o grupo do usuário ("ensino médio completo, o maior nível entre pai e mãe") e mostra a posição nesse grupo (85,2%, entre 729.727 participantes) e no Brasil (81,4%). A comparação com outro nível de escolaridade é opcional, por uma caixa de seleção, porque pode causar desconforto em quem a lê como ranking de pessoas (DL-05, item 5).

## Visão simples, visão técnica e dicionário de indicadores

Todo resultado do produto aparece em duas abas, criadas na AV6 para adequar a representação a dois públicos diferentes. A "Visão simples", aberta por padrão, é para o público geral: uma frase em linguagem comum, em frequência natural, e barras de 0 a 100% por grupo. A "Visão técnica" é para quem quer o detalhe: tabela de medidas, curvas de distribuição, quartis e medianas das UFs. As duas mostram o mesmo resultado, e a visão simples usa o texto já protegido pelos limites de exibição, de modo que nenhuma das duas revela mais que a outra.

Cada número exibido tem um contrato em `docs/indicadores.md`, no formato de contrato de indicador: pergunta, fórmula, universo, unidade, arredondamento, regra de exibição e dono. O produto não tem metas nem semáforos, porque descreve uma posição e não pede uma ação; por isso os campos de meta, limiar de alerta e responsável pela ação não se aplicam.

Quadro: Indicadores exibidos pelo Radar ENEM
Larguras: 9,22,41,28
| ID | Indicador | Fórmula e regra | Exibição |
| --- | --- | --- | --- |
| IND-01 | Percentil | (abaixo + iguais/2) / N × 100; exato no Brasil, com limites de exibição em UF, região, faixa e nível | Anel, cartões, frase em frequência natural e barra |
| IND-02 | Média, mediana e desvio | Momentos populacionais; mediana inferior | Tabela da visão técnica, 1 casa |
| IND-03 | Quartis e caixa protegida | Q1, mediana e Q3; bigodes em P5 e P95; só com N ≥ 2.000 | Boxplot horizontal com a nota marcada |
| IND-04 | Z-Score | (nota − média) / desvio; nunca convertido em percentil pela normal | Tabela, 2 casas |
| IND-05 | Diferença de posição | Percentil no grupo A − percentil no grupo B, em pp; omitida se um dos dois estiver em limite | Frase comparativa |
| IND-06 | Probabilidade de superioridade | P(A > B) + 0,5 · P(A = B) | Frase "sorteando uma pessoa de cada grupo" |
| IND-07 | Posição da mediana da UF | 1 + número de UFs com mediana maior; empatadas dividem a posição | Frase e gráfico de pontos |
| IND-08 | Tamanho do grupo (N) | Elegíveis do grupo com nota na área; abaixo de 100, "grupo insuficiente" | Sempre ao lado do resultado |
Fonte: `docs/indicadores.md`.

## Identidade visual, temas e responsividade

A interface usa as fontes IBM Plex Sans e IBM Plex Mono, servidas pelo próprio app a partir de `app/static/fonts/`, com licença OFL. Buscar as fontes no Google enviaria o endereço IP de cada visitante a um terceiro, o que contraria a regra R6; por isso o servidor de arquivos estáticos foi ligado só para as fontes, com as condições registradas na DL-09 (seção 6.11).

A identidade visual final entrou no PR #38, revisado e aprovado por Guilherme da Silva Anselmo: o logotipo do Radar ENEM no topo da barra lateral, o logotipo da KiraSapiens Neurotech no pé dela e bordas e arcos em azul neon, inspirados no ambiente virtual de aprendizagem Neolevel, também criado pelo PO. O neon é ciano (`#22d3ee`) no tema escuro e azul forte (`#1d4ed8`) no tema claro, para manter o contraste sobre fundo branco. Os arcos decorativos ficam só nas margens da página: no pente fino, a coluna de conteúdo ganhou fundo opaco, depois que a avaliação heurística mostrou arcos passando por trás do texto do resultado.

O tema claro é o padrão, e o escuro é opcional. Os papéis das cores nos gráficos são fixos nos dois temas: azul para o grupo do usuário, ocre para o segundo grupo e verde-azulado para o Brasil. Até a AV4 o Brasil era cinza; na AV6 passou ao verde-azulado da paleta Okabe-Ito, segura para daltonismo, porque cinza sugere "sem dado" e tinha contraste baixo no tema escuro. A nota do usuário é marcada também por forma (linha tracejada ou losango), para que a identidade nunca dependa só da cor.

Figura: g_temas.png | 12,5 | À esquerda, o tema escuro ativado pelo interruptor "Modo escuro" (Recorte territorial); à direita, telas em largura de celular (390 px): página inicial, Recorte territorial e visão técnica do Capital escolar
Fonte: capturas do Radar ENEM feitas pela equipe em 24/11/2026.

Em largura de celular, a barra lateral se recolhe num botão, o formulário passa a uma coluna, os cartões de resultado são empilhados e as tabelas da visão técnica cabem na largura da tela. No pente fino, as quatro páginas foram conferidas também com 375 px de largura, nos dois temas, sem texto cortado.

## Acessibilidade

O RNF05 pede acessibilidade, e o teste com pessoas do público-alvo não pôde ser feito (DL-10, seção 6.9). Para cobrir parte desse risco, a equipe fez duas verificações que não dependem de usuários externos.

**Auditoria automática.** A ferramenta axe-core 4.14, com as regras dos níveis A e AA da WCAG 2.0 e 2.1, foi aplicada com o app rodando sobre os artefatos reais e depois de uma comparação (Matemática 650), para que o resultado também fosse auditado, em 16 combinações: 4 páginas, 2 temas e 2 larguras de tela (1.280 px e 375 px). A primeira rodada encontrou 2 violações críticas por página, nas 16 combinações: os dois logotipos do PR #38 sem texto alternativo (`image-alt`). Corrigido o `alt`, a segunda rodada terminou com **0 violações** nas 16 combinações.

**Contraste conferido em teste.** O axe não calcula contraste de texto sobre imagem de fundo, problema resolvido pelo desenho (arcos só nas margens). O contraste das cores de dados (3:1 contra o fundo) e dos textos (4,5:1, e 7:1 nos tons fortes) nos dois temas é conferido pelos testes de `tests/test_ui.py`, que falham se alguém trocar uma cor por outra com contraste insuficiente.

**Avaliação heurística.** O PO percorreu as quatro páginas no computador e no celular, nos dois temas, aplicando as dez heurísticas de Nielsen, com gravidade de 0 a 4. Foram encontrados três problemas de gravidade 2, todos corrigidos no pente fino: a mensagem técnica "Running carregar()" na primeira abertura depois de publicar, trocada por "Carregando os dados do ENEM..."; a legenda dos cartões, que dizia "acima dessa porcentagem" e passou a dizer "parcela dos N participantes com nota menor que a sua, contando metade de quem tirou a mesma nota", igual à definição do cálculo (posto médio); e os arcos atrás do texto. As outras sete heurísticas não tiveram problemas (gravidade 0). O quadro completo está em `docs/qa/relatorio-qa-av6.md`, seção 5.2.

Essas verificações não medem se um usuário real entende o resultado sozinho. O protocolo do teste de usabilidade, com tarefas, métricas e roteiro, está pronto em `docs/qa/teste-usabilidade.md` para uma próxima versão.

## Privacidade na interface

A regra R6 de `docs/privacidade.md` trata as notas, a renda, a UF e a escolaridade informadas como dados pessoais no momento em que chegam ao produto (RNF04). A implementação na interface é a seguinte:

- as entradas ficam só no estado da sessão do Streamlit e são descartadas quando a aba é fechada; não são gravadas em banco, arquivo ou armazenamento do navegador;
- as entradas não vão para a URL: o app não usa parâmetros de consulta, e o teste `test_notas_nao_vao_para_a_url` falha se isso mudar;
- os erros mostram só o tipo da exceção (`showErrorDetails = "type"`), e o código não escreve as entradas em log;
- o app não envia nada a terceiros: a telemetria do Streamlit está desligada (`gatherUsageStats = false`), as fontes são locais e, na publicação, as análises de visitantes e o widget de feedback do Replit ficam desligados;
- nenhum grupo com menos de 100 participantes é exibido, e as pontas da distribuição de grupos menores que o Brasil aparecem como "acima de X%" ou "abaixo de X%" (seção 4.7);
- o dado sensível (cor ou raça, regra R4) não é usado por nenhum módulo, e o município (regra R5) foi deixado de fora do módulo territorial.

O texto de cada página usa linguagem observacional ("a mesma nota fica em posições diferentes conforme o grupo") e avisa que o resultado não prevê aprovação e não indica causa.
